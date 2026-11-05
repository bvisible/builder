# //// Neoffice — added file (no upstream equivalent): what the editor's shell answers a visitor.
import unittest
from unittest.mock import patch

import frappe

from builder.www import _builder


class TestTheShellForAVisitor(unittest.TestCase):
	def setUp(self):
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user("Guest")

	def test_a_visitor_goes_to_the_login_page_on_the_site_s_own_path(self):
		"""The merge that reads the path per site left the redirect naming a variable gone: 500 for every visitor."""
		with (
			patch.object(_builder, "get_boot", return_value={}),
			patch.object(_builder, "get_builder_path", return_value="editor"),
			patch.object(_builder.EditorDemo, "from_app_path", return_value=None),
			self.assertRaises(frappe.Redirect),
		):
			_builder.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/editor")
