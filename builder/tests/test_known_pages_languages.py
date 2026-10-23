# //// Neoffice — added file (no upstream equivalent): the page titles of a German or an Italian site are known.
"""A German site's "Startseite" was no home page (2026-10-23: typed "generic", routed "startseite", given no hero, and the root of the
site served the instance's own default page); its "Leistungen", "Über uns" and "Projekte" were no services, about or portfolio pages. The
titles of the generator's four languages are known, with the same routes and types as the French ones. No model is called."""

import unittest

from builder.site_ai.nora import site_builder
from builder.site_ai.nora.site_builder import KNOWN_PAGES, _bare, normalise_pages


def typed(*titles):
	return {p["title"]: (p["route"], p["type"]) for p in normalise_pages([{"title": t} for t in titles], "vitrine")}


class TestTheTitlesOfAGermanSite(unittest.TestCase):
	def test_the_pages_of_a_german_site_are_the_pages_they_say(self):
		got = typed("Startseite", "Leistungen", "Projekte", "Über uns", "Kontakt", "Preise", "Kundenstimmen", "Häufige Fragen", "Unser Team")
		self.assertEqual(("home", "accueil"), got["Startseite"])
		self.assertEqual(("services", "services"), got["Leistungen"])
		self.assertEqual(("projects", "portfolio"), got["Projekte"])
		self.assertEqual(("about", "about"), got["Über uns"])
		self.assertEqual(("contact", "contact"), got["Kontakt"])
		self.assertEqual(("pricing", "pricing"), got["Preise"])
		self.assertEqual(("testimonials", "testimonials"), got["Kundenstimmen"])
		self.assertEqual(("faq", "faq"), got["Häufige Fragen"])
		self.assertEqual(("team", "team"), got["Unser Team"])

	def test_the_home_page_comes_first_whatever_the_order_it_was_given(self):
		pages = normalise_pages([{"title": "Leistungen"}, {"title": "Startseite"}], "vitrine")
		self.assertEqual("home", pages[0]["route"])

	def test_the_german_legal_titles_are_legal_pages(self):
		got = typed("Datenschutzerklärung", "Allgemeine Geschäftsbedingungen", "Impressum", "Datenschutz", "AGB")
		self.assertEqual(("privacy-policy", "legal"), got["Datenschutzerklärung"])
		self.assertEqual(("terms-conditions", "legal"), got["Allgemeine Geschäftsbedingungen"])
		self.assertEqual(("legal-notice", "legal"), got["Impressum"])


class TestTheTitlesOfAnItalianSite(unittest.TestCase):
	def test_the_pages_of_an_italian_site_are_the_pages_they_say(self):
		got = typed("Pagina iniziale", "Chi siamo", "Servizi", "Progetti", "Contatti", "Prezzi", "Domande frequenti", "Informativa sulla privacy", "Note legali")
		self.assertEqual(("home", "accueil"), got["Pagina iniziale"])
		self.assertEqual(("about", "about"), got["Chi siamo"])
		self.assertEqual(("services", "services"), got["Servizi"])
		self.assertEqual(("projects", "portfolio"), got["Progetti"])
		self.assertEqual(("contact", "contact"), got["Contatti"])
		self.assertEqual(("pricing", "pricing"), got["Prezzi"])
		self.assertEqual(("faq", "faq"), got["Domande frequenti"])
		self.assertEqual(("privacy-policy", "legal"), got["Informativa sulla privacy"])
		self.assertEqual(("legal-notice", "legal"), got["Note legali"])


class TestTheTableIsConsistent(unittest.TestCase):
	def test_a_title_is_listed_once_and_in_its_bare_form(self):
		seen = {}
		for page, titles in site_builder._OTHER_LANGUAGE_PAGES.items():
			for title in titles:
				self.assertEqual(_bare(title), title, title)
				self.assertNotIn(title, seen, f"{title} is listed under {seen.get(title)} and {page}")
				seen[title] = page

	def test_the_french_and_english_titles_keep_their_pages(self):
		self.assertEqual(("home", "accueil"), KNOWN_PAGES["accueil"])
		self.assertEqual(("services", "services"), KNOWN_PAGES["prestations"])
		self.assertEqual(("pricing", "pricing"), KNOWN_PAGES["tarifs"])
		self.assertEqual(("about", "about"), KNOWN_PAGES["about"])
		self.assertEqual(("privacy-policy", "legal"), KNOWN_PAGES["datenschutz"])
		self.assertEqual(("legal-notice", "legal"), KNOWN_PAGES["impressum"])
		self.assertEqual(("terms-conditions", "legal"), KNOWN_PAGES["agb"])

	def test_every_title_resolves_to_the_pair_it_was_listed_under(self):
		for page, titles in site_builder._OTHER_LANGUAGE_PAGES.items():
			for title in titles:
				self.assertEqual(page, KNOWN_PAGES[title], title)

	def test_the_contact_forms_still_come_with_the_contact_pages_of_every_language(self):
		for title in ("Kontakt", "Contatti", "Contact", "Contattaci"):
			self.assertEqual("contact", typed(title)[title][1], title)


if __name__ == "__main__":
	unittest.main()
