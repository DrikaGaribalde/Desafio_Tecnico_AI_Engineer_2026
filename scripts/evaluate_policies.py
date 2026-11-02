"""Conversas reais e métricas de contexto: py -3.12 -m scripts.evaluate_policies."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.context import CONTEXT_TOKENS
from emporio.ollama_client import OllamaClient
from emporio.policies import PolicyStore


SCENARIOS = [
    ("01-sabado", ["Qual é o horário de funcionamento no sábado?"]),
    ("02-arrependimento", ["Comprei online e me arrependi. Posso devolver? Quais são as condições?"]),
    ("03-parcelamento", ["Como funciona o parcelamento? Quais são os valores mínimos das parcelas?"]),
    ("04-pix-promocao", ["Posso acumular uma promoção com o desconto de pagamento no PIX?"]),
    ("05-frete-500", ["Meu pedido é de exatamente R$ 500 para Campo Grande. O frete é grátis ou pago?"]),
    ("06-produto-e-politica", ["Quanto custa o Kalani KAL-700T e posso acumular a promoção dele com o desconto PIX?",
                              "E se eu comprar esse produto online e me arrepender, posso devolver?"]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rodada", default="rodada-01")
    args = parser.parse_args()
    if not args.rodada.replace("-", "").isalnum():
        parser.error("Use apenas letras, números e hífen em --rodada.")
    output = Path(__file__).resolve().parents[1] / "docs" / "avaliacoes" / "politicas" / args.rodada
    output.mkdir(parents=True, exist_ok=False)
    records = []
    store = PolicyStore()
    for name, questions in SCENARIOS:
        agent = Agent(Catalog(), OllamaClient(), policies=store)
        lines = [f"# Conversa real — {name}", "", f"Execução UTC: {datetime.now(timezone.utc).isoformat()}",
                 f"Modelo: llama3.1:latest; contexto: {CONTEXT_TOKENS}; temperatura: 0; saída máxima: 768.", ""]
        for question in questions:
            start = perf_counter()
            answer = agent.reply(question)
            elapsed = round(perf_counter() - start, 2)
            record = {"cenario": name, "pergunta": question, "ferramentas": agent.last_trace,
                      "classificacao_escopo": agent.last_scope,
                      "resposta": answer, "resposta_bruta_modelo": agent.last_model_answer,
                      "contexto": agent.last_usage, "segundos": elapsed}
            records.append(record)
            lines += [f"**Cliente:** {question}", "", "```json",
                      json.dumps({"ferramentas": agent.last_trace, "contexto": agent.last_usage},
                                 ensure_ascii=False, indent=2), "```", "", f"**Agente:** {answer}",
                      "", "A aplicação acrescenta o rodapé de fontes; resposta bruta do modelo:", "",
                      agent.last_model_answer or "(sem resposta do modelo)", "", f"Tempo: {elapsed} s.", ""]
            print(json.dumps({**record, "ferramentas": [
                {"nome": t["ferramenta"], "argumentos": t["argumentos"],
                 "secoes": [s["id"] for s in t["resultado"].get("secoes", [])],
                 "erro": t["resultado"].get("erro")}
                for t in agent.last_trace]}, ensure_ascii=True), flush=True)
        (output / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")
        (output / "resultados.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
