import ipaddress
# //// Neoffice — needed by the generation/chat/chrome code added below; upstream's api.py
# //// has no json import (7deba177: NameError on every site-generation path).
import json
import os
import socket
from io import BytesIO
from types import FunctionType, MethodType, ModuleType
from typing import Any
from urllib.parse import unquote, urlparse

import frappe
# //// Neoffice — frappe._ is used by our endpoints below (4661ae05). `import frappe.utils`
# //// on the next line blames to upstream 8b96f0c9 but is ABSENT at the merge base: upstream
# //// dropped it and our merge kept it — our code calls frappe.utils.now() 13 times, so it
# //// stays, but treat it as ours from now on.
from frappe import _
import frappe.utils
import requests
from frappe import _
from frappe.apps import get_apps as get_permitted_apps
from frappe.core.doctype.file.file import get_local_image
from frappe.core.doctype.file.utils import delete_file
from frappe.model.document import Document
# //// Neoffice — rate_limit: the two allow_guest endpoints we added below (newsletter
# //// subscription, click autocapture) had no ceiling at all.
from frappe.rate_limiter import rate_limit
from frappe.utils.caching import redis_cache
from frappe.utils.safe_exec import NamespaceDict, get_safe_globals
from PIL import Image
from werkzeug.wrappers import Response

from builder import builder_analytics
from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer
from builder.builder.doctype.builder_snapshot import builder_snapshot
# //// Neoffice — builder_role_required: the guard the AI/chat/site-chrome endpoints below
# //// carry. Upstream needs none — it ships no endpoint that an untrusted caller can reach.
from builder.utils import builder_role_required, compact_json, has_page_read, has_page_write, normalize_renamed_doc


@frappe.whitelist()
def get_versioned_doc(snapshot: str) -> dict:
	return builder_snapshot.get_versioned_doc(snapshot).as_dict()


# =============================================================================
# SITE TYPE CONFIGURATION CONSTANTS
# =============================================================================

