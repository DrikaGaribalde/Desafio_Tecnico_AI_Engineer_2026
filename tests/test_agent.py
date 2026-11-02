import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from emporio.agent import Agent, OUT_OF_SCOPE_ANSWER
from emporio.catalog import Catalog
from emporio.context import fits_context
from emporio.ollama_client import OllamaClient, OllamaError
from emporio.prompts import SYSTEM_PROMPT
from emporio.tools import TOOLS, execute_tool


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()

    def test_name_search_without_id_mapping(self):
        result = execute_tool(self.catalog, "buscar_produtos", {"nome": "Takamine GD20"})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["produtos"][0]["preco_final_brl"], "2199.00")

    def test_empty_optional_filters_mean_no_constraint(self):
        result = execute_tool(self.catalog, "buscar_produtos", {
            "nome": "Takamine GD20", "categoria": "", "preco_maximo": ""})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["produtos"][0]["preco_final_brl"], "2199.00")

    def test_category_and_price(self):
        result = execute_tool(self.catalog, "buscar_produtos", {
            "categoria": "violoes", "preco_maximo": "1000", "disponibilidade": "disponiveis"})
        self.assertGreater(result["total"], 0)
        self.assertTrue(all(p["categoria"] == "Violões" for p in result["produtos"]))
        self.assertTrue(all(p["disponibilidade"] == "disponível" for p in result["produtos"]))

    def test_distinct_unavailable_states(self):
        for query, state in [("GF-3D", "sem estoque"), ("SN-7C", "descontinuado"),
                             ("KA-ABP-CTG", "lançamento futuro")]:
            with self.subTest(query=query):
                result = execute_tool(self.catalog, "buscar_produtos", {"nome": query})
                self.assertEqual(result["produtos"][0]["disponibilidade"], state)

    def test_available_filter_diagnoses_existing_unavailable_models(self):
        for name, state in (("GF-3D", "sem estoque"), ("SN-7C", "descontinuado"),
                            ("KA-ABP-CTG", "lançamento futuro")):
            with self.subTest(name=name):
                result = execute_tool(self.catalog, "buscar_produtos", {"nome": name, "disponibilidade": "disponiveis"})
                self.assertEqual(result["produtos"], [])
                self.assertEqual(result["total"], 0)
                self.assertEqual(result["total_indisponiveis"], 1)
                self.assertEqual(result["indisponiveis"][0]["disponibilidade"], state)
                self.assertFalse(result["indisponiveis"][0]["disponivel_para_compra"])

    def test_unavailable_diagnosis_preserves_other_filters(self):
        for args in ({"nome": "GF-3D", "preco_maximo": "100"},
                     {"nome": "GF-3D", "categoria": "Ukuleles"},
                     {"nome": "produto inexistente"}, {"categoria": "inexistente"}):
            with self.subTest(args=args):
                result = execute_tool(self.catalog, "buscar_produtos", {**args, "disponibilidade": "disponiveis"})
                self.assertEqual(result["produtos"], [])
                self.assertNotIn("indisponiveis", result)
        result = execute_tool(self.catalog, "buscar_produtos", {"categoria": "Violões", "disponibilidade": "disponiveis"})
        self.assertTrue(all(p["disponivel_para_compra"] for p in result["produtos"]))
        self.assertNotIn("indisponiveis", result)

    def test_promotion_values_and_no_matches(self):
        product = execute_tool(self.catalog, "buscar_produtos", {"nome": "KAL-700T"})["produtos"][0]
        self.assertEqual((product["preco_original_brl"], product["desconto_percentual"],
                          product["preco_final_brl"]), ("359.00", "10", "323.10"))
        self.assertEqual(execute_tool(self.catalog, "buscar_produtos", {"nome": "inexistente"})["total"], 0)

    def test_pix_price_is_exposed_without_stacking_promotions(self):
        for name, final_price, pix_price in (
            ("Takamine GD20", "2199.00", "2089.05"),
            ("Yamaha C40", "599.90", "569.91"),
            ("KAL-700T", "323.10", "323.10"),
        ):
            with self.subTest(name=name):
                product = execute_tool(self.catalog, "buscar_produtos", {"nome": name})["produtos"][0]
                self.assertEqual(product["preco_final_brl"], final_price)
                self.assertEqual(product["preco_pix_brl"], pix_price)

    def test_pagination_covers_all_matches_in_order(self):
        filters = {"nome": "nylon", "categoria": "Violões", "disponibilidade": "disponiveis"}
        expected = self.catalog.search_products("nylon", category="Violões")
        names = []
        for page, expected_size in ((1, 5), (2, 5), (3, 4)):
            result = execute_tool(self.catalog, "buscar_produtos", {**filters, "pagina": page})
            self.assertEqual(result["total"], 14)
            self.assertEqual(result["pagina"], page)
            self.assertEqual(result["total_paginas"], 3)
            self.assertEqual(result["proxima_pagina"], page + 1 if page < 3 else None)
            self.assertEqual(len(result["produtos"]), expected_size)
            names.extend(p["nome"] for p in result["produtos"])
        self.assertEqual(names, [p.name for p in expected])
        self.assertEqual(len(set(names)), len(names))

    def test_pagination_validation_empty_results_and_default(self):
        for page in (True, False, 0, -1, 1.5, None, [], "1.0", "x", 1000001):
            with self.subTest(page=page):
                self.assertIn("erro", execute_tool(self.catalog, "buscar_produtos", {"pagina": page}))
        self.assertIn("erro", execute_tool(self.catalog, "buscar_produtos", {"nome": "GD20", "pagina": 2}))
        default = execute_tool(self.catalog, "buscar_produtos", {"nome": "GD20"})
        self.assertEqual(default, execute_tool(self.catalog, "buscar_produtos", {"nome": "GD20", "pagina": "1"}))
        self.assertEqual(default["total_paginas"], 1)
        self.assertIsNone(default["proxima_pagina"])
        empty = execute_tool(self.catalog, "buscar_produtos", {"nome": "inexistente"})
        self.assertEqual(empty["total_paginas"], 0)
        self.assertEqual(empty["produtos"], [])
        self.assertIsNone(empty["proxima_pagina"])

    def test_nylon_page_fits_context_with_tool_result(self):
        arguments = {"nome": "nylon", "categoria": "Violões", "disponibilidade": "disponiveis"}
        result = execute_tool(self.catalog, "buscar_produtos", arguments)
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "Quais os violões de nylon?"},
                    {"role": "assistant", "content": "", "tool_calls": [{"function": {
                        "name": "buscar_produtos", "arguments": arguments}}]},
                    {"role": "tool", "tool_name": "buscar_produtos", "content": json.dumps(result, ensure_ascii=False)}]
        self.assertTrue(fits_context(messages, TOOLS))

    def test_argument_validation(self):
        invalid = [{"id": 95}, {"nome": 95}, {"categoria": None}, {"preco_maximo": True},
                   {"preco_maximo": "NaN"}, {"preco_maximo": "-1"}, {"preco_maximo": "1.000,00"},
                   {"disponibilidade": True}, {"disponibilidade": "invalida"}, [], {"nome": "x" * 201}]
        for arguments in invalid:
            with self.subTest(arguments=arguments):
                self.assertIn("erro", execute_tool(self.catalog, "buscar_produtos", arguments))
        self.assertIn("erro", execute_tool(self.catalog, "executar_codigo", {}))


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append(messages)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def call():
    return {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "buscar_produtos", "arguments": {"nome": "GD20"}}}]}


