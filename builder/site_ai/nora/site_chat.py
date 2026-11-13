# //// Neoffice — added file (no upstream equivalent): Nora's conversation about a whole site, outside the editor.
"""Nora's conversation about a whole site, held in the Website space of the desk (its « Nora » tab).

The editor's agent works on the page open in the editor and mirrors every edit to its canvas. Here nobody has
a page open: the person talks about the site, and Nora goes from page to page herself. The same agent runs,
with four differences, all in this module:

- the turn's events go to the conversation (the session), never to an editor that may be open on the same page,
  which would apply another page's edits to its canvas;
- `open_page` moves Nora to another page of the same site, and her block tools edit that page from then on;
- when the turn ends, what changed is computed from the pages themselves (site_changes) and stored on the turn's
  last message: one card per page under her answer, with its links (preview, online, editor) and its state;
- publishing and reverting a turn work on every page the turn touched.

A conversation keeps the site's home page as its `page` (the agent's sessions are page-scoped), and each message
the person sends carries `siteChat` (the site) in its metadata: that is how a conversation of the tab is told
from the editor's, with no field added to the session.
"""

from __future__ import annotations

import json

import frappe
from frappe import _

from builder.ai import locks
from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import Tool
from builder.ai.agent.tools import site_scope
from builder.ai.session import AISession
from builder.site_ai.nora import site_changes
from builder.utils import builder_role_required, require_session_owner

MARK = "siteChat"
# How many conversations of a site the tab offers to reopen.
SESSION_LIMIT = 20
# Changes that are the whole site's, by the record that holds them.
SITE_WIDE = (
	("Website Header Footer Config", "chrome"),
	("Website Header Footer Variant", "chrome"),
	("Builder Token", "design"),
)
logger = frappe.logger("builder.site_chat")


# ─────────────────────────── the sites a reader works on ───────────────────────────


def has_profiles() -> bool:
	return bool(frappe.db.exists("DocType", "Website Profile"))


def readable_sites() -> list[dict]:
	"""The sites of this instance the reader may read, the default first. Empty on an instance without Website
	Profiles: it has one site, the instance itself."""
	if not has_profiles():
		return []
	rows = frappe.get_list(
		"Website Profile",
		filters={"enabled": 1},
		fields=["name", "title", "primary_domain", "is_default", "website_online", "maintenance_mode"],
		order_by="is_default desc, title asc",
		limit_page_length=0,
	)
	return [
		{
			"name": row.name,
			"title": row.title or row.name,
			"domain": (row.primary_domain or "").strip(),
			"is_default": bool(row.is_default),
			"state": "maintenance"
			if row.maintenance_mode
			else ("online" if row.website_online else "offline"),
		}
		for row in rows
	]


def chosen_site(website_profile: str | None, sites: list[dict]) -> str | None:
	"""The site asked for when the reader may read it, else the default one. Asking for a site one may not read
	is refused, never silently swapped for another."""
	if not sites:
		return None
	names = [site["name"] for site in sites]
	if website_profile:
		if website_profile not in names:
			frappe.throw(_("You cannot work on this site"), frappe.PermissionError)
		return website_profile
	return names[0]


def site_title(profile: str | None) -> str:
	if profile and has_profiles():
		return frappe.db.get_value("Website Profile", profile, "title") or profile
	return frappe.db.get_single_value("Website Settings", "app_name") or _("the site")


# ─────────────────────────── conversations ───────────────────────────


def is_site_session(session_id: str | None) -> bool:
	if not session_id:
		return False
	return bool(
		frappe.db.exists(
			AISession.MESSAGE_DOCTYPE,
			{"session": session_id, "role": "user", "metadata_json": ["like", f'%"{MARK}":%']},
		)
	)


def session_site(session_id: str) -> str | None:
	"""The site a conversation is about, as its latest message from the person says."""
	meta = frappe.db.get_value(
		AISession.MESSAGE_DOCTYPE,
		{"session": session_id, "role": "user", "metadata_json": ["like", f'%"{MARK}":%']},
		"metadata_json",
		order_by="creation desc",
	)
	return AISession.load_metadata(meta).get(MARK) or None


def site_session_names(page: str | None, user: str | None = None) -> list[str]:
	"""Every conversation of the tab the person holds on `page` (a site's home page, where the tab anchors them)."""
	if not page:
		return []
	sessions = frappe.get_all(
		AISession.DOCTYPE, filters={"page": page, "session_user": user or frappe.session.user}, pluck="name"
	)
	if not sessions:
		return []
	return frappe.get_all(
		AISession.MESSAGE_DOCTYPE,
		filters={"session": ["in", sessions], "role": "user", "metadata_json": ["like", f'%"{MARK}":%']},
		pluck="session",
		distinct=True,
	)


