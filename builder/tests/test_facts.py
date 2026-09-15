# //// Neoffice — added file (no upstream equivalent): the facts a written page states that its brief
# //// never gave (builder/site_ai/nora/facts.py), the photo slots a picture would lie in
# //// (placeholders.neutral_named_slots), and the site's name kept out of the image prompts.
import unittest

from builder.site_ai.nora.facts import facts_issues, invented_facts, known_text
from builder.site_ai.nora.placeholders import neutral_named_slots

KNOWN = known_text(
	{
		"site_name": "Physio Test",
		"activity": "Cabinet de physiothérapie à Sion ouvrant en octobre",
		"differentiators": "Claire Morand, physiothérapeute",
		"categories": ["Rééducation", "Pilates thérapeutique"],
	},
	"BUSINESS DATA: Rue du Test 5, 1950 Sion. Séance de 45 minutes : CHF 110.",
)
TODAY = "2026-09-13"
PALETTE = {"pt-background": "#ffffff", "pt-secondary": "#f3e9d9"}


def text(element, html, **styles):
	return {"element": element, "innerHTML": html, "baseStyles": styles, "children": []}


def box(*children):
	return {"element": "div", "children": list(children)}


class TestInventedFacts(unittest.TestCase):
	"""A practice about to open came out with prices, session lengths, an opening in "Octobre 2024"
	and a patient's testimonial, none of them in its brief."""

	def test_prices_durations_and_years_nobody_gave(self):
		page = [box(text("h3", "Bilan initial"), text("p", "CHF 120"), text("p", "60 minutes"), text("p", "Ouverture du cabinet : Octobre 2024"))]
		found = {(f["kind"], f["text"]) for f in invented_facts(page, "", KNOWN, TODAY)}
		self.assertIn(("price", "CHF 120"), found)
		self.assertIn(("quantity", "60 minutes"), found)
		self.assertIn(("year", "Octobre 2024"), found)

	def test_what_the_brief_gives_passes(self):
		page = [
			box(
				text("p", "Une séance de 45 minutes : CHF 110"),
				text("p", "Ouverture en octobre 2026"),
				text("p", "4 domaines de soins"),
				text("span", "01"),
				text("p", "Rue du Test 5, 1950 Sion"),
			)
		]
		self.assertEqual(invented_facts(page, "", KNOWN, TODAY), [])

	def test_a_signed_quotation_is_a_testimonial(self):
		quote = box(
			text("div", '<svg data-lucide="quote"></svg>'),
			text("p", "Claire est à l'écoute, précise et rassurante. Grâce à elle je retrouve confiance.", fontStyle="italic"),
			text("p", "Marie, patiente"),
		)
		self.assertEqual(invented_facts([quote], "", KNOWN, TODAY), [{"kind": "testimonial", "text": "Marie, patiente"}])

	def test_the_practitioner_the_brief_names_is_not_a_testimonial(self):
		about = box(
			text("h2", "Marc Dupont, votre physiothérapeute"),
			text("p", "« Formée aux dernières approches de rééducation, elle accompagne chaque patient avec rigueur. »"),
			text("p", "Claire Morand, physiothérapeute"),
		)
		self.assertEqual(invented_facts([about], "", KNOWN, TODAY), [])

	def test_the_data_script_is_read_but_not_its_paths(self):
		script = 'data.plans = [{"title": "Séance de suivi", "price": "CHF 90", "image": "/files/cabinet-2024.jpg"}]'
		self.assertEqual(invented_facts([], script, KNOWN, TODAY), [{"kind": "price", "text": "CHF 90"}])
		quotes = 'data.items = [{"quote": "Super", "author": "Marc"}]'
		self.assertEqual([f["kind"] for f in invented_facts([], quotes, KNOWN, TODAY)], ["testimonial"])

	def test_the_revision_is_told_what_to_remove(self):
		from builder.site_ai.nora.visual_check import revision_instructions

		issues = facts_issues([{"kind": "price", "text": "CHF 120"}, {"kind": "testimonial", "text": "Marie, patiente"}])
		self.assertEqual([i["area"] for i in issues], ["facts", "facts"])
		instructions = revision_instructions(issues)
		self.assertIn("'CHF 120'", instructions)
		self.assertIn("'Marie, patiente'", instructions)


class TestNamedSlots(unittest.TestCase):
	"""An access map drawn with a street address nobody gave, a stranger's face beside the name of
	the practitioner: pictures that state something false are not drawn."""

	def slot(self, alt):
		return {"element": "img", "attributes": {"src": "https://placehold.co/1024x640/e5e7eb/9ca3af/png?text=x", "alt": alt}}

	def test_a_named_person_a_portrait_and_a_map_are_not_drawn(self):
		page = [
			self.slot("Claire Morand, physiothérapeute à Sion"),
			self.slot("Portrait de la praticienne"),
			self.slot("Plan d'accès au cabinet"),
			self.slot("Espace lumineux du cabinet Physio Test"),
			self.slot("Séance de rééducation au cabinet"),
		]
		withheld = neutral_named_slots(page, PALETTE, "pt", names=["Physio Test", "Rééducation"])
		self.assertEqual(len(withheld), 3)
		self.assertTrue(page[0]["attributes"]["src"].startswith("data:image/svg+xml"))
		self.assertIn("placehold.co", page[3]["attributes"]["src"])
		self.assertIn("placehold.co", page[4]["attributes"]["src"])

	def test_a_title_case_alt_names_nobody(self):
		self.assertEqual(neutral_named_slots([self.slot("Physiotherapy Session In Progress")], PALETTE, "pt"), [])


