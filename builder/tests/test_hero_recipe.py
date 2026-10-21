# //// Neoffice — added file (no upstream equivalent): what stands behind the home's hero is said to the writer.
"""Over 23 test builds the hero of the home was a flat block of the primary colour in 17 and a photograph in none: the writer
was given the bare word "image" (2026-10-20). The recipe is a line of the home's page brief; no model is called."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.site_ai.nora.hero import composition, hero_recipe
from builder.site_ai.nora.site_builder import page_brief_text
from builder.site_ai.nora.site_plan import PlannedPage, PlannedSection, section_lines

HANDLES = {
	"primary": "var(--t-primary)",
	"secondary": "var(--t-secondary)",
	"background": "var(--t-background)",
	"text": "var(--t-text)",
	"font-heading": "var(--t-font-heading)",
	"font-body": "var(--t-font-body)",
}
# a deep red, a gold, a warm white and a deep brown ink
PALETTE = {"t-primary": "#7a2e1d", "t-secondary": "#d9b26f", "t-background": "#faf5ee", "t-text": "#2b1810"}
PHOTO = "https://placehold.co/1600x900/e5e7eb/9ca3af/png?text=Inn%2C%20hero"


class TestTheHeroPhoto(unittest.TestCase):
	def test_an_image_hero_is_a_photograph_under_the_site_s_own_veil(self):
		text = hero_recipe("image", HANDLES, PALETTE, "", PHOTO)
		self.assertIn("classes: [u-over-image]", text)
		self.assertIn(f"src: '{PHOTO}'", text)
		self.assertIn("objectFit: cover", text)
		self.assertIn("write no overlay", text)
		self.assertNotIn("linear-gradient", text)

	def test_the_example_is_valid_yaml_the_page_parser_expands(self):
		from builder.ai.page_writer import expand_page_yaml

		text = hero_recipe("image", HANDLES, PALETTE, "", PHOTO)
		example = text[text.index("- el: section") :]
		indented = "\n".join("  " + line for line in example.splitlines())
		page = (
			"el: div\nname: body\nstyle: {display: flex, flexDirection: column, alignItems: center}\nc:\n"
			+ indented
		)
		blocks, _script = expand_page_yaml(page)
		hero = blocks[0]["children"][0]
		self.assertEqual(hero["element"], "section")
		self.assertIn("u-over-image", hero["classes"])
		picture = hero["children"][0]
		self.assertEqual(picture["element"], "img")
		self.assertEqual(picture["attributes"]["src"], PHOTO)
		self.assertEqual(picture["baseStyles"]["position"], "absolute")

	def test_a_photograph_needs_no_palette_to_be_asked_for(self):
		self.assertIn("u-over-image", hero_recipe("image", HANDLES, None, "", PHOTO))

	def test_an_image_hero_without_a_photograph_is_a_gradient_not_a_bare_block(self):
		text = hero_recipe("image", HANDLES, PALETTE, "", None)
		self.assertNotIn("u-over-image", text)
		self.assertIn("backgroundImage: '", text)
		self.assertIn("linear-gradient(160deg", text)


class TestTheHeroGradient(unittest.TestCase):
	def test_a_dark_primary_goes_into_the_ink_with_a_glow_of_the_secondary(self):
		text = hero_recipe("gradient", HANDLES, PALETTE, "", PHOTO)
		self.assertNotIn("u-over-image", text)
		self.assertIn("linear-gradient(160deg, var(--t-primary) 0%, var(--t-text) 100%)", text)
		self.assertIn("radial-gradient(ellipse at 80% 15%, rgba(217, 178, 111, 0.28)", text)
		self.assertIn("The ink is var(--t-background)", text)

	def test_a_dark_primary_with_a_light_ink_goes_into_a_deeper_shade_of_itself(self):
		palette = {**PALETTE, "t-text": "#f2f2f2"}
		text = hero_recipe("solid", HANDLES, palette, "", None)
		self.assertIn("linear-gradient(160deg, var(--t-primary) 0%, #", text)
		self.assertNotIn("var(--t-text) 100%", text)

	def test_a_light_ground_keeps_the_hero_light(self):
		text = hero_recipe("gradient", HANDLES, PALETTE, "light", None)
		self.assertIn("backgroundColor: var(--t-background)", text)
		self.assertIn("linear-gradient(160deg, var(--t-background) 0%, rgba(", text)
		self.assertIn("The ink is var(--t-text)", text)
		self.assertNotIn("radial-gradient", text)

	def test_a_light_style_gets_the_light_gradient_even_on_a_dark_primary(self):
		for style in ("minimal", "split", "asymmetric", "cards"):
			self.assertIn("a tint of the brand", hero_recipe(style, HANDLES, PALETTE, "", None), style)

	def test_a_mid_primary_on_an_ordinary_site_is_a_tint_of_the_brand_on_light(self):
		palette = {**PALETTE, "t-primary": "#c8a2c8"}
		self.assertIn("a tint of the brand", hero_recipe("gradient", HANDLES, palette, "", None))

	def test_a_dark_site_with_a_pale_primary_starts_from_its_own_dark_background(self):
		palette = {**PALETTE, "t-primary": "#c8a2c8", "t-background": "#14110f", "t-text": "#f5efe6"}
		text = hero_recipe("gradient", HANDLES, palette, "dark", None)
		self.assertIn("linear-gradient(160deg, var(--t-background) 0%, #", text)
		self.assertIn("The ink is var(--t-text)", text)

	def test_a_site_without_colours_is_told_nothing(self):
		self.assertEqual(hero_recipe("gradient", HANDLES, None, "", None), "")
		self.assertEqual(hero_recipe("gradient", {}, PALETTE, "", None), "")


def _expand(recipe):
	"""The recipe's YAML section, expanded by the page parser under a root block (what the writer would hand back)."""
	from builder.ai.page_writer import expand_page_yaml

	example = recipe[recipe.index("- el: section") :]
	indented = "\n".join("  " + line for line in example.splitlines())
	page = (
		"el: div\nname: body\nstyle: {display: flex, flexDirection: column, alignItems: center}\nc:\n"
		+ indented
	)
	blocks, _script = expand_page_yaml(page)
	return blocks[0]["children"][0]


