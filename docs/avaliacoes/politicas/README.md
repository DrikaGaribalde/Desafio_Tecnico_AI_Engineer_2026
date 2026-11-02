# Avaliação real — integração das políticas

Modelo `llama3.1:latest`, ID `46e0c10c039e`, Ollama 0.40.13, temperatura 0,
contexto configurado de **8.192 tokens** e limite de 768 tokens de saída.
Ollama informou execução 100% GPU, com aproximadamente 5,8 GB para o modelo carregado.
Os registros incluem horário UTC da execução, ferramentas, argumentos, trechos,
resposta bruta do modelo, rodapé acrescentado pela aplicação, tokens e tempo.

## Rodada final: `rodada-05`

| Cenário | Recuperação | Resultado observado | Avaliação | Tempo |
| --- | --- | --- | --- | --- |
| [Sábado](rodada-05/01-sabado.md) | Seção 2, página 2 | Respondeu 09h–13h; o trecho também continha feriados e datas especiais, mas o modelo não repetiu essas exceções | Parcial: horário regular correto, omissão de condições | 5,75 s |
| [Arrependimento online](rodada-05/02-arrependimento.md) | Seção 4.1, página 4 | Explicou sete dias após recebimento, embalagem, ausência de uso, acessórios/manuais, reembolso e frete; pediu recebimento e estado do produto | Aprovado na informação geral, sem verificação de elegibilidade real | 8,39 s |
| [Parcelamento](rodada-05/03-parcelamento.md) | Seções 3.1 e 3, página 3 | Apresentou faixas e destacou divergência da tabela geral, pedindo confirmação | Aprovado com ressalva: a expressão relativa a R$ 50 foi reproduzida, não resolvida | 8,84 s |
| [Promoção + PIX](rodada-05/04-pix-promocao.md) | Seção 6.2, página 6 | Respondeu que não acumulam | Aprovado | 6,15 s |
| [Frete exatamente R$ 500](rodada-05/05-frete-500.md) | Seção 5.1, página 4 | Reconheceu falta de regra para igualdade e pediu confirmação; não afirmou valor | Aprovado | 6,20 s |
| [Produto e política](rodada-05/06-produto-e-politica.md) | `buscar_produtos` + seção 6.2; continuidade com 4.1 | Informou R$ 323,10, 10%, vedou cumulatividade e respondeu à continuidade sobre devolução | Parcial: as duas ferramentas funcionaram, mas omitiu o preço original R$ 359,00 e na continuidade usou formulação pouco natural (“lembre-se de perguntar”) | 6,92 s + 7,48 s |

A classificação distingue recuperação e fidelidade da resposta. Não declarar seis
aprovações integrais: instruções e fontes corretas não eliminam omissões do modelo.
O rodapé de referências é gerado pela aplicação porque o modelo omitiu citações.
Ele mostra o que foi consultado; não certifica cada frase gerada.

## Verificação de contexto

Os 14 envios da rodada final incluíram instruções, os dois contratos de ferramentas,
mensagens e, quando presentes, resultados e histórico. São sete turnos em seis cenários.

| Cenário | Maior prompt informado pelo Ollama | Maior estimativa conservadora de entrada |
| --- | ---: | ---: |
| Sábado | 1.020 | 5.282 |
| Arrependimento | 1.032 | 5.602 |
| Parcelamento | 1.132 | 6.001 |
| Promoção + PIX | 1.025 | 5.499 |
| Frete R$ 500 | 1.033 | 5.373 |
| Produto + política, primeiro turno | 1.085 | 6.070 |
| Continuidade | 1.553 | 6.469 |

O maior prompt observado mais a reserva máxima de saída foi **1.553 + 768 = 2.321**,
abaixo de 8.192. A maior estimativa antes do envio mais reserva foi
**6.469 + 768 = 7.237**, também abaixo do limite. Os resultados das ferramentas por
turno ficaram entre aproximadamente 675 e 1.296 caracteres, com seções completas.

Há uma limitação importante: na primeira chamada da continuidade foram enviadas cinco
mensagens do turno anterior; após recuperar a nova seção, a estimativa ultrapassaria
o orçamento conservador. A aplicação removeu esse turno inteiro antes da segunda
chamada. As métricas mostram `mensagens_historico: 5` e depois `0`. Portanto, **os trechos
enviados couberam, mas não preservamos todo o histórico junto das novas fontes**.
Essa política pode perder referências e pedir esclarecimento em outras conversas.