class TestPlaceholdersAtRender(unittest.TestCase):
	"""A test site's home showed "Cave daffinage" in grey capitals across its hero: a slot the image
	job never filled is drawn as a plain block at render, and the stored page keeps it."""

	def test_a_slot_is_drawn_plain_and_the_stored_page_keeps_it(self):
		import json
		from unittest.mock import patch

		from builder.site_ai.nora import buttons, placeholders

		url = "https://placehold.co/1920x1080/2C1810/ffffff?text=Cave+daffinage"
		hero = {"element": "section", "baseStyles": {"background": f"linear-gradient(rgba(0,0,0,.5),rgba(0,0,0,.3)), url('{url}')"}}
		stored = json.dumps([hero])
		plain = json.dumps([{"element": "p", "innerHTML": "Bonjour"}])
		with patch.object(buttons, "_render_palette", return_value={"background": "#1b1f24", "secondary": "#a67c00"}):
			drawn = placeholders.neutral_for_render(stored)
			self.assertIs(placeholders.neutral_for_render(plain), plain)
		background = drawn[0]["baseStyles"]["background"]
		self.assertNotIn("placehold.co", background)
		# inside url('…') the data URI carries no bare quote that would close it
		inside = background.split("url('", 1)[1].rsplit("')", 1)[0]
		self.assertTrue(inside.startswith("data:image/svg+xml") and "'" not in inside)
		# the dark brown the hero was composed on, under its light text
		self.assertIn("2c1810", inside)
		self.assertIn("placehold.co", stored)

	def test_a_caption_with_an_apostrophe_is_replaced_whole(self):
		"""Cut at the apostrophe of "Cave+d'affinage", an image kept "'affinage" after its plain
		block and showed its alt text instead."""
		from builder.site_ai.nora.placeholders import neutral_placeholders

		img = {"element": "img", "attributes": {"src": "https://placehold.co/800x1000/A67C00/ffffff?text=Cave+d'affinage", "alt": "Cave"}}
		inline = {"element": "div", "innerHTML": "<img src=\"https://placehold.co/600x400/e5e7eb/9ca3af?text=L'atelier\" alt=\"\">"}
		self.assertEqual(neutral_placeholders([img, inline], {"x-background": "#ffffff", "x-secondary": "#b08548"}, "x"), 2)
		src = img["attributes"]["src"]
		self.assertTrue(src.startswith("data:image/svg+xml") and "affinage" not in src and "a67c00" in src)
		# our default grey stands for no colour: the site's own takes its place
		self.assertNotIn("atelier", inline["innerHTML"])
		self.assertIn("b08548", inline["innerHTML"])


class TestSiteIdentity(unittest.TestCase):
	"""A consumer site asked to show its new legal name and its town alone, while the company in
	ERPNext keeps its name and its full address."""

	def test_the_site_settings_name_the_business(self):
		from builder.api import site_identity

		config = frappe_dict(business_name="Atelier Nord Sàrl", business_address="Lausanne, Switzerland")
		# //// Neoffice — a site that names itself and gives no line of its own publishes NONE
		# //// (2026-09-15): the company's switchboard belongs to another business.
		self.assertEqual(
			site_identity(config),
			{"company_name": "Atelier Nord Sàrl", "address": "Lausanne, Switzerland", "phone": "", "email": "", "website": ""},
		)
		# with its own line, it publishes it
		own = frappe_dict(business_name="Atelier Nord Sàrl", business_address="Lausanne, Switzerland",
		                  business_phone="+41 21 000 00 00", business_email="bonjour@atelier-nord.test",
		                  business_website="https://atelier-nord.test")
		self.assertEqual(
			site_identity(own),
			{"company_name": "Atelier Nord Sàrl", "address": "Lausanne, Switzerland",
			 "phone": "+41 21 000 00 00", "email": "bonjour@atelier-nord.test", "website": "https://atelier-nord.test"},
		)
		# empty settings leave the company's own data in place
		self.assertEqual(site_identity(frappe_dict(business_name="", business_address="  ")), {})
		self.assertEqual(site_identity(None), {})


def frappe_dict(**values):
	import frappe

	return frappe._dict(values)


class TestImagePrompt(unittest.TestCase):
	def test_the_site_name_stays_out_of_the_picture(self):
		"""Asked for "the practice <name>", the image model lettered the name on a wall."""
		from builder.api import _build_image_prompt

		prompt = _build_image_prompt("Espace lumineux du cabinet Physio Test", subject="physiothérapie", avoid=("Physio Test",))
		self.assertNotIn("Physio Test", prompt)
		self.assertIn("Espace lumineux du cabinet", prompt)