def not_site_sessions(page: str | None) -> dict:
	"""The filter that keeps the tab's conversations of `page` out of the editor's chat: the editor neither reopens,
	lists nor writes into them, or a question asked in the editor lands in the tab's conversation (13.11)."""
	names = site_session_names(page)
	return {"name": ["not in", names]} if names else {}


def editor_session(session_id: str | None) -> str | None:
	"""The editor's chat may go on in this conversation; None for one of the tab (a new conversation then)."""
	return None if is_site_session(session_id) else session_id


def site_sessions(page: str | None) -> list[dict]:
	"""The reader's conversations of the tab about the site whose home is `page`, the latest first."""
	if not page:
		return []
	sessions = frappe.get_all(
		AISession.DOCTYPE,
		filters={"page": page, "session_user": frappe.session.user, "status": "Active"},
		fields=["name", "title", "last_interaction_on"],
		order_by="last_interaction_on desc",
		limit=SESSION_LIMIT * 3,
	)
	if not sessions:
		return []
	marked = set(
		frappe.get_all(
			AISession.MESSAGE_DOCTYPE,
			filters={
				"session": ["in", [s.name for s in sessions]],
				"role": "user",
				"metadata_json": ["like", f'%"{MARK}":%'],
			},
			pluck="session",
			distinct=True,
		)
	)
	return [
		{"name": s.name, "title": s.title or "", "when": str(s.last_interaction_on or "")}
		for s in sessions
		if s.name in marked
	][:SESSION_LIMIT]


def ai_ready() -> bool:
	"""Whether a model answers here: a conversation that can only fail is not offered as one."""
	from builder.ai.llm import resolve_api_key
	from builder.ai.models import ModelRegistry

	try:
		resolve_api_key(ModelRegistry.get_default("openrouter"))
		return True
	except Exception:
		return False


@frappe.whitelist()
@builder_role_required()
def open_chat(website_profile: str | None = None, session_id: str | None = None) -> dict:
	"""Everything the tab shows when it opens: the sites, the one it works on, its conversations and the open
	one's messages. Nothing is created: a site with no page gets its first one with the first message."""
	from builder.site_ai.config import get_assistant_name
	from builder.site_ai.nora.api import site_home_page

	sites = readable_sites()
	profile = chosen_site(website_profile, sites)
	page = site_home_page(profile)
	sessions = site_sessions(page)
	names = [s["name"] for s in sessions]
	current = session_id if session_id in names else (names[0] if names else None)
	return {
		"sites": sites,
		"site": profile,
		"site_title": site_title(profile),
		"page": page,
		"sessions": sessions,
		"session": current,
		"messages": with_live_states(AISession(frappe.get_doc(AISession.DOCTYPE, current)).get_messages())
		if current
		else [],
		"running": turn_running(current),
		"ready": ai_ready(),
		"assistant": get_assistant_name(),
		"pages": site_page_count(profile),
	}


def site_scopes(profile: str | None) -> list[dict]:
	"""The page filters of a site: its own pages, then the shared ones (untagged, served by every site), as the agent's
	reads resolve them (site_scope.own_site_filters). One filter, nothing, on an instance without Website Profiles."""
	if not frappe.db.has_column("Builder Page", site_scope.PROFILE_FIELD):
		return [{}]
	if not profile:
		return [{site_scope.PROFILE_FIELD: ("is", "not set")}]
	return list(site_scope.own_site_filters(profile))


def site_page_count(profile: str | None) -> int:
	if not frappe.has_permission("Builder Page", "read"):
		return 0
	return sum(frappe.db.count("Builder Page", {"is_template": 0, **scope}) for scope in site_scopes(profile))


