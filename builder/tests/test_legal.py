# //// Neoffice — added file (no upstream equivalent): the privacy policy and the legal notice of a generated site.
"""Every site the generator builds carries a privacy policy and a legal notice, written without a model (legal.py): a fixed document
in the four languages of the generator, filled with what the business gave and with what the pages of the site hold. What is pinned
here: the library is complete in every language, a document never describes a processing the site does not have and never leaves out
one it has, a missing contact line is a visible blank (never an invented one), and the page goes through the writer's own YAML. No
model is called."""

import datetime
import unittest
from unittest.mock import patch

from builder.ai.page_writer import expand_page_yaml
from builder.site_ai.nora import legal
from builder.site_ai.nora import recipes as R

HANDLES = {
	"primary": "var(--t-primary)",
	"secondary": "var(--t-secondary)",
	"background": "var(--t-background)",
	"text": "var(--t-text)",
	"font-heading": "var(--t-font-heading)",
	"font-body": "var(--t-font-body)",
}
PALETTE = {"t-primary": "#7a2e1d", "t-secondary": "#d9b26f", "t-background": "#faf5ee", "t-text": "#2b1810"}
TODAY = datetime.date(2026, 10, 22)

FULL = legal.Facts(
	name="Atelier Test Sàrl",
	address="Rue du Test 1, 1950 Sion",
	email="hello@atelier-test.example",
	phone="+41 00 000 00 00",
	website="https://atelier-test.example",
	form=True,
	map=True,
	newsletter=True,
	shop=True,
)
BARE = legal.Facts(name="Atelier Test Sàrl")


def headings(kind, facts, lang):
	sections = legal.privacy_sections(facts, lang, TODAY) if kind == "privacy" else legal.notice_sections(facts, lang, TODAY)
	return [h for h, _ in sections if h]


class TestTheLibraryIsCompleteInEveryLanguage(unittest.TestCase):
	def test_the_four_languages_have_the_same_keys(self):
		reference = set(legal.TEXT["fr"])
		for lang in legal.LANGUAGES:
			self.assertEqual(reference, set(legal.TEXT[lang]), lang)

	def test_every_paragraph_is_filled_for_a_full_business_and_for_a_bare_one(self):
		for lang in legal.LANGUAGES:
			for facts in (FULL, BARE):
				for key in (k for k in legal.TEXT[lang] if k != "blank"):
					value = legal.text(lang, key, facts, TODAY)
					self.assertNotIn("{", value, f"{lang}.{key}")
					self.assertNotIn("}", value, f"{lang}.{key}")

	def test_the_titles_and_the_months_exist_in_every_language(self):
		for lang in legal.LANGUAGES:
			self.assertTrue(legal.title("privacy", lang) and legal.title("notice", lang))
			self.assertEqual(12, len(legal.MONTHS[lang]))

	def test_an_unknown_language_is_french(self):
		self.assertEqual("Politique de confidentialité", legal.title("privacy", "nl"))
		self.assertEqual("fr", legal.language_of(None))

	def test_a_date_is_written_the_way_the_language_writes_it(self):
		self.assertEqual("22 octobre 2026", legal.date_text("fr", TODAY))
		self.assertEqual("1er novembre 2026", legal.date_text("fr", datetime.date(2026, 11, 1)))
		self.assertEqual("October 22, 2026", legal.date_text("en", TODAY))
		self.assertEqual("22. Oktober 2026", legal.date_text("de", TODAY))
		self.assertEqual("22 ottobre 2026", legal.date_text("it", TODAY))


