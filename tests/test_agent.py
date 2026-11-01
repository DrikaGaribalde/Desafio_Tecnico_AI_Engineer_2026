import unittest
from unittest.mock import patch
from urllib.error import URLError

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.ollama_client import OllamaClient, OllamaError
from emporio.tools import execute_tool


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

    def test_promotion_values_and_no_matches(self):
        product = execute_tool(self.catalog, "buscar_produtos", {"nome": "KAL-700T"})["produtos"][0]
        self.assertEqual((product["preco_original_brl"], product["desconto_percentual"],
                          product["preco_final_brl"]), ("359.00", "10", "323.10"))
        self.assertEqual(execute_tool(self.catalog, "buscar_produtos", {"nome": "inexistente"})["total"], 0)

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
        for question in ("Posso trocar meu violão que veio com cordas e cabos?",
                         "Vocês vendem instrumentos de cordas?", "Vocês vendem cordas orquestrais?"):
            with self.subTest(question=question):
                client = FakeClient([{"role": "assistant", "content": "Vou verificar."}])
                agent = Agent(Catalog(), client)
                agent.reply(question)
                self.assertEqual(len(client.requests), 1)
                self.assertEqual(agent.last_trace, [])

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