def with_live_states(messages: list[dict]) -> list[dict]:
	"""The conversation with each page card's state and links as the page is NOW: a card is written when its turn
	ends, and the page is published, edited again or deleted afterwards (« Publish the pages » must turn its cards
	to « Online » with the link to the page online). A page gone keeps its card, without links."""
	site = next(
		(
			(m.get("metadata") or {}).get(MARK)
			for m in messages
			if m.get("role") == "user" and (m.get("metadata") or {}).get(MARK)
		),
		None,
	)
	fields = ["name", "route", "published", "draft_blocks", "blocks"]
	if frappe.db.has_column("Builder Page", site_scope.PROFILE_FIELD):
		fields.append(site_scope.PROFILE_FIELD)
	pages: dict = {}
	for message in messages:
		for card in (message.get("metadata") or {}).get("changes") or []:
			if card.get("kind") != "page" or not card.get("page"):
				continue
			name = card["page"]
			if name not in pages:
				pages[name] = frappe.db.get_value("Builder Page", name, fields, as_dict=True)
			doc = pages[name]
			if not doc:
				card["state"], card["links"] = "deleted", {}
				continue
			first = next((s.get("block_id") for s in card.get("sections") or [] if s.get("block_id")), None)
			card["state"] = site_changes.page_state(doc)
			card["links"] = site_changes.page_links(doc, doc.get(site_scope.PROFILE_FIELD) or site, first)
	return messages


def turn_running(session_id: str | None) -> bool:
	"""A turn of the conversation at work (its lock) or still waiting in the queue (its job, named by turn_job_id): a turn
	queued behind a busy worker holds no lock yet, and the tab took it for one that had ended (13.11, osiris's default
	queue thousands of jobs long), as the editor's panel had."""
	if not session_id:
		return False
	from builder.site_ai.nora.api import turn_state

	return AISession.is_session_running(session_id) or bool(turn_state(session_id).get("running"))


@frappe.whitelist()
@builder_role_required()
def get_messages(session_id: str) -> dict:
	require_session_owner(session_id)
	if not is_site_session(session_id):
		frappe.throw(_("This conversation is not one of the Website space"), frappe.PermissionError)
	return {
		"messages": with_live_states(AISession(frappe.get_doc(AISession.DOCTYPE, session_id)).get_messages()),
		"running": turn_running(session_id),
	}


@frappe.whitelist(methods=["POST"])
@builder_role_required()
def send(
	prompt: str,
	website_profile: str | None = None,
	session_id: str | None = None,
	display_text: str | None = None,
	image_data: str | None = None,
) -> dict:
	"""One message of the person: queue Nora's turn on the site, as the editor's chat does on its page."""
	from builder.ai.api import save_attached_image
	from builder.ai.block_codec import BlockCodec
	from builder.ai.llm import resolve_api_key
	from builder.ai.models import ModelRegistry
	from builder.site_ai.nora.api import site_creation_page

	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Write something for Nora first"))
	sites = readable_sites()
	if session_id:
		require_session_owner(session_id)
		if not is_site_session(session_id):
			frappe.throw(_("This conversation is not one of the Website space"), frappe.PermissionError)
		website_profile = session_site(session_id) or website_profile
	profile = chosen_site(website_profile, sites)
	# A plain answer, never 429 or 202 as the editor's endpoint gives: the desk's frappe.call runs its callback for a 200 only.
	if turn_running(session_id):
		return {"status": "busy", "message": _("Nora is still working on your last message.")}

	page = frappe.db.get_value(AISession.DOCTYPE, session_id, "page") if session_id else None
	page = page or site_creation_page(profile)["page_id"]
	model = ModelRegistry.get_default("openrouter")
	# Fails fast on a missing key; the job resolves its own copy so the key never sits in the queue.
	resolve_api_key(model)
	image_url = BlockCodec.validate_image_data(image_data) if image_data else None
	image_file_url = save_attached_image(image_url) if image_url else None

	if not session_id:
		session_id = AISession.create({"page": page}, model).name
	session = AISession.get(session_id, page_id=page)
	meta: dict = {MARK: profile or ""}
	if display_text:
		meta["displayText"] = display_text.strip()[:300]
	if image_url:
		meta["attachedImageUrl"] = image_file_url or image_url
	session.append_message("user", prompt, message_type="chat", task_type="agent", metadata=meta)

	from builder.site_ai.nora.api import turn_job_id

	frappe.enqueue(
		run_site_job,
		queue="default",
		# named, so that a turn still in the queue is seen as running (turn_running), not as ended
		job_id=turn_job_id(session_id),
		timeout=frappe.utils.cint(frappe.conf.get("builder_agent_job_timeout")) or 14400,
		prompt=prompt,
		model=model,
		user=frappe.session.user,
		page_id=page,
		session_id=session_id,
		profile=profile,
		image_url=image_url,
		image_file_url=image_file_url,
		enqueue_after_commit=True,
	)
	return {"status": "accepted", "session_id": session_id, "page": page}


