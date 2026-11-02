# Classificação de intenção — 02/11/2026

Validação local com `llama3.1:latest`, ID `46e0c10c039e`, via Ollama.
Substitui o controle lexical registrado em `2026-11-02.md`, sem alterar esse registro.

## Comportamento implementado

Antes do atendimento, o modelo recebe a mensagem e o texto dos dois últimos turnos,
limitado a 1.000 caracteres por mensagem. Não recebe ferramentas nessa chamada.
O Ollama recebe um schema JSON com enum `loja`, `fora`, `ambiguo`, e a aplicação
valida novamente a resposta. Isso restringe o formato, não garante acerto semântico.

`fora` recebe a resposta padrão da aplicação sem consultas comerciais.
`loja` e `ambiguo` seguem para o atendimento existente, inclusive esclarecimentos.
Aulas ou serviços não documentados permanecem assuntos da loja: ausência de fonte
não autoriza concluir que o assunto está fora do escopo ou inventar disponibilidade.

## Tentativas e ajustes preservados neste relato

A primeira versão pediu JSON somente por instrução. Programação e uma continuidade
retornaram formato inválido, tratado como erro sem consultar ferramentas comerciais.
Foi acrescentado o schema na requisição HTTP. Em seguida, uma pergunta de programação
foi classificada incorretamente como `loja`. Exemplos curtos de intenção foram
adicionados ao prompt. A tabela seguinte é da execução após esses ajustes.

## Classificações reais finais

Cada linha foi uma chamada real independente, sem histórico:

| Mensagem | JSON retornado |
| --- | --- |
| Me ensine uma receita de bolo de cenoura. | `{"escopo":"fora"}` |
| Me ajude a declarar imposto de renda. | `{"escopo":"fora"}` |
| Escreva um script Python para renomear arquivos. | `{"escopo":"fora"}` |
| Vocês oferecem aulas de violão? | `{"escopo":"loja"}` |
| Qual a previsão de entrega do pedido 1? | `{"escopo":"loja"}` |
| Quero um violão e uma receita de bolo. | `{"escopo":"loja"}` |
| E esse? | `{"escopo":"ambiguo"}` |

Essas chamadas verificam classificação; não comprovam respostas comerciais para aulas,
pedido ou pergunta mista. O prompt do atendimento orienta responder somente à parte
da loja, mas a redação de perguntas mistas ainda depende do modelo.

## Fluxo real em uma sessão

1. **Me ensine uma receita de bolo de cenoura.** Classificação `fora`, sem ferramentas
   comerciais. Resposta da aplicação:

   > Esse assunto fica fora do atendimento da Empório da Música. Posso ajudar com instrumentos musicais, produtos, pedidos e políticas da loja.

2. **Quanto custa o Takamine GD20?** Classificação `loja`.
   O atendimento chamou `buscar_produtos` com
   `{"nome":"Takamine GD20","disponibilidade":"disponiveis","pagina":"1"}`.
   Resposta do modelo, também apresentada:

   > O preço do Takamine GD20 é de R$ 2.199,00. Ele está disponível na loja e há 5 unidades em estoque. O preço no PIX é de R$ 2.089,05. Se você quiser saber mais sobre esse produto ou precisar de informações adicionais, sinta-se à vontade para perguntar!

3. **E no PIX?** Classificação `loja` usando o histórico. O atendimento chamou
   `consultar_politicas` com `{"pergunta":"E no PIX?"}` e apresentou:

   > A loja aceita pagamentos via PIX com 5% de desconto sobre o preço de tabela. Além disso, é possível combinar formas de pagamento, como PIX com cartão, para compras acima de R$ 2.000,00. No entanto, é importante notar que promoções não são cumulativas e o desconto de PIX não se aplica sobre preços já promocionais.

A classificação preservou o assunto comercial da continuidade, mas o atendimento
respondeu regra geral, sem repetir o preço do produto. Essa pendência anterior
permanece. O filtro `disponiveis` para produto específico também permanece pendente.

## Testes e limites

91 testes locais passaram. Os testes específicos verificam enum/formato, uso do
histórico sem mensagens de ferramentas, falha HTTP, repetição após falha,
redirecionamento e passagem de classificações `loja`/`ambiguo` ao atendimento.
Os testes anteriores de negócio isolam a classificação com retorno simulado `loja`.

A nova etapa custa uma chamada adicional ao modelo por mensagem. Classificações
erradas continuam possíveis; os exemplos foram usados também no ajuste do prompt,
não são benchmark independente. O histórico reduzido pode perder referências.
Os registros novos dos scripts de avaliação incluem `classificacao_escopo`,
separada de `resposta_bruta_modelo` do atendimento. Nenhuma avaliação anterior foi sobrescrita.