# Default header/footer settings for each site type
SITE_TYPE_HEADER_FOOTER_DEFAULTS = {
	"one_page": {
		"header_style": "Transparent",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": False,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Minimal",
		"sticky_header": True,  # Important for one-page navigation
	},
	"vitrine": {
		"header_style": "Classic",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": False,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"vitrine_user": {
		"header_style": "Classic",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"blog": {
		"header_style": "Minimal",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Icon (overlay)",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"ecommerce": {
		"header_style": "Classic",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Icon (overlay)",
		"show_cta": False,
		"show_user": True,
		"show_wishlist": True,
		"show_cart": True,
		"footer_template": "Extended",
	},
	"ecommerce_search": {
		"header_style": "Classic",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Search Bar (inline)",
		"show_cta": False,
		"show_user": True,
		"show_wishlist": True,
		"show_cart": True,
		"footer_template": "Extended",
	},
	"saas": {
		"header_style": "Floating",
		"header_layout": "Logo | Menu Right | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Extended",
	},
	"portfolio": {
		"header_style": "Minimal",
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": False,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Minimal",
	},
}

# Default pages to generate for each site type
# Page configurations by site type
# Note: The AI has full creative freedom for sections - we only define pages and routes
DEFAULT_PAGES_BY_SITE_TYPE = {
	"one_page": [
		# Single page with all sections - menu will use anchor links
		{"title": "Accueil", "route": "home", "type": "one_page"},
	],
	"vitrine": [
		{"title": "Accueil", "route": "home", "type": "accueil"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Services", "route": "services", "type": "services"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"vitrine_user": [
		{"title": "Accueil", "route": "home", "type": "accueil"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Services", "route": "services", "type": "services"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"blog": [
		{"title": "Accueil", "route": "home", "type": "accueil"},
		{"title": "Articles", "route": "blog", "type": "blog"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"ecommerce": [
		{"title": "Accueil", "route": "home", "type": "accueil_ecommerce"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"ecommerce_search": [
		{"title": "Accueil", "route": "home", "type": "accueil_ecommerce"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"saas": [
		{"title": "Accueil", "route": "home", "type": "accueil"},
		{"title": "Fonctionnalités", "route": "features", "type": "features"},
		{"title": "Tarifs", "route": "pricing", "type": "pricing"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"portfolio": [
		{"title": "Accueil", "route": "home", "type": "accueil"},
		{"title": "Projets", "route": "projects", "type": "portfolio"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
}

# Optional pages available per site type (proposed in chat, user selects)
OPTIONAL_PAGES_BY_SITE_TYPE = {
	"vitrine": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Équipe", "route": "team", "type": "team", "description": "Team members presentation"},
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
		{"title": "Témoignages", "route": "testimonials", "type": "testimonials", "description": "Customer testimonials"},
	],
	"vitrine_user": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Équipe", "route": "team", "type": "team", "description": "Team members presentation"},
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
		{"title": "Témoignages", "route": "testimonials", "type": "testimonials", "description": "Customer testimonials"},
	],
	"ecommerce": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Livraison", "route": "shipping", "type": "custom", "description": "Shipping information"},
		{"title": "CGV", "route": "terms", "type": "custom", "description": "Terms and conditions"},
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
	],
	"ecommerce_search": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Livraison", "route": "shipping", "type": "custom", "description": "Shipping information"},
		{"title": "CGV", "route": "terms", "type": "custom", "description": "Terms and conditions"},
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
	],
	"blog": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Équipe", "route": "team", "type": "team", "description": "Team members presentation"},
		{"title": "Portfolio", "route": "portfolio", "type": "portfolio", "description": "Portfolio / projects showcase"},
	],
	"saas": [
		{"title": "FAQ", "route": "faq", "type": "faq", "description": "Frequently asked questions"},
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
		{"title": "Équipe", "route": "team", "type": "team", "description": "Team members presentation"},
		{"title": "Changelog", "route": "changelog", "type": "custom", "description": "Product changelog"},
	],
	"portfolio": [
		{"title": "Blog", "route": "articles", "type": "blog", "description": "Blog articles listing"},
		{"title": "Témoignages", "route": "testimonials", "type": "testimonials", "description": "Customer testimonials"},
		{"title": "Services", "route": "services", "type": "services", "description": "Services offered"},
	],
}


# =============================================================================
# AI GENERATION API (Creative AI with full freedom)
# =============================================================================

@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def generate_page_blocks(
	prompt: str,
	theme: str = "modern",
	primary_color: str = None,
	secondary_color: str = None,
	provider: str = None,
	model: str = None,
):
	"""
	Generate page blocks using creative AI generation.

	The AI has full creative freedom to design unique pages.
	Header and footer are managed via Website Header Footer Config.

	Args:
		prompt: Description of the desired page
		theme: Visual theme (modern, neobrutalist, glassmorphism, minimal, corporate, creative)
		primary_color: Custom primary color (e.g., "#6c5ce7")
		secondary_color: Custom secondary color (e.g., "#00b894")
		provider: AI provider override (ollama, openai)
		model: Model name override

	Returns:
		list[dict]: Generated Frappe Builder blocks
	"""
	from builder.site_ai.generators.page_generator import PageGenerator

	generator = PageGenerator(provider=provider, model=model)

	blocks = generator.generate_page(
		prompt=prompt,
		theme=theme,
		primary_color=primary_color,
		secondary_color=secondary_color,
	)

	return blocks


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_ai_themes():
	"""
	Get available AI generation themes.

	Returns:
		list[dict]: List of available themes with descriptions
	"""
	from builder.site_ai.design_system.themes import THEMES

	return [
		{
			"name": name,
			"label": theme.get("name", name.title()),
			"description": theme.get("description", ""),
		}
		for name, theme in THEMES.items()
	]


def _update_generation_status(job_id: str, data: dict):
	"""Update the generation status in cache and broadcast via socketio."""
	cache_key = f"site_generation_{job_id}"
	# Stamp each update — the watchdog uses this to detect dead workers.
	data = dict(data)
	data["last_update"] = frappe.utils.now()
	frappe.cache().set_value(cache_key, data, expires_in_sec=14400)  # 4 hours TTL
	print(f"[SITE_GEN] Status update: job_id={job_id}, status={data.get('status')}, progress={data.get('progress')}%, step={data.get('current_step', '')[:50]}")

	# Push to the browser via frappe.realtime (socketio). The event name is
	# prefixed with the job_id so multiple concurrent generations don't
	# interfere. The frontend subscribes in start_generation_polling().
	try:
		frappe.publish_realtime(
			event=f"builder_gen_progress:{job_id}",
			message={**data, "job_id": job_id},
			user=frappe.session.user if getattr(frappe, "session", None) else None,
			after_commit=False,
		)
	except Exception as e:
		# Never let realtime failures break generation — polling still works.
		print(f"[SITE_GEN] publish_realtime failed: {e}")


def _get_generation_status(job_id: str) -> dict:
	"""Get the generation status from cache."""
	cache_key = f"site_generation_{job_id}"
	return frappe.cache().get_value(cache_key) or {"status": "not_found", "error": "Job not found"}


def generate_one_image(prompt: str, width: int = 1024, height: int = 576) -> str:
	"""One image, through whichever backend this site actually has.

	The site image worker picks between Codex, ComfyUI and an OpenAI-compatible
	endpoint. Anything else that wants a picture — an article cover — has to
	make the same choice, or it works on the developer's bench and silently
	produces nothing on a site configured differently.

	Returns the /files/ URL. Raises if no backend produced one.
	"""
	from builder.site_ai.config import get_image_settings
	from builder.site_ai.generators import comfyui_client
	from builder.site_ai.logging import ai_log

	settings = get_image_settings()

	if settings.get("provider") == "codex":
		from builder.site_ai.providers.codex_provider import CodexProvider

		ok, why = CodexProvider.login_status()
		if ok:
			content = CodexProvider().generate_image_file(prompt, width=width, height=height)
			return _save_generated_png(content, prefix="codex")
		ai_log("warning", "Codex unavailable for image, falling back", reason=why)

	if comfyui_client.is_configured():
		healthy, why = comfyui_client.health()
		if healthy:
			return comfyui_client.generate_image(prompt, width=width, height=height)
		ai_log("warning", "ComfyUI unavailable for image, falling back", reason=why)

	from builder.site_ai.generators.image_generator import ImageGenerator

	return ImageGenerator().generate(prompt=prompt, size=f"{width}x{height}").file_url


def _image_backend_available() -> bool:
	"""Is an image backend usable on this site?

	ComfyUI must be explicitly pointed at a server; otherwise the legacy
	generator has to be switched on in site_config.
	"""
	from builder.site_ai.generators import comfyui_client

	return bool(comfyui_client.is_configured() or frappe.conf.get("image_generation_enabled"))


def _enqueue_image_generation(placeholder_images: list, session_id: str = None) -> str:
	"""Queue the image worker and return its job id.

	Shared by the automatic post-generation path and the chat's explicit
	trigger, so both report progress under the same cache key.
	"""
	img_job_id = f"img_gen_{frappe.generate_hash(length=10)}"

	_update_generation_status(img_job_id, {
		"status": "queued",
		"progress": 0,
		"total_images": len(placeholder_images),
		"images_completed": 0,
		"images_failed": 0,
		"current_image": None,
		"error": None,
	})

	if session_id:
		try:
			name = frappe.db.get_value("Builder Chat Session", {"session_id": session_id})
			if name:
				frappe.db.set_value("Builder Chat Session", name, "image_job_id", img_job_id)
		except Exception:
			pass

	frappe.enqueue(
		"builder.api._generate_images_worker",
		queue="default",
		timeout=1800,
		job_name=img_job_id,
		img_job_id=img_job_id,
		placeholder_images=placeholder_images,
	)
	return img_job_id


# Max minutes we allow a generation to be "running" without a cache update
# before the watchdog declares it dead. Workers can get OOM-killed, hit
# supervisorctl restart, lose their Moonshot HTTP connection — in all cases
# the RQ job stops updating the cache but the session stays "Generating"
# forever. The watchdog flips those to "Failed" so the UI can recover.
STUCK_GENERATION_TIMEOUT_MIN = 20


def check_stuck_generations():
	"""Find sessions stuck in 'Generating' and mark them Failed.

	Run every 10 minutes by the scheduler (see hooks.scheduler_events). A
	session is considered stuck when its cached status hasn't been updated
	for STUCK_GENERATION_TIMEOUT_MIN minutes — that's the telltale sign the
	RQ worker died mid-job.
	"""
	from datetime import timedelta
	from frappe.utils import get_datetime, now_datetime

	cutoff = now_datetime() - timedelta(minutes=STUCK_GENERATION_TIMEOUT_MIN)
	stuck_sessions = frappe.get_all(
		"Builder Chat Session",
		filters={"status": "Generating"},
		fields=["name", "session_id", "job_id", "modified"],
	)

	marked = 0
	for row in stuck_sessions:
		snapshot = _get_generation_status(row.job_id) if row.job_id else {}
		last_update_str = snapshot.get("last_update")

		# If the cache is fresh, the worker is still alive — leave it alone.
		if last_update_str:
			try:
				if get_datetime(last_update_str) > cutoff:
					continue
			except Exception:
				pass  # Bad timestamp → treat as stuck.

		# Also bail out if the session itself was modified recently (defensive).
		if row.modified and row.modified > cutoff:
			continue

		try:
			session = frappe.get_doc("Builder Chat Session", row.name)
			session.status = "Failed"
			session.generation_status = "failed"
			session.save(ignore_permissions=True)
			marked += 1
			if row.job_id:
				_update_generation_status(row.job_id, {
					**snapshot,
					"status": "failed",
					"error": f"Worker died — no update for >{STUCK_GENERATION_TIMEOUT_MIN} min",
				})
		except Exception as e:
			frappe.log_error("check_stuck_generations: session update failed", str(e))

	if marked:
		frappe.db.commit()
		print(f"[SITE_GEN] Watchdog marked {marked} stuck session(s) as Failed")


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_site_generation_status(job_id: str):
	"""
	Get the status of a site generation job.

	Args:
		job_id: The job ID returned by generate_complete_site()

	Returns:
		dict: Job status with progress, current step, pages created, etc.
	"""
	return _get_generation_status(job_id)


@frappe.whitelist()
def is_site_read_only() -> bool:
	return bool(frappe.flags.read_only)


@frappe.whitelist()
def get_page_preview_html(page: str, **kwargs) -> Response:
	if not frappe.has_permission("Builder Page", "read", page):
		frappe.throw(_("No permission to preview this page"))

	# to load preview without publishing
	frappe.form_dict.update(kwargs)
	frappe.local.request.for_preview = True
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page
	renderer.doctype = "Builder Page"
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	page_doc = frappe.get_cached_doc("Builder Page", page)
	frappe.enqueue_doc(
		page_doc.doctype,
		page_doc.name,
		"generate_page_preview_image",
		html=str(response.data, "utf-8"),
		queue="short",
	)
	return response


@frappe.whitelist()
@has_page_write("You do not have permission to upload assets.")
def upload_builder_asset():
	from frappe.handler import upload_file

	image_file = upload_file()
	if (
		image_file
		and image_file.file_url.endswith((".png", ".jpeg", ".jpg"))
		and frappe.get_cached_value("Builder Settings", "Builder Settings", "auto_convert_images_to_webp")
	):
		convert_to_webp(file_doc=image_file)
	return image_file


@frappe.whitelist()
@has_page_write("You do not have permission to import assets.")
def import_remote_assets(urls: list[str] | str) -> dict[str, str]:
	"""Pull remote images into this site and return {original_url: local_url}.

	A page that arrives from somewhere else (a paste from another site, an import)
	points at images it does not own. They break when the source moves, cannot be
	optimised, and leak traffic to a third party. URLs that cannot be fetched are
	left out so the caller keeps the original.
	"""
	if isinstance(urls, str):
		urls = frappe.parse_json(urls)

	imported = {}
	for url in list(dict.fromkeys(urls))[:MAX_IMPORTED_ASSETS]:
		if not isinstance(url, str) or not url.startswith("http"):
			continue
		try:
			imported[url] = import_remote_asset(url)
		except Exception:
			frappe.log_error(title="Builder: remote asset import failed", message=frappe.get_traceback())
	return imported


@frappe.whitelist()
@has_page_write("You do not have permission to import fonts.")
def import_remote_fonts(fonts: list[dict] | str) -> dict[str, str]:
	"""Recreate remote webfonts as User Fonts and return {family: file_url}.

	A font that keeps loading from the site it was copied from is the one asset most
	likely to fail outright, since a self hosted font is usually served without the
	CORS headers a cross origin webfont needs. Recreating it here also puts the family
	in Builder's font picker, so it can be used on blocks that never had it.
	"""
	if isinstance(fonts, str):
		fonts = frappe.parse_json(fonts)

	imported = {}
	for font in fonts[:MAX_IMPORTED_FONTS]:
		family = (font or {}).get("family", "").strip()
		url = (font or {}).get("url", "")
		if not family or not isinstance(url, str) or not url.startswith("http"):
			continue
		try:
			imported[family] = import_remote_font(family, url)
		except Exception:
			frappe.log_error(title="Builder: remote font import failed", message=frappe.get_traceback())
	return imported


MAX_IMPORTED_FONTS = 12
MAX_FONT_BYTES = 6 * 1024 * 1024
FONT_EXTENSIONS = ("woff2", "woff", "ttf", "otf")


def import_remote_font(family: str, url: str) -> str:
	existing = frappe.db.get_value("User Font", {"font_name": family}, "font_file")
	if existing:
		return existing

	assert_not_private_url(url)
	extension = next((e for e in FONT_EXTENSIONS if urlparse(url).path.lower().endswith(f".{e}")), None)
	if not extension:
		frappe.throw(f"Not a font file: {url}")

	response = requests.get(url, timeout=20, headers={"User-Agent": "FrappeBuilder/1.0"})
	response.raise_for_status()
	if len(response.content) > MAX_FONT_BYTES:
		frappe.throw(f"Font is larger than {MAX_FONT_BYTES // (1024 * 1024)}MB: {url}")

	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{frappe.scrub(family)}.{extension}",
			"is_private": 0,
			"folder": "Home/Builder Uploads/Fonts",
			"content": response.content,
		}
	).insert()
	frappe.get_doc({"doctype": "User Font", "font_name": family, "font_file": file.file_url}).insert()
	return file.file_url


MAX_IMPORTED_ASSETS = 200
MAX_ASSET_BYTES = 12 * 1024 * 1024
# formats that lose something on a webp round trip (animation, vector text)
KEEP_AS_IS = {"image/svg+xml": "svg", "image/gif": "gif"}
# the canvas never draws more than a couple of thousand pixels across, even at 2x
MAX_IMAGE_EDGE = 2048


def import_remote_asset(url: str) -> str:
	import hashlib

	assert_not_private_url(url)
	digest = hashlib.md5(url.encode()).hexdigest()[:10]
	# the name is derived from the URL, so importing the same asset twice reuses the file
	stem = f"builder-import-{digest}"
	existing = frappe.db.get_value("File", {"file_name": ["like", f"{stem}.%"]}, "file_url")
	if existing:
		return existing

	response = requests.get(url, timeout=20, headers={"User-Agent": "FrappeBuilder/1.0"})
	response.raise_for_status()
	content = response.content
	if len(content) > MAX_ASSET_BYTES:
		frappe.throw(f"Asset is larger than {MAX_ASSET_BYTES // (1024 * 1024)}MB: {url}")

	content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
	extension = KEEP_AS_IS.get(content_type) or guess_keep_as_is_extension(url)
	if extension:
		return save_imported_asset(f"{stem}.{extension}", content)

	image = Image.open(BytesIO(content))
	if image.mode not in ("RGB", "RGBA"):
		image = image.convert("RGBA" if "A" in image.mode else "RGB")
	buffer = BytesIO()
	image.save(buffer, "WEBP")
	return save_imported_asset(f"{stem}.webp", buffer.getvalue())


def guess_keep_as_is_extension(url: str) -> str | None:
	path = urlparse(url).path.lower()
	for extension in KEEP_AS_IS.values():
		if path.endswith(f".{extension}"):
			return extension
	return None


def save_imported_asset(file_name: str, content: bytes) -> str:
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_private": 0,
			"folder": "Home/Builder Uploads",
			"content": content,
		}
	).insert()
	return file.file_url


@frappe.whitelist()
def convert_to_webp(image_url: str | None = None, file_doc: Document | None = None) -> str:
	"""
	Convert image to webp format.
	Handles local files, builder assets, and external URLs.
	Returns the new webp file URL or the original if conversion is not possible.
	"""
	import hashlib

	CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

	def can_convert_image(extn: str) -> bool:
		return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

	def get_extension(filename: str) -> str:
		return filename.split(".")[-1].lower() if "." in filename else ""

	def save_as_webp(image, path: str) -> None:
		# a 5000px original costs ~100MB decoded and thrashes the browser's image cache,
		# so the canvas re-decodes it on every pan; thumbnail() only ever shrinks
		image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
		image.save(path, "WEBP")

	def to_webp_url(url: str, extn: str) -> str:
		return url.replace(extn, "webp")

	def to_webp_path(path: str, extn: str) -> str:
		return path.replace(extn, "webp")

	def handle_file_doc(file_doc: Document) -> str:
		if not file_doc.file_url.startswith("/files"):
			return file_doc.file_url
		image, _, extn = get_local_image(file_doc.file_url)
		if not can_convert_image(extn):
			return file_doc.file_url
		save_as_webp(image, to_webp_path(file_doc.get_full_path(), extn))
		delete_file(file_doc.get_full_path())
		file_doc.file_url = to_webp_url(file_doc.file_url, extn)
		file_doc.save()
		return file_doc.file_url

	def handle_local_url(image_url: str) -> str:
		image, _, extn = get_local_image(image_url)
		if not can_convert_image(extn):
			return image_url
		files = frappe.get_all("File", filters={"file_url": image_url}, fields=["name"], limit=1)
		if not files:
			return image_url
		file = frappe.get_doc("File", files[0].name)
		save_as_webp(image, to_webp_path(file.get_full_path(), extn))
		new_file = frappe.copy_doc(file)
		new_file.file_name = to_webp_url(file.file_name, extn)
		new_file.file_url = to_webp_url(file.file_url, extn)
		new_file.save()
		return new_file.file_url

	def handle_builder_asset(image_url: str) -> str:
		image_path = os.path.abspath(frappe.get_app_path("builder", "www", image_url.lstrip("/")))
		image_path = image_path.replace("_", "-").replace("/builder-assets", "/builder_assets")
		extn = get_extension(image_path)
		if not can_convert_image(extn):
			return image_url
		image = Image.open(image_path)
		save_as_webp(image, to_webp_path(image_path, extn))
		return to_webp_url(image_url, extn)

	def get_external_webp_filename(image_url: str) -> str:
		filename = image_url.split("/")[-1].split("?")[0]
		base = filename.rsplit(".", 1)[0] if "." in filename else ""
		if not base or base.lower() == "webp" or filename.lower() == "webp":
			return f"external-{hashlib.md5(image_url.encode()).hexdigest()[:8]}.webp"
		return base + ".webp"

	def handle_external_url(image_url: str) -> str:
		url = unquote(image_url)
		assert_not_private_url(url)
		image = Image.open(BytesIO(requests.get(url).content))
		filename = get_external_webp_filename(url)
		file = frappe.get_doc({"doctype": "File", "file_name": filename, "file_url": f"/files/{filename}"})
		save_as_webp(image, file.get_full_path())
		file.save()
		return file.file_url

	if not image_url and not file_doc:
		return ""
	if file_doc:
		return handle_file_doc(file_doc)

	image_url = image_url or ""
	if image_url.startswith("/files"):
		return handle_local_url(image_url)
	if image_url.startswith("/builder_assets"):
		return handle_builder_asset(image_url)
	if image_url.startswith("http"):
		return handle_external_url(image_url)
	return image_url


def assert_not_private_url(url: str) -> list[str]:
	"""Raise PermissionError if the URL resolves to a private/internal IP (SSRF guard).
	Returns the addresses it validated so a caller can PIN its connection to one — a
	second DNS resolution at connect time can answer differently (DNS rebinding)."""
	parsed = urlparse(url)
	if parsed.scheme not in ("http", "https"):
		frappe.throw(_("Only HTTP/HTTPS URLs are allowed for external images."), frappe.PermissionError)
	hostname = parsed.hostname
	if not hostname:
		frappe.throw(_("Invalid URL: missing hostname."), frappe.ValidationError)
	try:
		addr_infos = socket.getaddrinfo(hostname, None)
	except socket.gaierror:
		frappe.throw(_("Could not resolve hostname: {0}").format(hostname), frappe.ValidationError)
	ips = []
	for addr_info in addr_infos:
		ip = ipaddress.ip_address(addr_info[4][0])
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
			frappe.throw(
				_("Requests to private or internal addresses are not allowed."), frappe.PermissionError
			)
		ips.append(str(ip))
	return ips


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	if frappe.has_permission("Builder Page", ptype="write"):
		return True

	return False


@frappe.whitelist()
def get_pending_invitations() -> list[dict]:
	from frappe.core.doctype.user_invitation.user_invitation import UserInvitation

	UserInvitation.validate_role("builder")
	invitations = frappe.get_all(
		"User Invitation",
		filters={"status": "Pending", "app_name": "builder"},
		fields=["name", "email", "creation", "invited_by"],
		order_by="creation desc",
	)
	for invitation in invitations:
		invitation.invited_by_name = frappe.db.get_value("User", invitation.invited_by, "full_name")
	return invitations


@frappe.whitelist()
def get_builder_users() -> list[dict]:
	from frappe.core.doctype.user_invitation.user_invitation import UserInvitation

	UserInvitation.validate_role("builder")
	role_rows = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["System Manager", "Website Manager"]], "parenttype": "User"},
		fields=["parent", "role"],
	)
	admins = {row.parent for row in role_rows if row.role == "System Manager"}
	users = frappe.get_all(
		"User",
		filters=[
			["name", "in", list({row.parent for row in role_rows})],
			["name", "not in", ["Administrator", "Guest"]],
			["enabled", "=", 1],
			["user_type", "=", "System User"],
		],
		fields=["name", "full_name", "user_image"],
		order_by="full_name",
	)
	for user in users:
		user.is_admin = user.name in admins
	return users


@frappe.whitelist()
@redis_cache()
def get_apps():
	apps = get_permitted_apps()
	app_list = [
		{
			"name": "frappe",
			"logo": "/assets/builder/images/desk.png",
			"title": "Desk",
			"route": "/app",
		}
	]
	app_list += filter(lambda app: app.get("name") != "builder", apps)

	return app_list


@frappe.whitelist()
@has_page_write("You do not have permission to update page folder.")
def update_page_folder(pages: list[str], folder_name: str) -> None:
	if not pages:
		return
	frappe.db.set_value(
		"Builder Page", {"name": ["in", pages]}, "project_folder", folder_name, update_modified=False
	)


def clone_client_scripts(source_page, new_page) -> None:
	"""Clone the source page's client scripts onto new_page with hashed names,
	so the copy never shares scripts with the source."""
	client_scripts = source_page.client_scripts
	new_page.client_scripts = []
	for script in client_scripts:
		builder_script = frappe.get_doc("Builder Client Script", script.builder_script)
		new_script = frappe.copy_doc(builder_script)
		new_script.name = f"{builder_script.name}-{frappe.generate_hash(length=5)}"
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})