def run_site_job(prompt: str, model: str, profile: str | None = None, **kwargs):
	from builder.ai import llm

	# a worker starts in the site's config language: what the turn writes for the person is said in theirs
	frappe.set_user_lang(frappe.session.user)
	kwargs.pop("api_key", None)
	SiteChatRunner(prompt, model, llm.resolve_api_key(model), profile=profile, **kwargs).run()


def resume_job(session_id: str):
	"""How a conversation of the tab goes on after a confirmed action (builder.ai.api.resume_after_action): its own
	runner, so the rest of the turn still reaches the tab. None for the editor's conversations. A function of the
	module, never a closure: the queue finds a job by its import path."""
	return run_resumed_site_job if is_site_session(session_id) else None


def run_resumed_site_job(prompt: str, model: str, session_id: str | None = None, **kwargs):
	kwargs.pop("canvas_theme", None)
	run_site_job(
		prompt,
		model,
		profile=session_site(session_id) if session_id else None,
		session_id=session_id,
		**kwargs,
	)


# ─────────────────────────── publishing and going back ───────────────────────────


@frappe.whitelist(methods=["POST"])
@builder_role_required()
def publish(pages) -> dict:
	"""Publish the pages a card names, each one the reader may write. Returns each page's new card state."""
	pages = frappe.parse_json(pages) if isinstance(pages, str) else pages
	if not isinstance(pages, list) or not pages:
		frappe.throw(_("No page to publish"))
	done = {}
	for name in pages[:50]:
		if not frappe.db.exists("Builder Page", name):
			continue
		doc = frappe.get_doc("Builder Page", name)
		doc.check_permission("write")
		doc.publish()
		done[name] = site_changes.page_state(frappe.get_doc("Builder Page", name))
	return {"pages": done}


@frappe.whitelist(methods=["POST"])
@builder_role_required()
def revert(session_id: str, message_id: str) -> dict:
	"""Take back one turn: every page it changed goes back to how it was before, then the conversation is rewound
	to before the message that asked for it."""
	require_session_owner(session_id)
	if not is_site_session(session_id):
		frappe.throw(_("This conversation is not one of the Website space"), frappe.PermissionError)
	if turn_running(session_id):
		frappe.throw(_("Nora is still working: wait for her answer before going back."))
	row = frappe.db.get_value(
		AISession.MESSAGE_DOCTYPE, {"name": message_id, "session": session_id}, "metadata_json"
	)
	snapshots = AISession.load_metadata(row).get("siteSnapshots") or {}
	for page, snapshot in snapshots.items():
		if not (frappe.db.exists("Builder Page", page) and frappe.db.exists("Builder Snapshot", snapshot)):
			continue
		doc = frappe.get_doc("Builder Page", page)
		doc.check_permission("write")
		doc.restore_snapshot(snapshot)
	session = AISession.get(session_id)
	session.truncate_from_turn(message_id)
	return {"messages": with_live_states(session.get_messages()), "reverted": sorted(snapshots)}


# ─────────────────────────── the runner ───────────────────────────


