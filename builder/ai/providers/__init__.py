#//// Neoffice — added file (no upstream equivalent): provider registry (OpenAI, Ollama, Codex CLI).
#//// builder/ai/** = the Neoffice AI site generator; frappe/builder ships no such module. First commit
#//// 563d9875 2026-02-01.
# AI Providers Module
# Supports multiple AI providers: OpenAI, Ollama, Anthropic

from builder.ai.providers.base import BaseProvider
from builder.ai.providers.codex_provider import CodexProvider
from builder.ai.providers.openai_provider import OpenAIProvider
from builder.ai.providers.ollama_provider import OllamaProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    # local Codex CLI driven by a ChatGPT plan (self-host / dogfooding)
    "codex": CodexProvider,
}


def get_provider(provider_name: str, model: str = None, **kwargs) -> BaseProvider:
    """
    Factory function to get the appropriate AI provider

    Args:
        provider_name: Name of the provider ("openai", "ollama")
        model: Optional model name override
        **kwargs: Additional provider-specific configuration

    Returns:
        BaseProvider: Configured provider instance

    Raises:
        ValueError: If provider_name is not supported
    """
    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Supported providers: {list(PROVIDERS.keys())}"
        )

    provider_class = PROVIDERS[provider_name]

    # The reasoning effort is a site-wide setting, and every call site would
    # otherwise have to remember to thread it through. Read it here once; a
    # caller that passes its own still wins.
    if provider_name == "codex" and "reasoning_effort" not in kwargs:
        try:
            from builder.ai.config import get_ai_settings

            kwargs["reasoning_effort"] = get_ai_settings().reasoning_effort
        except Exception:
            pass

    return provider_class(model=model, **kwargs)


__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "get_provider",
    "PROVIDERS",
]
