# Empório da Música — Agente de Atendimento

Protótipo em Python para o Desafio Técnico AI Engineer da Artefact.
Atende pelo terminal, em português, consultando produtos, promoções, políticas e pedidos.
Os dados são estáticos e a identificação do cliente é simulada, sem autenticação real.

## Configuração e execução

Ambiente testado: **Python 3.12.9**, **Ollama 0.40.13** e **`llama3.1:latest`**
(8B, Q4_K_M, identificador `46e0c10c039e`). A tag pode mudar entre instalações.
Instale Python 3.12 e Ollama antes de seguir os comandos. O projeto não baixa
o modelo automaticamente.

No PowerShell, na raiz do projeto, confira o serviço e os modelos instalados:

```powershell
ollama list
Invoke-RestMethod -Uri 'http://localhost:11434/api/version'
```

Se o serviço estiver parado, abra o Ollama ou execute `ollama serve` em outro terminal.
Se `llama3.1:latest` não aparecer na lista, baixe o modelo:

```powershell
ollama pull llama3.1:latest
```

Crie o ambiente virtual e inicie o atendimento:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m emporio --customer-id 3
```

Aplicação e testes usam somente a biblioteca padrão; `requirements.txt` contém apenas
comentários, sem pacotes a instalar. Não há credenciais ou variáveis de ambiente obrigatórias.

No VS Code, selecione `.venv\Scripts\python.exe` como interpretador.
Para acentuação em redirecionamentos, use `-X utf8` antes de `-m`.

## Como usar

Digite uma pergunta no terminal, por exemplo:

- “Fale sobre a Empório da Música.”
- “Quais violões de nylon estão disponíveis?”
- “Quanto custa o Takamine GD20 no PIX?”
- “Como funciona o parcelamento?”
- “Qual o status do pedido 1?”

As listas mostram até cinco produtos por página, ordenados por preço.
Digite **`continuar`** ou **`próxima página`** para ver mais opções com os mesmos
filtros, ou faça outra pergunta para seguir o atendimento. Após a última página,
o agente informa que não há outra. Em buscas conjuntas, a continuação segue a
última lista paginada apresentada.

Após apresentar um único produto, “E no PIX?” consulta novamente seu preço.
Se a referência não estiver clara, o agente pede o nome ou modelo. O valor vem
da ferramenta, sem acumular desconto PIX com promoção.

Para encerrar a sessão, use `sair`, `/sair`, `exit` ou Ctrl+C.
O histórico e os filtros de paginação existem somente durante a sessão.

### Consulta de pedidos

O cliente padrão **3** pode consultar o pedido **1** ou o rastreio `BRAB1234567BR`;
o pedido **2** fica bloqueado. Para demonstrar o pedido **9**, sem previsão ou rastreamento,
execute com `--customer-id 6`. A identidade não pode ser alterada pelo chat.

```powershell
.\.venv\Scripts\python.exe -m emporio --customer-id 6
```

Informe o número do pedido **ou** o código de rastreio, um por consulta.
A aplicação verifica se o pedido pertence ao cliente da sessão. Essa identificação
é uma simulação: quem inicia o programa pode escolher outro ID; não há login real.

## Arquitetura e decisões

O modelo solicita ferramentas; a aplicação valida os argumentos, consulta os arquivos
e devolve resultados estruturados. Algumas respostas são controladas pela aplicação
para conter falhas observadas, como aprovações indevidas de devolução.

Antes do atendimento, o modelo identifica se a mensagem é da loja, fora do escopo
ou ambígua, considerando o histórico recente. A aplicação redireciona assuntos
alheios; os demais seguem para consulta ou esclarecimento. Essa etapa acrescenta
uma chamada ao Ollama por mensagem. Se a classificação falhar, o agente informa
o erro e não executa consultas. Os detalhes estão na
[avaliação de escopo](docs/avaliacoes/escopo/classificacao-intencao-2026-11-02.md).

| Escolha | Motivo |
| --- | --- |
| Python e CLI, sem framework de agentes | Solução simples e explicável no prazo de dois dias |
| `llama3.1:latest` via Ollama local | Completou o ciclo de ferramentas, com limitações registradas |
| Funções sobre CSVs e `Decimal` | Consultas e cálculos explícitos, sem banco de dados |
| Busca textual por seções do PDF | Recupera regras completas sem embeddings ou banco vetorial |
| Histórico em memória | Continuidade sem persistência adicional |

| Ferramenta | O que consulta |
| --- | --- |
| `buscar_produtos` | Modelos, preços, promoções e disponibilidade nos CSVs |
| `consultar_politicas` | Apresentação da loja, categorias comercializadas e regras do manual |
| `consultar_pedido` | Dados do pedido autorizado para o cliente da sessão |

O prompt não contém mapeamentos fixos de nomes de produtos para IDs.
Há limite de três chamadas de ferramentas por turno e contexto de **12.288 tokens**, com remoção de
turnos antigos quando necessário. O PDF inteiro não é enviado ao modelo.

- Disponibilidade distingue estoque, descontinuados e lançamentos futuros.
  Se uma busca por nome retornar vazia com o filtro de disponíveis, a aplicação
  também verifica indisponíveis, mantendo categoria e orçamento. Assim, falta de
  estoque não é confundida com ausência do produto nos resultados.
- Promoções usam `is_active`; havendo várias, aplica-se somente o maior desconto.
  PIX não acumula com promoção. Os cálculos são feitos em Python.
- Pedidos têm autorização em Python pelo cliente da sessão e preservam o total histórico.
  Previsão de entrega não comprova recebimento.
- Trocas e devoluções são apenas informativas: não há abertura de processos ou aprovação
  de elegibilidade. Todas as ferramentas são somente leitura.
- Decisões confirmadas para lacunas do manual: WhatsApp **(67) 3341-4444** e frete
  metropolitano de Campo Grande grátis a partir de **R$ 500**, inclusive; abaixo, **R$ 35**.
  O PDF original foi preservado.

Justificativas e alternativas estão nas [ADRs](docs/adr/), especialmente
[arquitetura inicial](docs/adr/0001-arquitetura-inicial.md),
[políticas](docs/adr/0003-consulta-as-politicas.md),
[pedidos](docs/adr/0004-consulta-de-pedidos.md) e
[devoluções informativas](docs/adr/0009-devolucoes-informativas.md).

## Testes e conversas reais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Na última validação local desta revisão, **100 testes passaram**, cobrindo filtros,
cálculos, disponibilidade, políticas, contexto, autorização, paginação e falhas.
Testes com clientes simulados não comprovam a
qualidade do modelo. Execuções reais e falhas estão nas avaliações de
[produtos](docs/avaliacoes/README.md), [políticas](docs/avaliacoes/politicas/README.md),
[pedidos](docs/avaliacoes/pedidos/README.md) e [estilo](docs/avaliacoes/estilo/README.md).

Cinco conversas reais da rodada mais recente, executada em 02/11/2026 (horário de Brasília):

1. [Apresentação, fora do escopo e acessórios](docs/conversas/versao-final-2026-11-02-rodada-02/01-loja-e-escopo.md).
2. [Orçamento e paginação](docs/conversas/versao-final-2026-11-02-rodada-02/02-orcamento-e-paginacao.md).
3. [Preço e continuidade no PIX](docs/conversas/versao-final-2026-11-02-rodada-02/03-preco-e-continuidade.md).
4. [Indisponibilidade, descontinuado e promoção](docs/conversas/versao-final-2026-11-02-rodada-02/04-disponibilidade-e-promocao.md).
5. [Pedido próprio, pedido alheio e devolução informativa](docs/conversas/versao-final-2026-11-02-rodada-02/05-pedidos-e-devolucao.md).

Cada arquivo separa classificação de escopo, resposta bruta do modelo, resposta
apresentada e intervenções da aplicação. Inclui as ferramentas, resultados e métricas,
sem editar as falas para ocultar falhas. O código e o modelo utilizados estão
identificados nos [metadados](docs/conversas/versao-final-2026-11-02-rodada-02/metadados.json).
Esta rodada inclui as correções de continuidade no PIX e de instruções de compra na CLI.
Os registros preservam as falhas observadas e não representam aprovação integral das respostas.
Na consulta promocional, o modelo informou o valor final e o estoque, mas omitiu
o preço original e o percentual de desconto.

A [rodada anterior](docs/conversas/versao-final-2026-11-02/) foi preservada como
evidência histórica, anterior a essas correções.

Os [cinco exemplos anteriores de catálogo](docs/avaliacoes/catalogo-historico/) foram
arquivados nas avaliações, com as falas originais preservadas.

Para repetir as cinco conversas com Ollama, escolha uma pasta nova:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_final --saida docs/conversas/nova-execucao
```

