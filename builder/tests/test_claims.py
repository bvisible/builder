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
