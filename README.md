# Empório da Música — Agente de Atendimento

Protótipo em Python para o Desafio Técnico AI Engineer da Artefact.
Atende pelo terminal, em português, consultando produtos, promoções, políticas e pedidos.
Os dados são estáticos e a identificação do cliente é simulada, sem autenticação real.

## Como executar

Ambiente testado: **Python 3.12.9**, **Ollama 0.40.13** e **`llama3.1:latest`**
(8B, Q4_K_M, identificador `46e0c10c039e`). A tag pode mudar entre instalações.
O modelo deve estar disponível no Ollama; não há download automático.

No PowerShell, na raiz do projeto:

```powershell
ollama list
Invoke-RestMethod -Uri 'http://localhost:11434/api/version'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m emporio --customer-id 3
```

Se o serviço estiver parado, abra o Ollama ou execute `ollama serve` em outro terminal.
Aplicação e testes usam somente a biblioteca padrão; `requirements.txt` contém apenas
comentários, sem pacotes a instalar. Não há credenciais ou variáveis de ambiente obrigatórias.

A CLI apresenta boas-vindas, sugestões de perguntas e a identificação simulada da sessão.
Para encerrar, use `sair`, `/sair`, `exit` ou Ctrl+C. O histórico dura somente a sessão.
No VS Code, selecione `.venv\Scripts\python.exe` como interpretador.
Para acentuação em redirecionamentos, use `-X utf8` antes de `-m`.

O cliente padrão **3** pode consultar o pedido **1** ou o rastreio `BRAB1234567BR`;
o pedido **2** fica bloqueado. Para demonstrar o pedido **9**, sem previsão ou rastreamento,
execute com `--customer-id 6`. A identidade não pode ser alterada pelo chat.

## Arquitetura e decisões

O modelo solicita ferramentas; a aplicação valida os argumentos, consulta os arquivos
e devolve resultados estruturados. Algumas respostas são controladas pela aplicação
para conter falhas observadas, como aprovações indevidas de devolução.

| Escolha | Motivo |
| --- | --- |
| Python e CLI, sem framework de agentes | Solução simples e explicável no prazo de dois dias |
| `llama3.1:latest` via Ollama local | Completou o ciclo de ferramentas, com limitações registradas |
| Funções sobre CSVs e `Decimal` | Consultas e cálculos explícitos, sem banco de dados |
| Busca textual por seções do PDF | Recupera regras completas sem embeddings ou banco vetorial |
| Histórico em memória | Continuidade sem persistência adicional |

As ferramentas são `buscar_produtos`, `consultar_politicas` e `consultar_pedido`.
O prompt não contém mapeamentos fixos de nomes de produtos para IDs.
Há limite de três chamadas por turno e contexto de **12.288 tokens**, com remoção de
turnos antigos quando necessário. O PDF inteiro não é enviado ao modelo.

- Disponibilidade distingue estoque, descontinuados e lançamentos futuros.
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

## Testes e conversas reais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Há registro de **65 testes aprovados**, cobrindo filtros, cálculos, disponibilidade,
políticas, contexto e autorização. Testes com clientes simulados não comprovam a
qualidade do modelo. Execuções reais e falhas estão nas avaliações de
[produtos](docs/avaliacoes/README.md), [políticas](docs/avaliacoes/politicas/README.md),
[pedidos](docs/avaliacoes/pedidos/README.md) e [estilo](docs/avaliacoes/estilo/README.md).

Cinco conversas reais da etapa de catálogo:

1. [Preço do Takamine GD20](docs/conversas/01-preco.md).
2. [Violões disponíveis até R$ 1.000](docs/conversas/02-orcamento.md).
3. [Produto sem estoque](docs/conversas/03-sem-estoque.md).
4. [Promoção ativa](docs/conversas/04-promocao.md).
5. [Continuidade sobre um produto](docs/conversas/05-continuidade.md).

Para repetir a avaliação de catálogo com Ollama, preservando esses exemplos:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_catalog --saida docs/avaliacoes/catalogo-nova-execucao
```

Use uma pasta nova: esse script sobrescreve arquivos de mesmo nome no destino.
Os registros históricos refletem versões sucessivas e não garantem consistência atual.

## Limitações

- Dados estáticos, sem integração comercial ou com transportadoras; autenticação simulada.
- O modelo pode omitir condições, deixar de consultar ferramentas ou contradizer resultados.
  Os controles não validam semanticamente todas as respostas.
- Busca textual limitada para sinônimos e perguntas mistas; catálogo com até dez resultados,
  sem paginação. Inconsistências dos dados afetam a busca.
- Orçamento de contexto estimado; conversas longas perdem turnos antigos.
- Devoluções usam reconhecimento textual e podem repetir regras. Não há motor de elegibilidade.
- Desempenho depende do hardware local. Os testes não cobrem todas as situações.

## Uso de IA

O ChatGPT apoiou a interpretação do desafio e a discussão de arquitetura.
O Codex apoiou a implementação, documentação, revisão e execução de testes.
Os registros distinguem respostas do modelo e intervenções da aplicação.
