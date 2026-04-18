"""
Drop the legacy "AI Settings" (and "Builder AI Settings") DocType.

Before deletion, migrate any populated values into site_config.json so
on-premise instances that never had the keys pushed by neoffice-devops
keep working. Only non-empty values from the DocType overwrite absent
site_config keys — if the key already exists in site_config, we keep it.
"""

import frappe
from frappe.installer import update_site_config


# Map DocType field → site_config key. Password fields fetched via get_password.
FIELD_TO_CONF = {
    "default_provider": ("ai_provider", False),
    "ollama_base_url": ("ollama_base_url", False),
    "ollama_model": ("ollama_model", False),
    "ollama_api_key": ("ollama_api_key", True),
    "ollama_num_ctx": ("ollama_num_ctx", False),
    "ollama_timeout": ("ollama_timeout", False),
    "openai_api_key": ("openai_api_key", True),
    "openai_model": ("openai_model", False),
    "temperature": ("ai_temperature", False),
    "image_generation_enabled": ("image_generation_enabled", False),
    "image_model": ("image_model", False),
    "image_size": ("image_size", False),
    "default_theme": ("ai_default_theme", False),
    "default_site_type": ("ai_default_site_type", False),
    "output_language": ("ai_output_language", False),
}


def _migrate_doctype(doctype_name: str) -> None:
    if not frappe.db.exists("DocType", doctype_name):
        return

    # We read field values directly via DB — not via frappe.get_single —
    # because the Python controller module has already been deleted when
    # this patch runs, which would raise ImportError.
    for field, (conf_key, is_password) in FIELD_TO_CONF.items():
        if frappe.conf.get(conf_key):
            continue  # site_config already has it — respect existing value

        value = frappe.db.get_single_value(doctype_name, field)

        if is_password and value:
            try:
                value = frappe.utils.password.get_decrypted_password(
                    doctype_name, doctype_name, field, raise_exception=False
                )
            except Exception:
                value = None

        if value in (None, ""):
            continue

        try:
            update_site_config(conf_key, value)
        except Exception as e:
            frappe.log_error(
                f"AI Settings migration: failed to set {conf_key}",
                str(e),
            )


def execute():
    for name in ("AI Settings", "Builder AI Settings"):
        _migrate_doctype(name)
        frappe.delete_doc(
            "DocType",
            name,
            force=True,
            ignore_missing=True,
            ignore_permissions=True,
        )

    frappe.db.commit()
