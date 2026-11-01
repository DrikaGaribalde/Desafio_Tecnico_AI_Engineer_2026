"""Coordena histórico e execução controlada de ferramentas."""

import json
import re

from emporio.catalog import _normalize
from emporio.context import fits_context
from emporio.ollama_client import OllamaError
from emporio.prompts import SYSTEM_PROMPT
from emporio.tools import TOOLS, execute_tool


def _clarification_focus(text, has_history):
    """Reconhece somente aberturas simples sem dados; consultas explícitas seguem o fluxo normal."""
    if has_history:
        return None
    normalized = _normalize(text)
    if re.search(r"\d|preco|custa|valor|estoque|disponiv|pedido|promoc|politica|garantia|prazo|troca|devol|horario|frete|pagamento|parcel", normalized):
        return None
    if not re.search(r"violao|guitarra|teclado|baixo|instrumento|bateria|ukulele|piano|sax|flauta|violino", normalized):
        return None
    if ("nao sei qual escolher" in normalized or "nao sei qual comprar" in normalized) and not re.search(
        r"orcamento|reais|gastar|comecando|iniciante|ja toco|experiente", normalized
    ):
        return "Neste turno, pergunte apenas se está começando ou já toca e a faixa de preço. Não liste produtos ou fatos comerciais."
    if "chegou" in normalized and re.search(r"sem funcionar|nao funciona|defeito|quebrad", normalized):
        return "Neste turno, acolha o problema e pergunte quando recebeu. Não explique regras, não aprove troca nem prometa resolver. Não use nome não informado."
    return None


_ACCESSORIES = r"(?:cabos?|palhetas?|pedais|pedal|cases?|amplificadores?|acessorios?|cordas?(?!\s+orquestrais))"


def _accessory_exchange_question(text):
    # O objeto da troca precisa ser o acessório. Não bloqueia "trocar meu
    # violão que veio com cordas", nem instrumentos de cordas orquestrais.
    normalized = _normalize(text)
    return bool(re.search(
        r"\b(?:troca|trocar|trocas|devolver|devolucao)\s+"
        r"(?:(?:de|do|da|dos|das|o|a|os|as|meu|minha|meus|minhas|um|uma)\s+)*"
        + _ACCESSORIES + r"\b", normalized
    ))


def _accessory_scope_question(text):
    normalized = _normalize(text)
    sale_text = re.sub(r"\binstrumentos?\s+de\s+cordas\b", "instrumento", normalized)
    return _accessory_exchange_question(text) or bool(
        re.search(r"\b(vendem|vende|comercializam)\b", normalized)
        and re.search(r"\b" + _ACCESSORIES + r"\b", sale_text)
        and not re.search(r"preco|quanto|custa|orcamento", normalized)
    )


