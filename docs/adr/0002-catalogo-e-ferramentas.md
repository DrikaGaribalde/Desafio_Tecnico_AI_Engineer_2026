# ADR 0002 — Catálogo e execução de ferramentas

- **Status:** aceita e implementada na primeira etapa.
- **Data:** 31/10/2026.
- Complementa a [ADR 0001](0001-arquitetura-inicial.md).

## Contexto

No prazo de dois dias, precisamos demonstrar consultas reais pelo modelo sem
mapeamentos fixos entre nomes e IDs no prompt. Pedidos e políticas ficam fora
desta etapa. O primeiro experimento isolado não avaliava busca por nome.

## Decisões

- Usar a biblioteca padrão, inclusive `urllib` para a API `/api/chat` do Ollama.
- Expor somente `buscar_produtos`, com nome, categoria, preço máximo e disponibilidade
  opcionais. Nome usa termos no nome/categoria/descrição; categoria é correspondência
  parcial no nome da categoria. As comparações ignoram caixa e acentos.
- Aceitar preço decimal textual ou numérico JSON, convertido com `Decimal(str(valor))`;
  rejeitar booleanos, valores não finitos, negativos, formatos ambíguos e valores acima
  de um bilhão de reais. Arredondamento monetário: `ROUND_HALF_UP` para centavos.
- Consultar categorias, produtos e promoções estáticos. Promoções usam `is_active`;
  o maior desconto ativo é a interpretação adotada se houver mais de um, sem soma.
- Usar disponibilidade `todas` por padrão para não esconder produtos indisponíveis.
  O contrato usa enum textual `todas`/`disponiveis`: na primeira rodada, o modelo
  enviava booleanos como strings, rejeitados pela validação. Não afrouxamos os tipos
  silenciosamente; simplificamos o contrato e mantivemos a rejeição de valores inválidos.
- Devolver estado textual e `disponivel_para_compra` calculados pela aplicação.
  `active` e estoque positivo é disponível; `active` com zero é sem estoque;
  `discontinued` é descontinuado e `coming_soon` é lançamento futuro, mesmo com estoque.
- Retornar até dez itens ordenados por preço promocional, com total e indicador de limite.
- Limitar a três execuções de ferramentas por turno, contando chamadas inválidas.
  Após o limite, encerrar sem salvar o turno parcial. Até quatro turnos completos
  são mantidos, com seleção de aproximadamente 10.000 caracteres de histórico para envio.
- Usar contexto de 4.096 tokens, temperatura zero, saída máxima de 768 tokens e
  timeout HTTP de 120 segundos por chamada. Não há retry automático.
- Manter o histórico somente em memória e não acessar os CSVs de clientes/pedidos.

## Alternativas

Um SDK HTTP ou framework de agentes adicionaria dependências sem necessidade para
este fluxo. Um filtro booleano de disponibilidade foi testado e substituído pela
enum textual após falhas reais. Renderização determinística de respostas poderia
reduzir contradições; nesta etapa a redação final ainda é responsabilidade do modelo.

## Consequências e limites

A validação controla a execução, não garante fidelidade de todas as frases geradas.
Na segunda rodada o modelo disse “disponível, mas não tem estoque”; adicionamos
o indicador de compra e instruções específicas. A rodada final respondeu corretamente,
mas isso não comprova consistência. Registros das falhas foram preservados.

O modelo nem sempre inclui a ressalva da fonte estática e chegou a usar o filtro de
disponíveis em uma continuidade sobre produto específico, apesar da orientação de
usar todos os estados. Nesse caso o produto estava disponível e o resultado foi correto.
Ainda é necessário avaliar casos de continuidade com itens indisponíveis.

A limitação de caracteres não mede tokens nem garante que todas as mensagens caibam
no contexto. Não há paginação ou busca semântica, persistência, pedidos ou políticas.
A inclusão do PDF completo no contexto permanece não validada.

## Validação

21 testes automatizados aprovados e cinco conversas reais (seis turnos), com ferramentas
e retornos registrados. A CLI foi executada com pergunta real e `sair`. A falha de conexão
foi verificada apontando o cliente para uma porta local sem serviço, sem parar o Ollama.
Na execução avaliada, `ollama ps` mostrou modelo 100% GPU e contexto de 4.096 tokens.
