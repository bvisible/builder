# //// Neoffice — added file (no upstream equivalent): the cookie notice and the Google map agree on the visitor's answer.
"""On a site that holds a Google map the cookie notice asks (Accept / Refuse) and the map follows: it is drawn at once for a visitor who
accepted, stays behind its button for anyone else, and the visitor can take the agreement back under the map (2026-10-26). The two
templates and the generator's captures share one key of the browser's localStorage; what is pinned here is that they cannot drift
apart, and that the privacy policy says what the site does. The behaviour in a browser is exercised by a real run on osiris. No
browser is started here."""

import re
import unittest
from pathlib import Path

from builder.site_ai.inspiration import screenshotter
from builder.site_ai.nora import legal

TEMPLATES = Path(screenshotter.__file__).parents[2] / "templates" / "includes"
NOTICE = (TEMPLATES / "data_notice.html").read_text()
MAP = (TEMPLATES / "google_map.html").read_text()


def key_of(source: str) -> str:
	return re.search(r'var KEY = "([^"]+)"', source).group(1)


class TestTheNoticeAndTheMapShareTheAnswer(unittest.TestCase):
	def test_one_key_for_the_notice_the_map_and_the_captures(self):
		self.assertEqual(key_of(NOTICE), key_of(MAP))
		self.assertIn(f"'{key_of(NOTICE)}'", screenshotter.NOTICE_ANSWERED_SCRIPT)

	def test_the_map_opens_only_for_the_value_the_notice_writes_on_accept(self):
		written = re.findall(r'data-notice-choice="([a-z]+)"', NOTICE)
		self.assertIn("accepted", written)
		self.assertIn("declined", written)
		self.assertIn('=== "accepted"', MAP)
		self.assertNotIn('=== "1"', MAP, "a visitor who only closed the older notice never agreed to the map")

	def test_a_capture_never_loads_google(self):
		"""The loopback captures close the notice with a refusal: the map stays behind its button and nothing is sent to Google."""
		self.assertIn("'declined'", screenshotter.NOTICE_ANSWERED_SCRIPT)

	def test_accepting_in_the_notice_draws_the_map_of_the_page_being_read(self):
		self.assertIn('new CustomEvent("neo-maps-agreed")', NOTICE)
		self.assertIn('addEventListener("neo-maps-agreed"', MAP)

	def test_the_notice_asks_only_on_a_site_that_holds_a_map(self):
		"""A site without a map keeps the single OK that only tells; the answer it stores is the old one."""
		self.assertIn("neo_legal.maps", NOTICE)
		self.assertIn('data-notice-choice="seen"', NOTICE)
		self.assertIn('choice === "seen" ? "1" : choice', NOTICE)

	def test_an_older_ok_does_not_count_as_an_agreement_on_a_site_that_asks(self):
		line = next(l for l in NOTICE.splitlines() if l.strip().startswith("var decided"))
		self.assertIn('stored === "accepted"', line)
		self.assertIn('stored === "declined"', line)
		self.assertIn("!asks", line)

	def test_the_agreement_can_be_taken_back_under_the_map(self):
		self.assertIn("data-revoke", MAP)
		self.assertIn('setItem(KEY, "declined")', MAP)
		self.assertIn("builder-map-revoke__button", MAP)

	def test_a_visitor_who_clicks_the_button_does_not_agree_for_the_other_pages(self):
		"""The click loads this map once; the revoke link is only drawn for an agreement given in the notice (`automatic`)."""
		self.assertIn("open(show.closest(\".builder-map-gate\"), false)", MAP)
		self.assertIn("if (automatic && label", MAP)


class TestThePolicyDescribesTheAgreement(unittest.TestCase):
	def test_every_language_says_the_map_needs_the_agreement_and_can_be_withdrawn(self):
		for lang in legal.LANGUAGES:
			text = legal.TEXT[lang]["p_map"]
			self.assertIn("Google", text, lang)
			self.assertNotIn("Tant que vous ne cliquez pas", text, lang)
		self.assertIn("accord", legal.TEXT["fr"]["p_map"])
		self.assertIn("retirer votre accord", legal.TEXT["fr"]["p_map"])
		self.assertIn("withdraw your agreement", legal.TEXT["en"]["p_map"])
		self.assertIn("Zustimmung", legal.TEXT["de"]["p_map"])
		self.assertIn("ritirare il consenso", legal.TEXT["it"]["p_map"])

	def test_the_withdrawal_link_is_named_as_the_page_names_it(self):
		self.assertIn("Ne plus afficher la carte automatiquement", legal.TEXT["fr"]["p_map"])
		self.assertIn("Stop showing the map automatically", legal.TEXT["en"]["p_map"])
		self.assertIn("Stop showing the map automatically", MAP)


if __name__ == "__main__":
	unittest.main()
