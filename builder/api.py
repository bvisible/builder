import json
import os
from io import BytesIO
from types import FunctionType, MethodType, ModuleType
from typing import Any
from urllib.parse import unquote

import frappe
import frappe.utils
import requests
from frappe.apps import get_apps as get_permitted_apps
from frappe.core.doctype.file.file import get_local_image
from frappe.core.doctype.file.utils import delete_file
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from frappe.utils.safe_exec import NamespaceDict, get_safe_globals
from frappe.utils.telemetry import POSTHOG_HOST_FIELD, POSTHOG_PROJECT_FIELD
from PIL import Image
from werkzeug.wrappers import Response

from builder import builder_analytics
from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer


# =============================================================================
# SITE TYPE CONFIGURATION CONSTANTS
# =============================================================================

# Default header/footer settings for each site type
SITE_TYPE_HEADER_FOOTER_DEFAULTS = {
	"vitrine": {
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": False,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"vitrine_user": {
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"blog": {
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Icon (overlay)",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Standard",
	},
	"ecommerce": {
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Icon (overlay)",
		"show_cta": False,
		"show_user": True,
		"show_wishlist": True,
		"show_cart": True,
		"footer_template": "Extended",
	},
	"ecommerce_search": {
		"header_layout": "Logo | Menu Center | Icons",
		"search_type": "Search Bar (inline)",
		"show_cta": False,
		"show_user": True,
		"show_wishlist": True,
		"show_cart": True,
		"footer_template": "Extended",
	},
	"saas": {
		"header_layout": "Logo | Menu Right | Icons",
		"search_type": "None",
		"show_cta": True,
		"show_user": True,
		"show_wishlist": False,
		"show_cart": False,
		"footer_template": "Extended",
	},
	"portfolio": {
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
	"vitrine": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Services", "route": "services", "type": "services"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"vitrine_user": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Services", "route": "services", "type": "services"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"blog": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "Articles", "route": "blog", "type": "blog"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"ecommerce": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "Boutique", "route": "shop", "type": "boutique"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"ecommerce_search": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "Boutique", "route": "shop", "type": "boutique"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"saas": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "Fonctionnalités", "route": "features", "type": "features"},
		{"title": "Tarifs", "route": "pricing", "type": "pricing"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
	"portfolio": [
		{"title": "Accueil", "route": "", "type": "accueil"},
		{"title": "Projets", "route": "projects", "type": "portfolio"},
		{"title": "À propos", "route": "about", "type": "about"},
		{"title": "Contact", "route": "contact", "type": "contact"},
	],
}


# =============================================================================
# AI GENERATION API (Creative AI with full freedom)
# =============================================================================

@frappe.whitelist()
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
	from builder.ai.generators.page_generator import PageGenerator

	generator = PageGenerator(provider=provider, model=model)

	blocks = generator.generate_page(
		prompt=prompt,
		theme=theme,
		primary_color=primary_color,
		secondary_color=secondary_color,
	)

	return blocks






@frappe.whitelist()
def get_ai_themes():
	"""
	Get available AI generation themes.

	Returns:
		list[dict]: List of available themes with descriptions
	"""
	from builder.ai.design_system.themes import THEMES

	return [
		{
			"name": name,
			"label": theme.get("name", name.title()),
			"description": theme.get("description", ""),
		}
		for name, theme in THEMES.items()
	]




@frappe.whitelist()
def check_ai_provider_status():
	"""
	Check the status of configured AI providers.

	Returns:
		dict: Status of each provider
	"""
	result = {
		"ollama": {"available": False, "message": "Not configured"},
		"openai": {"available": False, "message": "Not configured"},
	}

	# Check Ollama
	try:
		from builder.ai.providers.ollama_provider import OllamaProvider
		from builder.ai.config import get_ai_settings

		settings = get_ai_settings()
		if settings.provider == "ollama" or settings.base_url:
			provider = OllamaProvider(
				base_url=settings.base_url,
				model=settings.model
			)
			if provider.is_available():
				result["ollama"] = {
					"available": True,
					"message": f"Connected - Model: {settings.model}",
					"model": settings.model
				}
			else:
				result["ollama"] = {
					"available": False,
					"message": f"Server running but model '{settings.model}' not found"
				}
	except Exception as e:
		result["ollama"]["message"] = str(e)

	# Check OpenAI
	try:
		api_key = frappe.conf.get("openai_api_key")
		if api_key:
			result["openai"] = {
				"available": True,
				"message": "API key configured"
			}
	except Exception as e:
		result["openai"]["message"] = str(e)

	return result


@frappe.whitelist()
def generate_complete_site(
	prompt: str,
	site_name: str,
	site_type: str = "vitrine",
	theme: str = "modern",
	primary_color: str = None,
	secondary_color: str = None,
	logo_text: str = None,
	logo_image: str = None,
	cta_text: str = "Contact",
	cta_url: str = "/contact",
	social_links: str = None,
	provider: str = None,
	model: str = None,
):
	"""
	Generate a complete site asynchronously.

	This function queues the site generation as a background job to avoid
	HTTP timeouts (Cloudflare 100s limit). Use get_site_generation_status()
	to poll for completion.

	Args:
		prompt: Description of the desired site
		site_name: Name of the site (used for logo if no logo_text provided)
		site_type: Type of site (vitrine, vitrine_user, blog, ecommerce, ecommerce_search, saas, portfolio)
		theme: Visual theme (modern, neobrutalist, glassmorphism, minimal, corporate, creative)
		primary_color: Primary color hex (e.g., "#6c5ce7")
		secondary_color: Secondary color hex (e.g., "#00b894")
		logo_text: Text logo (overrides site_name)
		logo_image: Image logo path (if provided, uses image instead of text)
		cta_text: Call-to-action button text
		cta_url: Call-to-action button URL
		social_links: JSON string with social media URLs {"facebook": "...", "instagram": "...", ...}
		provider: AI provider override (ollama, openai)
		model: Model name override

	Returns:
		dict: {job_id: str, status: "queued"}
	"""
	# Generate a unique job ID
	job_id = f"site_gen_{frappe.generate_hash(length=10)}"

	# Initialize job status in cache
	_update_generation_status(job_id, {
		"status": "queued",
		"progress": 0,
		"total_pages": len(DEFAULT_PAGES_BY_SITE_TYPE.get(site_type, DEFAULT_PAGES_BY_SITE_TYPE["vitrine"])),
		"current_page": None,
		"pages_created": [],
		"error": None,
		"site_name": site_name,
		"created_at": frappe.utils.now(),
	})

	# Enqueue the generation job
	# Note: job_id is a reserved parameter in frappe.enqueue() for RQ job naming
	# We pass our tracking ID as generation_job_id to avoid conflict
	frappe.enqueue(
		"builder.api._generate_complete_site_worker",
		queue="long",
		timeout=600,  # 10 minutes max
		job_name=job_id,
		generation_job_id=job_id,  # Our tracking ID
		prompt=prompt,
		site_name=site_name,
		site_type=site_type,
		theme=theme,
		primary_color=primary_color,
		secondary_color=secondary_color,
		logo_text=logo_text,
		logo_image=logo_image,
		cta_text=cta_text,
		cta_url=cta_url,
		social_links=social_links,
		provider=provider,
		model=model,
	)

	return {
		"job_id": job_id,
		"status": "queued",
		"message": "Site generation started. Use get_site_generation_status() to track progress."
	}


def _update_generation_status(job_id: str, data: dict):
	"""Update the generation status in cache."""
	cache_key = f"site_generation_{job_id}"
	frappe.cache().set_value(cache_key, data, expires_in_sec=3600)  # 1 hour TTL


def _get_generation_status(job_id: str) -> dict:
	"""Get the generation status from cache."""
	cache_key = f"site_generation_{job_id}"
	return frappe.cache().get_value(cache_key) or {"status": "not_found", "error": "Job not found"}


def _generate_complete_site_worker(
	generation_job_id: str,
	prompt: str,
	site_name: str,
	site_type: str,
	theme: str,
	primary_color: str,
	secondary_color: str,
	logo_text: str,
	logo_image: str,
	cta_text: str,
	cta_url: str,
	social_links: str,
	provider: str,
	model: str,
):
	"""
	Background worker for site generation.

	This function runs in a background job and updates progress via cache.

	Args:
		generation_job_id: Our tracking ID for this generation job (not the RQ job_id)
	"""
	# Use local variable for cleaner code
	job_id = generation_job_id
	from builder.ai.generators.page_generator import PageGenerator

	pages_config = DEFAULT_PAGES_BY_SITE_TYPE.get(site_type, DEFAULT_PAGES_BY_SITE_TYPE["vitrine"])
	total_pages = len(pages_config)

	# Track generation time
	import time
	start_time = time.time()

	try:
		# Update status: starting
		_update_generation_status(job_id, {
			"status": "running",
			"progress": 0,
			"total_pages": total_pages,
			"current_step": "Deleting existing pages",
			"current_page": None,
			"pages_created": [],
			"error": None,
			"site_name": site_name,
			"started_at": frappe.utils.now(),
		})

		# =====================================================================
		# STEP 1: Delete ALL existing Builder Pages
		# =====================================================================
		existing_pages = frappe.get_all("Builder Page", pluck="name")
		for page_name in existing_pages:
			frappe.delete_doc("Builder Page", page_name, ignore_permissions=True)
		frappe.db.commit()

		# =====================================================================
		# STEP 2: Configure Website Header Footer Config
		# =====================================================================
		_update_generation_status(job_id, {
			"status": "running",
			"progress": 5,
			"total_pages": total_pages,
			"current_step": "Configuring header/footer",
			"current_page": None,
			"pages_created": [],
			"error": None,
			"site_name": site_name,
		})

		config = frappe.get_single("Website Header Footer Config")

		# Apply site_type defaults
		defaults = SITE_TYPE_HEADER_FOOTER_DEFAULTS.get(site_type, SITE_TYPE_HEADER_FOOTER_DEFAULTS["vitrine"])
		for key, value in defaults.items():
			if hasattr(config, key):
				setattr(config, key, value)

		# Apply explicit parameters
		if logo_image:
			config.logo_type = "Image"
			config.logo_image = logo_image
		else:
			config.logo_type = "Text"
			config.logo_text = logo_text or site_name

		# Apply colors if provided
		if primary_color and hasattr(config, "primary_color"):
			config.primary_color = primary_color
		if secondary_color and hasattr(config, "secondary_color"):
			config.secondary_color = secondary_color

		# CTA configuration
		config.cta_text = cta_text
		config.cta_url = cta_url
		# CTA button uses primary color
		if primary_color and hasattr(config, "cta_button_color"):
			config.cta_button_color = primary_color
		if hasattr(config, "cta_button_text_color"):
			config.cta_button_text_color = "#ffffff"

		# Social links
		if social_links:
			try:
				links = json.loads(social_links) if isinstance(social_links, str) else social_links
				config.show_social_links = True
				if links.get("facebook"):
					config.facebook_url = links["facebook"]
				if links.get("instagram"):
					config.instagram_url = links["instagram"]
				if links.get("twitter"):
					config.twitter_url = links["twitter"]
				if links.get("linkedin"):
					config.linkedin_url = links["linkedin"]
				if links.get("youtube"):
					config.youtube_url = links["youtube"]
			except (json.JSONDecodeError, TypeError):
				pass

		# Clear menu items (will be populated after page creation)
		config.menu_items = []
		config.save(ignore_permissions=True)
		frappe.db.commit()

		# =====================================================================
		# STEP 3: Generate pages in PARALLEL (content only, no header/footer blocks)
		# =====================================================================
		from concurrent.futures import ThreadPoolExecutor, as_completed

		_update_generation_status(job_id, {
			"status": "running",
			"progress": 10,
			"total_pages": total_pages,
			"current_step": f"Generating {total_pages} pages in parallel...",
			"current_page": None,
			"pages_created": [],
			"error": None,
			"site_name": site_name,
		})

		# Get current site info for thread initialization
		current_site = frappe.local.site
		sites_path = frappe.local.sites_path

		def generate_single_page(page_def: dict) -> dict:
			"""
			Generate a single page. Runs in a thread.
			Returns dict with page_def, blocks, and error info.
			"""
			# Initialize Frappe in this thread (required for thread-local DB connection)
			frappe.init(site=current_site, sites_path=sites_path)
			frappe.connect()

			try:
				# Each thread needs its own generator instance
				gen = PageGenerator(provider=provider, model=model)
				page_prompt = f"{prompt}. Page: {page_def['title']}."

				blocks = gen.generate_page(
					prompt=page_prompt,
					theme=theme,
					primary_color=primary_color,
					secondary_color=secondary_color,
					page_title=page_def["title"],
					page_type=page_def.get("type", ""),
				)
				return {"page_def": page_def, "blocks": blocks, "error": None}
			except Exception as e:
				error_msg = str(e)[:200]
				try:
					frappe.log_error(f"Page generation failed: {page_def['title']}", str(e))
				except Exception:
					pass  # Ignore logging errors in thread
				return {"page_def": page_def, "blocks": None, "error": error_msg}
			finally:
				# Clean up thread-local Frappe state
				frappe.destroy()

		# Generate all pages in parallel (max 4 workers to avoid overload)
		generated_results = []
		with ThreadPoolExecutor(max_workers=4) as executor:
			futures = {
				executor.submit(generate_single_page, page_def): page_def
				for page_def in pages_config
			}

			completed_count = 0
			for future in as_completed(futures):
				completed_count += 1
				page_def = futures[future]
				result = future.result()
				generated_results.append(result)

				# Update progress
				progress = 10 + int((completed_count / total_pages) * 80)
				status_msg = f"Generated {completed_count}/{total_pages}"
				if result["error"]:
					status_msg += f" (warning: {page_def['title']} failed)"

				_update_generation_status(job_id, {
					"status": "running",
					"progress": progress,
					"total_pages": total_pages,
					"current_step": status_msg,
					"current_page": page_def["title"],
					"pages_created": [],  # Will be filled after DB operations
					"error": result["error"],
					"site_name": site_name,
				})

		# Sort results by original page order (pages_config order)
		# This ensures menu items appear in the correct order (Accueil first)
		page_order = {p["title"]: i for i, p in enumerate(pages_config)}
		generated_results.sort(key=lambda r: page_order.get(r["page_def"]["title"], 999))

		# Now create all pages in DB (sequential, but fast)
		created_pages = []
		for result in generated_results:
			if result["error"] or not result["blocks"]:
				continue

			page_def = result["page_def"]
			blocks = result["blocks"]

			# Create the Builder Page
			page = frappe.new_doc("Builder Page")
			page.page_title = page_def["title"]
			page.blocks = json.dumps(blocks)
			page.draft_blocks = json.dumps(blocks)
			page.published = 1
			page.insert(ignore_permissions=True)

			# Force route (no /pages/ prefix)
			route = page_def["route"]
			frappe.db.set_value("Builder Page", page.name, "route", route)
			frappe.db.commit()

			created_pages.append({
				"name": page.name,
				"title": page_def["title"],
				"route": f"/{route}" if route else "/",
			})

		# =====================================================================
		# STEP 4: Update menu from created pages
		# =====================================================================

		# Check that at least one page was created
		if not created_pages:
			raise ValueError(f"No pages could be generated. All {total_pages} page generations failed.")

		_update_generation_status(job_id, {
			"status": "running",
			"progress": 95,
			"total_pages": total_pages,
			"current_step": "Updating menu",
			"current_page": None,
			"pages_created": created_pages,
			"error": None,
			"site_name": site_name,
		})

		config = frappe.get_single("Website Header Footer Config")

		# ---- Update Menu ----
		config.menu_items = []
		# Track routes to prevent duplicates
		seen_routes = set()
		for page in created_pages:
			route = page["route"]
			# Skip if route already added (prevents "/" duplication)
			if route in seen_routes:
				continue
			seen_routes.add(route)

			# Use "Accueil" for home page, otherwise use page title
			label = "Accueil" if route == "/" else page["title"]

			config.append("menu_items", {
				"label": label,
				"url": route,
				"is_external": False,
				"open_in_new_tab": False,
			})

		# ---- Update Footer ----
		# Footer logo: same as header
		if hasattr(config, "footer_logo_type"):
			config.footer_logo_type = config.logo_type
		if hasattr(config, "footer_logo_text"):
			config.footer_logo_text = config.logo_text
		if hasattr(config, "footer_logo_image"):
			config.footer_logo_image = config.logo_image
		if hasattr(config, "show_footer_logo"):
			config.show_footer_logo = True

		# Footer description: extract from prompt
		if hasattr(config, "footer_description"):
			# Use a short version of the prompt as description
			short_desc = prompt[:200] if len(prompt) > 200 else prompt
			# Clean up if it contains site name prefix
			if " - " in short_desc:
				short_desc = short_desc.split(" - ", 1)[1]
			config.footer_description = short_desc

		# Footer links: same as menu
		if hasattr(config, "footer_links"):
			config.footer_links = []
			for page in created_pages:
				route = page["route"]
				if route in seen_routes:
					label = "Accueil" if route == "/" else page["title"]
					config.append("footer_links", {
						"label": label,
						"url": route,
					})

		config.save(ignore_permissions=True)
		frappe.db.commit()

		# =====================================================================
		# STEP 5: Mark as completed
		# =====================================================================
		end_time = time.time()
		duration_seconds = int(end_time - start_time)
		duration_str = f"{duration_seconds // 60}m {duration_seconds % 60}s"

		_update_generation_status(job_id, {
			"status": "completed",
			"progress": 100,
			"total_pages": total_pages,
			"current_step": "Completed",
			"current_page": None,
			"pages_created": created_pages,
			"error": None,
			"site_name": site_name,
			"completed_at": frappe.utils.now(),
			"duration_seconds": duration_seconds,
			"duration": duration_str,
			"result": {
				"success": True,
				"pages": created_pages,
				"pages_generated": len(created_pages),
				"pages_failed": total_pages - len(created_pages),
				"duration": duration_str,
				"duration_seconds": duration_seconds,
				"config": {
					"site_type": site_type,
					"theme": theme,
					"logo_type": config.logo_type,
					"logo_value": config.logo_image if config.logo_type == "Image" else config.logo_text,
					"menu_items_count": len(config.menu_items),
				},
				"message": f"Site generated in {duration_str} with {len(created_pages)}/{total_pages} pages"
			}
		})

	except Exception as e:
		# Log error and update status
		frappe.log_error("Site generation failed", str(e))
		_update_generation_status(job_id, {
			"status": "failed",
			"progress": 0,
			"total_pages": total_pages,
			"current_step": "Failed",
			"current_page": None,
			"pages_created": [],
			"error": str(e),
			"site_name": site_name,
			"failed_at": frappe.utils.now(),
		})
		raise


@frappe.whitelist()
def get_site_generation_status(job_id: str):
	"""
	Get the status of a site generation job.

	Args:
		job_id: The job ID returned by generate_complete_site()

	Returns:
		dict: Job status with progress, current step, pages created, etc.
	"""
	return _get_generation_status(job_id)


# =============================================================================
# POSTHOG & OTHER UTILITIES
# =============================================================================

@frappe.whitelist()
def get_posthog_settings():
	can_record_session = False
	if start_time := frappe.db.get_default("session_recording_start"):
		time_difference = (
			frappe.utils.now_datetime() - frappe.utils.get_datetime(start_time)
		).total_seconds()
		if time_difference < 86400:  # 1 day
			can_record_session = True

	return {
		"posthog_project_id": frappe.conf.get(POSTHOG_PROJECT_FIELD),
		"posthog_host": frappe.conf.get(POSTHOG_HOST_FIELD),
		"enable_telemetry": frappe.get_system_settings("enable_telemetry"),
		"telemetry_site_age": frappe.utils.telemetry.site_age(),
		"record_session": can_record_session,
		"posthog_identifier": frappe.local.site,
	}


@frappe.whitelist()
def get_page_preview_html(page: str, **kwarg) -> Response:
	# to load preview without publishing
	frappe.form_dict.update(kwarg)
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
def upload_builder_asset():
	from frappe.handler import upload_file

	image_file = upload_file()
	if image_file.file_url.endswith((".png", ".jpeg", ".jpg")) and frappe.get_cached_value(
		"Builder Settings", "Builder Settings", "auto_convert_images_to_webp"
	):
		convert_to_webp(file_doc=image_file)
	return image_file


@frappe.whitelist()
def convert_to_webp(image_url: str | None = None, file_doc: Document | None = None) -> str:
	"""BETA: Convert image to webp format"""

	CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

	def is_external_image(image_url):
		return image_url.startswith("http") or image_url.startswith("https")

	def can_convert_image(extn):
		return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

	def get_extension(filename):
		return filename.split(".")[-1].lower()

	def convert_and_save_image(image, path):
		image.save(path, "WEBP")
		return path

	def update_file_doc_with_webp(file_doc, image, extn):
		webp_path = file_doc.get_full_path().replace(extn, "webp")
		convert_and_save_image(image, webp_path)
		delete_file(file_doc.get_full_path())
		file_doc.file_url = f"{file_doc.file_url.replace(extn, 'webp')}"
		file_doc.save()
		return file_doc.file_url

	def create_new_webp_file_doc(file_url, image, extn):
		files = frappe.get_all("File", filters={"file_url": file_url}, fields=["name"], limit=1)
		if files:
			_file = frappe.get_doc("File", files[0].name)
			webp_path = _file.get_full_path().replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			new_file = frappe.copy_doc(_file)
			new_file.file_name = f"{_file.file_name.replace(extn, 'webp')}"
			new_file.file_url = f"{_file.file_url.replace(extn, 'webp')}"
			new_file.save()
			return new_file.file_url
		return file_url

	def handle_image_from_url(image_url):
		image_url = unquote(image_url)
		response = requests.get(image_url)
		image = Image.open(BytesIO(response.content))
		filename = image_url.split("/")[-1]
		extn = get_extension(filename)
		if can_convert_image(extn) or is_external_image(image_url):
			_file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"{filename.replace(extn, 'webp')}",
					"file_url": f"/files/{filename.replace(extn, 'webp')}",
				}
			)
			webp_path = _file.get_full_path()
			convert_and_save_image(image, webp_path)
			_file.save()
			return _file.file_url
		return image_url

	if not image_url and not file_doc:
		return ""

	if file_doc:
		if file_doc.file_url.startswith("/files"):
			image, filename, extn = get_local_image(file_doc.file_url)
			if can_convert_image(extn):
				return update_file_doc_with_webp(file_doc, image, extn)
		return file_doc.file_url

	image_url = image_url or ""
	if image_url.startswith("/files"):
		image, filename, extn = get_local_image(image_url)
		if can_convert_image(extn):
			return create_new_webp_file_doc(image_url, image, extn)
		return image_url

	if image_url.startswith("/builder_assets"):
		image_path = os.path.abspath(frappe.get_app_path("builder", "www", image_url.lstrip("/")))
		image_path = image_path.replace("_", "-")
		image_path = image_path.replace("/builder-assets", "/builder_assets")

		image = Image.open(image_path)
		extn = get_extension(image_path)
		if can_convert_image(extn):
			webp_path = image_path.replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			return image_url.replace(extn, "webp")
		return image_url

	if image_url.startswith("http"):
		return handle_image_from_url(image_url)

	return image_url


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	if frappe.has_permission("Builder Page", ptype="write"):
		return True

	return False


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
def update_page_folder(pages: list[str], folder_name: str) -> None:
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to update page folder.")
	for page in pages:
		frappe.db.set_value("Builder Page", page, "project_folder", folder_name, update_modified=False)


