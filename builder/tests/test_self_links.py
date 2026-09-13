# //// Neoffice — added file (no upstream equivalent): a call to action never leads to the page
# //// it is on (builder/site_ai/nora/buttons.py).
import unittest

from builder.site_ai.nora.buttons import drop_closing_band, retarget_self_links

FORM = "{% include 'builder/templates/includes/contact_form.html' %}"


def button(href, words="Contact us"):
	return {
		"element": "a",
		"classes": ["u-btn", "u-btn--primary"],
		"attributes": {"href": href},
		"innerHTML": words,
	}


class TestSelfLinks(unittest.TestCase):
	def test_on_the_contact_page_the_button_goes_to_the_form(self):
		form = {"element": "div", "innerHTML": FORM}
		closing = button("/contact")
		band = {
			"element": "section",
			"children": [{"element": "h2", "innerHTML": "Start a conversation"}, closing],
		}
		edits = retarget_self_links([{"element": "div", "children": [form, band]}], "contact", "/contact")
		self.assertEqual(closing["attributes"]["href"], "#contact-form")
		self.assertEqual(form["attributes"]["id"], "contact-form")
		self.assertIn("scrollMarginTop", form["baseStyles"])
		self.assertEqual(len(edits), 1)

	def test_elsewhere_an_invitation_goes_to_the_call_to_action(self):
		self_link = button("/brands", "See the brands")
		retarget_self_links([self_link], "brands", "/contact")
		self.assertEqual(self_link["attributes"]["href"], "/contact")

	def test_links_to_other_pages_and_anchors_stay(self):
		other, anchor = button("/contact"), button("/about#team")
		retarget_self_links([other, anchor], "about", "/contact")
		self.assertEqual(other["attributes"]["href"], "/contact")
		self.assertEqual(anchor["attributes"]["href"], "/about#team")

	def test_a_plain_label_is_not_retargeted(self):
		label = button("/", "Home")
		retarget_self_links([label], "home", "/contact")
		self.assertEqual(label["attributes"]["href"], "/")


class TestClosingBand(unittest.TestCase):
	"""A contact page closed on "Vous avez une question ? Voir le formulaire", under its own form."""

	def page(self, *last):
		form = {"element": "section", "children": [{"element": "div", "innerHTML": FORM}]}
		return [{"element": "div", "children": [form, {"element": "section", "children": list(last)}]}]

	def test_a_band_back_to_the_page_goes(self):
		blocks = self.page({"element": "h2", "innerHTML": "Vous avez une question ?"}, button("#contact-form", "Voir le formulaire"))
		self.assertEqual(drop_closing_band(blocks, "contact"), ["Vous avez une question ?"])
		self.assertEqual(len(blocks[0]["children"]), 1)

	def test_a_band_to_another_page_or_holding_the_form_stays(self):
		elsewhere = self.page({"element": "h2", "innerHTML": "Nos tarifs"}, button("/tarifs", "Voir les tarifs"))
		self.assertEqual(drop_closing_band(elsewhere, "contact"), [])
		alone = [{"element": "div", "children": [{"element": "section", "children": [{"element": "div", "innerHTML": FORM}, button("/contact#top")]}]}]
		self.assertEqual(drop_closing_band(alone, "contact"), [])
		self.assertEqual(len(alone[0]["children"]), 1)
