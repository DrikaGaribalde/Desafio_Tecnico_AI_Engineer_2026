# ADR 0005 — Estilo de atendimento e esclarecimento inicial

- **Status:** aceita e implementada, com limitações de redação observadas.
- **Data:** 01/11/2026.

## Contexto

O atendimento precisa ser acolhedor, informal e profissional, aproveitar o contexto
e reconhecer reclamações sem inventar dados, nomes ou ações. Os exemplos fornecidos
pelo autor são referências ilustrativas de estilo, não fontes de preços ou condições.

Testar apenas instruções mais longas não foi suficiente: o modelo listou produtos
antes de entender a necessidade, inventou um nome em reclamação e tratou acessórios
como ausência temporária de estoque. O aumento do prompt também causou recusa por
contexto em uma das execuções; o texto foi posteriormente reduzido.

O template instalado do `llama3.1:latest`, inspecionado com `ollama show --template`,
instrui a escolher uma função quando o último turno do usuário recebe ferramentas.
Isso dificulta pedir esclarecimentos antes de consultar uma fonte.

## Decisões

- Centralizar orientações em `STYLE_GUIDE`, sem preços, IDs ou disponibilidade fictícia.
  Usar o primeiro nome somente quando informado, explicar termos conforme a experiência,
  evitar formalidade, repetição de perguntas, cumprimentos e entusiasmo artificial.
- Preservar as instruções de consulta, autorização, dados ausentes e ausência de ações
  comerciais. As fontes continuam sendo ferramentas e materiais fornecidos.
- Em aberturas simples sem histórico, reconhecer frases de escolha sem experiência e
  orçamento ou relato de instrumento que chegou com defeito, sem pergunta explícita
  de regra/dado nem números. Nesses casos, fazer uma chamada sem ferramentas, orientada
  a perguntar o que falta. Consultas explícitas de preço, estoque, pedido ou política
  mantêm o fluxo de ferramentas. O reconhecimento é lexical, não um classificador geral.
- Recuperar a seção 1 do manual para termos de acessórios. Em perguntas simples sobre
  se a loja vende acessórios, a aplicação inicia `consultar_politicas` e só afirma que
  não os vende se o trecho recuperado contiver essa regra. Sem fonte, reconhece falha.
  A origem da consulta fica marcada como `aplicacao`; não há chamada ao modelo nesse
  caminho. Não usar uma busca vazia de catálogo para concluir o escopo da loja.
- Para uma pergunta de disponibilidade/estoque que retorna um único produto sem estoque,
  sem pedido de preço ou promoção, apresentar o estado confirmado e oferecer consulta
  a alternativas. Isso impede acrescentar um serviço não implementado de notificação
  de reposição. A resposta bruta do modelo continua disponível nas avaliações.

## Alternativas consideradas

Apenas acrescentar exemplos e instruções foi testado e produziu falhas. Remover
ferramentas de toda conversa impediria consultas necessárias. Um novo framework,
classificador por outro modelo ou serviço de notificações ampliaria o escopo sem
necessidade para esta etapa. Foram adotados controles pequenos e explícitos, mantendo
a mesma arquitetura e o contexto de 12.288 tokens.

## Consequências e limites

O esclarecimento inicial evita consultas prematuras nas formas reconhecidas, mas não
cobre todas as paráfrases. O tratamento de acessórios reconhece perguntas simples de
venda e aquelas cujo objeto explícito da troca/devolução é um acessório. A regra
condicionada ao texto do manual precisa de revisão se o documento mudar.

### Correção: troca de cordas e cabos

O autor relatou que “posso fazer a trocar de cordas e cabos” recebia indevidamente
uma regra de sete dias. O reconhecimento anterior cobria venda, não troca.
Foi ampliado para troca/devolução dos acessórios listados e para cordas avulsas.
A aplicação consulta explicitamente o escopo da loja antes de qualquer regra de troca,
recuperando a seção 1. Só apresenta a exclusão de acessórios se essa seção confirmar
que não são comercializados. Sem fonte, continua informando falha, sem inventar regra.

Quando “troca de cordas” puder significar manutenção, a resposta reconhece que esse
serviço não está confirmado; não conclui que substituir cordas seja impossível.
Trocar um violão que menciona cordas/cabos e consultar instrumentos de cordas ou
cordas orquestrais não são tratados como troca de acessórios. Essas distinções foram
verificadas nas funções; a pergunta relatada também foi executada na CLI.
Perguntas compostas ou paráfrases não reconhecidas continuam dependentes do fluxo normal.

Respostas controladas são mais previsíveis, porém podem repetir sua estrutura.
As demais respostas continuam sujeitas a desvios do modelo: na continuidade ele
repetiu a saudação, apesar da instrução. Não há garantia de adequação do tom ou de
ausência de afirmações indevidas em toda pergunta possível.

Os testes reais e as tentativas malsucedidas foram preservados em
[avaliação de estilo](../avaliacoes/estilo/README.md). Testes automatizados verificam
o controle de esclarecimento, preservação das ferramentas em perguntas explícitas,
necessidade de fonte para acessórios e bloqueio de oferta de notificação sem serviço.
