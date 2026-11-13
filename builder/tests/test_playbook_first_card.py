# //// Neoffice — added file (no upstream equivalent): the first card of the site playbook (neoffice-maintenance#2614).
"""The first card of the site playbook asks the site type FIRST and is written in the person's language.

A person who started the wizard from the Website space saw the card open with « One page, or several pages with a menu? » and
its first question was « Name »: the opening sentence belonged to the fourth question. And the model took the language of the
playbook's English examples and wrote a French person's card in English.
"""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

import frappe

from builder.site_ai.nora import prompts


class TestTheFirstCard(unittest.TestCase):
	def first_card(self):
		text = prompts.site_playbook(None)
		return text.split("1. The business.")[1].split("2. The pages.")[0]

	def test_the_site_type_is_the_first_group_so_the_opening_sentence_is_the_first_question(self):
		card = self.first_card()
		for later in ("label:'Name'", "label:'Activity'", "label:'What makes you different'"):
			self.assertLess(card.index("label:'Site type'"), card.index(later), later)

	def test_the_card_still_names_the_six_site_types_the_pipeline_knows(self):
		card = self.first_card()
		for label in ("Showcase", "Showcase with customer accounts", "Online shop", "Blog", "Portfolio", "One page"):
			self.assertIn("label:'" + label + "'", card)
		for site_type in ("vitrine", "vitrine_user", "ecommerce", "blog", "portfolio", "one_page"):
			self.assertIn(site_type, card)

	def test_the_options_say_whether_the_site_has_several_pages_and_a_menu_or_one_page(self):
		card = self.first_card()
		self.assertIn("several pages with a menu", card)
		self.assertIn("a single long page, no menu", card)

	def test_the_card_is_asked_in_the_persons_language(self):
		self.assertIn("in the user's language", self.first_card())


class TestPicturesSentInAMessage(unittest.TestCase):
	"""« My images » hands the assistant the addresses of the pictures the person chose. Without a rule, the model took them for
	a request to put the picture on the page and applied thirty-seven changes to a blank draft (13.11, on osiris)."""

	def test_they_are_kept_for_the_site_and_never_put_on_the_page(self):
		text = prompts.site_playbook(None)
		self.assertIn("are THEIR OWN pictures", text)
		self.assertIn("do NOT edit or read any block", text)
		self.assertIn("keep their addresses for generate_site", text)
		self.assertIn("logo_image for a logo, photos for the others", text)

	def test_they_answer_the_card_that_asks_for_them(self):
		"""After « My images » the assistant presented the logo and photographs card again instead of going on (13.11)."""
		text = prompts.site_playbook(None)
		self.assertIn("They ANSWER step 4 (the logo and photographs card)", text)
		self.assertIn("never present that card again after them", text)


class TestThePersonsLanguage(unittest.TestCase):
	def say(self, user_language, system_language=None, builder_language=None, language_name="français"):
		def get_value(doctype, name, field=None, *args, **kwargs):
			return user_language if doctype == "User" else language_name

		def get_single_value(doctype, field):
			return system_language if doctype == "System Settings" else builder_language

		# frappe.session is a proxy of the request's session: the local object holds it, and it is put back as it was (a
		# patch that deletes it leaves every later test of the process without a session)
		previous = getattr(frappe.local, "session", None)
		frappe.local.session = frappe._dict(user="someone@example.test")
		try:
			with (
				mock.patch.object(frappe.db, "get_value", side_effect=get_value),
				mock.patch.object(frappe.db, "get_single_value", side_effect=get_single_value),
			):
				return prompts.person_language_line()
		finally:
			frappe.local.session = previous

	def test_the_language_of_the_account_is_said_by_name_and_code(self):
		line = self.say("fr")
		self.assertIn("français (fr)", line)
		self.assertIn("every question, option, description and button", line)

	def test_the_system_language_stands_in_when_the_account_has_none(self):
		self.assertIn("(de)", self.say(None, system_language="de", language_name="Deutsch"))

	def test_the_builders_default_language_is_the_last_resort(self):
		self.assertIn("(it)", self.say(None, builder_language="it", language_name="italiano"))

	def test_no_language_at_all_says_nothing(self):
		self.assertEqual(self.say(None), "")

	def test_the_playbook_carries_it(self):
		with mock.patch.object(prompts, "person_language_line", return_value="The person you talk to uses français (fr)."):
			self.assertIn("The person you talk to uses français (fr).", prompts.site_playbook(None))


