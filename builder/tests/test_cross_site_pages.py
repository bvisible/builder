# //// Neoffice — added file (no upstream equivalent): a page of one site must not answer on
# //// another site of the same instance, whichever renderer resolved it.
"""The guard that closes the multi-site hole in the renderer chain.

BuilderPageRenderer refuses a page tagged for another Website Profile. Frappe, however, tries
its renderers in turn, and when ours declines, upstream's DocumentPage picks the very same
Builder Page up by route and serves it. Measured on a two-site instance on 2026-09-16: one
site's domain answered the other's /a-propos and /nos-marques with 200 and no canonical,
because the render never went through our renderer at all.

A check made by one renderer is not isolation. The guard therefore lives in the document's own
get_context, which every renderer must go through.
"""

import unittest
from unittest.mock import patch

import frappe

from builder.builder.doctype.builder_page import builder_page as module


class TestCrossSitePages(unittest.TestCase):
	def page(self, profile):
		doc = frappe.get_doc({"doctype": "Builder Page", "page_title": "P", "route": "p", "blocks": "[]"})
		doc.neo_website_profile = profile
		return doc

	def refusal(self, page_profile, current_profile, has_field=True):
		"""Whether the page refuses to render under that profile."""
		with patch.object(module, "_page_has_site_field", return_value=has_field), patch.object(
			module, "_current_site_profile", return_value=current_profile
		):
			try:
				self.page(page_profile)._refuse_another_sites_page()
			except frappe.PageDoesNotExistError:
				return True
		return False

	def test_another_sites_page_does_not_answer_here(self):
		self.assertTrue(self.refusal("Site A", "Site B"))

	def test_the_sites_own_page_answers(self):
		self.assertFalse(self.refusal("Site A", "Site A"))

	def test_an_untagged_page_still_serves_everywhere(self):
		# the rule a multi-site instance already relies on: shared pages carry no profile
		self.assertFalse(self.refusal(None, "Site B"))
		self.assertFalse(self.refusal("", "Site B"))

	def test_nothing_is_refused_when_no_site_is_resolved(self):
		# the editor, the build's own server-side render, a one-site instance
		self.assertFalse(self.refusal("Site A", None))

	def test_an_instance_without_the_field_is_untouched(self):
		self.assertFalse(self.refusal("Site A", "Site B", has_field=False))

	def test_the_guard_runs_before_anything_else_in_get_context(self):
		"""It has to be the first thing: get_context reads page data and deletes context keys,
		and a page of another site must not get that far."""
		import inspect

		source = inspect.getsource(module.BuilderPage.get_context)
		body = [line.strip() for line in source.split("\n") if line.strip() and not line.strip().startswith(("#", '"""', "def "))]
		self.assertEqual("self._refuse_another_sites_page()", body[0])
