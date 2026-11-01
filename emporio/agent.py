"""Coordena histórico e execução controlada de ferramentas."""

import json

from emporio.ollama_client import OllamaError
from emporio.prompts import SYSTEM_PROMPT
from emporio.tools import TOOLS, execute_tool


class Agent:
    def __init__(self, catalog, client, max_tool_calls=3):
        self.catalog = catalog
        self.client = client
        self.max_tool_calls = max_tool_calls
        self.turns = []
        self.last_trace = []

    def reply(self, text):
        if not text.strip():
            return "Digite uma pergunta sobre os instrumentos."
        if len(text) > 2000:
            return "Sua mensagem é muito longa. Use até 2.000 caracteres."
        # Mantém turnos completos para não separar chamadas de seus resultados.
        history = []
        for turn in reversed(self.turns[-4:]):
            if len(json.dumps(turn, ensure_ascii=False)) + len(json.dumps(history, ensure_ascii=False)) > 10000:
                break
            history = turn + history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        current = [{"role": "user", "content": text}]
        self.last_trace = []
        count = 0
        try:
            while True:
                message = self.client.chat(messages + current, TOOLS)
                calls = message.get("tool_calls", [])
                if not calls:
                    answer = message.get("content", "").strip()
                    if not answer:
                        raise OllamaError("O modelo não produziu uma resposta. Tente reformular a pergunta.")
                    current.append(message)
                    self.turns = (self.turns + [current])[-4:]
                    return answer
                if count + len(calls) > self.max_tool_calls:
                    return "Não consegui concluir a consulta dentro do limite de ferramentas. Tente uma pergunta mais específica."
                current.append(message)
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    name = function.get("name", "") if isinstance(function, dict) else ""
                    arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
                    result = execute_tool(self.catalog, name, arguments)
                    self.last_trace.append({"ferramenta": name, "argumentos": arguments, "resultado": result})
                    current.append({"role": "tool", "tool_name": name,
                                    "content": json.dumps(result, ensure_ascii=False)})
                    count += 1
        except OllamaError as exc:
            # Um turno incompleto não contamina o histórico para a próxima tentativa.
            return str(exc)
