"""Endpoints the Studio calls around the site playbook."""

from __future__ import annotations

import frappe
from frappe import _

from builder.utils import builder_role_required


@frappe.whitelist()
@builder_role_required()
def site_creation_page(website_profile: str | None = None) -> dict:
    """The page whose editor hosts the site conversation: the profile's home page when it
    exists, else its first page, else a fresh blank draft the pipeline turns into the
    home page. The agent's sessions are page-scoped, so a site needs one page to start."""
    filters: dict = {"is_template": 0}
    scoped = frappe.db.has_column("Builder Page", "neo_website_profile")
    if scoped:
        filters["neo_website_profile"] = website_profile if website_profile else ("is", "not set")
    if website_profile and frappe.db.exists("DocType", "Website Profile"):
        home = frappe.db.get_value("Website Profile", website_profile, "home_page")
        if home and frappe.db.exists("Builder Page", home):
            return {"page_id": home, "created": False}
    for route in ("home", "index"):
        found = frappe.db.get_value("Builder Page", {**filters, "route": route}, "name")
        if found:
            return {"page_id": found, "created": False}
    first = frappe.get_all("Builder Page", filters=filters, pluck="name", order_by="creation asc", limit=1)
    if first:
        return {"page_id": first[0], "created": False}
    page = frappe.new_doc("Builder Page")
    page.page_title = _("Home")
    page.published = 0
    if scoped and website_profile:
        page.neo_website_profile = website_profile
    page.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"page_id": page.name, "created": True}
