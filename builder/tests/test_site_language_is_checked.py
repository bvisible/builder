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

	def test_nothing_left_is_said_with_what_was_read(self):
		line = site_builder.foreign_language_line([{"title": "Accueil", "issues": []}], "French")
		self.assertIn("read 1 page(s) and found no text in another language than French", line)

	def test_nothing_read_says_nothing(self):
		self.assertEqual(
			site_builder.foreign_language_line([{"title": "Accueil", "error": "no screenshot"}], "French"), ""
		)
		self.assertEqual(site_builder.foreign_language_line([], "French"), "")


class TestWhatIsReusedFollowsTheLanguage(unittest.TestCase):
	"""The parts a build reuses or writes without the model: they follow the site's language too."""

	def test_the_site_language_is_set_before_the_first_page_is_written(self):
		source = inspect.getsource(site_builder.build_site)
		early = source.index("Site language set before the pages are written")
		self.assertLess(early, source.index("_write_page("))
		self.assertIn(
			"if not building_part and profile and remember_site_language(profile, lang_code)", source
		)

	def test_a_plan_is_reused_only_in_its_own_language(self):
		self.assertIn(
			'plan_key = f"nora_site_plan::{profile or site_name}::{lang_code}"',
			inspect.getsource(site_builder.build_site),
		)

	def test_a_page_says_its_site_language(self):
		with (
			patch.object(site_builder.frappe.db, "has_column", return_value=True),
			patch.object(site_builder.frappe.db, "get_value", return_value="en"),
		):
			self.assertEqual(site_builder.page_language("A Site"), "en")
		self.assertIsNone(site_builder.page_language(None))
		self.assertIn("doc.language = language", inspect.getsource(site_builder._write_page))

	def test_the_picture_still_to_make_is_described_in_the_site_language(self):
		from builder.site_ai.nora import examples

		self.assertEqual(examples.premises_alt("Contact", "French"), "Contact, les locaux de l’entreprise")
		self.assertEqual(
			examples.premises_alt("Kontakt", "German"), "Kontakt, die Räumlichkeiten des Unternehmens"
		)
		self.assertNotIn("the premises of the business", inspect.getsource(examples.rewrite))

	def test_a_connected_form_speaks_the_page_language(self):
		from builder import site_forms

		script = site_forms.guarded_form_script(".form", "Booking", ["name", "email"], "Nora")
		self.assertIn("document.documentElement.lang", script)
		self.assertIn("Envoi en cours…", script)
		self.assertIn("SAY.sending", script)
		self.assertNotIn("'Sending…'", script)

	def test_the_scripts_already_wired_are_rewritten_once(self):
		from builder import site_forms
		from builder.builder.patches import connected_forms_speak_the_page_language as patch_module

		old = site_forms.guarded_form_script(".form", "Booking", ["name"], "Nora").replace(
			"SAY.sending", "'Sending…'"
		)
		doc = SimpleNamespace(script=old, save=lambda **kwargs: None)
		with (
			patch.object(site_forms, "available", return_value=True),
			patch.object(patch_module.frappe.db, "table_exists", return_value=True),
			patch.object(patch_module.frappe, "get_all", return_value=["Save Booking submissions"]),
			patch.object(patch_module.frappe, "get_doc", return_value=doc),
		):
			patch_module.execute()
			self.assertIn("SAY.sending", doc.script)
			again = doc.script
			patch_module.execute()  # a script already speaking the page's language is left alone
		self.assertEqual(doc.script, again)


class TestTheFormsNoPageShows(unittest.TestCase):
	def test_a_former_build_form_is_named_and_the_person_asked(self):
		from builder import site_forms

		module = SimpleNamespace(
			list_forms=lambda profile: [
				{"name": "quote-request", "title": "Quote request", "profile": "A Site", "enabled": 1},
				{"name": "demande-de-devis", "title": "Demande de devis", "profile": "A Site", "enabled": 1},
				{"name": "shared", "title": "Shared", "profile": None, "enabled": 1},
			]
		)
		pages = [
			SimpleNamespace(
				blocks='[{"innerHTML": "{%- set site_form = \\"demande-de-devis\\" -%}"}]', draft_blocks=""
			)
		]
		with (
			patch.object(site_forms, "available", return_value=True),
			patch.object(site_forms, "theme_module", return_value=module),
			patch.object(site_forms.frappe, "get_all", return_value=pages),
		):
			unused = site_forms.unused_forms("A Site")
			line = site_builder.unused_forms_line("A Site")
		self.assertEqual(unused, [{"name": "quote-request", "title": "Quote request"}])
		self.assertIn("« Quote request »", line)
		self.assertIn("delete nothing yourself", line)
