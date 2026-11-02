# Disponibilidade e produto não encontrado — 02/11/2026

Execução real pelo `Agent` atual com `llama3.1:latest`, ID `46e0c10c039e`.
Cada pergunta foi enviada em uma sessão independente. Nenhum registro anterior
foi sobrescrito.

## Correção

Se `buscar_produtos` não encontrar disponíveis e houver filtro `nome`, a aplicação
consulta novamente os CSVs sem restringir disponibilidade. Categoria e preço máximo
são preservados. A lista para compra (`produtos`, `total` e paginação) permanece
filtrada; `indisponiveis` e `total_indisponiveis` trazem diagnóstico separado.
Até cinco indisponíveis são apresentados, com indicação de resultado parcial quando
necessário. Não há promessa de reposição nem disponibilidade presumida.

Em consultas apenas de catálogo, esse diagnóstico é apresentado pela aplicação,
inclusive junto a outras buscas de produtos. O atendimento de políticas em perguntas
mistas continua sujeito às ferramentas e à redação do modelo.

## 1. Produto sem estoque

**Cliente:** O Giannini GF-3D está disponível?

Classificação real: `loja`.
Ferramenta solicitada pelo modelo:

```json
{"nome":"Giannini GF-3D","disponibilidade":"disponiveis","pagina":"1"}
```

Retorno: `total=0`, `produtos=[]`, `total_indisponiveis=1`;
diagnóstico: Giannini GF-3D Dreadnought Sunburst, `sem estoque`,
`disponivel_para_compra=false`.

**Resposta apresentada pela aplicação:**

> Não há produtos disponíveis para esses filtros. Na base fornecida:
> - Giannini GF-3D Dreadnought Sunburst: sem estoque; indisponível para compra.

A resposta bruta do modelo reconheceu falta de estoque, mas acrescentou a oferta
de verificar se seria lançado no futuro. Essa redação foi substituída pelo diagnóstico.

## 2. Descontinuado

**Cliente:** O Shelby SN-7C está disponível?

Classificação real: `loja`.
Ferramenta: `buscar_produtos` com
`{"nome":"Shelby SN-7C","disponibilidade":"todas","pagina":"1"}`.
Retorno: um produto, `descontinuado`, estoque zero, compra indisponível.

**Resposta bruta do modelo:**

> O Shelby SN-7C está descontinuado e não está disponível para compra.

**Resposta apresentada pela aplicação:**

> O Shelby SN-7C 7 Cordas Nylon Natural está descontinuado na base fornecida. Quer que eu consulte modelos parecidos? O que você mais gostou nele?

Neste cenário real o modelo escolheu `todas`. A mesma consulta incorretamente
restrita a `disponiveis` é coberta pelos testes locais de diagnóstico.

## 3. Nome sem correspondência

**Cliente:** Vocês têm o violão Modelo XYZ-Inexistente?

Classificação real: `loja`.
Ferramenta: `buscar_produtos` com
`{"nome":"Modelo XYZ-Inexistente","categoria":"Violões","disponibilidade":"todas","pagina":"1"}`.
Retorno vazio, sem diagnóstico de indisponíveis.

**Trecho inicial da resposta real, sem substituição pela aplicação:**

> Desculpe, mas não encontramos o violão Modelo XYZ-Inexistente em nossa base de produtos.

O modelo pediu mais detalhes e ofereceu buscar alternativas. Ausência de correspondência
na base não prova inexistência no mercado ou fora dos filtros aplicados.

## Testes

95 testes passaram. Os novos casos verificam GF-3D, SN-7C e lançamento futuro com
filtro de disponíveis, preservação de categoria/orçamento, nome sem correspondência,
listas de compra, bloqueio de afirmação incorreta do modelo e preservação de outra
consulta de produto no mesmo turno. Testes simulados não comprovam consistência
do modelo em todas as paráfrases.