class TestHowTheCopySits(unittest.TestCase):
	def test_the_composition_comes_from_the_hero_style_and_the_tone(self):
		self.assertEqual(composition("split", "professional", PHOTO), "split")
		self.assertEqual(composition("asymmetric", "bold", PHOTO), "split")
		self.assertEqual(composition("cards", "", PHOTO), "split")
		# a split needs its photograph
		self.assertEqual(composition("split", "professional", None), "left")
		self.assertEqual(composition("minimal", "professional", None), "centred")
		self.assertEqual(composition("image", "elegant", PHOTO), "centred")
		self.assertEqual(composition("gradient", "minimal", None), "centred")
		for tone in ("professional", "bold", "playful", "", None):
			self.assertEqual(composition("image", tone, PHOTO), "left", tone)

	def test_a_centred_photograph_hero_sits_low_under_the_even_veil(self):
		text = hero_recipe("image", HANDLES, PALETTE, "", PHOTO, tone="elegant")
		hero = _expand(text)
		self.assertEqual(hero["classes"], ["u-over-image", "u-over-image--center"])
		self.assertEqual(hero["baseStyles"]["alignItems"], "flex-end")
		copy = hero["children"][1]
		self.assertEqual(copy["baseStyles"]["textAlign"], "center")
		self.assertEqual(copy["baseStyles"]["alignItems"], "center")
		self.assertIn("CENTRED", text)

	def test_a_left_photograph_hero_keeps_the_default_veil_and_its_copy_on_the_left(self):
		hero = _expand(hero_recipe("image", HANDLES, PALETTE, "", PHOTO, tone="bold"))
		self.assertEqual(hero["classes"], ["u-over-image"])
		self.assertEqual(hero["children"][1]["baseStyles"]["alignItems"], "flex-start")

	def test_left_copy_is_kept_on_the_veiled_half_and_centred_copy_is_not(self):
		"""A sentence running across the whole photograph sat on its bright half, where the left-hand veil has faded (2026-10-20)."""
		left = hero_recipe("image", HANDLES, PALETTE, "", PHOTO, tone="bold")
		self.assertIn("the sentence maxWidth 28rem", left)
		self.assertIn("on the left half", left)
		centred = hero_recipe("image", HANDLES, PALETTE, "", PHOTO, tone="elegant")
		self.assertNotIn("28rem", centred)
		self.assertIn("the sentence maxWidth 36rem", centred)

	def test_copy_over_a_photograph_carries_a_soft_shadow_and_copy_on_a_gradient_does_not(self):
		"""The subtitle of a left-aligned hero sat on a bright patch of sky, where the veil has little to give (2026-10-21)."""
		for tone in ("bold", "elegant"):
			copy = _expand(hero_recipe("image", HANDLES, PALETTE, "", PHOTO, tone=tone))["children"][1]
			self.assertEqual(copy["baseStyles"]["textShadow"], "0 1px 14px rgba(0,0,0,0.5)", tone)
		split = _expand(hero_recipe("split", HANDLES, PALETTE, "", PHOTO))
		self.assertNotIn("textShadow", split["children"][0]["baseStyles"])

	def test_the_site_grid_is_the_copy_s_own(self):
		handles = {
			**HANDLES,
			"container": "var(--t-container)",
			"gutter": "var(--t-gutter)",
			"gutter-phone": "var(--t-gutter-phone)",
		}
		copy = _expand(hero_recipe("image", handles, PALETTE, "", PHOTO))["children"][1]
		self.assertEqual(copy["baseStyles"]["maxWidth"], "var(--t-container)")
		self.assertEqual(copy["baseStyles"]["paddingLeft"], "var(--t-gutter)")

	def test_a_split_hero_is_a_narrow_column_of_copy_beside_a_wide_photograph(self):
		text = hero_recipe("split", HANDLES, PALETTE, "", PHOTO)
		self.assertNotIn("u-over-image", text)
		hero = _expand(text)
		self.assertIn("linear-gradient(160deg, var(--t-background) 0%", hero["baseStyles"]["backgroundImage"])
		grid = hero["children"][0]
		self.assertEqual(grid["baseStyles"]["gridTemplateColumns"], "5fr 7fr")
		picture = next(b for b in grid["children"] if b.get("element") == "img")
		self.assertIn("u-media", picture["classes"])
		self.assertEqual(picture["attributes"]["src"], PHOTO)

	def test_a_centred_gradient_hero_is_told_to_centre_its_copy(self):
		self.assertIn("Centre the copy", hero_recipe("gradient", HANDLES, PALETTE, "", None, tone="elegant"))
		self.assertIn("Centre the copy", hero_recipe("minimal", HANDLES, PALETTE, "", None))
		self.assertNotIn("Centre the copy", hero_recipe("gradient", HANDLES, PALETTE, "", None, tone="bold"))


