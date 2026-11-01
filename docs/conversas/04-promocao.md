# Conversa real — 04-promocao

Execução real com llama3.1:latest via Ollama; dados estáticos do desafio.

**Cliente:** O Kalani KAL-700T tem promoção ativa? Qual é o preço?

Ferramentas e resultados:

```json
[
  {
    "ferramenta": "buscar_produtos",
    "argumentos": {
      "disponibilidade": "todas",
      "nome": "Kalani KAL-700T"
    },
    "resultado": {
      "fonte": "CSV estático do desafio",
      "total": 1,
      "limitado": false,
      "produtos": [
        {
          "nome": "Kalani KAL-700T Tenor Natural",
          "categoria": "Ukuleles",
          "preco_original_brl": "359.00",
          "desconto_percentual": "10",
          "preco_final_brl": "323.10",
          "disponibilidade": "disponível",
          "disponivel_para_compra": true,
          "estoque": 11
        }
      ]
    }
  }
]
```

**Agente:** Sim, o Kalani KAL-700T tem promoção ativa. O preço original é de R$ 359,00, com desconto de 10%, o preço final é de R$ 323,10. O produto está disponível para compra.

Tempo do turno: 5.8 s.