class AgentTests(unittest.TestCase):
    def setUp(self):
        # Estes testes isolam o atendimento. A classificação é exercitada em test_scope.
        scope = patch("emporio.agent.classify_scope", return_value={"escopo": "loja"})
        scope.start()
        self.addCleanup(scope.stop)

    def test_wrong_available_filter_cannot_hide_existing_product(self):
        for name, state in (("GF-3D", "sem estoque"), ("SN-7C", "descontinuado")):
            with self.subTest(name=name):
                client = FakeClient([
                    {"role": "assistant", "content": "", "tool_calls": [{"function": {
                        "name": "buscar_produtos", "arguments": {"nome": name, "disponibilidade": "disponiveis"}}}]},
                    {"role": "assistant", "content": "Esse produto não existe na loja."},
                ])
                agent = Agent(Catalog(), client)
                answer = agent.reply(f"O {name} está disponível?")
                self.assertIn(name, answer)
                self.assertIn(state, answer)
                self.assertIn("indisponível para compra", answer)
                self.assertNotIn("não existe", answer)
                self.assertEqual(agent.turns[-1][-1]["content"], answer)

    def test_unavailable_diagnosis_does_not_erase_other_product(self):
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "buscar_produtos", "arguments": {"nome": "GD20"}}},
                {"function": {"name": "buscar_produtos", "arguments": {"nome": "GF-3D", "disponibilidade": "disponiveis"}}},
            ]},
            {"role": "assistant", "content": "Não encontrei GF-3D."},
        ])
        answer = Agent(Catalog(), client).reply("Quanto custa GD20 e tem GF-3D?")
        for part in ("2199.00", "GD20", "GF-3D", "sem estoque"):
            self.assertIn(part, answer)

    def test_explicit_out_of_scope_requests_redirect_without_tools(self):
        for question in ("Me ensine uma receita de bolo de cenoura.",
                         "Quais ingredientes para preparar uma pizza?",
                         "Qual é a capital da França?", "Vai chover amanhã?"):
            with self.subTest(question=question):
                client = FakeClient([])
                agent = Agent(Catalog(), client, scope_classifier=lambda *_: {"escopo": "fora"})
                self.assertEqual(agent.reply(question), OUT_OF_SCOPE_ANSWER)
                self.assertEqual(client.requests, [])
                self.assertEqual(agent.last_trace, [])
                self.assertIsNone(agent.last_model_answer)
                self.assertEqual(agent.turns[-1][-1]["content"], OUT_OF_SCOPE_ANSWER)

    def test_scope_guard_preserves_store_questions_and_mixed_requests(self):
        for question in ("Qual a previsão de entrega do pedido 1?",
                         "Vocês vendem acessórios?", "Fale sobre a loja.",
                         "Quanto custa o Takamine GD20?", "Qual o preço da bateria?",
                         "Quero um violão e uma receita de bolo.", "E no PIX?", "continuar"):
            with self.subTest(question=question):
                agent = Agent(Catalog(), FakeClient([{"role": "assistant", "content": "Vou verificar."}]))
                self.assertNotEqual(agent.reply(question), OUT_OF_SCOPE_ANSWER)
        client = FakeClient([call(), {"role": "assistant", "content": "R$ 2.199,00"}])
        agent = Agent(Catalog(), client)
        with patch("emporio.agent.classify_scope", return_value={"escopo": "fora"}):
            agent.reply("Me ensine uma receita de bolo.")
        answer = agent.reply("Quanto custa o Takamine GD20?")
        self.assertIn("2.199", answer)
        self.assertEqual(agent.last_trace[0]["ferramenta"], "buscar_produtos")
    def test_paginated_response_preserves_other_product_queries(self):
        for extra, expected in (({"nome": "GD20"}, "Takamine GD20"),
                                ({"nome": "inexistente"}, "Não encontrei produtos"),
                                ({"nome": True}, "Não consegui consultar os produtos")):
            with self.subTest(extra=extra):
                client = FakeClient([
                    {"role": "assistant", "content": "", "tool_calls": [
                        {"function": {"name": "buscar_produtos", "arguments": {}}},
                        {"function": {"name": "buscar_produtos", "arguments": extra}},
                    ]},
                    {"role": "assistant", "content": "Resposta incompleta"},
                ])
                agent = Agent(Catalog(), client)
                answer = agent.reply("Liste produtos e consulte outro modelo")
                self.assertIn("página 1", answer)
                self.assertIn(expected, answer)
                self.assertEqual(agent._last_presented_product_page[0], {})
                self.assertEqual(agent.turns[-1][-1]["content"], answer)

    def test_failed_turn_does_not_replace_presented_page(self):
        search = {"role": "assistant", "content": "", "tool_calls": [{"function": {
            "name": "buscar_produtos", "arguments": {}}}]}
        for failure in ("http", "context", "limit"):
            with self.subTest(failure=failure):
                responses = [search, OllamaError("Falha simulada")] if failure == "http" else [search, search]
                agent = Agent(Catalog(), FakeClient(responses), max_tool_calls=1)
                # Uma página já apresentada deve sobreviver a uma nova tentativa falha.
                previous_args = {"categoria": "Violões", "nome": "nylon", "disponibilidade": "disponiveis"}
                previous = execute_tool(agent.catalog, "buscar_produtos", previous_args)
                agent._last_presented_product_page = (previous_args, previous)
                if failure == "context":
                    with patch("emporio.agent.fits_context", side_effect=[True, False]):
                        answer = agent.reply("Liste outros produtos")
                    self.assertIn("Não há espaço", answer)
                else:
                    answer = agent.reply("Liste outros produtos")
                    self.assertIn("Falha" if failure == "http" else "limite", answer)
                self.assertEqual(agent.turns, [])
                self.assertEqual(agent._last_presented_product_page, (previous_args, previous))
                self.assertIn("página 2", agent.reply("continuar"))
                self.assertEqual(agent.last_trace[0]["argumentos"], {**previous_args, "pagina": 2})

    def test_first_failed_search_cannot_skip_to_second_page(self):
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [{"function": {
                "name": "buscar_produtos", "arguments": {}}}]},
            OllamaError("Falha simulada"),
        ])
        agent = Agent(Catalog(), client)
        self.assertIn("Falha", agent.reply("Liste produtos"))
        self.assertIsNone(agent._last_presented_product_page)
        self.assertIn("Informe os filtros", agent.reply("continuar"))

    def test_next_page_preserves_filters_and_stops_at_end(self):
        arguments = {"nome": "nylon", "categoria": "Violões", "disponibilidade": "disponiveis"}
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [{"function": {
                "name": "buscar_produtos", "arguments": arguments}}]},
            {"role": "assistant", "content": "Há mais opções, sem listar produtos."},
        ])
        agent = Agent(Catalog(), client)
        first = agent.reply("Quais os violões de nylon disponíveis?")
        self.assertIn("Tagima Memphis", first)
        self.assertIn("página 1 de 3", first)
        self.assertIn("Digite 'continuar' para ver mais opções ou faça outra pergunta.", first)
        for page in (2, 3):
            answer = agent.reply("continuar" if page == 2 else "próxima página")
            self.assertIn(f"página {page} de 3", answer)
            self.assertEqual(agent.last_trace[0]["argumentos"], {**arguments, "pagina": page})
            for product in agent.last_trace[0]["resultado"]["produtos"]:
                self.assertIn(product["nome"], answer)
        self.assertIn("última página", answer)
        self.assertIn("não tem próxima página", agent.reply("continuar"))
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(agent.last_trace, [])
        self.assertIn("Informe os filtros", Agent(Catalog(), object()).reply("próxima página"))
        self.assertIn("Informe os filtros", Agent(Catalog(), object()).reply("continuar"))

    def test_price_and_warranty_preserves_model_answer(self):
        expected = "O Takamine custa R$ 2.199,00 e tem garantia legal de 90 dias após recebimento."
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "buscar_produtos", "arguments": {"nome": "Takamine GD20"}}},
                {"function": {"name": "consultar_politicas", "arguments": {"pergunta": "garantia"}}},
            ]},
            {"role": "assistant", "content": expected},
        ])
        agent = Agent(Catalog(), client)
        self.assertEqual(agent.reply("Quanto custa o Takamine GD20 e qual a garantia?"), expected)
        self.assertTrue(any(s["id"] == "4.2" for t in agent.last_trace
                            for s in t["resultado"].get("secoes", [])))
        self.assertIsNone(agent._exchange_topic)
        self.assertEqual(agent.turns[-1][-1]["content"], expected)

    def test_price_and_return_preserves_product_but_blocks_approval(self):
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "buscar_produtos", "arguments": {"nome": "KAL-700T"}}},
                {"function": {"name": "consultar_politicas", "arguments": {"pergunta": "arrependimento online"}}},
            ]},
            {"role": "assistant", "content": "Sua devolução está aprovada."},
        ])
        agent = Agent(Catalog(), client)
        answer = agent.reply("Quanto custa o KAL-700T e posso devolver se me arrepender?")
        for value in ("359.00", "10%", "323.10", "apenas informativo", "7 (sete) dias"):
            self.assertIn(value, answer)
        self.assertNotIn("devolução está aprovada", answer)
        self.assertEqual(agent.turns[-1][-1]["content"], answer)

    def test_opening_clarification_does_not_force_tool_call(self):
        class Client:
            def chat(self, messages, tools):
                self.tools = tools
                return {"role": "assistant", "content": "Você está começando ou já toca? Qual faixa de preço?"}
        client = Client()
        Agent(Catalog(), client).reply("Quero comprar um violão, mas não sei qual escolher.")
        self.assertEqual(client.tools, [])

    def test_explicit_price_keeps_tools_even_with_uncertainty(self):
        class Client:
            def chat(self, messages, tools):
                self.tools = tools
                return {"role": "assistant", "content": "Vou verificar."}
        client = Client()
        Agent(Catalog(), client).reply("Não sei qual escolher. Quanto custa o Takamine GD20?")
        self.assertTrue(any(tool["function"]["name"] == "buscar_produtos" for tool in client.tools))

    def test_accessory_scope_is_grounded_in_manual(self):
        class Client:
            def __init__(self):
                self.calls = 0
            def chat(self, messages, tools):
                self.calls += 1
                self.tools = tools
                if self.calls == 1:
                    return {"role": "assistant", "content": "", "tool_calls": [{"function": {
                        "name": "consultar_politicas", "arguments": {"pergunta": "Vocês vendem cabo?"}}}]}
                return {"role": "assistant", "content": "Sim, vendemos."}
        client = Client()
        agent = Agent(Catalog(), client)
        answer = agent.reply("Vocês vendem cabo para guitarra?")
        self.assertEqual(client.calls, 0)
        self.assertIn("não vende acessórios", answer)
        self.assertNotIn("Fontes consultadas", answer)
        self.assertIn("seção 1", agent.last_trace[0]["resultado"]["secoes"][0]["referencia"])
        self.assertIsNone(agent.last_model_answer)
        self.assertEqual(agent.last_trace[0]["origem"], "aplicacao")

    def test_accessory_without_source_does_not_assume_store_policy(self):
        class Store:
            def search(self, question):
                return {"encontrado": False, "suficiente": False, "secoes": []}
        agent = Agent(Catalog(), object(), policies=Store())
        answer = agent.reply("Vocês vendem cabo para guitarra?")
        self.assertIn("Não consegui confirmar", answer)
        self.assertNotIn("não vende acessórios", answer)

    def test_accessory_exchange_checks_scope_before_return_rules(self):
        agent = Agent(Catalog(), object())
        answer = agent.reply("posso fazer a trocar de cordas e cabos")
        self.assertIn("não vende acessórios", answer)
        self.assertIn("não vou aplicar a política de troca de instrumentos", answer)
        self.assertIn("não tenho informações para confirmar esse serviço", answer)
        self.assertNotIn("7 dias", answer)
        self.assertNotIn("Fontes consultadas", answer)
        self.assertEqual([s["id"] for s in agent.last_trace[0]["resultado"]["secoes"]], ["1"])

    def test_accessory_exchange_variations_are_not_approved(self):
        for item in ("cordas", "cabos", "palhetas", "cases", "pedais", "amplificadores"):
            with self.subTest(item=item):
                agent = Agent(Catalog(), object())
                answer = agent.reply(f"Posso trocar meus {item}?")
                self.assertIn("não vende acessórios", answer)
                self.assertNotIn("7 dias", answer)

    def test_instrument_exchange_is_not_blocked_by_mention_of_strings(self):
        agent = Agent(Catalog(), object())
        answer = agent.reply("Posso trocar meu violão que veio com cordas e cabos?")
        self.assertIn("apenas informativo", answer)
        self.assertNotIn("não vende acessórios", answer)
        for question in ("Vocês vendem instrumentos de cordas?", "Vocês vendem cordas orquestrais?"):
            with self.subTest(question=question):
                client = FakeClient([{"role": "assistant", "content": "Vou verificar."}])
                agent = Agent(Catalog(), client)
                agent.reply(question)
                self.assertEqual(len(client.requests), 1)
                self.assertEqual(agent.last_trace, [])

    def test_return_and_volunteered_receipt_do_not_start_workflow(self):
        agent = Agent(Catalog(), object())
        for question in ("Me arrependi da minha compra, posso devolver meu pedido?",
                         "10/10/26 e se encontra na embalagem original"):
            answer = agent.reply(question)
            self.assertIn("apenas informativo", answer)
            self.assertIn("não confirma a elegibilidade", answer)
            self.assertNotIn("forneça", answer.lower())
            self.assertNotIn("Você está dentro do prazo", answer)
            self.assertEqual(agent.last_trace[0]["origem"], "aplicacao")
            self.assertIsNone(agent.last_model_answer)

    def test_return_without_policy_source_does_not_invent_rules(self):
        class Store:
            def search(self, question):
                return {"suficiente": False, "secoes": []}
        answer = Agent(Catalog(), object(), policies=Store()).reply("Posso devolver?")
        self.assertIn("Não consegui consultar", answer)
        self.assertNotIn("7 dias", answer)

    def test_out_of_stock_does_not_offer_unimplemented_notification(self):
        client = FakeClient([
            {"role": "assistant", "content": "", "tool_calls": [{"function": {
                "name": "buscar_produtos", "arguments": {"nome": "Giannini GF-3D"}}}]},
            {"role": "assistant", "content": "Vamos cadastrar uma notificação de reposição."}])
        agent = Agent(Catalog(), client)
        answer = agent.reply("O Giannini GF-3D está disponível?")
        self.assertIn("sem estoque na base fornecida", answer)
        self.assertNotIn("notificação", answer)
        self.assertIn("notificação", agent.last_model_answer)

    def test_history_and_tool_result(self):
        client = FakeClient([call(), {"role": "assistant", "content": "R$ 2.199,00"},
                             {"role": "assistant", "content": "Continuação"}])
        agent = Agent(Catalog(), client)
        agent.reply("Preço do GD20?")
        self.assertEqual(client.requests[1][-1]["role"], "tool")
        agent.reply("E ele?")
        self.assertTrue(any(m.get("content") == "Preço do GD20?" for m in client.requests[2]))

    def test_history_keeps_four_complete_turns_across_reply_paths(self):
        client = FakeClient([call(), {"role": "assistant", "content": "R$ 2.199,00"}])
        agent = Agent(Catalog(), client)
        agent.reply("Preço do GD20?")
        self.assertEqual([m["role"] for m in agent.turns[0]],
                         ["user", "assistant", "tool", "assistant"])
        for question in ("Posso devolver?", "Vocês vendem cabo?", "Posso trocar?", "Vocês vendem palhetas?"):
            agent.reply(question)
        self.assertEqual(len(agent.turns), 4)
        self.assertEqual(agent.turns[0][0]["content"], "Posso devolver?")
        for turn in agent.turns:
            self.assertEqual(turn[0]["role"], "user")
            self.assertEqual(turn[-1]["role"], "assistant")
        # Antes da remoção, o primeiro turno também foi armazenado completo.
        self.assertEqual([m["role"] for m in client.requests[1][-3:]],
                         ["user", "assistant", "tool"])

    def test_limit_stops_repeated_calls(self):
        client = FakeClient([call(), call(), call(), call()])
        agent = Agent(Catalog(), client, max_tool_calls=3)
        self.assertIn("limite", agent.reply("Preço?"))
        self.assertEqual(len(agent.last_trace), 3)
        self.assertEqual(agent.turns, [])

    def test_unavailable_does_not_save_partial_turn(self):
        agent = Agent(Catalog(), FakeClient([OllamaError("Ollama indisponível")]))
        self.assertIn("indisponível", agent.reply("Olá"))
        self.assertEqual(agent.turns, [])

    def test_http_connection_failure(self):
        with patch("emporio.ollama_client.urlopen", side_effect=URLError("connection refused")):
            with self.assertRaisesRegex(OllamaError, "ollama serve"):
                OllamaClient().chat([], [])

    def test_invalid_http_payload_becomes_ollama_error(self):
        invalid = [[], None, "texto", 42, True, {}, {"message": None},
                   {"message": {"role": "user", "content": "Olá"}},
                   {"message": {"role": "assistant", "content": []}},
                   {"message": {"role": "assistant", "tool_calls": {}}}]
        for payload in invalid:
            with self.subTest(payload=payload):
                with patch("emporio.ollama_client.urlopen", return_value=io.StringIO(json.dumps(payload))):
                    with self.assertRaisesRegex(OllamaError, "resposta inválida"):
                        OllamaClient().chat([], [])
        with patch("emporio.ollama_client.urlopen", return_value=io.StringIO("{json incompleto")):
            with self.assertRaisesRegex(OllamaError, "resposta inválida"):
                OllamaClient().chat([], [])

    def test_invalid_http_payload_allows_next_turn(self):
        client = OllamaClient()
        agent = Agent(Catalog(), client)
        valid = {"message": {"role": "assistant", "content": "Como posso ajudar?"}}
        with patch("emporio.ollama_client.urlopen", side_effect=[
            io.StringIO("null"), io.StringIO(json.dumps(valid)),
        ]):
            self.assertIn("resposta inválida", agent.reply("Olá"))
            self.assertEqual(agent.turns, [])
            self.assertEqual(agent.reply("Olá novamente"), "Como posso ajudar?")
        self.assertEqual(len(agent.turns), 1)
