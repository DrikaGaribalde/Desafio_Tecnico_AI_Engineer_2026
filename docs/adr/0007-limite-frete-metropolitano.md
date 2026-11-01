# ADR 0007 — Limite inclusivo do frete metropolitano

- **Status:** aceita e implementada na consulta às políticas.
- **Data:** 01/11/2026.

## Contexto e decisão

A seção 5.1 prevê frete grátis acima de R$ 500 e taxa de R$ 35 abaixo desse valor,
sem esclarecer a igualdade. O autor confirmou que **pedidos a partir de R$ 500,
inclusive, têm frete grátis na região metropolitana de Campo Grande**. Portanto:

- Total maior ou igual a R$ 500: frete grátis.
- Total menor que R$ 500: taxa de R$ 35.

Essa decisão não altera as regras para outras cidades. É necessário confirmar
o destino antes de aplicar a condição a uma compra específica.

## Implementação e consequências

`consultar_politicas` retorna o limite decimal textual `500.00`, sua inclusão,
a taxa `35.00`, região e origem da decisão em `decisoes_confirmadas`.
O modelo deve priorizar essa escolha diante da lacuna do texto literal.

O PDF e sua extração permanecem preservados. Os registros anteriores que relatam
a ambiguidade são evidências históricas, anteriores à confirmação do autor.
Não foi criado um cotador ou uma função de cálculo de frete nesta alteração;
a decisão está aplicada à consulta das regras. Uma futura função deve comparar
valores com `Decimal` e usar `>= Decimal("500.00")`, respeitando a região.

A alternativa de manter a igualdade pendente foi substituída pela decisão explícita
do autor. Não há integração de transportadora, cálculo por CEP ou alteração de pedidos.
