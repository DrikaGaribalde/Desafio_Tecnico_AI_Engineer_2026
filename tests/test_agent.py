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