@frappe.whitelist()
@has_page_write("You do not have permission to duplicate a page.")
def duplicate_page(page_name: str):
	page = frappe.get_doc("Builder Page", page_name)
	new_page = frappe.copy_doc(page)
	del new_page.page_name
	new_page.route = None
	clone_client_scripts(page, new_page)
	new_page.insert()
	return new_page


# Templates live on a central Builder Hub site. Builder just fetches the catalog
# and, on use, a per-page bundle over HTTP (server-side — no CORS), then builds a
# page from it. Point at the hub via `template_hub_url` in the site config (or
# common_site_config for the whole bench).
DEFAULT_HUB_URL = "https://preview.frappe.cloud"


def hub_url() -> str:
	return (frappe.conf.get("template_hub_url") or DEFAULT_HUB_URL).rstrip("/")


@redis_cache(ttl=600)
def hub_get_cached(method: str, params_key: tuple):
	# make_get_request (not builder's make_safe_get_request, which blocks private
	# IPs and would reject a localhost hub). Trust = admin-set hub URL.
	from frappe.integrations.utils import make_get_request

	resp = make_get_request(
		f"{hub_url()}/api/method/builder_hub.api.{method}", params=dict(params_key) or None
	)
	return resp.get("message") if resp else None


def hub_get(method: str, **params):
	return hub_get_cached(method, tuple(sorted(params.items())))


