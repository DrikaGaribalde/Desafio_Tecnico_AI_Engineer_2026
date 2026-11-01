"""Consulta de pedidos estáticos, restrita à identidade configurada pela aplicação."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from emporio.catalog import Catalog, CatalogDataError, _money, _read_table


class OrderDataError(ValueError):
    pass


@dataclass(frozen=True)
class Session:
    """Identificação simulada; não autentica a pessoa que usa o terminal."""

    customer_id: int

    def __post_init__(self):
        if type(self.customer_id) is not int or self.customer_id <= 0:
            raise ValueError("customer_id deve ser um inteiro positivo.")


STATUS = {
    "pending": "pendente", "confirmed": "confirmado", "shipped": "enviado",
    "delivered": "entregue", "cancelled": "cancelado",
}


def _not_found():
    return {"encontrado": False,
            "mensagem": "Pedido não localizado para o cliente desta sessão. Confira o número ou código de rastreio, ou procure o atendimento da loja."}


class OrderStore:
    def __init__(self, catalog: Catalog, session: Session, data_dir: Path | None = None):
        if not isinstance(session, Session):
            raise ValueError("A aplicação deve fornecer uma Session válida.")
        self._session = session
        self._catalog = catalog
        directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
        try:
            rows = _read_table(directory, "orders", {"order_id", "customer_id", "status", "total_brl"})
            item_rows = _read_table(directory, "order_items", {"order_id", "product_id", "quantity"})
            self._orders = {}
            for row in rows:
                key, owner = int(row["order_id"]), int(row["customer_id"])
                total = Decimal(row["total_brl"])
                if key <= 0 or owner <= 0 or key in self._orders:
                    raise ValueError("Identificador inválido ou duplicado em orders.")
                if not total.is_finite() or total < 0 or row["status"] not in STATUS:
                    raise ValueError("Total ou status inválido em orders.")
                estimated = (row.get("estimated_delivery") or "").strip() or None
                if estimated is not None:
                    date.fromisoformat(estimated)
                self._orders[key] = {
                    "owner": owner, "status": STATUS[row["status"]],
                    "total": _money(total), "estimated": estimated,
                    "tracking": (row.get("tracking_code") or "").strip() or None,
                }
            self._items = {}
            for row in item_rows:
                key, product_id, quantity = int(row["order_id"]), int(row["product_id"]), int(row["quantity"])
                if key not in self._orders or product_id <= 0 or quantity <= 0:
                    raise ValueError("Item com identificador ou quantidade inválida.")
                self._items.setdefault(key, []).append((product_id, quantity))
        except (CatalogDataError, ValueError, InvalidOperation) as exc:
            raise OrderDataError(f"Não foi possível carregar a base de pedidos: {exc}") from exc

    @property
    def session(self) -> Session:
        return self._session

    def get_order_by_tracking(self, tracking_code: str) -> dict:
        if not isinstance(tracking_code, str) or not re.fullmatch(r"[A-Za-z0-9]{6,40}", tracking_code.strip()):
            return {"erro": "codigo_rastreio deve conter de 6 a 40 letras ou dígitos, sem espaços internos."}
        normalized = tracking_code.strip().upper()
        matches = [order_id for order_id, order in self._orders.items()
                   if order["owner"] == self._session.customer_id
                   and order["tracking"] is not None and order["tracking"].upper() == normalized]
        if len(matches) != 1:
            # Código alheio, ausente ou ambíguo não revela dados de outros clientes.
            return _not_found()
        return self.get_order(matches[0])

    def get_order(self, order_id: int) -> dict:
        if type(order_id) is not int or order_id <= 0:
            return {"erro": "pedido_id deve ser um inteiro positivo."}
        order = self._orders.get(order_id)
        # Autoriza antes de relacionar itens/produtos e de montar qualquer resposta.
        if order is None or order["owner"] != self._session.customer_id:
            return _not_found()
        items = []
        for product_id, quantity in self._items.get(order_id, []):
            product = self._catalog.get_product(product_id)
            items.append({"produto_id": product_id,
                          "nome": product.name if product else None, "quantidade": quantity})
        return {
            "encontrado": True, "fonte": "CSVs estáticos do desafio", "pedido_id": order_id,
            "itens": items, "status": order["status"], "total_registrado_brl": str(order["total"]),
            "previsao_entrega": order["estimated"], "rastreamento": order["tracking"],
            "informacoes_ausentes": ["data efetiva de recebimento", "canal da compra", "condições do produto"],
            "observacao": "Somente consulta. Previsão não comprova recebimento. Total histórico não recalculado. Valores nulos significam não informado.",
        }
