# ADR 0001 — Arquitetura inicial

- **Status:** aceita como arquitetura inicial; validações pendentes registradas abaixo.
- **Data:** 31/10/2026.

## Contexto

O desafio da Artefact exige um protótipo de agente de atendimento por texto para a loja fictícia Empório da Música. Python é a linguagem obrigatória; modelo, provedor, abordagem, interface e persistência são escolhas livres, justificadas no README.

Os materiais disponíveis são seis CSVs estáticos e um PDF de políticas. O agente precisa distinguir consultas operacionais de respostas fundamentadas nas políticas, reconhecer dados ausentes e preservar os dados de clientes.

## Decisões confirmadas

1. **Python como linguagem principal**, usando inicialmente a instalação 3.12.9 disponível no ambiente.
2. **Interface de linha de comando (CLI)** para priorizar o atendimento e sua validação dentro do prazo.
3. **Consultas diretas aos CSVs por funções Python**, sem banco de dados nesta arquitetura inicial. Os arquivos originais serão tratados como fontes estáticas, sem alterações para simular operações reais.
4. **Chamadas de ferramentas pelo modelo, com execução controlada pela aplicação.** O modelo solicita uma função; a aplicação valida o nome e os argumentos, executa somente funções permitidas e devolve o resultado ao modelo. Consultas de pedidos devem respeitar a identidade da sessão, sem permitir que o modelo escolha livremente outro cliente.
5. **Histórico em memória durante a sessão**, sem persistência entre execuções nesta etapa. A política para limitar o histórico ainda será definida.
6. **`llama3.1:latest` via Ollama local como escolha inicial.** O modelo instalado declarou suporte a ferramentas e completou o ciclo básico no experimento. A escolha poderá ser revista se os testes completos mostrarem qualidade ou desempenho insuficientes.

O fluxo inicial será: mensagem na CLI → modelo com instruções e ferramentas → validação e execução da consulta pela aplicação → resultado da ferramenta → resposta ao cliente. Esse fluxo descreve a arquitetura aceita, não uma implementação já concluída.

## Evidências da escolha inicial do modelo

O experimento foi executado com Ollama 0.40.13 e `llama3.1:latest`, ID `46e0c10c039e`, 8B, quantização Q4_K_M. A tag `latest` é mutável; o ID registra o artefato avaliado.

O ambiente possui Intel Core i7-13700, aproximadamente 31,7 GiB de RAM utilizável e NVIDIA RTX 3070 com 8 GiB de VRAM. O teste usou contexto de 4.096 tokens, temperatura 0 e limite de 512 tokens gerados por chamada. Foi executado diretamente no interpretador, com a biblioteca padrão do Python, sem script versionado.

Em três sessões independentes, foi enviada a pergunta “Quanto custa o Takamine GD20 e ele está disponível?”. A descrição da ferramenta informava explicitamente o mapeamento para o produto 95. Em todos os casos, o modelo solicitou `consultar_produto` com `{"product_id": 95}`; a aplicação validou a chamada e devolveu o resultado antes de solicitar a resposta final.

| Cenário | Retorno da aplicação | Resultado | Tempo aproximado |
| --- | --- | --- | --- |
| Consulta real ao CSV | R$ 2.199,00, estoque 5, status `active` | Respondeu preço e estoque corretamente | 43 s, incluindo cerca de 22 s de carregamento |
| Retorno simulado identificado como teste | R$ 1.234,56 e estoque zero | Usou os dados simulados e informou indisponibilidade, mas omitiu que eram dados de teste | 5,3 s |
| Produto não encontrado, em retorno simulado | `found: false`, sem preço ou estoque | Reconheceu a ausência e não inventou os valores, mas também omitiu a identificação da simulação | 5,4 s |

O ciclo básico de ferramentas foi validado, mas a exigência de identificar a simulação falhou. Houve apenas uma execução por cenário; os tempos não constituem um benchmark e não demonstram consistência. O experimento não avaliou busca por nome, promoções, políticas, identidade de clientes, conversas longas ou tratamento amplo de falhas.

