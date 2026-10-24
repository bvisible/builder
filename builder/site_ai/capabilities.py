# //// Neoffice — added file (no upstream equivalent): what this instance lets the Studio and the agent do.
"""What this instance allows the Studio and the agent to do.

A capability is a server answer, never a build flag: the same code serves a
managed instance (the host runs the models and keeps schema-writing tools off)
and a self-hosted one (everything configurable). The Studio reads the dict from
its boot payload; the agent registry reads `disabled_tools()` when it is built.
"""

from __future__ import annotations

import functools

import frappe
from frappe import _

from builder.site_ai.config import MANAGED_KEY, get_assistant_name

# Agent tools that write schema or run code. On a managed instance an
# administrator must not be able to have a model write an ERP schema or execute
# Python from the site editor; the confirm card is not enough of a gate there.
MANAGED_DISABLED_TOOLS = ("run_python", "create_doctype", "seed_sample_data")


def is_managed() -> bool:
    return bool(frappe.conf.get(MANAGED_KEY))


def host_owns_ai_settings() -> bool:
    """Whether this user may connect, change or remove AI providers, keys and models.

    On a managed instance they are the host's: the `Managed` provider row carries the host's key, and
    whoever may rewrite its API base receives that key at the next chat. Same rule as the model picker
    (`ai_capabilities`): the host's Administrator only. Anywhere else, whoever could before still can.
    """
    return not is_managed() or frappe.session.user == "Administrator"


def require_host_ai_settings() -> None:
    if not host_owns_ai_settings():
        frappe.throw(_("The AI of this site is managed by its host"), frappe.PermissionError)


def host_ai_settings_only(fn):
    """Decorator for the endpoints that set up providers: the menu hides them from a client of a managed
    instance, this makes the server refuse them too (a hidden button is not a permission)."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        require_host_ai_settings()
        return fn(*args, **kwargs)

    return wrapper


def ai_provider_permission(doc=None, ptype=None, user=None, **kwargs):
    """`has_permission` hook of Builder AI Provider: a client of a managed instance reads the row (the picker
    needs it) but never saves or deletes it. Code that writes it on the host's behalf passes
    `ignore_permissions` and never reaches this hook."""
    if ptype in ("write", "create", "delete") and is_managed() and (user or frappe.session.user) != "Administrator":
        return False
    return None


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
    from builder.ai.models import ModelRegistry

    # the host names the model behind the assistant (`nora_assistant_model`): no picker for anyone but its Administrator
    host_model = bool(ModelRegistry.host_assistant_model())
    return {
        "assistant_name": get_assistant_name(),
        "managed": managed,
        "disabled_tools": disabled_tools(),
        "users_tab": not managed,
        # the model behind the assistant is the host's choice on a managed instance: a
        # client sees "Nora", not a picker of Kimi ids (Jérémy, 2026-09-08); the host's
        # Administrator keeps the picker to test
        "model_picker": ((not managed) and not host_model) or frappe.session.user == "Administrator",
    }
