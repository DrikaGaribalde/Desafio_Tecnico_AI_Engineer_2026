"""Coordena histórico e execução controlada de ferramentas."""

import json

from emporio.context import fits_context
from emporio.ollama_client import OllamaError
from emporio.prompts import SYSTEM_PROMPT
from emporio.tools import TOOLS, execute_tool


class Agent:
    def __init__(self, catalog, client, max_tool_calls=3, policies=None):
        self.catalog = catalog
        self.client = client
        self.max_tool_calls = max_tool_calls
        self.turns = []
        self.last_trace = []
        self.last_usage = []
        self.policies = policies
        self.last_model_answer = None

    def reply(self, text):
        self.last_trace = []
        self.last_usage = []
        self.last_model_answer = None
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
        system = [{"role": "system", "content": SYSTEM_PROMPT}]
        current = [{"role": "user", "content": text}]
        count = 0
        try:
            while True:
                # Remove turnos antigos completos, sem cortar regras, exceções ou
                # resultados do turno atual. Se nem assim couber, não envia ao LLM.
                while history and not fits_context(system + history + current, TOOLS):
                    history.pop(0)
                    while history and history[0]["role"] != "user":
                        history.pop(0)
                if not fits_context(system + history + current, TOOLS):
                    return "Não há espaço para as fontes completas nesta consulta. Faça uma pergunta mais específica."
                message = self.client.chat(system + history + current, TOOLS)
                usage = getattr(self.client, "last_usage", {})
                if usage:
                    self.last_usage.append({**usage, "mensagens_historico": len(history)})
                calls = message.get("tool_calls", [])
                if not calls:
                    answer = message.get("content", "").strip()
                    if not answer:
                        raise OllamaError("O modelo não produziu uma resposta. Tente reformular a pergunta.")
                    current.append(message)
                    self.turns = (self.turns + [current])[-4:]
                    self.last_model_answer = answer
                    references = list(dict.fromkeys(
                        section["referencia"] for trace in self.last_trace
                        if trace["ferramenta"] == "consultar_politicas"
                        for section in trace["resultado"].get("secoes", [])
                    ))
                    if references:
                        answer += "\n\nFontes consultadas: " + "; ".join(references) + "."
                    return answer
                if count + len(calls) > self.max_tool_calls:
                    return "Não consegui concluir a consulta dentro do limite de ferramentas. Tente uma pergunta mais específica."
                current.append(message)
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    name = function.get("name", "") if isinstance(function, dict) else ""
                    arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
                    result = execute_tool(self.catalog, name, arguments, self.policies)
                    self.last_trace.append({"ferramenta": name, "argumentos": arguments, "resultado": result})
                    current.append({"role": "tool", "tool_name": name,
                                    "content": json.dumps(result, ensure_ascii=False, separators=(",", ":"))})
                    count += 1
        except OllamaError as exc:
            # Um turno incompleto não contamina o histórico para a próxima tentativa.
            return str(exc)
