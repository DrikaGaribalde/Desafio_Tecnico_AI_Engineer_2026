"""Coordena histórico e execução controlada de ferramentas."""

import json
import re

from emporio.catalog import _normalize
from emporio.context import fits_context
from emporio.ollama_client import OllamaError
from emporio.prompts import SYSTEM_PROMPT
from emporio.scope import classify_scope
from emporio.tools import TOOLS, execute_tool


MAX_HISTORY_TURNS = 4
OUT_OF_SCOPE_ANSWER = (
    "Esse assunto fica fora do atendimento da Empório da Música. "
    "Posso ajudar com instrumentos musicais, produtos, pedidos e políticas da loja."
)


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


def _exchange_policy_topic(text):
    normalized = _normalize(text)
    if re.search(r"defeito|chegou.*(?:sem funcionar|nao funciona|quebrad)", normalized):
        return "trocas por defeito e garantia"
    if re.search(r"arrepend|devolv|devoluc|desisti da compra", normalized):
        return "arrependimento em compras online"
    if re.search(r"\b(?:troca|trocar|trocas)\b", normalized):
        return "trocas por preferência e itens não elegíveis para troca"
    return None


def _informational_policy_answer(sections):
    if not sections:
        return "Não consegui consultar a política agora. Você pode tentar novamente ou falar com o atendimento da loja."
    excerpts = "\n\n".join(section["titulo"] + "\n" + section["texto"] for section in sections)
    return ("Posso te explicar as regras da loja. Este atendimento é apenas informativo: "
            "não abre solicitações e não confirma a elegibilidade de uma compra específica.\n\n"
            + excerpts + "\n\nPara tratar de uma troca ou devolução, fale diretamente com o atendimento da loja.")


def _product_summary(product: dict) -> str:
    return (f"{product['nome']}: original R$ {product['preco_original_brl']}; "
            f"desconto {product['desconto_percentual']}%; final R$ {product['preco_final_brl']}; "
            f"PIX R$ {product['preco_pix_brl']}; {product['disponibilidade']}.")


def _product_page_answer(result: dict) -> str:
    if "erro" in result:
        return "Não consegui consultar os produtos: " + result["erro"]
    if not result["produtos"]:
        if result.get("indisponiveis"):
            lines = ["Não há produtos disponíveis para esses filtros. Na base fornecida:"]
            lines.extend(f"- {p['nome']}: {p['disponibilidade']}; indisponível para compra."
                         for p in result["indisponiveis"])
            if result["total_indisponiveis"] > len(result["indisponiveis"]):
                lines.append("Há outros indisponíveis; informe um modelo mais específico.")
            return "\n".join(lines)
        return "Não encontrei produtos para esses filtros na base fornecida."
    lines = [f"Na base fornecida: página {result['pagina']} de {result['total_paginas']}, "
             f"{result['total']} produtos encontrados."]
    for product in result["produtos"]:
        lines.append("- " + _product_summary(product))
    lines.append("Digite 'continuar' para ver mais opções ou faça outra pergunta." if result["proxima_pagina"] is not None
                 else "Esta é a última página.")
    return "\n".join(lines)


def _order_summary(order: dict) -> str:
    """Apresenta somente dados autorizados, sem recalcular o total histórico."""
    items = "; ".join(f"{item['quantidade']} x {item['nome'] or 'nome não informado'}"
                      for item in order["itens"]) or "não informados"
    return (f"Na base fornecida, o pedido {order['pedido_id']} consta como {order['status']}. "
            f"Total registrado: R$ {order['total_registrado_brl']}. Itens: {items}. "
            f"Previsão de entrega: {order['previsao_entrega'] or 'não informada'} "
            "(não comprova recebimento). "
            f"Rastreamento: {order['rastreamento'] or 'não informado'}.")


