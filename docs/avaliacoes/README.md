# Avaliação real da primeira etapa

Execuções realizadas em 31/10/2026 com `llama3.1:latest`, ID `46e0c10c039e`,
Ollama 0.40.13, temperatura 0 e contexto de 4.096 tokens. Os dados são CSVs estáticos.
O script `py -3.12 -m scripts.evaluate_catalog` usa a mesma classe `Agent` da CLI.

## Rodadas

1. [Primeira rodada](primeira-rodada/01-preco.md): chamadas enviaram booleanos como
   strings, rejeitadas corretamente. O modelo tentou representar novas chamadas como
   texto, sem executá-las. No cenário sem estoque, usou filtro de disponíveis e não
   encontrou o item. Os cinco registros foram preservados nessa pasta.
2. [Segunda rodada](segunda-rodada/03-sem-estoque.md): contrato alterado para enum textual
   de disponibilidade e instrução para consultar todos os estados de produtos específicos.
   Os filtros funcionaram, mas a resposta ao item sem estoque foi contraditória:
   “disponível, mas não tem estoque”. Os cinco registros foram preservados.
3. [Rodada final](../conversas/01-preco.md): indicador explícito de disponibilidade para
   compra no retorno e instruções adicionais sobre os estados. Os cinco registros finais
   estão em `docs/conversas/`, sem edição das falas do modelo.

## Resultados da rodada final

| Cenário | Avaliação dos dados | Tempo por turno |
| --- | --- | --- |
| Takamine GD20 | Aprovado: busca por nome, preço R$ 2.199,00 | 5,6 s |
| Violões até R$ 1.000 | Aprovado: filtros corretos, dez opções de doze e aviso de limite | 8,4 s |
| Giannini GF-3D sem estoque | Aprovado: indisponível por falta de estoque | 5,4 s |
| Kalani KAL-700T em promoção | Aprovado: R$ 359,00, 10%, R$ 323,10 | 5,8 s |
| Continuidade sobre Takamine | Aprovado: identifica o produto pelo histórico e consulta novamente | 5,5 s e 5,6 s |

As respostas não repetiram a ressalva “na base fornecida”, apesar da instrução.
A CLI apresenta um aviso fixo de dados estáticos na abertura. A aprovação da tabela
se refere aos dados e ao fluxo pedido, não ao cumprimento de todas as instruções.
Na continuidade, o modelo usou `disponiveis` em vez de `todas`; o item estava disponível,
então isso não alterou a resposta, mas exige avaliação adicional para itens indisponíveis.

São execuções individuais após ajustes, não um benchmark ou prova de consistência.
Os 21 testes automatizados verificam funções e controles com clientes simulados;
não equivalem a testes reais de comportamento do modelo. Descontinuados e lançamentos
estão cobertos nas funções, sem avaliação conversacional completa nesta rodada.
