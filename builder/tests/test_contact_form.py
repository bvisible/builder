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