class TestThePrivacyPolicyDescribesWhatTheSiteDoes(unittest.TestCase):
	def test_a_bare_site_has_the_core_of_the_law_and_nothing_else(self):
		for lang in legal.LANGUAGES:
			got = headings("privacy", BARE, lang)
			for key in ("p_controller_h", "p_visit_h", "p_cookies_h", "p_recip_h", "p_abroad_h", "p_rights_h", "p_sec_h", "p_chg_h"):
				self.assertIn(legal.TEXT[lang][key], got, f"{lang} {key}")
			for key in ("p_form_h", "p_news_h", "p_shop_h", "p_map_h"):
				self.assertNotIn(legal.TEXT[lang][key], got, f"{lang} {key}")

	def test_each_processing_the_site_has_is_described(self):
		for lang in legal.LANGUAGES:
			got = headings("privacy", FULL, lang)
			for key in ("p_form_h", "p_news_h", "p_shop_h", "p_map_h"):
				self.assertIn(legal.TEXT[lang][key], got, f"{lang} {key}")

	def test_google_is_named_only_when_the_site_has_a_map(self):
		for lang in legal.LANGUAGES:
			bare = legal.plain_text("privacy", BARE, lang, TODAY)
			full = legal.plain_text("privacy", FULL, lang, TODAY)
			self.assertNotIn("Google", bare, lang)
			self.assertIn("Google", full, lang)

	def test_a_site_that_sells_speaks_of_the_account_the_basket_and_the_orders(self):
		for lang in legal.LANGUAGES:
			shop = legal.plain_text("privacy", FULL, lang, TODAY)
			bare = legal.plain_text("privacy", BARE, lang, TODAY)
			self.assertIn(legal.text(lang, "p_cookies_shop", FULL, TODAY), shop, lang)
			self.assertNotIn(legal.text(lang, "p_cookies_shop", BARE, TODAY), bare, lang)
			self.assertIn(legal.TEXT[lang]["p_shop_h"], headings("privacy", FULL, lang))

	def test_a_profile_that_sells_is_a_shop_for_the_policy_whatever_its_site_type(self):
		"""A B2B or B2C profile has an account to request and a basket: the build gives it its terms, so its policy describes them too."""
		import inspect

		from builder.site_ai.nora import site_builder

		source = inspect.getsource(site_builder.build_site)
		self.assertIn('uses["shop"] = sells_to_visitors(profile, site_type)', source)

	def test_the_assistant_that_reads_messages_is_told_only_to_a_site_with_a_form(self):
		for lang in legal.LANGUAGES:
			self.assertNotIn(legal.text(lang, "p_form_ai", BARE, TODAY), legal.plain_text("privacy", BARE, lang, TODAY))
			self.assertIn(legal.text(lang, "p_form_ai", FULL, TODAY), legal.plain_text("privacy", FULL, lang, TODAY))

	def test_the_policy_names_who_is_responsible_and_how_to_write_to_them(self):
		for lang in legal.LANGUAGES:
			body = legal.plain_text("privacy", FULL, lang, TODAY)
			self.assertIn("Atelier Test Sàrl", body)
			self.assertIn("Rue du Test 1, 1950 Sion", body)
			self.assertIn("hello@atelier-test.example", body)

	def test_the_hosting_provider_and_the_federal_commissioner_are_named(self):
		for lang in legal.LANGUAGES:
			body = legal.plain_text("privacy", BARE, lang, TODAY)
			self.assertIn("Infomaniak", body)
			self.assertIn("edoeb.admin.ch", body)

	def test_the_policy_says_what_the_site_does_with_cookies_and_never_more(self):
		fr = legal.plain_text("privacy", BARE, "fr", TODAY)
		self.assertIn("cookies techniques", fr)
		self.assertNotIn("Google Analytics", fr)

	def test_the_policy_carries_the_date_of_its_last_update(self):
		self.assertIn("22 octobre 2026", legal.plain_text("privacy", BARE, "fr", TODAY))
		self.assertIn("October 22, 2026", legal.plain_text("privacy", BARE, "en", TODAY))


