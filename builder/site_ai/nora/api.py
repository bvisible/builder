# //// Neoffice — added file (no upstream equivalent): the endpoints the Studio calls around the site playbook.
"""Endpoints the Studio calls around the site playbook."""

from __future__ import annotations

import json

import frappe
from frappe import _

from builder.utils import builder_role_required


def blank_root_blocks() -> str:
    """The same root the Studio writes for a new page (frontend getBlockTemplate("body"))."""
    return json.dumps([
        {
            "blockId": "root",
            "element": "div",
            "originalElement": "body",
            "attributes": {},
            "baseStyles": {"display": "flex", "flexWrap": "wrap", "flexShrink": 0, "flexDirection": "column", "alignItems": "center"},
            "children": [],
        }
    ])


@frappe.whitelist()
@builder_role_required()
def site_creation_page(website_profile: str | None = None) -> dict:
    """The page whose editor hosts the site conversation: the profile's home page when it
    exists, else its first page, else a fresh blank draft the pipeline turns into the
    home page. The agent's sessions are page-scoped, so a site needs one page to start."""
    found = site_home_page(website_profile)
    if found:
        return {"page_id": found, "created": False}
    scoped = frappe.db.has_column("Builder Page", "neo_website_profile")
    page = frappe.new_doc("Builder Page")
    page.page_title = _("Home")
    page.published = 0
    # the editor's own blank page (getRootBlockTemplate): a page with no root block hangs the canvas
    page.blocks = page.draft_blocks = blank_root_blocks()
    if scoped and website_profile:
        page.neo_website_profile = website_profile
    page.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"page_id": page.name, "created": True}


@frappe.whitelist()
@builder_role_required()
def page_kickoff(page_id: str) -> dict:
    """What « Design with Nora » starts on an empty page of the editor (13.11): the site's conversation (`site`) when no
    other page of its site is built yet, else this page's; and whether the editor's conversation of the page has begun
    (`started`: a message of the person), when the button is no longer offered."""
    from builder.ai.session import AISession
    from builder.site_ai.nora.site_chat import not_site_sessions

    if not page_id or not frappe.db.exists("Builder Page", page_id):
        return {"site": False, "started": False}
    filters: dict = {"is_template": 0, "name": ("!=", page_id)}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        profile = frappe.db.get_value("Builder Page", page_id, "neo_website_profile")
        filters["neo_website_profile"] = profile if profile else ("is", "not set")
    others = frappe.get_all("Builder Page", filters=filters, fields=["blocks", "draft_blocks"], limit=200)
    built = any(has_content(page.draft_blocks) or has_content(page.blocks) for page in others)
    # the editor's conversations only: the Website tab's live on the site's home page too
    sessions = frappe.get_all(
        AISession.DOCTYPE,
        filters={"page": page_id, "session_user": frappe.session.user, **not_site_sessions(page_id)},
        pluck="name",
    )
    started = bool(sessions) and bool(
        frappe.db.exists(AISession.MESSAGE_DOCTYPE, {"session": ("in", sessions), "role": "user"})
    )
    return {"site": not built, "started": started}


def has_content(blocks: str | None) -> bool:
    """Whether a page's block tree holds anything under its root (a new page is a root and nothing else)."""
    try:
        tree = json.loads(blocks or "[]")
    except ValueError:
        return False
    root = tree[0] if isinstance(tree, list) and tree else tree if isinstance(tree, dict) else {}
    return bool(isinstance(root, dict) and root.get("children"))


def site_home_page(website_profile: str | None = None) -> str | None:
    """The site's existing page that hosts its conversation, without creating one: the profile's
    home page, else its page at « home » or « index », else its first page; None when the site
    has no page yet (the Website space's Nora tab asks this when it opens, and creates nothing)."""
    filters: dict = {"is_template": 0}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        filters["neo_website_profile"] = website_profile if website_profile else ("is", "not set")
    if website_profile and frappe.db.exists("DocType", "Website Profile"):
        home = frappe.db.get_value("Website Profile", website_profile, "home_page")
        if home and frappe.db.exists("Builder Page", home):
            return home
    for route in ("home", "index"):
        found = frappe.db.get_value("Builder Page", {**filters, "route": route}, "name")
        if found:
            return found
    first = frappe.get_all("Builder Page", filters=filters, pluck="name", order_by="creation asc", limit=1)
    return first[0] if first else None


@frappe.whitelist()
@builder_role_required()
def turn_state(session_id: str) -> dict:
	"""Whether a turn of this chat session is still running, read from the session
	lock upstream holds for the whole turn (a site build included), or still waiting in
	the queue (turn_job_id). The panel's watchdog polls it when a closing event may have
	been lost."""
	from builder.ai import locks
	from builder.utils import require_session_owner

	require_session_owner(session_id)
	if not session_id:
		return {"running": False}
	if locks.held(locks.session_key(session_id)):
		return {"running": True}
	# a turn still waiting in the queue holds no lock yet: on a busy worker the watchdog took it for a turn that had
	# ended and the panel dropped it (13.11, behind hundreds of queued jobs)
	from frappe.utils.background_jobs import is_job_enqueued

	job_id = frappe.cache().get_value(TURN_JOB_KEY + session_id)
	return {"running": bool(job_id) and is_job_enqueued(job_id)}


TURN_JOB_KEY = "builder_turn_job:"
AGENT_QUEUES = ("short", "default", "long")


def agent_queue() -> str:
	"""The queue a turn of Nora waits in: « short », not « default », where everything the instance does in the background
	waits its turn (13.11: thousands of deletions queued on osiris, and a turn of Nora waited behind them for an hour).
	A bench's short worker serves « short » before « default », and its long worker serves it after « long » and
	« default »: Nora answers at once however full the instance's own queue is. Jérémy, 13.11: « mets la file prioritaire
	pour Nora ». The price: a long turn (a whole site built) holds a worker that also serves the short jobs, which the other
	worker still serves. A site may name another queue (`builder_agent_queue`)."""
	queue = str(frappe.conf.get("builder_agent_queue") or "short")
	return queue if queue in AGENT_QUEUES else "short"


def turn_job_id(session_id: str) -> str:
	"""The name of the RQ job of this chat's next turn, kept for turn_state (one per turn: a second message must never
	overwrite the job of the first one)."""
	job_id = f"builder-turn::{session_id}::{frappe.generate_hash(length=8)}"
	frappe.cache().set_value(TURN_JOB_KEY + session_id, job_id, expires_in_sec=6 * 3600)
	return job_id