A estimativa usa bytes UTF-8 do JSON completo mais 512 de margem para template,
reservando 768 para saída. É uma aproximação conservadora para esta configuração,
não um tokenizador nem prova geral para templates futuros. `prompt_eval_count` é a
medição devolvida pelo Ollama; não é uma contagem independente do prompt renderizado.
Não concluímos que o PDF inteiro cabe no contexto.

## Evolução e falhas preservadas

- `rodada-01`: PIX + promoção foi respondido incorretamente; no cenário misto o modelo
  chegou a oferecer preço PIX alternativo calculado por ele. Também omitiu referências.
- `rodada-02`: reduzida a confusão entre meios de pagamento e descontos; referências
  passaram a ser acrescentadas pela aplicação. A busca ainda trazia seções irrelevantes.
- `rodada-03`: melhorado o ranking; o modelo ainda importou restrições de troca para
  arrependimento. Reforçar apenas o prompt não resolveu consistentemente esse problema.
- `rodada-04`: removida a associação automática entre 4.1 e 4.4. As exceções de troca
  continuam recuperadas quando se pergunta sobre troca. A regra de arrependimento
  passou a vir sem restrições de outra modalidade.
- `rodada-05`: JSON de ferramenta compactado, sem perda de conteúdo; repetidos todos
  os cenários. São os resultados finais descritos acima.

Os diretórios são registros de execuções reais em versões sucessivas do código,
sem reescrever as respostas anteriores. A comparação não é um benchmark e não mede
consistência estatística; houve ajustes após observar falhas nesses mesmos cenários.

## Regressão e testes das funções

34 testes automatizados passaram, incluindo os testes anteriores de produtos,
recuperação por assunto, condições/exceções, ausência de informação, hash divergente,
argumentos inválidos, recusa por contexto e remoção de histórico sem cortar fontes.
Esses testes usam dados reais e fontes sintéticas e não precisam do Ollama.

A regressão real do catálogo foi registrada em `regressao-produtos/` e repetida após
compactar o JSON em `regressao-produtos-final/`. Os exemplos originais em
`docs/avaliacoes/catalogo-historico/` foram preservados. A primeira regressão confirmou filtros e preços,
mas o modelo descreveu dez resultados como se fossem todos, apesar de haver doze.
Foi adicionado um aviso explícito de lista parcial ao retorno da ferramenta.

Na regressão final, preços, filtros, falta de estoque, promoção e continuidade
voltaram a usar os dados corretos. A lista informou doze correspondências, apresentou
dez e avisou que existem mais opções. Os turnos levaram aproximadamente 5,3 a 8,7 s.
Na continuidade de produtos, quatro mensagens históricas foram preservadas nas duas
chamadas. A maior estimativa nessa regressão foi 7.307; com a reserva de 768,
totalizou 8.075, abaixo de 8.192. O modelo ainda omite a ressalva de base estática
e usa o filtro de disponíveis na continuidade, mesmo para consulta específica.

A CLI também foi executada com pergunta real sobre sábado e comando `sair`;
respondeu 09h–13h com rodapé da seção 2, página 2, e encerrou normalmente.

## Reproduzir

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -X utf8 -m scripts.evaluate_policies --rodada rodada-06
py -3.12 -X utf8 -m scripts.evaluate_catalog --saida docs/avaliacoes/politicas/nova-regressao
```

Use um nome novo para políticas: o script não sobrescreve rodadas existentes.
`rodada-06` e `nova-regressao` são nomes sugeridos para a próxima execução; a rodada
final registrada foi `rodada-05` e a regressão final usou `regressao-produtos-final`.
As políticas usam `data/politicas_secoes.json`, cuja integridade em relação à fonte
é verificada pelo hash do PDF. Somente a regeneração exige `pdftotext` no PATH:

```powershell
py -3.12 -m scripts.extract_policies
```

## Limitações

Busca textual não compreende todas as paráfrases ou perguntas amplas; a seleção é
heurística e uma correspondência não garante suficiência semântica. Não encontrar
trecho não prova ausência da regra em todo o manual. As ressalvas precisam de revisão
quando a fonte mudar. Garantia, ausência de informação e exceções de troca foram
verificadas nas funções, mas não receberam uma bateria conversacional completa.
As omissões de feriados, de preço original e a perda de histórico permanecem visíveis.
Pedidos, autenticação e ações comerciais reais continuam fora do escopo implementado.
