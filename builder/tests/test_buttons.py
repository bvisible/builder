# //// Neoffice — added file (no upstream equivalent): the buttons and calls to action passes.
import json
import unittest
from unittest.mock import patch

from builder.site_ai.nora import buttons
from builder.site_ai.nora.buttons import (
	guess_target,
	repair_button_variants,
	settle_for_render,
	settle_rendered_variants,
	wire_dead_ctas,
)

PALETTE = {"site-primary": "#1b1f24", "site-secondary": "#e578d1", "site-background": "#1b1f24", "site-text": "#f5f5f5"}
# a light site whose primary reads on its page: the theme paints the buttons as they are
LIGHT = {"site-primary": "#2f6f5e", "site-secondary": "#e8d9b0", "site-background": "#ffffff", "site-text": "#1f272e"}
ROUTES = ["/", "/a-propos", "/nos-marques", "/espace-revendeurs", "/contact", "/login", "/all-products", "/compte-professionnel"]


def button(text, variant, block_id="b1"):
	return {"element": "a", "blockId": block_id, "classes": ["u-btn", variant], "attributes": {"href": "/contact"}, "innerHTML": text}


class TestButtonVariants(unittest.TestCase):
	# the colours judged are the ones the theme paints (rendered_buttons, header_footer.
	# button_colours): on the dark site above, whose primary is its own background, the theme
	# paints the primary buttons in the readable secondary and outlines the secondary ones

	def test_on_a_dark_site_the_primary_button_already_reads(self):
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--site-background)"}, "children": [button("Contactez-nous", "u-btn--primary")]}
		light = {"element": "section", "baseStyles": {"backgroundColor": "#fefefe"}, "children": [button("Contactez-nous", "u-btn--primary", "b2")]}
		self.assertEqual(repair_button_variants([hero, light], PALETTE), [])
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--primary"])

	def test_on_a_section_of_the_colour_it_is_painted_it_is_outlined(self):
		# the pink section of the dark site: its primary buttons are painted pink too, and its
		# secondary ones are outlines, so the button steps back to an outline
		band = {"element": "section", "baseStyles": {"backgroundColor": "var(--site-secondary)"}, "children": [button("Contactez-nous", "u-btn--primary"), button("Catalogue", "u-btn--secondary", "b2")]}
		repair_button_variants([band], PALETTE)
		self.assertEqual(band["children"][0]["classes"], ["u-btn", "u-btn--outline"])
		# an outlined secondary reads everywhere
		self.assertEqual(band["children"][1]["classes"], ["u-btn", "u-btn--secondary"])

	def test_a_primary_button_on_a_primary_section_becomes_secondary(self):
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--site-primary)"}, "children": [button("Contactez-nous", "u-btn--primary")]}
		repair_button_variants([hero], LIGHT)
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--secondary"])

	def test_two_filled_buttons_side_by_side_keep_one_main_action(self):
		# a hero with a contact and a catalogue button on a primary-coloured section: both
		# would turn secondary, so the second steps back to outline
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--site-primary)"}, "children": [{"element": "div", "children": [button("Voir le catalogue", "u-btn--secondary", "b1"), button("Contactez-nous", "u-btn--primary", "b2")]}]}
		repair_button_variants([hero], LIGHT)
		row = hero["children"][0]["children"]
		self.assertEqual(row[0]["classes"], ["u-btn", "u-btn--secondary"])
		self.assertEqual(row[1]["classes"], ["u-btn", "u-btn--outline"])

	def test_the_background_is_inherited_from_the_section(self):
		# the button sits in a grid inside the primary section: the section's colour still counts
		hero = {"element": "section", "baseStyles": {"backgroundColor": "var(--site-primary)"}, "children": [{"element": "div", "children": [button("Voir", "u-btn--primary")]}]}
		repair_button_variants([hero], LIGHT)
		self.assertEqual(hero["children"][0]["children"][0]["classes"], ["u-btn", "u-btn--secondary"])


	def test_an_outline_button_over_a_photograph_gets_its_own_backing(self):
		"""The ghost "Contact us" of a photo hero was a dark outline on a dark photograph."""
		hero = {
			"element": "section",
			"classes": ["u-over-image", "u-over-image--bottom"],
			"children": [
				{"element": "img", "baseStyles": {"position": "absolute"}, "children": []},
				button("Contact us", "u-btn--outline", "b1"),
				{"element": "div", "baseStyles": {"backgroundColor": "#ffffff"}, "children": [button("Read", "u-btn--outline", "b2")]},
			],
		}
		edits = repair_button_variants([hero], PALETTE)
		self.assertEqual(hero["children"][1]["classes"], ["u-btn", "u-btn--on-image"])
		# a card of its own colour inside the photograph keeps its outline
		self.assertEqual(hero["children"][2]["children"][0]["classes"], ["u-btn", "u-btn--outline"])
		self.assertEqual(sum("on-image" in e for e in edits), 1)
		# a tile whose photograph is laid across it counts as well
		tile = {"element": "a", "children": [{"element": "img", "baseStyles": {"position": "absolute"}}, button("Go", "u-btn--ghost", "b3")]}
		repair_button_variants([tile], PALETTE)
		self.assertEqual(tile["children"][1]["classes"], ["u-btn", "u-btn--on-image"])

