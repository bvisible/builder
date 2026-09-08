# //// Neoffice — added file (no upstream equivalent): drops the Builder Settings custom fields
# //// of the pre-1.33 AI settings tab (unpress_ai_provider, _base_url, _brief_model,
# //// _page_model, _reasoning_effort, _output_language). Upstream's AI settings (Builder AI
# //// Provider / Model rows) and site_config are the two layers now; builder/ai_settings_fields.py
# //// that created them is deleted with this patch.
import frappe

FIELDS = (
	"unpress_ai_provider",
	"unpress_ai_base_url",
	"unpress_ai_brief_model",
	"unpress_ai_page_model",
	"unpress_ai_reasoning_effort",
	"unpress_ai_output_language",
)


def execute():
	dropped = []
	for fieldname in FIELDS:
		name = frappe.db.get_value("Custom Field", {"dt": "Builder Settings", "fieldname": fieldname}, "name")
		if name:
			frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
			dropped.append(fieldname)
	if dropped:
		frappe.clear_cache(doctype="Builder Settings")
		frappe.logger().info("dropped legacy AI settings fields — " + ", ".join(dropped))
