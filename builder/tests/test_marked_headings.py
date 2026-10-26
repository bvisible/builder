# //// Neoffice — added file (no upstream equivalent): a heading that holds inline markup is a line of text, never a flex container.
"""On the About page of a regenerated site two headings carried `display: flex; align-items: center; gap: 0.6rem` (the writer laid them
out around a small square) and held an accent word in `<em>`: every run of text of a flex container is a flex item of its own, so the
accent word stood apart from the heading, at the right of the line. layout.settle_marked_headings takes the flex off such a heading, and
the square, an inline-block that carries its own margin, stays where the line puts it. No model is called."""

import unittest

from builder.site_ai.nora.layout import settle_marked_headings
from builder.tests.test_recipes import walk

SQUARE = '<span style="display:inline-block;width:10px;height:10px;background:var(--t-primary);margin-right:0.6rem"></span>'
ACCENT = '<em style="font-style: italic; color: var(--t-primary)">histoire</em>'
FLEX_KEYS = ("display", "alignItems", "gap", "justifyContent", "flexDirection")


def page(yaml_heading: str) -> list:
	"""A heading as the writer's own YAML expands it, inside a root like the writer's."""
	from builder.ai.page_writer import expand_page_yaml

	body = "\n".join("    " + line for line in yaml_heading.splitlines())
	blocks, _script = expand_page_yaml(
		"el: div\nname: body\nstyle: {display: flex, flexDirection: column}\nc:\n" + body
	)
	return blocks


def headings(blocks):
	return [
		b for b in walk(blocks) if str(b.get("element") or "").lower() in ("h1", "h2", "h3", "h4", "h5", "h6")
	]


def flex_left(block):
	return {
		k
		for key in ("baseStyles", "tabletStyles", "mobileStyles")
		for k in (block.get(key) or {})
		if k in FLEX_KEYS
	}


class TestHeadingsWithMarkup(unittest.TestCase):
	def test_the_flex_the_writer_laid_around_a_square_is_taken_off(self):
		blocks = page(
			"- el: h2\n"
			"  style: {display: flex, alignItems: center, gap: 0.6rem, fontSize: 3rem, color: var(--t-text)}\n"
			f"  text: '{SQUARE}Notre {ACCENT}'\n"
		)
		(heading,) = headings(blocks)
		self.assertEqual(heading["baseStyles"]["display"], "flex", "the page as the writer gave it")
		self.assertEqual(settle_marked_headings(blocks), 1)
		self.assertEqual(flex_left(heading), set())
		self.assertEqual(heading["baseStyles"]["fontSize"], "3rem")
		self.assertEqual(heading["baseStyles"]["color"], "var(--t-text)")
		self.assertIn("inline-block", heading["innerHTML"], "the square keeps its own place in the line")
		self.assertIn("<em", heading["innerHTML"])

	def test_every_size_of_screen_is_released(self):
		blocks = page(
			"- el: h2\n"
			"  style: {display: flex, alignItems: center, gap: 0.6rem}\n"
			"  m_style: {display: flex, flexDirection: column, alignItems: flex-start, gap: 0.3rem, fontSize: 1.75rem}\n"
			f"  text: 'Notre {ACCENT}'\n"
		)
		self.assertEqual(settle_marked_headings(blocks), 1)
		(heading,) = headings(blocks)
		self.assertEqual(flex_left(heading), set())
		self.assertEqual(heading["mobileStyles"]["fontSize"], "1.75rem")

	def test_a_phone_style_that_only_turns_the_direction_is_released_too(self):
		blocks = page(
			f"- el: h2\n  style: {{display: flex, alignItems: center, gap: 0.6rem}}\n  m_style: {{flexDirection: column, alignItems: flex-start}}\n  text: 'Notre {ACCENT}'\n"
		)
		settle_marked_headings(blocks)
		(heading,) = headings(blocks)
		self.assertEqual(flex_left(heading), set())

	def test_a_centred_flex_heading_stays_centred(self):
		blocks = page(
			f"- el: h2\n  style: {{display: flex, justifyContent: center, alignItems: center, gap: 0.5rem}}\n  text: 'Notre {ACCENT}'\n"
		)
		settle_marked_headings(blocks)
		(heading,) = headings(blocks)
		self.assertEqual(heading["baseStyles"].get("textAlign"), "center")
		self.assertNotIn("justifyContent", heading["baseStyles"])

	def test_a_heading_with_its_own_text_alignment_keeps_it(self):
		blocks = page(
			f"- el: h2\n  style: {{display: flex, justifyContent: center, textAlign: left}}\n  text: 'Notre {ACCENT}'\n"
		)
		settle_marked_headings(blocks)
		(heading,) = headings(blocks)
		self.assertEqual(heading["baseStyles"]["textAlign"], "left")

	def test_a_heading_of_plain_text_is_left_as_it_is(self):
		"""One run of text in a flex container is one item: nothing flies off, and the writer may have centred it that way."""
		blocks = page(
			"- el: h2\n  style: {display: flex, alignItems: center, gap: 0.6rem}\n  text: 'Notre histoire'\n"
		)
		self.assertEqual(settle_marked_headings(blocks), 0)
		(heading,) = headings(blocks)
		self.assertEqual(heading["baseStyles"]["display"], "flex")

	def test_a_heading_with_markup_and_no_flex_is_left_alone(self):
		blocks = page(f"- el: h3\n  style: {{fontSize: 2rem, margin: 0}}\n  text: 'Notre {ACCENT}'\n")
		before = repr(blocks)
		self.assertEqual(settle_marked_headings(blocks), 0)
		self.assertEqual(repr(blocks), before)

	def test_a_flex_row_that_is_not_a_heading_is_left_alone(self):
		"""A button row, a label with its icon: flex is what they are for."""
		blocks = page(
			f"- el: div\n  style: {{display: flex, alignItems: center, gap: 0.6rem}}\n  text: '{SQUARE}Notre {ACCENT}'\n"
		)
		self.assertEqual(settle_marked_headings(blocks), 0)

	def test_each_level_of_heading_is_read(self):
		for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
			with self.subTest(level=level):
				blocks = page(
					f"- el: {level}\n  style: {{display: flex, alignItems: center, gap: 0.6rem}}\n  text: 'Notre {ACCENT}'\n"
				)
				self.assertEqual(settle_marked_headings(blocks), 1)

	def test_a_heading_with_a_line_break_is_a_line_of_text_too(self):
		blocks = page(
			"- el: h2\n  style: {display: flex, flexDirection: column}\n  text: 'Première ligne<br>seconde ligne'\n"
		)
		self.assertEqual(settle_marked_headings(blocks), 1)
		(heading,) = headings(blocks)
		self.assertEqual(flex_left(heading), set())


if __name__ == "__main__":
	unittest.main()
