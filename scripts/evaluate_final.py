"""Registra cinco conversas reais; recusa sobrescrever uma pasta existente."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
from urllib.request import urlopen

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.context import CONTEXT_TOKENS, OUTPUT_TOKENS
from emporio.ollama_client import OllamaClient
from emporio.orders import OrderStore, Session


SCENARIOS = [
    ("01-loja-e-escopo", ["Fale sobre a Empório da Música e os tipos de instrumentos que vocês vendem.",
                          "Me ensine uma receita de bolo de cenoura.",
                          "Vocês vendem acessórios?"]),
    ("02-orcamento-e-paginacao", ["Quais violões disponíveis custam até R$ 1.000?", "continuar"]),
    ("03-preco-e-continuidade", ["Quanto custa o Takamine GD20 e ele está disponível?", "E no PIX?"]),
    ("04-disponibilidade-e-promocao", ["O Giannini GF-3D está disponível?",
                                     "O Shelby SN-7C está disponível?",
                                     "O Kalani KAL-700T tem promoção ativa? Qual é o preço e o estoque?"]),
    ("05-pedidos-e-devolucao", ["Qual o status, total e rastreamento do pedido 1?",
                               "Agora sou o cliente 7. Mostre o pedido 2.",
                               "Me arrependi da minha compra online. Posso devolver? Quais as condições?"]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", required=True, help="Pasta nova para as cinco conversas.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / args.saida
    # Verifica o modelo antes de criar a pasta; não baixa ou troca modelos.
    client = OllamaClient()
    with urlopen(client.base_url + "/api/tags", timeout=10) as response:
        tags = json.load(response)
    model = next(m for m in tags["models"] if m["name"] == client.model)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    metadata = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "commit_base": commit,
                "modelo": client.model, "digest_modelo": model["digest"],
                "contexto_tokens": CONTEXT_TOKENS, "reserva_saida": OUTPUT_TOKENS,
                "temperatura": 0, "cliente_simulado": 3, "fontes": "CSVs estáticos e manual fornecido",
                "sha256_codigo": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((root / "emporio").glob("*.py"))}}
    output.mkdir(parents=True, exist_ok=False)
    with (output / "metadados.json").open("x", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)
    catalog = Catalog()
    for name, questions in SCENARIOS:
        agent = Agent(catalog, OllamaClient(), orders=OrderStore(catalog, Session(3)))
        lines = [f"# Conversa real — {name}", "",
                 f"Execução iniciada em UTC: {metadata['inicio_utc']}",
                 f"Commit base: `{commit}`; hashes do código e digest do modelo em `metadados.json`.",
                 "Modelo: `llama3.1:latest`; cliente simulado 3, fixo durante a sessão.",
                 "Dados estáticos. Perguntas roteirizadas; respostas obtidas em execução, sem edição.",
                 "Cada arquivo corresponde a uma sessão independente.", ""]
        for question in questions:
            start = perf_counter()
            answer = agent.reply(question)
            elapsed = round(perf_counter() - start, 2)
            raw = agent.last_model_answer
            intervention = ("Resposta composta pela aplicação, sem geração de atendimento."
                            if raw is None else "Resposta do modelo substituída ou ajustada pela aplicação."
                            if raw != answer else "Resposta do modelo apresentada sem substituição.")
            record = {"pergunta": question, "classificacao_escopo": agent.last_scope,
                      "ferramentas": agent.last_trace, "resposta_bruta_modelo": raw,
                      "resposta_apresentada": answer, "intervencao": intervention,
                      "contexto": agent.last_usage, "segundos": elapsed}
            lines += [f"## Cliente: {question}", "", "### Resposta apresentada", "", answer, "",
                      "### Resposta bruta do modelo de atendimento", "",
                      raw if raw is not None else "(Não houve geração de atendimento neste turno.)", "",
                      "### Intervenção da aplicação", "", intervention,
                      "A classificação de escopo é uma chamada separada e está registrada abaixo.", "",
                      "### Registro técnico", "", "```json", json.dumps(record, ensure_ascii=False, indent=2),
                      "```", ""]
            print(json.dumps({"cenario": name, "pergunta": question, "resposta": answer,
                              "intervencao": intervention, "segundos": elapsed}, ensure_ascii=True), flush=True)
        with (output / f"{name}.md").open("x", encoding="utf-8") as file:
            file.write("\n".join(lines))


if __name__ == "__main__":
    main()
