# Empório da Música — Agente de Atendimento

Protótipo de agente de atendimento por texto desenvolvido para o
Desafio Técnico AI Engineer da Artefact.

O objetivo é auxiliar clientes da loja fictícia Empório da Música,
respondendo dúvidas sobre produtos, disponibilidade, promoções,
pedidos e políticas da loja com base nos materiais fornecidos.

## Status do projeto

Primeira etapa funcional: CLI com histórico em memória, integração local com
`llama3.1:latest` via Ollama e consultas ao catálogo por ferramentas.
As consultas, os cálculos e os controles da aplicação possuem testes automatizados;
cinco conversas reais foram executadas e registradas.

Pedidos e consulta às políticas ainda não estão implementados. Não há leitura
dos dados de clientes pelo agente nesta etapa.

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
| Interface | CLI | Permite priorizar o funcionamento do agente no prazo disponível |
| Histórico | Em memória | Permite continuidade durante a sessão sem banco de dados |
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
O contrato da ferramenta e os controles da primeira etapa estão na
[ADR 0002 — Catálogo e execução de ferramentas](docs/adr/0002-catalogo-e-ferramentas.md).

## Arquitetura e estratégia de prompt

O fluxo é CLI → modelo → validação de ferramenta → consulta Python aos CSVs →
resultado estruturado → resposta do modelo. Não há framework de agentes nem
dependências externas ao Python. O cliente HTTP usa a biblioteca padrão.

`prompts.py` define persona e instruções, sem catálogo ou mapeamentos de nomes
para IDs. `buscar_produtos` aceita `nome`, `categoria`, `preco_maximo` e
`disponibilidade` (`todas` ou `disponiveis`), todos opcionais. A aplicação rejeita
ferramentas desconhecidas, argumentos extras e tipos ou valores inválidos.
Os preços são calculados em Python e enviados ao modelo como texto decimal.

São permitidas até três chamadas de ferramentas por turno. A quarta solicitação
encerra o turno com mensagem compreensível. O histórico guarda até quatro turnos
completos em memória; para envio, retém os mais recentes até aproximadamente
10.000 caracteres serializados. Isso é uma heurística, não uma contagem de tokens.
Contexto configurado: 4.096 tokens; temperatura: 0; saída: até 768 tokens por chamada;
timeout HTTP: 120 segundos por chamada. Turnos incompletos não entram no histórico.
As políticas não são enviadas ao modelo nesta etapa.

| Arquivo | Responsabilidade |
| --- | --- |
| `emporio/__main__.py` | Entrada da CLI e encerramento |
| `emporio/agent.py` | Histórico e ciclo de ferramentas |
| `emporio/ollama_client.py` | Comunicação HTTP e erros do Ollama |
| `emporio/tools.py` | Contrato, validação e execução de `buscar_produtos` |
| `emporio/catalog.py` | Leitura dos CSVs, filtros e cálculos |
| `emporio/prompts.py` | Persona, limites e instruções do modelo |
| `tests/` | Testes locais, sem depender do modelo |
| `scripts/evaluate_catalog.py` | Conversas reais reproduzíveis e registro das ferramentas |

## Dados utilizados

| Arquivo | Finalidade |
|---|---|
| `categories.csv` | Categorias dos instrumentos |
| `products.csv` | Catálogo, preços, estoque e especificações |
| `promotions.csv` | Promoções e descontos |
| `customers.csv` | Dados dos clientes |
| `orders.csv` | Dados e status dos pedidos |
| `order_items.csv` | Produtos e quantidades dos pedidos |
| políticas_da_loja.pdf | Regras e procedimentos de atendimento |

Todos esses arquivos estão na pasta `data/`.

## Pré-requisitos

Ambiente verificado em 31/10/2026: Python **3.12.9** e Ollama **0.40.13**.
No ambiente avaliado, use `py -3.12`.

Modelo utilizado: llama3.1:latest.

Identificador do modelo testado: **`46e0c10c039e`** (8B, quantização Q4_K_M).
A tag `latest` pode apontar para outro artefato em uma instalação futura.

## Configuração e execução

No PowerShell, abra a raiz deste repositório. Com Python 3.12 e Ollama instalados,
verifique o serviço e o modelo:

```powershell
py -3.12 --version
ollama --version
ollama list
Invoke-RestMethod -Uri 'http://localhost:11434/api/version'
```

O modelo `llama3.1:latest` precisa estar instalado. Nenhum modelo ou dependência
é baixado automaticamente. Se o serviço estiver parado, abra o aplicativo Ollama
ou execute `ollama serve` em outro terminal. Não foi necessário iniciar um segundo
servidor no ambiente avaliado, pois o serviço já estava ativo.