## Alternativas consideradas

| Alternativa | Avaliação nesta etapa |
| --- | --- |
| `phi3:latest` já instalado | Declara apenas geração de texto; não foi escolhido para o teste de ferramentas |
| Modelo via API externa | Alternativa se o modelo local não atender; exigiria avaliar custo, credenciais e envio de dados |
| Framework de agentes | Pode ajudar em fluxos maiores, mas acrescentaria abstrações e dependências antes de uma necessidade demonstrada |
| Banco de dados ou agente de SQL | Não necessário inicialmente para o volume estático fornecido; consultas Python são mais diretas para este escopo |
| Interface web, API ou notebook | Permitidos pelo desafio; a CLI reduz o trabalho de interface no prazo disponível |
| Persistência de conversas | Pode ser útil futuramente, mas não é necessária para manter o contexto de uma única sessão |
| PDF completo no contexto ou recuperação de trechos | Alternativas ainda em avaliação; nenhuma estratégia de consulta às políticas foi confirmada |

## Consequências e limitações

- O fluxo explícito facilita compreender e testar consultas separadamente do comportamento do modelo.
- A CLI e o histórico em memória reduzem o escopo, mas não oferecem interface web nem continuidade após encerrar a sessão.
- Os dados não se atualizam por um sistema externo. O agente não deve apresentar a base como estoque ou pedidos em tempo real.
- A execução local depende do hardware, do contexto configurado e do modelo instalado. A distribuição da execução entre CPU e GPU ainda não foi medida.
- O modelo pode ignorar instruções, como ocorreu com os marcadores de simulação. Validação de ferramentas e restrições de acesso precisam estar na aplicação, acompanhadas de testes reais de comportamento.
- Os pedidos não informam data efetiva de recebimento nem canal de compra. A previsão de entrega não pode ser usada como recebimento para concluir elegibilidade para devolução.
- Há inconsistências no catálogo e ambiguidades no manual. As interpretações adotadas devem ser documentadas sem transformar suposições em fatos.
- O protótipo não deve afirmar que executou reservas, cancelamentos ou encaminhamentos sem uma implementação que realize essas ações.

## Decisões ainda pendentes

- **Consulta às políticas:** avaliar como extrair e disponibilizar o conteúdo relevante. Não foi medido se o PDF completo cabe no contexto de 4.096 tokens junto das instruções, ferramentas, resultados e histórico. Nem o tamanho máximo declarado pelo modelo nem o teste realizado comprovam essa capacidade.
- Definir as ferramentas, seus contratos, filtros de busca, respostas de erro e limites de chamadas por turno.
- Definir identificação do cliente na sessão e documentar as limitações de autenticação do protótipo.
- Definir limites do histórico, orçamento de contexto, timeouts e tratamento de indisponibilidade do Ollama.
- Validar o modelo em português nos cenários completos, incluindo acesso a pedidos, políticas e perguntas fora do escopo.
- Validar os cálculos monetários também nos cenários completos com o modelo;
  o módulo de catálogo já usa `Decimal` e `ROUND_HALF_UP` para centavos.
- Documentar interpretações para disponibilidade por status, parcelamento, contatos divergentes e frete de exatamente R$ 500.
- Definir dependências e comandos reproduzíveis, implementar testes das funções e registrar de três a cinco conversas reais.

## Uso de IA neste registro

A primeira etapa de implementação adicionou `emporio/catalog.py` e 12 testes
das funções. Disponibilidade exige `active` e estoque positivo. Promoções
dependem de `is_active`; na eventualidade de múltiplas promoções ativas,
o protótipo escolhe a maior, sem cumulatividade. Essa suposição complementa
o manual e está documentada no README. O desconto PIX não se acumula com
promoção. A busca por teto usa o preço promocional, sem PIX. A estratégia
de políticas e a integração com o modelo permanecem pendentes.

O Codex apoiou a redação desta ADR e sua integração ao README, com base nas escolhas confirmadas pelo autor e nos testes reais realizados durante a sessão de desenvolvimento.
