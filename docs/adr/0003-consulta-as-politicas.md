# ADR 0003 — Consulta textual às políticas e orçamento de contexto

- **Status:** aceita e implementada; limitações de comportamento registradas na avaliação real.
- **Data:** 31/10/2026.
- Complementa as ADRs [0001](0001-arquitetura-inicial.md) e [0002](0002-catalogo-e-ferramentas.md).

## Contexto

A consulta de produtos já existe. Precisamos responder sobre horários, pagamentos,
frete, trocas, devoluções e garantia sem incluir o PDF inteiro no prompt nem inventar
regras. O prazo de desenvolvimento de dois dias favorece uma solução inspecionável,
sem embeddings, banco vetorial ou framework adicional. O manual contém ambiguidades
que precisam permanecer visíveis, não ser corrigidas silenciosamente.

## Decisões

### Fonte e preparação

Usar `pdftotext -raw -enc UTF-8` para extrair o PDF fornecido, separando seu conteúdo
pelos títulos numerados. A opção `-raw` preservou as associações entre colunas nas
tabelas de horários e pagamento deste documento; `-layout` havia produzido ordem
inadequada para algumas dessas tabelas. Os trechos relevantes foram conferidos contra
a extração original. Cabeçalhos e rodapés repetidos são removidos, sem resumo do texto.

O script `scripts/extract_policies.py` gera `data/politicas_secoes.json`, com 25 seções
não vazias, títulos, páginas e SHA-256 do PDF. A aplicação lê esse artefato versionado
e verifica o hash do PDF. Se a fonte mudar ou estiver ausente, informa falha em vez
de usar conteúdo silenciosamente desatualizado. Regenerar o arquivo exige `pdftotext`
no PATH; executar o agente não exige Poppler ou dependência Python adicional.

O hash vincula a extração à versão da fonte, mas não prova que o parser interpretou
corretamente a diagramação nem detecta edição manual do JSON. Alterações na fonte ou
no extrator exigem regeneração, revisão dos trechos e novos testes.

### Recuperação

Adicionar `consultar_politicas(pergunta)` ao conjunto de ferramentas. A aplicação
valida um único argumento textual de 1 a 500 caracteres. `PolicyStore` compara a
pergunta com títulos e termos associados aos assuntos, ignorando caixa e acentos.
Seleciona até dois assuntos principais, com dependências explícitas para preservar
condições e exceções; por exemplo, parcelamento recupera a tabela geral e a seção 3.1,
troca por preferência recupera também 4.4, e garantia recupera suas exclusões.

Cada seção é retornada integralmente com título, número e páginas. O limite padrão
é 4.400 caracteres para o resultado serializado. Se o conjunto completo exceder esse
limite, retorna insuficiência e pede uma pergunta mais específica: não corta frases
nem elimina uma exceção para caber. Sem correspondência, retorna `encontrado=false`
e `suficiente=false`. Uma correspondência textual não garante que o manual contenha
todos os dados exigidos pela pergunta; o modelo recebe instruções para reconhecer isso.

As `ressalvas` são análises documentadas de lacunas, separadas do texto literal:

- A seção 5.1 não cobre exatamente R$ 500. Não decidir frete grátis ou taxa de R$ 35.
- A tabela 3 e o detalhamento 3.1 divergem sobre mínimos; a expressão referente a
  R$ 50 também é ambígua. Apresentar a divergência e pedir confirmação.
- A seção 4.4 fala de troca. Sua aplicação a arrependimento online não é explícita;
  não importar essas exclusões para 4.1. A busca genérica de arrependimento recupera
  apenas 4.1; buscas de troca preservam 4.4.
- A garantia de 90 dias após recebimento não é o mesmo prazo da troca de 30 dias
  após compra. A recuperação inclui ambas quando trata de defeitos/garantia.
- Não calcular frete externo sem dados e integração de cotação, nem determinar
  elegibilidade de devolução sem recebimento efetivo e condições do produto.

### Integração e referências

O modelo solicita a ferramenta antes de explicar regras; uma mesma conversa pode
consultar produtos e políticas. A execução de ferramentas permanece limitada a três
por turno. As consultas de produtos e seus cálculos foram preservados. Resultados JSON
enviados ao modelo são compactados para reduzir orçamento sem alterar os dados.

