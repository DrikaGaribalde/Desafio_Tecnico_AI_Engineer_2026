"""Executa conversas reais com o agente e registra mensagens e ferramentas.

Uso: py -3.12 -m scripts.evaluate_catalog --saida docs/avaliacoes/nova-execucao
"""

import argparse
import json
from pathlib import Path
from time import perf_counter

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.ollama_client import OllamaClient


SCENARIOS = [
    ("01-preco", ["Quanto custa o Takamine GD20?"]),
    ("02-orcamento", ["Quais violões disponíveis custam até R$ 1.000?"]),
    ("03-sem-estoque", ["O Giannini GF-3D está disponível?"]),
    ("04-promocao", ["O Kalani KAL-700T tem promoção ativa? Qual é o preço?"]),
    ("05-continuidade", ["Me apresente o Takamine GD20.", "Quanto custa esse que você apresentou e ele está disponível?"]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--saida", required=True, help="Pasta nova para os registros; não sobrescreve históricos.")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / args.saida
    output.mkdir(parents=True, exist_ok=False)
    for name, questions in SCENARIOS:
        agent = Agent(Catalog(), OllamaClient())
        lines = [f"# Conversa real — {name}", "",
                 "Execução real com llama3.1:latest via Ollama; dados estáticos do desafio.", ""]
        for question in questions:
            start = perf_counter()
            answer = agent.reply(question)
            elapsed = perf_counter() - start
            lines += [f"**Cliente:** {question}", "", "Ferramentas e resultados:", "", "```json",
                      json.dumps({"classificacao_escopo": agent.last_scope,
                                  "resposta_bruta_modelo": agent.last_model_answer,
                                  "ferramentas": agent.last_trace, "contexto": agent.last_usage},
                                 ensure_ascii=False, indent=2), "```", "",
                      f"**Agente:** {answer}", "", f"Tempo do turno: {elapsed:.1f} s.", ""]
            print(json.dumps({"cenario": name, "pergunta": question, "trace": agent.last_trace,
                              "classificacao_escopo": agent.last_scope,
                              "resposta_bruta_modelo": agent.last_model_answer,
                              "resposta": answer, "contexto": agent.last_usage,
                              "segundos": round(elapsed, 1)}, ensure_ascii=True), flush=True)
        (output / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
