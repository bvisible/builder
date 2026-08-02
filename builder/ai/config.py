"""
AI Configuration Module

Resolution order (first non-empty wins):

1. site_config.json (frappe.conf) — the operator layer. neoffice-devops
   pushes the canonical values to each instance via SiteConfigPhase;
   anything set there always wins.
2. Builder Settings — the Settings > AI tab, for instances the fleet does
   not pin. Added 2026-08-02; an instance whose site_config already covers
   everything behaves exactly as before.
3. The DEFAULTS below.

Local dev overrides: edit sites/<site>/site_config.json manually.
"""

from dataclasses import dataclass
from typing import Literal, Optional

import frappe


ProviderType = Literal["openai", "ollama"]
ThemeType = Literal["modern", "neobrutalist", "glassmorphism", "minimal", "corporate", "creative"]
SiteType = Literal["single_page", "multi_page", "multi_page_auth", "ecommerce", "blog", "portfolio"]


# Think level → per-model value. Kimi expects bool, GPT-OSS expects string,
# everything else defaults to bool.
THINK_LEVEL_MAP = {
    # K3 ships with reasoning ALWAYS ON (no instruct variant) — never send
    # think=False, whatever the configured level.
    "kimi-k3": {"low": True, "medium": True, "high": True},
    "kimi-k2.5": {"low": False, "medium": True, "high": True},
    "kimi-k2": {"low": False, "medium": True, "high": True},
    "glm": {"low": True, "medium": True, "high": True},
    "gpt-oss": {"low": "low", "medium": "medium", "high": "high"},
    "default": {"low": False, "medium": True, "high": True},
}


# Production defaults — decision validated by Jérémy on 2026-07-18 after the
# A/B on the dev16 bench (see Unpress/16-Design-Intelligence-Et-K3):
# - brief on kimi-k3: the quality step comes from the K3 brief + design
#   candidates; one call per site, so the 5× output pricing is negligible there.
# - pages on kimi-k2.7-code: ~90% of K3 page quality at ~1/7 the cost and
#   2.5× the speed (K3 pages: 47 min/91.8k tokens vs k2.7: 19 min/64k).
# Fleet rollout note: instances whose site_config pins openai_model override
# this default — SiteConfigPhase (neoffice-devops) must push kimi-k3 there.
DEFAULTS = {
    "provider": "openai",
    "model": "kimi-k3",
    "page_model": "kimi-k2.7-code",
    "base_url": "https://api.moonshot.ai/v1",
    "api_key": None,
    "temperature": 0.6,
    "max_tokens": 16384,
    # 1200s: kimi-k2.6 with thinking can exceed 15 min on dense pages
    "request_timeout": 1200,
    "connect_timeout": 30,
    "default_theme": "modern",
    "default_site_type": "multi_page",
    "output_language": "French",
    "brief_think_level": "high",
    "page_think_level": "high",
}


# Per-provider recommended models.
RECOMMENDED_MODELS = {
    "openai": {
        # K3 leads Frontend Code Arena and has native vision + 1M context;
        # kept out of "balanced"/"fast" for cost (5× K2.x on output tokens).
        "best_quality": "kimi-k3",
        "balanced": "kimi-k2.6",
        "fast": "kimi-k2.6",
        "creative": "kimi-k3",
    },
    "ollama": {
        "best_quality": "kimi-k2.6:cloud",
        "balanced": "kimi-k2.6:cloud",
        "fast": "qwen2.5:7b",
        "creative": "kimi-k2.6:cloud",
        "code": "deepseek-coder:6.7b",
    },
}


@dataclass
class AIConfig:
    """Runtime AI configuration, resolved from site_config.json."""

    provider: ProviderType = DEFAULTS["provider"]
    model: Optional[str] = DEFAULTS["model"]
    # Model used for page generation (code). Falls back to `model` when unset.
    page_model: Optional[str] = DEFAULTS["page_model"]
    api_key: Optional[str] = DEFAULTS["api_key"]
    base_url: Optional[str] = DEFAULTS["base_url"]

    temperature: float = DEFAULTS["temperature"]
    max_tokens: int = DEFAULTS["max_tokens"]
    max_retries: int = 3

    default_theme: ThemeType = DEFAULTS["default_theme"]
    default_site_type: SiteType = DEFAULTS["default_site_type"]
    output_language: str = DEFAULTS["output_language"]

    request_timeout: int = DEFAULTS["request_timeout"]
    connect_timeout: int = DEFAULTS["connect_timeout"]

    brief_think_level: str = DEFAULTS["brief_think_level"]
    page_think_level: str = DEFAULTS["page_think_level"]

    def get_think_value(self, level: str) -> bool | str:
        """Convert a think level to the value expected by the current model."""
        if not self.model:
            return THINK_LEVEL_MAP["default"].get(level, True)

        model_lower = self.model.lower()
        value = THINK_LEVEL_MAP["default"].get(level, True)
        for model_key, mapping in THINK_LEVEL_MAP.items():
            if model_key != "default" and model_key in model_lower:
                value = mapping.get(level, True)
                break
        # Moonshot *-code models (e.g. kimi-k2.7-code) REQUIRE thinking — a
        # request with thinking disabled returns a 400. Never send think=False
        # for them, whatever the configured think level resolves to.
        if value is False and "code" in model_lower:
            return True
        return value


def _settings_value(field: str) -> str | None:
    """One field from the Builder Settings single (the AI tab).

    Returns None when the table is missing (pre-migrate) or the field is
    empty — resolution then falls through to the code defaults.
    """
    try:
        return getattr(frappe.get_cached_doc("Builder Settings"), field, None) or None
    except Exception:
        return None