Como o modelo omitiu citações nas execuções reais, a aplicação acrescenta um rodapé
com as fontes efetivamente consultadas. Esse rodapé indica consultas, não prova que
toda frase gerada é correta. Os registros distinguem resposta bruta do modelo e resposta
apresentada ao usuário. O prompt não contém preços, catálogo ou políticas completas.

### Contexto

Ampliar o contexto configurado de 4.096 para **8.192 tokens**, mantendo temperatura
zero e reserva máxima de **768 tokens de saída**. A inclusão de duas ferramentas,
fontes e histórico justifica a mudança; não significa que o PDF inteiro caiba.

Antes de cada chamada, estimar o custo com o tamanho UTF-8 do JSON completo
(instruções, ferramentas, histórico, mensagens e resultados) mais 512 unidades de
margem para o template. Contar um token por byte é propositalmente conservador para
esse modelo BPE e esse texto. Não é tokenização exata nem garantia para qualquer
template futuro. Se estimativa + 768 ultrapassar 8.192, remover turnos antigos completos.
Se o turno atual sozinho não couber, recusar a chamada e pedir pergunta mais específica.
Não truncar os trechos recuperados ou seus vínculos com chamadas de ferramentas.

Registrar `prompt_eval_count` e `eval_count` devolvidos pelo Ollama, junto da estimativa,
reserva e quantidade de mensagens históricas. Verificar também o prompt medido contra
a reserva. As métricas observadas estão na avaliação; não constituem uma prova geral
de ausência de truncamento para outros modelos ou templates. O cliente segue usando
timeout de 120 segundos por chamada, sem retry automático.

## Alternativas consideradas

- PDF inteiro no prompt: descartado nesta etapa para reduzir conteúdo irrelevante e
  preservar espaço de histórico; seu encaixe completo não foi validado.
- Extração do PDF a cada turno: repetiria preparação e exigiria Poppler no atendimento.
- `pypdf`/outro leitor Python: alternativa válida; o extrator já disponível mais artefato
  versionado evita uma dependência de execução e permite conferir as tabelas.
- Embeddings e banco vetorial: desnecessários para esse manual pequeno, com seções
  explícitas. A busca textual facilita explicar e revisar o que foi recuperado.
- Tokenizador local adicional: não adotado para evitar dependência e possível divergência
  do template real do Ollama. Usamos orçamento conservador e medição observada da API.
- Regras inteiramente codificadas: reduziriam algumas falhas, mas duplicariam o manual.
  Apenas as relações de seções, ressalvas e controles são explícitos na aplicação.

## Consequências, limites e validação

A busca não compreende semanticamente qualquer paráfrase, pode não recuperar um assunto
inesperado e limita perguntas com vários assuntos. Alterações de formato do PDF podem
quebrar a segmentação. Não há OCR para PDF digitalizado. As dependências e ressalvas
precisam ser revisadas quando o manual mudar.

O orçamento é conservador e pode remover histórico mesmo quando os tokens reais caberiam.
Isso ocorreu na continuidade avaliada e está explicitado nas métricas. Perguntas com
pronomes podem exigir esclarecimento após perda de histórico.

O modelo ainda pode omitir ressalvas, confundir regras ou deixar de chamar ferramentas.
Houve falhas reais de cumulatividade e de mistura entre troca e arrependimento nas
rodadas iniciais; os registros foram preservados. O horário regular foi respondido
corretamente, mas o modelo não repetiu as exceções de feriados/datas especiais.
Não tratar todas as execuções como aprovadas só porque a recuperação acertou.

Os testes automatizados verificam recuperação, exceções, dados ausentes, integridade
da fonte, contexto e regressão das funções de produtos. Conversas reais e métricas
estão em [avaliação de políticas](../avaliacoes/politicas/README.md). Pedidos e identidade
de clientes continuam fora desta etapa; não há alterações nos CSVs nem no PDF original.

## Uso de IA

Codex implementou a ferramenta, o extrator, os controles e testes, executou os cenários,
inspecionou falhas e apoiou esta documentação. Os diálogos registrados são execuções
reais, sem reescrever falas para aparentar sucesso.
