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

## Funcionalidades implementadas

O agente permite:

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
O estilo, os esclarecimentos iniciais e as respostas controladas estão na
[ADR 0005 — Estilo de atendimento](docs/adr/0005-estilo-e-esclarecimento.md).

## Arquitetura e estratégia de prompt

O fluxo é CLI → modelo → validação de ferramenta → consulta Python aos CSVs →
resultado estruturado → resposta do modelo. Não há framework de agentes nem
dependências externas ao Python. O cliente HTTP usa a biblioteca padrão.

`prompts.py` define persona e instruções, sem catálogo ou mapeamentos de nomes
para IDs. `buscar_produtos` aceita `nome`, `categoria`, `preco_maximo` e
`disponibilidade` (`todas` ou `disponiveis`), todos opcionais. A aplicação rejeita
ferramentas desconhecidas, argumentos extras e tipos ou valores inválidos.
Os preços são calculados em Python e enviados ao modelo como texto decimal.
Cada produto inclui `preco_final_brl` (preço com promoção, quando ativa) e
`preco_pix_brl` (5% sobre tabela sem promoção; com promoção, mantém o preço
promocional sem desconto adicional). O modelo usa esses valores sem recalcular.

O prompt orienta linguagem acolhedora e objetiva, adaptação à experiência do cliente,
uso do contexto e empatia nas reclamações, sem saudações ou perguntas repetitivas.
As referências de estilo são ilustrativas, sem preços ou IDs de exemplo como fatos.
Consultas e restrições de privacidade continuam obrigatórias; o escopo de acessórios
é recuperado do manual, sem inventar parceiros ou insistir em uma venda.
Em aberturas simples reconhecidas, a aplicação permite perguntar sem ferramentas;
nas perguntas explícitas de dados, mantém as consultas. Perguntas reconhecidas de venda
ou troca de acessórios passam primeiro pela consulta ao escopo do manual, sem aplicar
regras de troca de instrumentos a esses itens. Substituição de cordas como manutenção
não é confirmada sem informação suficiente. Uma consulta
específica de falta de estoque pode receber resposta controlada, sem oferecer
notificações inexistentes. Há limites lexicais e desvios de estilo ainda observados.

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
total do turno. As referências ficam nos resultados das ferramentas e nos registros
internos; a inclusão do rodapé na resposta está comentada em `agent.py` para não
aparecer no terminal. Os registros históricos podem conter o rodapé antigo.

`consultar_pedido` aceita `pedido_id` **ou** `codigo_rastreio`, apenas um por chamada,
e valida em Python se o proprietário é o cliente da sessão
antes de relacionar itens e produtos. O modelo não recebe argumento para escolher a
identidade. Pedidos alheios e inexistentes têm a mesma resposta, sem exposição de dados.
O total vem do registro histórico, sem usar preços atuais. Previsão não é recebimento.
O rastreio é pesquisado nos CSVs, sem consulta à transportadora, e não substitui a
identidade da sessão. Códigos alheios e inexistentes têm a mesma resposta genérica.
Ver [ADR 0008](docs/adr/0008-consulta-por-rastreio.md).

Trocas e devoluções têm atendimento apenas informativo: a aplicação apresenta as
seções recuperadas, sem iniciar processos, solicitar dados para abertura ou confirmar
elegibilidade individual. Dados fornecidos espontaneamente não geram aprovação.
A consulta de pedidos permanece somente leitura. Ver [ADR 0009](docs/adr/0009-devolucoes-informativas.md).
Nas respostas controladas que combinam pedidos e devolução, os dados autorizados
do pedido são preservados, incluindo total histórico, itens, previsão e rastreio.
Isso também vale para uma consulta de pedido após uma pergunta de devolução.
Recuperar uma seção de troca como dependência de garantia não ativa sozinho a
resposta controlada: é necessário assunto de troca/devolução reconhecido na conversa.
Quando essa proteção substitui a resposta em uma consulta conjunta de produtos,
os preços e a disponibilidade retornados pela ferramenta são preservados no texto.
Os registros distinguem respostas do modelo e proteções da aplicação.

