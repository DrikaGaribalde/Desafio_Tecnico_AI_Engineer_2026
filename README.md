# Empório da Música — Agente de Atendimento

Protótipo de agente de atendimento por texto desenvolvido para o
Desafio Técnico AI Engineer da Artefact.

O objetivo é auxiliar clientes da loja fictícia Empório da Música,
respondendo dúvidas sobre produtos, disponibilidade, promoções,
pedidos e políticas da loja com base nos materiais fornecidos.

## Status do projeto

CLI funcional com histórico em memória, `llama3.1:latest` via Ollama e ferramentas
de produtos, políticas e pedidos. As consultas, cálculos, recuperação de seções e controles
possuem testes automatizados e conversas reais registradas, incluindo falhas observadas.

Pedidos são restritos a um `customer_id` configurado pela aplicação. A identificação
é simulada, sem autenticação real. O cadastro `customers.csv` não é carregado.

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

A consulta às políticas usa busca textual por seções completas extraídas do PDF,
com títulos, páginas e ressalvas. Não envia o PDF inteiro ao contexto.

A [ADR 0001 — Arquitetura inicial](docs/adr/0001-arquitetura-inicial.md)
registra o contexto, as alternativas, os resultados dos testes e as limitações.
O contrato da ferramenta e os controles da primeira etapa estão na
[ADR 0002 — Catálogo e execução de ferramentas](docs/adr/0002-catalogo-e-ferramentas.md).
A integração das políticas, as ambiguidades e o novo orçamento estão na
[ADR 0003 — Consulta às políticas](docs/adr/0003-consulta-as-politicas.md).
A identidade simulada, autorização e proteção na consulta de pedidos estão na
[ADR 0004 — Consulta de pedidos](docs/adr/0004-consulta-de-pedidos.md).

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
10.000 caracteres serializados. Antes de cada envio há um orçamento adicional com
bytes UTF-8 do prompt completo mais margem de template e reserva de saída.
Turnos antigos são removidos inteiros se necessário; fontes não são cortadas.
Se ainda não couber, a aplicação pede uma pergunta mais específica.

Contexto configurado: **12.288 tokens**; temperatura: 0; saída: até 768 tokens por chamada;
timeout HTTP: 120 segundos. A API informa os tokens efetivos de cada chamada para
avaliação. A estimativa local é conservadora, não um tokenizador exato.
Turnos incompletos não entram no histórico.

`consultar_politicas(pergunta)` busca por palavras e títulos em 25 seções do manual,
incluindo seções relacionadas quando necessárias para preservar exceções. O resultado
inclui título, conteúdo completo e referência; sem evidência ou orçamento, informa
insuficiência. O limite por resultado é 4.400 caracteres, sujeito também ao orçamento
total do turno. A aplicação acrescenta o rodapé das fontes efetivamente consultadas.

`consultar_pedido(pedido_id)` valida em Python se o proprietário é o cliente da sessão
antes de relacionar itens e produtos. O modelo não recebe argumento para escolher a
identidade. Pedidos alheios e inexistentes têm a mesma resposta, sem exposição de dados.
O total vem do registro histórico, sem usar preços atuais. Previsão não é recebimento.

Na consulta conjunta de pedido autorizado e política de arrependimento, a aplicação
pede os dados ausentes e apresenta a seção recuperada, sem aprovar devolução. Os
registros mostram separadamente a resposta bruta do modelo e a resposta protegida.

| Arquivo | Responsabilidade |
| --- | --- |
| `emporio/__main__.py` | Entrada da CLI e encerramento |
| `emporio/agent.py` | Histórico e ciclo de ferramentas |
| `emporio/ollama_client.py` | Comunicação HTTP e erros do Ollama |
| `emporio/tools.py` | Contrato, validação e execução de `buscar_produtos` |
| `emporio/catalog.py` | Leitura dos CSVs, filtros e cálculos |
| `emporio/orders.py` | Sessão simulada, autorização e dados mínimos dos pedidos |
| `emporio/policies.py` | Recuperação de seções, dependências e ressalvas do manual |
| `emporio/context.py` | Estimativa conservadora do orçamento de contexto |
| `emporio/prompts.py` | Persona, limites e instruções do modelo |
| `tests/` | Testes locais, sem depender do modelo |
| `scripts/evaluate_catalog.py` | Conversas reais reproduzíveis e registro das ferramentas |
| `scripts/extract_policies.py` | Preparação das seções a partir do PDF |
| `scripts/evaluate_policies.py` | Conversas reais de políticas e métricas de contexto |
| `scripts/evaluate_orders.py` | Conversas reais de pedidos, privacidade e devolução |

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
| `politicas_secoes.json` | Texto derivado do PDF, com títulos, páginas e hash da fonte |

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

