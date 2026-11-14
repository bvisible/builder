# //// Neoffice — added file (no upstream equivalent): a build said done when no tool ran goes
# //// back to the model (builder/site_ai/nora/claims.py, AgentRunner.send_back_unrun_claim), and a
# //// recap's bare bracketed buttons become a card (builder/site_ai/nora/cards.py).
import unittest
from unittest.mock import MagicMock, patch

from builder.site_ai.nora.cards import parse_card
from builder.site_ai.nora.claims import NUDGE, unrun_build_claim

ASKED = "Rebuild the whole site again with the same brief, the same 12 photos, the same four pages."
CLAIMED = "Atelier Nord is rebuilt and published on Nora Test 3. All four pages are live at /home, /brands."


class TestUnrunBuildClaim(unittest.TestCase):
	def test_a_build_asked_and_said_done(self):
		self.assertTrue(unrun_build_claim(ASKED, CLAIMED))
		self.assertTrue(
			unrun_build_claim("Reconstruis le site, s'il te plaît.", "Le site est reconstruit et publié.")
		)

	def test_a_build_said_launched_is_a_claim(self):
		self.assertTrue(unrun_build_claim("Relance la reconstruction complète du site.", "J'ai relancé la reconstruction complète du site avec le même brief. Le processus est en cours."))
		self.assertTrue(unrun_build_claim("Rebuild the site.", "I've launched the rebuild of the site; it is running now."))

	def test_a_question_about_an_earlier_build_is_not_a_request(self):
		self.assertFalse(
			unrun_build_claim("What did you do yesterday?", "The site was built with four pages.")
		)

	def test_a_recap_is_not_a_claim(self):
		self.assertFalse(
			unrun_build_claim(ASKED, "Here is the recap: four pages, English. Shall I build it?")
		)


class TestSendBack(unittest.TestCase):
	def setUp(self):
		from builder.ai.agent import loop

		# the log is the production log: a test writes nothing there
		logging = patch.object(loop, "logger")
		logging.start()
		self.addCleanup(logging.stop)

	def runner(self, **extra):
		runner = MagicMock(
			prompt=ASKED, applied_operations=[], live_text=CLAIMED, claim_sent_back=False, **extra
		)
		runner.tool_steps.return_value = []
		return runner

	def test_the_claim_goes_back_once(self):
		from builder.ai.agent import loop

		runner, messages = self.runner(), []
		self.assertTrue(loop.AgentRunner.send_back_unrun_claim(runner, messages, CLAIMED))
		self.assertEqual(
			messages, [{"role": "assistant", "content": CLAIMED}, {"role": "user", "content": NUDGE}]
		)
		# the false claim comes off the chat before the model answers again
		runner.emit.assert_called_once_with("stream", chunk="", replace=True)
		self.assertEqual(runner.live_text, "")
		self.assertFalse(loop.AgentRunner.send_back_unrun_claim(runner, messages, CLAIMED))

	def test_a_turn_that_ran_a_tool_is_not_questioned(self):
		from builder.ai.agent import loop

		runner = self.runner()
		runner.tool_steps.return_value = [{"kind": "tool", "tool": "generate_site"}]
		self.assertFalse(loop.AgentRunner.send_back_unrun_claim(runner, [], CLAIMED))


class TestBareButtons(unittest.TestCase):
	def test_a_recap_with_bracketed_buttons_is_a_card(self):
		recap = (
			"Atelier Nord\nSite profile: Nora Test 3\nPages: Home, Brands, About, Contact\nLanguage: English\n"
			"I'll replace every existing page and rebuild the site.\n[Build the site] [Change something]"
		)
		card = parse_card(recap)
		self.assertIsNotNone(card)
		self.assertIn("Site profile: Nora Test 3", card["text"])
		self.assertEqual(
			[b["label"] for b in card["ui"][-1]["buttons"]], ["Build the site", "Change something"]
		)

	def test_a_footnote_is_not_a_button(self):
		self.assertIsNone(parse_card("The brief says so in the second email [1]"))