def _settings_api_key() -> str | None:
    """Builder Settings ai_api_key (Password field, encrypted)."""
    try:
        from frappe.utils.password import get_decrypted_password

        return (
            get_decrypted_password(
                "Builder Settings", "Builder Settings", "ai_api_key", raise_exception=False
            )
            or None
        )
    except Exception:
        return None


def get_ai_settings() -> AIConfig:
    """
    Resolve AI settings: site_config.json > Builder Settings (the AI tab) > defaults.

    site_config always wins, so an instance that pins everything there keeps
    behaving exactly as it did before this middle layer existed.

    Keys read from frappe.conf:
        ai_provider        (default: "openai")
        openai_model       aliases: ollama_model
        openai_base_url    aliases: ollama_base_url, ollama_url
        openai_api_key     aliases: ollama_api_key
        ai_temperature
        ai_max_tokens
        ai_request_timeout
        ai_default_theme
        ai_default_site_type
        ai_output_language
    """
    conf = frappe.conf

    provider = (
        conf.get("ai_provider")
        or conf.get("ollama_provider")
        or _settings_value("unpress_ai_provider")
        or DEFAULTS["provider"]
    )
    model = (
        conf.get("openai_model")
        or conf.get("ollama_model")
        or _settings_value("unpress_ai_brief_model")
        or DEFAULTS["model"]
    )
    page_model = (
        conf.get("openai_page_model")
        or conf.get("ollama_page_model")
        or _settings_value("unpress_ai_page_model")
        or DEFAULTS["page_model"]
    )
    base_url = (
        conf.get("openai_base_url")
        or conf.get("ollama_base_url")
        or conf.get("ollama_url")
        or _settings_value("unpress_ai_base_url")
        or DEFAULTS["base_url"]
    )
    api_key = (
        conf.get("openai_api_key")
        or conf.get("ollama_api_key")
        or _settings_api_key()
        or DEFAULTS["api_key"]
    )

    return AIConfig(
        provider=provider,
        model=model,
        page_model=page_model,
        base_url=base_url,
        api_key=api_key,
        temperature=float(conf.get("ai_temperature") or DEFAULTS["temperature"]),
        max_tokens=int(conf.get("ai_max_tokens") or DEFAULTS["max_tokens"]),
        request_timeout=int(conf.get("ai_request_timeout") or DEFAULTS["request_timeout"]),
        default_theme=conf.get("ai_default_theme") or DEFAULTS["default_theme"],
        default_site_type=conf.get("ai_default_site_type") or DEFAULTS["default_site_type"],
        output_language=(
            conf.get("ai_output_language")
            or _settings_value("unpress_ai_output_language")
            or DEFAULTS["output_language"]
        ),
    )


# site_config keys that silently win over anything chosen in the AI tab.
# Kept next to get_ai_settings so the two never drift.
PINNING_KEYS = {
    "provider": ("ai_provider", "ollama_provider"),
    "base_url": ("openai_base_url", "ollama_base_url", "ollama_url"),
    "api_key": ("openai_api_key", "ollama_api_key"),
    "model": ("openai_model", "ollama_model"),
    "output_language": ("ai_output_language",),
}


@frappe.whitelist()
def describe_resolution() -> dict:
    """Which AI settings are pinned in site_config, and to what.

    Neoffice instances are fleet-managed, so most of them ARE pinned. Without
    this the AI tab would show a provider the engine is not using — which is
    exactly what it did before. Never returns a secret: an API key is reported
    as pinned, not quoted.
    """
    frappe.only_for("System Manager")
    conf = frappe.conf
    pinned = {}
    for field, keys in PINNING_KEYS.items():
        for key in keys:
            if conf.get(key):
                pinned[field] = {
                    "key": key,
                    "value": "********" if "key" in field else str(conf.get(key)),
                }
                break

    settings = get_ai_settings()
    return {
        "pinned": pinned,
        "effective": {
            "provider": settings.provider,
            "base_url": settings.base_url,
            "model": settings.model,
        },
    }


ASSISTANT_NAME = "Unpress AI"


def get_assistant_name() -> str:
    """How the assistant introduces itself.

    The engine is Unpress AI wherever it runs; a site that wants to put its own
    product name in front of the user sets `unpress_ai_name` in site_config.
    """
    return frappe.conf.get("unpress_ai_name") or ASSISTANT_NAME


def get_model_for_task(task: str, provider: str = None) -> str:
    """Return the recommended model name for a given task + provider."""
    if not provider:
        provider = get_ai_settings().provider
    models = RECOMMENDED_MODELS.get(provider, {})
    return models.get(task, models.get("balanced", ""))


def validate_provider_config(config: AIConfig) -> tuple[bool, str]:
    """Ensure the resolved config has enough info to call the provider."""
    if config.provider == "openai":
        if not config.api_key:
            return False, "openai_api_key missing from site_config.json"
        if not config.model:
            return False, "openai_model missing from site_config.json"
        return True, ""

    if config.provider == "ollama":
        if not config.base_url:
            return False, "ollama_base_url missing from site_config.json"
        if not config.model:
            return False, "ollama_model missing from site_config.json"
        return True, ""

    return False, f"Unknown provider: {config.provider}"


__all__ = [
    "AIConfig",
    "DEFAULTS",
    "RECOMMENDED_MODELS",
    "THINK_LEVEL_MAP",
    "ProviderType",
    "SiteType",
    "ThemeType",
    "get_ai_settings",
    "get_model_for_task",
    "validate_provider_config",
]
