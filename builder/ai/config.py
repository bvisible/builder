"""
AI Configuration Module
Manages AI provider settings, model configurations, and generation parameters.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import frappe


# Type definitions
ProviderType = Literal["openai", "ollama", "anthropic"]
ThemeType = Literal["modern", "neobrutalist", "glassmorphism", "minimal", "corporate", "creative"]
SiteType = Literal["single_page", "multi_page", "multi_page_auth", "ecommerce", "blog", "portfolio"]


@dataclass
class AIConfig:
    """Configuration for AI generation"""

    # Provider settings
    provider: ProviderType = "ollama"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Generation settings
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3

    # Default theme and site type
    default_theme: ThemeType = "modern"
    default_site_type: SiteType = "multi_page"

    # Timeouts (in seconds)
    request_timeout: int = 120
    connect_timeout: int = 30

    def __post_init__(self):
        """Set default model based on provider if not specified"""
        if not self.model:
            self.model = RECOMMENDED_MODELS.get(self.provider, {}).get("balanced")


# Recommended models for each provider
RECOMMENDED_MODELS = {
    "ollama": {
        "best_quality": "qwen2.5:32b",
        "balanced": "qwen2.5:7b",
        "fast": "qwen2.5:3b",
        "creative": "llama3.2:8b",
        "code": "deepseek-coder:6.7b",
    },
    "openai": {
        "best_quality": "gpt-4o",
        "balanced": "gpt-4o-mini",
        "fast": "gpt-3.5-turbo",
        "creative": "gpt-4o",
    },
    "anthropic": {
        "best_quality": "claude-3-opus-20240229",
        "balanced": "claude-3-sonnet-20240229",
        "fast": "claude-3-haiku-20240307",
    },
}

# Default Ollama configuration
DEFAULT_OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "qwen2.5:7b",
    "temperature": 0.7,
    "num_predict": 4096,
    "num_ctx": 8192,
}

# Default OpenAI configuration
DEFAULT_OPENAI_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 4096,
}


def get_ai_settings() -> AIConfig:
    """
    Get AI settings from Frappe configuration or AI Settings DocType.

    Priority:
    1. AI Settings DocType (if exists)
    2. Site config (common_site_config.json)
    3. Default values

    Returns:
        AIConfig: Configured AI settings
    """
    config = AIConfig()

    # Try to get from AI Settings DocType
    try:
        if frappe.db.exists("DocType", "AI Settings"):
            settings = frappe.get_single("AI Settings")

            config.provider = settings.get("default_provider") or config.provider
            config.temperature = settings.get("temperature") or config.temperature
            config.max_retries = settings.get("max_retries") or config.max_retries
            config.default_theme = settings.get("default_theme") or config.default_theme

            # Provider-specific settings
            if config.provider == "ollama":
                config.base_url = settings.get("ollama_base_url") or DEFAULT_OLLAMA_CONFIG["base_url"]
                config.model = settings.get("ollama_model") or DEFAULT_OLLAMA_CONFIG["model"]
            elif config.provider == "openai":
                config.api_key = settings.get("openai_api_key")
                config.model = settings.get("openai_model") or DEFAULT_OPENAI_CONFIG["model"]
            elif config.provider == "anthropic":
                config.api_key = settings.get("anthropic_api_key")
                config.model = settings.get("anthropic_model")

    except Exception:
        pass  # DocType doesn't exist yet, use defaults

    # Fallback to site config for API keys
    if not config.api_key:
        if config.provider == "openai":
            config.api_key = frappe.conf.get("openai_api_key")
        elif config.provider == "anthropic":
            config.api_key = frappe.conf.get("anthropic_api_key")

    # Ensure base_url for Ollama
    if config.provider == "ollama" and not config.base_url:
        config.base_url = frappe.conf.get("ollama_base_url", DEFAULT_OLLAMA_CONFIG["base_url"])

    return config


def get_model_for_task(task: str, provider: str = None) -> str:
    """
    Get the recommended model for a specific task.

    Args:
        task: Type of task ("quality", "balanced", "fast", "creative", "code")
        provider: Provider name (defaults to configured provider)

    Returns:
        str: Model name
    """
    if not provider:
        provider = get_ai_settings().provider

    models = RECOMMENDED_MODELS.get(provider, {})
    return models.get(task, models.get("balanced", ""))


def validate_provider_config(config: AIConfig) -> tuple[bool, str]:
    """
    Validate that the provider configuration is complete.

    Args:
        config: AI configuration to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if config.provider == "ollama":
        if not config.base_url:
            return False, "Ollama base_url is required"
        if not config.model:
            return False, "Ollama model is required"
        return True, ""

    elif config.provider == "openai":
        if not config.api_key:
            return False, "OpenAI API key is required. Set it in AI Settings or site config."
        if not config.model:
            return False, "OpenAI model is required"
        return True, ""

    elif config.provider == "anthropic":
        if not config.api_key:
            return False, "Anthropic API key is required. Set it in AI Settings or site config."
        if not config.model:
            return False, "Anthropic model is required"
        return True, ""

    return False, f"Unknown provider: {config.provider}"


# Export configuration for easy access
__all__ = [
    "AIConfig",
    "get_ai_settings",
    "get_model_for_task",
    "validate_provider_config",
    "RECOMMENDED_MODELS",
    "DEFAULT_OLLAMA_CONFIG",
    "DEFAULT_OPENAI_CONFIG",
    "ProviderType",
    "ThemeType",
    "SiteType",
]
