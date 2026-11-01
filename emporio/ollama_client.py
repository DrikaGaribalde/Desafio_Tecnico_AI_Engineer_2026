"""Cliente HTTP local com a biblioteca padrão do Python."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3.1:latest", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages, tools):
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "stream": False, "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 768}}
        request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
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