class TestChoicesWrittenAsTextOverOneButton(unittest.TestCase):
	"""The style step came as five bullets (palette, colours, layout, ground) over a lone « Continue »: nothing to choose
	(13.11, osiris). present_ui bounces such a card so the model puts the groups in `ui`."""

	STYLE = "Quelques choix sur le style :\n- Palette, 3 options\n- Couleur principale\n- Fond clair ou sombre"
	ONE = [{"kind": "actions", "buttons": [{"label": "Continuer"}]}]

	def test_a_listed_card_over_one_button_is_bounced(self):
		from builder.ai.agent.tools.conversation import listed_choices_over_one_button, run_present_ui

		self.assertTrue(listed_choices_over_one_button(self.STYLE, self.ONE))
		answer = run_present_ui(SimpleNamespace(), {"text": self.STYLE, "ui": self.ONE})
		self.assertTrue(str(answer).startswith("FAILED: the card lists its choices in its text"))

	def test_a_confirmation_a_recap_or_a_real_card_is_not(self):
		from builder.ai.agent.tools.conversation import listed_choices_over_one_button

		two = [{"kind": "actions", "buttons": [{"label": "Construire le site"}, {"label": "Changer quelque chose"}]}]
		self.assertFalse(listed_choices_over_one_button(self.STYLE, two), "a recap has two buttons")
		self.assertFalse(listed_choices_over_one_button("On construit ?", self.ONE), "a plain question over one button")
		self.assertFalse(
			listed_choices_over_one_button(self.STYLE, [{"kind": "choices", "options": [{"label": "Clair"}]}, *self.ONE]),
			"a card with a group to answer",
		)


class TestASiteWaitsForItsRecap(unittest.TestCase):
	"""The model built a whole site straight from the style answer, skipping the photographs step and the recap (13.11,
	osiris): generate_site refuses a whole site until the conversation presented the recap card."""

	def rows(self, *cards):
		return [SimpleNamespace(metadata_json=json.dumps({"ui": ui})) for ui in cards]

	def test_no_recap_no_whole_site(self):
		from builder.site_ai.nora import tools

		style = [{"kind": "actions", "buttons": [{"label": "Continuer"}]}]
		with mock.patch.object(tools.frappe, "get_all", return_value=self.rows(style)):
			self.assertFalse(tools.recap_was_presented("s1"))
			answer = tools.run_generate_site(SimpleNamespace(session_id="s1"), {"site_name": "X", "activity": "Y", "pages": []})
		self.assertEqual(answer, tools.RECAP_FIRST)

	def test_a_recap_a_part_of_a_site_or_no_conversation_goes_on(self):
		from builder.site_ai.nora import tools

		recap = [{"kind": "list", "items": ["Nom : X"]}, {"kind": "actions", "buttons": [{"label": "Construire le site"}, {"label": "Changer quelque chose"}]}]
		with mock.patch.object(tools.frappe, "get_all", return_value=self.rows(recap)):
			self.assertTrue(tools.recap_was_presented("s1"))
		self.assertTrue(tools.recap_was_presented(None), "a build run from the console has no conversation")
		with mock.patch.object(tools, "recap_was_presented", return_value=False), mock.patch(
			"builder.site_ai.nora.site_builder.build_site", return_value="DONE"
		):
			self.assertEqual(tools.run_generate_site(SimpleNamespace(session_id="s1"), {"scope": "pages"}), "DONE")


class TestWhatThePersonGaveReachesTheBuild(unittest.TestCase):
	"""The model built a site without the logo, the photographs, the site liked and the language the person gave on the cards,
	though its recap said « your logo and photos included » (13.11, osiris)."""

	ANSWER = (
		"Continue\nLogo: /files/logo-lumiere.png\nVos photos (soins, institut, vous): /files/a.png, /files/b.png\n"
		"Le site que vous aimez (lien): https://www.example.ch/fr/\nLangue du site: Français"
	)

	def test_the_answers_are_read(self):
		from builder.site_ai.nora import tools

		with mock.patch.object(tools.frappe, "get_all", return_value=[SimpleNamespace(content=self.ANSWER)]):
			found = tools.answers_of_the_conversation("s1")
		self.assertEqual(found["logo_image"], "/files/logo-lumiere.png")
		self.assertEqual(found["photos"], ["/files/a.png", "/files/b.png"])
		self.assertEqual(found["inspiration_urls"], ["https://www.example.ch/fr/"])
		self.assertEqual(found["language"], "fr")
		self.assertEqual(tools.answers_of_the_conversation(None), {})

	def test_they_fill_only_what_the_model_left_out(self):
		from builder.site_ai.nora import tools

		with mock.patch.object(tools.frappe, "get_all", return_value=[SimpleNamespace(content=self.ANSWER)]):
			args = tools.with_the_persons_answers("s1", {"site_name": "X", "logo_image": "/files/model.png", "photos": []})
		self.assertEqual(args["logo_image"], "/files/model.png", "what the model passed stays")
		self.assertEqual(args["photos"], ["/files/a.png", "/files/b.png"], "an empty list is filled")
		self.assertEqual(args["site_name"], "X")

	def test_the_playbooks_buttons_in_the_persons_language(self):
		from builder.site_ai.nora.cards import BUILD_BUTTON, buttons_in_the_persons_language

		ui = [{"kind": "actions", "buttons": [{"label": "Build the site"}, {"label": "Change something"}, {"label": "Voir"}]}]
		labels = [b["label"] for b in buttons_in_the_persons_language(ui, "fr")[0]["buttons"]]
		self.assertEqual(labels, ["Construire le site", "Changer quelque chose", "Voir"])
		self.assertTrue(BUILD_BUTTON.search(labels[0]), "still a recap")
		same = [{"kind": "actions", "buttons": [{"label": "Build the site"}]}]
		self.assertEqual(buttons_in_the_persons_language(same, "en")[0]["buttons"][0]["label"], "Build the site")