class Agent:
    def __init__(self, catalog, client, max_tool_calls=3, policies=None, orders=None, scope_classifier=None):
        self.catalog = catalog
        self.client = client
        self.scope_classifier = scope_classifier
        self.last_scope = None
        self.max_tool_calls = max_tool_calls
        self.turns = []
        self.last_trace = []
        self.last_usage = []
        self.policies = policies
        self.orders = orders
        self.last_model_answer = None
        self._exchange_topic = None
        self._last_presented_product_page: tuple[dict, dict] | None = None

    def _save_turn(self, messages: list[dict]) -> None:
        """Guarda somente turnos completos, preservando chamadas e resultados."""
        self.turns = (self.turns + [messages])[-MAX_HISTORY_TURNS:]

    def _reply_next_page(self, text: str) -> str:
        """Avança somente a partir de uma consulta apresentada com sucesso."""
        if self._last_presented_product_page is None:
            return "Qual busca de produtos você quer fazer? Informe os filtros para começar."
        arguments, previous = self._last_presented_product_page
        if previous["proxima_pagina"] is None:
            return "Essa busca não tem próxima página. Você pode informar novos filtros."
        arguments = {**arguments, "pagina": previous["proxima_pagina"]}
        result = execute_tool(self.catalog, "buscar_produtos", arguments, self.policies, self.orders)
        self.last_trace.append({"ferramenta": "buscar_produtos", "argumentos": arguments,
                                "resultado": result, "origem": "aplicacao"})
        if "erro" in result:
            return result["erro"]
        answer = _product_page_answer(result)
        self._save_turn([{"role": "user", "content": text}, {"role": "assistant", "content": answer}])
        self._last_presented_product_page = (arguments, result)
        return answer

    def _apply_response_guards(self, answer: str, text: str, topic: str | None) -> str:
        """Aplica proteções antes de apresentar e guardar a resposta final."""
        for trace in self.last_trace:
            if trace["ferramenta"] == "consultar_politicas":
                contact = trace["resultado"].get("decisoes_confirmadas", {}).get("whatsapp")
                if contact:
                    answer = re.sub(r"\(?67\)?\s*3321[-\s]?4500", lambda _: contact, answer)
        # Não depender da redação do LLM para autorizar acesso ou
        # concluir elegibilidade quando a própria base não tem os dados.
        order_results = [trace["resultado"] for trace in self.last_trace
                         if trace["ferramenta"] == "consultar_pedido"]
        policy_sections = [section for trace in self.last_trace
                           if trace["ferramenta"] == "consultar_politicas"
                           for section in trace["resultado"].get("secoes", [])]
        exchange_sections = any(section["id"] == "4" or section["id"].startswith("4.") for section in policy_sections)
        denied = next((result for result in order_results if result.get("encontrado") is False), None)
        owned = next((result for result in order_results if result.get("encontrado") is True), None)
        products = [product for trace in self.last_trace
                    if trace["ferramenta"] == "buscar_produtos"
                    for product in trace["resultado"].get("produtos", [])]
        if denied is not None:
            answer = denied["mensagem"]
        # Garantia recupera 4.2 como dependência; isso, sozinho,
        # não indica intenção de trocar ou devolver.
        elif exchange_sections and (topic or self._exchange_topic):
            self._exchange_topic = topic or self._exchange_topic or "arrependimento em compras online"
            answer = _informational_policy_answer(policy_sections)
            if products:
                summaries = [_product_summary(p) for p in products]
                answer = "Na base fornecida:\n" + "\n".join(summaries) + "\n\n" + answer
                for trace in self.last_trace:
                    result = trace["resultado"]
                    if trace["ferramenta"] == "buscar_produtos" and result.get("limitado"):
                        answer += f"\nPágina {result['pagina']} de {result['total_paginas']}."
                        if result["proxima_pagina"] is not None:
                            answer += " Digite 'continuar' para ver mais opções ou faça outra pergunta."
            if owned is not None:
                answer = _order_summary(owned) + "\n\n" + answer
        elif owned is not None and self._exchange_topic:
            answer = (_order_summary(owned) + " "
                      "Esta consulta não inicia uma troca ou devolução. "
                      "Para solicitar atendimento sobre esse caso, fale diretamente com a loja.")
        elif (len(products) == 1 and not products[0]["disponivel_para_compra"]
              and re.search(r"disponiv|estoque", _normalize(text))
              and not re.search(r"preco|custa|valor|quanto|promoc", _normalize(text))):
            answer = (f"O {products[0]['nome']} está {products[0]['disponibilidade']} na base fornecida. "
                      "Quer que eu consulte modelos parecidos? O que você mais gostou nele?")
        elif all(t["ferramenta"] == "buscar_produtos" for t in self.last_trace) and any(
                 t["ferramenta"] == "buscar_produtos" and (t["resultado"].get("limitado")
                                                         or t["resultado"].get("indisponiveis"))
                 for t in self.last_trace):
            answer = "\n\n".join(_product_page_answer(t["resultado"]) for t in self.last_trace
                                    if t["ferramenta"] == "buscar_produtos")
        return answer

    def _reply_exchange_policy(self, text, topic):
        result = execute_tool(self.catalog, "consultar_politicas", {"pergunta": topic}, self.policies, self.orders)
        self.last_trace.append({"ferramenta": "consultar_politicas", "argumentos": {"pergunta": topic},
                                "resultado": result, "origem": "aplicacao"})
        answer = _informational_policy_answer(result.get("secoes", []))
        self._exchange_topic = topic
        self._save_turn([{"role": "user", "content": text},
                         {"role": "assistant", "content": answer}])
        return answer

    def reply(self, text):
        self.last_trace = []
        self.last_usage = []
        self.last_model_answer = None
        self.last_scope = None
        if not text.strip():
            return "Digite uma pergunta sobre os instrumentos."
        if len(text) > 2000:
            return "Sua mensagem é muito longa. Use até 2.000 caracteres."
        try:
            classifier = self.scope_classifier or classify_scope
            self.last_scope = classifier(self.client, text, self.turns)
            if self.last_scope.get("uso"):
                self.last_usage.append({**self.last_scope["uso"], "fase": "escopo"})
        except OllamaError as exc:
            self.last_scope = {"erro": str(exc)}
            return str(exc)
        if self.last_scope["escopo"] == "fora":
            self._save_turn([{"role": "user", "content": text},
                             {"role": "assistant", "content": OUT_OF_SCOPE_ANSWER}])
            return OUT_OF_SCOPE_ANSWER
        if re.fullmatch(r"(?:continuar|(?:mostre (?:a )?|quero (?:a )?)?proxima pagina)[.!?]?", _normalize(text).strip()):
            return self._reply_next_page(text)
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
            else:
                answer = "Não consegui confirmar essa informação no manual agora. Você pode tentar novamente daqui a pouco."
            self._save_turn([{"role": "user", "content": text},
                             {"role": "assistant", "content": answer}])
            return answer
        topic = _exchange_policy_topic(text)
        normalized = _normalize(text)
        order_lookup = bool(re.search(r"status|rastrei|rastreamento|consult(?:e|ar).*pedido", normalized))
        other_lookup = bool(re.search(r"preco|custa|estoque|disponiv|horario|frete|parcel|pix|vendem|comprar|escolher", normalized))
        if topic and not order_lookup and not other_lookup:
            return self._reply_exchange_policy(text, topic)
        if topic:
            self._exchange_topic = topic
        elif self._exchange_topic and re.search(
            r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|recebi|recebido|embalagem|sem uso|manuais|presencial|online|iniciar|proceder|abrir|solicitar", normalized
        ) and not order_lookup and not other_lookup:
            # Dados fornecidos espontaneamente não viram uma coleta para abertura
            # de processo ou uma aprovação calculada pelo modelo.
            return self._reply_exchange_policy(text, self._exchange_topic)
        elif other_lookup:
            self._exchange_topic = None
        # Mantém turnos completos para não separar chamadas de seus resultados.
        history = []
        for turn in reversed(self.turns[-MAX_HISTORY_TURNS:]):
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
                    answer = self._apply_response_guards(answer, text, topic)
                    current.append({**message, "content": answer})
                    self._save_turn(current)
                    # Só confirma navegação depois de concluir o turno. Em buscas
                    # conjuntas, continuar se refere à última lista paginada.
                    presented = [t for t in self.last_trace if t["ferramenta"] == "buscar_produtos"
                                 and "erro" not in t["resultado"]]
                    denied = any(t["ferramenta"] == "consultar_pedido" and
                                 t["resultado"].get("encontrado") is False for t in self.last_trace)
                    if presented and not denied:
                        page = next((t for t in reversed(presented) if t["resultado"].get("limitado")), presented[-1])
                        self._last_presented_product_page = (dict(page["argumentos"]), page["resultado"])
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