@frappe.whitelist()
@has_page_read("You do not have permission to view templates.")
def get_template_groups() -> list[dict]:
	"""Template groups for the picker, fetched live from the hub. Empty (just
	Blank page) if the hub is unreachable."""
	try:
		return hub_get("get_catalog") or []  # type: ignore[return-value]
	except Exception:
		frappe.log_error("Failed to fetch templates from hub")
		return []


# //// Neoffice — added. A hub template ships its own navbar/footer blocks, but a Neoffice
# //// site renders the centrally-managed header/footer (Website Header Footer Config)
# //// around every page: importing verbatim stacked two of each (e545a8b3).
def _strip_template_navigation(blocks: list, components: list) -> list:
	"""bvisible: drop a template's own top-level navigation/footer blocks.

	Neoffice sites render the centrally-managed header/footer (Website Header
	Footer Config) around every page; importing a hub template verbatim would
	stack the template's navbar/footer on top of ours. Removes root-level
	<nav>/<footer> elements and root-level blocks extending a bundle component
	whose name says it is a navbar/header/footer."""
	nav_component_ids = set()
	for comp in components:
		label = f"{comp.get('component_name') or ''} {comp.get('name') or ''}".lower()
		if any(token in label for token in ("navbar", "nav bar", "header", "footer")):
			if comp.get("component_id"):
				nav_component_ids.add(comp["component_id"])
			if comp.get("name"):
				nav_component_ids.add(comp["name"])

	def is_navigation(block: dict) -> bool:
		if not isinstance(block, dict):
			return False
		if block.get("element") in ("nav", "footer"):
			return True
		return block.get("extendedFromComponent") in nav_component_ids

	def strip(level_blocks: list) -> list:
		kept = [b for b in level_blocks if not is_navigation(b)]
		# Single root container (body/wrapper): strip one level deeper too
		if len(kept) == 1 and isinstance(kept[0], dict) and kept[0].get("children"):
			kept[0]["children"] = [c for c in kept[0]["children"] if not is_navigation(c)]
		return kept

	return strip(blocks if isinstance(blocks, list) else [blocks])


def create_page_from_bundle(bundle: dict, project_folder: str | None = None) -> str:
	"""Create an editable page from a fetched hub bundle and return its name.

	Installs shared components/variables/scripts/fonts, then builds the page
	from its blocks. Created pages hot-link the hub's /builder_assets/ images."""
	from frappe.modules.import_file import import_doc

	for font in bundle.get("fonts") or []:
		import_doc(docdict=font)
	for var in bundle.get("variables") or []:
		# a hub still on the pre-rename schema sends Builder Variable docs
		import_doc(docdict=normalize_renamed_doc(var))
	for comp in bundle.get("components") or []:
		import_doc(docdict=comp)

	page = bundle.get("page")
	assert isinstance(page, dict)
	preview = page.get("preview")
	# //// Neoffice — see _strip_template_navigation above (e545a8b3).
	# bvisible: hub templates ship their own navbar/footer components, but on
	# Neoffice instances navigation is provided site-wide by Website Header
	# Footer Config — keeping both stacks two headers/footers on every page.
	page_blocks = _strip_template_navigation(
		page.get("blocks") or [], bundle.get("components") or []
	)
	new_page = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": page.get("page_title") or "My Page",
			"preview": preview or None,
			# //// Neoffice — the stripped blocks, not the bundle's raw ones (e545a8b3).
			"draft_blocks": compact_json(page_blocks),
			"page_data_script": page.get("page_data_script"),
			"head_html": page.get("head_html"),
			"body_html": page.get("body_html"),
			"meta_description": page.get("meta_description"),
			"project_folder": project_folder or None,
		}
	)
	for cs in bundle.get("client_scripts") or []:
		new_script = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"name": f"{cs.get('name')}-{frappe.generate_hash(length=5)}",
				"script_type": cs.get("script_type"),
				"script": cs.get("script"),
			}
		)
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})
	new_page.insert()
	# only fall back to async generation when the template carried no preview
	if not preview:
		frappe.enqueue_doc(
			"Builder Page",
			new_page.name,
			"generate_page_preview_image",
			queue="short",
			enqueue_after_commit=True,
		)
	return new_page.name or ""


@frappe.whitelist()
@has_page_write("You do not have permission to create a page.")
def create_page_from_template(template_page: str, project_folder: str | None = None) -> str:
	"""Create an editable page from a hub template and return its name."""
	try:
		bundle = hub_get("get_template_bundle", page=template_page)
	except Exception:
		frappe.log_error("Failed to fetch template bundle")
		bundle = None
	if not bundle or not bundle.get("page"):
		frappe.throw(frappe._("Could not load the selected template. Please try again."))

	assert isinstance(bundle, dict)
	return create_page_from_bundle(bundle, project_folder)


@frappe.whitelist()
@has_page_write("You do not have permission to create pages.")
def import_template_group(template_group: str, project_folder: str | None = None) -> list[str]:
	"""Import all pages from a template group and return their names."""
	groups = get_template_groups()
	group = next((g for g in groups if g.get("name") == template_group), None)
	if not group:
		frappe.throw(frappe._("Template group not found."))

	pages = group.get("pages") or []
	if not pages:
		frappe.throw(frappe._("No pages found in this template group."))

	created = []
	for page in pages:
		try:
			bundle = hub_get("get_template_bundle", page=page.get("name"))
		except Exception:
			frappe.log_error(f"Failed to fetch template bundle for {page.get('name')}")
			continue
		if not bundle or not bundle.get("page"):
			continue
		name = create_page_from_bundle(bundle, project_folder)
		created.append(name)

	if not created:
		frappe.throw(frappe._("Could not import any pages from this template group."))

	# //// Neoffice — added (4c3a4979): a template group's manifest can carry a header/footer
	# //// design, applied to the site-wide config so navigation matches the template.
	# bvisible: adopting a template group = adopting its design. The group's
	# manifest can carry a header/footer design (colors, height, CTA shape...)
	# that we apply to the centrally-managed Website Header Footer Config, so
	# the site-wide navigation matches the imported template instead of
	# clashing with it (the template's own navbar/footer blocks are stripped
	# at import — see _strip_template_navigation).
	_apply_template_header_footer(group.get("header_footer"))

	return created


def get_site_contact_context(website_profile=None) -> dict:  # //// Neoffice multi-site
	"""bvisible: real, verified contact data of this site — ERPNext Company,
	its linked Address, and the header config logo. Injected into generation
	prompts so the model never fabricates an address/phone/email."""
	data = {}
	try:
		company_name = frappe.db.get_default("company")
		if not company_name:
			companies = frappe.get_all("Company", limit=1, pluck="name")
			company_name = companies[0] if companies else None
		if company_name:
			company = frappe.get_doc("Company", company_name)
			data["company_name"] = company.company_name or company_name
			if company.get("phone_no"):
				data["phone"] = company.phone_no
			if company.get("email"):
				data["email"] = company.email
			if company.get("website"):
				data["website"] = company.website
			# Note: on the Neoffice fleet /files/logo-default.png IS the client's
			# logo (the default file gets replaced per instance) — don't filter it.
			if company.get("company_logo"):
				data["logo"] = company.company_logo
			address_name = frappe.db.get_value(
				"Dynamic Link",
				{"link_doctype": "Company", "link_name": company_name, "parenttype": "Address"},
				"parent",
			)
			if address_name:
				address = frappe.get_doc("Address", address_name)
				parts = [
					address.address_line1,
					address.address_line2,
					f"{address.get('pincode') or ''} {address.get('city') or ''}".strip(),
					address.get("country"),
				]
				data["address"] = ", ".join(p for p in parts if p)
				if not data.get("phone") and address.get("phone"):
					data["phone"] = address.phone
				if not data.get("email") and address.get("email_id"):
					data["email"] = address.email_id
	except Exception:
		pass

	try:
		# //// Neoffice multi-site: logo fallback comes from the target site's chrome
		config = _get_site_chrome_config(website_profile)
		if not data.get("logo") and config.get("logo_image"):
			data["logo"] = config.logo_image
	except Exception:
		pass

	return data


def _contact_context_prompt(data: dict) -> str:
	"""Prompt section carrying the verified business data."""
	labeled = [
		("company_name", "Company name"),
		("address", "Address"),
		("phone", "Phone"),
		("email", "Email"),
		("website", "Website"),
	]
	lines = [f"- {label}: {data[key]}" for key, label in labeled if data.get(key)]
	if not lines:
		return ""
	return (
		"\n\n## REAL BUSINESS DATA (use EXACTLY these values)\n"
		+ "\n".join(lines)
		+ "\nNEVER invent contact details. If a detail is not listed above "
		"(opening hours, extra phone numbers...), omit it or use an obviously "
		"neutral placeholder — never a realistic-looking fabricated value."
	)


