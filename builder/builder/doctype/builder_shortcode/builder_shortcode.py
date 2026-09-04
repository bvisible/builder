#//// Neoffice — added file (no upstream equivalent): registry of reusable Jinja components the
#//// generator may include. Neoffice DocType, no upstream counterpart. First commit 057ddaaa
#//// 2026-02-02.
# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuilderShortcode(Document):
	pass


def get_all_shortcodes():
	"""Get all enabled shortcodes for AI generation context."""
	shortcodes = frappe.get_all(
		"Builder Shortcode",
		filters={"enabled": 1},
		fields=["shortcode_name", "category", "description", "usage_syntax", "parameters", "example_code"]
	)
	return shortcodes


def get_shortcodes_for_prompt():
	"""Format shortcodes for inclusion in AI prompts."""
	shortcodes = get_all_shortcodes()
	if not shortcodes:
		return ""

	lines = ["## Available Shortcodes\n"]
	for sc in shortcodes:
		lines.append(f"### {sc.shortcode_name}")
		if sc.description:
			lines.append(sc.description)
		if sc.usage_syntax:
			lines.append(f"```jinja\n{sc.usage_syntax}\n```")
		lines.append("")

	return "\n".join(lines)