class SiteChatRunner(AgentRunner):
	"""The editor's agent, talking about a whole site: see the module's docstring."""

	def __init__(self, prompt: str, model: str, api_key: str, *, profile: str | None = None, **kwargs):
		super().__init__(prompt, model, api_key, **kwargs)
		# The conversation, never the page: an editor open on the site's home must not apply this turn's edits.
		self.channel = self.session_id
		self.site_profile = profile
		self.site_started = frappe.utils.now_datetime()
		# page -> its blocks when this turn first opened it, and its revert snapshot
		self.site_before: dict[str, str] = {}
		self.site_snapshots: dict[str, str] = {}
		self.registry.register(OPEN_PAGE)
		self.system_prompt += site_chat_prompt(profile, self.page_id)

	def load_page(self, page_id: str) -> str:
		"""As the editor's runner, plus: a page opened again in the same turn keeps its lock, its first state
		and its first snapshot (a second snapshot would make « go back » stop half way)."""
		from builder.ai import page_writer
		from builder.ai.agent.tree import WorkingTree
		from builder.ai.snapshots import capture_page_state

		key = locks.page_key(page_id)
		if not any(held == key for held, _token in self.held_locks):
			token = locks.acquire(key, locks.PAGE_LOCK_TTL)
			if token is None:
				return f"FAILED: page {page_id} is being edited by another AI task right now. Try again in a moment."
			self.held_locks.append((key, token))
			self.heartbeat.watch(key, token, locks.PAGE_LOCK_TTL)
		root, base = page_writer.load_page_draft(page_id)
		self.tree = WorkingTree(root, base=base)
		if page_id not in self.site_before:
			draft, published = frappe.db.get_value("Builder Page", page_id, ["draft_blocks", "blocks"]) or (
				None,
				None,
			)
			self.site_before[page_id] = draft or published or ""
		if page_id in self.site_snapshots:
			self.pending_state, self.revert_snapshot = None, self.site_snapshots[page_id]
		else:
			self.pending_state, self.revert_snapshot = capture_page_state(page_id), None
		return ""

	def switch_page(self, page_id: str) -> str:
		"""Make `page_id` the page the block tools edit. Returns "" or a FAILED reason, the open page unchanged."""
		if page_id == self.page_id and self.tree is not None:
			return ""
		previous = (self.page_id, self.tree, self.pending_state, self.revert_snapshot)
		if self.page_id and self.revert_snapshot:
			self.site_snapshots.setdefault(self.page_id, self.revert_snapshot)
		self.page_id = page_id
		failed = self.load_page(page_id)
		if failed:
			self.page_id, self.tree, self.pending_state, self.revert_snapshot = previous
		return failed

	def run_turn(self, started: float):
		if self.site_profile:
			# the site of the turn, for a page shared by every site (site_scope.current_profile)
			frappe.local.website_profile = self.site_profile
		try:
			super().run_turn(started)
		finally:
			try:
				self.attach_site_changes()
			except Exception:
				frappe.log_error("Site conversation: changes not attached", frappe.get_traceback())

	# --- what the turn changed ------------------------------------------------

	def site_changes(self) -> list[dict]:
		cards: list[dict] = []
		seen: set[str] = set()
		for page, before in self.site_before.items():
			seen.add(page)
			if card := site_changes.page_card(page, before, self.site_profile):
				cards.append(card)
		for page, created in self.pages_written_meanwhile(seen):
			if card := site_changes.page_card(page, None, self.site_profile):
				card["whole"] = "created" if created else "updated"
				cards.append(card)
		try:
			cards += [site_changes.site_card(kind, self.site_profile) for kind in self.site_wide_kinds()]
		except Exception:
			# the pages' cards are worth more than the whole site's: a failure here never takes them away
			frappe.log_error("Site conversation: whole-site changes not read", frappe.get_traceback())
		return cards

	def pages_written_meanwhile(self, seen: set[str]) -> list[tuple[str, bool]]:
		"""The site's pages this turn wrote without opening them (a page built or rebuilt by generate_site, a
		component synced into them), with whether the turn created them."""
		rows = []
		for scope in site_scopes(self.site_profile):
			rows += frappe.get_all(
				"Builder Page",
				filters={"is_template": 0, "modified": [">=", self.site_started], **scope},
				fields=["name", "creation"],
				order_by="creation asc",
			)
		return [(row.name, row.creation >= self.site_started) for row in rows if row.name not in seen]

	def site_wide_kinds(self) -> list[str]:
		kinds: list[str] = []
		for doctype, kind in SITE_WIDE:
			if kind in kinds or not frappe.db.exists("DocType", doctype):
				continue
			if changed_since(doctype, self.site_started):
				kinds.append(kind)
		return kinds

	def attach_site_changes(self) -> None:
		"""Store the cards on the turn's last message, with each page's snapshot for « go back », and tell the tab.
		Runs before the job commits, so the « complete » event already finds them."""
		if self.page_id and self.revert_snapshot:
			self.site_snapshots.setdefault(self.page_id, self.revert_snapshot)
		cards = self.site_changes()
		if not cards or not self.session_id:
			return
		row = frappe.db.get_value(
			AISession.MESSAGE_DOCTYPE,
			{"session": self.session_id, "role": "assistant", "creation": [">=", self.site_started]},
			["name", "metadata_json"],
			order_by="creation desc",
			as_dict=True,
		)
		if not row:
			return
		meta = AISession.load_metadata(row.metadata_json)
		meta["changes"] = cards
		if self.site_snapshots:
			meta["siteSnapshots"] = self.site_snapshots
		frappe.db.set_value(
			AISession.MESSAGE_DOCTYPE,
			row.name,
			"metadata_json",
			json.dumps(meta, separators=(",", ":"), default=str),
			update_modified=False,
		)
		self.emit("changes", message_id=row.name, changes=cards, after_commit=True)


