# ADR 0006 — Contato de WhatsApp adotado

- **Status:** aceita e implementada.
- **Data:** 01/11/2026.

## Contexto e decisão

O manual apresenta `(67) 3341-4444` na seção 1.2 e outro contato na seção 7.
O autor confirmou explicitamente que o projeto deve usar **(67) 3341-4444**
como WhatsApp de atendimento. Essa é uma decisão do projeto, sem afirmar que
o documento original foi corrigido ou que o contato foi verificado externamente.

## Implementação e consequências

A consulta de políticas recupera as seções de contato e retorna a escolha em
`decisoes_confirmadas`, separada do texto literal. O prompt prioriza esse campo.
Se a redação do modelo repetir o telefone divergente conhecido, a aplicação o
substitui pelo número adotado antes de apresentar e guardar a resposta.

O PDF e o arquivo extraído permanecem inalterados, preservando rastreabilidade.
A alternativa de deixar o modelo escolher entre os contatos foi rejeitada diante
da decisão explícita do autor. A escolha não resolve outras ambiguidades do manual.