Crie o ambiente virtual local (a pasta `.venv/` já é ignorada pelo Git):

```powershell
py -3.12 -m venv .venv
```

O ambiente foi criado e verificado com Python 3.12.9. Para executar sem depender
da ativação de scripts do PowerShell, use diretamente seu interpretador:

```powershell
.\.venv\Scripts\python.exe -m emporio --customer-id 3
```

Para rodar os testes nesse ambiente:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A ativação é opcional, caso seja permitida no seu terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m emporio --customer-id 3
```

Na sessão de preparação, `Activate.ps1` foi bloqueado; o interpretador direto
funcionou. Não foi alterada a política de execução do PowerShell. No VS Code,
use **Python: Select Interpreter** e selecione `.venv\Scripts\python.exe`.
O ambiente isola os pacotes Python; o Ollama continua como serviço separado.

Sem ambiente virtual, a aplicação também pode ser iniciada com o comando verificado:

```powershell
py -3.12 -m emporio
```

O cliente simulado padrão é **3**, exibido ao iniciar. Para escolher outro cliente
antes de iniciar a sessão:

```powershell
py -3.12 -X utf8 -m emporio --customer-id 3
```

Esse comando foi verificado com consulta real ao pedido 1 e encerramento com `sair`.
O pedido 1 pertence ao cliente 3; o pedido 2 não fica acessível nessa sessão.
O cliente 6 permite demonstrar o pedido 9, sem rastreamento nem previsão.
A identidade não pode ser alterada pelo chat. **A opção de terminal é uma simulação,
não comprova quem é o usuário**; não utilizar com dados reais ou como autenticação.

Digite sua pergunta e pressione Enter. Use `sair`, `/sair`, `exit` ou Ctrl+C para
encerrar. O histórico é descartado ao sair. O comando foi verificado com uma
pergunta real sobre o Takamine GD20 e encerramento com `sair`.

Não é necessário executar `pip install`; esta etapa usa somente a biblioteca
padrão. Não há variáveis de ambiente obrigatórias nem credenciais. A CLI usa
`http://localhost:11434` e `llama3.1:latest`. O ambiente virtual é recomendado,
embora opcional; a pasta local deve ser recriada por quem clonar o projeto.
Se houver problemas de acentuação em terminais ou redirecionamentos, use
`py -3.12 -X utf8 -m emporio`, também verificado.

O arquivo `data/politicas_secoes.json` já está preparado. A aplicação verifica seu
vínculo com o PDF por SHA-256. Se o PDF mudar, regenere e revise a extração:

```powershell
py -3.12 -m scripts.extract_policies
```

Esse comando foi executado usando `pdftotext` disponível no PATH do ambiente.
Somente a regeneração exige esse executável (Poppler); a execução normal não.
Não houve instalação de dependências ou download de modelos nesta integração.

## Regras e suposições

Regras implementadas em `emporio/catalog.py`:

- Disponibilidade exige status `active` e estoque maior que zero.
- A busca combina termos no nome, categoria e descrição, ignorando caixa e acentos.
  Descrições inconsistentes da fonte podem afetar os resultados; não há correção automática.
- O teto de preço é inclusivo e usa o preço promocional, sem desconto PIX.
  Filtros textuais opcionais vazios significam ausência de restrição.
- Promoções são consideradas ativas por `is_active`, pois não há datas de vigência.
  Se houver mais de uma ativa para o produto, aplica-se somente o maior desconto;
  essa é uma suposição do protótipo, não uma regra explícita do manual.
- Valores usam `Decimal` e arredondamento `ROUND_HALF_UP` para centavos.
  O PIX aplica 5% somente quando não há promoção ativa, sem cumulatividade.
- Consulta por ID ausente retorna `None`; busca sem resultados retorna uma lista vazia.
  Arquivos ausentes ou ambíguos e dados obrigatórios ausentes ou inválidos geram
  `CatalogDataError`, sem inventar valores padrão.
- O catálogo é carregado em memória por instância, sem escrever nos CSVs originais.

Ressalvas do manual ficam separadas dos trechos literais: o frete de exatamente
R$ 500 não é definido; parcelamento contém divergências; exclusões de troca não
devem ser importadas automaticamente para arrependimento online. A aplicação não
escolhe silenciosamente uma regra para preencher essas lacunas.
A identificação é simulada por `--customer-id`; autenticação real permanece pendente.
Nos pedidos, itens são relacionados pelo ID do produto somente para nome e quantidade.
O total registrado não é reconstruído com o catálogo. Campos ausentes são informados
sem valores presumidos. As ferramentas são somente leitura, sem cancelamento, troca,
devolução, reembolso ou encaminhamento real.

## Testes e avaliação

Para executar os testes das funções, sem Ollama nem dependências externas:

