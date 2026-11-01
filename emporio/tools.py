"""Contrato e execução das ferramentas autorizadas."""

from decimal import Decimal, InvalidOperation
import re

from emporio.catalog import Catalog
from emporio.policies import PolicyDataError, PolicyStore


TOOLS = [{"type": "function", "function": {
    "name": "buscar_produtos",
    "description": (
        "Consulta produtos na base estática por termos do nome, categoria e preço. "
        "Sem filtros lista o catálogo. Inclui indisponíveis por padrão para distinguir "
        "sem estoque, descontinuados e lançamentos. Retorna até 10 itens, ordenados por preço."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "nome": {"type": "string", "description": "Termos do produto, sem frases ou preço."},
            "categoria": {"type": "string", "description": "Nome da categoria, por exemplo Violões ou Ukuleles."},
            "preco_maximo": {"type": "string", "description": "Valor decimal em reais com ponto, sem símbolo ou milhar, por exemplo 1000.00."},
            "disponibilidade": {"type": "string", "enum": ["todas", "disponiveis"],
                                "description": "Use todas ao consultar um produto específico; disponiveis apenas para listar opções para compra."},
        },
        "additionalProperties": False,
    },
}}, {"type": "function", "function": {
    "name": "consultar_politicas",
    "description": "Busca seções do manual com condições, exceções e referências. Use para horários, pagamentos, parcelamento, frete, trocas, devoluções, garantia e acumular promoções com PIX. Não consulta preços de produtos.",
    "parameters": {"type": "object", "properties": {
        "pergunta": {"type": "string", "description": "Pergunta completa e específica sobre a política."}},
        "required": ["pergunta"], "additionalProperties": False},
}}, {"type": "function", "function": {
    "name": "consultar_pedido",
    "description": "Consulta um pedido do cliente da sessão por número OU código de rastreio. Informe somente um identificador. Somente leitura, sem consulta à transportadora; não aceita identidade do cliente.",
    "parameters": {"type": "object", "properties": {
        "pedido_id": {"type": "string", "pattern": "^[0-9]{1,12}$", "description": "Número do pedido, apenas dígitos. Omita se usar rastreio."},
        "codigo_rastreio": {"type": "string", "description": "Código alfanumérico recebido do cliente. Omita pedido_id; não deduza o número do pedido."}},
        "additionalProperties": False},
}}]


def execute_tool(catalog: Catalog, name: str, arguments: dict, policies=None, orders=None) -> dict:
    if name == "consultar_pedido":
        if not isinstance(arguments, dict) or set(arguments) - {"pedido_id", "codigo_rastreio"}:
            return {"erro": "Informe apenas pedido_id ou codigo_rastreio. A identidade é definida pela aplicação."}
        arguments = {key: value for key, value in arguments.items() if value != ""}
        if len(arguments) != 1:
            return {"erro": "Informe somente um identificador: pedido_id ou codigo_rastreio."}
        if "codigo_rastreio" in arguments:
            code = arguments["codigo_rastreio"]
            if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9]{6,40}", code.strip()):
                return {"erro": "codigo_rastreio deve conter de 6 a 40 letras ou dígitos, sem espaços internos."}
            if orders is None:
                return {"erro": "Consulta de pedidos indisponível: sessão não configurada pela aplicação."}
            return orders.get_order_by_tracking(code)
        order_id = arguments["pedido_id"]
        if isinstance(order_id, str) and re.fullmatch(r"[0-9]{1,12}", order_id):
            order_id = int(order_id)
        if type(order_id) is not int or not 0 < order_id < 10**12:
            return {"erro": "pedido_id deve ser um inteiro positivo ou texto de até 12 dígitos."}
        if orders is None:
            return {"erro": "Consulta de pedidos indisponível: sessão não configurada pela aplicação."}
        return orders.get_order(order_id)
    if name == "consultar_politicas":
        if (not isinstance(arguments, dict) or set(arguments) != {"pergunta"}
                or not isinstance(arguments["pergunta"], str)
                or not 1 <= len(arguments["pergunta"].strip()) <= 500):
            return {"erro": "Informe apenas pergunta, como texto de 1 a 500 caracteres."}
        try:
            return (policies if policies is not None else PolicyStore()).search(arguments["pergunta"])
        except PolicyDataError as exc:
            return {"erro": str(exc), "suficiente": False}
    if name != "buscar_produtos":
        return {"erro": "Ferramenta não autorizada."}
    if not isinstance(arguments, dict) or set(arguments) - {
        "nome", "categoria", "preco_maximo", "disponibilidade",
    }:
        return {"erro": "Argumentos inválidos ou desconhecidos."}
    for field in ("nome", "categoria"):
        if field in arguments and (not isinstance(arguments[field], str) or len(arguments[field]) > 200):
            return {"erro": f"{field} deve ser texto de até 200 caracteres."}
    availability = arguments.get("disponibilidade", "todas")
    if not isinstance(availability, str) or availability not in {"todas", "disponiveis"}:
        return {"erro": "disponibilidade deve ser todas ou disponiveis."}
    maximum = None
    if "preco_maximo" in arguments and arguments["preco_maximo"] != "":
        value = arguments["preco_maximo"]
        if type(value) not in (str, int, float) or len(str(value)) > 30:
            return {"erro": "preco_maximo deve ser um decimal não negativo."}
        try:
            maximum = Decimal(str(value))
            if not maximum.is_finite() or not 0 <= maximum <= Decimal("1000000000"):
                raise ValueError()
        except (InvalidOperation, ValueError):
            return {"erro": "preco_maximo deve usar ponto decimal, sem milhar, e estar entre 0 e 1000000000."}
    products = catalog.search_products(
        arguments.get("nome", "").strip(), category=arguments.get("categoria", "").strip(),
        max_price=maximum, available_only=availability == "disponiveis",
    )
    items = []
    for product in products[:10]:
        if product.status == "discontinued":
            availability = "descontinuado"
        elif product.status == "coming_soon":
            availability = "lançamento futuro"
        else:
            availability = "disponível" if product.available else "sem estoque"
        items.append({
            "nome": product.name, "categoria": product.category_name,
            "preco_original_brl": str(product.price_brl),
            "desconto_percentual": str(product.discount_percent),
            "preco_final_brl": str(product.sale_price_brl),
            "disponibilidade": availability, "disponivel_para_compra": product.available,
            "estoque": product.stock_quantity,
        })
    result = {"fonte": "CSV estático do desafio", "total": len(products),
              "limitado": len(products) > 10, "produtos": items}
    if len(products) > 10:
        result["aviso"] = f"Há {len(products)} correspondências, mas apenas as primeiras 10 estão nesta lista. Informe que há mais opções."
    return result
