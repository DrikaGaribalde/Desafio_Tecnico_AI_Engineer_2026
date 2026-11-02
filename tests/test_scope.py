import io
import json
import unittest
from unittest.mock import patch

from emporio.agent import Agent, OUT_OF_SCOPE_ANSWER
from emporio.catalog import Catalog
from emporio.ollama_client import OllamaClient, OllamaError
from emporio.scope import SCOPE_FORMAT, classify_scope


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def chat(self, messages, tools, response_format=None):
        self.requests.append((messages, tools))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def message(content):
    return {"role": "assistant", "content": content}


class ScopeTests(unittest.TestCase):
    def test_classifier_requests_structured_output_over_http(self):
        response = {"message": message('{"escopo":"fora"}')}
        with patch("emporio.ollama_client.urlopen", return_value=io.StringIO(json.dumps(response))) as http:
            self.assertEqual(classify_scope(OllamaClient(), "Uma pergunta", [])["escopo"], "fora")
        payload = json.loads(http.call_args.args[0].data)
        self.assertEqual(payload["format"], SCOPE_FORMAT)
        self.assertEqual(payload["tools"], [])

    def test_outside_redirects_after_classification_without_business_tools(self):
        client = Client([message('{"escopo":"fora"}')])
        agent = Agent(Catalog(), client)
        self.assertEqual(agent.reply("Me ajude com meu imposto de renda"), OUT_OF_SCOPE_ANSWER)
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0][1], [])
        self.assertEqual(agent.last_trace, [])
        self.assertIsNone(agent.last_model_answer)
        self.assertEqual(agent.last_scope["escopo"], "fora")
        self.assertEqual(agent.turns[-1][-1]["content"], OUT_OF_SCOPE_ANSWER)

    def test_store_and_ambiguous_follow_normal_flow(self):
        for label, question in (("loja", "Vocês oferecem aulas?"), ("ambiguo", "E esse?")):
            with self.subTest(label=label):
                client = Client([message('{"escopo":"' + label + '"}'), message("Pode explicar melhor?")])
                agent = Agent(Catalog(), client)
                self.assertEqual(agent.reply(question), "Pode explicar melhor?")
                self.assertEqual(len(client.requests), 2)
                self.assertTrue(client.requests[1][1])

    def test_invalid_classification_does_not_lookup_or_save_turn(self):
        for content in ('[]', 'null', 'loja', '{"escopo":"outro"}',
                        '{"escopo":"loja","extra":true}', '{"escopo":[]}'):
            with self.subTest(content=content):
                client = Client([message(content)])
                agent = Agent(Catalog(), client)
                self.assertIn("Não consegui identificar", agent.reply("Uma pergunta"))
                self.assertEqual(len(client.requests), 1)
                self.assertEqual(agent.turns, [])
                self.assertEqual(agent.last_trace, [])

    def test_failure_preserves_history_and_allows_retry(self):
        client = Client([OllamaError("Ollama indisponível"), message('{"escopo":"fora"}')])
        agent = Agent(Catalog(), client)
        self.assertIn("indisponível", agent.reply("Uma pergunta"))
        self.assertEqual(agent.turns, [])
        self.assertEqual(agent.reply("Uma pergunta"), OUT_OF_SCOPE_ANSWER)

    def test_classifier_receives_recent_text_without_tool_messages(self):
        turns = [[{"role": "user", "content": "Quanto custa o GD20?"},
                  {"role": "assistant", "content": "", "tool_calls": []},
                  {"role": "tool", "content": "fonte"},
                  {"role": "assistant", "content": "R$ 2.199,00"}]]
        client = Client([message('{"escopo":"loja"}')])
        result = classify_scope(client, "E no PIX?", turns)
        self.assertEqual(result["escopo"], "loja")
        sent, tools = client.requests[0]
        self.assertEqual([m["role"] for m in sent], ["system", "user", "assistant", "user"])
        self.assertEqual(sent[1]["content"], "Quanto custa o GD20?")
        self.assertEqual(sent[-1]["content"], "E no PIX?")
        self.assertEqual(tools, [])

    def test_classifier_rejects_tool_calls(self):
        client = Client([{**message('{"escopo":"loja"}'), "tool_calls": [{}]}])
        with self.assertRaises(OllamaError):
            classify_scope(client, "Uma pergunta", [])
