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

