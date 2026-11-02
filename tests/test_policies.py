import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.context import CONTEXT_TOKENS, OUTPUT_TOKENS, fits_context, input_bound
from emporio.ollama_client import OllamaClient, OllamaError
from emporio.policies import PolicyDataError, PolicyStore
from emporio.prompts import SYSTEM_PROMPT
from emporio.tools import TOOLS, execute_tool


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = PolicyStore()

    def test_accessories_scope_comes_from_manual(self):
        result = self.store.search("Vocês vendem cabo para guitarra?")
        self.assertEqual([s["id"] for s in result["secoes"]], ["1"])
        self.assertIn("não comercializamos acessórios", result["secoes"][0]["texto"])

    def test_whatsapp_uses_confirmed_decision_without_rewriting_pdf_text(self):
        result = self.store.search("Qual é o WhatsApp da loja?")
        self.assertEqual(result["decisoes_confirmadas"]["whatsapp"], "(67) 3341-4444")
        self.assertEqual({s["id"] for s in result["secoes"]}, {"7", "1.2"})
        self.assertIn("(67) 3321-4500", next(s["texto"] for s in result["secoes"] if s["id"] == "7"))

    def test_whatsapp_response_does_not_repeat_superseded_contact(self):
        class Client:
            def __init__(self):
                self.calls = 0
            def chat(self, messages, tools):
                self.calls += 1
                if self.calls == 1:
                    return {"role": "assistant", "content": "", "tool_calls": [{"function": {
                        "name": "consultar_politicas", "arguments": {"pergunta": "Qual o WhatsApp?"}}}]}
                return {"role": "assistant", "content": "O WhatsApp é (67) 3321-4500."}
        agent = Agent(Catalog(), Client())
        answer = agent.reply("Qual o WhatsApp da loja?")
        self.assertIn("(67) 3341-4444", answer)
        self.assertNotIn("3321-4500", answer)

    def test_saturday_includes_holiday_and_special_date_exceptions(self):
        result = self.store.search("horário de sábado")
        self.assertEqual([s["id"] for s in result["secoes"]], ["2"])
        text = result["secoes"][0]["texto"]
        for phrase in ("Sábado 09:00 às 13:00", "Domingo e Feriados Fechado", "datas especiais"):
            self.assertIn(phrase, text)
        self.assertIn("página(s) 2", result["secoes"][0]["referencia"])

    def test_return_keeps_conditions_without_importing_exchange_exclusions(self):
        result = self.store.search("devolução arrependimento online")
        self.assertEqual({s["id"] for s in result["secoes"]}, {"4.1"})
        text = result["secoes"][0]["texto"]
        for phrase in ("dias corridos", "recebimento", "embalagem original", "sem sinais de uso", "10 dias úteis", "por conta da loja"):
            self.assertIn(phrase, text)
        self.assertTrue(any("não inventar restrições" in note for note in result["ressalvas"]))

    def test_installments_keeps_conflicting_general_table(self):
        result = self.store.search("parcelamento")
        self.assertEqual({s["id"] for s in result["secoes"]}, {"3", "3.1"})
        self.assertTrue(any("divergência" in note for note in result["ressalvas"]))
        text = " ".join(s["texto"] for s in result["secoes"])
        for phrase in ("50,00", "80,00", "100,00", "2.000,00"):
            self.assertIn(phrase, text)

    def test_pix_and_promotions(self):
        result = self.store.search("acumular promoção desconto PIX")
        text = " ".join(s["texto"] for s in result["secoes"])
        self.assertIn("não são cumulativas", text)
        self.assertIn("não se aplica", text)

    def test_exact_500_has_confirmed_inclusive_regional_rule(self):
        result = self.store.search("frete para pedido de exatamente R$ 500")
        self.assertTrue(result["suficiente"])
        rule = result["decisoes_confirmadas"]["frete_metropolitano"]
        self.assertTrue(rule["limite_inclusivo"])
        self.assertEqual(rule["limite_frete_gratis_brl"], "500.00")
        self.assertEqual(rule["taxa_abaixo_do_limite_brl"], "35.00")
        self.assertEqual(rule["regiao"], "Região metropolitana de Campo Grande")
        text = " ".join(s["texto"] for s in result["secoes"])
        self.assertIn("acima de R$ 500", text)
        self.assertIn("abaixo de R$ 500", text)

    def test_shipping_from_campo_grande_keeps_other_cities(self):
        for question in (
            "Qual o frete de Campo Grande para outras cidades?",
            "Como funciona a entrega em Campo Grande e em outras cidades?",
            "Qual o frete para outras cidades?",
        ):
            with self.subTest(question=question):
                result = self.store.search(question)
                self.assertTrue(result["suficiente"])
                section = next(s for s in result["secoes"] if s["id"] == "5.2")
                self.assertEqual(section["texto"], self.store.sections["5.2"]["texto"])
                for term in ("CEP", "peso", "dimensões", "cotação individual"):
                    self.assertIn(term, section["texto"])
                self.assertTrue(any("não calcular frete" in note for note in result["ressalvas"]))

    def test_local_shipping_keeps_confirmed_regional_rule(self):
        result = self.store.search("Qual o frete na região metropolitana de Campo Grande?")
        self.assertTrue(result["suficiente"])
        self.assertIn("5.1", {s["id"] for s in result["secoes"]})
        rule = result["decisoes_confirmadas"]["frete_metropolitano"]
        self.assertTrue(rule["limite_inclusivo"])
        self.assertEqual(rule["limite_frete_gratis_brl"], "500.00")

    def test_no_match_and_no_partial_section(self):
        result = self.store.search("aulas de canto gratuitas")
        self.assertFalse(result["encontrado"])
        self.assertFalse(result["suficiente"])
        result = self.store.search("garantia", max_chars=100)
        self.assertTrue(result["encontrado"])
        self.assertFalse(result["suficiente"])
        self.assertEqual(result["secoes"], [])

    def test_warranty_dependencies(self):
        result = self.store.search("garantia")
        self.assertEqual({s["id"] for s in result["secoes"]}, {"8.1", "8.2", "8.3", "4.2"})
        self.assertTrue(result["suficiente"])

    def test_exchange_keeps_its_exclusions(self):
        result = self.store.search("troca por preferência")
        self.assertEqual({s["id"] for s in result["secoes"]}, {"4.3", "4.4"})
        self.assertIn("disponibilidade", result["secoes"][0]["texto"])
        self.assertIn('"venda final"', result["secoes"][1]["texto"])

    def test_validation_and_missing_policy_data(self):
        for args in ({}, {"pergunta": ""}, {"pergunta": 123}, {"pergunta": "x" * 501},
                     {"pergunta": "horário", "extra": True}):
            self.assertIn("erro", execute_tool(Catalog(), "consultar_politicas", args, self.store))
        with TemporaryDirectory() as directory:
            with self.assertRaises(PolicyDataError):
                PolicyStore(Path(directory))

    def test_pdf_hash_mismatch(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "políticas_da_loja.pdf").write_bytes(b"modified")
            (path / "politicas_secoes.json").write_text(json.dumps({
                "sha256_pdf": hashlib.sha256(b"original").hexdigest()}), encoding="utf-8")
            with self.assertRaisesRegex(PolicyDataError, "PDF mudou"):
                PolicyStore(path)


