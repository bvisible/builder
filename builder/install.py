from frappe.core.api.file import create_new_folder

#//// Neoffice — the three subsystems upstream does not have: the AI settings custom
#//// fields, the plugin registry and the chrome Web Templates.
from builder.ai_settings_fields import ensure_ai_custom_fields
from builder.plugins import sync_plugins
from builder.web_chrome import ensure_web_chrome_templates
from builder.export_import_standard_page import sync_standard_builder_pages
from builder.utils import (
	add_composite_index_to_web_page_view,
	sync_block_templates,
	sync_builder_variables,
	sync_page_templates,
)


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()
	sync_builder_variables()
	add_composite_index_to_web_page_view()
	sync_standard_builder_pages()
	#//// Neoffice — install the AI fields and the chrome templates on a fresh site.
	ensure_ai_custom_fields()
	ensure_web_chrome_templates()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
	sync_builder_variables()
	sync_standard_builder_pages()
	#//// Neoffice — same on every migrate, plus a plugin-registry resync (an app added or
	#//// removed on the bench must show up in Settings > Plugins).
	ensure_ai_custom_fields()
	ensure_web_chrome_templates()
	sync_plugins()


def after_app_install(app_name=None):
	sync_standard_builder_pages(app_name)
	#//// Neoffice — see sync_plugins in after_migrate above.
	# installing the blog app is what makes the blog plugin appear
	sync_plugins(app_name)
