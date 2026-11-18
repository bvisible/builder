# //// Neoffice — added file (no upstream equivalent): a site deleted by the person who runs it, or by Nora on their word (2026-11-18).
"""Deleting a site, from the desk or from Nora.

A site could only be emptied by hand: its record refused to go while its pages linked to it, and a person who wanted to start
again had someone delete the pages one by one; the conversation that built the site went with its home page, the texts the
person had pasted into it included. Now:

* deleting the site record deletes its pages first (to the trash, where an administrator can restore them) and its header and
  footer; the conversations with Nora are kept, archived. The theme's own guard still refuses the only site of an instance;
* Nora deletes a site on the person's word (`delete_site`): it asks first, and acts only on an answer given after its question.
  The only site of an instance is emptied instead (its pages go, the site stays, ready to be built again)."""

import frappe

from builder.ai.agent.registry import Tool

VARIANT = "Website Header Footer Variant"
ASK_KEY = "builder_delete_site_asked:{session}:{site}"
ASK_SECONDS = 15 * 60


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


def _asked_key(ctx, site: str) -> str:
	return ASK_KEY.format(session=getattr(ctx, "session_id", None) or "-", site=site)


def _answered_since(ctx, asked_at: float) -> bool:
	"""Whether the person wrote in this conversation after the question was asked. Without a conversation (a console), yes."""
	session = getattr(ctx, "session_id", None)
	if not session:
		return True
	from builder.ai.session import AISession

	last = frappe.get_all(
		AISession.MESSAGE_DOCTYPE,
		filters={"session": session, "role": "user"},
		fields=["creation"],
		order_by="creation desc",
		limit=1,
	)
	return bool(last) and frappe.utils.get_datetime(last[0].creation).timestamp() > asked_at


def leave_the_open_page(ctx, page_names: list[str], site: str | None) -> bool:
	"""The page this conversation is on went with the site: its screen is told after the commit (it must not look before
	the deletion lands), with the site that stays emptied, if any, where « Build a new site » starts. The event goes on
	the conversation's channel: the editor's page, or the conversation itself in the Website space's Nora tab.

	- The editor reloaded a conversation of a page that no longer exists, met an empty one, and stayed open on a page it
	  could no longer save (18.11): it now opens a window whose button is its « Create with AI » (site_creation_page).
	- The tab stayed on the deleted site, ready to send into a conversation with no page: it now keeps Nora's answer and
	  puts the button under it, to the form of a new site or a new conversation on the emptied one (theme, site_nora.js).
	  The tab with no site named was no way on for the editor: it opens the instance's default site."""
	page = getattr(ctx, "page_id", None)
	if not page or page not in page_names or not hasattr(ctx, "emit"):
		return False
	ctx.emit("refetch", resources=["page_gone"], site=site, after_commit=True)
	return True


def _site_of(ctx, args: dict) -> str | None:
	site = (args.get("website_profile") or "").strip()
	if not site and getattr(ctx, "page_id", None):
		site = frappe.db.get_value("Builder Page", ctx.page_id, "neo_website_profile") or ""
	return site or None


def run_delete_site(ctx, args: dict) -> str:
	if not frappe.db.exists("DocType", "Website Profile"):
		return "FAILED: this instance keeps no site records: its pages are deleted one by one in the Builder."
	site = _site_of(ctx, args or {})
	if not site or not frappe.db.exists("Website Profile", site):
		return "FAILED: name the site to delete (website_profile): the open page belongs to none."
	only = _only_site(site)
	may_delete_record = bool(frappe.has_permission("Website Profile", "delete", doc=site))
	may_delete_pages = bool(frappe.has_permission("Builder Page", "delete"))
	if not (may_delete_record or (only and may_delete_pages)):
		return "FAILED: this person may not delete this site: the site's administrator (or a website manager) can, from the desk or here."
	pages = pages_of(site)
	key = _asked_key(ctx, site)
	asked = frappe.cache.get_value(key)
	if not (args or {}).get("confirmed") or not asked or not _answered_since(ctx, float(asked)):
		frappe.cache.set_value(key, frappe.utils.now_datetime().timestamp(), expires_in_sec=ASK_SECONDS)
		titles = ", ".join(p.page_title or p.route or p.name for p in pages[:6]) + (
			" …" if len(pages) > 6 else ""
		)
		what = (
			"its pages go and the site stays, empty and ready to be built again (it is the only site of this instance)"
			if only
			else "the site, its header and footer, and its pages go"
		)
		return (
			f"CONFIRM_NEEDED: deleting the site « {site} »: {what}. {len(pages)} page(s): {titles or 'none'}. The pages go to the "
			"trash, where an administrator can restore them; the conversations with Nora are kept. Ask the person with ONE present_ui "
			"confirm card, in their language, naming the site and what goes; call delete_site again with confirmed=true only after they "
			"say yes, never in the same turn."
		)
	frappe.cache.delete_value(key)
	if only:
		removed = remove_pages(site)
		done = (
			f"DONE: the {removed['pages']} page(s) of « {site} » are in the trash; the site stays, empty, ready to be built again "
			f"({removed['conversations_kept']} conversation(s) with Nora kept)."
		)
	else:
		frappe.delete_doc("Website Profile", site)
		done = f"DONE: the site « {site} » is deleted, with its {len(pages)} page(s) (in the trash) and its header and footer."
	left = leave_the_open_page(ctx, [page.name for page in pages], site if only else None)
	frappe.db.commit()
	if left:
		done += (
			" The page this conversation was on went with it: the person's screen (the editor's window, or a button under "
			"your answer in the Website space) now offers them to build the new site with you. Say in one or two sentences "
			"that it is done and that this starts the new site; ask nothing more here."
		)
	return done


delete_site = Tool(
	name="delete_site",
	side="server",
	handler=run_delete_site,
	description=(
		"Delete a whole website when the person asks for it (« supprime mon site », « je veux repartir de zéro »): its pages to the "
		"trash, its header and footer, and the site itself; the only site of an instance is emptied instead, ready to be built again. "
		"It answers CONFIRM_NEEDED first: ask the person on a confirm card, then call it again with confirmed=true after their yes."
	),
	parameters={
		"type": "object",
		"properties": {
			"website_profile": {
				"type": "string",
				"description": "The site to delete; leave it out for the site of the open page.",
			},
			"confirmed": {
				"type": "boolean",
				"description": "true only in a later turn, after the person said yes on the confirm card.",
			},
		},
	},
)

TOOLS = [delete_site]