class TestAMissingContactLineIsABlankNeverAnInvention(unittest.TestCase):
	def test_no_email_and_no_phone_leaves_a_visible_blank(self):
		for lang in legal.LANGUAGES:
			body = legal.plain_text("privacy", BARE, lang, TODAY)
			self.assertTrue(legal.has_blank(body), lang)
			self.assertIn(legal.TEXT[lang]["what_contact"], body)

	def test_a_phone_alone_is_enough_for_the_contact(self):
		facts = legal.Facts(name="Atelier", phone="+41 00 000 00 00")
		self.assertFalse(legal.has_blank(legal.text("fr", "p_controller", facts, TODAY)))

	def test_the_notice_leaves_a_blank_for_the_company_number_it_was_not_given(self):
		for lang in legal.LANGUAGES:
			self.assertTrue(legal.has_blank(legal.plain_text("notice", FULL, lang, TODAY)), lang)

	def test_the_notice_lists_only_the_lines_the_business_gave(self):
		lines = legal.notice_sections(BARE, "fr", TODAY)[1][1][0]
		self.assertEqual("Atelier Test Sàrl", lines[0])
		self.assertEqual(2, len(lines))
		full = legal.notice_sections(FULL, "fr", TODAY)[1][1][0]
		self.assertEqual(6, len(full))

	def test_the_notice_points_to_the_privacy_policy(self):
		sections = legal.notice_sections(FULL, "fr", TODAY)
		links = [part for _, parts in sections for part in parts if isinstance(part, tuple)]
		self.assertEqual([("link", "/privacy-policy", legal.TEXT["fr"]["n_data_link"])], links)


class TestThePageIsAPageLikeThoseTheModelWrites(unittest.TestCase):
	def blocks(self, kind, facts=FULL, lang="fr"):
		yaml_text = legal.page_yaml(kind, facts, lang, HANDLES, PALETTE, TODAY)
		blocks, script = expand_page_yaml(yaml_text)
		return blocks, script, yaml_text

	def test_both_documents_expand_into_a_page(self):
		for kind in ("privacy", "notice"):
			for lang in legal.LANGUAGES:
				blocks, script, _ = self.blocks(kind, FULL, lang)
				self.assertEqual(1, len(blocks), f"{kind} {lang}")
				self.assertEqual("", script)

	def test_it_is_one_column_of_reading_in_one_section(self):
		blocks, _, _ = self.blocks("privacy")
		root = blocks[0]
		self.assertEqual(1, len(root["children"]))
		self.assertEqual("section", root["children"][0]["element"])

	def test_it_uses_the_handles_of_the_site_and_no_literal_colour(self):
		_, _, yaml_text = self.blocks("privacy")
		self.assertIn("var(--t-text)", yaml_text)
		self.assertNotRegex(yaml_text, r"#[0-9a-fA-F]{6}")

	def test_no_slot_is_left_for_the_writer(self):
		for kind in ("privacy", "notice"):
			blocks, _, yaml_text = self.blocks(kind)
			self.assertNotIn("WRITE ", yaml_text)
			self.assertEqual([], R.unfilled_slots(blocks))

	def test_the_words_of_the_document_are_in_the_page(self):
		_, _, yaml_text = self.blocks("privacy", FULL, "de")
		self.assertIn(legal.TEXT["de"]["p_rights_h"], yaml_text)
		self.assertIn("Atelier Test Sàrl", yaml_text)

	def test_a_name_with_quotes_colons_and_braces_survives_the_yaml(self):
		facts = legal.Facts(name='Café "Chez: Paul" {1}', address="Rue: de l'Essai, 1950 Sion", email="a@b.example")
		blocks, _, _ = self.blocks("privacy", facts)
		self.assertEqual(1, len(blocks))
		self.assertIn('Café "Chez: Paul" {1}', legal.plain_text("privacy", facts, "fr", TODAY))

	def test_the_headings_are_h2_and_the_page_has_no_h1(self):
		_, _, yaml_text = self.blocks("privacy")
		self.assertIn("el: h2", yaml_text)
		self.assertNotIn("el: h1", yaml_text)


