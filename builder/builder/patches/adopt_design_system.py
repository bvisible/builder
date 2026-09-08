# //// Neoffice — added file (no upstream equivalent): sites built before the design system adopt it.
# The tokens are minted from each chrome's colours and fonts, the chrome points at
# them, and the pages' palette literals become token handles (visually a no-op,
# see builder/site_ai/nora/adopt.py). Idempotent: a chrome that already has a
# token prefix only has its tokens refreshed and its pages re-checked.
import frappe


def execute():
	from builder.site_ai.nora.adopt import adopt_everywhere

	if not frappe.db.exists("DocType", "Website Header Footer Config"):
		return
	try:
		reports = adopt_everywhere()
	except Exception:
		frappe.log_error("Design system adoption failed", frappe.get_traceback())
		return
	summary = "; ".join(
		f"{r.get('profile') or 'main site'}: {r.get('skipped') or f'{r.get('pages_changed')}/{r.get('pages')} pages, {r.get('values')} values, prefix {r.get('prefix')}'}"
		for r in reports
	)
	frappe.logger().info("design system adopted — " + summary)