```powershell
py -3.12 -m unittest discover -s tests -v
```

Foram executados 48 testes com sucesso, cobrindo consultas, filtros,
disponibilidade, promoções, cálculos, argumentos inválidos, limite de ferramentas,
histórico, erros HTTP, dados ausentes ou inválidos, políticas, referências,
exceções, orçamento de contexto, autorização dos pedidos e identidade da sessão.
Os testes usam a base fornecida e CSVs sintéticos em diretórios temporários.

Os testes de orquestração usam um cliente simulado, não comprovam a qualidade do
modelo. Para executar as cinco conversas reais com o Ollama local:

```powershell
py -3.12 -m scripts.evaluate_catalog
```

Esse comando foi executado e grava os diálogos, argumentos, resultados e tempos
em `docs/conversas/`, substituindo os registros anteriores nessa pasta. As rodadas
iniciais com falhas foram preservadas em `docs/avaliacoes/`.

Para avaliar políticas com o modelo e registrar tokens, ferramentas e respostas:

```powershell
py -3.12 -X utf8 -m scripts.evaluate_policies --rodada rodada-06
```

As rodadas `rodada-01` a `rodada-05` foram executadas. Escolha um identificador
novo: o script recusa sobrescrever uma rodada existente. Ele grava em
`docs/avaliacoes/politicas/`. O parâmetro mostrado permite uma nova execução;
o comando efetivamente usado na rodada final foi o mesmo com `--rodada rodada-05`.

Para avaliar os cinco cenários de pedidos (incluindo tentativa de troca de identidade):

```powershell
py -3.12 -X utf8 -m scripts.evaluate_orders --rodada rodada-05
```

As rodadas de pedidos `rodada-01` a `rodada-04` já foram executadas; use um nome novo
para reproduzir. O script grava em `docs/avaliacoes/pedidos/` sem sobrescrever rodadas.
A rodada final registrada foi executada com `--rodada rodada-04`.

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

Os seis cenários de políticas, as respostas reais e a medição do contexto estão em
[avaliação de políticas](docs/avaliacoes/politicas/README.md). O horário regular foi
respondido corretamente, mas houve omissão de exceções; a consulta mista executou as
duas ferramentas, com limitações de apresentação registradas. Não é aprovação irrestrita
de todas as respostas. Os exemplos anteriores de produtos são registros históricos.

Os cinco cenários de pedidos, as respostas brutas e as proteções da aplicação estão na
[avaliação de pedidos](docs/avaliacoes/pedidos/README.md). A consulta de produtos foi
repetida após adicionar a terceira ferramenta, preservando os registros anteriores.

## Limitações conhecidas

- Dados estáticos, sem atualização por um sistema externo.
- Desempenho dependente do hardware e do modelo local.
- O teste inicial não comprova consistência em todos os cenários.
- O modelo às vezes omite que a fonte é estática; a CLI informa isso ao iniciar.
- A busca retorna até dez itens, sem paginação, e não faz busca semântica ou correção
  de digitação. Categoria usa correspondência parcial, ignorando caixa e acentos.
- A aplicação valida ferramentas, mas não valida semanticamente todo o texto gerado.
  O modelo ainda pode deixar de consultar a ferramenta ou contradizer seu retorno.
- O orçamento local não usa um tokenizador exato. Conversas podem perder referências
  antigas ao remover turnos inteiros. Isso ocorreu na avaliação real das políticas,
  embora as chamadas enviadas coubessem no contexto configurado.
- A busca textual não garante compreensão de sinônimos ou perguntas com vários assuntos.
  O extrator é adequado ao PDF fornecido, sem OCR, e exige revisão se sua estrutura mudar.
- Seções completas preservam condições no retorno, mas o modelo ainda pode omiti-las
  na resposta. Citações no rodapé são adicionadas pela aplicação e não garantem fidelidade.
- Descontinuados e lançamentos foram testados nas funções; as conversas reais não
  cobrem todos esses estados nem todas as falhas.
- A identidade de clientes é simulada: quem executa a CLI pode escolher qualquer ID.
  A autorização restringe a sessão, mas não substitui autenticação real.
- Não existe motor de elegibilidade ou estado estruturado para validar respostas sobre
  devolução; a proteção conservadora pode repetir perguntas. Ela depende das ferramentas
  chamadas no turno e não valida semanticamente todas as respostas possíveis.
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
Na integração das políticas, também preparou o extrator e o arquivo derivado,
implementou busca e orçamento de contexto e executou avaliações reais com métricas.
Na consulta de pedidos, implementou a sessão simulada, autorização, normalização dos
argumentos e proteções de resposta, além de testes e conversas reais. As falhas iniciais
e intervenções da aplicação foram documentadas.

Esta seção será atualizada conforme a participação das ferramentas
na implementação, revisão e testes.
