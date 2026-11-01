"""Consultas à fotografia estática do catálogo, sem dependência de LLM."""

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import unicodedata


class CatalogDataError(ValueError):
    """A fonte não pôde ser lida ou contém dados inválidos."""


def _normalize(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(char) != "Mn"
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category_id: int
    category_name: str
    description: str
    price_brl: Decimal
    stock_quantity: int
    status: str
    discount_percent: Decimal = Decimal("0")

    @property
    def available(self) -> bool:
        return self.status == "active" and self.stock_quantity > 0

    @property
    def sale_price_brl(self) -> Decimal:
        return _money(self.price_brl * (1 - self.discount_percent / 100))

    @property
    def pix_price_brl(self) -> Decimal:
        # O desconto PIX não acumula com uma promoção ativa.
        if self.discount_percent > 0:
            return self.sale_price_brl
        return _money(self.price_brl * Decimal("0.95"))


def _read_table(directory: Path, name: str, fields: set[str]) -> list[dict]:
    candidates = sorted(directory.glob(f"*{name}.csv"))
    if len(candidates) != 1:
        raise CatalogDataError(f"Esperado um único arquivo {name}.csv em {directory}.")
    try:
        with candidates[0].open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not fields.issubset(reader.fieldnames or []):
                raise CatalogDataError(f"Colunas obrigatórias ausentes em {name}.csv.")
            rows = list(reader)
            if any(not row.get(field, "") or not row[field].strip()
                   for row in rows for field in fields):
                raise CatalogDataError(f"Dados obrigatórios ausentes em {name}.csv.")
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CatalogDataError(f"Falha ao ler {name}.csv: {exc}") from exc


class Catalog:
    """Carrega os CSVs uma vez por instância; nunca escreve nas fontes."""

    def __init__(self, data_dir: str | Path | None = None):
        directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
        categories = _read_table(directory, "categories", {"category_id", "name"})
        promotions = _read_table(directory, "promotions", {
            "promotion_id", "product_id", "discount_percent", "is_active",
        })
        products = _read_table(directory, "products", {
            "product_id", "name", "category_id", "description",
            "price_brl", "stock_quantity", "status",
        })
        try:
            category_names = {}
            for row in categories:
                key = int(row["category_id"])
                if key in category_names:
                    raise ValueError("Categoria duplicada.")
                category_names[key] = row["name"]

            discounts = {}
            promotion_ids = set()
            for row in promotions:
                promotion_id = int(row["promotion_id"])
                key = int(row["product_id"])
                discount = Decimal(row["discount_percent"])
                if promotion_id in promotion_ids:
                    raise ValueError("Promoção duplicada.")
                promotion_ids.add(promotion_id)
                if row["is_active"] not in {"0", "1"}:
                    raise ValueError("Indicador de promoção inválido.")
                if not discount.is_finite() or not 0 < discount <= 100:
                    raise ValueError("Percentual de desconto inválido.")
                if row["is_active"] == "1":
                    # Promoções não acumulam: escolhemos o maior desconto ativo.
                    discounts[key] = max(discounts.get(key, Decimal("0")), discount)

            self._products = {}
            for row in products:
                key = int(row["product_id"])
                category_id = int(row["category_id"])
                price = Decimal(row["price_brl"])
                stock = int(row["stock_quantity"])
                if key in self._products:
                    raise ValueError("Produto duplicado.")
                if not price.is_finite() or price < 0 or stock < 0:
                    raise ValueError("Preço ou estoque inválido.")
                if category_id not in category_names:
                    raise ValueError("Categoria do produto não encontrada.")
                if row["status"] not in {"active", "coming_soon", "discontinued"}:
                    raise ValueError("Status do produto desconhecido.")
                self._products[key] = Product(
                    key, row["name"], category_id, category_names[category_id],
                    row["description"], _money(price), stock, row["status"],
                    discounts.get(key, Decimal("0")),
                )
            if any(int(row["product_id"]) not in self._products for row in promotions):
                raise ValueError("Produto de promoção não encontrado.")
        except (ValueError, InvalidOperation) as exc:
            raise CatalogDataError(f"Catálogo inválido: {exc}") from exc

    def get_product(self, product_id: int) -> Product | None:
        return self._products.get(product_id)

    def search_products(
        self, query: str = "", *, category_id: int | None = None,
        max_price: Decimal | None = None, available_only: bool = True,
        category: str = "",
    ) -> list[Product]:
        """Busca no nome, categoria e descrição; teto inclusivo promocional, sem PIX."""
        if max_price is not None:
            if not isinstance(max_price, Decimal) or not max_price.is_finite() or max_price < 0:
                raise ValueError("max_price deve ser um Decimal finito não negativo.")
        terms = _normalize(query).split()
        matches = []
        for product in self._products.values():
            text = _normalize(f"{product.name} {product.category_name} {product.description}")
            if not all(term in text for term in terms):
                continue
            if category_id is not None and product.category_id != category_id:
                continue
            if category and _normalize(category) not in _normalize(product.category_name):
                continue
            if available_only and not product.available:
                continue
            if max_price is not None and product.sale_price_brl > max_price:
                continue
            matches.append(product)
        return sorted(matches, key=lambda product: (product.sale_price_brl, product.product_id))
