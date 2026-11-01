# ADR 0009 — Trocas e devoluções somente informativas

- **Status:** aceita e implementada.
- **Data:** 01/11/2026.

## Contexto

O modelo ofereceu iniciar uma devolução, coletou informações e afirmou que uma compra
estava no prazo sem validação válida. A aplicação não executa devoluções. Dri confirmou
que o atendimento deve apenas informar as políticas. Esta decisão substitui a orientação
anterior de coletar dados ausentes para analisar devoluções descrita na ADR 0004.

## Decisão

O prompt proíbe oferecer abertura, andamento ou aprovação de troca e devolução.
Para perguntas reconhecidas, a aplicação consulta `consultar_politicas` e apresenta
as seções completas pertinentes, com aviso de atendimento informativo. Não usa datas
ou condições fornecidas espontaneamente para concluir elegibilidade. Orienta procurar
o atendimento da loja sem afirmar que encaminhou uma solicitação.

A conversa mantém apenas o assunto em memória para reconhecer continuidade. Na consulta
conjunta com pedido, a aplicação preserva autorização e apresenta status e política sem
pedir dados para abrir processo. Rastreio continua sendo consulta aos CSVs, sem ações.
As referências permanecem no registro técnico, com rodapé oculto na CLI.

## Alternativas e consequências

Alterar somente o prompt não protege contra a falha já observada. Implementar um fluxo
transacional ou um motor de elegibilidade está fora do escopo. A resposta controlada
preserva condições e exceções do PDF, mas é menos natural e pode repetir trechos.
O reconhecimento usa expressões textuais, não cobre toda paráfrase e pode confundir
assuntos. Perguntas mistas ainda dependem das ferramentas selecionadas pelo modelo.
Nenhum PDF ou CSV original foi alterado. Não há cálculo individual de prazos.

## Validação

65 testes automatizados passaram, incluindo continuidade com data e embalagem,
ausência de fonte, acessórios e bloqueio de aprovação indevida em consulta conjunta.
A execução reproduzível `python -m scripts.evaluate_returns` registrou a conversa em
[devolucao-informativa.json](../avaliacoes/pedidos/devolucao-informativa.json).

As duas primeiras mensagens consultaram a política por controle da aplicação,
sem chamada ao modelo (menos de 0,01 s cada). Na terceira, `llama3.1:latest` via Ollama
solicitou `consultar_pedido` com `codigo_rastreio: BRAB1234567BR`. A consulta autorizada
retornou pedido 1 entregue; a resposta apresentada foi informativa, sem abrir processo
ou solicitar dados adicionais (8,52 s). O registro separa a resposta bruta do modelo,
a resposta apresentada, as ferramentas e o contexto. Não se trata de evidência de
que o modelo sozinho resolveu os três turnos corretamente.