class TestChoicesWrittenAsACall(unittest.TestCase):
	"""After a build, the question about three refused pages came as text, its choices written as the tool's arguments,
	and the card showed every piece between two commas as a choice: « en gardant vos tarifs) » (13.11, osiris)."""

	REFUSED = (
		"Trois pages n'ont pas passé mon contrôle qualité.\n"
		"[choices: Tarifs — que faire? options=[Reconstruire avec une autre direction (description: je réécris la page, "
		"en gardant vos tarifs), Publier telle quelle (description: elle reste avec les défauts), Je la finis moi-même "
		"(description: elle reste dans le brouillon, hors du menu)]]\n"
		"[choices: À propos — que faire? options=[Reconstruire (description: je réécris la page, en gardant votre histoire), "
		"Publier telle quelle]]\n"
		"[buttons: Continuer]"
	)

	def test_each_page_is_a_question_with_its_three_answers(self):
		card = parse_card(self.REFUSED)
		groups = [el for el in card["ui"] if el["kind"] == "choices"]
		self.assertEqual([g["label"] for g in groups], ["Tarifs — que faire?", "À propos — que faire?"])
		first = groups[0]["options"]
		self.assertEqual([o["label"] for o in first], ["Reconstruire avec une autre direction", "Publier telle quelle", "Je la finis moi-même"])
		self.assertEqual(first[0]["description"], "je réécris la page, en gardant vos tarifs")
		self.assertEqual(first[2]["description"], "elle reste dans le brouillon, hors du menu")
		self.assertEqual([o["label"] for o in groups[1]["options"]], ["Reconstruire", "Publier telle quelle"])
		self.assertNotIn("description", groups[1]["options"][1])

	def test_bullets_above_the_buttons_are_the_choices(self):
		"""The next turn wrote its question as bullets over « [buttons: Continuer] »: present_ui bounced the card (one button
		under listed choices) and the raw text stayed on screen (13.11). The bullets become the card's choices."""
		from builder.ai.agent.tools.conversation import listed_choices_over_one_button

		text = (
			"Tarifs n'a pas passé le contrôle qualité. Que faire ?\n"
			"* Reconstruire avec une autre direction — je réécris la page, en gardant vos tarifs\n"
			"* Publier telle quelle — elle reste avec les défauts\n"
			"* Je la finis moi-même — elle reste dans le brouillon, hors du menu\n"
			"[buttons: Continuer]"
		)
		card = parse_card(text)
		self.assertEqual(card["text"], "Tarifs n'a pas passé le contrôle qualité. Que faire ?")
		self.assertEqual(card["ui"][0]["kind"], "choices")
		self.assertEqual(card["ui"][0]["options"][1], {"label": "Publier telle quelle", "description": "elle reste avec les défauts"})
		self.assertFalse(listed_choices_over_one_button(card["text"], card["ui"]), "present_ui takes it")

	def test_the_broken_card_copied_back_is_joined_again(self):
		"""The model copied the broken card of its history, pieces and all: they are joined back into one question."""
		text = (
			"À propos est construite et publiée. Tarifs n'a pas passé le contrôle qualité. Que faire ?\n"
			"* Tarifs — que faire? options=[Reconstruire avec une autre direction (description: je réécris la page\n"
			"* en gardant vos tarifs)\n"
			"* Publier telle quelle (description: elle reste avec les défauts)\n"
			"* Je la finis moi-même (description: elle reste dans le brouillon\n"
			"* hors du menu)]\n"
			"[buttons: Continuer]"
		)
		card = parse_card(text)
		self.assertTrue(card["text"].endswith("Que faire ?"))
		group = card["ui"][0]
		self.assertEqual(group["label"], "Tarifs — que faire?")
		self.assertEqual([o["label"] for o in group["options"]], ["Reconstruire avec une autre direction", "Publier telle quelle", "Je la finis moi-même"])
		self.assertEqual(group["options"][0]["description"], "je réécris la page, en gardant vos tarifs")

	def test_a_question_of_two_answers_over_the_buttons_is_a_card(self):
		"""Whose business the site is, asked as text with its two answers as bullets over « [buttons: Continuer] »: two
		bullets were not enough for a choice, present_ui bounced the card and the raw text stayed on screen (14.11)."""
		from builder.ai.agent.tools.conversation import listed_choices_over_one_button

		text = (
			"Une dernière chose avant de lancer la construction : ce site est-il pour Dupont & Fils SA elle-même, ou pour une "
			"autre entreprise ?\n"
			"* Ce site est à Dupont & Fils SA — ses coordonnées, son équipe et sa boutique y apparaissent\n"
			"* C'est le site d'une autre entreprise — aucun de ces éléments n'y figure\n"
			"[buttons: Continuer]"
		)
		card = parse_card(text)
		self.assertTrue(card["text"].endswith("ou pour une autre entreprise ?"))
		group = card["ui"][0]
		self.assertEqual(group["kind"], "choices")
		self.assertEqual([o["label"] for o in group["options"]], ["Ce site est à Dupont & Fils SA", "C'est le site d'une autre entreprise"])
		self.assertFalse(listed_choices_over_one_button(card["text"], card["ui"]), "present_ui takes it")
		# two bullets with no question above them stay a report
		card = parse_card("J'ai fait deux choses.\n- Accueil réécrite\n- Menu mis à jour\n[buttons: Continuer]")
		self.assertNotIn("choices", [el["kind"] for el in card["ui"]])

	def test_a_question_of_two_answers_with_no_button_is_a_card(self):
		"""The same question written with the company's name and no button line: two bullets closing the message stayed raw
		text, the safety net asking three where no button is written (14.11)."""
		text = (
			"Le site est-il celui de Dupont & Fils SA ou d'une de ses marques, ou celui d'une autre entreprise ?\n"
			"* Oui, Dupont & Fils SA\n"
			"* Non, une autre entreprise"
		)
		card = parse_card(text)
		self.assertEqual(card["text"], "Le site est-il celui de Dupont & Fils SA ou d'une de ses marques, ou celui d'une autre entreprise ?")
		self.assertEqual(card["ui"], [{"kind": "choices", "options": [{"label": "Oui, Dupont & Fils SA"}, {"label": "Non, une autre entreprise"}]}])
		# two lines that do not sit right under the question, or with no question at all, stay what they are
		self.assertIsNone(parse_card("Vous voulez la suite ?\nVoici ce que j'ai fait :\n- Accueil réécrite\n- Menu mis à jour"))
		self.assertIsNone(parse_card("J'ai fait deux choses.\n- Accueil réécrite\n- Menu mis à jour"))

	def test_a_report_over_one_button_stays_a_report(self):
		card = parse_card("J'ai fait trois choses.\n- Accueil réécrite\n- Photos placées\n- Menu mis à jour\n[buttons: Continuer]")
		self.assertNotIn("choices", [el["kind"] for el in card["ui"]])

	def test_a_comma_between_parentheses_never_splits_a_choice(self):
		card = parse_card("Quel ton ?\n[choices: Chaleureux (proche, simple), Sobre]\n[buttons: Continuer]")
		self.assertEqual([o["label"] for o in card["ui"][0]["options"]], ["Chaleureux (proche, simple)", "Sobre"])
		card = parse_card("[choices: A, B, C]\n[buttons: OK]")
		self.assertEqual([o["label"] for o in card["ui"][0]["options"]], ["A", "B", "C"])


