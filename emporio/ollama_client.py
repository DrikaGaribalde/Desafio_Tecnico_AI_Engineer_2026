"""Cliente HTTP local com a biblioteca padrão do Python."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from emporio.context import CONTEXT_TOKENS, OUTPUT_TOKENS, fits_context, input_bound


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3.1:latest", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.last_usage = {}

    def chat(self, messages, tools, response_format=None):
        self.last_usage = {}
        if not fits_context(messages, tools):
            raise OllamaError("A consulta excede o orçamento de contexto. Faça uma pergunta mais específica ou inicie uma nova sessão.")
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "stream": False, "options": {"temperature": 0, "num_ctx": CONTEXT_TOKENS, "num_predict": OUTPUT_TOKENS}}
        if response_format is not None:
            payload["format"] = response_format
        request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError("A resposta deve ser um objeto JSON")
            self.last_usage = {"prompt_tokens": data.get("prompt_eval_count"),
                               "output_tokens": data.get("eval_count"),
                               "limite_contexto": CONTEXT_TOKENS,
                               "reserva_saida": OUTPUT_TOKENS,
                               "estimativa_conservadora_entrada": input_bound(messages, tools)}
            if data.get("prompt_eval_count", 0) + OUTPUT_TOKENS > CONTEXT_TOKENS:
                raise OllamaError("O prompt medido excedeu o orçamento reservado de contexto. Reformule a consulta.")
            message = data["message"]
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise ValueError("Mensagem inválida")
            if not isinstance(message.get("content", ""), str) or not isinstance(message.get("tool_calls", []), list):
                raise ValueError("Formato inválido")
            if data.get("done_reason") == "length":
                raise OllamaError("O modelo atingiu o limite de resposta. Tente uma pergunta mais específica.")
            return message
        except HTTPError as exc:
            raise OllamaError(f"Ollama respondeu com erro HTTP {exc.code}. Confira o serviço e o modelo com 'ollama list'.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaError("Não foi possível conversar com o Ollama. Abra o aplicativo ou execute 'ollama serve' e tente novamente; a consulta também pode ter excedido 120 segundos.") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaError("O Ollama devolveu uma resposta inválida. Tente novamente.") from exc
