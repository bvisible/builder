import frappe

from . import __version__ as app_version

app_name = "builder"
app_title = "Frappe Builder"
app_publisher = "Frappe Technologies Pvt Ltd"
app_description = "An easier way to build web pages for your needs!"
app_email = "suraj@frappe.io"
app_license = "GNU Affero General Public License v3.0"

# Includes in <head>
# ------------------
# include js, css files in header of desk.html
app_include_css = "/assets/builder/css/builder-chat.css"
app_include_js = "/assets/builder/js/builder.js"

export_python_type_annotations = True

# include js, css files in header of web template
# web_include_css = "/assets/builder/css/builder.css"
# web_include_js = "/assets/builder/js/builder.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "builder/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Website Settings": "public/js/website_settings.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page managed via Website Settings — set to "home" (Builder Page) or "index" (under construction)

# website user home page (by Role)

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = ["Builder Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"builder.hf_utils.header_footer.render_header",
		"builder.hf_utils.header_footer.render_footer",
		"builder.hf_utils.header_footer.get_header_footer_config",
	]
}

# Installation
# ------------

# before_install = "builder.install.before_install"
after_install = "builder.install.after_install"
after_migrate = "builder.install.after_migrate"
after_app_install = "builder.install.after_app_install"

# Fixtures
# --------
fixtures = [
	{
		"dt": "Builder Shortcode",
		"filters": [["source_app", "=", "webshop"]]
	}
]

# Uninstallation
# ------------

# before_uninstall = "builder.uninstall.before_uninstall"
# after_uninstall = "builder.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "builder.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Website Settings": {
		"on_update": "builder.hf_utils.menu_integration.sync_from_website_settings"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"*/10 * * * *": [
			"builder.builder_analytics.ingest_web_page_views_to_duckdb",
			"builder.api.check_stuck_generations",
		],
	}
}

# Testing
# -------

# before_tests = "builder.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# "frappe.desk.doctype.event.event.get_events": "builder.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# "Task": "builder.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]


# User Data Protection
# --------------------

# user_data_fields = [
# {
# "doctype": "{doctype_1}",
# "filter_by": "{filter_by}",
# "redact_fields": ["{field_1}", "{field_2}"],
# "partial": 1,
# },
# {
# "doctype": "{doctype_2}",
# "filter_by": "{filter_by}",
# "partial": 1,
# },
# {
# "doctype": "{doctype_3}",
# "strict": False,
# },
# {
# "doctype": "{doctype_4}"
# }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# "builder.auth.validate"
# ]

try:
	builder_path = frappe.conf.builder_path or "builder"
except Exception:
	builder_path = "builder"
website_route_rules = [
	{"from_route": f"/{builder_path}/<path:app_path>", "to_route": "_builder"},
	{"from_route": f"/{builder_path}", "to_route": "_builder"},
]

website_path_resolver = "builder.builder.doctype.builder_page.builder_page.resolve_path"
page_renderer = "builder.builder.doctype.builder_page.builder_page.BuilderPageRenderer"

get_web_pages_with_dynamic_routes = (
	"builder.builder.doctype.builder_page.builder_page.get_web_pages_with_dynamic_routes"
)

get_website_user_home_page = (
	"builder.builder.doctype.builder_settings.builder_settings.get_website_user_home_page"
)

add_to_apps_screen = [
	{
		"name": "builder",
		"logo": "/assets/builder/icon-builder-website.jpg",
		"title": "Builder",
		"route": f"/{builder_path}",
		"has_permission": "builder.api.check_app_permission",
	}
]
