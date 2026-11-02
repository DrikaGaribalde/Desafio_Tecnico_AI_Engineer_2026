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
    print("\nBem-vindo ao Empório da Música!\n")
    print("Quer encontrar um instrumento, conhecer as políticas da loja")
    print("ou consultar um pedido? Vamos conversar!\n")
    print("Experimente:")
    print('  • "Quais violões estão disponíveis até R$ 1.000?"')
    print('  • "Como funciona o parcelamento?"')
    print('  • "Qual é o status do meu pedido?"\n')
    print('Digite "sair" para encerrar.\n')
    print(f"Sessão de teste · Cliente {args.customer_id} · Identificação simulada\n")
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
