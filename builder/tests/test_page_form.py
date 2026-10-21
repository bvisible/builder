# //// Neoffice — added file (no upstream equivalent): a page made to be written to always carries the site's form.
"""Built with the local model, the booking page of a restaurant came out with no form in two builds of two: its title was not one the
generator knew, so the page was typed "generic", the contact form was not offered to it and nobody drew one (2026-10-21). No model is
called."""

import unittest

from builder.site_ai.nora import page_form
from builder.site_ai.nora.site_builder import _bare, normalise_pages, repair_includes

HANDLES = {
	"primary": "var(--t-primary)",
	"secondary": "var(--t-secondary)",
	"background": "var(--t-background)",
	"text": "var(--t-text)",
	"font-heading": "var(--t-font-heading)",
	"font-body": "var(--t-font-body)",
}
PALETTE = {"t-primary": "#7a2e1d", "t-secondary": "#d9b26f", "t-background": "#faf5ee", "t-text": "#2b1810"}


def section(name, *children, html=None):
	block = {"blockId": name, "element": "section", "blockName": name, "children": list(children)}
	if html is not None:
		block["innerHTML"] = html
	return block


def body(*sections):
	return [{"blockId": "root", "element": "div", "blockName": "body", "children": list(sections)}]


def kinds(blocks):
	return [c.get("blockName") for c in blocks[0]["children"]]


class TestTheTitlesOfAPageMadeToBeWrittenTo(unittest.TestCase):
	def test_book_reserve_quote_and_contact_in_three_languages(self):
		for title in (
			"Réserver",
			"Réservation",
			"Réserver une table",
			"Reservations de groupes",
			"Booking",
			"Book a table",
			"Demande de devis",
			"Devis",
			"Request a quote",
			"Get a Quote",
			"Offerte anfragen",
			"Anfrage",
			"Prendre rendez-vous",
			"Rendez-vous",
			"Appointments",
			"Terminvereinbarung",
			"Nous contacter",
			"Contactez-nous",
			"Contact us",
			"Kontakt",
			"Contact",
		):
			self.assertTrue(page_form.wants_form(_bare(title)), title)

	def test_the_other_pages_are_left_alone(self):
		for title in (
			"Accueil",
			"La carte",
			"Groupes et banquets",
			"L'auberge",
			"Prestations",
			"L'équipe",
			"Conditions générales",
			"Politique de confidentialité",
			"Mentions légales",
			"Terminal",
			"Blog",
			"Création d'entreprise",
			"FAQ",
			"Tarifs",
		):
			self.assertFalse(page_form.wants_form(_bare(title)), title)

	def test_a_quote_asks_the_questions_and_a_booking_takes_a_message(self):
		self.assertEqual(page_form.form_model(_bare("Demande de devis")), "questions")
		self.assertEqual(page_form.form_model(_bare("Request a quote")), "questions")
		self.assertEqual(page_form.form_model(_bare("Réserver")), "simple")
		self.assertEqual(page_form.form_model(_bare("Contact")), "simple")


class TestThePageTypes(unittest.TestCase):
	def types(self, *titles):
		return {p["title"]: p["type"] for p in normalise_pages([{"title": t} for t in titles], "vitrine")}

	def test_a_booking_page_is_a_contact_page(self):
		got = self.types("Accueil", "La carte", "Réserver")
		self.assertEqual(got["Réserver"], "contact")
		self.assertEqual(got["La carte"], "generic")
		self.assertEqual(got["Accueil"], "accueil")

	def test_a_known_title_keeps_its_type(self):
		got = self.types("Contact", "Conditions générales", "FAQ", "Tarifs")
		self.assertEqual(got["Contact"], "contact")
		self.assertEqual(got["Conditions générales"], "legal")
		self.assertEqual(got["FAQ"], "faq")
		self.assertEqual(got["Tarifs"], "pricing")

	def test_the_contact_the_site_names_is_the_target_of_its_call_to_action(self):
		import inspect

		from builder.site_ai.nora import site_builder

		source = inspect.getsource(site_builder.build_site)
		self.assertIn('KNOWN_PAGES.get(_bare(p["title"]), (None,))[0] == "contact"', source)