class TestCardEcho(unittest.TestCase):
	"""The question written as the message, then again as the card's text: shown twice."""

	FIRST = (
		"Deux pages existantes ont été retouchées à la main : Accueil et À propos. Je dois les "
		"remplacer aussi pour construire le site complet. Tu confirmes ?"
	)
	CARD = (
		"Deux pages existantes ont été retouchées à la main : Accueil et À propos. Pour construire "
		"le site complet, je dois les remplacer. Tu confirmes ?"
	)

	def test_the_same_question_in_other_words(self):
		from builder.site_ai.nora.cards import says_the_same

		self.assertTrue(says_the_same(self.FIRST, self.CARD))
		self.assertFalse(says_the_same("Which pages do you want?", "Pages"))
		self.assertFalse(says_the_same("I read the three sites you like.", self.CARD))

	def test_the_echo_leaves_the_timeline(self):
		from builder.ai.agent.tools.conversation import _without_echo

		tool = {"id": 0, "kind": "tool", "tool": "generate_site"}
		echo = {"id": 1, "kind": "text", "text": self.FIRST}
		self.assertEqual(_without_echo([tool, echo], self.CARD), [tool])
		# a narration before a later tool call is another moment of the turn
		self.assertEqual(_without_echo([echo, tool], self.CARD), [echo, tool])
		other = {"id": 1, "kind": "text", "text": "I read the three sites you like."}
		self.assertEqual(_without_echo([tool, other], self.CARD), [tool, other])


