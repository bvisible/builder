# //// Neoffice — added file (no upstream equivalent): the writer is told how much copy a page carries.
"""With the density "standard" nothing told the page writer how much to write: the strong model wrote 220 to 280
words on an interior page, the local one 50 to 210 (a heading over one short line), and the reviewer called the
page thin (2026-10-20). A floor is said in the page brief; a minimal-copy site and a legal page do not get it.
No model is called."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.site_ai.nora.site_builder import COPY_FLOOR_WORDS, copy_length_line, page_brief_text

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


if __name__ == "__main__":
	unittest.main()
