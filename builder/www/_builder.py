import frappe
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.pulse.utils import get_app_version
from frappe.translate import get_translations_from_apps, get_user_translations
from frappe.utils.telemetry import capture

from builder.editor_demo import EditorDemo
from builder.utils import get_builder_path

no_cache = 1


def get_context(context):
	context.builder_path = get_builder_path()
	context.boot = get_boot()
	if demo := EditorDemo.from_app_path(frappe.form_dict.app_path):
		# no csrf token or session details: the demo must stay inert for signed-in visitors too
		demo.set_context(context)
		return

	# //// Neoffice — the opt-in, inert editor demo above is public by design (it carries only a page the
	# //// site already publishes). Everything below is the shell, and the shell is for people who may author pages. Upstream serves it to any
	# //// signed-in user and lets the router alert() "no permission" and send them to /app:
	# //// for a portal customer (no desk) that is a modal dead end ending on "Not permitted".
	# //// Refused here instead, on the same source of truth as require_builder_role (the
	# //// Builder Page write permission): frappe renders its 403 page. A Guest goes straight
	# //// to the login page the router would have sent them to, without loading the app.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to=/{context.builder_path}"
		raise frappe.Redirect
	if not frappe.has_permission("Builder Page", "write"):
		raise frappe.PermissionError(frappe._("You do not have permission to use the site builder"))
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	if frappe._dev_server:
		# production proxies socket.io on the page's origin, bench start runs it on a port of its own
		context.socketio_port = frappe.conf.socketio_port
	context.builder_version = get_app_version("builder")
	# developer mode
	context.is_developer_mode = frappe.conf.developer_mode
	context.is_fc_site = is_fc_site()
	context.is_read_only_mode = bool(frappe.flags.read_only)
	if frappe.session.user != "Guest":
		capture("active_site", "builder")


def get_boot() -> dict:
	# only Builder's own catalog, the editor never looks up another app's strings
	lang = frappe.local.lang
	# //// Neoffice — and the catalogs the Neoffice cockpit around the editor draws its own words from
	# //// (neoffice_theme, frappe): the editor never looks them up, the cockpit does, through this same __.
	# //// Without them « Search… », « Favorites », « Collapse menu » stayed English on /builder (07.10).
	# //// Builder's own catalog comes last, so its words keep its translations.
	messages = get_translations_from_apps(lang, cockpit_catalogs())
	messages.update(get_user_translations(lang) or {})
	# //// Neoffice — the Chat tab draws Nora's one conversation (see nora_chat_boot): its files, and only
	# //// its own strings, under the cockpit's and Builder's, which keep their words.
	nora_chat = nora_chat_boot(lang)
	if nora_chat:
		messages = {**nora_chat.pop("messages"), **messages}
	# //// Neoffice — the assistant's name and what this instance allows (managed models, tools
	# //// kept off, Users tab) ride the boot so a registry condition can read them at module load,
	# //// before any request. See builder/site_ai/capabilities.py and builder/plugins.py.
	from builder.plugins import get_capabilities
	from builder.site_ai.capabilities import ai_capabilities

	return {
		"translated_messages": messages,
		"assistant_name": ai_capabilities()["assistant_name"],
		"capabilities": {**get_capabilities(), "ai": ai_capabilities()},
		# //// Neoffice — the Studio's telemetry plugin calls frappe.utils.telemetry.pulse (v16);
		# //// on a v15 bench that call fails with a 417 on every load. The flag tells main.ts
		# //// whether the endpoint exists. Drop with the flag once the fleet is on v16.
		"telemetry_pulse": _has_pulse(),
		# //// Neoffice — None where nora is not installed: the Chat tab is then upstream's panel.
		"nora_chat": nora_chat,
	}


def _has_pulse() -> bool:
	# find_spec raises on a v15 bench, where frappe.utils.telemetry is a module, not a
	# package (the first deploy of the flag answered 500 on every Studio page)
	import importlib.util

	try:
		return importlib.util.find_spec("frappe.utils.telemetry.pulse") is not None
	except (ImportError, ValueError, AttributeError):
		return False