class TestRecapNamesTheSite(unittest.TestCase):
	"""A whole recap listed a new site's name, pages and colours, not the site it was built on."""

	def recap(self):
		return [
			{"kind": "heading", "text": "Récap du site"},
			{"kind": "list", "items": ["Cabinet : Atelier Nord", "Pages : Accueil, Contact"]},
			{"kind": "actions", "buttons": [{"label": "Build the site"}, {"label": "Change something"}]},
		]

	def test_the_site_is_named_before_the_build(self):
		from builder.site_ai.nora.cards import recap_names_the_site

		ui = recap_names_the_site(self.recap(), "Voici le récapitulatif.", "Nora Test")
		self.assertEqual(ui[1]["items"][-1], "Site : Nora Test")
		bare = recap_names_the_site([{"kind": "actions", "buttons": [{"label": "Construire le site"}]}], "", "Nora Test")
		self.assertEqual(bare[0], {"kind": "list", "items": ["Site: Nora Test"]})

	def test_a_card_that_names_it_or_asks_something_else_stays(self):
		from builder.site_ai.nora.cards import recap_names_the_site

		named = self.recap()
		named[1]["items"].append("Site : Nora Test")
		self.assertEqual(recap_names_the_site([dict(el) for el in named], "", "Nora Test"), named)
		question = [{"kind": "choices", "options": [{"label": "Oui"}]}, {"kind": "actions", "buttons": [{"label": "Continuer"}]}]
		self.assertEqual(recap_names_the_site(list(question), "", "Nora Test"), question)
		self.assertEqual(recap_names_the_site(self.recap(), "", None), self.recap())


# //// Neoffice ▼▼▼ — added tests (2026-09-16): a question announced is not a question asked.
class TestAnnouncedQuestionNotAsked(unittest.TestCase):
	"""Twice in one session the model answered "Avant de reconstruire le site, je te pose les
	questions essentielles." and ended the turn calling nothing: no card, nothing to tap, the
	build stalled until a human nudged it."""

	def announced(self, text):
		from builder.site_ai.nora.claims import announced_question_not_asked

		return announced_question_not_asked(text)

	def test_the_sentence_that_stalled_two_builds_is_caught(self):
		self.assertTrue(self.announced("D'accord. Avant de reconstruire tout le site, je te pose les questions essentielles."))

	def test_the_other_ways_of_announcing_are_caught(self):
		for text in (
			"Je vais te poser quelques questions avant de commencer.",
			"Voici les questions pour cadrer le site :",
			"Voici la carte pour l'étape 3.",
			"Before we start, here are the questions I need answered.",
			"I'll ask you a few questions first.",
		):
			self.assertTrue(self.announced(text), text)

	def test_an_answer_that_asks_nothing_is_left_alone(self):
		for text in (
			"Le site est reconstruit : cinq pages, menu à jour.",
			"J'ai corrigé le hero et publié la page.",
			"Quelle palette préfères-tu ?",
			"",
		):
			self.assertFalse(self.announced(text), text)

	def test_the_nudge_names_the_tool_the_model_must_call(self):
		from builder.site_ai.nora.claims import NUDGE_QUESTION

		self.assertIn("present_ui", NUDGE_QUESTION)
		self.assertIn("same turn", NUDGE_QUESTION)

	def test_the_loop_sends_it_back_once_and_only_when_nothing_ran(self):
		"""Same contract as the unrun build claim: once per turn, and never when a tool ran."""
		from builder.ai.agent.loop import AgentRunner

		self.assertTrue(hasattr(AgentRunner, "send_back_unasked_question"))
		import inspect

		src = inspect.getsource(AgentRunner.send_back_unasked_question)
		self.assertIn("question_sent_back", src)
		self.assertIn("self.tool_steps()", src)
		self.assertIn("self.applied_operations", src)


# //// Neoffice — added (2026-09-17): a tool call written as text is sent back.
class TestAToolCallWrittenAsText(unittest.TestCase):
	def test_the_arguments_of_generate_site_as_a_json_block_are_not_a_call(self):
		from builder.site_ai.nora.claims import tool_call_written_as_text

		text = '{\n"site_name": "Atelier Nord",\n"activity": "a workshop",\n"pages": [{"title": "Home", "route": "home"}],\n"website_profile": "Nora Test",\n"replace_existing": "force",\n"scope": "site"\n}'
		self.assertTrue(tool_call_written_as_text(text))

	def test_a_sentence_naming_the_site_is_not(self):
		from builder.site_ai.nora.claims import tool_call_written_as_text

		self.assertFalse(tool_call_written_as_text("The site name is Atelier Nord and it has four pages."))
		self.assertFalse(tool_call_written_as_text(""))

