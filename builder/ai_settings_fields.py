#//// Neoffice — added file (no upstream equivalent): the custom fields behind Settings > AI; mirror of
#//// unpress_core/setup.py so both editions stay identical. Neoffice/Unpress-only surface;
#//// frappe/builder has no AI settings. First commit c58af069 2026-08-02.
# AI settings editable from the builder's Settings > AI tab.
#
# Mirror of unpress_core/setup.py: the Studio is the source of truth for the AI
# engine and Neoffice consumes it, so the field names and semantics are
# identical on both sides. Keep them in sync.
#
# Resolution order, unchanged: site_config.json always wins over these. A
# Neoffice instance that pins everything in site_config today behaves exactly
# as before — this layer only fills in what site_config leaves silent.
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# No `default` on any of these on purpose: empty means "use the code default"
# (ai/config.py DEFAULTS), so changing a default never needs a data migration.
AI_SETTINGS_FIELDS = {
	"Builder Settings": [
		{
			"fieldname": "unpress_ai_provider",
			"fieldtype": "Select",
			"label": "AI Provider",
			"options": "\nopenai\nollama\ncodex",
			"insert_after": "ai_api_key",
			"description": "Empty = OpenAI-compatible API (default)",
		},
		{
			"fieldname": "unpress_ai_base_url",
			"fieldtype": "Data",
			"label": "AI API Base URL",
			"insert_after": "unpress_ai_provider",
			"description": "Empty = the code default",
		},
		{
			"fieldname": "unpress_ai_brief_model",
			"fieldtype": "Data",
			"label": "AI Brief Model",
			"insert_after": "unpress_ai_base_url",
			"description": "Model for the creative brief. Empty = the code default",
		},
		{
			"fieldname": "unpress_ai_page_model",
			"fieldtype": "Data",
			"label": "AI Page Model",
			"insert_after": "unpress_ai_brief_model",
			"description": "Model for page generation. Empty = the code default",
		},
		{
			# How hard the model thinks before answering. The single biggest
			# lever on both quality and wall-clock, and it was only reachable
			# from site_config until now.
			"fieldname": "unpress_ai_reasoning_effort",
			"fieldtype": "Select",
			"label": "AI Reasoning Effort",
			"options": "\nminimal\nlow\nmedium\nhigh",
			"insert_after": "unpress_ai_page_model",
			"description": "How long the model thinks before answering. Empty = the provider decides.",
		},
		{
			"fieldname": "unpress_ai_output_language",
			"fieldtype": "Data",
			"label": "AI Content Language",
			"insert_after": "unpress_ai_reasoning_effort",
			"description": "Language of the generated content. Empty = French",
		},
	]
}


def ensure_ai_custom_fields():
	if not frappe.db.exists("DocType", "Builder Settings"):
		return
	create_custom_fields(AI_SETTINGS_FIELDS, ignore_validate=True)
