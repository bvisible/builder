# //// Neoffice — added file (no upstream equivalent): a site deleted by the person who runs it, from the desk or on Nora's card (2026-11-18).
"""Deleting a site, from the desk or from Nora.

A site could only be emptied by hand: its record refused to go while its pages linked to it, and a person who wanted to start
again had someone delete the pages one by one; the conversation that built the site went with its home page, the texts the
person had pasted into it included. Now:

* deleting the site record deletes its pages first (to the trash, where an administrator can restore them) and its header and
  footer; the conversations with Nora are kept, archived. The theme's own guard still refuses the only site of an instance;
* Nora proposes to delete a site (`delete_site`), and the person's click deletes it: the tool raises a confirm card
  (builder.ai.agent.pending) whose question the code writes, and the deletion runs when the person applies it
  (`apply_delete_site`, from confirm_pending_settings), with their own rights. The only site of an instance is emptied
  instead (its pages go, the site stays, ready to be built again).

The first version let the model confirm: it asked, then had to call the tool again after the person's yes. In the
Website space's Nora tab the model answered « the site has been deleted » without calling it (18.11): nothing was
deleted. A deletion is no longer a word of the model."""

import frappe
from frappe import _

from builder.ai.agent.registry import Tool

VARIANT = "Website Header Footer Variant"
KIND = "delete_site"


def pages_of(site: str) -> list[dict]:
	return frappe.get_all(
		"Builder Page",
		filters={"neo_website_profile": site, "is_template": 0},
		fields=["name", "page_title", "route"],
		order_by="creation asc",
	)


def keep_the_conversations(page_names: list[str]) -> int:
	"""The conversations with Nora on these pages, detached and archived instead of deleted with them (Builder Page.on_trash)."""
	if not page_names:
		return 0
	sessions = frappe.get_all("Builder AI Session", filters={"page": ("in", page_names)}, pluck="name")
	for name in sessions:
		frappe.db.set_value(
			"Builder AI Session", name, {"page": None, "status": "Archived"}, update_modified=False
		)
	return len(sessions)


def remove_pages(site: str) -> dict:
	"""Every page of the site to the trash, its conversations kept. The caller checked the person may do it."""
	pages = pages_of(site)
	kept = keep_the_conversations([page.name for page in pages])
	for page in pages:
		frappe.delete_doc("Builder Page", page.name, ignore_permissions=True, ignore_missing=True)
	return {"pages": len(pages), "conversations_kept": kept}


def on_profile_trash(doc, method=None):
	"""doc_events: a site record that goes takes its pages and its header and footer with it. Run after the theme's guard (the
	record's own on_trash), which refuses the only site; frappe checks the links after on_trash, so the pages no longer hold it."""
	removed = remove_pages(doc.name)
	if frappe.db.exists("DocType", VARIANT) and frappe.db.exists(VARIANT, doc.name):
		frappe.delete_doc(VARIANT, doc.name, ignore_permissions=True, ignore_missing=True)
	frappe.logger("builder").info(
		f"site {doc.name} deleted with {removed['pages']} pages, {removed['conversations_kept']} conversations kept"
	)


def _only_site(site: str) -> bool:
	return not frappe.db.exists("Website Profile", {"name": ["!=", site]})


def may_delete(site: str, only: bool | None = None) -> bool:
	"""The right to delete the site, or, for the only site of an instance (emptied, never deleted), its pages."""
	only = _only_site(site) if only is None else only
	if frappe.has_permission("Website Profile", "delete", doc=site):
		return True
	return bool(only and frappe.has_permission("Builder Page", "delete"))


def _site_of(ctx, args: dict) -> str | None:
	site = (args.get("website_profile") or "").strip()
	if not site and getattr(ctx, "page_id", None):
		site = frappe.db.get_value("Builder Page", ctx.page_id, "neo_website_profile") or ""
	return site or None


def question(site: str, pages: list, only: bool) -> str:
	"""The card's question, in the person's language, written by the code: the site and its pages as they are."""
	titles = ", ".join(p.page_title or p.route or p.name for p in pages[:6]) + (
		" …" if len(pages) > 6 else ""
	)
	if only:
		return _(
			"Empty the site « {0} »? It is the only site of this instance: its {1} page(s) ({2}) go to the trash, where an "
			"administrator can restore them, and the site stays, ready to be built again."
		).format(site, len(pages), titles or "-")
	return _(
		"Delete the site « {0} »? Its {1} page(s) ({2}) go to the trash, where an administrator can restore them, and its "
		"header and footer are removed. Your conversations with Nora are kept."
	).format(site, len(pages), titles or "-")


