"""Entrada: py -3.12 -m emporio."""

from emporio.agent import Agent
from emporio.catalog import Catalog, CatalogDataError
from emporio.ollama_client import OllamaClient


def main():
    try:
        agent = Agent(Catalog(), OllamaClient())
    except CatalogDataError as exc:
        print(f"Não foi possível carregar o catálogo: {exc}")
        return 1
    print("Empório da Música — consultas de catálogo. Digite 'sair' para encerrar.")
    print("Fonte: CSVs estáticos do desafio. Pedidos e políticas ainda não disponíveis.")
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
