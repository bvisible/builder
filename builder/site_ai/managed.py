"""The managed AI provider: one Builder AI Provider row, kept in sync with
site_config on every migrate, so the upstream agent (litellm) runs on the
models the host operates for its customers without anyone entering a key.

The row is the only place the upstream engine reads a provider from; the key
is copied from site_config into the (encrypted) Password field because
`Builder AI Provider.resolved_key()` is what `builder.ai.llm.route` calls, and
`ai_setup_state` counts a provider as configured only when it carries a key.
Rotating the key in site_config is picked up by the next migrate, or by
calling `sync_managed_ai_provider()` directly.
"""

from __future__ import annotations

import json

import frappe

from builder.site_ai.capabilities import is_managed
from builder.site_ai.config import get_ai_settings

PROVIDER_NAME = "Managed"
ROUTE_PREFIX = "managed"
#: The host's own vision endpoint (Olares "nora": fast, multimodal, structured
#: output), used by the document understanding and the visual critique. Seeded
#: from site_config `nora_base_url` / `nora_api_key` so that those callers go
#: through the same litellm route as everything else.
NORA_PROVIDER_NAME = "Nora Vision"
NORA_ROUTE_PREFIX = "nora"


def nora_vision_model() -> str | None:
    """The Builder AI Model name of the host's vision endpoint, when seeded."""
    if not frappe.db.exists("DocType", "Builder AI Model"):
        return None
    rows = frappe.get_all(
        "Builder AI Model", filters={"provider": NORA_PROVIDER_NAME, "enabled": 1}, pluck="name", order_by="creation asc", limit=1
    )
    return rows[0] if rows else None


def sync_nora_vision_provider() -> str | None:
    """Create or refresh the host's vision provider row from site_config. No-op
    without `nora_base_url` and `nora_api_key`."""
    conf = frappe.conf
    base_url, api_key = conf.get("nora_base_url"), conf.get("nora_api_key")
    if not base_url or not api_key or not frappe.db.exists("DocType", "Builder AI Provider"):
        return None
    if frappe.db.exists("Builder AI Provider", NORA_PROVIDER_NAME):
        doc = frappe.get_doc("Builder AI Provider", NORA_PROVIDER_NAME)
    else:
        doc = frappe.new_doc("Builder AI Provider")
        doc.provider_name = NORA_PROVIDER_NAME
    doc.enabled = 1
    doc.route_prefix = NORA_ROUTE_PREFIX
    doc.litellm_provider = "openai"
    doc.api_base = base_url
    doc.api_key = api_key
    doc.flags.ignore_permissions = True
    doc.save()
    model_id = conf.get("nora_ocr_model") or conf.get("nora_model") or "nora"
    name = f"{NORA_ROUTE_PREFIX}/{model_id}"
    if not frappe.db.exists("Builder AI Model", name):
        frappe.get_doc(
            {"doctype": "Builder AI Model", "provider": NORA_PROVIDER_NAME, "enabled": 1, "model_id": model_id, "label": "Nora vision", "supports_vision": 1}
        ).insert(ignore_permissions=True)
    else:
        frappe.db.set_value("Builder AI Model", name, {"enabled": 1, "supports_vision": 1})
    for other in frappe.get_all("Builder AI Model", filters={"provider": NORA_PROVIDER_NAME, "name": ("!=", name)}, pluck="name"):
        frappe.db.set_value("Builder AI Model", other, "enabled", 0)
    frappe.db.commit()
    return NORA_PROVIDER_NAME


def managed_models() -> list[dict]:
    """The models the host exposes, in picker order: the chat model first (the
    picker starts on it), the heavy page model when it differs, then any extra
    model listed in site_config `nora_extra_models` (a list, or comma-separated).
    Labels are the model ids: the host decides what its customers see, the ids
    are not secret."""
    settings = get_ai_settings()
    extra = frappe.conf.get("nora_extra_models") or []
    if isinstance(extra, str):
        # `bench set-config` without --parse stores the JSON list as a string
        stripped = extra.strip()
        if stripped.startswith("["):
            try:
                extra = json.loads(stripped)
            except ValueError:
                extra = []
        else:
            extra = [m.strip() for m in stripped.split(",")]
    extra = [m for m in extra if isinstance(m, str) and m.strip()]
    seen: list[str] = []
    for model_id in [settings.model, settings.page_model, *extra]:
        if model_id and model_id not in seen:
            seen.append(model_id)
    return [{"model_id": model_id, "label": model_id, "supports_vision": 0} for model_id in seen]


def sync_managed_ai_provider() -> str | None:
    """Create or refresh the managed provider and its models. No-op unless the
    instance is managed and the provider table exists (a bench that has not
    migrated yet). Returns the provider name when something was synced."""
    if not is_managed() or not frappe.db.exists("DocType", "Builder AI Provider"):
        return None
    settings = get_ai_settings()
    if not settings.api_key or not settings.base_url:
        return None

    if frappe.db.exists("Builder AI Provider", PROVIDER_NAME):
        doc = frappe.get_doc("Builder AI Provider", PROVIDER_NAME)
    else:
        doc = frappe.new_doc("Builder AI Provider")
        doc.provider_name = PROVIDER_NAME
    doc.enabled = 1
    doc.route_prefix = ROUTE_PREFIX
    doc.litellm_provider = "openai"  # an OpenAI-compatible gateway
    doc.api_base = settings.base_url
    doc.api_key = settings.api_key
    doc.flags.ignore_permissions = True
    doc.save()

    wanted = {spec["model_id"]: spec for spec in managed_models()}
    # the picker lists models in creation order, so the rows are recreated whenever the
    # wanted order changed (a session keeps its selected_model as plain text, so a
    # recreated row loses nothing)
    existing = [
        name[len(ROUTE_PREFIX) + 1 :]
        for name in frappe.get_all("Builder AI Model", filters={"provider": PROVIDER_NAME}, pluck="name", order_by="creation asc")
    ]
    if [m for m in existing if m in wanted] != [m for m in wanted if m in existing]:
        for model_id in existing:
            frappe.delete_doc("Builder AI Model", f"{ROUTE_PREFIX}/{model_id}", ignore_permissions=True, force=True)
    for spec in wanted.values():
        name = f"{ROUTE_PREFIX}/{spec['model_id']}"
        if frappe.db.exists("Builder AI Model", name):
            frappe.db.set_value("Builder AI Model", name, {"enabled": 1, "label": spec["label"]})
            continue
        frappe.get_doc(
            {"doctype": "Builder AI Model", "provider": PROVIDER_NAME, "enabled": 1, **spec}
        ).insert(ignore_permissions=True)
    # a model the host no longer serves must not stay in the picker
    for name in frappe.get_all("Builder AI Model", filters={"provider": PROVIDER_NAME}, pluck="name"):
        model_id = name[len(ROUTE_PREFIX) + 1 :]
        if model_id not in wanted:
            frappe.db.set_value("Builder AI Model", name, "enabled", 0)
    # upstream's seed patch ships an OpenRouter shortlist; without a key those models
    # would sit in the picker and fail on first use. A disabled provider takes its
    # models with it (builder.ai.models.load_models); an operator can re-enable one.
    for other in frappe.get_all(
        "Builder AI Provider", filters={"name": ("not in", (PROVIDER_NAME, NORA_PROVIDER_NAME)), "enabled": 1}, pluck="name"
    ):
        frappe.db.set_value("Builder AI Provider", other, "enabled", 0)
    frappe.db.commit()
    sync_nora_vision_provider()
    from builder.ai.models import ModelRegistry

    ModelRegistry.clear_cache()
    return PROVIDER_NAME