def _blocks_fingerprint(raw) -> str:
	"""bvisible: stable hash of a page's blocks JSON (order-insensitive)."""
	import hashlib

	if not raw:
		return ""
	try:
		data = json.loads(raw) if isinstance(raw, str) else raw
		normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
	except Exception:
		normalized = str(raw)
	return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def _get_site_chrome_config(website_profile=None):
	"""#//// Neoffice multi-site: generation targeting a profile writes its chrome
	into the profile's Website Header Footer Variant (bootstrapped from the
	Single on first use); otherwise the global Single (default site / fleet)."""
	if website_profile and frappe.db.exists("DocType", "Website Header Footer Variant"):
		if not frappe.db.exists("Website Header Footer Variant", website_profile):
			single = frappe.get_single("Website Header Footer Config")
			variant = frappe.new_doc("Website Header Footer Variant")
			for f in variant.meta.fields:
				if f.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Table", "Table MultiSelect"):
					continue
				if f.fieldname == "website_profile":
					continue
				try:
					variant.set(f.fieldname, single.get(f.fieldname))
				except Exception:
					pass
			variant.website_profile = website_profile
			variant.insert(ignore_permissions=True)
			frappe.db.commit()
		return frappe.get_doc("Website Header Footer Variant", website_profile)
	return frappe.get_single("Website Header Footer Config")


def classify_existing_pages(website_profile=None) -> dict:
	"""bvisible: classify the site's pages for the regenerate decision.

	- untouched: AI-generated pages never edited since (current blocks hash
	  still matches the hash stamped at generation) — safe to replace silently
	- protected: pages a user designed or edited (hand-made pages, imported
	  templates kept as drafts, or AI pages whose blocks changed since
	  generation) — replacing them requires explicit confirmation
	Template pages and hub staging are excluded entirely.
	"""
	filters = {"is_template": 0}
	# //// Neoffice multi-site: a profile-targeted generation only classifies its
	# //// own pages; an untargeted one never touches profile-tagged pages.
	if frappe.db.has_column("Builder Page", "neo_website_profile"):
		filters["neo_website_profile"] = website_profile if website_profile else ("is", "not set")
	pages = frappe.get_all(
		"Builder Page",
		filters=filters,
		fields=[
			"name", "page_title", "project_folder",
			"ai_generated_at", "ai_blocks_hash", "blocks", "draft_blocks",
		],
	)
	untouched, protected = [], []
	for p in pages:
		if (p.project_folder or "").startswith("Hub Inbox"):
			continue
		info = {"name": p.name, "title": p.page_title}
		current = _blocks_fingerprint(p.draft_blocks or p.blocks)
		if p.ai_generated_at and p.ai_blocks_hash and current == p.ai_blocks_hash:
			untouched.append(info)
		else:
			protected.append(info)
	return {"untouched": untouched, "protected": protected}


# Brief fields applied 1:1 to Website Header Footer Config (site chrome).
# Colors are applied only when non-empty; enum fields always carry a value.
BRIEF_CHROME_FIELDS = (
	# the design system first: these become the site's CSS variables, and the
	# pages reference them instead of carrying their own copies
	"radius_style", "shadow_style", "button_hover", "motion_style",
	"header_bg_color", "header_text_color", "header_height", "header_border",
	"header_style",
	"cta_style", "cta_shape", "cta_size",
	"footer_template", "footer_bg_color", "footer_text_color",
)


def apply_brief_site_chrome(design_brief, website_profile=None) -> list[str]:
	"""bvisible: apply the design brief's header/footer design (site chrome)
	to the Website Header Footer Config. Returns the list of applied fields."""
	# //// Neoffice multi-site: targeted generations write the profile's Variant
	config = _get_site_chrome_config(website_profile)
	applied = []
	for field in BRIEF_CHROME_FIELDS:
		value = getattr(design_brief, field, None)
		if value in (None, ""):
			continue
		if config.get(field) != value:
			config.set(field, value)
		applied.append(field)
	if applied:
		config.save(ignore_permissions=True)
		frappe.db.commit()
	return applied


# Website Header Footer Config fields a hub template manifest may configure.
TEMPLATE_HF_ALLOWED_FIELDS = {
	"radius_style", "shadow_style", "button_hover", "motion_style",
	"header_layout", "header_style", "sticky_header", "header_height", "header_border",
	"header_bg_color", "header_text_color",
	"show_cta", "cta_text", "cta_url", "cta_style", "cta_shape", "cta_size",
	"footer_template", "footer_bg_color", "footer_text_color",
	"primary_color", "secondary_color", "background_color", "text_color",
	"heading_font", "body_font",
}


def _apply_template_header_footer(hf: dict | None) -> None:
	"""bvisible: apply a template group's header/footer design to the site's
	Website Header Footer Config (whitelisted fields only)."""
	if not hf or not isinstance(hf, dict):
		return
	try:
		config = frappe.get_single("Website Header Footer Config")
	except Exception:
		return
	changed = False
	for field, value in hf.items():
		if field in TEMPLATE_HF_ALLOWED_FIELDS and value not in (None, ""):
			config.set(field, value)
			changed = True
	if changed:
		config.save(ignore_permissions=True)
		frappe.clear_cache()


@frappe.whitelist()
@has_page_write("You do not have permission to delete a folder.")
def delete_folder(folder_name: str) -> None:
	# remove folder from all pages in a single update
	frappe.db.set_value(
		"Builder Page", {"project_folder": folder_name}, "project_folder", "", update_modified=False
	)

	frappe.db.delete("Builder Project Folder", {"folder_name": folder_name})


@frappe.whitelist()
@has_page_write("You do not have permission to sync a component.")
def sync_component(component_id: str):
	component = frappe.get_doc("Builder Component", component_id)
	component.sync_component()