| Arquivo | Responsabilidade |
| --- | --- |
| `emporio/__main__.py` | Entrada da CLI e encerramento |
| `emporio/agent.py` | Histórico e ciclo de ferramentas |
| `emporio/ollama_client.py` | Comunicação HTTP e erros do Ollama |
| `emporio/tools.py` | Contratos, validação e execução das três ferramentas |
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

## Materiais fornecidos

| Arquivo | Finalidade |
|---|---|
| `categories.csv` | Categorias dos instrumentos |
| `products.csv` | Catálogo, preços, estoque e especificações |
| `promotions.csv` | Promoções e descontos |
| `customers.csv` | Cadastro fornecido, mas não utilizado pela aplicação |
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
verifique se o modelo `llama3.1:latest` está disponível e o serviço está ativo:

```powershell
ollama list
Invoke-RestMethod -Uri 'http://localhost:11434/api/version'
```

Se o serviço estiver parado, abra o aplicativo Ollama ou execute `ollama serve`
em outro terminal. Nenhum modelo é baixado automaticamente.

Crie a `.venv` e execute usando seu interpretador, sem precisar ativar scripts:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m emporio --customer-id 3
```

Digite sua pergunta e pressione Enter. Para encerrar, use `sair`, `/sair`, `exit`
ou Ctrl+C. O histórico existe somente durante a sessão.

O cliente simulado padrão é **3**: o pedido 1 pertence a ele, enquanto o pedido 2
fica bloqueado. Para demonstrar o pedido 9, sem previsão ou rastreamento, altere
o argumento para `--customer-id 6`. A identidade não muda pelo chat e **não
constitui autenticação real**.

Na sessão do cliente 3, também é possível informar apenas `BRAB1234567BR` para
consultar o pedido correspondente na base. O mesmo código permanece bloqueado em
sessões de outros clientes.

O ambiente foi verificado com Python 3.12.9. A aplicação e os testes usam apenas
a biblioteca padrão; `requirements.txt` contém somente comentários e não há
`requirements-dev.txt`. Se desejar validar o arquivo, o comando abaixo foi
verificado sem acessar um índice nem instalar pacotes:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index -r requirements.txt
```

A `.venv/` é ignorada pelo Git e deve ser recriada por quem clonar o projeto.
Não há credenciais ou variáveis de ambiente obrigatórias. O Ollama roda como
serviço separado em `http://localhost:11434`.

**Alternativas de execução:** a ativação com `.\.venv\Scripts\Activate.ps1`
é opcional; se for bloqueada, use o interpretador direto acima. Sem ambiente
virtual, também é possível usar `py -3.12 -m emporio --customer-id 3`.
Para acentuação em redirecionamentos, acrescente `-X utf8` antes de `-m`.
No VS Code, selecione `.venv\Scripts\python.exe` em **Python: Select Interpreter**.

O arquivo `data/politicas_secoes.json` já está preparado e vinculado ao PDF por
SHA-256. Somente se alterar o manual, regenere e revise a extração:

```powershell
.\.venv\Scripts\python.exe -m scripts.extract_policies
```

A regeneração exige `pdftotext` (Poppler) no PATH. Esse executável e o Ollama
não são pacotes Python e não entram em `requirements.txt`. A execução normal
usa o arquivo derivado e não exige Poppler.

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

