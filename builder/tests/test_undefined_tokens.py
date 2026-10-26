# //// Neoffice — added file (no upstream equivalent): a token the writer invented is replaced by the one it meant.
"""The writer wrote `var(--<prefix>-tint)` for a tinted band; nothing defines it, the browser drops the declaration, the band paints nothing.
What is pinned: a ground becomes the brand tint the recipes use, a deep one the primary, an ink the text, a pale ink the background; a token
the site defines, a variable with its own fallback and a variable of someone else are left alone; every breakpoint is read; no model, no database."""

import unittest

from builder.site_ai.nora.undefined_tokens import repair_undefined_tokens

TOKENS = {"t-primary": "#253357", "t-secondary": "#434647", "t-background": "#ffffff", "t-text": "#434647", "t-accent": "#3f8f5b", "t-gutter": "64px"}


def block(**styles):
	return {"element": "section", "baseStyles": dict(styles), "children": []}


def repaired(**styles):
	blocks = [block(**styles)]
	edits = repair_undefined_tokens(blocks, TOKENS, "t")
	return blocks[0]["baseStyles"], edits


class TestAnInventedTokenIsReplacedByWhatItMeant(unittest.TestCase):
	def test_a_tinted_ground_becomes_the_tint_of_the_recipes(self):
		styles, edits = repaired(backgroundColor="var(--t-tint)")
		self.assertEqual("rgba(37, 51, 87, 0.08)", styles["backgroundColor"])
		self.assertEqual(["backgroundColor: t-tint -> rgba(37, 51, 87, 0.08)"], edits)

	def test_every_pale_name_of_a_ground_is_a_tint(self):
		for name in ("soft", "surface", "light", "muted", "alt", "bg", "subtle", "tint", "pale"):
			styles, _ = repaired(backgroundColor=f"var(--t-{name})")
			self.assertTrue(styles["backgroundColor"].startswith("rgba("), name)

	def test_a_deep_ground_is_the_primary(self):
		styles, _ = repaired(background="var(--t-dark)")
		self.assertEqual("var(--t-primary)", styles["background"])

	def test_an_ink_is_the_text_a_pale_ink_the_background_a_brand_ink_the_primary(self):
		self.assertEqual("var(--t-text)", repaired(color="var(--t-ink-soft)")[0]["color"])
		self.assertEqual("var(--t-background)", repaired(color="var(--t-on-dark)")[0]["color"])
		self.assertEqual("var(--t-primary)", repaired(color="var(--t-brand)")[0]["color"])
		self.assertEqual("var(--t-accent)", repaired(borderColor="var(--t-highlight)")[0]["borderColor"])

	def test_a_token_the_site_defines_is_left_alone(self):
		styles, edits = repaired(backgroundColor="var(--t-accent)", color="var(--t-text)")
		self.assertEqual({"backgroundColor": "var(--t-accent)", "color": "var(--t-text)"}, styles)
		self.assertEqual([], edits)

	def test_a_variable_with_its_own_fallback_is_left_alone(self):
		styles, edits = repaired(backgroundColor="var(--t-tint, #eef)")
		self.assertEqual("var(--t-tint, #eef)", styles["backgroundColor"])
		self.assertEqual([], edits)

	def test_a_variable_of_someone_else_is_left_alone(self):
		styles, edits = repaired(backgroundColor="var(--theme-surface)")
		self.assertEqual("var(--theme-surface)", styles["backgroundColor"])
		self.assertEqual([], edits)

	def test_a_declaration_that_is_not_a_colour_is_left_alone(self):
		styles, edits = repaired(boxShadow="0 0 8px var(--t-glow)", padding="var(--t-gap) 0")
		self.assertEqual({"boxShadow": "0 0 8px var(--t-glow)", "padding": "var(--t-gap) 0"}, styles)
		self.assertEqual([], edits)

	def test_every_breakpoint_and_every_depth_is_read(self):
		inner = {"element": "div", "baseStyles": {}, "mobileStyles": {"backgroundColor": "var(--t-wash)"}, "children": []}
		outer = {"element": "section", "baseStyles": {}, "children": [inner]}
		edits = repair_undefined_tokens([outer], TOKENS, "t")
		self.assertTrue(inner["mobileStyles"]["backgroundColor"].startswith("rgba("))
		self.assertEqual(1, len(edits))

	def test_a_value_with_several_variables_swaps_only_the_undefined_one(self):
		styles, _ = repaired(backgroundImage="linear-gradient(var(--t-primary), var(--t-tint))")
		self.assertEqual("linear-gradient(var(--t-primary), var(--t-tint))", styles["backgroundImage"], "not a ground key: left as written")
		styles, _ = repaired(background="linear-gradient(var(--t-primary), var(--t-tint))")
		self.assertEqual("linear-gradient(var(--t-primary), rgba(37, 51, 87, 0.08))", styles["background"])

	def test_without_a_prefix_or_tokens_nothing_happens(self):
		blocks = [block(backgroundColor="var(--t-tint)")]
		self.assertEqual([], repair_undefined_tokens(blocks, {}, "t"))
		self.assertEqual([], repair_undefined_tokens(blocks, TOKENS, ""))
		self.assertEqual("var(--t-tint)", blocks[0]["baseStyles"]["backgroundColor"])

	def test_no_primary_means_a_neutral_tint(self):
		blocks = [block(backgroundColor="var(--t-tint)")]
		repair_undefined_tokens(blocks, {"t-background": "#fff"}, "t")
		self.assertEqual("rgba(0, 0, 0, 0.04)", blocks[0]["baseStyles"]["backgroundColor"])


if __name__ == "__main__":
	unittest.main()
