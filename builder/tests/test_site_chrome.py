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
