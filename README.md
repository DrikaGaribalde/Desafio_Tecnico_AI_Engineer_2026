# Empório da Música — Agente de Atendimento

Protótipo de agente de atendimento por texto desenvolvido para o
Desafio Técnico AI Engineer da Artefact.

O objetivo é auxiliar clientes da loja fictícia Empório da Música,
respondendo dúvidas sobre produtos, disponibilidade, promoções,
pedidos e políticas da loja com base nos materiais fornecidos.

## Status do projeto

Em desenvolvimento. O agente completo ainda não foi implementado;
foi executado apenas um teste isolado de chamadas de ferramentas.

Foi validado o ciclo básico de chamada de ferramenta com o modelo
local llama3.1:latest via Ollama.

As consultas de catálogo e os cálculos de promoções estão implementados e
testados como funções Python. A integração com o modelo, a CLI e a consulta
às políticas ainda serão implementadas e avaliadas.

## Escopo

O agente deverá:

- Consultar produtos, preços e disponibilidade.
- Consultar promoções ativas.
- Responder perguntas sobre as políticas da loja.
- Consultar pedidos no contexto de um cliente identificado.
- Tratar perguntas fora do escopo e informações ausentes.

Os CSVs representam uma base estática fornecida pelo desafio,
sem integração com um sistema comercial em tempo real.

## Tecnologias e decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python | Requisito obrigatório do desafio |
| Modelo inicial em avaliação | llama3.1:latest | Completou o ciclo básico de ferramentas, com limitações observadas |
| Execução do modelo | Ollama local | Permite executar o modelo sem chamadas a uma API externa |
| Interface proposta | CLI | Permite priorizar o funcionamento do agente no prazo disponível |
| Histórico proposto | Em memória | Permite continuidade durante a sessão sem banco de dados |
| Dados operacionais | Funções Python sobre CSVs | Mantém consultas e cálculos explícitos e verificáveis |

A escolha do modelo ainda será avaliada nos cenários completos
de atendimento.

## Decisões de arquitetura

A arquitetura inicial confirmada utiliza Python, CLI, consultas diretas aos
CSVs, chamadas de ferramentas executadas de forma controlada pela aplicação
e histórico em memória. A escolha inicial de modelo é `llama3.1:latest` via
Ollama, sujeita à validação nos cenários completos.

A estratégia de consulta às políticas permanece pendente de validação;
não foi verificado se o PDF completo cabe no contexto configurado.

A [ADR 0001 — Arquitetura inicial](docs/adr/0001-arquitetura-inicial.md)
registra o contexto, as alternativas, os resultados dos testes e as limitações.
As referências a propostas na tabela anterior correspondem à etapa de avaliação;
CLI e histórico em memória estão agora confirmados para a arquitetura inicial.

## Arquitetura e estratégia de prompt

Será documentado após a implementação e validação.

Explicar:

- Como o modelo recebe a persona e as instruções.
- Quais ferramentas estão disponíveis.
- Como a aplicação valida e executa as chamadas.
- Como as políticas são disponibilizadas ao modelo.
- Como o histórico é mantido e limitado.

## Dados utilizados

| Arquivo | Finalidade |
|---|---|
| `desafio_tecnico_ai_eng - categories.csv` | Categorias dos instrumentos |
| `desafio_tecnico_ai_eng - products.csv` | Catálogo, preços, estoque e especificações |
| `desafio_tecnico_ai_eng - promotions.csv` | Promoções e descontos |
| `desafio_tecnico_ai_eng - customers.csv` | Dados dos clientes |
| `desafio_tecnico_ai_eng - orders.csv` | Dados e status dos pedidos |
| `desafio_tecnico_ai_eng - order_items.csv` | Produtos e quantidades dos pedidos |
| políticas_da_loja.pdf | Regras e procedimentos de atendimento |

Todos esses arquivos estão na pasta `data/`.

## Pré-requisitos

Ambiente verificado em 31/10/2026: Python **3.12.9** e Ollama **0.40.13**.
No ambiente avaliado, use `py -3.12`.

Modelo utilizado: llama3.1:latest.

Identificador do modelo testado: **`46e0c10c039e`** (8B, quantização Q4_K_M).
A tag `latest` pode apontar para outro artefato em uma instalação futura.