class TestWhichPagesAreWrittenHere(unittest.TestCase):
	def test_the_policy_and_the_notice_are_written_without_a_model_and_the_terms_are_not(self):
		self.assertTrue(legal.is_mechanical({"type": "legal", "route": "privacy-policy"}))
		self.assertTrue(legal.is_mechanical({"type": "legal", "route": "/legal-notice"}))
		self.assertFalse(legal.is_mechanical({"type": "legal", "route": "terms-conditions"}))
		self.assertFalse(legal.is_mechanical({"type": "generic", "route": "privacy-policy"}))
		self.assertEqual("privacy", legal.kind_of({"type": "legal", "route": "privacy-policy"}))
		self.assertEqual("notice", legal.kind_of({"type": "legal", "route": "legal-notice"}))

	def test_every_site_is_planned_with_both_and_a_shop_with_its_terms_too(self):
		from builder.site_ai.nora.site_builder import plan_legal_pages

		with patch("builder.site_ai.nora.site_builder.legal_pages", return_value=[]), patch(
			"builder.site_ai.nora.site_builder._profile_sells", return_value=False
		):
			for lang in legal.LANGUAGES:
				added = plan_legal_pages([{"title": "Home", "route": "home", "type": "accueil"}], "A Site", "vitrine", lang)
				self.assertEqual(["privacy-policy", "legal-notice"], [p["route"] for p in added])
				self.assertEqual([legal.title("privacy", lang), legal.title("notice", lang)], [p["title"] for p in added])
				self.assertTrue(all(p["type"] == "legal" for p in added))
			shop = plan_legal_pages([], "A Shop", "ecommerce", "fr")
			self.assertEqual(["terms-conditions", "privacy-policy", "legal-notice"], [p["route"] for p in shop])
			# the terms carry the name the country's shops give them (a German shop says AGB, not "Bedingungen & Konditionen")
			self.assertEqual("Allgemeine Geschäftsbedingungen", plan_legal_pages([], "A Shop", "ecommerce", "de")[0]["title"])

	def test_a_page_the_client_asked_for_under_another_name_is_not_planned_twice(self):
		from builder.site_ai.nora.site_builder import normalise_pages, plan_legal_pages

		pages = normalise_pages(["Accueil", "Datenschutz", "Impressum"], "vitrine")
		with patch("builder.site_ai.nora.site_builder.legal_pages", return_value=[]), patch(
			"builder.site_ai.nora.site_builder._profile_sells", return_value=False
		):
			self.assertEqual([], plan_legal_pages(pages, "A Site", "vitrine", "de"))


class TestTheFinalPassesLeaveTheFixedDocumentsAlone(unittest.TestCase):
	def test_the_invented_facts_check_skips_the_policy_and_the_notice(self):
		"""The policy says "30 jours": the delay the law gives to answer a request for access, not a figure the model made up. Told of
		it, the final pass would have revised a page that only rewrites the same text (seen on the cabinet build, 2026-10-22)."""
		import inspect

		from builder.site_ai.nora import site_builder

		source = inspect.getsource(site_builder.build_site)
		self.assertIn('legal.is_mechanical({"type": item.get("type"), "route": item.get("planned")})', source)


class TestTheFactsOfASite(unittest.TestCase):
	def test_the_facts_come_from_the_verified_business_data(self):
		facts = legal.facts_from(
			{"company_name": "Atelier Test Sàrl", "email": "hello@atelier-test.example", "address": "Rue du Test 1"},
			"A Site Name",
			{"form": True, "map": False, "newsletter": False, "shop": False},
		)
		self.assertEqual("Atelier Test Sàrl", facts.name)
		self.assertEqual("", facts.phone)
		self.assertTrue(facts.form and not facts.map)

	def test_the_name_of_the_site_stands_in_for_a_company_nobody_named(self):
		self.assertEqual("A Site Name", legal.facts_from({}, "A Site Name", {}).name)

	def test_the_pages_of_the_site_tell_what_it_holds(self):
		rows = [
			{"blocks": '{"innerHTML": "{% include \\"builder/templates/includes/contact_form.html\\" %}"}'},
			{"blocks": '{"innerHTML": "{% include \\"builder/templates/includes/google_map.html\\" %}"}'},
		]
		with patch("builder.site_ai.nora.legal.frappe") as mock_frappe:
			mock_frappe.get_all.return_value = rows
			mock_frappe.db.has_column.return_value = True
			uses = legal.uses_of("A Profile", "vitrine")
		self.assertTrue(uses["form"] and uses["map"])
		self.assertFalse(uses["shop"])

	def test_a_shop_is_a_shop_whatever_its_pages_hold(self):
		with patch("builder.site_ai.nora.legal.frappe") as mock_frappe:
			mock_frappe.get_all.return_value = []
			self.assertTrue(legal.uses_of("A Profile", "ecommerce")["shop"])


if __name__ == "__main__":
	unittest.main()