@frappe.whitelist()
@has_page_read("You do not have permission to view analytics.")
def get_page_analytics(
	route: str,
	interval: str = "daily",
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	return builder_analytics.get_page_analytics(
		route=route,
		interval=interval,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


@frappe.whitelist()
@has_page_read("You do not have permission to view analytics.")
def get_overall_analytics(
	interval: str = "daily",
	route: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	return builder_analytics.get_overall_analytics(
		interval=interval,
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


@frappe.whitelist()
@has_page_read("You do not have permission to view analytics.")
def get_page_ctr(
	route: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	return builder_analytics.get_page_ctr(
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
# //// Neoffice — rate-limited. Guest POST with no ceiling: one visitor could fill
# //// `tabBuilder Page Click` (and the deferred-insert queue behind it) as fast as the
# //// network allowed. 120/min/IP is far above real autocapture — a busy page fires a
# //// handful of clicks a minute — and far below a flood.
@rate_limit(limit=120, seconds=60)
def make_click_log(
	element: str | None = None,
	text: str | None = None,
	visitor_id: str | None = None,
):
	"""Autocapture a click on a published Builder page. Mirrors Frappe's make_view_log so
	clicks share the exact same `path` (derived from the Referer) as Web Page View rows."""
	from frappe.website.doctype.web_page_view.web_page_view import is_tracking_enabled

	if not is_tracking_enabled():
		return

	path = frappe.request.headers.get("Referer")
	if not frappe.utils.is_site_link(path):
		return

	path = urlparse(path).path
	if path != "/" and path.startswith("/"):
		path = path[1:]
	if path.startswith(("api/", "app/", "assets/", "private/files/")):
		return

	# //// Neoffice — capped BEFORE the uniqueness probe, not just before the insert: the
	# //// probe below queries on `element`, so an uncapped value would look up a row that
	# //// can never exist and mark every click unique. All three are Data(140).
	element = element[:140] if element else element
	text = text[:140] if text else text
	visitor_id = visitor_id[:140] if visitor_id else visitor_id

	is_unique = bool(visitor_id) and not frappe.db.exists(
		"Builder Page Click", {"visitor_id": visitor_id, "path": path, "element": element or ""}
	)

	click = frappe.new_doc("Builder Page Click")
	click.path = path
	click.element = element
	# //// Neoffice — capped above, before the uniqueness probe (see the marker there).
	click.text = text
	click.is_unique = is_unique
	click.visitor_id = visitor_id

	try:
		click.deferred_insert()
	except Exception:
		frappe.log_error("Failed to log builder page click")


def get_keys_for_autocomplete(
	key: str,
	value: Any,
	depth: int = 0,
	max_depth: int | None = None,
):
	if max_depth and depth > max_depth:
		return None  # Or some other sentinel value to indicate termination

	if key.startswith("_"):
		return None

	if isinstance(value, NamespaceDict | dict) and value:
		result = {}
		for k, v in value.items():
			nested_result = get_keys_for_autocomplete(
				k,
				v,
				depth + 1,
				max_depth=max_depth,
			)
			if nested_result is not None:  # Only add if not terminated
				result[k] = nested_result
		return result if result else None  # Return None if the dictionary is empty

	else:
		if isinstance(value, type) and issubclass(value, Exception):
			var_type = "type"  # Exceptions are types
		elif isinstance(value, ModuleType):
			var_type = "namespace"
		elif isinstance(value, FunctionType | MethodType):
			var_type = "function"
		elif isinstance(value, type):
			var_type = "type"
		elif isinstance(value, dict):
			var_type = "property"  # Assuming dict should be mapped to other
		else:
			var_type = "property"  # Default to text if no other type matches
		return {"true_type": type(value).__name__, "type": var_type}


@frappe.whitelist()
@redis_cache()
def get_codemirror_completions():
	return get_keys_for_autocomplete(
		key="",
		value=get_safe_globals(),
	)


@frappe.whitelist()
@has_page_write("You do not have permission to reorder client scripts")
def reorder_client_scripts(script_order: list[str]):
	for idx, script_name in enumerate(script_order, start=1):
		frappe.db.set_value("Builder Page Client Script", script_name, "idx", idx)


@frappe.whitelist()
@has_page_write("You do not have permission to evaluate component scripts")
def get_component_data(
	component_name: str, props: dict | str | None = None, script: str | None = None
) -> dict:
	from builder.builder.doctype.builder_component.builder_component import (
		get_component_data as _get_component_data,
	)

	return _get_component_data(component_name, props, script)


# //// Neoffice — added block (no upstream equivalent), ~1350 lines to the end of the file:
# //// the site chrome API (Website Header Footer Config), the newsletter subscription, the
# //// shortcode and inspiration endpoints, and the whole AI chat / image-generation surface
# //// (5233329b and the AI-chat commits). frappe/builder has none of it — at the merge, keep
# //// everything from here down and re-apply only upstream's changes ABOVE this line.
# =============================================================================
# WEBSITE HEADER FOOTER CONFIG API
# =============================================================================

@frappe.whitelist(allow_guest=True)
def render_site_header():
	"""
	Render the site header from Website Header Footer Config.

	Returns:
		str: HTML for the header
	"""
	from builder.hf_utils.header_footer import render_header
	return render_header()


@frappe.whitelist(allow_guest=True)
def render_site_footer():
	"""
	Render the site footer from Website Header Footer Config.

	Returns:
		str: HTML for the footer
	"""
	from builder.hf_utils.header_footer import render_footer
	return render_footer()


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_header_layout_info():
	"""
	Get information about header layouts.

	Returns:
		dict: Available layouts with descriptions
	"""
	return {
		"Logo | Menu Center | Icons": {
			"layout": "A",
			"menu": "center",
			"description": "Logo on left, menu centered, icons and CTA on right"
		},
		"Logo | Menu Right | Icons": {
			"layout": "A",
			"menu": "right",
			"description": "Logo on left, menu aligned right, icons and CTA on right"
		},
		"Menu Left | Logo Center | Icons": {
			"layout": "B",
			"menu": "left",
			"description": "Menu on left, logo centered, icons and CTA on right"
		}
	}


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_search_type_info():
	"""
	Get information about search types.

	Returns:
		dict: Available search types with descriptions
	"""
	return {
		"None": {
			"description": "No search functionality"
		},
		"Icon (overlay)": {
			"description": "Search icon that opens a slide-down overlay"
		},
		"Search Bar (inline)": {
			"description": "Search bar displayed inline next to icons"
		},
		"Search Bar (full width bottom)": {
			"description": "Full width search bar displayed below the header"
		}
	}


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def add_page_to_menu(page_name: str, label: str = None, url: str = None):
	"""
	Add a Builder Page to the Website Header Footer Config menu.

	Args:
		page_name: Name of the Builder Page
		label: Menu label (defaults to page title)
		url: Menu URL (defaults to page route)

	Returns:
		dict: The added menu item
	"""
	page = frappe.get_doc("Builder Page", page_name)

	if not label:
		label = page.page_title or page.page_name

	if not url:
		url = f"/{page.route}" if page.route else "/"

	config = frappe.get_single("Website Header Footer Config")
	config.append("menu_items", {
		"label": label,
		"url": url,
		"is_external": False,
		"open_in_new_tab": False,
	})
	config.save()

	return {
		"label": label,
		"url": url,
	}


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def auto_populate_menu_from_pages():
	"""
	Auto-populate the menu with all published Builder Pages.

	Returns:
		list: Added menu items
	"""
	pages = frappe.get_all(
		"Builder Page",
		filters={"published": 1},
		fields=["name", "page_title", "route"],
		order_by="modified desc"
	)

	config = frappe.get_single("Website Header Footer Config")

	# Clear existing menu items
	config.menu_items = []

	added = []
	for page in pages:
		label = page.page_title or page.name
		url = f"/{page.route}" if page.route else "/"

		# Don't add duplicates
		if any(item.url == url for item in config.menu_items):
			continue

		config.append("menu_items", {
			"label": label,
			"url": url,
			"is_external": False,
			"open_in_new_tab": False,
		})
		added.append({"label": label, "url": url})

	config.save()
	return added


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def apply_site_type_defaults(site_type: str):
	"""
	Apply default header/footer settings based on site type.

	Args:
		site_type: Type of site (vitrine, vitrine_user, blog, ecommerce, ecommerce_search)

	Returns:
		dict: Applied settings
	"""
	SITE_TYPE_DEFAULTS = {
		"vitrine": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "None",
			"show_cta": True,
			"show_user": False,
			"show_wishlist": False,
			"show_cart": False,
		},
		"vitrine_user": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "None",
			"show_cta": True,
			"show_user": True,
			"show_wishlist": False,
			"show_cart": False,
		},
		"blog": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "Icon (overlay)",
			"show_cta": True,
			"show_user": True,
			"show_wishlist": False,
			"show_cart": False,
		},
		"ecommerce": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "Icon (overlay)",
			"show_cta": False,
			"show_user": True,
			"show_wishlist": True,
			"show_cart": True,
		},
		"ecommerce_search_inline": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "Search Bar (inline)",
			"show_cta": False,
			"show_user": True,
			"show_wishlist": True,
			"show_cart": True,
		},
		"ecommerce_search_full": {
			"header_layout": "Logo | Menu Center | Icons",
			"search_type": "Search Bar (full width bottom)",
			"show_cta": False,
			"show_user": True,
			"show_wishlist": True,
			"show_cart": True,
		},
	}

	defaults = SITE_TYPE_DEFAULTS.get(site_type, SITE_TYPE_DEFAULTS["vitrine"])

	config = frappe.get_single("Website Header Footer Config")

	for key, value in defaults.items():
		if hasattr(config, key):
			setattr(config, key, value)

	config.save()

	return defaults


# =============================================================================
# NEWSLETTER SUBSCRIPTION API
# =============================================================================

@frappe.whitelist(allow_guest=True)
# //// Neoffice — rate-limited. Guest endpoint that inserts a row with
# //// ignore_permissions and sends a welcome mail: unthrottled it was a free mailer and a
# //// free way to grow tabEmail Group Member. 5/min/IP is a form nobody fills faster.
@rate_limit(limit=5, seconds=60)
def subscribe_to_newsletter(email: str, email_group: str = None):
	"""
	Subscribe an email address to an Email Group (newsletter).

	Args:
		email: Email address to subscribe
		email_group: IGNORED (//// Neoffice — the group comes from the site config, never
			from the request; the footer form posts back the value we rendered into
			data-email-group, so the parameter stays for compatibility and is discarded).

	Returns:
		dict with success status and message
	"""
	from frappe.utils import validate_email_address

	# Validate email
	if not email:
		frappe.throw(_("Email is required"))

	email = email.strip().lower()
	if not validate_email_address(email, throw=False):
		frappe.throw(_("Invalid email address"))

	# //// Neoffice — the group comes from the SITE, never from the request. A guest used
	# //// to name any Email Group in the payload and be inserted into it — subscribing
	# //// strangers to lists nobody published, and firing that list's welcome template at
	# //// them. The footer form posts `email_group` back (it reads it from
	# //// data-email-group, which we rendered), so the parameter stays for compatibility
	# //// and is discarded. get_header_footer_config() rather than get_single(): with a
	# //// Website Profile the chrome — and its newsletter group — is per-site.
	from builder.hf_utils.header_footer import get_header_footer_config

	config = get_header_footer_config()
	email_group = (config.get("newsletter_email_group") if config else None) or None

	if not email_group:
		frappe.throw(_("No Email Group configured for newsletter"))

	# Check if Email Group exists
	if not frappe.db.exists("Email Group", email_group):
		frappe.throw(_("Email Group not found"))

	# Check if already subscribed
	if frappe.db.exists("Email Group Member", {"email_group": email_group, "email": email}):
		return {
			"success": True,
			"message": _("You are already subscribed to our newsletter"),
			"already_subscribed": True
		}

	# Add to Email Group
	try:
		doc = frappe.get_doc({
			"doctype": "Email Group Member",
			"email_group": email_group,
			"email": email
		})
		doc.insert(ignore_permissions=True)

		# Update subscriber count
		frappe.get_doc("Email Group", email_group).update_total_subscribers()

		# Send welcome email if configured
		welcome_template = frappe.db.get_value("Email Group", email_group, "welcome_email_template")
		if welcome_template:
			try:
				template = frappe.get_doc("Email Template", welcome_template)
				message = frappe.render_template(template.response_, {"email": email, "email_group": email_group})
				frappe.sendmail(email, subject=template.subject, message=message)
			except Exception:
				pass  # Don't fail subscription if welcome email fails

		return {
			"success": True,
			"message": _("Thank you for subscribing to our newsletter!"),
			"already_subscribed": False
		}

	except frappe.DuplicateEntryError:
		return {
			"success": True,
			"message": _("You are already subscribed to our newsletter"),
			"already_subscribed": True
		}
	except Exception as e:
		frappe.log_error("Newsletter subscription failed", str(e))
		frappe.throw(_("Failed to subscribe. Please try again later."))


# =============================================================================
# BUILDER SHORTCODES API
# =============================================================================

@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_available_shortcodes():
	"""
	Get all enabled shortcodes for use in Builder pages.

	Returns:
		list: List of shortcode objects with usage info
	"""
	shortcodes = frappe.get_all(
		"Builder Shortcode",
		filters={"enabled": 1},
		fields=["shortcode_name", "category", "source_app", "template_path",
				"description", "usage_syntax", "parameters", "example_code"],
		order_by="category, shortcode_name"
	)

	# Parse JSON parameters
	for sc in shortcodes:
		if sc.get("parameters"):
			try:
				sc["parameters"] = json.loads(sc["parameters"])
			except Exception:
				sc["parameters"] = []

	return shortcodes


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def generate_image(
	prompt: str,
	size: str = None,
	negative_prompt: str = None,
	async_generation: bool = False,
	callback_doctype: str = None,
	callback_name: str = None,
	callback_field: str = None,
):
	"""
	Generate an image using AI (Flux via Ollama).

	Args:
		prompt: Text description of the image to generate
		size: Image size (e.g., "1024x1024", "512x512", "1024x576")
		negative_prompt: What to avoid in the image
		async_generation: If True, runs in background and returns job ID
		callback_doctype: DocType to update when done (for async)
		callback_name: Document name to update (for async)
		callback_field: Field to store the image URL (for async)

	Returns:
		dict: Generated image info or job ID for async
	"""
	from builder.site_ai.generators.image_generator import ImageGenerator

	generator = ImageGenerator()

	if async_generation:
		# Queue as background job
		job_id = generator.generate_async(
			prompt=prompt,
			size=size,
			negative_prompt=negative_prompt,
			callback_doctype=callback_doctype,
			callback_name=callback_name,
			callback_field=callback_field,
		)
		return {
			"job_id": job_id,
			"status": "queued",
			"message": "Image generation started in background"
		}
	else:
		# Generate synchronously
		result = generator.generate(
			prompt=prompt,
			size=size,
			negative_prompt=negative_prompt,
		)
		return {
			"file_url": result.file_url,
			"file_doc_name": result.file_doc_name,
			"prompt": result.prompt,
			"width": result.width,
			"height": result.height,
		}


# =============================================================================
# INSPIRATION API
# =============================================================================

@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def capture_inspiration(
	url: str = None,
	image: str = None,
	sentiment: str = "like",
	description: str = None,
):
	"""
	Capture a website or image for design inspiration.

	Args:
		url: Website URL to capture (optional)
		image: Uploaded image file URL (optional)
		sentiment: User sentiment (like, dislike, neutral)
		description: User notes about what they like/dislike

	Returns:
		dict with doc name and status
	"""
	from builder.builder.doctype.builder_site_inspiration.builder_site_inspiration import (
		capture_inspiration as _capture_inspiration
	)
	return _capture_inspiration(url=url, image=image, sentiment=sentiment, description=description)


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_inspirations(limit: int = 20, sentiment: str = None):
	"""
	Get list of captured inspirations.

	Args:
		limit: Max number to return
		sentiment: Optional filter by sentiment (like, dislike, neutral)

	Returns:
		List of inspiration summaries with dominant colors
	"""
	from builder.builder.doctype.builder_site_inspiration.builder_site_inspiration import (
		get_inspirations as _get_inspirations
	)
	return _get_inspirations(limit=int(limit), sentiment=sentiment)


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def analyze_inspirations_for_generation(inspiration_names: str = None):
	"""
	Analyze inspirations and return aggregated data for AI generation.

	Args:
		inspiration_names: JSON array of inspiration names (or None for all)

	Returns:
		Aggregated inspiration data for the design brief
	"""
	from builder.builder.doctype.builder_site_inspiration.builder_site_inspiration import (
		analyze_inspirations_for_generation as _analyze
	)
	return _analyze(inspiration_names=inspiration_names)


@frappe.whitelist()
# //// Neoffice — builder role required: this was a bare @frappe.whitelist(), so ANY
# //// authenticated user (a portal customer included) could call it. See require_builder_role.
@builder_role_required()
def get_shortcodes_for_ai():
	"""
	Get shortcodes formatted for AI prompt context.

	Returns:
		str: Markdown formatted shortcode documentation
	"""
	shortcodes = frappe.get_all(
		"Builder Shortcode",
		filters={"enabled": 1},
		fields=["shortcode_name", "category", "description", "usage_syntax", "parameters", "example_code"],
		order_by="category, shortcode_name"
	)

	if not shortcodes:
		return ""

	lines = ["## Available Shortcodes\n"]
	lines.append("You can use these Jinja includes in Builder pages:\n")

	current_category = None
	for sc in shortcodes:
		if sc.category != current_category:
			current_category = sc.category
			lines.append(f"\n### {current_category}\n")

		lines.append(f"#### {sc.shortcode_name}")
		if sc.description:
			lines.append(f"{sc.description}\n")
		if sc.usage_syntax:
			lines.append(f"**Usage:**\n```jinja\n{sc.usage_syntax}\n```\n")
		if sc.example_code:
			lines.append(f"**Example:**\n```jinja\n{sc.example_code}\n```\n")

	return "\n".join(lines)


# =========================================================================
# CHAT API ENDPOINTS
# =========================================================================


def _scan_placeholder_images(page_names: list, subject: str = "") -> list:
	"""Scan Builder Pages for img blocks with placehold.co URLs."""
	import re
	results = []

	for page_name in page_names:
		try:
			page = frappe.get_doc("Builder Page", page_name)
			blocks = json.loads(page.blocks) if page.blocks else []
			_walk_blocks_for_placeholders(blocks, page_name, results, subject=subject)
		except Exception as e:
			frappe.log_error("Scan placeholder images error", f"Page {page_name}: {str(e)}")

	return results


def _image_subject(session_id: str = None, site_name: str = None, site_description: str = None) -> str:
	"""One short phrase describing the business, for image slots with no text.

	A hero background rarely carries a description; without this the model is
	asked for a stock photo and answers with one.
	"""
	description = (site_description or "").strip()
	name = (site_name or "").strip()
	if not description and session_id:
		try:
			row = frappe.db.get_value(
				"Builder Chat Session",
				{"session_id": session_id},
				["site_name", "site_description"],
				as_dict=True,
			)
			if row:
				description = (row.site_description or "").strip()
				name = name or (row.site_name or "").strip()
		except Exception:
			pass
	subject = description or name
	if len(subject) <= 180:
		return subject.rstrip(" .,;")
	# the model reads a sentence better than a paragraph — and a phrase cut
	# mid-word reads as noise, so stop on the last clean break
	head = subject[:180]
	for stop in (". ", " ; ", ", "):
		cut = head.rfind(stop)
		if cut > 60:
			return head[:cut].rstrip(" .,;")
	return head[: head.rfind(" ")].rstrip(" .,;")


QUALITY_SUFFIX = "photorealistic, high resolution, no text, no words, no logos, no letters"


def _build_image_prompt(context: str, is_background: bool = False, subject: str = "") -> str:
	"""Build an image generation prompt from context text.

	Avoids words like 'website', 'section', 'page' that cause Flux
	to generate website mockups instead of photographs.

	`subject` is what the site is about. It is the fallback when a slot
	carries no description of its own — a hero background usually does not.
	Without it the fallback used to ask for "beautiful landscape photography",
	which is why a yoga studio got a mountain lake above the fold.
	"""
	# Words that are too generic/abstract for image generation
	generic_words = {"Hero Image", "Feature", "Image", "Photo", "Hero", "Section", "Banner"}

	if not context or context.strip() in generic_words:
		if subject:
			lead = "atmospheric photography of" if is_background else "professional photography of"
			return f"{lead} {subject}, natural lighting, {QUALITY_SUFFIX}"
		if is_background:
			return f"atmospheric interior photography, soft natural lighting, {QUALITY_SUFFIX}"
		return f"professional product photography, clean background, {QUALITY_SUFFIX}"

	# Clean up context: remove page-type words that confuse image models
	import re as _re
	cleaned = context.strip()
	# Remove page-type words (Accueil, Contact, About, etc.)
	page_words = _re.compile(
		r'\b(accueil|home|contact|about|à propos|services?|blog|shop|boutique|page|section|hero|banner)\b',
		_re.IGNORECASE
	)
	cleaned = page_words.sub("", cleaned).strip()
	# Remove leftover multiple spaces
	cleaned = _re.sub(r'\s+', ' ', cleaned).strip()

	if not cleaned or len(cleaned) < 3:
		return _build_image_prompt("", is_background=is_background, subject=subject)

	if is_background:
		return f"beautiful photography related to {cleaned}, atmospheric lighting, photorealistic, high resolution, no text, no words, no logos, no letters"
	return f"professional photography of {cleaned}, clean composition, photorealistic, high resolution, no text, no words, no logos, no letters"


def _walk_blocks_for_placeholders(blocks, page_name, results, subject: str = ""):
	"""Recursively walk blocks to find placehold.co URLs in img src or background images."""
	import re

	if not isinstance(blocks, list):
		return

	for block in blocks:
		if not isinstance(block, dict):
			continue

		block_id = block.get("blockId", "")

		# Check <img> elements
		if block.get("element") == "img":
			attrs = block.get("attributes", {})
			src = attrs.get("src", "")
			if "placehold.co" in src and block_id:
				size_match = re.search(r"placehold\.co/(\d+)x(\d+)", src)
				if size_match:
					w, h = int(size_match.group(1)), int(size_match.group(2))
					if w < 200 or h < 200:
						pass  # Skip small images (avatars, icons)
					else:
						size = f"{w}x{h}"
						alt = _build_image_prompt(attrs.get("alt", ""), is_background=False, subject=subject)
						results.append({
							"page_name": page_name,
							"block_id": block_id,
							"src": src,
							"alt": alt,
							"size": size,
							"type": "img",
						})
				else:
					alt = _build_image_prompt(attrs.get("alt", ""), is_background=False, subject=subject)
					results.append({
						"page_name": page_name,
						"block_id": block_id,
						"src": src,
						"alt": alt,
						"size": "1024x1024",
						"type": "img",
					})

		# Check CSS background images (backgroundImage or background with url())
		if block_id:
			styles = block.get("baseStyles", {})
			bg = styles.get("backgroundImage", "") or ""
			if not bg:
				bg_prop = styles.get("background", "") or ""
				if "url(" in bg_prop:
					bg = bg_prop

			if "placehold.co" in bg:
				size_match = re.search(r"placehold\.co/(\d+)x(\d+)", bg)
				size = f"{size_match.group(1)}x{size_match.group(2)}" if size_match else "1920x1080"
				# Extract text param as thematic context (NOT literal text to render in image)
				text_match = re.search(r"text=([^&'\"]+)", bg)
				context = text_match.group(1).replace("+", " ") if text_match else ""
				alt = _build_image_prompt(context, is_background=True, subject=subject)
				results.append({
					"page_name": page_name,
					"block_id": block_id,
					"src": bg,
					"alt": alt,
					"size": size,
					"type": "background",
				})

		# Recurse into children
		if block.get("children"):
			_walk_blocks_for_placeholders(block["children"], page_name, results, subject=subject)


def _generate_images_worker(img_job_id: str, placeholder_images: list):
	"""Background worker that fills placeholder images. Prefers the self-hosted
	ComfyUI server (FLUX.2, our GPU) when configured; falls back to the Ollama
	ImageGenerator otherwise."""
	import re as _re
	from builder.site_ai.generators.image_generator import ImageGenerator
	from builder.site_ai.generators import comfyui_client

	total = len(placeholder_images)
	completed = 0
	failed = 0

	use_comfy = comfyui_client.is_configured()
	generator = None if use_comfy else ImageGenerator()

	for idx, img_info in enumerate(placeholder_images):
		prompt = img_info["alt"]
		size = img_info["size"]
		page_name = img_info["page_name"]
		block_id = img_info["block_id"]

		short_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
		_update_generation_status(img_job_id, {
			"status": "running",
			"progress": int((idx / total) * 100),
			"total_images": total,
			"images_completed": completed,
			"images_failed": failed,
			"current_image": f"{short_prompt} ({idx + 1}/{total})",
			"error": None,
		})

		try:
			img_type = img_info.get("type", "img")
			if use_comfy:
				m = _re.match(r"(\d+)x(\d+)", size or "")
				w, h = (int(m.group(1)), int(m.group(2))) if m else (1024, 1024)
				new_url = comfyui_client.generate_image(prompt, width=w, height=h)
			else:
				new_url = generator.generate(prompt=prompt, size=size).file_url
			_replace_image_in_page(page_name, block_id, new_url, img_type=img_type)
			completed += 1
		except Exception as e:
			failed += 1
			frappe.log_error(
				"Image generation failed",
				f"Prompt: {prompt[:100]}\nPage: {page_name}\nBlock: {block_id}\nError: {str(e)}"
			)
			continue

	_update_generation_status(img_job_id, {
		"status": "completed",
		"progress": 100,
		"total_images": total,
		"images_completed": completed,
		"images_failed": failed,
		"current_image": None,
		"error": None,
	})


def _replace_image_in_page(page_name: str, block_id: str, new_src: str, img_type: str = "img"):
	"""Replace a placeholder image src in a Builder Page by blockId."""
	page = frappe.get_doc("Builder Page", page_name)

	for field in ("blocks", "draft_blocks"):
		blocks_json = page.get(field)
		if not blocks_json:
			continue

		blocks = json.loads(blocks_json)
		if _replace_block_src(blocks, block_id, new_src, img_type=img_type):
			page.set(field, json.dumps(blocks))

	page.save(ignore_permissions=True)
	frappe.db.commit()


_SCRIM = "linear-gradient(rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.30))"
_LIGHT_TEXT = {"#fff", "#ffff", "#ffffff", "white", "rgb(255,255,255)"}


def _has_light_text(block, depth: int = 0) -> bool:
	"""Does anything inside this block rely on the background being dark?"""
	if depth > 6 or not isinstance(block, dict):
		return False
	for key in ("baseStyles", "mobileStyles", "tabletStyles"):
		colour = str((block.get(key) or {}).get("color", "")).strip().lower().replace(" ", "")
		if colour in _LIGHT_TEXT:
			return True
	return any(_has_light_text(child, depth + 1) for child in block.get("children") or [])


# Layout properties that belong on the constrained container, not on the
# full-bleed section that carries the background.
_LAYOUT_PROPS = (
	"display", "gridTemplateColumns", "gridTemplateRows", "gridAutoFlow",
	"gap", "rowGap", "columnGap", "alignItems", "justifyContent",
	"flexDirection", "flexWrap", "alignContent",
)

_SITE_CONTAINER = {
	"maxWidth": "var(--container-width, 1280px)",
	"marginLeft": "auto",
	"marginRight": "auto",
	"width": "100%",
}


def _split_padding(styles: dict) -> tuple:
	"""(vertical, horizontal) from whatever padding notation the block used."""
	for axis in ("paddingLeft", "paddingRight"):
		if styles.get(axis):
			return None, str(styles[axis])
	shorthand = str(styles.get("padding") or "").strip()
	if not shorthand:
		return None, None
	parts = shorthand.split()
	if len(parts) == 1:
		return parts[0], parts[0]
	if len(parts) in (2, 3):
		return parts[0], parts[1]
	return parts[0], parts[1]


def _describe_page(blocks) -> str:
	"""One line describing this page, taken from what the page itself says.

	It fills `meta_description`, which does two jobs: the search snippet, and
	the line under the title in the shared page header. Generated pages had
	neither — the prompt never asked for a description, so every page shipped
	without one and every band rendered as a bare breadcrumb + title.

	It deliberately prefers a **paragraph** over the page's headline. Taking the
	headline printed the same sentence twice, a few centimetres apart: once as
	the band's subtitle, once as the big coloured heading right below it. The
	first real sentence of body copy says the same thing without the echo.
	"""
	import html
	import re

	HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

	def walk(node, found, depth=0):
		if depth > 8 or not isinstance(node, dict):
			return
		raw = node.get("innerHTML") or node.get("innerText") or ""
		if raw:
			# the blocks carry markup: strip the tags, then turn &nbsp; and
			# friends back into characters — this line is read by a human and
			# by a search engine, not by a browser
			clean = re.sub(r"<[^>]+>", " ", str(raw))
			clean = html.unescape(clean).replace("\u00a0", " ")
			clean = re.sub(r"\s+", " ", clean).strip()
			# skip eyebrows (short, shouted) and bare stat numerals
			if len(clean) > 40 and not clean.isupper():
				found.setdefault(
					"heading" if str(node.get("element", "")).lower() in HEADINGS else "body",
					clean,
				)
		for child in node.get("children") or []:
			walk(child, found, depth + 1)

	found = {}
	for block in blocks if isinstance(blocks, list) else []:
		walk(block, found)
		if "body" in found:
			break

	chosen = found.get("body") or found.get("heading") or ""
	return _shorten_for_footer(chosen, limit=180) if chosen else ""


def _shorten_for_footer(text: str, limit: int = 200) -> str:
	"""A short version of the brief that does not stop mid-word.

	`text[:200]` left the footer of a generated site reading "... et les
	possib", on every page. Prefer whole sentences; failing that, the last
	complete word, with an ellipsis so the cut is visibly deliberate.
	"""
	import re

	text = (text or "").strip()
	if len(text) <= limit:
		return text

	kept = ""
	for sentence in re.findall(r"[^.!?]*[.!?]", text):
		if len(kept) + len(sentence) > limit:
			break
		kept += sentence
	if kept.strip():
		return kept.strip()

	cut = text[:limit]
	space = cut.rfind(" ")
	return (cut[:space] if space > 0 else cut).rstrip(" ,;:") + "…"


def _background_with_scrim(block, new_src: str) -> str:
	"""The new photo, keeping (or earning) the veil the text needs to stay readable.

	Two failures this prevents, both seen on a generated homepage:

	- Overwriting `backgroundImage` wholesale **destroyed** the gradient the AI
	  had put in front of its own placeholder. The scrim is part of the design,
	  not part of the placeholder.
	- Where the AI never wrote one, a slate placeholder hid the problem: white
	  text on a dark rectangle reads fine. Swap in a real photo with a bright
	  sky and the headline disappears.

	So: keep an existing gradient, and add a default one when the block draws
	light text over the image. A section with dark text is left alone — a veil
	there would only muddy the photo.
	"""
	previous = str((block.get("baseStyles") or {}).get("backgroundImage") or "")
	prefix = previous.split("url(")[0].strip().rstrip(",").strip()
	if "gradient(" in prefix:
		return f"{prefix}, url('{new_src}')"
	if _has_light_text(block):
		return f"{_SCRIM}, url('{new_src}')"
	return f"url('{new_src}')"


def _replace_block_src(blocks, block_id: str, new_src: str, img_type: str = "img") -> bool:
	"""Recursively find a block by blockId and replace its image source."""
	if not isinstance(blocks, list):
		return False

	for block in blocks:
		if not isinstance(block, dict):
			continue

		if block.get("blockId") == block_id:
			if img_type == "background":
				# Replace CSS background image with proper cover styles
				if "baseStyles" not in block:
					block["baseStyles"] = {}
				block["baseStyles"]["backgroundImage"] = _background_with_scrim(block, new_src)
				block["baseStyles"]["backgroundSize"] = "cover"
				block["baseStyles"]["backgroundPosition"] = "center"
				block["baseStyles"]["backgroundRepeat"] = "no-repeat"
				# Clean up background shorthand if it contained the old URL
				if "background" in block["baseStyles"] and "placehold.co" in block["baseStyles"].get("background", ""):
					del block["baseStyles"]["background"]
			else:
				# Replace <img> src attribute
				if "attributes" not in block:
					block["attributes"] = {}
				block["attributes"]["src"] = new_src
			return True

		if block.get("children"):
			if _replace_block_src(block["children"], block_id, new_src, img_type=img_type):
				return True

	return False