class TestThePlanDoesNotOverrideTheRecipe(unittest.TestCase):
	"""The plan's own layout for the hero ("a full-height centred block on the primary colour") was read before the recipe and
	followed over it: the home of a build came out flat although its brief asked for a split hero (2026-10-20)."""

	def page(self):
		return PlannedPage(
			route="home",
			title="Accueil",
			sections=[
				PlannedSection(
					kind="hero",
					purpose="open the site",
					copy="the promise",
					layout="full-height centred block on the primary",
					photos=[PHOTO],
				),
				PlannedSection(kind="intro", purpose="who they are", layout="two columns 5fr 7fr"),
			],
		)

	def test_a_dressed_hero_keeps_its_copy_and_drops_its_layout_and_photos(self):
		hero, intro = section_lines(self.page(), hero_dressed=True)
		self.assertIn("copy: the promise", hero)
		self.assertIn("HERO BACKGROUND", hero)
		self.assertNotIn("centred block", hero)
		self.assertNotIn(PHOTO, hero)
		# the other sections are untouched
		self.assertIn("layout: two columns 5fr 7fr", intro)

	def test_without_a_recipe_the_plan_reads_as_before(self):
		hero = section_lines(self.page())[0]
		self.assertIn("layout: full-height centred block on the primary", hero)
		self.assertIn(PHOTO, hero)


class TestThePageBrief(unittest.TestCase):
	def brief(self, page, photos, style="image", tone=""):
		site = {
			"site_name": "Atelier Test",
			"activity": "a workshop",
			"site_type": "vitrine",
			"profile": None,
			"page_types": ["accueil", page["type"]],
		}
		with patch("builder.site_ai.nora.site_builder.available_includes", return_value=[]):
			return page_brief_text(
				site,
				SimpleNamespace(hero_style=style, site_tone=tone),
				page,
				HANDLES,
				"",
				"classic-centered",
				"French",
				photos,
				("Contact", "/contact"),
				palette=PALETTE,
			)

	def test_the_home_is_told_what_stands_behind_its_hero_with_its_first_photograph(self):
		text = self.brief(
			{"title": "Accueil", "route": "home", "type": "accueil"},
			[PHOTO, "https://placehold.co/1200x800/e5e7eb/9ca3af/png?text=Second"],
		)
		self.assertIn("HERO BACKGROUND", text)
		self.assertIn(f"src: '{PHOTO}'", text)
		# the second photograph is in the list of photos, not in the hero
		self.assertEqual(text.count("text=Second"), 1)

	def test_the_tone_of_the_brief_decides_how_the_copy_sits(self):
		page = {"title": "Accueil", "route": "home", "type": "accueil"}
		self.assertIn("u-over-image--center", self.brief(page, [PHOTO], tone="elegant"))
		self.assertNotIn(
			"u-over-image--center",
			self.brief(page, [PHOTO], tone="bold").split("HERO BACKGROUND")[1].split("PAGE NOTES")[0],
		)

	def test_an_interior_page_has_no_hero_to_dress(self):
		text = self.brief({"title": "À propos", "route": "about", "type": "about"}, [PHOTO])
		self.assertNotIn("HERO BACKGROUND", text)


if __name__ == "__main__":
	unittest.main()
