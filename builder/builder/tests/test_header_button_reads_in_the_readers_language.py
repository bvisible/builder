# //// Neoffice — added file (no upstream equivalent): the header button reads in the reader's language
# //// (maintenance#1091). Its default text, « Contact Us », read in English on every French portal.
import frappe
from frappe.tests.utils import FrappeTestCase

TEMPLATE = (
	"{% from 'builder/templates/includes/header_footer/macros.html' import render_cta %}{{ render_cta(cta) }}"
)


def _button(text):
	return frappe.render_template(TEMPLATE, {"cta": {"text": text, "url": "/contact", "style": "Primary"}})


class TestTheHeaderButtonReadsInTheReadersLanguage(FrappeTestCase):
	def setUp(self):
		self.lang = frappe.local.lang
		frappe.local.lang = "fr"

	def tearDown(self):
		frappe.local.lang = self.lang

	def test_the_default_text_is_translated(self):
		self.assertNotIn("Contact Us", _button("Contact Us"))
		self.assertIn(frappe._("Contact Us"), _button("Contact Us"))

	def test_a_text_the_client_wrote_is_kept(self):
		self.assertIn("Écrivez-nous", _button("Écrivez-nous"))