@frappe.whitelist()
def duplicate_page(page_name: str):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to duplicate a page.")
	page = frappe.get_doc("Builder Page", page_name)
	new_page = frappe.copy_doc(page)
	del new_page.page_name
	new_page.route = None
	client_scripts = page.client_scripts
	new_page.client_scripts = []
	for script in client_scripts:
		builder_script = frappe.get_doc("Builder Client Script", script.builder_script)
		new_script = frappe.copy_doc(builder_script)
		new_script.name = f"{builder_script.name}-{frappe.generate_hash(length=5)}"
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})
	new_page.insert()
	return new_page


@frappe.whitelist()
def delete_folder(folder_name: str) -> None:
	if not frappe.has_permission("Builder Project Folder", ptype="write"):
		frappe.throw("You do not have permission to delete a folder.")

	# remove folder from all pages
	pages = frappe.get_all("Builder Page", filters={"project_folder": folder_name}, fields=["name"])
	for page in pages:
		frappe.db.set_value("Builder Page", page.name, "project_folder", "", update_modified=False)

	frappe.db.delete("Builder Project Folder", {"folder_name": folder_name})


@frappe.whitelist()
def sync_component(component_id: str):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to sync a component.")

	component = frappe.get_doc("Builder Component", component_id)
	component.sync_component()


