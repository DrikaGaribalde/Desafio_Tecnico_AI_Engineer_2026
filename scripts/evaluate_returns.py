"""Reproduz a conversa de devolução; distingue aplicação e modelo real."""

import json
from pathlib import Path
from time import perf_counter

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.ollama_client import OllamaClient
from emporio.orders import OrderStore, Session


def main():
    catalog = Catalog()
    agent = Agent(catalog, OllamaClient(), orders=OrderStore(catalog, Session(3)))
    records = []
    for question in (
        "me arrependi da minha compra posso devolver o meu pedido?",
        "10/10/26 e se encontra na embalagem original",
        "BRAB1234567BR",
    ):
        start = perf_counter()
        answer = agent.reply(question)
        records.append({"pergunta": question, "resposta": answer,
                        "ferramentas": agent.last_trace,
                        "resposta_bruta_modelo": agent.last_model_answer,
                        "contexto": agent.last_usage,
                        "segundos": round(perf_counter() - start, 2)})
        print(json.dumps(records[-1], ensure_ascii=True), flush=True)
    output = Path("docs/avaliacoes/pedidos/devolucao-informativa.json")
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
