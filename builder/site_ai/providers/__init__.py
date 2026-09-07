# //// Neoffice — added file (no upstream equivalent): the site engine's LLM access.
"""One route for every model call of the site engine: upstream's litellm layer
(`builder.ai.llm`), configured by the Builder AI Provider rows.

The direct providers (OpenAI-compatible, Ollama, Codex CLI) lived here until
2026-09-07; a managed instance, an OpenRouter key or a self-hosted gateway now
configure ONE thing, the provider rows, and the editor agent and the site
engine read the same configuration. `get_provider()` keeps its signature for
the generators: a legacy provider name maps to the litellm route and the
`api_key` / `base_url` keyword arguments are ignored (the provider row holds
them)."""

from builder.site_ai.providers.base import BaseProvider, GenerationError
from builder.site_ai.providers.litellm_provider import LiteLLMProvider

PROVIDERS = {"litellm": LiteLLMProvider}
LEGACY_NAMES = ("openai", "ollama", "codex", "moonshot", "openrouter", "custom")


def get_provider(provider_name: str | None = None, model: str = None, **kwargs) -> BaseProvider:
    """A provider on the litellm route.

    `provider_name` is accepted for the callers written against the direct
    providers (a site_config `ai_provider` of "openai" or "ollama" still
    resolves); `model` is a Builder AI Model name (managed/kimi-k3) or a bare
    model id, which the provider resolves against the enabled rows."""
    kwargs.pop("api_key", None)
    kwargs.pop("base_url", None)
    kwargs.pop("reasoning_effort", None)
    return LiteLLMProvider(model=model, **kwargs)


__all__ = ["BaseProvider", "GenerationError", "LiteLLMProvider", "PROVIDERS", "LEGACY_NAMES", "get_provider"]
