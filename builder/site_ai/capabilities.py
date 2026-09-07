"""What this instance allows the Studio and the agent to do.

A capability is a server answer, never a build flag: the same code serves a
managed instance (the host runs the models and keeps schema-writing tools off)
and a self-hosted one (everything configurable). The Studio reads the dict from
its boot payload; the agent registry reads `disabled_tools()` when it is built.
"""

from __future__ import annotations

import frappe

from builder.site_ai.config import MANAGED_KEY, get_assistant_name

# Agent tools that write schema or run code. On a managed instance an
# administrator must not be able to have a model write an ERP schema or execute
# Python from the site editor; the confirm card is not enough of a gate there.
MANAGED_DISABLED_TOOLS = ("run_python", "create_doctype", "seed_sample_data")


def is_managed() -> bool:
    return bool(frappe.conf.get(MANAGED_KEY))


def disabled_tools() -> list[str]:
    """Tool names removed from the agent registry on this instance.

    `nora_disabled_tools` in site_config overrides the managed default (a list,
    or a comma-separated string); an empty list re-enables everything.
    """
    configured = frappe.conf.get("nora_disabled_tools")
    if configured is None:
        return list(MANAGED_DISABLED_TOOLS) if is_managed() else []
    if isinstance(configured, str):
        configured = [name.strip() for name in configured.split(",")]
    return [name for name in configured if name]


def ai_capabilities() -> dict:
    """The AI part of the Studio boot: the name, whether the models are managed
    by the host (read-only AI settings, no provider setup), which tools are off,
    and whether the Users tab (invitations outside the licence quota) shows."""
    managed = is_managed()
    return {
        "assistant_name": get_assistant_name(),
        "managed": managed,
        "disabled_tools": disabled_tools(),
        "users_tab": not managed,
    }
