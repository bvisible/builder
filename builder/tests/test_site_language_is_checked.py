# //// Neoffice — added file (no upstream equivalent): the language of a built site is read by the judge, and what is left in another
# //// language is said in the summary (2026-11-18).
"""A site rebuilt in French kept English words that a reused part had brought (a form of a former build, a section), nobody looked at
the language, and Nora told the person all was in French. The judge of every page is now told the site's language: a text in
another language is a high point (the page is revised), marked by the judge itself (`language`), and the summary says the pages
where some is left. The code passes the language and reads the judge's mark; it decides nothing about words."""

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.site_ai.nora import site_builder, visual_check
from builder.site_ai.schemas.page_critique import PageCritique


class TestTheJudgeKnowsTheLanguage(unittest.TestCase):
	def setUp(self):
		logging = patch.object(visual_check, "ai_log")
		logging.start()
		self.addCleanup(logging.stop)

	def context_for(self, **kwargs):
		seen = {}

		def critique(url, model=None, context="", extra_images=None, style="default"):
			seen["context"] = context
			return SimpleNamespace(looks_professional=True, overall="fine", issues=[]), "judge"

		with (
			patch.object(
				visual_check, "_screenshot", return_value={"success": True, "file_url": "/files/x.png"}
			),
			patch.object(visual_check, "measure_page", return_value={"status": 200, "widths": {}}),
			patch.object(visual_check, "capture_phone", return_value=None),
			patch.object(visual_check, "_drop_capture"),
			patch("builder.site_ai.ingestion.visual_critique.critique_screenshot", side_effect=critique),
			patch.object(visual_check.frappe.db, "commit"),
			patch.object(visual_check, "_readable_data_url", return_value=None),
		):
			visual_check.review_page(
				{"name": "p1", "title": "Accueil", "route": "/home"}, "A Site", "judge", **kwargs
			)
		return seen.get("context", "")

	def test_the_site_language_is_said_to_the_judge(self):
		context = self.context_for(site_name="A Shop", activity="a shop", language="French")
		self.assertIn("The site is written in French", context)
		self.assertIn("set `language` to true", context)

	def test_without_a_language_nothing_is_added(self):
		self.assertNotIn("The site is written in", self.context_for(site_name="A Shop", activity="a shop"))

	def test_every_review_of_a_build_passes_the_language(self):
		source = inspect.getsource(site_builder.build_site)
		calls = source.count("visual_check.review_page(")
		self.assertGreater(calls, 0)
		self.assertEqual(source.count("activity=activity, language=language"), calls)


class TestALanguagePoint(unittest.TestCase):
	def critique(self, **issue):
		return PageCritique.model_validate(
			{
				"overall": "",
				"looks_professional": True,
				"issues": [{"area": "hero", "severity": "high", **issue}],
			}
		)

	def test_the_judge_marks_it_and_the_mark_is_kept(self):
		critique = self.critique(
			problem='"Get a quote" is English', fix="« Demander un devis »", language=True
		)
		self.assertTrue(critique.issues[0].language)
		self.assertTrue(visual_check.actionable(critique)[0]["language"])

	def test_an_ordinary_point_is_not_a_language_point(self):
		self.assertFalse(
			visual_check.actionable(self.critique(problem="the title overlaps the photo"))[0]["language"]
		)

	def test_a_high_language_point_sends_the_page_back(self):
		report = {
			"professional": True,
			"gate": [],
			"issues": visual_check.actionable(self.critique(problem="English", language=True)),
		}
		self.assertFalse(visual_check.accepted(report))


class TestTheSummarySaysWhatIsLeft(unittest.TestCase):
	def test_the_pages_with_another_language_are_named(self):
		reviews = [
			{"title": "Accueil", "issues": [{"problem": '"Our services" is English', "language": True}]},
			{"title": "Contact", "issues": [{"problem": "the map is small", "language": False}]},
		]
		line = site_builder.foreign_language_line(reviews, "French")
		self.assertIn("Accueil", line)
		self.assertIn("Our services", line)
		self.assertNotIn("Contact", line)
		self.assertIn("never that the whole site is in French", line)

	def test_nothing_left_says_nothing(self):
		self.assertEqual(
			site_builder.foreign_language_line([{"title": "Accueil", "issues": []}], "French"), ""
		)