class TestRenderedVariants(unittest.TestCase):
	"""The render's half: the page keeps the variant its author chose, the render draws the one
	that reads with the theme of the moment."""

	def band(self, *children, background="var(--site-secondary)", **styles):
		return {"element": "section", "baseStyles": dict(styles, backgroundColor=background), "children": list(children)}

	def test_a_primary_on_a_band_of_its_painted_colour_is_drawn_as_an_outline(self):
		band = self.band(button("Contactez-nous", "u-btn--primary"))
		page = {"element": "section", "children": [button("Contactez-nous", "u-btn--primary", "b2")]}
		self.assertEqual(settle_rendered_variants([band, page], PALETTE), 1)
		self.assertEqual(band["children"][0]["classes"], ["u-btn", "u-btn--outline"])
		# on the dark page itself the pink button reads
		self.assertEqual(page["children"][0]["classes"], ["u-btn", "u-btn--primary"])

	def test_a_variant_worn_beside_it_is_not_doubled(self):
		hero = self.band(button("Catalogue", "u-btn--secondary", "b1"), button("Contact", "u-btn--primary", "b2"), background="var(--site-primary)")
		self.assertEqual(settle_rendered_variants([hero], LIGHT), 1)
		self.assertEqual([b["classes"][1] for b in hero["children"]], ["u-btn--secondary", "u-btn--outline"])
		alone = self.band(button("Contact", "u-btn--primary"), background="var(--site-primary)")
		settle_rendered_variants([alone], LIGHT)
		self.assertEqual(alone["children"][0]["classes"], ["u-btn", "u-btn--secondary"])

	def test_a_button_over_a_photograph_keeps_its_variant(self):
		hero = self.band(button("Contact", "u-btn--primary"), backgroundImage="url(/files/hero.jpg)")
		self.assertEqual(settle_rendered_variants([hero], PALETTE), 0)
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--primary"])

	# //// Neoffice — added test (2026-09-15): an outline over a photograph reads on no picture,
	# //// so the render gives it the design system's own backing, whatever the stored page says.
	def test_an_outline_over_a_photograph_takes_the_backing_at_render(self):
		hero = self.band(button("Contact us", "u-btn--outline"), backgroundImage="url(/files/hero.jpg)")
		self.assertEqual(settle_rendered_variants([hero], PALETTE), 1)
		self.assertEqual(hero["children"][0]["classes"], ["u-btn", "u-btn--on-image"])
		# and a section already scrimmed by the build is a photograph too
		veiled = self.band(button("Contact us", "u-btn--ghost"))
		veiled["classes"] = ["u-over-image"]
		self.assertEqual(settle_rendered_variants([veiled], PALETTE), 1)
		self.assertEqual(veiled["children"][0]["classes"], ["u-btn", "u-btn--on-image"])
		# one that already carries the backing is left alone
		done = self.band(button("Contact us", "u-btn--on-image"), backgroundImage="url(/files/hero.jpg)")
		self.assertEqual(settle_rendered_variants([done], PALETTE), 0)

	def test_the_render_leaves_the_stored_page_alone(self):
		stored = json.dumps([self.band(button("Contactez-nous", "u-btn--primary"))])
		with patch.object(buttons, "_render_palette", return_value=PALETTE):
			drawn = settle_for_render(stored)
			readable = json.dumps([{"element": "section", "children": [button("Go", "u-btn--primary")]}])
			self.assertIs(settle_for_render(readable), readable)
		self.assertEqual(drawn[0]["children"][0]["classes"], ["u-btn", "u-btn--outline"])
		self.assertIn("u-btn--primary", stored)

	def test_a_page_without_buttons_or_a_failure_renders_as_stored(self):
		plain = json.dumps([{"element": "section", "children": [{"element": "p", "innerHTML": "Bonjour"}]}])
		with patch.object(buttons, "_render_palette", side_effect=AssertionError("not reached")):
			self.assertIs(settle_for_render(plain), plain)
		stored = json.dumps([self.band(button("Go", "u-btn--primary"))])
		with patch.object(buttons, "_render_palette", side_effect=RuntimeError("no theme")), patch("frappe.log_error") as log:
			self.assertIs(settle_for_render(stored), stored)
		log.assert_called_once()


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

		grid = {"element": "div", "classes": ["u-grid", "u-grid--3"], "children": [card("Aurora", True), card("Bravo Boards", False), card("Espace revendeur", True)]}
		edits = wire_dead_ctas([grid], ROUTES, "/contact")
		west = grid["children"][1]["children"]
		self.assertEqual(west[-1]["element"], "a")
		self.assertEqual(west[-1]["innerHTML"], "En savoir plus")
		self.assertEqual(west[-1]["attributes"]["href"], "/nos-marques")
		self.assertNotEqual(west[-1]["blockId"], "aAurora")
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
