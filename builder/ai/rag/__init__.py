# RAG Module
# Retrieval-Augmented Generation for template examples

from builder.ai.rag.template_retriever import (
    TemplateRetriever,
    get_retriever,
    get_examples_for_section,
    get_builtin_examples,
)

__all__ = [
    "TemplateRetriever",
    "get_retriever",
    "get_examples_for_section",
    "get_builtin_examples",
]