def changed_since(doctype: str, since) -> bool:
	"""Whether a record of `doctype` was written since `since`. A single doctype keeps its `modified` in tabSingles, which
	get_single_value refuses to read (it is no field of the doctype's meta)."""
	if frappe.get_meta(doctype).issingle:
		singles = frappe.qb.DocType("Singles")
		stamp = (
			frappe.qb.from_(singles)
			.select(singles.value)
			.where((singles.doctype == doctype) & (singles.field == "modified"))
			.run(pluck=True)
		)
		return bool(stamp and stamp[0] and str(stamp[0]) >= str(since))
	return bool(frappe.db.exists(doctype, {"modified": [">=", since]}))


# ─────────────────────────── open_page ───────────────────────────


def own_pages(profile: str | None, limit: int = 60) -> list[dict]:
	"""The site's pages: its own first, then the shared ones."""
	pages: list[dict] = []
	for scope in site_scopes(profile):
		pages += frappe.get_all(
			"Builder Page",
			filters={"is_template": 0, **scope},
			fields=["name", "page_title", "route", "published"],
			order_by="published desc, page_title asc",
			limit=limit,
		)
	return pages[:limit]


def pages_line(profile: str | None) -> str:
	pages = own_pages(profile)
	if not pages:
		return "The site has no page yet."
	return "; ".join(
		f'"{p.page_title or p.name}" {site_changes.visitor_route(p.route)}{"" if p.published else " (never published)"}'
		for p in pages
	)


def run_open_page(ctx, args: dict) -> str:
	from builder.ai.agent.loop import render_skeleton_context
	from builder.ai.agent.tools import site_scope
	from builder.ai.agent.tools.query import resolve_page_reference

	page_id, why = resolve_page_reference(str((args or {}).get("page") or ""), ctx)
	if not page_id:
		return f"FAILED: {why}. The pages of this site: {pages_line(getattr(ctx, 'site_profile', None))}"
	if owner := site_scope.other_site_of(page_id, ctx):
		return f"FAILED: that page belongs to another site ({owner}). This conversation works on its own site only."
	title, route, template = frappe.db.get_value(
		"Builder Page", page_id, ["page_title", "route", "is_template"]
	)
	if template:
		return "FAILED: that page is a template, not a page of the site."
	if not frappe.has_permission("Builder Page", "write", page_id, user=ctx.user):
		return "FAILED: the person you work for may not change that page."
	failed = ctx.switch_page(page_id)
	if failed:
		return failed
	outline = render_skeleton_context(ctx.tree.root) if ctx.tree and ctx.tree.root else "(the page is empty)"
	return (
		f'OPEN: "{title or page_id}" ({site_changes.visitor_route(route)}) is now the page your block, script and '
		f"page tools work on. Its outline:\n{outline}"
	)


OPEN_PAGE = Tool(
	name="open_page",
	side="server",
	handler=run_open_page,
	description=(
		"Move to another page of THIS site: its title, its route or its id. From then on query_blocks, read_block, "
		"the block tools, the script tools and set_page_settings work on that page, until you open another. Call it "
		"before changing anything on a page other than the one open, and whenever the person names a page."
	),
	parameters={
		"type": "object",
		"properties": {
			"page": {
				"type": "string",
				"description": 'The page\'s title ("Contact"), route ("/contact") or id.',
			}
		},
		"required": ["page"],
	},
)


def site_chat_prompt(profile: str | None, page_id: str | None) -> str:
	title, route = (
		(frappe.db.get_value("Builder Page", page_id, ["page_title", "route"]) or (None, None))
		if page_id
		else (None, None)
	)
	return f"""

# This conversation: the whole site, from the Website space (Neoffice)
The person talks to you from the Website space of their ERP, not from the editor: they see no canvas, no selected block and no page open. The conversation is about the WHOLE site "{site_title(profile)}".
- The rule above that you work on the one page the user has open does not hold here. To change a page, call open_page with its title or route first; your block, script and page tools then work on that page. The page open now is "{title or page_id or "none"}" ({site_changes.visitor_route(route)}).
- The pages of the site: {pages_line(profile)}
- Block changes land in each page's draft. Under your answer the person sees one card per page you changed, with its state (draft or online), the links to see it and to open it in the editor, and the button that publishes it: never repeat any of that, never write links or routes for them to click, and never tell them to open the editor or to select a block. Say in one or two sentences what you changed, on which page and where, in their language.
"""
