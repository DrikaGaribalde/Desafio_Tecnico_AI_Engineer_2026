# Avaliações do agente

Esta pasta reúne execuções reais, falhas observadas e verificações feitas durante
o desenvolvimento. Os registros refletem versões diferentes do projeto; não são
um benchmark nem garantia de consistência da versão atual.

## Índice

- [Conversas da versão final registrada em 02/11/2026](../conversas/versao-final-2026-11-02/): cinco sessões com respostas brutas, respostas apresentadas e intervenções da aplicação.
- [Políticas e orçamento de contexto](politicas/README.md).
- [Pedidos, autorização e devolução](pedidos/README.md).
- [Estilo e esclarecimentos](estilo/README.md).
- [Classificação de escopo por intenção](escopo/classificacao-intencao-2026-11-02.md).
- [Produtos indisponíveis e buscas sem correspondência](produtos-indisponiveis-2026-11-02.md).
- [Conversas históricas de catálogo](catalogo-historico/).

Os testes locais e os comandos para executar o projeto estão no
[README principal](../../README.md).

## Histórico da primeira etapa — catálogo

O relato abaixo descreve a etapa de 31/10/2026. Contexto de 4.096 tokens,
listas de até dez produtos e 21 testes pertencem àquela versão; não representam
a configuração ou a cobertura atual.

Execuções realizadas em 31/10/2026 com `llama3.1:latest`, ID `46e0c10c039e`,
Ollama 0.40.13, temperatura 0 e contexto de 4.096 tokens. Os dados são CSVs estáticos.
O script `scripts.evaluate_catalog` usa a mesma classe `Agent` da CLI. Para uma nova
execução, informe `--saida` com uma pasta que ainda não exista; o script recusa sobrescrita.

### Rodadas

1. [Primeira rodada](primeira-rodada/01-preco.md): chamadas enviaram booleanos como
   strings, rejeitadas corretamente. O modelo tentou representar novas chamadas como
   texto, sem executá-las. No cenário sem estoque, usou filtro de disponíveis e não
   encontrou o item. Os cinco registros foram preservados nessa pasta.
2. [Segunda rodada](segunda-rodada/03-sem-estoque.md): contrato alterado para enum textual
   de disponibilidade e instrução para consultar todos os estados de produtos específicos.
   Os filtros funcionaram, mas a resposta ao item sem estoque foi contraditória:
   “disponível, mas não tem estoque”. Os cinco registros foram preservados.
3. [Rodada final daquela etapa](catalogo-historico/01-preco.md): indicador explícito de disponibilidade para
   compra no retorno e instruções adicionais sobre os estados. Os cinco registros finais
   estão em `docs/avaliacoes/catalogo-historico/`, sem edição das falas do modelo.
   Os [exemplos atuais](../conversas/versao-final-2026-11-02/) são de uma etapa posterior.

### Resultados da rodada final daquela etapa

| Cenário | Avaliação dos dados | Tempo por turno |
| --- | --- | --- |
| Takamine GD20 | Aprovado: busca por nome, preço R$ 2.199,00 | 5,6 s |
| Violões até R$ 1.000 | Aprovado: filtros corretos, dez opções de doze e aviso de limite | 8,4 s |
| Giannini GF-3D sem estoque | Aprovado: indisponível por falta de estoque | 5,4 s |
| Kalani KAL-700T em promoção | Aprovado: R$ 359,00, 10%, R$ 323,10 | 5,8 s |
| Continuidade sobre Takamine | Aprovado: identifica o produto pelo histórico e consulta novamente | 5,5 s e 5,6 s |

As respostas não repetiram a ressalva “na base fornecida”, apesar da instrução.
Naquela versão, a CLI apresentava um aviso fixo de dados estáticos na abertura. A aprovação da tabela
se refere aos dados e ao fluxo pedido, não ao cumprimento de todas as instruções.
Na continuidade, o modelo usou `disponiveis` em vez de `todas`; o item estava disponível,
então isso não alterou a resposta, mas exige avaliação adicional para itens indisponíveis.

São execuções individuais após ajustes, não um benchmark ou prova de consistência.
Os 21 testes automatizados daquela etapa verificavam funções e controles com clientes simulados;
não equivalem a testes reais de comportamento do modelo. Descontinuados e lançamentos
estão cobertos nas funções, sem avaliação conversacional completa nesta rodada.
