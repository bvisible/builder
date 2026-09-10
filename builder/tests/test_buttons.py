# //// Neoffice — added file (no upstream equivalent): the buttons and calls to action passes.
import unittest

from builder.site_ai.nora.buttons import guess_target, repair_button_variants, wire_dead_ctas

PALETTE = {"tla-primary": "#1b1f24", "tla-secondary": "#e578d1", "tla-background": "#1b1f24", "tla-text": "#f5f5f5"}
ROUTES = ["/", "/a-propos", "/nos-marques", "/espace-revendeurs", "/contact", "/login", "/all-products", "/compte-professionnel"]


def button(text, variant, block_id="b1"):
	return {"element": "a", "blockId": block_id, "classes": ["u-btn", variant], "attributes": {"href": "/contact"}, "innerHTML": text}


class TestButtonVariants(unittest.TestCase):
	def test_a_primary_button_on_a_primary_section_becomes_secondary(self):
		# a hero whose section wears the background token, which IS the primary colour
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--tla-background)"}, "children": [button("Contactez-nous", "u-btn--primary")]}
		light = {"element": "section", "baseStyles": {"backgroundColor": "#fefefe"}, "children": [button("Contactez-nous", "u-btn--primary", "b2")]}
		edits = repair_button_variants([hero, light], PALETTE)
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--secondary"])
		self.assertEqual(light["children"][0]["classes"], ["u-btn", "u-btn--primary"])
		self.assertEqual(len(edits), 1)

	def test_without_a_contrasting_secondary_the_button_is_outlined(self):
		palette = dict(PALETTE, **{"tla-secondary": "#1b1f24"})
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--tla-primary)"}, "children": [button("Contactez-nous", "u-btn--primary")]}
		repair_button_variants([hero], palette)
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--outline"])

	def test_two_filled_buttons_side_by_side_keep_one_main_action(self):
		# a hero with a contact and a catalogue button on a primary-coloured section: both
		# would turn secondary, so the second steps back to outline
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--tla-primary)"}, "children": [{"element": "div", "children": [button("Voir le catalogue", "u-btn--secondary", "b1"), button("Contactez-nous", "u-btn--primary", "b2")]}]}
		repair_button_variants([hero], PALETTE)
		row = hero["children"][0]["children"]
		self.assertEqual(row[0]["classes"], ["u-btn", "u-btn--secondary"])
		self.assertEqual(row[1]["classes"], ["u-btn", "u-btn--outline"])

	def test_the_background_is_inherited_from_the_section(self):
		# the button sits in a grid inside the dark section: the section's colour still counts
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--tla-primary)"}, "children": [{"element": "div", "children": [button("Voir", "u-btn--primary")]}]}
		repair_button_variants([hero], PALETTE)
		self.assertEqual(hero["children"][0]["children"][0]["classes"], ["u-btn", "u-btn--secondary"])


class TestCallsToAction(unittest.TestCase):
	def test_a_bare_learn_more_becomes_a_link_to_the_matching_page(self):
		# the card names a brand, the section says "brands": the section's words decide
		card = {"element": "div", "children": [{"element": "h3", "innerHTML": "Aurora"}, {"element": "p", "innerHTML": "Textile et accessoires"}, {"element": "span", "blockId": "s1", "innerHTML": "En savoir plus"}]}
		login = {"element": "div", "children": [{"element": "h3", "innerHTML": "Espace revendeur"}, {"element": "span", "blockId": "s2", "innerHTML": "Se connecter"}]}
		section = {"element": "section", "children": [{"element": "h2", "innerHTML": "Marques et services"}, card, login]}
		edits = wire_dead_ctas([section], ROUTES, "/contact")
		self.assertEqual(card["children"][2]["element"], "a")
		self.assertEqual(card["children"][2]["attributes"]["href"], "/nos-marques")
		self.assertEqual(login["children"][1]["attributes"]["href"], "/login")
		self.assertEqual(len(edits), 2)

	def test_a_real_link_and_plain_copy_are_left_alone(self):
		link = {"element": "a", "attributes": {"href": "/about"}, "innerHTML": "Découvrir l’agence"}
		copy = {"element": "p", "innerHTML": "Voir grand, c'est notre métier depuis 2004 et nous en sommes fiers."}
		edits = wire_dead_ctas([link, copy], ROUTES, "/contact")
		self.assertEqual(edits, [])
		self.assertEqual(link["attributes"]["href"], "/about")
		self.assertEqual(copy["element"], "p")

	def test_every_card_of_a_grid_gets_the_action_of_its_siblings(self):
		def card(title, with_action):
			children = [{"element": "h3", "blockId": "h" + title, "innerHTML": title}]
			if with_action:
				children.append({"element": "a", "blockId": "a" + title, "attributes": {"href": "/nos-marques"}, "innerHTML": "En savoir plus"})
			return {"element": "div", "blockId": "c" + title, "children": children}

		grid = {"element": "div", "classes": ["u-grid", "u-grid--3"], "children": [card("Volcom", True), card("West Snowboards", False), card("Espace revendeur", True)]}
		edits = wire_dead_ctas([grid], ROUTES, "/contact")
		west = grid["children"][1]["children"]
		self.assertEqual(west[-1]["element"], "a")
		self.assertEqual(west[-1]["innerHTML"], "En savoir plus")
		self.assertEqual(west[-1]["attributes"]["href"], "/nos-marques")
		self.assertNotEqual(west[-1]["blockId"], "aVolcom")
		self.assertEqual(len(edits), 1)

	def test_a_link_to_another_site_s_page_comes_home(self):
		from builder.site_ai.nora.buttons import repair_foreign_links

		# the model linked the about page of the instance's other site: this site's about page
		about = {"element": "a", "attributes": {"href": "/about"}, "innerHTML": "Découvrir l’agence"}
		file = {"element": "a", "attributes": {"href": "/files/brochure.pdf"}, "innerHTML": "Brochure"}
		ours = {"element": "a", "attributes": {"href": "/contact?from=home"}, "innerHTML": "Contact"}
		external = {"element": "a", "attributes": {"href": "https://example.ch/"}, "innerHTML": "example.ch"}
		edits = repair_foreign_links([about, file, ours, external], ROUTES, "/contact")
		self.assertEqual(about["attributes"]["href"], "/a-propos")
		self.assertEqual(file["attributes"]["href"], "/files/brochure.pdf")
		self.assertEqual(ours["attributes"]["href"], "/contact?from=home")
		self.assertEqual(external["attributes"]["href"], "https://example.ch/")
		self.assertEqual(len(edits), 1)

	def test_the_target_follows_the_words(self):
		self.assertEqual(guess_target("Demander un compte revendeur", ROUTES, "/contact"), "/espace-revendeurs")
		self.assertEqual(guess_target("Voir le catalogue", ROUTES, "/contact"), "/all-products")
		self.assertEqual(guess_target("Découvrir l'agence", ROUTES, "/contact"), "/a-propos")
		self.assertEqual(guess_target("En savoir plus", ROUTES, "/contact"), "/contact")
