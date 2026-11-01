"""Entrada: py -3.12 -m emporio."""

import argparse

from emporio.agent import Agent
from emporio.catalog import Catalog, CatalogDataError
from emporio.ollama_client import OllamaClient
from emporio.orders import OrderDataError, OrderStore, Session


def main():
    parser = argparse.ArgumentParser(description="Atendimento com identificação simulada, sem autenticação real.")
    parser.add_argument("--customer-id", type=int, default=3, help="Cliente simulado da sessão (padrão: 3).")
    args = parser.parse_args()
    if args.customer_id <= 0:
        parser.error("--customer-id deve ser positivo.")
    try:
        catalog = Catalog()
        orders = OrderStore(catalog, Session(args.customer_id))
        agent = Agent(catalog, OllamaClient(), orders=orders)
    except (CatalogDataError, OrderDataError) as exc:
        print(f"Não foi possível iniciar o atendimento: {exc}")
        return 1
    print("Empório da Música — catálogo, políticas e pedidos. Digite 'sair' para encerrar.")
    print("Fontes: CSVs estáticos e manual fornecido.")
    print(f"Cliente simulado: {args.customer_id}. Identificação local sem autenticação real.")
    try:
        while True:
            text = input("Você: ").strip()
            if text.casefold() in {"sair", "/sair", "exit"}:
                break
            if text:
                print(f"Empório: {agent.reply(text)}")
    except (EOFError, KeyboardInterrupt):
        pass
    print("Até mais!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