Inicie a aplicação com o comando verificado:

```powershell
py -3.12 -m emporio
```

Digite sua pergunta e pressione Enter. Use `sair`, `/sair`, `exit` ou Ctrl+C para
encerrar. O histórico é descartado ao sair. O comando foi verificado com uma
pergunta real sobre o Takamine GD20 e encerramento com `sair`.

Não é necessário executar `pip install`; esta etapa usa somente a biblioteca
padrão. Não há variáveis de ambiente obrigatórias nem credenciais. A CLI usa
`http://localhost:11434` e `llama3.1:latest`. Um ambiente virtual é opcional.
Se houver problemas de acentuação em terminais ou redirecionamentos, use
`py -3.12 -X utf8 -m emporio`, também verificado.

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

As interpretações das ambiguidades do manual e a identificação de clientes
permanecem pendentes, pois políticas e pedidos não fazem parte desta etapa.

## Testes e avaliação

Para executar os testes das funções, sem Ollama nem dependências externas:

```powershell
py -3.12 -m unittest discover -s tests -v
```

Foram executados 21 testes com sucesso, cobrindo consultas, filtros,
disponibilidade, promoções, cálculos, argumentos inválidos, limite de ferramentas,
histórico, erros HTTP e dados ausentes ou inválidos.
Os testes usam a base fornecida e CSVs sintéticos em diretórios temporários.

Os testes de orquestração usam um cliente simulado, não comprovam a qualidade do
modelo. Para executar as cinco conversas reais com o Ollama local:

```powershell
py -3.12 -m scripts.evaluate_catalog
```

Esse comando foi executado e grava os diálogos, argumentos, resultados e tempos
em `docs/conversas/`, substituindo os registros anteriores nessa pasta. As rodadas
iniciais com falhas foram preservadas em `docs/avaliacoes/`.

No teste inicial, o modelo solicitou corretamente a ferramenta
e utilizou os dados retornados. Entretanto, não informou que
os retornos simulados eram dados de teste.

Esse experimento preliminar utilizou um mapeamento explícito entre nome e ID.
As conversas da implementação atual usam busca por nome sem esse mapeamento.

## Exemplos de interação

Conversas reais executadas com o mesmo agente usado pela CLI:

1. [Preço do Takamine GD20](docs/conversas/01-preco.md).
2. [Violões disponíveis até R$ 1.000](docs/conversas/02-orcamento.md).
3. [Produto sem estoque](docs/conversas/03-sem-estoque.md).
4. [Promoção ativa e preço calculado](docs/conversas/04-promocao.md).
5. [Continuidade sobre produto apresentado](docs/conversas/05-continuidade.md).

Os cinco cenários atenderam aos critérios de dados na rodada final: Takamine a
R$ 2.199,00; lista filtrada com dez das doze opções; item sem estoque identificado
como indisponível; promoção de 10% de R$ 359,00 para R$ 323,10; continuidade com
nova consulta do produto correto. Cada turno levou aproximadamente 5 a 9 segundos
com o modelo carregado. Não é um benchmark nem uma garantia de consistência.

Veja a [avaliação das rodadas e limitações](docs/avaliacoes/README.md).

## Limitações conhecidas

- Dados estáticos, sem atualização por um sistema externo.
- Desempenho dependente do hardware e do modelo local.
- O teste inicial não comprova consistência em todos os cenários.
- O modelo às vezes omite que a fonte é estática; a CLI informa isso ao iniciar.
- A busca retorna até dez itens, sem paginação, e não faz busca semântica ou correção
  de digitação. Categoria usa correspondência parcial, ignorando caixa e acentos.
- A aplicação valida ferramentas, mas não valida semanticamente todo o texto gerado.
  O modelo ainda pode deixar de consultar a ferramenta ou contradizer seu retorno.
- Não há orçamento exato de tokens. Conversas longas podem perder contexto e referências
  antigas ao limitar o histórico. Descontinuados e lançamentos foram testados nas
  funções; as cinco conversas reais não cobrem todos esses estados nem todas as falhas.
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
e a implementação da CLI, cliente Ollama, ferramenta, catálogo e testes. Também
executou as conversas reais, inspecionou as falhas, ajustou o contrato e as instruções
e documentou os resultados, incluindo as rodadas malsucedidas.

Esta seção será atualizada conforme a participação das ferramentas
na implementação, revisão e testes.