class TestAPageWithoutItsForm(unittest.TestCase):
	def test_the_form_is_there_when_a_page_carries_the_include(self):
		tag = page_form.tag()
		self.assertTrue(page_form.has_form(body(section("a"), section("b", html=tag))))
		self.assertTrue(
			page_form.has_form(
				body(
					section("a"),
					section(
						"b",
						{
							"element": "div",
							"innerHTML": "{% include 'builder/templates/includes/site_form.html' %}",
						},
					),
				)
			)
		)
		self.assertTrue(page_form.has_form(body(section("a", {"element": "form", "blockName": "mine"}))))

	def test_a_page_without_one_has_none(self):
		self.assertFalse(
			page_form.has_form(body(section("a"), section("b", html="<p>Réservez par téléphone</p>")))
		)
		self.assertFalse(
			page_form.has_form(
				body(section("a", {"element": "p", "innerHTML": "an include word and nothing else"}))
			)
		)

	def test_the_form_comes_right_after_the_opening_section(self):
		blocks = body(section("opening"), section("story"), section("closing"))
		self.assertTrue(
			page_form.ensure_form(
				blocks, {"type": "contact", "title": "Réserver"}, "reserver", HANDLES, PALETTE
			)
		)
		self.assertEqual(kinds(blocks), ["opening", "form-section", "story", "closing"])

	def test_a_page_of_one_section_gets_it_after_that_section(self):
		blocks = body(section("only"))
		self.assertTrue(
			page_form.ensure_form(
				blocks, {"type": "contact", "title": "Contact"}, "contact", HANDLES, PALETTE
			)
		)
		self.assertEqual(kinds(blocks), ["only", "form-section"])

	def test_the_section_carries_the_include_and_no_copy_of_its_own(self):
		blocks = body(section("opening"), section("closing"))
		page_form.ensure_form(
			blocks, {"type": "contact", "title": "Demande de devis"}, "demande de devis", HANDLES, PALETTE
		)
		added = blocks[0]["children"][1]
		texts = []

		def walk(node):
			if node.get("innerHTML"):
				texts.append(node["innerHTML"])
			for child in node.get("children") or []:
				walk(child)

		walk(added)
		self.assertEqual(len(texts), 1)
		self.assertIn("contact_form.html", texts[0])
		self.assertIn('contact_model = "questions"', texts[0])
		self.assertNotIn("WRITE", texts[0])

	def test_a_page_that_has_its_form_is_left_alone_and_nothing_is_added_twice(self):
		blocks = body(section("opening"), section("form", html=page_form.tag()))
		self.assertFalse(
			page_form.ensure_form(
				blocks, {"type": "contact", "title": "Contact"}, "contact", HANDLES, PALETTE
			)
		)
		blocks = body(section("opening"), section("closing"))
		self.assertTrue(
			page_form.ensure_form(
				blocks, {"type": "contact", "title": "Réserver"}, "reserver", HANDLES, PALETTE
			)
		)
		self.assertFalse(
			page_form.ensure_form(
				blocks, {"type": "contact", "title": "Réserver"}, "reserver", HANDLES, PALETTE
			)
		)
		self.assertEqual(kinds(blocks).count("form-section"), 1)

	def test_the_other_pages_and_the_legal_ones_never_get_one(self):
		for page, bare in (
			({"type": "generic", "title": "La carte"}, "la carte"),
			({"type": "legal", "title": "Conditions générales"}, "conditions generales"),
			({"type": "legal", "title": "Contact"}, "contact"),
			({"type": "about", "title": "L'auberge"}, "l'auberge"),
		):
			blocks = body(section("opening"), section("closing"))
			self.assertFalse(page_form.ensure_form(blocks, page, bare, HANDLES, PALETTE), page["title"])
			self.assertEqual(kinds(blocks), ["opening", "closing"])

	def test_a_page_whose_title_says_book_gets_one_even_when_it_is_not_typed_contact(self):
		blocks = body(section("opening"), section("closing"))
		self.assertTrue(
			page_form.ensure_form(
				blocks, {"type": "generic", "title": "Booking"}, "booking", HANDLES, PALETTE
			)
		)

	def test_an_empty_page_is_left_alone(self):
		self.assertFalse(
			page_form.ensure_form([], {"type": "contact", "title": "Contact"}, "contact", HANDLES, PALETTE)
		)

	def test_the_added_form_survives_the_include_repair(self):
		blocks = body(section("opening"), section("closing"))
		page_form.ensure_form(blocks, {"type": "contact", "title": "Réserver"}, "reserver", HANDLES, PALETTE)
		fixed, dropped = repair_includes(blocks, [])
		self.assertEqual(dropped, 0)
		self.assertTrue(page_form.has_form(blocks))

	def test_the_tag_is_a_catalogued_one(self):
		from builder.site_ai import components

		parsed = components.parse_tag(page_form.tag("questions"))
		self.assertIsNotNone(parsed)
		self.assertEqual(parsed[1], {"contact_model": "questions"})


class TestThePlanIsToldToo(unittest.TestCase):
	def test_the_rules_of_the_plan_name_the_form(self):
		from types import SimpleNamespace

		from builder.site_ai.nora.site_plan import plan_prompt

		site = {"site_name": "Atelier", "activity": "a workshop", "site_type": "vitrine"}
		text = plan_prompt(
			site,
			SimpleNamespace(),
			[{"route": "reserver", "title": "Réserver", "type": "contact"}],
			{},
			[],
			"French",
		)
		self.assertIn("A page made to be written to", text)
		self.assertIn("'contact-form' section", text)


if __name__ == "__main__":
	unittest.main()
