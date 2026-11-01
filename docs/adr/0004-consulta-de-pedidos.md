# ADR 0004 — Pedidos com identidade de sessão simulada

- **Status:** aceita e implementada.
- **Data:** 31/10/2026.
- Complementa as ADRs [0001](0001-arquitetura-inicial.md), [0002](0002-catalogo-e-ferramentas.md) e [0003](0003-consulta-as-politicas.md).

## Contexto

O protótipo já consulta produtos e políticas. A consulta de pedidos precisa relacionar
`orders.csv`, `order_items.csv` e produtos, sem permitir acesso a pedidos alheios ou
alteração de identidade pelo modelo. As fontes são estáticas e não oferecem data
efetiva de recebimento, canal da compra ou estado do produto. O prazo de dois dias
favorece reutilizar o catálogo, o executor de ferramentas e a CLI existentes.

## Decisões

### Identidade sob controle da aplicação

Criar `Session`, um objeto imutável com `customer_id`, e vincular um `OrderStore`
a essa sessão. A CLI configura o cliente antes da conversa com `--customer-id`,
usando 3 como padrão explícito na abertura. Um novo processo pode usar outro cliente.
Não há comando ou ferramenta para trocar a identidade durante a conversa.

**Essa identificação é simulada, não autenticação real.** Quem pode executar a CLI
pode escolher qualquer ID, ler ou editar os arquivos locais. A autorização demonstra
restrição de acesso dentro da sessão; não torna o protótipo adequado a dados reais
de clientes ou exposição pública. O cadastro `customers.csv` não é carregado.

### Autorização em Python

Expor `consultar_pedido(pedido_id)`, sem argumento de identidade. A aplicação rejeita
`customer_id`, `cliente_id` e qualquer argumento adicional. `OrderStore.get_order`
compara o proprietário armazenado com o cliente da sessão **antes** de relacionar
itens e produtos ou montar a resposta. Sem sessão configurada, a ferramenta recusa.

Pedido inexistente e pedido alheio retornam o mesmo conteúdo: “Pedido não localizado
para o cliente desta sessão”. Não devolver status, itens, total, proprietário ou
rastreamento, nem confirmar a existência de um pedido de outro cliente. A aplicação
também padroniza a resposta final de negação, evitando que a redação do modelo acrescente
afirmações sem respaldo. Isso não pretende eliminar canais de tempo de resposta.

O modelo instalado enviou números de pedido como strings, mesmo com schema inteiro.
O contrato passou a declarar texto de dígitos. A aplicação aceita inteiro positivo
ou string ASCII de 1 a 12 dígitos e normaliza apenas o número do pedido. Rejeita
booleanos, floats, negativos, expressões, notação científica e valores fora do limite.
Essa conversão não envolve a identidade, que permanece fixa.

### Resposta mínima e somente leitura

Retornar identificador do pedido, nomes/IDs e quantidades dos itens, status,
total registrado, previsão e rastreamento. Não retornar cliente, contatos,
observações internas ou forma de pagamento. O relacionamento com o catálogo usa
apenas o nome do produto, sem consultar seu preço para calcular o pedido.

Ler o total de `orders.total_brl` com `Decimal` e formatar para centavos. Não somar
quantidades pelos preços atuais. O pedido 3 é uma evidência concreta: total registrado
R$ 3.450,00, embora duas unidades do produto 130 aos preços atuais somem R$ 3.498,00.

Previsão e rastreamento ausentes retornam `null`. Nome de produto não encontrado
retorna `null`, preservando ID e quantidade; itens ausentes ficam em lista vazia.
Não inventar dados. A ferramenta informa as lacunas para avaliar devolução e que
previsão não comprova recebimento. Nenhuma função grava nos CSVs ou executa cancelamento,
troca, devolução, reembolso ou contato externo.

### Devolução: não confiar somente no prompt

O modelo consultou pedido e manual, mas respondeu “sim, pode devolver” sem perguntar
os dados ausentes. Por isso, quando o turno consulta um pedido autorizado e a seção
4.1 de arrependimento, a aplicação substitui a redação final por perguntas de canal
da compra, data efetiva de recebimento e condições do produto, acompanhadas do texto
integral da seção e sua referência. Não calcula elegibilidade ou inicia uma devolução.

O histórico guarda a resposta segura apresentada, evitando propagar a aprovação
inadequada do modelo. A resposta bruta permanece nos registros de avaliação, separada
da resposta final. Essa proteção depende das ferramentas efetivamente chamadas;
não é um classificador geral de todas as afirmações do modelo.

Não há estado estruturado para validar respostas posteriores do cliente nem motor
automático de elegibilidade. A proteção é conservadora e pode repetir perguntas
mesmo se o usuário já informou dados em texto. Isso fica como limitação, em vez de
aprovar ou negar com base em uma previsão ou dado ausente.

### Contexto e preservação do catálogo

A terceira ferramenta e as instruções de privacidade aumentaram o orçamento conservador.
Uma tentativa de reduzir descrições prejudicou chamadas de produtos: o modelo preencheu
filtros incorretos. Restaurar as descrições anteriores de produtos e políticas e
ampliar `num_ctx` para **12.288 tokens**, mantendo saída máxima de 768, temperatura
zero, três ferramentas por turno e demais controles da ADR 0003.

Ollama informou contexto 12.288 e execução 100% GPU, aproximadamente 6,4 GB para
o modelo carregado. Isso foi verificado neste hardware; outras máquinas podem ter
desempenho diferente. O limite de contexto continua sujeito à estimativa conservadora
e remoção de turnos antigos. Não implica que o PDF inteiro foi validado no contexto.

Filtros textuais opcionais vazios de produtos são tratados como ausência de filtro,
inclusive `preco_maximo=""`; valores não vazios continuam validados. A normalização
foi testada após observar strings vazias em chamadas reais. Consultas e cálculos do
catálogo permanecem no módulo existente, sem alteração das fontes.

## Alternativas consideradas

- Identificar cliente pelo nome/ID fornecido ao modelo: rejeitado; permitiria consultar
  dados de outra pessoa por instrução de chat.
- Consultar `customers.csv` ou implementar login: não necessário à simulação; autenticação
  real exigiria outro mecanismo e está fora do escopo desta etapa.
- Diferenciar pedido alheio e inexistente: rejeitado para não revelar sua existência.
- Recalcular total com catálogo atual: rejeitado; não há preços históricos nos itens.
- Aprovar devolução com status entregue ou previsão: rejeitado; não demonstram quando
  o recebimento ocorreu, nem o canal e as condições do produto.
- Confiar apenas nas instruções ao modelo: insuficiente nas execuções reais; autorização
  e proteção contra aprovação sem dados são responsabilidades da aplicação.

## Consequências e validação

Consultas são reproduzíveis sem infraestrutura adicional, com autorização independente
do LLM. O protótipo não oferece autenticação real, alterações comerciais, rastreamento
externo, atualização de status ou avaliação automática de devolução.

A suíte cobre autorização, tentativa de alteração de identidade, argumentos inválidos,
minimização de dados, campos ausentes, múltiplos itens, produtos ausentes, totais históricos
e bloqueio de aprovação indevida. Conversas reais, falhas preservadas e regressão de
produtos estão na [avaliação de pedidos](../avaliacoes/pedidos/README.md).

## Uso de IA

Codex implementou a consulta, testes, integração e documentação, executou conversas
reais e identificou falhas que motivaram validações e proteções. Os registros distinguem
o que o modelo gerou do que foi acrescentado ou substituído pela aplicação.
