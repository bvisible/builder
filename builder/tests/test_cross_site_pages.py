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

	def refusal(self, page_profile, current_profile, has_field=True, for_preview=None):
		"""Whether the page refuses to render under that profile."""
		from types import SimpleNamespace

		request = SimpleNamespace(for_preview=for_preview)
		with patch.object(module, "_page_has_site_field", return_value=has_field), patch.object(
			module, "_current_site_profile", return_value=current_profile
		), patch.object(frappe.local, "request", request, create=True):
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

	def test_an_editors_preview_is_not_a_visitors_request(self):
		"""get_page_preview_html renders a page BY NAME for someone who holds read permission on
		it, from whichever domain the editor is open on. Refusing there broke the editor."""
		self.assertFalse(self.refusal("Site A", "Site B", for_preview=True))
		# and it is still refused for anyone actually browsing that domain
		self.assertTrue(self.refusal("Site A", "Site B", for_preview=None))

	def test_the_guard_runs_before_anything_else_in_get_context(self):
		"""It has to be the first thing: get_context reads page data and deletes context keys,
		and a page of another site must not get that far."""
		import inspect

		source = inspect.getsource(module.BuilderPage.get_context)
		body = [line.strip() for line in source.split("\n") if line.strip() and not line.strip().startswith(("#", '"""', "def "))]
		self.assertEqual("self._refuse_another_sites_page()", body[0])


class TestTheRouteIsClaimedNotDropped(unittest.TestCase):
	"""Refusing by DECLINING is what opened the hole: frappe then offers the route to its own
	DocumentPage, which serves the page anyway. Our renderer has to claim it and answer 404."""

	def renderer(self, path="a-propos"):
		return module.BuilderPageRenderer(path=path, http_status_code=None)

	def can_render(self, mine_exists, other_exists, profile="Site B"):
		with patch.object(module, "find_page_with_path", return_value="page-1" if mine_exists else None), patch.object(
			module, "_current_site_profile", return_value=profile
		), patch.object(module, "_route_of_another_site", return_value=other_exists), patch.object(
			module, "get_web_pages_with_dynamic_routes", return_value=[]
		):
			page = self.renderer()
			with patch.object(module.BuilderPageRenderer, "validate_access"):
				return page.can_render(), getattr(page, "belongs_to_another_site", False)

	def test_another_sites_route_is_claimed_so_frappe_never_offers_it_elsewhere(self):
		claimed, refused = self.can_render(mine_exists=False, other_exists=True)
		self.assertTrue(claimed, "declining hands the route to frappe's DocumentPage")
		self.assertTrue(refused)

	def test_a_route_nobody_has_is_left_alone(self):
		claimed, refused = self.can_render(mine_exists=False, other_exists=False)
		self.assertFalse(claimed)
		self.assertFalse(refused)

	def test_the_sites_own_page_is_rendered_not_refused(self):
		claimed, refused = self.can_render(mine_exists=True, other_exists=True)
		self.assertTrue(claimed)
		self.assertFalse(refused)

	def test_a_claimed_route_renders_the_404_page(self):
		page = self.renderer()
		page.belongs_to_another_site = True
		with patch("frappe.website.page_renderers.not_found_page.NotFoundPage") as not_found:
			not_found.return_value.render.return_value = "404 response"
			self.assertEqual("404 response", page.render())
		not_found.assert_called_once_with("a-propos")

	def test_the_question_is_only_asked_of_a_site_that_has_one(self):
		# no profile resolved (editor, build render, single-site instance): nothing is refused
		with patch.object(module, "_page_has_site_field", return_value=True):
			self.assertFalse(module._route_of_another_site("a-propos", None))
		with patch.object(module, "_page_has_site_field", return_value=False):
			self.assertFalse(module._route_of_another_site("a-propos", "Site B"))
