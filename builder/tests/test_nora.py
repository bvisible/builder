# //// Neoffice — added file (no upstream equivalent): tests of the site playbook helpers.
"""The pure parts of builder/site_ai/nora: page normalisation, token prefixes, the
layout choice, the page brief, the text-card parser and the capability rules. No
model is called; frappe is only needed for the capability and managed-model
helpers (site_config)."""

import unittest
from unittest.mock import patch

import frappe

from builder.site_ai.capabilities import MANAGED_DISABLED_TOOLS, disabled_tools
from builder.site_ai.nora.cards import parse_card
from builder.site_ai.nora.site_builder import (
	_color,
	choose_layout_system,
	normalise_pages,
	page_brief_text,
	placeholder_photos,
	token_prefix,
)


class FakeBrief:
	design_concept = "Editorial workshop"
	signature_element = "Oversized numerals"
	site_tone = "professional"
	hero_style = "split"
	heading_font = "Raleway"
	body_font = "Source Sans 3"
	border_radius_style = "subtle"
	cta_shape = "Rounded"
	button_hover = "Darken"
	motion_style = "Calm"


class TestPages(unittest.TestCase):
	def test_known_titles_get_their_route_and_type(self):
		pages = normalise_pages(["Accueil", "À propos", "Prestations", "Contact", "FAQ", "Boutique"], "vitrine")
		self.assertEqual([p["route"] for p in pages], ["home", "about", "services", "contact", "faq", "shop"])
		self.assertEqual(pages[0]["type"], "accueil")
		self.assertEqual(pages[2]["type"], "services")

	def test_home_comes_first_whatever_the_order(self):
		pages = normalise_pages(["Contact", "Accueil"], "vitrine")
		self.assertEqual(pages[0]["route"], "home")

	def test_unknown_title_is_slugged_and_generic(self):
		(page,) = normalise_pages([{"title": "Nos ateliers créatifs"}], "vitrine")
		self.assertEqual(page["route"], "nos-ateliers-creatifs")
		self.assertEqual(page["type"], "generic")

	def test_duplicate_routes_collapse(self):
		pages = normalise_pages(["Accueil", "Home", "Contact"], "vitrine")
		self.assertEqual(len(pages), 2)

	def test_empty_list_falls_back_to_the_site_type_defaults(self):
		pages = normalise_pages([], "vitrine")
		self.assertTrue(pages and pages[0]["route"] == "home")


class TestTokens(unittest.TestCase):
	def test_prefix_is_the_initials_or_the_first_word(self):
		self.assertEqual(token_prefix("The League Agency"), "tla")
		self.assertEqual(token_prefix("The 5 Burrows"), "t5b")
		self.assertEqual(token_prefix("Fromagerie"), "fromager")

	def test_colour_values_are_literal_or_the_fallback(self):
		self.assertEqual(_color("var(--muted-color)", "#123456", fallback="#000"), "#123456")
		self.assertEqual(_color("", None, fallback="#1a1a1a"), "#1a1a1a")
		self.assertEqual(_color("rgba(0,0,0,0.5)", fallback="#000"), "rgba(0,0,0,0.5)")


class TestLayout(unittest.TestCase):
	def test_direction_words_pick_the_system(self):
		self.assertEqual(choose_layout_system("Poster affirmé", FakeBrief()), "poster-brutalist")
		self.assertEqual(choose_layout_system("grille éditoriale", FakeBrief()), "editorial-grid")

	def test_tone_decides_without_a_direction(self):
		self.assertEqual(choose_layout_system("", FakeBrief()), "editorial-grid")


class TestPageBrief(unittest.TestCase):
	def test_brief_carries_handles_photos_and_rules(self):
		site = {"site_name": "Atelier Lumen", "activity": "Menuiserie", "differentiators": "Bois suisse"}
		handles = {k: f"var(--al-{k})" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		page = {"title": "Contact", "route": "contact", "type": "contact"}
		photos = placeholder_photos(page, "Menuiserie sur mesure")
		text = page_brief_text(site, FakeBrief(), page, handles, "", "editorial-grid", "French", photos, ("Contactez-nous", "/contact"))
		self.assertIn("var(--al-primary)", text)
		self.assertIn("INTERIOR page", text)
		self.assertIn("placehold.co", text)
		self.assertIn("no header, navigation or footer", text)
		self.assertIn("u-btn", text)
		self.assertIn("'Atelier Lumen'", text)

	def test_home_page_opens_with_the_hero(self):
		site = {"site_name": "X", "activity": "Y"}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		text = page_brief_text(site, FakeBrief(), {"title": "Accueil", "route": "home", "type": "accueil"}, handles, "", "bento", "French", [], ("CTA", "/"))
		self.assertIn("HOME page", text)


class TestTextCards(unittest.TestCase):
	def test_a_one_line_multi_choices_card(self):
		spec = parse_card("Quelles pages ? [choices multi: Accueil, Contact, FAQ] [buttons: Continue]")
		self.assertEqual(spec["text"], "Quelles pages ?")
		choices = spec["ui"][0]
		self.assertEqual(choices["kind"], "choices")
		self.assertTrue(choices["multi"])
		self.assertEqual([o["label"] for o in choices["options"]], ["Accueil", "Contact", "FAQ"])
		self.assertEqual(spec["ui"][-1]["kind"], "actions")

	def test_palettes_keep_their_colours_and_buttons_split(self):
		text = (
			"Couleurs.\n[choices: \n- Noyer: chaleureux\n  [colors: #3B2B20, #B08548]\n- Ardoise: sobre\n  [colors: #31413A, #A98A5B]]\n"
			"[color_input: Ou vos couleurs\n- Primaire: dominante, #3B2B20\n- Secondaire: accents, #B08548]\n[buttons: Créer le site / Modifier]"
		)
		spec = parse_card(text)
		self.assertEqual(spec["ui"][0]["options"][0]["colors"], ["#3B2B20", "#B08548"])
		self.assertEqual(spec["ui"][1]["kind"], "color_input")
		self.assertEqual([b["label"] for b in spec["ui"][-1]["buttons"]], ["Créer le site", "Modifier"])

	def test_a_recap_with_heading_and_list(self):
		spec = parse_card("Récap :\n[heading: Atelier]\n[list:\n- Pages : Accueil\n- Couleurs : #000]\n[buttons: Créer le site, Modifier]")
		self.assertEqual([el["kind"] for el in spec["ui"]], ["heading", "list", "actions"])

	def test_plain_prose_is_not_a_card(self):
		self.assertIsNone(parse_card("Le site est créé. Il comprend cinq pages."))
		self.assertIsNone(parse_card(""))

	def test_a_card_without_any_control_is_not_materialised(self):
		self.assertIsNone(parse_card("Voici :\n[heading: Titre]\n[list:\n- a]"))


class TestCapabilities(unittest.TestCase):
	def test_managed_instance_drops_the_schema_tools(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": None}):
			self.assertEqual(disabled_tools(), list(MANAGED_DISABLED_TOOLS))

	def test_self_hosted_keeps_everything(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 0, "nora_disabled_tools": None}):
			self.assertEqual(disabled_tools(), [])

	def test_site_config_overrides_the_list(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": "run_python, seed_sample_data"}):
			self.assertEqual(disabled_tools(), ["run_python", "seed_sample_data"])
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": []}):
			self.assertEqual(disabled_tools(), [])
