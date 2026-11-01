# Verificação de estilo de atendimento

Entradas roteirizadas e ilustrativas, com respostas de execuções reais usando
`llama3.1:latest`. O nome Ana é declarado no roteiro; não representa autenticação
nem um cadastro consultado. Preços e disponibilidade foram obtidos dos CSVs.

## Resultado final observado

| Situação | Resultado |
| --- | --- |
| Escolha de violão sem detalhes | Perguntou experiência e orçamento, usando somente o nome fornecido, sem listar produtos ou chamar ferramentas |
| Continuidade com experiência e teto de R$ 700 | Consultou os filtros e apresentou sete opções da base; não repetiu experiência/orçamento, mas repetiu a saudação |
| Venda de cabo | Aplicação consultou seção 1 do manual e informou que não vende acessórios, com referência; não ofereceu parceiros ou outra venda |
| Modelo sem estoque | Consulta confirmou GF-3D sem estoque; resposta controlada informou a situação na base e ofereceu consultar semelhantes, sem notificação fictícia |
| Teclado com tecla sem funcionar | Acolheu o problema e perguntou quando recebeu, sem inventar nome, explicar direito à troca ou prometer solução |

As falas completas estão em [validação 04](validacao-04.md). O caso de acessórios
nessa rodada ainda falhou; sua verificação final é
[validação 05 — acessório](validacao-05-acessorio.json), com consulta real do manual
iniciada pela aplicação e sem chamada ao modelo. O resultado final de estoque está em
[validação 06 — estoque](validacao-06-estoque.json), com resposta bruta e resposta
apresentada separadas. Não atribuir à geração livre do modelo as respostas controladas.

## Tentativas preservadas

- `validacao-01`: consulta prematura de catálogo, repetição de saudação, uso de nome
  não informado na reclamação e conclusão inadequada sobre acessórios.
- `validacao-02`: prompt mais longo não resolveu; houve bloqueio por orçamento de
  contexto, resposta incorreta de acessórios e chamada com número de pedido inventado.
- `validacao-03`: prompt reduzido e esclarecimento inicial sem ferramentas melhoraram
  escolha e reclamação. A consulta de acessórios ainda escolheu o catálogo e o modelo
  sugeriu notificação de reposição sem serviço implementado.
- `validacao-04`: restringir ferramentas para acessórios ainda levou o modelo a emitir
  JSON de uma função indisponível como texto. Os demais casos mantiveram as melhorias.
- `validacao-05-acessorio` e `validacao-06-estoque`: verificação dos controles explícitos,
  fundamentados nas consultas reais. Nenhuma inscrição ou ação comercial foi realizada.

As execuções foram pontuais, após ajustes sobre os mesmos roteiros; não são um
benchmark nem prova de consistência. Os registros JSON incluem contexto e ferramentas.
Os exemplos de estilo fornecidos pelo autor não foram usados como fatos do catálogo.

## Testes e limitações

54 testes automatizados passaram, incluindo produtos, políticas, pedidos e os novos
controles. Eles não equivalem à avaliação de linguagem do modelo. Erros de consulta
e devoluções mantêm os controles anteriores; nem todas as referências de estilo
receberam uma nova conversa real nesta verificação.

Ainda há repetição ocasional de cumprimentos e respostas longas ou pouco naturais.
As regras lexicais não cobrem todas as formas de pedir ajuda; perguntas compostas
continuam dependentes do modelo. O reconhecimento do escopo de acessórios depende
do manual fornecido. A proteção de devolução permanece conservadora e pode repetir
perguntas sem um estado estruturado de dados declarados pelo usuário.
