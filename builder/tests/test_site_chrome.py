# //// Neoffice — added file (no upstream equivalent): the legacy chrome injector serves visitors
# //// only, and its render errors keep their traceback (builder/overrides/site_chrome.py).
import unittest
from unittest.mock import patch

import frappe

from builder.overrides import site_chrome


class TestLegacyChrome(unittest.TestCase):
	def setUp(self):
		conf = patch.dict(frappe.conf, {"builder_legacy_site_chrome": 1})
		conf.start()
		self.addCleanup(conf.stop)
		shown = patch("builder.website_switch.hidden_from_visitor", return_value=False)
		shown.start()
		self.addCleanup(shown.stop)

	def test_a_render_with_no_request_gets_no_chrome(self):
		"""The website search index renders the routes from a job: no visitor there, and a navbar
		whose Jinja reads the request failed, twice a day on a migrated client site."""
		context = frappe._dict()
		with (
			patch.object(frappe.local, "request", None, create=True),
			patch.object(site_chrome, "get_builder_component_html") as component,
		):
			site_chrome.inject_site_chrome(context)
		component.assert_not_called()
		self.assertNotIn("navbar_html", context)

	def test_a_render_error_keeps_its_traceback(self):
		"""The message alone said "request": the frame that read it was lost."""
		data = {"success": True, "content": "{{ broken }}", "page_data": {}}
		with (
			patch.object(frappe, "call", return_value=data),
			patch("frappe.utils.jinja.render_template", side_effect=AttributeError("request")),
			patch.object(frappe, "log_error") as log,
		):
			site_chrome.get_builder_component_html("navbar")
		title, message = log.call_args.args
		self.assertEqual(title, "Legacy chrome Jinja render error")
		self.assertIn("Component navbar: request", message)
		self.assertIn("Traceback", message)


# //// Neoffice — added tests (2026-09-15): the footer's legal row. A site that HAS a privacy
# //// policy must let a visitor reach it from every page, and a shop without its terms in the
# //// footer is refused by the payment providers.
class TestFooterLegalRow(unittest.TestCase):
	def _links(self, rows, columns=None, profile="A Storefront"):
		from builder.hf_utils import header_footer

		config = frappe._dict({"website_profile": profile})
		with (
			patch.object(header_footer.frappe.db, "exists", side_effect=lambda dt, name=None: dt == "DocType" and name == "Builder Page"),
			patch.object(header_footer.frappe, "get_all", return_value=rows),
		):
			return header_footer._legal_links(config, columns or {})

	def test_the_legal_pages_are_found_by_route_and_ordered(self):
		rows = [
			{"route": "privacy-policy", "page_title": "Politique de confidentialité"},
			{"route": "home", "page_title": "Accueil"},
			{"route": "terms-conditions", "page_title": "Conditions générales"},
		]
		self.assertEqual(
			[("/terms-conditions", "Conditions générales"), ("/privacy-policy", "Politique de confidentialité")],
			[(row["url"], row["label"]) for row in self._links(rows)],
		)

	def test_a_page_the_client_already_placed_is_not_repeated(self):
		rows = [{"route": "terms-conditions", "page_title": "CGV"}, {"route": "privacy-policy", "page_title": "Confidentialité"}]
		columns = {"Legal": [frappe._dict({"url": "/terms-conditions", "label": "CGV"})]}
		self.assertEqual(["/privacy-policy"], [row["url"] for row in self._links(rows, columns)])

	def test_a_site_without_legal_pages_gets_no_row(self):
		self.assertEqual([], self._links([{"route": "home", "page_title": "Accueil"}]))