# //// Neoffice — added function (see get_boot).
def cockpit_catalogs() -> list:
	"""The apps whose translations /builder carries: the cockpit's, then Builder's own."""
	installed = set(frappe.get_installed_apps())
	return [app for app in ("frappe", "neoffice_theme") if app in installed] + ["builder"]


# //// Neoffice — added functions (see get_boot). Nora's one conversation in the editor's Chat tab.
# //// The desk's pages that talk with Nora share one conversation, nora.chat.Core (app nora), so that what
# //// improves it improves them all (13.11). The editor is no desk: the tab loads that conversation's files
# //// at run time (frontend/src/utils/noraChatHost.ts) with what they need of frappe. This says where they
# //// are, as the apps' own hooks name them (their ?v= included), and carries their translated strings only:
# //// the whole catalogues of nora and neoffice_activity would add some 800 KB to every opening of the editor.
NORA_CHAT_JQUERY = "/assets/frappe/js/lib/jquery/jquery.min.js"


def nora_chat_boot(lang: str) -> dict | None:
	"""Where the editor finds Nora's conversation, or None (nora not installed: upstream's panel)."""
	installed = set(frappe.get_installed_apps())
	if "nora" not in installed:
		return None
	core = hook_asset("nora", "app_include_js", "/nora_chat_core.js")
	if not core:
		return None
	# the desk's one entry (its orb, its microphone), where neoffice_activity is installed
	entry = (
		hook_asset("neoffice_activity", "app_include_js", "/nora_input.js")
		if "neoffice_activity" in installed
		else None
	)
	scripts = [url for url in (entry, core) if url]
	styles = [
		url
		for url in (
			hook_asset("nora", "app_include_css", "/nora_tokens.css"),
			hook_asset("nora", "app_include_css", "/nora-chat-core.css"),
		)
		if url
	]
	return {
		"jquery": NORA_CHAT_JQUERY,
		"styles": styles,
		"scripts": scripts,
		"lang": lang,
		"messages": nora_chat_messages(lang, scripts),
	}


def hook_asset(app: str, hook: str, name: str) -> str | None:
	"""The url an app's own hook gives one of its files (``?v=`` included), or None."""
	for url in frappe.get_hooks(hook, app_name=app) or []:
		if name in url.split("?")[0]:
			return url
	return None


def nora_chat_messages(lang: str, scripts: list[str]) -> dict:
	"""The translations of the strings these files say, from their apps' catalogues (cached per language and versions)."""
	if not lang or lang == "en" or not scripts:
		return {}

	def build() -> dict:
		import frappe.translate

		apps = sorted({url.split("/")[2] for url in scripts})
		catalog = frappe.translate.get_translations_from_apps(lang, apps)
		codes = [read_asset(url) for url in scripts]
		return strings_of(codes, catalog)

	return frappe.cache().hget("builder_nora_chat_messages", f"{lang}|{'|'.join(scripts)}", build)


def read_asset(url: str) -> str:
	"""The text of an app's public file named by its /assets url."""
	app, _, rest = url.split("?")[0].removeprefix("/assets/").partition("/")
	try:
		with open(frappe.get_app_path(app, "public", rest), encoding="utf-8") as handle:
			return handle.read()
	except OSError:
		return ""


def strings_of(codes: list[str], catalog: dict) -> dict:
	"""The part of ``catalog`` these JavaScript sources look up, keyed as the editor's __ reads it."""
	from frappe.translate import extract_messages_from_javascript_code

	out = {}
	for code in codes:
		for _line, message, context in extract_messages_from_javascript_code(code):
			key = f"{message}:{context}" if context else message
			# a string said with a context falls back to the plain one, as __ does
			for found in (key, message):
				if found in catalog:
					out[found] = catalog[found]
					break
	return out
