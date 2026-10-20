# //// Neoffice — added file (no upstream equivalent): the script of a form the assistant connected
# //// (2026-10-20, plan of neoffice-maintenance#1593).
"""A booking or sign-up form made by connect_form used to post its fields to Frappe's own web_form.accept, open to every
guest at ten requests a minute with nothing else. It now posts to the one door of the site's forms, with the token and
the traps of the contact form.

What is held here:
  * where the site keeps forms the script posts to that door, for this form, with the token and the decoy; where it
    does not (Unpress, a theme that predates the forms) the old script stands;
  * the three values the script is written from can be read back from either version (the patch that rewrites the
    scripts that exist relies on it, selector with quotes included);
  * the patch rewrites an old script into the guarded one, keeping the form, the selector and the fields, and leaves
    a script that is already guarded, or a site without forms, alone."""

import json
import re
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import site_forms
from builder.ai.agent.pending import build_form_script
from builder.builder.patches import rewire_connected_forms

FIELDS = ["guest_name", "guest_email", "people"]


def old_script(selector=".booking-form", web_form="test-booking"):
	with patch.object(site_forms, "available", return_value=False):
		return build_form_script(selector, web_form, FIELDS)


def new_script(selector=".booking-form", web_form="test-booking"):
	with patch.object(site_forms, "available", return_value=True):
		return build_form_script(selector, web_form, FIELDS)


class TestTheScript(FrappeTestCase):
	def test_where_the_site_keeps_forms_the_script_posts_to_the_one_door(self):
		script = new_script()
		self.assertIn("neoffice_theme.website_messages.submit", script)
		self.assertIn("neoffice_theme.website_messages.issue_token", script)
		self.assertIn("'webform:' + WF", script)
		self.assertNotIn("web_form.web_form.accept", script)
		for part in ("token", "elapsed", "answers", "data-neo-decoy"):
			self.assertIn(part, script)

	def test_where_it_keeps_none_the_old_script_stands(self):
		script = old_script()
		self.assertIn("frappe.website.doctype.web_form.web_form.accept", script)
		self.assertNotIn("website_messages", script)

	def test_the_values_are_read_back_from_either_version(self):
		for script in (old_script(), new_script()):
			found = re.search(site_forms.SCRIPT_VALUES, script)
			self.assertEqual(json.loads(found["selector"]), ".booking-form")
			self.assertEqual(json.loads(found["web_form"]), "test-booking")
			self.assertEqual(json.loads(found["fields"]), FIELDS)

	def test_a_selector_with_quotes_survives(self):
		selector = 'form[data-x="a b"] .row, #id'
		for script in (old_script(selector), new_script(selector)):
			found = re.search(site_forms.SCRIPT_VALUES, script)
			self.assertEqual(json.loads(found["selector"]), selector)

	def test_the_script_is_javascript(self):
		import shutil
		import subprocess
		import tempfile

		node = shutil.which("node")
		if not node:
			self.skipTest("node is not installed here")
		with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
			handle.write(new_script())
		result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
		self.assertEqual(result.returncode, 0, result.stderr)


class TestThePatch(FrappeTestCase):
	def setUp(self):
		super().setUp()
		forget_capability()
		if not site_forms.available():
			self.skipTest("the theme that keeps forms is not installed here")
		self.name = f"Save Test {uuid.uuid4().hex[:6]} submissions"
		self.make(old_script(web_form="test-booking-" + uuid.uuid4().hex[:4]))

	def tearDown(self):
		if frappe.db.exists("Builder Client Script", self.name):
			frappe.delete_doc("Builder Client Script", self.name, force=True, ignore_permissions=True)
		forget_capability()
		super().tearDown()

	def make(self, script):
		frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"name": self.name,
				"script_type": "JavaScript",
				"script": script,
			}
		).insert(ignore_permissions=True)

	def script(self):
		return frappe.db.get_value("Builder Client Script", self.name, "script")

	def test_an_old_script_is_rewritten_with_the_same_form_selector_and_fields(self):
		before = re.search(site_forms.SCRIPT_VALUES, self.script())
		rewire_connected_forms.execute()
		after = self.script()
		self.assertNotIn("web_form.web_form.accept", after)
		self.assertIn("neoffice_theme.website_messages.submit", after)
		kept = re.search(site_forms.SCRIPT_VALUES, after)
		for key in ("selector", "web_form", "fields"):
			self.assertEqual(kept[key], before[key])

	def test_a_script_already_guarded_is_left_alone(self):
		rewire_connected_forms.execute()
		once = self.script()
		rewire_connected_forms.execute()
		self.assertEqual(self.script(), once)

	def test_a_site_without_forms_keeps_its_old_scripts(self):
		before = self.script()
		with patch.object(site_forms, "available", return_value=False):
			rewire_connected_forms.execute()
		self.assertEqual(self.script(), before)

	def test_a_script_that_is_not_a_connected_forms_is_not_touched(self):
		other = "Hand written " + uuid.uuid4().hex[:6]
		frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"name": other,
				"script_type": "JavaScript",
				"script": "console.log(1)",
			}
		).insert(ignore_permissions=True)
		try:
			rewire_connected_forms.execute()
			self.assertEqual(frappe.db.get_value("Builder Client Script", other, "script"), "console.log(1)")
		finally:
			frappe.delete_doc("Builder Client Script", other, force=True, ignore_permissions=True)


def forget_capability():
	frappe.local.builder_site_forms_available = None
