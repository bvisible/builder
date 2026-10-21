# //// Neoffice — added file (no upstream equivalent): the managed AI provider, kept in sync with site_config.
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
#: The same local model under other route names, so it can read the pages it wrote (the judge is never
#: the model that wrote a page: visual_check.judge_model skips a route equal to the page model), and so a
#: judge can run on the reasoning lane, which answers a structured review 2 to 3 times faster than the
#: plain lane and refuses fewer good pages (Obsidian Neoffice/Builder/Projet-Builder-v15/14, section 8).
#: (provider, route prefix, site_config key of the lane's URL, label), the reasoning lane first.
NORA_JUDGE_LANES = (
    ("Nora Think", "nora-think", "nora_thinking_url", "Nora (reasoning judge)"),
    ("Nora Judge", "nora-judge", "nora_base_url", "Nora (judge)"),
)
#: Providers that read documents and pages for the host and are not conversation models: the model picker
#: does not offer them (builder.ai.models.is_host_vision).
HOST_ONLY_PROVIDERS = (NORA_PROVIDER_NAME, *(lane[0] for lane in NORA_JUDGE_LANES))


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


def sync_nora_judge_providers() -> list[str]:
    """Create or refresh one provider row per judge lane whose URL the host configured, and switch off the rows
    of a lane it no longer has. No-op without `nora_api_key`. Returns the providers that are on."""
    conf = frappe.conf
    api_key = conf.get("nora_api_key")
    if not frappe.db.exists("DocType", "Builder AI Provider"):
        return []
    model_id = conf.get("nora_ocr_model") or conf.get("nora_model") or "nora"
    on = []
    for provider, prefix, url_key, label in NORA_JUDGE_LANES:
        url = conf.get(url_key)
        exists = frappe.db.exists("Builder AI Provider", provider)
        if not url or not api_key:
            if exists:
                frappe.db.set_value("Builder AI Provider", provider, "enabled", 0)
            continue
        if exists:
            doc = frappe.get_doc("Builder AI Provider", provider)
        else:
            doc = frappe.new_doc("Builder AI Provider")
            doc.provider_name = provider
        doc.enabled = 1
        doc.route_prefix = prefix
        doc.litellm_provider = "openai"
        doc.api_base = url
        doc.api_key = api_key
        doc.flags.ignore_permissions = True
        doc.save()
        name = f"{prefix}/{model_id}"
        if frappe.db.exists("Builder AI Model", name):
            frappe.db.set_value("Builder AI Model", name, {"enabled": 1, "supports_vision": 1})
        else:
            frappe.get_doc(
                {"doctype": "Builder AI Model", "provider": provider, "enabled": 1, "model_id": model_id, "label": label, "supports_vision": 1}
            ).insert(ignore_permissions=True)
        for other in frappe.get_all("Builder AI Model", filters={"provider": provider, "name": ("!=", name)}, pluck="name"):
            frappe.db.set_value("Builder AI Model", other, "enabled", 0)
        on.append(provider)
    frappe.db.commit()
    return on


def nora_model_id() -> str:
    """The id of the host's own model, the same for its vision endpoint and its two judge lanes."""
    conf = frappe.conf
    return conf.get("nora_ocr_model") or conf.get("nora_model") or "nora"


# //// Neoffice — the host's own models on every instance that holds its endpoint and key, managed or not (2026-10-21).
# //// The three providers were only created by sync_managed_ai_provider, which does nothing on an instance without
# //// `ai_managed`: 9 of the 11 client instances had no `nora/…` route at all, so nothing could write their sites with
# //// the local model, and a host that wants it everywhere had to turn the whole managed mode on (hidden model picker,
# //// fewer agent tools, the other providers switched off). This creates only the three Nora providers and touches nothing else.
def sync_nora_providers() -> list[str]:
    """Create or refresh the host's own providers (vision, reasoning lane, plain lane) when site_config holds its endpoint
    (`nora_base_url`) and key (`nora_api_key`), whether or not the instance is managed. Run on every migrate (key rotation
    and an endpoint that moved are picked up) and by the patch that names the local model. Returns the providers that are on."""
    conf = frappe.conf
    if not conf.get("nora_base_url") or not conf.get("nora_api_key"):
        return []
    if not frappe.db.exists("DocType", "Builder AI Provider"):
        return []
    on = []
    if sync_nora_vision_provider():
        on.append(NORA_PROVIDER_NAME)
    on.extend(sync_nora_judge_providers())
    from builder.ai.models import ModelRegistry

    ModelRegistry.clear_cache()
    return on


def nora_judge_models() -> list[str]:
    """The Builder AI Model names of the judge lanes that are on, the reasoning lane first."""
    if not frappe.db.exists("DocType", "Builder AI Model"):
        return []
    found = []
    for provider, _prefix, _url_key, _label in NORA_JUDGE_LANES:
        if not frappe.db.get_value("Builder AI Provider", provider, "enabled"):
            continue
        found += frappe.get_all(
            "Builder AI Model", filters={"provider": provider, "enabled": 1}, pluck="name", order_by="creation asc", limit=1
        )
    return found


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
    # an id the endpoint cannot serve is incoherent by construction (a gpt-4o left in
    # site_config from before Moonshot failed every brief in silence on a reseller site,
    # neoffice-maintenance #274): it is dropped here, and the code default takes
    # its place when nothing is left
    coherent = [m for m in seen if _served_by(settings.base_url, m)]
    for dropped in [m for m in seen if m not in coherent]:
        frappe.logger("builder").warning(f"managed model {dropped!r} is not served by {settings.base_url}: ignored")
    if not coherent:
        from builder.site_ai.config import DEFAULTS

        coherent = [DEFAULTS["model"]]
    # Kimi K2.7 reads images (verified 2026-09-08 on both servings: a generated photo
    # described in 6 s): the brief's logo analysis runs on it, no separate vision row needed
    # //// Neoffice — and so does K3 (Moonshot's 2026-07 flagship is multimodal): registered without
    # //// the flag, it was handed the logo and the screenshots with the pictures silently dropped
    # //// (_format_messages keeps images for vision models only), 2026-09-16.
    return [{"model_id": model_id, "label": model_id, "supports_vision": 1 if model_id.lower().startswith(("kimi-k2.7", "kimi-k3")) else 0} for model_id in coherent]


def _served_by(base_url: str | None, model_id: str) -> bool:
    """Moonshot serves kimi-* and moonshot-* ids only; any other gateway is trusted."""
    if "moonshot" not in (base_url or "").lower():
        return True
    return model_id.lower().startswith(("kimi", "moonshot"))


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
            frappe.db.set_value("Builder AI Model", name, {"enabled": 1, "label": spec["label"], "supports_vision": spec.get("supports_vision", 0)})
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
        "Builder AI Provider", filters={"name": ("not in", (PROVIDER_NAME, *HOST_ONLY_PROVIDERS)), "enabled": 1}, pluck="name"
    ):
        frappe.db.set_value("Builder AI Provider", other, "enabled", 0)
    frappe.db.commit()
    sync_nora_vision_provider()
    sync_nora_judge_providers()
    from builder.ai.models import ModelRegistry

    ModelRegistry.clear_cache()
    return PROVIDER_NAME
