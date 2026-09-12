# //// Neoffice — added file (no upstream equivalent): the contact form the site generator
# //// includes reads on the section it sits in (neoffice-maintenance#394).
import pathlib
import re
import unittest

TEMPLATE = pathlib.Path(__file__).parent.parent / "templates/includes/contact_form.html"


def _rule(css: str, selector: str) -> str:
	"""The declarations of the first rule whose selector list starts with `selector`."""
	match = re.search(re.escape(selector) + r"[^{]*\{([^}]*)\}", css)
	return match.group(1) if match else ""


class TestTheContactFormFollowsItsSection(unittest.TestCase):
	"""On a dark site, in a light band, the labels were light on light and the fields black:
	the form wore the site's tokens instead of the ink of the section it sits in."""

	def setUp(self):
		source = TEMPLATE.read_text()
		# the rules only: the comments above them name the very tokens this test forbids
		self.css = re.sub(r"/\*.*?\*/", "", source.split("<style>", 1)[1], flags=re.S)

	def test_the_labels_wear_the_ink_of_their_section(self):
		self.assertIn("color: inherit", _rule(self.css, ".builder-contact-form label"))

	def test_the_fields_are_drawn_from_that_ink_not_from_the_site_tokens(self):
		fields = _rule(self.css, ".builder-contact-form input,")
		self.assertIn("color: inherit", fields)
		self.assertIn("background: transparent", fields)
		self.assertIn("currentColor", fields)
		for token in ("--text-color", "--surface-color", "--border-color"):
			self.assertNotIn(token, fields)

	def test_no_colour_comes_from_a_token_the_chrome_does_not_define(self):
		# --primary-color-dark is defined nowhere: the button turned blue under the pointer
		self.assertNotIn("--primary-color-dark", self.css)
		for blue in ("#3b82f6", "#2563eb", "59, 130, 246"):
			self.assertNotIn(blue, self.css)


class TestTheContactFormDeliversTheMessage(unittest.TestCase):
	"""The name field was named `sender` like the email one: frappe kept the first value, so
	send_message refused every message, a name not being an address (neoffice-maintenance#398)."""

	def setUp(self):
		source = TEMPLATE.read_text()
		self.form = source.split("<style>", 1)[0]
		self.script = source.split("<script>", 1)[1]

	def test_only_the_email_field_is_the_sender(self):
		senders = re.findall(r"<input\b[^>]*\bname=\"sender\"[^>]*>", self.form)
		self.assertEqual(len(senders), 1)
		self.assertIn('type="email"', senders[0])

	def test_frappe_reads_the_address_as_the_sender(self):
		"""The fields in the order a browser posts them, through frappe's own parser."""
		from urllib.parse import urlencode

		import frappe
		from frappe.app import make_form_dict
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		sample = {"full_name": "Jane Doe", "sender": "jane-test@yopmail.com", "message": "Hello"}
		names = re.findall(r"<(?:input|textarea)\b[^>]*\bname=\"([^\"]+)\"", self.form)
		body = urlencode([(name, sample.get(name, "x")) for name in names])
		environ = EnvironBuilder(
			method="POST", data=body, content_type="application/x-www-form-urlencoded"
		).get_environ()
		previous = getattr(frappe.local, "form_dict", None)
		try:
			make_form_dict(Request(environ))
			self.assertEqual(frappe.local.form_dict.sender, "jane-test@yopmail.com")
		finally:
			frappe.local.form_dict = previous

	def test_the_name_and_the_phone_travel_in_the_message(self):
		# send_message takes sender, subject and message: any other field is dropped on the way
		for name in ("full_name", "phone", "message"):
			self.assertIn(f'field("{name}")', self.script)
		self.assertIn("message: (head.length", self.script)

	def test_the_subject_is_translated_not_written_in_french(self):
		self.assertNotIn("Contact depuis le site web", TEMPLATE.read_text())
		self.assertIn("_('Contact from the website')", self.form)
