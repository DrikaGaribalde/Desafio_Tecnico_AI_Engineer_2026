"""Busca textual por seções integrais derivadas do manual fornecido."""

import hashlib
import json
from pathlib import Path
import re

from emporio.catalog import _normalize


class PolicyDataError(ValueError):
    pass


# Termos de recuperação, não respostas prontas. Textos vêm do PDF.
TOPICS = {
    "2": ("horario", "sabado", "domingo", "feriado", "abre", "fecha", "expediente"),
    "3": ("pagamento", "pagar", "pix", "boleto", "debito", "credito", "cartao"),
    "3.1": ("parcel", "12x", "6x", "3x", "juros", "prestac"),
    "4.1": ("arrepend", "devol", "reembols", "desist", "online"),
    "4.2": ("defeito", "quebrad"),
    "4.3": ("preferencia", "trocar", "troca", "cor", "tamanho"),
    "4.4": ("personaliz", "venda final", "boquilha", "regulagem"),
    "5.1": ("frete", "entrega", "campo grande", "motoboy", "500"),
    "5.2": ("frete", "entrega", "cidade", "cep", "pac", "sedex", "jadlog", "transport"),
    "5.3": ("rastre", "codigo"),
    "6.2": ("promoc", "desconto", "acumul", "cumul", "pix", "oferta"),
    "8.1": ("garantia",), "8.2": ("fabricante", "certificado", "garantia"),
    "8.3": ("garantia", "mau uso", "queda", "desgaste"),
    "9": ("privacidade", "dados pessoais", "exclusao", "lgpd"),
}

DEPENDENCIES = {
    "3": ("3.1", "6.2"), "3.1": ("3",),
    "4.2": ("4.4", "8.1", "8.2", "8.3"),
    "4.3": ("4.4",), "8.1": ("8.2", "8.3", "4.2"),
    "8.2": ("8.1", "8.3", "4.2"), "8.3": ("8.1", "8.2", "4.2"),
}

NOTES = {
    "3.1": "A tabela 3 indica parcela mínima geral de R$ 100, mas 3.1 detalha outras faixas. Há divergência; não escolher uma regra silenciosamente. A expressão 'exceto abaixo de R$ 50' é ambígua. Confirmar com a loja antes de concluir condições específicas.",
    "4.1": "Não concluir elegibilidade sem data efetiva de recebimento e condições do produto. Pergunte quando recebeu e se está sem uso, na embalagem original, com acessórios e manuais. Não há nesta seção exclusão por personalização ou venda final; não inventar restrições.",
    "4.4": "Esta seção trata de troca. Sua aplicação a arrependimento online não está esclarecida no texto; não negar devolução automaticamente com base nela.",
    "5.1": "O texto cobre acima e abaixo de R$ 500, mas não exatamente R$ 500. Nesse valor a regra é insuficiente: não afirmar frete grátis nem taxa de R$ 35. Solicitar confirmação à loja. Confirmar também região de destino.",
    "5.2": "Sem CEP, peso e dimensões e sem integração de cotação, não calcular frete de outras cidades nem prometer prazo específico.",
    "6.2": "Não é permitido somar desconto PIX com promoção. Combinar meios de pagamento é diferente de acumular descontos. Não oferecer alternativas de preço não calculadas pela consulta de produtos.",
    "8.1": "Preservar a diferença entre troca em 30 dias após compra (4.2) e garantia de 90 dias após recebimento (8.1). Não concluir cobertura sem os dados necessários.",
}


class PolicyStore:
    def __init__(self, data_dir: Path | None = None):
        directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
        try:
            data = json.loads((directory / "politicas_secoes.json").read_text(encoding="utf-8"))
            pdf = directory / "políticas_da_loja.pdf"
            if hashlib.sha256(pdf.read_bytes()).hexdigest() != data["sha256_pdf"]:
                raise ValueError("O PDF mudou; regenere e revise politicas_secoes.json.")
            self.sections = {section["id"]: section for section in data["secoes"]}
            if not all(section.get("texto") and section.get("paginas") for section in self.sections.values()):
                raise ValueError("Seção vazia ou sem referência.")
            self.source = data["fonte"]
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise PolicyDataError(f"Não foi possível carregar as políticas: {exc}") from exc

    def search(self, question: str, max_chars: int = 4400) -> dict:
        normalized = _normalize(question)
        words = set(re.findall(r"[a-z0-9]+", normalized)) - {
            "a", "o", "as", "os", "de", "da", "do", "e", "em", "um", "uma", "para", "que", "qual", "como", "por", "na", "no", "se", "com", "posso", "loja", "funciona", "regras", "condicoes", "sobre",
        }
        ranked = []
        for key, section in self.sections.items():
            score = sum(5 for term in TOPICS.get(key, ())
                        if re.search(r"\b" + re.escape(term) + (r"\b" if len(term) <= 3 else ""), normalized))
            title = _normalize(section["titulo"])
            score += sum(2 for word in words if len(word) > 3 and word in title)
            if score:
                ranked.append((score, key))
        if not ranked:
            return {"encontrado": False, "suficiente": False, "secoes": [],
                    "mensagem": "Não encontrei seção relevante. Peça mais detalhes; não complete com informações presumidas."}
        ranked.sort(key=lambda item: (-item[0], item[1]))
        ranked = [item for item in ranked if item[0] >= ranked[0][0] / 2]
        if ranked[0][1] == "6.2" and any(term in normalized for term in ("acumul", "cumul", "promoc")):
            # A regra de cumulatividade é autocontida; não trazer a tabela de
            # parcelamento, que poderia confundir descontos e meios de pagamento.
            ranked = [item for item in ranked if item[1] not in {"3", "3.1", "6.1"}]
        if "campo grande" in normalized:
            ranked = [item for item in ranked if item[1] != "5.2"]
        selected = []
        # Até dois assuntos principais. Dependências preservam condições e exceções.
        for _, key in ranked[:2]:
            for related in (key,) + DEPENDENCIES.get(key, ()):
                if related not in selected:
                    selected.append(related)
        sections = []
        for key in selected:
            section = self.sections[key]
            sections.append({"id": key, "titulo": section["titulo"],
                             "referencia": f"{self.source}, seção {key}, página(s) {', '.join(map(str, section['paginas']))}",
                             "texto": section["texto"]})
        result = {"encontrado": True, "suficiente": True, "fonte": self.source,
                  "secoes": sections,
                  "ressalvas": [NOTES[key] for key in selected if key in NOTES]}
        # Nunca corta uma regra ou omite uma dependência para caber: pede pergunta mais específica.
        if len(json.dumps(result, ensure_ascii=False)) > max_chars:
            return {"encontrado": True, "suficiente": False, "secoes": [],
                    "mensagem": "As seções completas excedem o orçamento. Peça uma pergunta mais específica; não responda sem o texto."}
        if "5.1" in selected and re.search(r"(?:exatamente\s*(?:r\$\s*)?500|500\s*(?:reais)?\s*exat)", normalized):
            result["suficiente"] = False
        return result
