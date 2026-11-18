# //// Neoffice — added file (no upstream equivalent): what a site build takes from the conversation, and what it says back (2026-11-18).
"""A client's site was built in English, without the ten pictures the person had sent, and the assistant then said the pictures were
in the site. What is held here:

* the editor's « my images » button writes its label, then one address a line: every file reaches the build as a photograph, and
  the logo is the one the vision recognises among them, never the first file by its rank;
* a whole site in a language that is not the person's own is asked first, once;
* the build's summary always says what became of the client's photographs, and which pages the look could not see."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.site_ai.nora import site_builder, tools

FILES = ["/files/logo.png", "/files/site-1.webp", "/files/site-2.webp", "/files/inside.webp"]


def answers(*messages):
	with patch.object(tools.frappe, "get_all", return_value=[frappe._dict(content=m) for m in messages]):
		return tools.answers_of_the_conversation("a-session")


class TestTheImagesButton(unittest.TestCase):
	def test_every_file_of_the_button_is_a_photograph(self):
		found = answers("\n".join(["Here are my images (logo, photos):", *FILES]))
		self.assertEqual(found.get("photos"), FILES)
		self.assertNotIn("logo_image", found)

	def test_the_button_is_known_in_the_persons_language(self):
		french = "Voici mes images (logo, photos) :"
		with patch.object(
			tools.frappe, "_", side_effect=lambda text, lang=None: french if lang == "fr" else text
		):
			found = answers("\n".join([french, *FILES]))
		self.assertEqual(found.get("photos"), FILES)
		self.assertNotIn("logo_image", found)

	def test_two_sendings_add_up(self):
		found = answers(
			"\n".join(["Here are my images (logo, photos):", *FILES[:2]]),
			"\n".join(["Here are my images (logo, photos):", *FILES[2:]]),
		)
		self.assertEqual(found.get("photos"), FILES)

	def test_the_cards_answers_still_read_as_before(self):
		found = answers("Logo: /files/mark.png\nYour own photos for the site: /files/a.webp, /files/b.webp")
		self.assertEqual(found.get("logo_image"), "/files/mark.png")
		self.assertEqual(found.get("photos"), ["/files/a.webp", "/files/b.webp"])

	def test_addresses_written_under_a_card_label_count(self):
		found = answers("Your own photos for the site:\n/files/a.webp\n/files/b.webp")
		self.assertEqual(found.get("photos"), ["/files/a.webp", "/files/b.webp"])


class TestTheLogoTheVisionRecognised(unittest.TestCase):
	def rows(self):
		return [
			frappe._dict(
				file="/files/logo.png",
				suggested_slots="logo",
				original_filename="logo.png",
				summary="",
				tags="",
				orientation="square",
				quality="high",
				extracted_text="",
				suggested_section="generic",
				understanding="{}",
			),
			frappe._dict(
				file="/files/site-1.webp",
				suggested_slots="hero",
				original_filename="site-1.webp",
				summary="A site.",
				tags="",
				orientation="landscape",
				quality="high",
				extracted_text="",
				suggested_section="hero",
				understanding="{}",
			),
		]

	def test_the_logo_is_kept_off_the_pages(self):
		with (
			patch.object(site_builder.frappe.db, "exists", return_value=True),
			patch.object(site_builder.frappe, "get_all", return_value=self.rows()),
		):
			self.assertEqual(
				[p["url"] for p in site_builder.library_photos("a-session")], ["/files/site-1.webp"]
			)

	def test_the_logo_is_found_among_the_pictures(self):
		with (
			patch.object(site_builder.frappe.db, "exists", return_value=True),
			patch.object(site_builder.frappe, "get_all", return_value=self.rows()),
		):
			self.assertEqual(site_builder.library_logo("a-session", only=FILES), "/files/logo.png")
			self.assertIsNone(site_builder.library_logo("a-session", only=["/files/site-1.webp"]))


class TestTheLanguageOfTheSite(unittest.TestCase):
	def test_a_language_is_read_from_a_code_or_a_name(self):
		for value, code in (
			("en", "en"),
			("fr-CH", "fr"),
			("English", "en"),
			("français", "fr"),
			("Deutsch", "de"),
			("italiano", "it"),
			("", ""),
			("es", ""),
			# the names the model writes in the person's language (18.11)
			("anglais", "en"),
			("allemand", "de"),
			("inglese", "en"),
			("tedesco", "de"),
			("Englisch", "en"),
		):
			with self.subTest(value=value):
				self.assertEqual(tools.language_code(value), code)

	def test_the_build_reads_the_language_by_its_name_too(self):
		# read by its first two letters, « anglais » gave « an » and the site fell back to French (18.11)
		with patch.object(site_builder.frappe.db, "get_single_value", return_value="fr"):
			for value, code in (("anglais", "en"), ("allemand", "de"), ("English", "en"), ("it", "it"), ("", "fr"), ("es", "fr")):
				with self.subTest(value=value):
					self.assertEqual(site_builder.site_language({"language": value}), code)
		with patch.object(site_builder.frappe.db, "get_single_value", return_value="de"):
			self.assertEqual(site_builder.site_language({}), "de")

	def test_the_answer_after_a_build_is_in_the_persons_language(self):
		# a site written in English, and Nora asked a French person in English what to do with a refused page (18.11)
		with patch.object(tools, "persons_language", return_value="fr"):
			line = site_builder.answer_language_line("en")
			self.assertIn("English", line)
			self.assertIn("French", line)
			self.assertEqual(site_builder.answer_language_line("fr"), "")
		with patch.object(tools, "persons_language", return_value=""):
			self.assertEqual(site_builder.answer_language_line("en"), "")

	def ask(self, args, person="fr", named=None):
		with (
			patch.object(tools, "persons_language", return_value=person),
			patch.object(
				tools, "answers_of_the_conversation", return_value={"language": named} if named else {}
			),
		):
			return tools.language_to_ask("a-session", args)

	def test_a_site_in_another_language_than_the_persons_is_asked_first(self):
		question = self.ask({"language": "en"})
		self.assertTrue(
			question and question.startswith("FAILED") and "English" in question and "French" in question
		)

	def test_nothing_is_asked_when_the_language_is_theirs_or_chosen(self):
		self.assertIsNone(self.ask({"language": "fr"}))
		self.assertIsNone(self.ask({"language": "en", "language_confirmed": True}))
		self.assertIsNone(self.ask({"language": "en"}, named="English"))
		self.assertIsNone(self.ask({"language": "en", "scope": "pages"}))

	def test_the_build_waits_for_the_answer(self):
		ctx = SimpleNamespace(session_id=None, page_id=None)
		args = {
			"site_name": "Test",
			"activity": "an electrician",
			"pages": ["Accueil"],
			"language": "en",
			"example_site": "none",
		}
		with (
			patch.object(tools, "persons_language", return_value="fr"),
			patch("builder.site_ai.nora.site_builder.build_site", return_value="DONE") as build,
		):
			self.assertTrue(tools.run_generate_site(ctx, args).startswith("FAILED"))
			build.assert_not_called()
			self.assertEqual(tools.run_generate_site(ctx, {**args, "language_confirmed": True}), "DONE")
			self.assertEqual(build.call_args.args[1]["language"], "en")


class FakeCache(dict):
	def set_value(self, key, value, expires_in_sec=None):
		self[key] = value

	def get_value(self, key):
		return self.get(key)

	def delete_value(self, key):
		self.pop(key, None)


FIRST_CALL = {
	"site_name": "Lakeside Bakery",
	"activity": "an artisan bakery by the lake",
	"pages": [{"title": "Home"}, {"title": "About"}],
	"language": "en",
	"language_confirmed": True,
	"example_site": "restaurant",
	"example_use": "as_is",
	"website_profile": "ZZ Test Site",
	"instance_business": False,
}
CALL_AFTER_THE_TAP = {
	"site_name": "Lakeside Bakery",
	"activity": "an artisan bakery by the lake",
	"pages": [{"title": "Home"}, {"title": "About"}],
}


class TestTheCallTheRecapWasMadeFrom(unittest.TestCase):
	"""18.11, osiris: the call turned back for the recap carried the language, the example and the site; the call after the person's
	tap carried only the name, the activity and the pages, and the site came out in French, without its example."""

	def run_calls(self, *calls):
		recap = iter([False] + [True] * len(calls))
		ctx = SimpleNamespace(session_id="a-session", page_id=None)
		with (
			patch.object(tools.frappe, "cache", FakeCache()),
			patch.object(tools, "recap_was_presented", side_effect=lambda session: next(recap)),
			patch.object(tools, "answers_of_the_conversation", return_value={}),
			patch.object(tools, "persons_language", return_value="fr"),
			patch.object(tools, "business_from_answers", return_value=None),
			patch("builder.site_ai.nora.examples.first_site", return_value=False),
			patch("builder.site_ai.nora.prompts.page_profile", return_value=None),
			patch("builder.site_ai.logging.ai_log"),
			patch("builder.site_ai.nora.site_builder.build_site", return_value="DONE") as build,
		):
			answers = [tools.run_generate_site(ctx, dict(args)) for args in calls]
		return answers, build

	def test_the_call_after_the_tap_goes_back_with_what_it_left_out(self):
		answers, build = self.run_calls(FIRST_CALL, CALL_AFTER_THE_TAP, FIRST_CALL)
		self.assertEqual(answers[0], tools.RECAP_FIRST)
		self.assertTrue(answers[1].startswith("FAILED"))
		for said in ("language='en'", "example_site='restaurant'", "example_use='as_is'", "website_profile='ZZ Test Site'"):
			self.assertIn(said, answers[1])
		# the person's answer « another business » is an answer, carried like the others
		self.assertIn("instance_business=False", answers[1])
		self.assertEqual(answers[2], "DONE")
		build.assert_called_once()
		self.assertEqual(build.call_args.args[1]["language"], "en")
		self.assertEqual(build.call_args.args[1]["example_use"], "as_is")

	def test_it_goes_back_once_then_builds_what_the_model_says(self):
		answers, build = self.run_calls(FIRST_CALL, CALL_AFTER_THE_TAP, CALL_AFTER_THE_TAP)
		self.assertTrue(answers[1].startswith("FAILED"))
		self.assertEqual(answers[2], "DONE")
		self.assertNotIn("language", build.call_args.args[1])

	def test_a_call_that_carries_the_recap_builds_at_once(self):
		answers, _build = self.run_calls(FIRST_CALL, FIRST_CALL)
		self.assertEqual(answers[1], "DONE")

	def test_a_page_added_to_a_site_is_never_compared(self):
		answers, _build = self.run_calls(FIRST_CALL, {**CALL_AFTER_THE_TAP, "scope": "pages"})
		self.assertEqual(answers[1], "DONE")


class TestWhatTheSummarySays(unittest.TestCase):
	def test_a_build_without_the_clients_photographs_says_so(self):
		line = site_builder.photo_report_line([], {}, 0, building_part=False)
		self.assertIn("No photograph of the client reached this build", line)

	def test_the_photographs_used_are_counted(self):
		line = site_builder.photo_report_line(
			[{"url": "/files/a.webp"}, {"url": "/files/b.webp"}], {"/files/a.webp": 1}, 0, building_part=False
		)
		self.assertTrue(line.startswith("1 of the client's 2 photographs"))

	def test_a_page_added_to_a_site_says_nothing_of_photographs(self):
		self.assertEqual(site_builder.photo_report_line([], {}, 0, building_part=True), "")

	def test_the_pages_the_look_could_not_see_are_named(self):
		self.assertEqual(site_builder.unlooked_line([]), "")
		line = site_builder.unlooked_line(["Accueil", "Contact"])
		self.assertIn("2 page(s) could not be looked at", line)
		self.assertIn("Accueil, Contact", line)