@frappe.whitelist()
def get_page_analytics(
	route=None, interval: str = "daily", from_date=None, to_date=None, route_filter_type: str = "wildcard"
):
	return builder_analytics.get_page_analytics(
		route=route,
		interval=interval,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


@frappe.whitelist()
def get_overall_analytics(
	interval: str = "daily", route=None, from_date=None, to_date=None, route_filter_type: str = "wildcard"
):
	return builder_analytics.get_overall_analytics(
		interval=interval,
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


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
def reorder_client_scripts(script_order):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to reorder client scripts")

	if isinstance(script_order, str):
		script_order = frappe.parse_json(script_order)

	for idx, script_name in enumerate(script_order, start=1):
		frappe.db.set_value("Builder Page Client Script", script_name, "idx", idx)


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
def subscribe_to_newsletter(email: str, email_group: str = None):
	"""
	Subscribe an email address to an Email Group (newsletter).

	Args:
		email: Email address to subscribe
		email_group: Name of the Email Group (optional, uses config default if not provided)

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

	# Get email group from config if not provided
	if not email_group:
		config = frappe.get_single("Website Header Footer Config")
		email_group = getattr(config, "newsletter_email_group", None)

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
	from builder.ai.generators.image_generator import ImageGenerator

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


@frappe.whitelist()
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