def request_delete_site(ctx, args: dict) -> str | None:
	"""Check the proposal and raise the confirm card; nothing is deleted until the person applies it."""
	from builder.ai.agent import pending

	if not frappe.db.exists("DocType", "Website Profile"):
		return (
			"DECLINED: this instance keeps no site records: its pages are deleted one by one in the Builder."
		)
	site = _site_of(ctx, args or {})
	if not site or not frappe.db.exists("Website Profile", site):
		return "DECLINED: name the site to delete (website_profile): the open page belongs to none."
	only = _only_site(site)
	if not may_delete(site, only):
		return "DECLINED: this person may not delete this site: the site's administrator (or a website manager) can, from the desk or here."
	pages = pages_of(site)
	pending.request_confirmation(
		ctx,
		KIND,
		question(site, pages, only),
		{
			"site": site,
			"only": only,
			"page": getattr(ctx, "page_id", None) or "",
			# the realtime channel of this conversation: the editor's page, or the conversation in the Nora tab
			"channel": getattr(ctx, "channel", None) or "",
			"question": question(site, pages, only),
		},
	)
	return None


def apply_delete_site(payload: dict) -> str:
	"""The person applied the card: the site goes (or is emptied, when it is the only one), with their own rights."""
	site = (payload or {}).get("site") or ""
	if not site or not frappe.db.exists("Website Profile", site):
		frappe.throw(_("This site no longer exists."))
	only = _only_site(site)
	if not may_delete(site, only):
		frappe.throw(_("You may not delete this site."), frappe.PermissionError)
	if only:
		removed = remove_pages(site)
		return _(
			"The {0} page(s) of « {1} » are in the trash, where an administrator can restore them; the site stays, empty, "
			"ready to be built again."
		).format(removed["pages"], site)
	pages = len(pages_of(site))
	frappe.delete_doc("Website Profile", site)
	return _(
		"The site « {0} » is deleted: its {1} page(s) are in the trash, where an administrator can restore them, its "
		"header and footer are removed, and your conversations with Nora are kept."
	).format(site, pages)


def page_gone(payload: dict) -> dict | None:
	"""After the card was applied: whether the page the conversation was on went with the site, and the site that stays
	emptied (where a new one starts). The screen that applied the card reads it in confirm_pending_settings' answer: the
	editor opens its window (« Build a new site »), the Website space's Nora tab puts its button under the answer."""
	page = (payload or {}).get("page")
	if not page or frappe.db.exists("Builder Page", page):
		return None
	site = (payload or {}).get("site")
	return {"site": site if site and frappe.db.exists("Website Profile", site) else None}


def tell_the_screens(payload: dict, session: str | None = None) -> dict | None:
	"""page_gone, also said on the conversation's channel after the commit: another screen open on that page or that
	conversation (a second tab) hears that its page went, as the screen that applied the card reads it in its answer."""
	gone = page_gone(payload)
	channel = (payload or {}).get("channel")
	if gone is not None and channel:
		frappe.publish_realtime(
			f"ai_chat_refetch_{channel}",
			{"resources": ["page_gone"], "site": gone["site"], "session_id": session},
			user=frappe.session.user,
			after_commit=True,
		)
	return gone


delete_site = Tool(
	name="delete_site",
	side="terminal",
	handler=request_delete_site,
	description=(
		"Delete a whole website when the person asks for it (« supprime mon site », « je veux repartir de zéro »): its pages to the "
		"trash, its header and footer, and the site itself; the only site of an instance is emptied instead, ready to be built again. "
		"It shows the person a card that names what goes and ends your turn: the site is deleted only when they click its button. "
		"Never say it is deleted before that."
	),
	parameters={
		"type": "object",
		"properties": {
			"website_profile": {
				"type": "string",
				"description": "The site to delete; leave it out for the site of the open page.",
			},
		},
	},
)

TOOLS = [delete_site]
