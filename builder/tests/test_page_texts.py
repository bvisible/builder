# //// Neoffice — added file (no upstream equivalent): the texts of the pages a site rebuild replaces (#2624).
"""A site rebuilt over pages that already had their words keeps them when the person says so (neoffice-maintenance#2624).

Before, « Créer mon site avec Nora » replaced the pages without reading them: a client's prices, years, people and testimonials
were gone, and the facts pass would have removed them anyway as facts the brief did not give.
"""

import json
import unittest

from builder.site_ai.nora import page_texts
from builder.site_ai.nora.facts import known_text
from builder.site_ai.nora.site_builder import client_words_line

ABOUT = json.dumps(
	[
		{
			"element": "div",
			"children": [
				{"element": "h2", "innerHTML": "Notre histoire"},
				{"element": "p", "innerHTML": "Depuis 1998, Marie Dupont accueille vos chiens au&nbsp;salon."},
				{"element": "p", "innerHTML": "<strong>Toilettage complet</strong> : CHF 85.–"},
				{"element": "div", "innerHTML": '{% include "builder/templates/includes/contact_form.html" %}'},
				{"element": "p", "innerHTML": "Depuis 1998, Marie Dupont accueille vos chiens au&nbsp;salon."},
			],
		}
	]
)


class TestTheWordsOfAPage(unittest.TestCase):
	def test_a_page_gives_its_words_one_per_line_without_tags_includes_or_repeats(self):
		text = page_texts.text_of_blocks(ABOUT)
		self.assertEqual(
			text.split("\n"),
			["Notre histoire", "Depuis 1998, Marie Dupont accueille vos chiens au salon.", "Toilettage complet : CHF 85.–"],
		)

	def test_a_blank_or_broken_page_has_no_words(self):
		self.assertEqual(page_texts.text_of_blocks(""), "")
		self.assertEqual(page_texts.text_of_blocks("not json"), "")
		self.assertEqual(page_texts.text_of_blocks(json.dumps([{"element": "body", "children": []}])), "")

	def test_a_long_page_is_cut(self):
		long = json.dumps([{"element": "p", "innerHTML": "mot " * 3000}])
		self.assertLessEqual(len(page_texts.text_of_blocks(long)), page_texts.MAX_PAGE_CHARS)


class TestTheNewPageFindsTheOldOne(unittest.TestCase):
	OLD = [
		{"route": "accueil", "title": "Accueil", "text": "home words"},
		{"route": "a-propos", "title": "À propos", "text": "about words"},
		{"route": "nos-services", "title": "Services", "text": "services words"},
	]

	def test_by_route_by_title_and_the_home_under_any_of_its_names(self):
		self.assertEqual(page_texts.words_for({"route": "home", "title": "Home"}, self.OLD), "home words")
		self.assertEqual(page_texts.words_for({"route": "a-propos", "title": "About"}, self.OLD), "about words")
		self.assertEqual(page_texts.words_for({"route": "services", "title": "Services"}, self.OLD), "services words")
		self.assertEqual(page_texts.words_for({"route": "contact", "title": "Contact"}, self.OLD), "")

	def test_keys_ignore_accents_case_and_marks(self):
		self.assertEqual(page_texts.page_key("À Propos"), "a-propos")
		self.assertEqual(page_texts.page_key("/"), "home")
		self.assertEqual(page_texts.page_key("Accueil"), "home")


class TestTheWriterIsGivenThemAndTheFactsPassKeepsThem(unittest.TestCase):
	def test_the_page_brief_carries_the_old_page_words(self):
		site = {"client_texts": [{"route": "a-propos", "title": "À propos", "text": "Depuis 1998, CHF 85.–"}]}
		line = client_words_line(site, {"route": "a-propos", "title": "À propos"})
		self.assertIn("THE CLIENT'S OWN WORDS for this page", line)
		self.assertIn("Depuis 1998, CHF 85.–", line)
		self.assertIn("drop none", line)
		self.assertEqual(client_words_line(site, {"route": "contact", "title": "Contact"}), "")
		self.assertEqual(client_words_line({}, {"route": "a-propos", "title": "À propos"}), "")

	def test_their_facts_are_known_text(self):
		site = {"site_name": "Salon", "activity": "Toilettage", "client_words": "Depuis 1998, Marie Dupont, CHF 85.–"}
		self.assertIn("Marie Dupont", known_text(site))
		self.assertIn("CHF 85", known_text(site))
