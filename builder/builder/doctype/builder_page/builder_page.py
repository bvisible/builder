# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import copy
import hashlib
import re
from typing import Any
from urllib.parse import quote_plus

import bs4 as bs
import frappe
import frappe.utils
from frappe.utils import now, set_request
from frappe.utils.caching import redis_cache
from frappe.utils.jinja import render_template
from frappe.utils.telemetry import capture
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.path_resolver import evaluate_dynamic_routes
from frappe.website.path_resolver import resolve_path as original_resolve_path
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator
from werkzeug.routing import Map

from builder.builder.component_versions import (
	collect_restore_warnings,
	ensure_component_version,
	is_pin_outdated,
	pin_components_in_page_data,
	resolve_component,
)
from builder.builder.doctype.builder_project_folder.builder_project_folder import is_system_activity
from builder.builder.doctype.builder_snapshot.builder_snapshot import (
	prune_snapshots,
	take_snapshot,
)
from builder.builder.doctype.user_font.user_font import get_all_user_fonts
from builder.editor_demo import is_demo_page
from builder.export_import_standard_page import export_page_as_standard
from builder.hooks import builder_path
from builder.html_preview_image import generate_preview
from builder.template_sync import delete_template_page_fixture, export_template_group
# //// Neoffice — upstream's save_as_template path uses Block, export_to_files and
# //// copy_img_to_asset_folder without importing them, so it NameErrors at runtime.
# //// We add the three imports (here and in the builder.utils list below) — 7cb4eca3.
# //// Upstreamable: drop these three if upstream ever adds them.
# bvisible: Block, copy_img_to_asset_folder and export_to_files are missing
# upstream too — their save_as_template path NameErrors at runtime without them.
from frappe.modules.export_file import export_to_files

from builder.utils import (
	# //// Neoffice — see the import note above (7cb4eca3).
	Block,
	ColonRule,
	camel_case_to_kebab_case,
	clean_data,
	compact_json,
	# //// Neoffice — see the import note above (7cb4eca3).
	copy_img_to_asset_folder,
	count_blocks,
	escape_single_quotes,
	execute_script,
	get_builder_page_preview_file_paths,
	is_bulk_import,
	is_component_used,
	merge_raw_styles_into_base_styles,
	normalize_legacy_raw_styles,
	sanitize_style_value,
	split_styles,
)

MOBILE_BREAKPOINT = 576
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024

# Number of "Publish" snapshots retained per page (manual snapshots are never auto-pruned)
KEEP_PUBLISH_SNAPSHOTS = 25

# live and staging pages both render at their route (use as or_filters)
SERVED_PAGE_FILTERS = {"published": 1, "staging": 1}


class BuilderPageRenderer(DocumentPage):
	def can_render(self):
		# //// Neoffice multi-site: resolve against the current site's profile
		if page := find_page_with_path(self.path, _current_site_profile()):
			self.doctype = "Builder Page"
			self.docname = page
			self.validate_access()
			return True

		# //// Neoffice multi-site — claim a route that belongs to ANOTHER site of this instance
		# //// and answer 404 ourselves (2026-09-16). Declining used to hand the route straight to
		# //// frappe's DocumentPage, which found the very same Builder Page by route and served
		# //// it, 200: every site on the instance served every other site's pages. Custom
		# //// renderers are tried before DocumentPage, so claiming it here is what actually
		# //// closes that door — and it is also the only way to return a REAL 404. Raising
		# //// PageDoesNotExistError during render lands in upstream's handle_exception, which
		# //// passes the request's own status through: the not-found page came back as 200.
		if _route_of_another_site(self.path, _current_site_profile()) and not _served_before_document_page(
			self.path, self.http_status_code
		):
			self.belongs_to_another_site = True
			return True

		# //// Neoffice multi-site: dynamic routes resolved against the request's Website
		# //// Profile — a page tagged for another profile must not answer here (c3f2a043).
		for d in get_web_pages_with_dynamic_routes(_current_site_profile()):
			try:
				if evaluate_dynamic_routes([ColonRule(f"/{d.route}", endpoint=d.name)], self.path):
					self.doctype = "Builder Page"
					self.docname = d.name
					self.validate_access()
					return True
			except (ValueError, LookupError):
				continue

		return False

	def render(self):
		# //// Neoffice multi-site — a route claimed above only to be refused (see can_render).
		if getattr(self, "belongs_to_another_site", False):
			from frappe.website.page_renderers.not_found_page import NotFoundPage

			return NotFoundPage(self.path).render()
		return super().render()

	def validate_access(self):
		if self.docname:
			self.doc = frappe.get_cached_doc(self.doctype, self.docname)
			if self.doc.authenticated_access and frappe.session.user == "Guest":
				raise frappe.PermissionError(frappe._("Please log in to view this page."))

	def set_canonical_url(self):
		if not self.doc:
			return
		context = getattr(self, "context", frappe._dict())
		# //// Neoffice multi-site: canonical follows the resolved Website Profile's
		# //// domain and the requested path (a per-profile home canonicalizes to "/",
		# //// not to its internal route). An explicit per-page canonical still wins.
		profile = getattr(frappe.local, "website_profile_doc", None)
		if profile and profile.get("primary_domain") and not self.doc.canonical_url:
			if profile.get("home_route") and self.doc.route == profile["home_route"]:
				# //// the profile's home always canonicalizes to the site root, whatever
				# //// URL it was reached through — deterministic even when the first
				# //// render freezes into the per-profile page cache.
				context["canonical_url"] = f"https://{profile['primary_domain']}/"
			else:
				request = getattr(frappe.local, "request", None)
				request_path = (request.path if request is not None else "/" + self.path) or "/"
				context["canonical_url"] = f"https://{profile['primary_domain']}{request_path}"
		elif self.doc.is_home_page():
			context["canonical_url"] = frappe.utils.get_url()
		elif self.doc.canonical_url:
			context["canonical_url"] = render_template(self.doc.canonical_url, context)
		else:
			context["canonical_url"] = frappe.utils.get_url(self.path)
		self.context = context

	def set_missing_values(self):
		self.set_canonical_url()