Esse script recusa uma pasta existente. Os registros são execuções pontuais,
não garantem consistência em outras conversas ou após mudanças no código.

## Dados e estrutura

`data/` contém os CSVs de categorias, produtos, promoções, pedidos e itens, além de
`políticas_da_loja.pdf` e `politicas_secoes.json`. `customers.csv` é fornecido, mas não
é carregado. Os CSVs originais não são modificados.

- `emporio/`: CLI, agente, prompt, cliente Ollama e ferramentas.
- `tests/`: testes locais, sem depender do modelo.
- `scripts/`: extração do PDF e avaliações com o modelo.
- `docs/`: ADRs, conversas e resultados de avaliação.

O JSON de políticas já está preparado e vinculado ao PDF por SHA-256.
Se alterar o manual, regenere com `.\.venv\Scripts\python.exe -m scripts.extract_policies`
e revise a extração. Somente essa preparação exige `pdftotext` (Poppler) no PATH.

## Limitações e melhorias futuras

- Dados estáticos, sem integração comercial ou com transportadoras; autenticação simulada.
- O modelo pode omitir condições, deixar de consultar ferramentas ou contradizer resultados.
  Os controles não validam semanticamente todas as respostas.
- A classificação de escopo pode errar ou perder referências do histórico. Em perguntas
  mistas, o atendimento é orientado a responder somente à parte da loja.
- Busca textual limitada para sinônimos e perguntas mistas; inconsistências dos dados
  podem afetar os resultados.
- O orçamento de contexto é estimado de forma conservadora. Conversas podem perder
  turnos antigos ou receber um pedido de pergunta mais específica, mesmo com paginação.
- Devoluções usam reconhecimento textual e podem repetir regras. Não há motor de elegibilidade.
- Desempenho depende do hardware local. Os testes não cobrem todas as situações.

Com mais tempo, as prioridades seriam ampliar as avaliações reais do modelo,
melhorar a estimativa de contexto e a recuperação textual, e implementar autenticação
antes de usar dados reais de clientes.

## Uso de IA

O ChatGPT apoiou a interpretação do desafio e a discussão de arquitetura.
O Codex apoiou a implementação, documentação, revisão e execução de testes.
Os registros distinguem respostas do modelo e intervenções da aplicação.
