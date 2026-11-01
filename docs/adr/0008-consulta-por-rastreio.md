# ADR 0008 — Consulta de pedido por código de rastreio

- **Status:** aceita e implementada.
- **Data:** 01/11/2026.

## Contexto e decisão

O rastreamento era retornado na consulta por número, mas não era aceito como chave
de busca. Para atender quem possui apenas esse código, `consultar_pedido` passa a
aceitar `pedido_id` ou `codigo_rastreio`, exigindo exatamente um identificador.
Argumentos de identidade continuam proibidos.

`OrderStore.get_order_by_tracking` pesquisa o campo registrado em `orders.csv`,
normaliza caixa e espaços externos e filtra pelo cliente da sessão antes de resolver
os itens. Aceita de 6 a 40 letras/dígitos ASCII, sem espaços internos. A validação
é sintática para esta busca local, não confirmação de um código de transportadora.

A resposta usa o mesmo método autorizado da consulta por número, preservando total
histórico, campos ausentes e distinção entre previsão e recebimento. Código ausente,
alheio ou sem correspondência única na sessão retorna a mesma mensagem genérica.

## Alternativas e limitações

Exigir sempre o número do pedido dificultava atender quem já informou o rastreio.
Inferir o número pelo modelo foi rejeitado: a relação deve vir dos CSVs. Receber dois
identificadores simultaneamente também foi rejeitado para evitar correspondências
conflitantes. Campos opcionais com string vazia são tratados como omitidos.

Não há consulta aos Correios/Jadlog, atualização de eventos ou autenticação pelo código.
Conhecer um rastreamento não dá acesso ao pedido de outra sessão. A identificação
permanece simulada conforme a ADR 0004.

## Validação

63 testes automatizados passaram. Os novos casos verificam código próprio, normalização,
proteção de pedido alheio, código ausente, argumentos inválidos ou combinados e ausência
de sessão. Execuções reais usando somente `BRAB1234567BR` estão em
[`consulta-por-rastreio.json`](../avaliacoes/pedidos/consulta-por-rastreio.json).
Os CSVs originais foram preservados.