class ContextTests(unittest.TestCase):
    def test_client_refuses_oversized_request_before_http(self):
        messages = [{"role": "user", "content": "x" * CONTEXT_TOKENS}]
        self.assertFalse(fits_context(messages, TOOLS))
        with patch("emporio.ollama_client.urlopen") as http:
            with self.assertRaisesRegex(OllamaError, "orçamento"):
                OllamaClient().chat(messages, TOOLS)
            http.assert_not_called()

    def test_each_required_policy_fits_with_instructions_and_tool_call(self):
        store = PolicyStore()
        for question in ("horário sábado", "devolução online", "parcelamento", "PIX promoção", "frete exatamente 500", "garantia"):
            result = store.search(question)
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": "", "tool_calls": [{"function": {
                            "name": "consultar_politicas", "arguments": {"pergunta": question}}}]},
                        {"role": "tool", "tool_name": "consultar_politicas", "content": json.dumps(result, ensure_ascii=False)}]
            with self.subTest(question=question):
                self.assertLessEqual(input_bound(messages, TOOLS) + OUTPUT_TOKENS, CONTEXT_TOKENS)

    def test_old_turn_removed_without_cutting_sources(self):
        class Client:
            def chat(self, messages, tools):
                self.messages = messages
                return {"role": "assistant", "content": "Olá"}
        client = Client()
        agent = Agent(Catalog(), client)
        agent.turns = [[{"role": "user", "content": "x" * 9000},
                        {"role": "assistant", "content": "antigo"}]]
        agent.reply("Olá")
        self.assertFalse(any(message.get("content") == "antigo" for message in client.messages))
