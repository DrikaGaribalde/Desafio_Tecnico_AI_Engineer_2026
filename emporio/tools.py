"""Contrato e execução das ferramentas autorizadas."""

from decimal import Decimal, InvalidOperation

from emporio.catalog import Catalog


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
}}]


def execute_tool(catalog: Catalog, name: str, arguments: dict) -> dict:
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
    if "preco_maximo" in arguments:
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
    return {"fonte": "CSV estático do desafio", "total": len(products),
            "limitado": len(products) > 10, "produtos": items}