## Configuração e execução

Ainda não há comando de execução do agente. Os comandos de configuração
e execução serão documentados após a implementação e validação.

Incluir:

1. Como clonar o repositório.
2. Como criar e ativar o ambiente virtual.
3. Como instalar as dependências.
4. Como preparar o Ollama e o modelo.
5. Como iniciar a aplicação.
6. Quais variáveis de ambiente são utilizadas, se houver.

## Regras e suposições

Regras implementadas em `emporio/catalog.py`:

- Disponibilidade exige status `active` e estoque maior que zero.
- A busca combina termos no nome, categoria e descrição, ignorando caixa e acentos.
  Descrições inconsistentes da fonte podem afetar os resultados; não há correção automática.
- O teto de preço é inclusivo e usa o preço promocional, sem desconto PIX.
- Promoções são consideradas ativas por `is_active`, pois não há datas de vigência.
  Se houver mais de uma ativa para o produto, aplica-se somente o maior desconto;
  essa é uma suposição do protótipo, não uma regra explícita do manual.
- Valores usam `Decimal` e arredondamento `ROUND_HALF_UP` para centavos.
  O PIX aplica 5% somente quando não há promoção ativa, sem cumulatividade.
- Consulta por ID ausente retorna `None`; busca sem resultados retorna uma lista vazia.
  Arquivos ausentes ou ambíguos e dados obrigatórios ausentes ou inválidos geram
  `CatalogDataError`, sem inventar valores padrão.
- O catálogo é carregado em memória por instância, sem escrever nos CSVs originais.

Documentar, por exemplo:

- Como status e estoque determinam a disponibilidade.
- Como são calculados os descontos.
- Como são tratadas promoções sem datas de vigência.
- Como são tratados dados ausentes.
- Como foram resolvidas ambiguidades do manual.
- Como funciona a identificação do cliente no protótipo.

## Testes e avaliação

Para executar os testes das funções, sem Ollama nem dependências externas:

```powershell
py -3.12 -m unittest discover -s tests -v
```

Foram executados 12 testes com sucesso, cobrindo consultas, filtros,
disponibilidade, promoções, cálculos e dados ausentes ou inválidos.
Os testes usam a base fornecida e CSVs sintéticos em diretórios temporários.

O teste inicial com o modelo foi executado diretamente no interpretador,
sem um script salvo no repositório. A suíte acima não testa o modelo.

Distinguir:

- Testes das funções de consulta e cálculo.
- Testes de integração com o modelo local.

No teste inicial, o modelo solicitou corretamente a ferramenta
e utilizou os dados retornados. Entretanto, não informou que
os retornos simulados eram dados de teste.

Esse teste utilizou um mapeamento explícito entre nome e ID,
portanto não validou a busca de produtos por nome.

## Exemplos de interação

Pendente: registrar e incluir links para três a cinco conversas obtidas
em execuções reais da aplicação.

Incluir pelo menos um cenário não trivial envolvendo consulta
de dados ou aplicação de políticas.

## Limitações conhecidas

- Dados estáticos, sem atualização por um sistema externo.
- Desempenho dependente do hardware e do modelo local.
- O teste inicial não comprova consistência em todos os cenários.
- Identificação do cliente e restrição de acesso a pedidos ainda não implementadas.
- Pedidos sem data efetiva de recebimento ou canal da compra; a previsão de entrega
  não permite concluir elegibilidade para devolução.

As limitações serão atualizadas a partir da implementação e dos testes.

## Melhorias futuras

Ampliar a avaliação de consistência do modelo e, conforme o escopo implementado,
melhorar a autenticação de clientes. Outras melhorias serão definidas a partir
das limitações observadas.

## Uso de assistentes de IA

Utilizei o ChatGPT para interpretar o enunciado, discutir
alternativas de arquitetura e organizar as etapas do projeto.

O Codex apoiou a inspeção do ambiente, o experimento com Ollama, a documentação
e a implementação e execução dos testes do módulo de catálogo. A integração
com o agente ainda não foi implementada.

Esta seção será atualizada conforme a participação das ferramentas
na implementação, revisão e testes.
