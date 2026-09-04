#//// Neoffice — added file (no upstream equivalent): serves the translation catalog the SPA asks for at
#//// boot (same contract as lms/insights/mail). Neoffice-only: upstream's SPA is English-only and has
#//// no catalog endpoint. First commit 0ab11671 2026-07-31.
# Translation catalog for the Builder frontend.
# The Vue app has no build-time locale bundle: it asks for the catalog of the
# logged-in user's language at boot (cached client-side). Same contract as the
# other Frappe SPAs (lms, insights, mail).
import frappe


@frappe.whitelist(allow_guest=True)
def get_translations() -> dict:
	"""Every installed app's messages for the current language, merged."""
	language = frappe.local.lang or frappe.db.get_default("lang") or "en"
	if language == "en":
		# nothing to send: the source strings ARE English
		return {}
	return frappe.translate.get_all_translations(language)
