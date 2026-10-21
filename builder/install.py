from frappe.core.api.file import create_new_folder

# //// Neoffice — the subsystems upstream does not have: the plugin registry, the chrome Web
# //// Templates and the managed AI provider row.
from builder.plugins import sync_plugins
from builder.site_ai.managed import sync_managed_ai_provider, sync_nora_providers
from builder.web_chrome import ensure_web_chrome_templates
from builder.export_import_standard_page import sync_standard_builder_pages
from builder.utils import (
	add_composite_index_to_web_page_view,
	sync_block_templates,
	sync_builder_tokens,
	sync_page_templates,
	# //// Neoffice — the delivery path of the shortcode registry, which reached no site before
	# //// (see sync_shortcodes in utils.py).
	sync_shortcodes,
)


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	# //// Neoffice — the shortcode registry, which reached no site before (see sync_shortcodes).
	sync_shortcodes()
	add_composite_index_to_web_page_view()
	sync_standard_builder_pages()
	# //// Neoffice — the chrome templates on a fresh site.
	ensure_web_chrome_templates()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	# //// Neoffice — the shortcode registry, which reached no site before (see sync_shortcodes).
	sync_shortcodes()
	sync_standard_builder_pages()
	# //// Neoffice — same on every migrate, plus a plugin-registry resync (an app added or
	# //// removed on the bench must show up in Settings > Plugins).
	ensure_web_chrome_templates()
	sync_plugins()
	# //// Neoffice — a managed instance runs the upstream agent on the host's models: the provider
	# //// row follows site_config on every migrate (key rotation included), see site_ai/managed.py.
	sync_managed_ai_provider()
	# //// Neoffice — the host's own model providers on an instance that is not managed too (2026-10-21): the local model is
	# //// reachable from every client, and a route that does not exist cannot be named by `nora_site_model` (see managed.sync_nora_providers).
	sync_nora_providers()


def after_app_install(app_name=None):
	sync_standard_builder_pages(app_name)
	# //// Neoffice — see sync_plugins in after_migrate above.
	# installing the blog app is what makes the blog plugin appear
	sync_plugins(app_name)
