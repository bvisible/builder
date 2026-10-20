# //// Neoffice — added file (no upstream equivalent): the writer is told how much copy a page carries.
"""With the density "standard" nothing told the page writer how much to write: the strong model wrote 220 to 280
words on an interior page, the local one 50 to 210 (a heading over one short line), and the reviewer called the
page thin (2026-10-20). A floor is said in the page brief; a minimal-copy site and a legal page do not get it.
No model is called."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.site_ai.nora import visual_check
from builder.site_ai.nora.site_builder import (
	COPY_FLOOR_WORDS,
	copy_length_line,
	page_brief_text,
	script_word_count,
	thin_copy_issue,
)

HANDLES = {
	"primary": "var(--t-primary)",
	"secondary": "var(--t-secondary)",
	"background": "var(--t-background)",
	"text": "var(--t-text)",
	"font-heading": "var(--t-font-heading)",
	"font-body": "var(--t-font-body)",
}


def brief_for(page, density="standard"):
	site = {
		"site_name": "Atelier Test",
		"activity": "a workshop",
		"site_type": "vitrine",
		"profile": None,
		"page_types": ["accueil", page["type"]],
		"copy_density": density,
	}
	with patch("builder.site_ai.nora.site_builder.available_includes", return_value=[]):
		return page_brief_text(
			site,
			SimpleNamespace(),
			page,
			HANDLES,
			"",
			"classic-centered",
			"French",
			[],
			("Contact", "/contact"),
		)


class TestTheCopyLength(unittest.TestCase):
	def test_the_floor_depends_on_the_page(self):
		self.assertEqual(COPY_FLOOR_WORDS, {"home": 200, "interior": 150, "contact": 90})
		self.assertIn("at least 200 words", copy_length_line({"type": "accueil"}, True, "standard"))
		self.assertIn("at least 150 words", copy_length_line({"type": "about"}, False, "standard"))
		self.assertIn("at least 90 words", copy_length_line({"type": "contact"}, False, "standard"))

	def test_a_minimal_site_and_a_text_page_are_not_told(self):
		self.assertEqual(copy_length_line({"type": "about"}, False, "minimal"), "")
		for kind in ("legal", "faq", "blog"):
			self.assertEqual(copy_length_line({"type": kind}, False, "standard"), "")

	def test_an_unset_density_counts_as_standard(self):
		self.assertIn("COPY LENGTH", copy_length_line({"type": "about"}, False, None))

	def test_the_page_brief_carries_the_rule_after_the_sections(self):
		text = brief_for({"title": "À propos", "route": "about", "type": "about"})
		self.assertIn("COPY LENGTH: every section carries its copy in full", text)
		self.assertLess(text.index("SECTIONS, in order"), text.index("COPY LENGTH"))
		self.assertIn("at least 150 words in all", text)

	def test_the_page_brief_of_a_minimal_site_or_a_legal_page_does_not(self):
		self.assertNotIn(
			"COPY LENGTH", brief_for({"title": "À propos", "route": "about", "type": "about"}, "minimal")
		)
		self.assertNotIn("COPY LENGTH", brief_for({"title": "Mentions", "route": "legal", "type": "legal"}))


def blocks_of(words):
	"""A page whose sections carry `words` words in all, in paragraphs of ten."""
	paragraphs = [{"element": "p", "innerHTML": " ".join(["mot"] * 10)} for _ in range(words // 10)]
	return [{"element": "div", "children": [{"element": "section", "children": paragraphs}]}]


class TestThinCopyIsMeasured(unittest.TestCase):
	"""The strong hosted judge called the local writer's short pages "sparse" and they were rewritten longer; a judge
	under the instructions made for the local model does not, so the floor of the brief is checked on the words."""

	def test_a_page_below_the_floor_is_a_medium_point_with_its_numbers(self):
		point = thin_copy_issue(blocks_of(100), {"type": "accueil"}, True, "standard")
		self.assertEqual(point["severity"], "medium")
		self.assertIn("100 words", point["problem"])
		self.assertIn("at least 200", point["problem"])

	def test_a_page_under_half_the_floor_is_a_high_point_and_is_not_accepted_after_one_pass(self):
		point = thin_copy_issue(blocks_of(40), {"type": "about"}, False, "standard")
		self.assertEqual(point["severity"], "high")
		report = {"professional": True, "issues": [point], "gate": [], "error": None}
		self.assertFalse(visual_check.accepted(report, lenient=True))
		# exactly half is still only a short page
		self.assertEqual(thin_copy_issue(blocks_of(100), {"type": "accueil"}, True, "standard")["severity"], "medium")
		self.assertEqual(thin_copy_issue(blocks_of(90), {"type": "accueil"}, True, "standard")["severity"], "high")

	def test_a_page_at_or_above_the_floor_is_not(self):
		self.assertIsNone(thin_copy_issue(blocks_of(200), {"type": "accueil"}, True, "standard"))
		self.assertIsNone(thin_copy_issue(blocks_of(150), {"type": "about"}, False, None))
		self.assertIsNone(thin_copy_issue(blocks_of(90), {"type": "contact"}, False, "standard"))

	def test_the_floor_depends_on_the_page_as_the_brief_says(self):
		self.assertIsNotNone(thin_copy_issue(blocks_of(140), {"type": "about"}, False, "standard"))
		self.assertIsNone(thin_copy_issue(blocks_of(140), {"type": "contact"}, False, "standard"))

	def test_a_minimal_site_and_a_text_page_are_never_measured(self):
		self.assertIsNone(thin_copy_issue(blocks_of(10), {"type": "about"}, False, "minimal"))
		for kind in ("legal", "faq", "blog"):
			self.assertIsNone(thin_copy_issue(blocks_of(10), {"type": kind}, False, "standard"))

	def test_the_sentences_of_a_repeater_count_like_the_blocks(self):
		# as the build stores it: a JSON array with the accents escaped (\u00e0)
		items = [
			{"icon": "file-text", "title": "Menus sur mesure", "body": "Des menus adaptables à vos besoins, construits autour des produits de la vallée et des saisons."},
			{"icon": "users", "title": "Salle pour groupes", "body": "Un espace convivial pour vos rassemblements."},
		]
		script = "data.services = " + json.dumps(items)
		self.assertIn("\\u00e0", script)
		# keys, icon names and the one-word values are not words a visitor reads
		self.assertEqual(script_word_count(script), 3 + 15 + 3 + 6)
		self.assertEqual(script_word_count(""), 0)
		self.assertEqual(script_word_count('data.flag = {"on": true, "icon": "star"}'), 0)
		# 90 words in the blocks and 30 in the data of a home: 120, still below 200, but not "90"
		point = thin_copy_issue(blocks_of(90), {"type": "accueil"}, True, "standard", script='data.a = [{"body": "' + " ".join(["mot"] * 30) + '"}]')
		self.assertIn("120 words", point["problem"])
		self.assertIsNone(thin_copy_issue(blocks_of(150), {"type": "about"}, False, "standard", script=""))
		self.assertIsNone(thin_copy_issue(blocks_of(100), {"type": "about"}, False, "standard", script='data.a = [{"body": "' + " ".join(["mot"] * 60) + '"}]'))

	def test_it_asks_for_one_revision_and_no_more(self):
		# the point sits among the judge's, with a page the judge liked: revised once, then accepted
		point = thin_copy_issue(blocks_of(100), {"type": "accueil"}, True, "standard")
		report = {"professional": True, "issues": [point], "gate": [], "error": None}
		self.assertFalse(visual_check.accepted(report, lenient=False))
		self.assertTrue(visual_check.accepted(report, lenient=True))
		self.assertFalse(visual_check.refused(report))


if __name__ == "__main__":
	unittest.main()