class BuilderPage(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from builder.builder.doctype.builder_page_client_script.builder_page_client_script import (
			BuilderPageClientScript,
		)

		app: DF.Literal[None]
		authenticated_access: DF.Check
		blocks: DF.LongText | None
		body_html: DF.Code | None
		canonical_url: DF.Data | None
		client_scripts: DF.TableMultiSelect[BuilderPageClientScript]
		disable_indexing: DF.Check
		draft_blocks: DF.LongText | None
		dynamic_route: DF.Check
		favicon: DF.AttachImage | None
		head_html: DF.Code | None
		is_standard: DF.Check
		is_template: DF.Check
		language: DF.Data | None
		meta_description: DF.SmallText | None
		meta_image: DF.AttachImage | None
		page_data_script: DF.Code | None
		page_name: DF.Data | None
		page_title: DF.Data | None
		preview: DF.Data | None
		project_folder: DF.Link | None
		published: DF.Check
		published_at: DF.Datetime | None
		route: DF.Data | None
		staging: DF.Check
		template_group: DF.Data | None
	# end: auto-generated types

	def onload(self):
		self.set_onload("builder_path", builder_path)

	website = frappe._dict(
		template="templates/generators/webpage.html",
		condition_field="published",
		page_title_field="page_title",
	)

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=8)}"

	def before_insert(self):
		self.process_blocks()
		self.set_preview()
		self.set_default_values()

	# the name is only final after insert: naming wipes whatever before_insert set
	def after_insert(self):
		capture("builder_page_created", "builder", properties=self.creation_event_properties())

	# every write path, not just insert: callers that hand over a block tree
	# (paste, AI writes, the API) would otherwise fail on update with
	# "Value for Blocks cannot be a list"
	def before_save(self):
		self.process_blocks()

	def process_blocks(self):
		for block_type in ["blocks", "draft_blocks"]:
			if isinstance(getattr(self, block_type), list):
				setattr(self, block_type, compact_json(getattr(self, block_type)))
		if not self.blocks:
			self.blocks = "[]"

	def set_preview(self):
		if not self.preview:
			self.preview = "/assets/builder/images/fallback.png"
		else:
			self.flags.skip_preview = True

	def set_default_values(self):
		if not self.page_title:
			self.page_title = "My Page"
		if not (self.route or "").strip():
			if not self.name:
				self.autoname()
			self.route = f"pages/{self.name}"

	def block_count(self) -> int:
		return count_blocks(self.draft_blocks or self.blocks)

	def creation_event_properties(self) -> dict:
		block_count = self.block_count()
		# template and duplicate are stamped by their api entry points; anything
		# else arriving with content (paste, REST) is an import
		return {
			"page": self.name,
			"source": self.flags.source or ("blank" if block_count <= 1 else "import"),
			"template_page": self.flags.template_page,
			"block_count": block_count,
		}

	def publish_event_properties(self, is_first_publish: bool) -> dict:
		return {
			"page": self.name,
			"is_first_publish": is_first_publish,
			"seconds_since_created": int(frappe.utils.time_diff_in_seconds(now(), self.creation)),
			"block_count": self.block_count(),
			"has_client_script": bool(self.client_scripts),
			"has_data_script": bool(self.page_data_script),
		}

	def validate(self):
		super().validate()  # WebsiteGenerator route normalization
		self.validate_route_variables()

		# pages of shipped template groups can only be edited in developer mode
		if (
			self.is_template
			and self.template_group
			and not frappe.conf.get("developer_mode")
			and not is_system_activity()
		):
			frappe.throw(
				frappe._("Template pages can only be modified in developer mode."),
				frappe.PermissionError,
			)

	# //// Neoffice — added. Upstream enqueues a preview only from publish(), so a page born
	# //// anywhere else (the AI chat, a WordPress import, the REST API) kept the blank
	# //// fallback forever and the dashboard was a wall of white rectangles (c84c6bf8).
	FALLBACK_PREVIEW = "/assets/builder/images/fallback.png"

	def ensure_preview(self):
		"""Give a thumbnail to pages that never went through publish().

		publish() is the only path that used to enqueue a preview, so every
		page born anywhere else — the AI chat, a WordPress import, the REST
		API — kept the blank fallback forever and the dashboard was a wall of
		white rectangles.

		Fires once: as soon as the page has content and a preview exists, the
		guard below stops matching.
		"""
		if self.flags.get("skip_preview") or not self.published:
			return
		if self.preview and self.preview != self.FALLBACK_PREVIEW:
			return
		if not self.blocks or self.blocks == "[]":
			return
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"generate_page_preview_image",
			queue="short",
			enqueue_after_commit=True,
		)


	def set_route(self):
		if self.route:
			# frappe trims slashes and dots but keeps whitespace, which reaches URLs as %20
			self.route = self.route.strip("/. \t\n")
		super().set_route()

	def validate_route_variables(self):
		if not self.route or not (":" in self.route or "<" in self.route):
			return
		try:
			Map([ColonRule(f"/{self.route}", endpoint=self.name)])
		except (ValueError, LookupError):
			frappe.throw(
				frappe._(
					"Route variables can only use letters, numbers and underscores, like :slug or <slug>"
				)
			)

	def on_update(self):
		# //// Neoffice — on_update is the one hook every creation path goes through (c84c6bf8).
		self.ensure_preview()

		if self.has_value_changed("route"):
			if self.route and (":" in self.route or "<" in self.route):
				self.db_set("dynamic_route", 1)
			else:
				self.db_set("dynamic_route", 0)

		if (
			self.has_value_changed("dynamic_route")
			or self.has_value_changed("route")
			or self.has_value_changed("published")
			or self.has_value_changed("published_at")
			or self.has_value_changed("staging")
			or self.has_value_changed("disable_indexing")
			or self.has_value_changed("blocks")
		):
			self.clear_route_cache()

		if self.has_value_changed("published") and not self.published and not self.is_new():
			capture("builder_page_unpublished", "builder", properties={"page": self.name})

		if self.has_value_changed("published") and not self.published:
			# if this is homepage then clear homepage from builder settings
			if frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page") == self.route:
				frappe.db.set_value("Builder Settings", "Builder Settings", "home_page", None)

		if (
			frappe.conf.developer_mode
			and self.is_template
			and self.template_group
			and not is_system_activity()
		):
			# target app is the hub on the hub site (template_target_app=builder_hub),
			# builder by default — keeps builder from importing the hub (circular)
			export_template_group(
				self.template_group, target_app=frappe.conf.get("template_target_app") or "builder"
			)

		self.export_standard_files()

		previous_app = doc_before.app if (doc_before := self.get_doc_before_save()) else None
		if previous_app and (not self.is_standard or previous_app != self.app):
			self.cleanup_standard_page_exports(previous_app)

	def clear_route_cache(self):
		get_web_pages_with_dynamic_routes.clear_cache()
		# //// Neoffice — the cached lookup behind find_page_with_path (see _find_page_with_path_cached)
		_find_page_with_path_cached.clear_cache()
		clear_cache(self.route)

	def cleanup_standard_page_exports(self, app: str) -> None:
		"""Delete this page's exported files, and its orphaned dependencies, from the given app."""
		if not app or not frappe.conf.developer_mode:
			return
		doc_before = self.get_doc_before_save()

		from builder.export_import_standard_page import (
			delete_standard_client_script_files,
			delete_standard_component_files,
			delete_standard_font_files,
			delete_standard_page_files,
			delete_standard_variable_files,
			extract_components_from_blocks,
			extract_fonts_from_blocks,
			extract_variables_from_blocks,
		)

		def delete_standard_dependency_if_unreferenced(doctype, identifier, app, delete_files) -> None:
			"""Delete a dependency's exported files unless another standard page in the app still references it."""
			# blocks name fonts and tokens with no record; the export skips those too
			if not frappe.db.exists(doctype, identifier):
				return
			referencing_pages = frappe.get_doc(doctype, identifier).get_referencing_pages(
				filters={"is_standard": 1}, fields=["name", "app"]
			)
			referencing_apps = [page.app for page in referencing_pages if page.name != self.name]
			if app not in referencing_apps:
				delete_files(identifier, app)

		delete_standard_page_files(self.page_name, app)

		client_scripts = doc_before.client_scripts if doc_before else self.client_scripts
		blocks = frappe.parse_json(self.draft_blocks or self.blocks)

		dependencies = [
			(
				"Builder Client Script",
				[row.builder_script for row in client_scripts],
				delete_standard_client_script_files,
			),
			("Builder Component", extract_components_from_blocks(blocks), delete_standard_component_files),
			("Builder Token", extract_variables_from_blocks(blocks), delete_standard_variable_files),
			("User Font", extract_fonts_from_blocks(blocks), delete_standard_font_files),
		]

		for doctype, identifiers, delete_files in dependencies:
			for identifier in identifiers:
				delete_standard_dependency_if_unreferenced(doctype, identifier, app, delete_files)

	def on_trash(self):
		# //// Neoffice — a deleted page leaves the route lookup (2026-09-17). Upstream cleared it on
		# //// save only: after a rebuild deleted a profile's home, find_page_with_path kept answering
		# //// the deleted name for an hour, and the site's root fell through to another page.
		self.clear_route_cache()
		for session in frappe.get_all("Builder AI Session", filters={"page": self.name}, pluck="name"):
			# another user's chat on this page goes too, whoever deletes the page
			frappe.delete_doc("Builder AI Session", session, ignore_missing=True, ignore_permissions=True)

		if self.is_template and self.template_group:
			if frappe.conf.developer_mode:
				delete_template_page_fixture(self, app=frappe.conf.get("template_target_app") or "builder")
			elif not is_system_activity():
				frappe.throw(
					frappe._("Template pages can only be deleted in developer mode."),
					frappe.PermissionError,
				)
		# clean up snapshots (reference_name is plain Data, so no link-guard removes them)
		frappe.db.delete(
			"Builder Snapshot", {"reference_doctype": "Builder Page", "reference_name": self.name}
		)

		if self.is_standard and self.app and frappe.conf.developer_mode:
			self.cleanup_standard_page_exports(self.app)

	def after_rename(self, old: str, new: str, merge: bool = False) -> None:
		if not (self.is_standard and self.app and frappe.conf.developer_mode):
			return
		from builder.export_import_standard_page import delete_standard_page_files

		# rename_doc skips on_update, and the exported JSON holds the old name
		delete_standard_page_files(old, self.app)
		self.export_standard_files()

	def export_standard_files(self) -> None:
		if not (frappe.conf.developer_mode and self.is_standard and self.app) or is_bulk_import():
			return
		export_page_as_standard(self.name, target_app=self.app)

	def add_comment(self, comment_type="Comment", text=None, comment_email=None, comment_by=None):
		if comment_type in ["Attachment Removed", "Attachment"]:
			return

		super().add_comment(
			comment_type=comment_type,
			text=text,
			comment_email=comment_email,
			comment_by=comment_by,
		)

	@frappe.whitelist()
	def publish(self):
		is_first_publish = not self.published and not self.published_at
		self.published = 1
		self.staging = 0
		self.published_at = now()
		self.promote_draft_blocks()
		self.save()
		capture(
			"builder_page_published", "builder", properties=self.publish_event_properties(is_first_publish)
		)
		self.enqueue_preview_image()
		return self.route

	@frappe.whitelist()
	def publish_to_staging(self):
		"""Serve the page at its route like a live page, but keep it out of search engines and
		the sitemap (Frappe's sitemap lists only `published` pages). A live page moves there with
		`mark_as_staging` instead, so a stale editor can't take a page off live by publishing."""
		if self.published:
			frappe.throw(frappe._("This page is live. Mark it as staging instead."))
		self.staging = 1
		self.promote_draft_blocks()
		self.save()
		capture("builder_page_staged", "builder", properties={"page": self.name})
		self.enqueue_preview_image()
		return self.route

	@frappe.whitelist()
	def mark_as_staging(self):
		"""Move a live page to staging. Its live content stays at its route, and unpublished
		edits stay in the draft."""
		if not self.published:
			frappe.throw(frappe._("Only a live page can be marked as staging."))
		self.published = 0
		self.staging = 1
		self.save()
		capture("builder_page_staged", "builder", properties={"page": self.name})

	def promote_draft_blocks(self):
		if not self.draft_blocks:
			return
		# snapshot the content being published; blocks (ideally) already carry componentVersion pins
		# from when each component was used in the page (pinned at drag-drop), if not they are pinned now
		take_snapshot(
			"Builder Page",
			self.name,
			fields=["draft_blocks", "page_data_script"],
			snapshot_type="Publish",
			transform=pin_components_in_page_data,
		)
		prune_snapshots("Builder Page", self.name, keep=KEEP_PUBLISH_SNAPSHOTS, snapshot_type="Publish")
		self.blocks = self.draft_blocks
		self.draft_blocks = None

	def enqueue_preview_image(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"generate_page_preview_image",
			queue="short",
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def unpublish(self):
		self.published = 0
		self.staging = 0
		self.save()

	@frappe.whitelist()
	def create_manual_snapshot(self, label: str | None = None):
		# snapshot the current working content (unpublished draft if present, else live)
		field = "draft_blocks" if self.draft_blocks else "blocks"
		if not self.get(field):
			return
		return take_snapshot(
			"Builder Page",
			self.name,
			fields=[field, "page_data_script"],
			snapshot_type="Manual",
			label=label,
			transform=pin_components_in_page_data,
		)

	@frappe.whitelist()
	def restore_snapshot(self, snapshot: str):
		# restore into the draft for review (non-destructive); user publishes to go live
		snap = frappe.get_doc("Builder Snapshot", snapshot)
		if snap.reference_doctype != "Builder Page" or snap.reference_name != self.name:
			frappe.throw(frappe._("Snapshot does not belong to this page"))
		data = frappe.parse_json(snap.data)
		# stored blocks already carry pinned component versions; key depends on capture-time state
		blocks = data.get("draft_blocks") or data.get("blocks")
		# re-compact: older snapshots may hold pretty-printed blocks
		if blocks:
			blocks = compact_json(frappe.parse_json(blocks))
		self.draft_blocks = blocks
		if "page_data_script" in data:
			self.page_data_script = data.get("page_data_script")
		# AI snapshots also capture client scripts (publish/manual ones don't), so a single
		# revert restores them: re-set the page's links to the pre-turn set (this unlinks any
		# scripts the turn created) and restore each captured script's content (this reverts
		# scripts the turn edited).
		if "client_scripts" in data:
			self.set(
				"client_scripts",
				[{"builder_script": s.get("builder_script")} for s in (data.get("client_scripts") or [])],
			)
		self.save()
		for name, content in (data.get("_ai_scripts") or {}).items():
			if not frappe.db.exists("Builder Client Script", name):
				continue
			# Save through the doc (NOT db.set_value): on_update regenerates the public JS/CSS
			# file the published page actually loads (via public_url). A bare db write reverts
			# the field but leaves the stale file, so publish would keep serving the old script.
			script_doc = frappe.get_doc("Builder Client Script", name)
			script_doc.script = content.get("script")
			script_doc.script_type = content.get("script_type")
			script_doc.save(ignore_permissions=True)
		return {"draft_blocks": blocks, "warnings": collect_restore_warnings(blocks)}

	@frappe.whitelist()
	def get_current_component_version(self, component_id: str):
		# mint/reuse a version of the component's current state for the editor to re-pin to
		return ensure_component_version(component_id)

	@frappe.whitelist()
	def get_outdated_component_pins(self, pins: str):
		# of the editor's pinned (component_id, version) pairs, return those whose live component changed
		pins = frappe.parse_json(pins) if isinstance(pins, str) else pins
		outdated = []
		for pin in pins or []:
			component_id, version = pin.get("component_id"), pin.get("version")
			if component_id and version and is_pin_outdated(component_id, version):
				outdated.append({"component_id": component_id, "version": version})
		return outdated

	def _refuse_another_sites_page(self):
		"""404 a page that belongs to another site of this instance.

		//// Neoffice — untagged pages still serve everywhere, which is the rule this instance
		//// already relies on, and nothing is refused when no profile is resolved: that is the
		//// editor, the build's own server-side render, and every instance with no Website
		//// Profile at all."""
		if not _page_has_site_field():
			return
		# //// Neoffice — an editor's preview is not a visitor's request. get_page_preview_html
		# //// renders a page BY NAME for someone who already holds read permission on it, from
		# //// whichever domain the editor happens to be open on — so the profile of that domain
		# //// says nothing about what may be previewed. Without this, previewing any page of
		# //// another site of the instance answered 404 (measured, and it broke the editor).
		if getattr(getattr(frappe.local, "request", None), "for_preview", None):
			return
		mine = self.get("neo_website_profile")
		here = _current_site_profile()
		if mine and here and mine != here:
			raise frappe.PageDoesNotExistError

	def get_context(self, context):
		# //// Neoffice multi-site — the guard of last resort (2026-09-16). BuilderPageRenderer
		# //// already refuses a page tagged for ANOTHER site, but frappe tries its renderers in
		# //// turn: when ours declines, upstream's DocumentPage picks the very same Builder Page
		# //// up by route and serves it. Measured on a two-site instance — one site's domain
		# //// answered the other's /a-propos and /nos-marques, 200, with no canonical, because
		# //// the render never went through our renderer at all. A check that one renderer makes
		# //// is not isolation; this one lives where every renderer has to pass.
		self._refuse_another_sites_page()
		# delete default favicon
		del context.favicon
		context.disable_indexing = self.disable_indexing or self.staging

		context.preview = getattr(getattr(frappe.local, "request", None), "for_preview", None)

		if context.preview:
			context.disable_auto_dark_mode = 0
			# /builder_assets/tokens.css is a rendered route, not a real file, so
			# the preview/PDF generator can't fetch it. Inline the variables instead.
			from builder.builder.doctype.builder_token.builder_token import get_variables_css

			context.inline_tokens_css = get_variables_css()
			# Honour the dark/light mode the editor previews in (canvasDarkMode), so the
			# initial server render matches it instead of falling back to the OS scheme.
			scheme = frappe.form_dict.get("prefers_color_scheme")
			if scheme in ("dark", "light"):
				context.prefers_color_scheme = scheme
		else:
			context.disable_auto_dark_mode = frappe.get_cached_value(
				"Builder Settings", "Builder Settings", "disable_auto_dark_mode"
			)

		page_data = self._get_page_data(for_render=True)
		# //// Neoffice — upstream sets context.title only when page_data carries a title, so a
		# //// page without one fell back to the route name in <title>, e.g. "Homepage" (6fef27d8).
		# page_data may override the title; otherwise the page's own title is the
		# <title> (it previously fell back to the route name, e.g. "Homepage").
		# //// Neoffice — in another language of the site the title is the page's translated one (builder/translation.py)
		from builder.translation import localize_blocks, page_text

		context.title = page_data.get("title") or page_text(self, "page_title")

		blocks = self.blocks

		if context.preview and self.draft_blocks:
			blocks = self.draft_blocks

		# //// Neoffice — an include with nothing to show on this site (a map without an address,
		# //// hours never typed, an empty team) is not drawn, nor the short heading announcing it:
		# //// the page kept a label over an empty space (builder/empty_includes.py, 2026-09-13).
		from builder.empty_includes import prune_for_render

		blocks = prune_for_render(blocks, getattr(frappe.local, "website_profile", None))
		# //// Neoffice — a filled button is drawn in the variant that reads on its section with the
		# //// theme of this render (builder/site_ai/nora/buttons.py settle_for_render, 2026-09-13):
		# //// the rule for the buttons' colour changed under pages written before it, and a primary
		# //// button of a dark site went pink on a pink band. The stored variant stays the author's.
		from builder.site_ai.nora.buttons import settle_for_render

		blocks = settle_for_render(blocks)
		# //// Neoffice — and copy inside the design system's scrim reads on it (2026-09-15,
		# //// builder/site_ai/nora/contrast.py scrim_ink_for_render): a hero's heading was white and
		# //// read while its "Shop now" link, written black, was invisible on the same photograph.
		# //// The build repairs a page as it writes it; this covers the ones written before the rule.
		from builder.site_ai.nora.contrast import scrim_ink_for_render

		blocks = scrim_ink_for_render(blocks)
		# //// Neoffice — a photo slot never filled (a page written before 2026-09-09, or one whose
		# //// picture the image job is still drawing) is drawn as a plain block in the site's colours,
		# //// not as the third party's grey placeholder with its caption across the hero
		# //// (builder/site_ai/nora/placeholders.py neutral_for_render, 2026-09-13).
		from builder.site_ai.nora.placeholders import neutral_for_render

		blocks = neutral_for_render(blocks)
		# //// Neoffice — multilingual lot 4 (neoffice-maintenance#2032): in another language of the site the page is the
		# //// same page with its texts replaced by their translation, found by block id. Last of the render transforms, so
		# //// they all see the page as it was written; a site with no additional language gets its blocks back untouched.
		blocks = localize_blocks(blocks, self.name)
		content, style, fonts, has_dual_mode_image = get_block_html(blocks)

		# Propagate the root block's background to html/body. Otherwise a full-bleed
		# (e.g. all-black) page paints only its root <div>, and everything the div
		# doesn't cover — the preview screenshot's canvas, a short page's tail,
		# overscroll — falls through to the browser's default white.
		context.page_background = get_root_background(blocks)

		if self.dynamic_route or page_data or self.page_data_script:
			context.no_cache = 1
		context.has_dual_mode_image = has_dual_mode_image

		# //// Neoffice — the one runtime behind every contact form of a generated site
		# //// (public/js/neo_contact_form.js, neoffice-maintenance#1593): the signed token, the minimum
		# //// delay, the field only a script fills, the steps and the fallback to the stock URL. A page
		# //// carries it only if it has a form — a block template of the editor, which renders
		# //// data-neo-contact, or the Jinja include, whose {% include %} is still unrendered in
		# //// `content` at this point. Loaded here and NOT by web_include_js: frappe renders those in
		# //// base.html, and a Builder page never goes through it (our templates/generators/webpage.html
		# //// owns the document), so a page had no script at all and the form sent nothing.
		# //// Neoffice — site_form.html (a form kept as data, 2026-10-20) is the other include that draws a form
		context.has_contact_form = (
			"data-neo-contact" in content or "contact_form.html" in content or "site_form.html" in content
		)
		if context.has_contact_form:
			from builder.hooks import _asset_version

			context.contact_form_script = (
				f"/assets/builder/js/neo_contact_form.js?v={_asset_version('js/neo_contact_form.js')}"
			)

		self.set_custom_font(context, fonts)
		# //// Neoffice — the site's own copy of each Google stylesheet (SEO / GEO plan, D-10): a page
		# //// that linked fonts.googleapis.com handed every visitor's IP address to Google. The copy is
		# //// made once, server side, by builder/hosted_fonts.py.
		from builder.hosted_fonts import local_urls

		context.font_urls = local_urls(get_google_font_urls(fonts))
		context.__content = content
		context.style = render_template(style, page_data)
		context.editor_link = f"/{builder_path}/page/{self.name}"
		if frappe.form_dict and self.dynamic_route:
			query_string = "&".join(
				[
					f"{frappe.utils.escape_html(frappe.utils.quote(k))}={frappe.utils.escape_html(frappe.utils.quote(v))}"
					for k, v in frappe.form_dict.items()
				]
			)
			context.editor_link += f"?{query_string}"

		context.page_name = self.name
		if is_demo_page(self.name) and not context.preview:
			context.editor_demo_url = f"/{builder_path}/demo/{self.name}"
			# the file is served immutable for a year, so a build has to change its URL
			version = frappe.utils.get_build_version()
			context.editor_demo_script = f"/assets/builder/js/editor_demo.js?v={version}"
		if context.preview:
			if self.dynamic_route and hasattr(frappe.local, "request"):
				context.base_url = frappe.utils.get_url(frappe.local.request.path or self.route)
			else:
				context.base_url = frappe.utils.get_url(self.route)

		context.update(page_data)

		self.set_style_and_script(context)
		self.set_meta_tags(context=context, page_data=page_data)
		self.set_favicon(context)
		# //// Neoffice — the site's identity for search engines, on its home page (site_graph.py)
		self.set_site_graph(context)
		self.set_language(context)
		# tojson can't serialize dates or decimals; frappe's encoder can
		context.page_data = frappe.parse_json(frappe.as_json(clean_data(context.page_data)))
		# //// Neoffice — our templates/generators/webpage.html owns the document <body> (it wraps
		# //// the page in the site chrome), so a page's own <body> would nest one inside another.
		# //// Rewrite it into div.builder-page-content — which is also the anchor the tests scope
		# //// to (36cbdc0b, re-applied while resolving merge 721cf013).
		rendered_content = render_template(context.__content, context)
		# Replace <body> tags with <div> to avoid nested body elements
		# when the template already provides a body tag
		import re
		# //// Neoffice — merged into the body's own class list: the root block carries its style
		# //// class, so the rewrite wrote a second class attribute, which the browser drops, and
		# //// div.builder-page-content never existed on a generated page (2026-09-14).
		def _as_div(match):
			attrs = match.group(1)
			if re.search(r"\sclass=[\"']", attrs):
				return "<div" + re.sub(r"(\sclass=[\"'])", r"\1builder-page-content ", attrs, count=1) + ">"
			return f'<div{attrs} class="builder-page-content">'

		rendered_content = re.sub(r"<body([^>]*)>", _as_div, rendered_content)
		rendered_content = re.sub(r'</body>', '</div>', rendered_content)
		# //// Neoffice — a page that opens on its own title carries its breadcrumb trail under that title,
		# //// in its own top (page_header.place_page_crumbs, 2026-09-14). Written into the rendered markup,
		# //// after the page's Jinja ran, so no page title ever reaches the template engine.
		from builder.page_header import place_page_crumbs

		rendered_content = place_page_crumbs(rendered_content, self)
		context["__content"] = rendered_content

	def set_meta_tags(self, context, page_data=None):
		# //// Neoffice — page_text renders metatags in the request's language, by block id
		# //// (28970a28 "feat(translation): a page and the site chrome are shown in the
		# //// language of the request by projection (multilingual lot 4, neoffice-maintenance#2032)")
		from builder.translation import page_text

		if not page_data:
			page_data = {}

		metatags = {
			# //// Neoffice — the page's title and description in the language of the request (builder/translation.py)
			"title": page_text(self, "page_title") or "My Page",
			"description": page_text(self, "meta_description") or page_text(self, "page_title"),
			"image": self.meta_image or self.preview,
		}
		metatags.update(page_data.get("metatags", {}))
		context.metatags = metatags

	def set_favicon(self, context):
		# //// Neoffice — REWRITTEN: one icon for the whole site (builder/site_icon.py, 2026-09-24,
		# //// neoffice-maintenance#691 D27). Upstream took the page's favicon, then Builder
		# //// Settings', and our template fell back to Neoffice's SVG — which Google does not read
		# //// and which is not the client's. Website Settings' favicon, dropped by the `del
		# //// context.favicon` of get_context, was what the shop's pages of the same domain wore.
		# //// site_icon keeps upstream's order, then Website Settings', then an icon drawn from
		# //// the site's mark or initial; the standalone-bench fallback (3acfd7d6) lives there.
		from builder.site_icon import site_icon

		icon = site_icon(context.get("favicon") or self.favicon)
		context.site_icon = icon
		context.favicon = icon.href or None

	# //// Neoffice — added method (2026-09-24, neoffice-maintenance#691 lot 1): the site's WebSite and
	# //// Organization, declared once on its home page (builder/site_graph.py). A description of
	# //// the site must never cost the page: logged, and the page renders without it.
	def set_site_graph(self, context):
		from builder.site_graph import is_site_home, site_graph

		context.site_jsonld = None
		if not is_site_home(self):
			return
		try:
			context.site_jsonld = site_graph()
		except Exception:
			frappe.log_error("Site structured data failed", frappe.get_traceback())

	def set_language(self, context):
		# Set page-specific language or fall back to default language from Builder Settings
		context.language = self.language
		if not context.language:
			context.default_language = (
				# //// Neoffice — fall back to the request language before "en": a French bench served
				# //// lang="en" on every page with no explicit language (6fef27d8).
				frappe.get_cached_value("Builder Settings", "Builder Settings", "default_language")
				or frappe.local.lang
				or "en"
			)

	def is_component_used(self, component_id):
		if self.blocks and is_component_used(self.blocks, component_id):
			return True
		elif self.draft_blocks and is_component_used(self.draft_blocks, component_id):
			return True

	def set_style_and_script(self, context):
		builder_settings = frappe.get_cached_doc("Builder Settings", "Builder Settings")
		if builder_settings.script:
			context.setdefault("scripts", []).append(builder_settings.script_public_url)
		if builder_settings.style:
			context.setdefault("styles", []).append(builder_settings.style_public_url)

		client_scripts = self.get("client_scripts") or []
		for script in client_scripts:
			script_doc = frappe.get_cached_doc("Builder Client Script", script.builder_script)
			if script_doc.script_type == "JavaScript":
				context.setdefault("scripts", []).append(script_doc.public_url)
			else:
				context.setdefault("styles", []).append(script_doc.public_url)

		if not context.get("_head_html"):
			context._head_html = ""

		if not context.get("_body_html"):
			context._body_html = ""

		if builder_settings.head_html:
			context._head_html += builder_settings.head_html
		if builder_settings.body_html:
			context._body_html += builder_settings.body_html

		if self.head_html:
			context._head_html += self.head_html
		if self.body_html:
			context._body_html += self.body_html

		context["_head_html"] = render_template(context._head_html, context)
		context["_body_html"] = render_template(context._body_html, context)

	@frappe.whitelist()
	def get_page_data(self, route_variables: dict | None = None) -> dict:
		return self._get_page_data(route_variables=route_variables, for_render=False)

	def _get_page_data(self, route_variables: dict | None = None, for_render: bool = False) -> dict:
		if route_variables:
			frappe.form_dict.update({k: v for k, v in route_variables.items()})
		page_data = frappe._dict()
		if self.page_data_script:

			def redirect(location: str, http_status_code: int = 302):
				if for_render:
					frappe.local.flags.redirect_location = location
					raise frappe.Redirect(http_status_code)

			_locals = dict(data=frappe._dict(), redirect=redirect)
			execute_script(self.page_data_script, _locals, self.name)
			page_data.update(_locals["data"])

		# do not let users replace __content
		page_data.pop("__content", None)

		return page_data

	def generate_page_preview_image(self, html=None):
		public_path, local_path = get_builder_page_preview_file_paths(self)
		if not html:
			html = self.get_preview_html()

		generate_preview(
			html,
			local_path,
		)
		self.db_set("preview", public_path, commit=True, update_modified=False)

	def get_preview_html(self, color_scheme: str | None = None) -> str:
		"""Render this page in preview mode (uses draft_blocks when present), so a
		preview can be generated for unpublished/draft pages too — not just for
		pages reachable via their published route. `color_scheme` ("light"/"dark")
		forces that mode, as the editor's preview does."""
		# set_request() swaps frappe.local.request for a faked GET request. When
		# this runs synchronously inside a real web request (e.g. run_doc_method),
		# that clobbers the live request and drops its `after_response`, which
		# then breaks sync_database. Save and restore the original request.
		previous_request = getattr(frappe.local, "request", None)
		# //// Neoffice — the faked request never goes through the theme's before_request hook,
		# //// so a page of a secondary Website Profile was previewed inside the default site's
		# //// chrome (the agent's preview_page tool then "fixed" the wrong header, 2026-09-08).
		# //// Name the page's profile on frappe.local the way the hook would.
		previous_profile = (getattr(frappe.local, "website_profile", None), getattr(frappe.local, "website_profile_doc", None))
		# The render gets its own form_dict: a scheme left behind (even as None) leaks
		# into the caller's later renders, and dynamic routes quote every value.
		previous_form_dict = frappe.local.form_dict
		try:
			set_request(method="GET", path=f"/{self.route or ''}")
			frappe.local.request.for_preview = True
			frappe.local.no_cache = 1
			self._name_website_profile()  # //// Neoffice — see previous_profile above
			frappe.local.form_dict = frappe._dict(previous_form_dict)
			if color_scheme:
				frappe.local.form_dict.prefers_color_scheme = color_scheme
			renderer = BuilderPageRenderer(path="")
			renderer.docname = self.name
			renderer.doctype = "Builder Page"
			renderer.init_context()
			return str(renderer.render().data, "utf-8")
		finally:
			frappe.local.request = previous_request
			# //// Neoffice — see previous_profile above
			frappe.local.website_profile, frappe.local.website_profile_doc = previous_profile
			frappe.local.form_dict = previous_form_dict

	# //// Neoffice — see get_preview_html.
	def _name_website_profile(self) -> None:
		profile = self.get("neo_website_profile") if frappe.db.has_column("Builder Page", "neo_website_profile") else None
		if not profile:
			return
		try:
			from neoffice_theme.website_profiles import get_profiles_map
		except ImportError:
			return
		doc = next((p for p in (get_profiles_map() or {}).values() if p.get("name") == profile), None)
		if doc:
			frappe.local.website_profile = profile
			frappe.local.website_profile_doc = doc

	def set_custom_font(self, context, font_map):
		all_user_fonts = get_all_user_fonts()
		user_fonts = [f for f in all_user_fonts if f.font_name in font_map]
		if user_fonts:
			context.custom_fonts = user_fonts
		for font in user_fonts:
			font_map.pop(font.font_name, None)

	def replace_component(self, target_component, replace_with):
		updates = {}
		if self.blocks:
			blocks = frappe.parse_json(self.blocks)
			self.blocks = compact_json(replace_component_in_blocks(blocks, target_component, replace_with))
			updates["blocks"] = self.blocks
		if self.draft_blocks:
			draft_blocks = frappe.parse_json(self.draft_blocks)
			self.draft_blocks = compact_json(
				replace_component_in_blocks(draft_blocks, target_component, replace_with)
			)
			updates["draft_blocks"] = self.draft_blocks

		# one db_set (single commit per page) instead of one commit per field
		if updates:
			self.db_set(updates, commit=True, update_modified=False)

		self.clear_route_cache()

	def is_home_page(self):
		"""Check if this page is set as the home page in Builder Settings."""
		return frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page") == self.route


def replace_component_in_blocks(blocks, target_component, replace_with) -> list[dict]:
	for target_block in blocks:
		if target_block.get("extendedFromComponent") == target_component:
			new_component_block = frappe.parse_json(
				frappe.get_cached_value("Builder Component", replace_with, "block")
			)
			target_block.clear()
			target_block.update(new_component_block)
			target_block["extendedFromComponent"] = replace_with
			reset_with_component(target_block, replace_with, new_component_block.get("children"))
		else:
			target_block["children"] = replace_component_in_blocks(
				target_block.get("children", []) or [], target_component, replace_with
			)

	return blocks


@frappe.whitelist()
def get_block_data(
	block_id: str,
	block_data_script: str,
	props: str,
	prev_block_data: dict | None = None,
	route_variables: dict | None = None,
):
	if route_variables:
		frappe.form_dict.update({k: v for k, v in route_variables.items()})
	frappe.has_permission("Builder Page", "write", throw=True)
	props = frappe.parse_json(props or "{}")
	block_data = frappe._dict()
	_locals = dict(block=frappe._dict(prev_block_data or {}), props=props)
	execute_script(block_data_script, _locals, block_id)

	if isinstance(_locals["block"], dict):
		block_data = frappe._dict({k: v for k, v in _locals["block"].items() if prev_block_data.get(k) != v})
	return block_data


def get_root_background(blocks: str | list) -> str | None:
	"""The page's root (body) block background, to paint html/body so a full-bleed
	page has no white gaps. Returns a CSS value (color, var(--token), or gradient)
	or None when the root sets no background. `background`/`backgroundImage` (a
	gradient) win over a plain `backgroundColor`."""
	data = blocks if isinstance(blocks, list) else frappe.parse_json(blocks or "[]")
	root = (data[0] if data else None) if isinstance(data, list) else data
	if not isinstance(root, dict):
		return None
	styles = root.get("baseStyles") or {}
	return styles.get("background") or styles.get("backgroundImage") or styles.get("backgroundColor") or None


def get_block_html(blocks: str | list) -> tuple[str, str, dict, bool]:
	"""
	Main entry point for converting blocks to HTML.

	#### Args:
		blocks: JSON string or list of block dictionaries

	#### Returns:
		Tuple of (`html_content`, `css_styles`, `font_map`, `has_dual_mode_image`)
	"""
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	normalize_legacy_raw_styles(blocks)

	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	# Shared state during rendering
	shared_state = {
		"soup": soup,
		"style_tag": style_tag,
		"font_map": font_map,
		"has_dual_mode_image": False,
		"standard_props_stack": {},  # prop_name -> list of prop_info
		"global_script_tag": soup.new_tag("script"),
		"used_block_scripts": set(),
	}

	html_parts = []

	for block in blocks:
		block, component_id = extend_block_with_component(block)
		props = process_block_props(block, None, shared_state["standard_props_stack"])
		block_context = get_block_context(block, props, component_id)

		tag = build_tag(block, shared_state)
		# Add global script to the top
		tag.insert(0, shared_state["global_script_tag"])

		html = wrap_html_with_context(str(tag), block_context)

		cleanup_props_stack(props, shared_state["standard_props_stack"])

		html_parts.append(html)

	return (
		"".join(html_parts),
		str(style_tag),
		font_map,
		shared_state["has_dual_mode_image"],
	)


def build_tag(
	block: dict,
	state: dict,
	data_key: dict | None = None,
	ancestor_font: str | None = None,
	ancestor_italic: bool = False,
) -> bs.Tag:
	"""
	Transforms a single block to an HTML tag.

	#### Returns:
		BeautifulSoup tag element
	"""

	set_dynamic_content_placeholders(block, data_key)

	all_styles = [
		block.get("baseStyles") or {},
		block.get("mobileStyles") or {},
		block.get("tabletStyles") or {},
	]
	resolved_font = (
		next(
			(s.get("fontFamily", "").strip("'\"") for s in all_styles if s.get("fontFamily")),
			None,
		)
		or ancestor_font
	)
	# font-style cascades exactly like font-family: the block's own value wins,
	# otherwise italic (or not) is inherited from the ancestor
	resolved_italic = next(
		(str(s["fontStyle"]).lower() in ("italic", "oblique") for s in all_styles if s.get("fontStyle")),
		ancestor_italic,
	)

	tag = create_html_tag(block, state, ancestor_font=resolved_font)

	if resolved_italic and resolved_font:
		weight = next((s.get("fontWeight") for s in all_styles if s.get("fontWeight")), 400)
		register_italic_font(state["font_map"], get_font_family(resolved_font), weight)

	if is_repeater_block(block):
		render_repeater_children(
			tag, block, data_key, state, ancestor_font=resolved_font, ancestor_italic=resolved_italic
		)
	else:
		render_children(
			tag, block, data_key, state, ancestor_font=resolved_font, ancestor_italic=resolved_italic
		)

	attach_client_script(tag, block, state)

	# Add body scripts for body element
	effective_element = block.get("originalElement") or block.get("element")
	if effective_element == "body":
		tag.append("{% include 'templates/generators/webpage_scripts.html' %}")

	return tag


def get_block_context(block: dict, props: dict, component_id: str | None) -> dict:
	"""
	Get the Jinja template context for a block.

	#### Returns:
		Dict with keys: { `all_props`, `passed_down_props` }
	"""
	all_props = {name: info["value"] for name, info in props.items()}
	passed_down_props = {name: info["value"] for name, info in props.items() if info["is_passed_down"]}

	return {
		"block_id": block.get("blockId"),
		"component_id": component_id,
		"all_props": all_props,
		"passed_down_props": passed_down_props,
	}


def cleanup_props_stack(props: dict, props_stack: dict):
	"""Remove standard props from the stack after processing."""
	for name, info in props.items():
		if info["is_standard"] and name in props_stack:
			props_stack[name].pop()


def process_block_props(block: dict, data_key: dict | None, props_stack: dict) -> dict:
	"""
	Process all properties of a block. Also adds standard props info to the props stack if applicable.

	#### Returns:
		Dict with keys: { `value`, `is_standard`, `is_passed_down` }
	"""
	props = {}

	for prop_name, prop_config in block.get("props", {}).items():
		is_standard = prop_config.get("isStandard", False)
		is_passed_down = prop_config.get("isPassedDown", False)

		value = interpret_prop_value(prop_config, data_key)

		# Track standard properties in stack
		if is_standard:
			props_stack.setdefault(prop_name, []).append(prop_config)

		props[prop_name] = {"value": value, "is_standard": is_standard, "is_passed_down": is_passed_down}

	return props


def interpret_prop_value(prop_config: dict, data_key: dict | None) -> Any:
	"""Interpret prop value based on its configuration (static or dynamic)."""
	is_dynamic = prop_config.get("isDynamic", False)
	is_standard = prop_config.get("isStandard", False)
	comes_from = prop_config.get("comesFrom", "props")
	value = prop_config.get("value")
	is_empty = value is None or value == ""

	default_value = None
	if is_standard:
		prop_type = prop_config.get("propOptions", {}).get("type")
		default_value = parse_static_value(
			prop_config.get("propOptions", {}).get("options", {}).get("defaultValue"), prop_type
		)

	if is_empty:
		return default_value if is_standard else "undefined"

	if is_dynamic:
		return get_dynamic_props_template(value, comes_from, data_key, default_value)

	if is_standard:
		prop_type = prop_config.get("propOptions", {}).get("type")
		value = parse_static_value(value, prop_type)

	return value if not is_empty else "undefined"


def get_binding_key(key: str, comes_from: str, data_key: dict | None, missing: str = "{}") -> str:
	"""Jinja expression for a bound key that survives a missing root."""
	if comes_from == "props":
		return jinja_safe_key(f"props.{key}", missing)
	if comes_from == "componentData":
		return jinja_safe_key(f"component.{key}", missing)
	if data_key:
		return jinja_safe_key(f"{extract_data_key(data_key)}.{key}", missing)
	# a flat key keeps 0 and "" as-is; only a dotted path raises when its root is undefined
	if is_safe_data_key(key) and "." not in key:
		return key
	return jinja_safe_key(key, missing)


def get_dynamic_props_template(
	prop_value: str, comes_from: str, data_key: dict | None, default_value: Any
) -> str:
	"""Get a Jinja template reference for dynamic properties."""
	# props tell a missing path apart from an empty object, so the chain ends in none
	key = get_binding_key(prop_value, comes_from, data_key, missing="none")
	fallback = escape_single_quotes(default_value) if default_value is not None else "undefined"
	return f"{{{{ {key} if {key} is defined and {key} is not none else '{fallback}' }}}}"


# Reserved characters and existing %-escapes pass through, so absolute and data: URLs
# survive; only what a URL can't carry literally (spaces, non-ASCII) is encoded.
URL_SAFE_CHARS = "/:?#[]@!$&'()*+,;=%"


def quote_url(url: str | None) -> str | None:
	if not url:
		return None
	# In a data: URL "#" is payload (fill='#fff'), not a fragment.
	safe = URL_SAFE_CHARS.replace("#", "") if url.startswith("data:") else URL_SAFE_CHARS
	return frappe.utils.quote(url, safe=safe)


def create_html_tag(block: dict, state: dict, ancestor_font: str | None = None) -> bs.Tag:
	"""Create HTML tag element with attributes, classes, and styling."""
	soup = state["soup"]

	element = block.get("originalElement") or block.get("element") or "div"

	# fix: since p inside p is illegal
	if element in ["p", "__raw_html__"]:
		element = "div"

	if element == "img":
		attributes = block.get("attributes", {})
		dark_src = quote_url(attributes.get("darkSrc"))
		light_src = quote_url(attributes.get("src"))
		if dark_src and light_src:
			picture_tag = soup.new_tag("picture")

			# Add source for dark mode
			dark_source = soup.new_tag("source")
			dark_source["srcset"] = dark_src
			dark_source["media"] = "(prefers-color-scheme: dark)"
			dark_source["data-scheme"] = "dark"  # used by manual theme toggle script
			# browsers don't hide <source>, and display: contents on picture turns it into a flex/grid item
			dark_source["style"] = "display: none;"
			picture_tag.append(dark_source)
			picture_tag.attrs["style"] = "display: contents;"
			state["has_dual_mode_image"] = True

			tag = soup.new_tag("img")
			tag.attrs = {k: v for k, v in attributes.items() if k != "darkSrc"}
		else:
			if dark_src:  # use as src if no light src
				attributes["src"] = dark_src
				del attributes["darkSrc"]
			tag = soup.new_tag(element)
			tag.attrs = attributes.copy()
			picture_tag = None
	else:
		tag = soup.new_tag(element)
		tag.attrs = block.get("attributes", {})
		picture_tag = None

	for key, value in block.get("customAttributes", {}).items():
		tag[key] = value

	# Stamp the live blockId so duplicated blocks each get their own tracking id.
	if tag.get("data-track") and block.get("blockId"):
		tag["data-track"] = block.get("blockId")

	classes = build_tag_classes(block, state, ancestor_font=ancestor_font)
	tag.attrs["class"] = " ".join(classes)

	add_inner_html_content(tag, block, state, ancestor_font=ancestor_font)

	if picture_tag is not None:
		picture_tag.append(tag)
		return picture_tag

	return tag


def build_tag_classes(block: dict, state: dict, ancestor_font: str | None = None) -> list[str]:
	"""Build list of CSS classes for the tag."""
	classes = block.get("classes", [])
	if isinstance(classes, str):
		classes = [c.strip() for c in classes.split(",") if c.strip()]
	else:
		classes = classes.copy()
	element = block.get("originalElement") or block.get("element")

	text_elements = {"span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "label", "a"}
	if element in text_elements:
		classes.insert(0, "__text_block__")

	if block.get("baseStyles") or block.get("tabletStyles") or block.get("mobileStyles"):
		style_class = generate_and_apply_styles(block, state, ancestor_font=ancestor_font)
		classes.insert(0, style_class)

	return classes


def generate_and_apply_styles(block: dict, state: dict, ancestor_font: str | None = None) -> str:
	"""Generate a unique style class and append all styles to the style tag."""
	style_class = f"fb-{frappe.generate_hash(length=8)}"
	style_tag = state["style_tag"]
	font_map = state["font_map"]

	styles = {
		"base": split_styles(block.get("baseStyles", {})),
		"mobile": split_styles(block.get("mobileStyles", {})),
		"tablet": split_styles(block.get("tabletStyles", {})),
	}

	style_list = [
		styles["base"]["regular"],
		styles["mobile"]["regular"],
		styles["tablet"]["regular"],
	]
	set_fonts(style_list, font_map, inherited_font=ancestor_font)

	# Append styles for different states and devices
	# Base
	append_style(styles["base"]["regular"], style_tag, style_class)
	append_state_style(styles["base"]["state"], style_tag, style_class)

	# Tablet
	append_style(styles["tablet"]["regular"], style_tag, style_class, device="tablet")
	append_state_style(styles["tablet"]["state"], style_tag, style_class, device="tablet")

	# Mobile
	append_style(styles["mobile"]["regular"], style_tag, style_class, device="mobile")
	append_state_style(styles["mobile"]["state"], style_tag, style_class, device="mobile")

	return style_class


def add_inner_html_content(tag: bs.Tag, block: dict, state: dict, ancestor_font: str | None = None):
	"""Add inner HTML content to the tag."""
	inner_content = block.get("innerHTML")
	if inner_content:
		# Ensure inner_content is a string before passing to BeautifulSoup
		if not isinstance(inner_content, (str, bytes)):
			inner_content = str(inner_content)
		inner_soup = bs.BeautifulSoup(inner_content, "html.parser")
		set_fonts_from_html(inner_soup, state["font_map"])
		set_italics_from_html(inner_soup, state["font_map"], ancestor_font)
		if inner_soup.contents:
			tag.append(inner_soup)


def set_italics_from_html(soup, font_map, ancestor_font: str | None = None):
	"""Register italics used inside a block's inner HTML: <i>/<em> tags or
	inline font-style spans, which inherit the block's resolved font."""
	fallback = get_font_family(ancestor_font) if ancestor_font else None
	if soup.find(["i", "em"]):
		register_italic_font(font_map, fallback)
	for tag in soup.find_all(style=True):
		style = tag.attrs.get("style", "")
		if not re.search(r"font-style\s*:\s*(italic|oblique)", style):
			continue
		family = None
		for declaration in style.split(";"):
			if "font-family" in declaration:
				family = get_font_family(declaration.split(":", 1)[1])
		register_italic_font(font_map, family or fallback)


def is_repeater_block(block: dict) -> bool:
	"""Check if block is a repeater (loop) block."""
	return bool(
		block.get("isRepeaterBlock") and block.get("children") and (block.get("dataKey") or {}).get("key")
	)


def render_children(
	tag: bs.Tag,
	block: dict,
	data_key: dict | None,
	state: dict,
	ancestor_font: str | None = None,
	ancestor_italic: bool = False,
):
	"""Render (non-repeater) children."""
	for child in block.get("children", []) or []:
		child, component_id = extend_block_with_component(child)
		child_props = process_block_props(child, data_key, state["standard_props_stack"])
		child_context = get_block_context(child, child_props, component_id)
		child_context["visibility_key"] = get_visibility_condition_key(child, data_key)

		child_tag = build_tag(
			child, state, data_key, ancestor_font=ancestor_font, ancestor_italic=ancestor_italic
		)

		append_child_with_context(tag, child_tag, child_context)
		cleanup_props_stack(child_props, state["standard_props_stack"])


def render_repeater_children(
	tag: bs.Tag,
	block: dict,
	data_key: dict | None,
	state: dict,
	ancestor_font: str | None = None,
	ancestor_italic: bool = False,
):
	"""Render children for repeater blocks (with for loops)."""
	loop_info = get_loop_info(block, data_key, state["standard_props_stack"])

	tag.append(f"{{% for {loop_info['loop_var']} in {loop_info['iterator_key']} %}}")

	child = block.get("children")[0]
	child, component_id = extend_block_with_component(child)

	child_props = process_block_props(child, loop_info["data_key"], state["standard_props_stack"])
	child_context = get_block_context(child, child_props, component_id)

	if block.get("dataKey", {}).get("comesFrom") == "props":
		data_key_key = block.get("dataKey").get("key")
		child_context["default_props"] = extract_loop_variables(data_key_key, state["standard_props_stack"])

	child_tag = build_tag(
		child, state, loop_info["data_key"], ancestor_font=ancestor_font, ancestor_italic=ancestor_italic
	)

	append_child_with_context(tag, child_tag, child_context)
	cleanup_props_stack(child_props, state["standard_props_stack"])

	tag.append("{% endfor %}")


def get_loop_info(block: dict, data_key: dict | None, props_stack: dict) -> dict:
	"""
	Get loop information (variable name, iterator, data_key).

	Returns:
		Dict with keys: loop_var, iterator_key, data_key
	"""
	data_key_config = block.get("dataKey", {})
	iterator_key = data_key_config.get("key")
	comes_from = data_key_config.get("comesFrom", "dataScript")

	if comes_from == "props":
		loop_vars = extract_loop_variables(iterator_key, props_stack)
		loop_var = ", ".join(loop_vars)  # "item" or "key, value"
		safe_key = jinja_safe_key(f"props.{iterator_key}")

		# For objects, iterate over items()
		if len(loop_vars) > 1:
			safe_key = f"{safe_key}.items()"

		return {"loop_var": loop_var, "iterator_key": safe_key, "data_key": data_key}

	elif comes_from == "componentData":
		return {
			"loop_var": "component",
			"iterator_key": jinja_safe_key(f"component.{iterator_key}"),
			"data_key": data_key,
		}

	else:  # dataScript
		if data_key:
			full_key = f"{extract_data_key(data_key)}.{iterator_key}"
		else:
			full_key = iterator_key

		if not is_safe_data_key(full_key):
			loop_var = f"key_invalid_{block.get('blockId', 'x')}"
			return {
				"loop_var": loop_var,
				"iterator_key": "[]",
				"data_key": {"key": loop_var, "comesFrom": "dataScript"},
			}

		loop_var = f"key_{full_key.replace('.', '__')}"

		return {
			"loop_var": loop_var,
			"iterator_key": jinja_safe_key(full_key),
			"data_key": {"key": loop_var, "comesFrom": "dataScript"},
		}


def extract_loop_variables(key: str, props_stack: dict) -> list[str]:
	"""Extract loop variable names based on prop type (array or object)."""
	if key not in props_stack:
		return []

	prop_info = props_stack[key][-1]
	standard_options = prop_info.get("propOptions", {})
	prop_type = standard_options.get("type")

	if prop_type == "array":
		return ["item"]  # TODO: allow custom item name
	elif prop_type == "object":
		return ["key", "value"]  # TODO: allow custom key/value names

	return []


def get_visibility_condition_key(block: dict, data_key: dict | None) -> str | None:
	"""Get the Jinja key for visibility condition."""
	visibility_condition = block.get("visibilityCondition")
	if not visibility_condition:
		return None

	# Handle string format (legacy)
	if isinstance(visibility_condition, str):
		key = visibility_condition
		comes_from = "dataScript"
	else:
		key = visibility_condition.get("key")
		comes_from = visibility_condition.get("comesFrom", "dataScript")

	if not key:
		return None

	return get_binding_key(key, comes_from, data_key)


def escape_raw_text_end_tag(content: str, tag: str) -> str:
	pattern = rf"</{re.escape(tag)}(?=[\t\n\f\r />])"
	return re.sub(pattern, lambda match: match.group().replace("/", r"\/", 1), content, flags=re.IGNORECASE)


def create_client_script_tag(state: dict, script_id: str, script: dict) -> bs.Tag:
	"""Register a client script globally (once) and return its per-block tag."""
	if script["type"] == "JavaScript":
		if script_id not in state["used_block_scripts"]:
			block_script = escape_raw_text_end_tag(script["script"], "script")
			state["global_script_tag"].append(
				f"async function client_script_{script_id}(component_data, props) {{{block_script}}}\n"
			)
			state["used_block_scripts"].add(script_id)

		script_tag = state["soup"].new_tag("script")
		invocation = (
			f"(client_script_{script_id}).call("
			f"document.querySelector('[data-block-uid=\"{{{{ unique_hash }}}}\"]'), "
			f"{{{{ (component.component_data if component is defined else {{}}) | to_safe_json }}}}, "
			f"{{{{ (props if props is defined else {{}}) | to_safe_json }}}}"
			f");"
		)
		script_tag.string = invocation
		return script_tag

	style_tag = state["soup"].new_tag("style")
	block_style = escape_raw_text_end_tag(script["script"], "style")
	style_tag.string = f"@scope {{ {block_style} }}"
	return style_tag


def attach_client_script(tag: bs.Tag, block: dict, state: dict):
	"""Attach client-side JavaScript/CSS to the block."""
	client_script = block.get("clientScript")
	if client_script is None:
		client_script = {"js": block.get("blockClientScript")}
	scripts = [
		{"script": client_script.get("js"), "type": "JavaScript"},
		{"script": client_script.get("css"), "type": "CSS"},
	]
	scripts = [script for script in scripts if script["script"]]

	if not scripts:
		return

	tag.attrs["data-block-uid"] = "{{ unique_hash }}"

	for script in scripts:
		script_id = hashlib.sha256(script["script"].encode()).hexdigest()[:16]
		tag.append(create_client_script_tag(state, script_id, script))


def append_child_with_context(parent: bs.Tag, child: bs.Tag, context: dict):
	"""Append child tag with proper Jinja context wrapping."""
	# Generate unique hash for this block instance
	# This is unique for each block irrespective of loops or components
	parent.append("{% with unique_hash = (loop.index if loop is defined else 0) | hash %}")
	parent.append(f"{{% with block_id = '{context['block_id']}' %}}")

	if context.get("default_props"):
		props_str = ", ".join([f"'{var}': {var}" for var in context["default_props"]])
		parent.append(f"{{% with passed_down_props = passed_down_props | combine({{ {props_str} }}) %}}")
		parent.append("{% with props = passed_down_props %}")

	all_props_literal = to_jinja_literal(context["all_props"])
	passed_down_literal = to_jinja_literal(context["passed_down_props"])

	parent.append(f"{{% with props = {all_props_literal} | combine(passed_down_props) %}}")
	parent.append(f"{{% with passed_down_props = passed_down_props | combine({passed_down_literal}) %}}")

	if context.get("visibility_key"):
		parent.append(f"{{% if {context['visibility_key']} %}}")

	if context.get("component_id"):
		component_id_literal = to_jinja_literal(context["component_id"])
		parent.append(f"{{% with component = get_component_data({component_id_literal}, props) %}}")

	parent.append(child)

	if context.get("component_id"):
		parent.append("{% endwith %}")

	if context.get("visibility_key"):
		parent.append("{% endif %}")

	parent.append("{% endwith %}")
	parent.append("{% endwith %}")

	if context.get("default_props"):
		parent.append("{% endwith %}{% endwith %}")

	parent.append("{% endwith %}")
	parent.append("{% endwith %}")


def set_dynamic_content_placeholders(block: dict, data_key: dict | None = None):
	"""Apply dynamic content placeholders to block attributes and styles."""
	for binding in group_bindings_by_target(block):
		keys = resolve_binding_keys(binding, data_key)
		property_name = binding[0].get("property")
		value_type = binding[0].get("type")

		if value_type == "attribute":
			attributes = block.setdefault("attributes", {})
			custom_attributes = block.setdefault("customAttributes", {})
			if property_name in custom_attributes:
				current_value = custom_attributes.get(property_name, "") or ""
				custom_attributes[property_name] = build_placeholder(keys, current_value, keep_empty=True)
			else:
				current_value = attributes.get(property_name, "")
				attributes[property_name] = build_placeholder(keys, current_value)

		elif value_type == "style":
			attributes = block.setdefault("attributes", {})
			if not attributes.get("style"):
				attributes["style"] = ""

			css_property = camel_case_to_kebab_case(property_name)
			current_value = (block.get("baseStyles") or {}).get(property_name, "") or ""
			attributes["style"] += f"{css_property}: {build_placeholder(keys, current_value)};"

		elif value_type == "key" and not block.get("isRepeaterBlock"):
			current_value = block.get(property_name, "")
			block[property_name] = build_placeholder(keys, current_value, keep_empty=True)


def group_bindings_by_target(block: dict) -> list[list[dict]]:
	"""Group a block's bindings by (property, type), highest precedence first.

	The canvas resolver applies dataKey (the legacy single-binding field) first, then lets
	dynamicValues overwrite it, keeping the earlier value where a key does not resolve.
	"""
	bindings = {}
	for candidate in block.get("dynamicValues", []) or []:
		if not isinstance(candidate, dict):
			candidate = {"key": candidate, "type": "key", "property": candidate}
		if not candidate.get("key"):
			continue
		# a later entry for the same target overrides the ones before it
		bindings.setdefault((candidate.get("property"), candidate.get("type")), []).insert(0, candidate)

	block_data_key = block.get("dataKey") or {}
	if block_data_key.get("key"):
		signature = (block_data_key.get("property"), block_data_key.get("type"))
		bindings.setdefault(signature, []).append(block_data_key)

	return list(bindings.values())


def resolve_binding_keys(binding: list[dict], data_key: dict | None) -> list[str]:
	"""Jinja keys for one target, in precedence order and without repeats."""
	keys = []
	for candidate in binding:
		key = get_binding_key(candidate.get("key", ""), candidate.get("comesFrom", "dataScript"), data_key)
		if key not in keys:
			keys.append(key)
	return keys


def build_placeholder(keys: list[str], fallback_value, keep_empty: bool = False) -> str:
	"""Chain the keys into one placeholder so the first that resolves wins.

	Chaining inside a single expression, rather than applying a placeholder per key, keeps the raw
	expression out of its own fallback string, where it would leak to the page for falsy values.
	"""
	expression = f"'{escape_single_quotes(str(fallback_value))}'"
	for key in reversed(keys):
		if keep_empty:
			expression = f"{key} if {key} or {key} in ['', 0] else {expression}"
		else:
			expression = f"{key} or {expression}"
	return f"{{{{ {expression} }}}}"


def wrap_html_with_context(html: str, context: dict) -> str:
	"""
	Wrap HTML with Jinja context variables.

	#### Returns:
		HTML string
	"""
	all_props_literal = to_jinja_literal(context["all_props"])
	passed_down_literal = to_jinja_literal(context["passed_down_props"])

	# Set props contexts
	if context.get("component_id"):
		component_id_literal = to_jinja_literal(context["component_id"])
		html = (
			f"{{% with component = get_component_data({component_id_literal}, props) %}}{html}{{% endwith %}}"
		)
	html = f"{{% with props = {all_props_literal} %}}{html}{{% endwith %}}"
	html = f"{{% with passed_down_props = {passed_down_literal} %}}{html}{{% endwith %}}"

	return html


def extend_block_with_component(block: dict) -> tuple[dict, str | None]:
	if not block.get("extendedFromComponent"):
		return block, None

	component_id = block.get("extendedFromComponent")
	component_version = block.get("componentVersion")
	component = resolve_component(component_id, component_version)
	if not component:
		return block, None

	component_block = frappe.parse_json(component.get("block") or "{}")
	if component_block:
		extend_block(component_block, block)

		return component_block, component_id

	return block, None


def wrap_with_media_query(style_string, device):
	if device == "mobile":
		return f"@media only screen and (max-width: {MOBILE_BREAKPOINT}px) {{ {style_string} }}"
	elif device == "tablet":
		return f"@media only screen and (max-width: {DESKTOP_BREAKPOINT - 1}px) {{ {style_string} }}"
	return style_string


# //// Neoffice — added. Upstream strips quotes and escapes spaces on the WHOLE
# //// font-family string, which leaves the inner quote of a stack like 'X', sans-serif
# //// and yields a family no font matches: the browser silently fell back to serif (the
# //// cross-page font drift). Split per family instead (981c6c2a).
_GENERIC_FONT_KEYWORDS = {
	"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
	"ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "math",
	"emoji", "fangsong", "inherit", "initial", "unset", "revert", "revert-layer",
}


def normalize_font_family(value):
	"""Emit a valid CSS font-family stack from a stored value that may arrive
	already quoted ('"Raleway", sans-serif'), unquoted, or mixed. Naive
	quote-stripping/space-escaping on the whole string corrupts it — e.g.
	'"Raleway", sans-serif'.strip('\\'"') keeps the inner quote and yields a
	family literally named 'Raleway"' that no font matches, so the browser falls
	back to its default serif (the cross-page font drift). Split per family,
	strip stray quotes, re-quote only multi-word custom names, leave generic
	keywords bare."""
	if not isinstance(value, str):
		return value
	families = []
	for raw in value.split(","):
		fam = raw.strip().strip("'\"").strip()
		if not fam:
			continue
		if fam.lower() in _GENERIC_FONT_KEYWORDS:
			families.append(fam.lower())
		elif " " in fam:
			families.append(f'"{fam}"')
		else:
			families.append(fam)
	return ", ".join(families) or value


def get_style(style_obj):
	def _css_value(key, value):
		if key == "fontFamily" and isinstance(value, str):
			# //// Neoffice — route fontFamily through normalize_font_family (981c6c2a).
			value = normalize_font_family(value)
		return sanitize_style_value(value)

	return (
		"".join(
			f"{camel_case_to_kebab_case(key)}: {_css_value(key, value)};"
			for key, value in style_obj.items()
			if value is not None and value != "" and not key.startswith("__")
		)
		if style_obj
		else ""
	)


def append_style(style_obj, style_tag, style_class, device="desktop"):
	style = get_style(style_obj)
	if not style:
		return
	style_string = f".{style_class} {{ {style} }}"
	style_tag.append(wrap_with_media_query(style_string, device))


def append_state_style(style_obj, style_tag, style_class, device="desktop"):
	for key, value in style_obj.items():
		if ":" in key:
			state, property = key.split(":", 1)
			css_property = camel_case_to_kebab_case(property)
			style_string = f".{style_class}:{state} {{ {css_property}: {value}; }}"
			style_tag.append(wrap_with_media_query(style_string, device))


def get_font_family(font: str) -> str:
	"""Return the first family from a CSS font stack (e.g. 'Inter, sans-serif' -> 'Inter').
	A Font design token (var(--id)) resolves to its family so the Google Fonts
	links include tokenized families."""
	font = resolve_font_token(font)
	return font.split(",")[0].strip().strip("'\"")


def resolve_font_token(font: str) -> str:
	match = re.match(r"\s*var\(\s*(--[^),\s]+)", font or "")
	if not match:
		return font
	from builder.builder.doctype.builder_token.builder_token import get_css_variables

	# the cached token map, so a page full of tokenized fonts is not a query each
	css_variables, _ = get_css_variables()
	return css_variables.get(match.group(1), "")


def set_fonts(styles, font_map, inherited_font=None):
	weight_map = {
		"thin": "100",
		"extralight": "200",
		"light": "300",
		"normal": "400",
		"medium": "500",
		"semibold": "600",
		"bold": "700",
		"extrabold": "800",
		"black": "900",
	}
	system_fonts = {
		"arial",
		"helvetica",
		"times new roman",
		"times",
		"courier new",
		"courier",
		"verdana",
		"georgia",
		"palatino",
		"garamond",
		"bookman",
		"comic sans ms",
		"comic sans",
		"trebuchet ms",
		"arial black",
		"impact",
		"sans-serif",
		"serif",
		"monospace",
		"cursive",
		"fantasy",
		"system-ui",
		"intervar",  # loaded by default via reset.css
	}
	for style in styles:
		font = style.get("fontFamily")
		if not font and style.get("fontWeight") and inherited_font:
			# fontWeight is set but fontFamily is not — use explicitly passed ancestor font
			font = inherited_font
		if font:
			# Use the first family from a fallback list, e.g. "Inter, sans-serif" -> "Inter"
			font = get_font_family(font)
			# //// Neoffice — an AI-written stack can reduce to an empty family; upstream then puts a
			# //// "" key in the font map and asks Google Fonts for it (0674efd2).
			# AI-written stacks can reduce to an empty string (e.g. "', sans-serif'")
			if not font:
				continue

			# Skip system fonts and unresolvable font tokens
			if not font or font.lower() in system_fonts:
				continue

			weight = str(style.get("fontWeight") or "400").lower()
			weight = weight_map.get(weight, weight)

			# Ensure weight is a valid integer
			try:
				weight = int(weight)
			except (ValueError, TypeError):
				weight = 400

			if font in font_map:
				if weight not in font_map[font]["weights"]:
					font_map[font]["weights"].append(weight)
					font_map[font]["weights"].sort()
			else:
				font_map[font] = {"weights": [weight]}


def normalize_font_weights(font_map: dict) -> None:
	"""Make each font's weights render-ready for the Google Fonts request: numeric,
	deduped, sorted, and always including 400 so the regular face is loaded."""
	for options in font_map.values():
		weights = {int(weight) for weight in options.get("weights", [])}
		weights.add(400)
		options["weights"] = sorted(weights)


def register_italic_font(font_map: dict, font: str | None, weight=400) -> None:
	"""Record that a collected font is used in italic at `weight`. Fonts that
	set_fonts skipped (system fonts, CSS stacks) are ignored here too."""
	options = font_map.get(font) if font else None
	if options is None:
		return
	try:
		weight = int(str(weight))
	except (TypeError, ValueError):
		weight = 400
	italics = options.setdefault("italics", [])
	if weight not in italics:
		italics.append(weight)
		italics.sort()


def get_google_font_urls(font_map: dict) -> list[str]:
	"""Build one combined Google Fonts stylesheet URL per font family.

	Families used in italic get the `ital` axis at every weight the family is
	used at: an <em> or <i> inherits whatever weight surrounds it, which the
	renderer doesn't track. Faces only download when text uses them, and css2
	silently drops tuples a family doesn't ship, so no font catalog is needed."""
	normalize_font_weights(font_map)
	urls = []
	for font, options in font_map.items():
		family = quote_plus(font)
		italics = sorted({*options["weights"], *(int(weight) for weight in options.get("italics", []))})
		if options.get("italics"):
			tuples = [f"0,{weight}" for weight in options["weights"]]
			tuples += [f"1,{weight}" for weight in italics]
			axis = ";".join(tuples)
			urls.append(f"https://fonts.googleapis.com/css2?family={family}:ital,wght@{axis}&display=swap")
		else:
			weights = ";".join(str(weight) for weight in options["weights"])
			urls.append(f"https://fonts.googleapis.com/css2?family={family}:wght@{weights}&display=swap")
	return urls


def set_fonts_from_html(soup, font_map):
	# get font-family from inline styles
	for tag in soup.find_all(style=True):
		styles = tag.attrs.get("style").split(";")
		for style in styles:
			if "font-family" in style:
				# //// Neoffice — split on the FIRST colon only: upstream's split(":")[1] truncates a
				# //// declaration whose value itself contains a colon (0674efd2).
				font = get_font_family(style.split(":", 1)[1])
				if font:
					font_map[font] = {"weights": [400]}


def extend_block(block, overridden_block):
	# children are normalized by the recursive extend_block call below
	merge_raw_styles_into_base_styles(block)
	merge_raw_styles_into_base_styles(overridden_block)
	normalize_legacy_block_client_script(block)
	normalize_legacy_block_client_script(overridden_block)

	block.setdefault("baseStyles", {}).update(overridden_block.get("baseStyles") or {})
	block.setdefault("mobileStyles", {}).update(overridden_block.get("mobileStyles") or {})
	block.setdefault("tabletStyles", {}).update(overridden_block.get("tabletStyles") or {})
	block.setdefault("attributes", {}).update(overridden_block.get("attributes") or {})

	dynamicValues = overridden_block.get("dynamicValues") or []
	dynamicValuesProperties = [dv.get("property") for dv in dynamicValues]
	for dv in block.get("dynamicValues", []) or []:
		if dv.get("property") in dynamicValuesProperties:
			continue
		dynamicValues.append(dv)
	block["dynamicValues"] = dynamicValues

	if overridden_block.get("element"):
		block["element"] = overridden_block["element"]

	if overridden_block.get("visibilityCondition"):
		block["visibilityCondition"] = overridden_block.get("visibilityCondition")

	if not block.get("customAttributes"):
		block["customAttributes"] = {}
	block["customAttributes"].update(overridden_block.get("customAttributes", {}))

	block.setdefault("classes", []).extend(overridden_block.get("classes") or [])

	if not block.get("props"):
		block["props"] = {}
	block["props"].update(overridden_block.get("props", {}))

	if block.get("clientScript") or overridden_block.get("clientScript"):
		block.setdefault("clientScript", {}).update(overridden_block.get("clientScript", {}))

	dataKey = overridden_block.get("dataKey", {})
	if not block.get("dataKey"):
		block["dataKey"] = {}
	if dataKey:
		block["dataKey"].update({k: v for k, v in dataKey.items() if v is not None and v != ""})
	if overridden_block.get("innerHTML"):
		block["innerHTML"] = overridden_block["innerHTML"]
	component_children = block.get("children", []) or []
	overridden_children = overridden_block.get("children", []) or []
	extended_children = []
	for overridden_child in overridden_children:
		component_child = next(
			(
				child
				for child in component_children
				if child.get("blockId")
				in [
					overridden_child.get("blockId"),
					overridden_child.get("referenceBlockId"),
				]
			),
			None,
		)
		if component_child:
			extended_children.append(extend_block(copy.deepcopy(component_child), overridden_child))
		else:
			extended_children.append(overridden_child)
	block["children"] = extended_children
	return block


def _current_site_profile():
	# //// Neoffice multi-site: resolved per-request by neoffice_theme's
	# //// before_request hook. None on instances without Website Profiles.
	return getattr(frappe.local, "website_profile", None)


def _page_has_site_field():
	try:
		return frappe.db.has_column("Builder Page", "neo_website_profile")
	except Exception:
		return False


def _served_before_document_page(path, http_status_code=None):
	"""Whether a renderer that runs BEFORE frappe's DocumentPage would serve this path.

	//// Neoffice — claiming a route (see can_render) puts us ahead of the whole chain, so it
	//// must only take what DocumentPage would otherwise have taken. The renderers ahead of it
	//// are StaticPage and WebFormPage: a file or a web form on this site keeps its path, even
	//// when another site of the instance happens to have a Builder Page on the same route.
	//// Everything AFTER DocumentPage (TemplatePage, ListPage, PrintPage) was already shadowed
	//// by the leak we are closing, so nothing there changes."""
	try:
		from frappe.website.page_renderers.static_page import StaticPage
		from frappe.website.page_renderers.web_form import WebFormPage

		return any(renderer(path, http_status_code).can_render() for renderer in (StaticPage, WebFormPage))
	except Exception:
		return False


def _route_of_another_site(route, website_profile):
	"""Whether a published Builder Page on this route belongs to a DIFFERENT site.

	//// Neoffice — only ever asked once find_page_with_path has already come up empty, so
	//// this site has neither its own page on that route nor an untagged one. `!=` leaves the
	//// untagged pages out, which is what we want: those serve everywhere by design."""
	if not website_profile or not _page_has_site_field():
		return False
	try:
		return bool(
			frappe.get_all(
				"Builder Page",
				filters={"route": route, "neo_website_profile": ("!=", website_profile)},
				or_filters=SERVED_PAGE_FILTERS,
				limit=1,
				pluck="name",
			)
		)
	except Exception:
		return False


def find_page_with_path(route, website_profile=None):
	# //// Neoffice website switch: an offline site (Website Profile.website_online=0)
	# //// hides its pages from visitors — deep links 404 like the site never existed.
	# //// Editors keep seeing them logged-in: that IS the preview before going live.
	# //// Keyed on the key existing in the dict (pre-switch caches stay untouched).
	# //// The gate runs on EVERY call and only the lookup below is cached: with the
	# //// gate inside the cached body, the first caller's role decided for everyone for
	# //// an hour (a staff visit exposed an offline page, a visitor's 404 hid it from
	# //// staff) — neoffice-maintenance #280.
	# //// One answer for every gate, the server-side render included: builder/website_switch.py.
	from builder.website_switch import hidden_from_visitor

	if hidden_from_visitor():
		return None
	return _find_page_with_path_cached(route, website_profile)


# //// Neoffice — upstream v1.35 serves a staging page at its route like a live one, the live page
# //// first (SERVED_PAGE_FILTERS). Our site-scoped lookups above ask for the same thing, one profile
# //// at a time, so a staging page of another site never answers on this one's domain.
def _first_served_page(route, **filters):
	pages = frappe.get_all(
		"Builder Page",
		# //// Neoffice — the extra filters carry the profile column, when the caller asks for one
		filters={"route": route, **filters},
		or_filters=SERVED_PAGE_FILTERS,
		order_by="published desc, published_at desc, creation desc",
		limit=1,
		pluck="name",
	)
	return pages[0] if pages else None


# //// Neoffice — upstream's cached find_page_with_path, renamed: the public find_page_with_path
# //// above gates offline sites on every call, and only this lookup is cached (#280).
@redis_cache(ttl=60 * 60)
def _find_page_with_path_cached(route, website_profile=None):
	try:
		# //// Neoffice multi-site: a page tagged for the current profile wins on
		# //// that site (allows two home pages sharing a route); untagged pages
		# //// serve everywhere. Without a resolved profile: original behavior.
		if website_profile and _page_has_site_field():
			page = _first_served_page(route, neo_website_profile=website_profile)
			if page:
				return page
			return _first_served_page(route, neo_website_profile=("is", "not set"))
		return _first_served_page(route)
	except frappe.DoesNotExistError:
		pass


# //// Neoffice — the cache handle stays where callers and tests look for it (#280).
find_page_with_path.clear_cache = _find_page_with_path_cached.clear_cache


@redis_cache(ttl=60 * 60)
def get_web_pages_with_dynamic_routes(website_profile=None) -> list[dict]:
	fields = ["name", "route", "modified"]
	# //// Neoffice multi-site: dynamic routes tagged for another profile are
	# //// excluded on this site; untagged ones serve everywhere.
	has_site_field = _page_has_site_field()
	if has_site_field:
		fields.append("neo_website_profile")
	pages = frappe.get_all(
		"Builder Page",
		# //// Neoffice multi-site: the field list is built above so the profile column is asked
		# //// for only on instances that have it (c3f2a043).
		fields=fields,
		filters={"dynamic_route": 1},
		or_filters=SERVED_PAGE_FILTERS,
		# the renderer serves the first match, so live pages come before staging ones
		order_by="published desc, published_at desc, creation desc",
		update={"doctype": "Builder Page"},
	)
	# //// Neoffice multi-site: drop rows tagged for another profile; untagged serve
	# //// everywhere (c3f2a043).
	if website_profile and has_site_field:
		pages = [
			p for p in pages if not p.get("neo_website_profile") or p["neo_website_profile"] == website_profile
		]
	return pages


def resolve_path(path):
	try:
		# //// Neoffice multi-site: resolve against the request's profile (c3f2a043).
		if find_page_with_path(path, _current_site_profile()):
			return path
		elif evaluate_dynamic_routes(
			# //// Neoffice multi-site: same scoping for the dynamic routes (c3f2a043).
			[
				ColonRule(f"/{d.route}", endpoint=d.name)
				for d in get_web_pages_with_dynamic_routes(_current_site_profile())
			],
			path,
		):
			return path
	except Exception:
		pass

	return original_resolve_path(path)


def reset_with_component(block, extended_with_component, component_children):
	reset_block(block)
	block["children"] = []
	for component_child in component_children or []:
		component_child_id = component_child.get("blockId")
		child_block = reset_block(component_child)
		child_block["isChildOfComponent"] = extended_with_component
		child_block["referenceBlockId"] = component_child_id
		block["children"].append(child_block)
		if child_block.get("extendedFromComponent"):
			resolved = resolve_component(
				child_block.get("extendedFromComponent"), child_block.get("componentVersion")
			)
			if resolved:
				nested_block = frappe.parse_json(resolved.get("block") or "{}")
				reset_with_component(
					child_block, child_block.get("extendedFromComponent"), nested_block.get("children")
				)
			else:
				reset_with_component(child_block, extended_with_component, child_block.get("children"))
		else:
			reset_with_component(child_block, extended_with_component, child_block.get("children"))


def reset_block(block):
	block["blockId"] = frappe.generate_hash(length=8)
	block["innerHTML"] = None
	block["element"] = None
	block["baseStyles"] = {}
	block["mobileStyles"] = {}
	block["tabletStyles"] = {}
	block["attributes"] = {}
	block["customAttributes"] = {}
	block["classes"] = []
	block["dataKey"] = {}
	block["props"] = {}
	block["dynamicValues"] = []
	block["clientScript"] = {}
	block.pop("blockClientScript", None)
	return block


def normalize_legacy_block_client_script(block):
	if not block.get("clientScript") and block.get("blockClientScript"):
		block["clientScript"] = {"js": block.get("blockClientScript")}


def extract_data_key(data_key):
	if isinstance(data_key, str):
		return data_key
	elif isinstance(data_key, dict):
		return data_key.get("key")
	return None


# A data key is a dotted path of Jinja-safe identifiers (e.g. "features" or "props.items").
# Anything else (spaces, commas, brackets — e.g. an array stringified to "[object Object],...")
# would generate invalid Jinja and crash the page render.
SAFE_DATA_KEY = re.compile(r"^\w[\w.]*$")


def is_safe_data_key(key) -> bool:
	return isinstance(key, str) and bool(SAFE_DATA_KEY.match(key))


def jinja_safe_key(key, missing="{}"):
	# convert a.b to (a or {})['b'] to avoid undefined error in jinja; subscripts fall back to
	# attributes, so objects and dates resolve too, and the last segment falls back to `missing`
	if not is_safe_data_key(key):
		# render nothing rather than emitting a broken Jinja expression
		return missing
	keys = key.split(".")
	expr = f"({keys[0]} or {{}})"
	for k in keys[1:-1]:
		expr = f"({expr}['{k}'] or {{}})"
	if len(keys) > 1:
		last = f"{expr}['{keys[-1]}']"
		# the attribute fallback can land on a method, like str.title or dict.items
		expr = f"({missing} if {last} is callable else {last})"
	return expr


def to_jinja_literal(obj):
	# detect Jinja expressions inside strings (e.g. "{{ sample }}")
	if isinstance(obj, str):
		stripped = obj.strip()
		if re.fullmatch(r"{{\s*.*?\s*}}", stripped):
			# remove the {{ }} so Jinja receives the variable
			inner = stripped[2:-2].strip()
			return inner  # returned unquoted
		return repr(obj)

	if obj is True:
		return "True"
	if obj is False:
		return "False"
	if obj is None:
		return "None"

	if isinstance(obj, dict):
		parts = []
		for k, v in obj.items():
			parts.append(f"{to_jinja_literal(k)}: {to_jinja_literal(v)}")
		return "{ " + ", ".join(parts) + " }"

	if isinstance(obj, list | tuple):
		return "[ " + ", ".join(str(to_jinja_literal(i)) for i in obj) + " ]"

	return repr(obj)


def parse_static_value(value: str, prop_type: str) -> Any:
	"""Parse static value based on property type."""
	match prop_type:
		case "string" | "select":
			return str(value)
		case "number":
			try:
				number = float(value)
			except (ValueError, TypeError):
				return None
			# past 2**53 floats aren't exact, so an int would print digits the value doesn't have
			return int(number) if number.is_integer() and abs(number) < 2**53 else number
		case "boolean":
			if isinstance(value, bool):
				return value
			if str(value).lower() in ["true", "1"]:
				return True
			elif str(value).lower() in ["false", "0"]:
				return False
			return None
		case "array" | "object":
			try:
				return frappe.parse_json(value)
			except Exception:
				return None
		case _:
			return str(value)
