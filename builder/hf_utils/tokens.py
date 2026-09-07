# //// Neoffice — added file (no upstream equivalent): the tokens write back to the site chrome.
"""The site's colours and fonts live in two places for two readers, and this keeps
them equal:

- the Builder Tokens (`<prefix>-primary` … `<prefix>-font-body`), upstream's design
  system: what the pages reference (`var(--id)`) and what the chrome aliases at
  render time (theme_variables.html), editable in the Studio's Design Tokens;
- the theme fields of Website Header Footer Config (or the profile's Variant): what
  the Settings > Theme pane edits, and the fallback the chrome renders when a
  token is missing.

The Config pushes its fields into the tokens on save (`sync_tokens`); this hook
is the other direction, so a token edited in the Design Tokens is what the Theme
pane shows and what the chrome falls back to. Neither direction re-triggers the
other (`skip_token_sync`)."""

from __future__ import annotations

import frappe

CHROME_DOCTYPES = ("Website Header Footer Config", "Website Header Footer Variant")


def _chrome_for_prefix(prefix: str) -> tuple[str, str] | None:
    """(doctype, name) of the chrome whose token_prefix is `prefix`."""
    if frappe.db.exists("DocType", "Website Header Footer Variant"):
        name = frappe.db.get_value("Website Header Footer Variant", {"token_prefix": prefix}, "name")
        if name:
            return "Website Header Footer Variant", name
    if frappe.db.get_single_value("Website Header Footer Config", "token_prefix") == prefix:
        return "Website Header Footer Config", "Website Header Footer Config"
    return None


def sync_token_to_chrome(doc, method=None) -> bool:
    """doc_events hook on Builder Token: mirror a changed value into the theme
    field it stands for. Returns True when a chrome document was updated."""
    from builder.builder.doctype.website_header_footer_config.website_header_footer_config import (
        WebsiteHeaderFooterConfig,
    )

    name = doc.name or ""
    if "-" not in name or not doc.value:
        return False
    for field, key in WebsiteHeaderFooterConfig.TOKEN_FIELDS.items():
        if not name.endswith(f"-{key}"):
            continue
        prefix = name[: -len(key) - 1]
        target = _chrome_for_prefix(prefix)
        if not target:
            return False
        doctype, docname = target
        chrome = frappe.get_doc(doctype, docname)
        if (chrome.get(field) or "") == doc.value:
            return False
        chrome.set(field, doc.value)
        chrome.flags.skip_token_sync = True
        chrome.flags.ignore_permissions = True
        chrome.save()
        return True
    return False