Ressalvas do manual ficam separadas dos trechos literais: parcelamento contém
divergências; exclusões de troca não
devem ser importadas automaticamente para arrependimento online. A aplicação não
escolhe silenciosamente uma regra para preencher essas lacunas.
**WhatsApp adotado: (67) 3341-4444**, conforme decisão explícita do autor em
01/11/2026. O PDF possui contatos divergentes; a escolha é retornada separadamente
dos trechos originais, que foram preservados. Ver [ADR 0006](docs/adr/0006-contato-whatsapp.md).
**Frete na região metropolitana de Campo Grande:** grátis para pedidos com total
**maior ou igual a R$ 500**; abaixo desse valor, R$ 35. A inclusão da igualdade foi
confirmada pelo autor em 01/11/2026 e é retornada em `decisoes_confirmadas`, sem
reescrever o PDF. A regra não se aplica ao frete para outras cidades.
Ver [ADR 0007](docs/adr/0007-limite-frete-metropolitano.md).
A identificação é simulada por `--customer-id`; autenticação real permanece pendente.
Nos pedidos, itens são relacionados pelo ID do produto somente para nome e quantidade.
O total registrado não é reconstruído com o catálogo. Campos ausentes são informados
sem valores presumidos. As ferramentas são somente leitura, sem cancelamento, troca,
devolução, reembolso ou encaminhamento real.

## Testes e avaliação

Execute a suíte local, sem precisar do Ollama:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**65 testes passaram**, cobrindo filtros, disponibilidade, promoções, cálculos,
dados ausentes, políticas e referências, contexto, autorização dos pedidos e
identidade da sessão. Os testes usam os CSVs fornecidos, fontes sintéticas e
clientes simulados; não comprovam a qualidade das respostas do modelo.

Para executar avaliações reais com o Ollama:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_catalog
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_policies --rodada rodada-06
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_orders --rodada rodada-05
```

O primeiro comando substitui os exemplos em `docs/conversas/`; use `--saida`
para gravar em outra pasta. Os scripts de políticas e pedidos recusam sobrescrever
rodadas: escolha um identificador novo. Os nomes acima são sugestões para a próxima
execução; as últimas rodadas registradas são `rodada-05` de políticas e
`rodada-04` de pedidos.

Os registros preservam ferramentas, argumentos, resultados, tempos, respostas brutas
e intervenções da aplicação. Resultados, falhas e evolução dos experimentos estão em:

- [Avaliação inicial de produtos](docs/avaliacoes/README.md).
- [Políticas e orçamento de contexto](docs/avaliacoes/politicas/README.md).
- [Pedidos, autorização e devolução](docs/avaliacoes/pedidos/README.md).
- [Estilo, esclarecimentos e limitações de linguagem](docs/avaliacoes/estilo/README.md).

As avaliações são execuções reais em versões sucessivas, não um benchmark nem
garantia de consistência. O experimento preliminar usava um mapeamento explícito
entre nome e ID; a implementação atual busca produtos por nome, sem esse mapeamento.

## Exemplos de interação

Cinco conversas reais registradas com o agente:

1. [Preço do Takamine GD20](docs/conversas/01-preco.md).
2. [Violões disponíveis até R$ 1.000](docs/conversas/02-orcamento.md).
3. [Produto sem estoque](docs/conversas/03-sem-estoque.md).
4. [Promoção ativa e preço calculado](docs/conversas/04-promocao.md).
5. [Continuidade sobre produto apresentado](docs/conversas/05-continuidade.md).

Esses exemplos são registros históricos da etapa de catálogo. Os testes posteriores
de produtos, políticas e pedidos, incluindo omissões e proteções da aplicação,
estão nas avaliações vinculadas acima. Não há aprovação irrestrita de todas as
respostas geradas.

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
  na resposta. As referências internas não garantem fidelidade de todas as frases geradas.
- Descontinuados e lançamentos foram testados nas funções; as conversas reais não
  cobrem todos esses estados nem todas as falhas.
- A identidade de clientes é simulada: quem executa a CLI pode escolher qualquer ID.
  A autorização restringe a sessão, mas não substitui autenticação real.
- Não existe motor de elegibilidade para devolução. Perguntas reconhecidas de troca ou
  devolução recebem seções literais por controle da aplicação; o reconhecimento textual
  é limitado e pode repetir a política. Em perguntas mistas, a proteção depende das
  ferramentas chamadas e não valida semanticamente todas as respostas possíveis.
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

O Codex apoiou em todas as etapas do projeto.

Esta seção será atualizada conforme a participação das ferramentas
na implementação, revisão e testes.
