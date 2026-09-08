# //// Neoffice — added file (no upstream equivalent): resolves the AI settings — site_config first
# //// (operator layer), then Builder Settings. builder/site_ai/** = the Neoffice AI site generator;
# //// frappe/builder ships no such module. First commit 563d9875 2026-02-01.
"""
AI Configuration Module

Resolution order (first non-empty wins):

1. site_config.json (frappe.conf) — the operator layer. A managed host
   pins its values here; anything set in site_config always wins.
2. Hardcoded DEFAULTS below.

The models themselves are routed by the Builder AI Provider rows (upstream's
AI settings); the keys here name the host's models and the endpoint the managed
sync copies into its provider row. (The Builder Settings custom fields
unpress_ai_* that used to sit between the two were dropped on 2026-09-08.)
"""

from dataclasses import dataclass
from typing import Literal, Optional

import frappe

ProviderType = Literal["litellm"]
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
# - pages on the "highspeed" serving of the same kimi-k2.7-code (2026-09-08):
#   Moonshot streams it at 900 to 1100 characters/s against 150 to 190 for the
#   standard serving. The model reasons for 5 k to 80 k characters before the
#   first line of a page, so the standard serving took 5 to 10 minutes per page
#   and lost three pages of five to the thinking budget; highspeed writes the
#   same page in 30 to 60 s. Same model, same output, higher per-token price
#   that the page volume (five to six pages per site) does not make felt.
# Note: an instance whose site_config pins openai_model overrides this
# default — the operator has to push the new value there too.
# The provider is always upstream's litellm route (Builder AI Provider rows);
# `base_url` and `api_key` are what the managed sync copies into that row.
DEFAULTS = {
    "provider": "litellm",
    "model": "kimi-k3",
    "page_model": "kimi-k2.7-code-highspeed",
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


def _studio_value(field: str) -> Optional[str]:
    """One field from the Builder Settings single (the Studio UI settings).

    Returns None when builder is not installed yet, the table is missing
    (pre-migrate), or the field is empty — resolution then falls through
    to the code defaults.
    """
    try:
        value = getattr(frappe.get_cached_doc("Builder Settings"), field, None)
        return value or None
    except Exception:
        return None


def _studio_api_key() -> Optional[str]:
    """The upstream Builder Settings ai_api_key (Password field, encrypted)."""
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
    Resolve AI settings: site_config.json > Builder Settings (Studio UI) > DEFAULTS.

    Keys read from frappe.conf (always win when set):
        openai_model       aliases: ollama_model
        openai_page_model  aliases: ollama_page_model
        openai_base_url    aliases: ollama_base_url, ollama_url
        openai_api_key     aliases: ollama_api_key
        ai_temperature
        ai_max_tokens
        ai_request_timeout
        ai_default_theme
        ai_default_site_type
        ai_output_language

    The upstream `ai_api_key` of Builder Settings is read as a last resort for
    the key (a self-hosted site that typed it there before the provider rows).
    """
    conf = frappe.conf

    # one route since 2026-09-07: the legacy `ai_provider` values ("openai",
    # "ollama", "codex") are accepted and mean the same thing
    provider = DEFAULTS["provider"]
    model = conf.get("openai_model") or conf.get("ollama_model") or DEFAULTS["model"]
    page_model = conf.get("openai_page_model") or conf.get("ollama_page_model") or DEFAULTS["page_model"]
    base_url = conf.get("openai_base_url") or conf.get("ollama_base_url") or conf.get("ollama_url") or DEFAULTS["base_url"]
    api_key = (
        conf.get("openai_api_key")
        or conf.get("ollama_api_key")
        or _studio_api_key()
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
        output_language=conf.get("ai_output_language") or DEFAULTS["output_language"],
    )


# "Managed" is DECLARED, never inferred.
#
# It first tried to guess — endpoint + credential pinned in site_config meant
# managed — and that was wrong: a self-hoster who puts their own key in
# site_config (a perfectly normal thing to do) got locked out of their own
# settings. Hosting is a commercial fact about the install, not a shape its
# configuration happens to have.
#
#     bench --site <site> set-config ai_managed 1
#
# Only a provider that actually runs the models for its customers sets it.
MANAGED_KEY = "ai_managed"


ASSISTANT_NAME = "Unpress AI"


def get_assistant_name() -> str:
    """The name the assistant speaks under, everywhere it is named.

    Resolution order: `assistant_name` in site_config (per site), the legacy
    `unpress_ai_name` key, an app hook `builder_assistant_name` (an edition or a
    host app declares its product name once, in its own hooks.py), then the
    default. The Studio boot, the agent prompts and the chat all read this one
    function, so the name cannot drift between surfaces.
    """
    conf = getattr(frappe.local, "conf", None) or {}
    name = conf.get("assistant_name") or conf.get("unpress_ai_name")
    if not name:
        try:
            hooked = frappe.get_hooks("builder_assistant_name") or []
        except Exception:
            hooked = []
        name = hooked[-1] if hooked else None
    return name or ASSISTANT_NAME


def get_image_settings() -> dict:
    """Image backend for this site: site_config > Builder Settings > defaults.

    Deliberately provider-agnostic and endpoint-less by default — this app is
    open source, so it must never ship someone's private GPU as a fallback.
    Any OpenAI-compatible /v1/images/generations host works (OpenAI itself, a
    local Ollama serving Flux, a gateway); ComfyUI has its own client.
    """
    conf = frappe.conf
    enabled = conf.get("image_generation_enabled")
    if enabled is None:
        enabled = _studio_value("unpress_ai_image_enabled")

    base_url = (
        conf.get("image_base_url")
        or conf.get("ollama_base_url")
        or conf.get("ollama_url")
        or _studio_value("unpress_ai_image_base_url")
    )
    api_key = conf.get("image_api_key") or conf.get("ollama_api_key")
    if not api_key:
        try:
            from frappe.utils.password import get_decrypted_password

            api_key = (
                get_decrypted_password(
                    "Builder Settings", "Builder Settings", "unpress_ai_image_api_key", raise_exception=False
                )
                or None
            )
        except Exception:
            api_key = None

    return {
        "enabled": bool(frappe.utils.cint(enabled)),
        # ComfyUI when configured (comfyui_url), otherwise the OpenAI-compatible
        # images endpoint below.
        "provider": conf.get("image_provider") or _studio_value("unpress_ai_image_provider") or "",
        "base_url": base_url,
        "api_key": api_key,
        "model": conf.get("image_model") or _studio_value("unpress_ai_image_model") or "gpt-image-1",
        "size": conf.get("image_size") or _studio_value("unpress_ai_image_size") or "1024x1024",
    }


__all__ = [
    "AIConfig",
    "DEFAULTS",
    "MANAGED_KEY",
    "THINK_LEVEL_MAP",
    "ProviderType",
    "SiteType",
    "ThemeType",
    "get_ai_settings",
    "get_assistant_name",
    "get_image_settings",
]
