"""Orçamento conservador antes do envio; tokens observados vêm do Ollama."""

import json


CONTEXT_TOKENS = 12288
OUTPUT_TOKENS = 768
TEMPLATE_MARGIN = 512


def input_bound(messages, tools):
    # BPE trabalha sobre bytes; usamos 1 token por byte UTF-8 mais margem para
    # o template. Superestima fortemente o português normal; não é tokenizador.
    serialized = json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False)
    return len(serialized.encode("utf-8")) + TEMPLATE_MARGIN


def fits_context(messages, tools):
    return input_bound(messages, tools) + OUTPUT_TOKENS <= CONTEXT_TOKENS