class Agent:
    def __init__(self, catalog, client, max_tool_calls=3, policies=None, orders=None):
        self.catalog = catalog
        self.client = client
        self.max_tool_calls = max_tool_calls
        self.turns = []
        self.last_trace = []
        self.last_usage = []
        self.policies = policies
        self.orders = orders
        self.last_model_answer = None

    def reply(self, text):
        self.last_trace = []
        self.last_usage = []
        self.last_model_answer = None
        if not text.strip():
            return "Digite uma pergunta sobre os instrumentos."
        if len(text) > 2000:
            return "Sua mensagem é muito longa. Use até 2.000 caracteres."
        if _accessory_scope_question(text):
            # Consulta de escopo iniciada pela aplicação: o modelo local chegou
            # a chamar catálogo ou emitir JSON de função como texto nesse caso.
            # Consulta o escopo antes de qualquer regra de troca. A pergunta
            # original com "trocar" favorecia a recuperação indevida da seção 4.
            arguments = {"pergunta": "A loja comercializa acessórios?"}
            result = execute_tool(self.catalog, "consultar_politicas", arguments, self.policies, self.orders)
            self.last_trace.append({"ferramenta": "consultar_politicas", "argumentos": arguments,
                                    "resultado": result, "origem": "aplicacao"})
            scope = next((section for section in result.get("secoes", [])
                          if section["id"] == "1" and "nao comercializamos acessorios" in _normalize(section["texto"])), None)
            if scope is not None:
                answer = "A gente trabalha só com instrumentos musicais e não vende acessórios."
                if _accessory_exchange_question(text):
                    answer += " Por isso, não vou aplicar a política de troca de instrumentos a esses acessórios."
                    if re.search(r"\bcordas?\b", _normalize(text)):
                        answer += (" Se você quis dizer substituir as cordas de um instrumento, "
                                   "não tenho informações para confirmar esse serviço de manutenção na loja.")
                # Rodapé oculto no terminal; a referência continua em last_trace.
                # answer += "\n\nFontes consultadas: " + scope["referencia"] + "."
            else:
                answer = "Não consegui confirmar essa informação no manual agora. Você pode tentar novamente daqui a pouco."
            self.turns = (self.turns + [[{"role": "user", "content": text},
                                        {"role": "assistant", "content": answer}]])[-4:]
            return answer
        # Mantém turnos completos para não separar chamadas de seus resultados.
        history = []
        for turn in reversed(self.turns[-4:]):
            if len(json.dumps(turn, ensure_ascii=False)) + len(json.dumps(history, ensure_ascii=False)) > 10000:
                break
            history = turn + history
        focus = _clarification_focus(text, bool(self.turns))
        if focus:
            active_tools = []
        else:
            active_tools = TOOLS
        system = [{"role": "system", "content": SYSTEM_PROMPT + ("\n" + focus if focus else "")}]
        current = [{"role": "user", "content": text}]
        count = 0
        try:
            while True:
                # Remove turnos antigos completos, sem cortar regras, exceções ou
                # resultados do turno atual. Se nem assim couber, não envia ao LLM.
                while history and not fits_context(system + history + current, active_tools):
                    history.pop(0)
                    while history and history[0]["role"] != "user":
                        history.pop(0)
                if not fits_context(system + history + current, active_tools):
                    return "Não há espaço para as fontes completas nesta consulta. Faça uma pergunta mais específica."
                message = self.client.chat(system + history + current, active_tools)
                usage = getattr(self.client, "last_usage", {})
                if usage:
                    self.last_usage.append({**usage, "mensagens_historico": len(history)})
                calls = message.get("tool_calls", [])
                if calls and not active_tools:
                    return "Para seguir, preciso entender melhor sua necessidade. Pode dar mais detalhes?"
                if not calls:
                    answer = message.get("content", "").strip()
                    if not answer:
                        raise OllamaError("O modelo não produziu uma resposta. Tente reformular a pergunta.")
                    self.last_model_answer = answer
                    for trace in self.last_trace:
                        if trace["ferramenta"] == "consultar_politicas":
                            contact = trace["resultado"].get("decisoes_confirmadas", {}).get("whatsapp")
                            if contact:
                                answer = re.sub(r"\(?67\)?\s*3321[-\s]?4500", lambda _: contact, answer)
                    # Não depender da redação do LLM para autorizar acesso ou
                    # concluir elegibilidade quando a própria base não tem os dados.
                    order_results = [trace["resultado"] for trace in self.last_trace
                                     if trace["ferramenta"] == "consultar_pedido"]
                    return_sections = [section for trace in self.last_trace
                                       if trace["ferramenta"] == "consultar_politicas"
                                       for section in trace["resultado"].get("secoes", [])
                                       if section["id"] == "4.1"]
                    denied = next((result for result in order_results if result.get("encontrado") is False), None)
                    owned = next((result for result in order_results if result.get("encontrado") is True), None)
                    products = [product for trace in self.last_trace
                                if trace["ferramenta"] == "buscar_produtos"
                                for product in trace["resultado"].get("produtos", [])]
                    if denied is not None:
                        answer = denied["mensagem"]
                    elif owned is not None and return_sections:
                        answer = (
                            f"Para avaliar a devolução do pedido {owned['pedido_id']}, ainda preciso saber:\n"
                            "1. A compra foi online ou presencial?\n"
                            "2. Em que data você recebeu efetivamente o produto?\n"
                            "3. Ele está sem uso, na embalagem original, com acessórios e manuais?\n\n"
                            "A previsão de entrega não comprova a data de recebimento. "
                            "Não é possível confirmar elegibilidade com os dados disponíveis.\n\n"
                            "Para compras online, o manual informa:\n" + return_sections[0]["texto"]
                        )
                    elif (len(products) == 1 and products[0]["disponibilidade"] == "sem estoque"
                          and re.search(r"disponiv|estoque", _normalize(text))
                          and not re.search(r"preco|custa|valor|quanto|promoc", _normalize(text))):
                        answer = (f"O {products[0]['nome']} está sem estoque na base fornecida. "
                                  "Quer que eu consulte modelos parecidos? O que você mais gostou nele?")
                    current.append({**message, "content": answer})
                    self.turns = (self.turns + [current])[-4:]
                    references = list(dict.fromkeys(
                        section["referencia"] for trace in self.last_trace
                        if trace["ferramenta"] == "consultar_politicas"
                        for section in trace["resultado"].get("secoes", [])
                    ))
                    # Rodapé oculto no terminal; referências permanecem em last_trace.
                    # if references:
                    #     answer += "\n\nFontes consultadas: " + "; ".join(references) + "."
                    return answer
                if count + len(calls) > self.max_tool_calls:
                    return "Não consegui concluir a consulta dentro do limite de ferramentas. Tente uma pergunta mais específica."
                current.append(message)
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    name = function.get("name", "") if isinstance(function, dict) else ""
                    arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
                    result = execute_tool(self.catalog, name, arguments, self.policies, self.orders)
                    self.last_trace.append({"ferramenta": name, "argumentos": arguments, "resultado": result})
                    current.append({"role": "tool", "tool_name": name,
                                    "content": json.dumps(result, ensure_ascii=False, separators=(",", ":"))})
                    count += 1
        except OllamaError as exc:
            # Um turno incompleto não contamina o histórico para a próxima tentativa.
            return str(exc)
