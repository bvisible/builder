# //// Neoffice — added file (no upstream equivalent): the door of the site's translations
# //// (builder/translation.py, multilingual lot 4, neoffice-maintenance#2032).
import copy
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from builder import translation
from frappe.tests.utils import FrappeTestCase

BLOCKS = [{"blockId": "a", "element": "h1", "innerHTML": "Bonjour"}]


def _door(language="de", found=None, units=None):
	"""A stand-in for the theme: the tests of Builder must not need it."""
	localized = SimpleNamespace(
		content_language=lambda: language,
		site_languages=lambda: {"de": {"hreflang": "de-CH", "publication": "Publish at once"}},
		get_document_translations=lambda doctype, name, lang: found or {},
	)

	def replace_blocks(blocks, translations):
		out = copy.deepcopy(blocks)
		for block in out:
			text = translations.get((block["blockId"], "innerHTML"))
			if text:
				block["innerHTML"] = text
		return out

	def replace_chrome(config, translations):
		for fieldname in ("cta_text",):
			if translations.get(("", fieldname)):
				config[fieldname] = translations[("", fieldname)]

	units = units or SimpleNamespace(localize_blocks=replace_blocks, localize_chrome=replace_chrome)
	return localized, units


class Config(frappe._dict):
	"""The chrome document of a request: a dict that has a name, a doctype and flags."""

	def __init__(self, **values):
		super().__init__(doctype="Website Header Footer Variant", name="Site", flags=frappe._dict(), **values)


class TestTranslationDoor(FrappeTestCase):
	def test_a_bench_without_the_theme_changes_nothing(self):
		page = {"name": "p", "page_title": "Accueil"}
		config = Config(cta_text="Nous visiter")
		with patch.object(translation, "_door", return_value=None):
			self.assertIsNone(translation.language())
			self.assertIs(translation.localize_blocks(BLOCKS, "p"), BLOCKS)
			self.assertEqual(translation.page_text(page, "page_title"), "Accueil")
			self.assertEqual(translation.page_label("Builder Page", "p", "Accueil"), "Accueil")
			self.assertIs(translation.localize_chrome(config), config)
			self.assertEqual(config.cta_text, "Nous visiter")

	def test_the_site_s_own_language_changes_nothing(self):
		with patch.object(
			translation, "_door", return_value=_door(language=None, found={("a", "innerHTML"): "Hallo"})
		):
			self.assertIs(translation.localize_blocks(BLOCKS, "p"), BLOCKS)
			self.assertEqual(
				translation.page_text({"name": "p", "page_title": "Accueil"}, "page_title"), "Accueil"
			)

	def test_in_another_language_the_blocks_the_title_and_the_chrome_are_the_translations(self):
		found = {
			("a", "innerHTML"): "Hallo",
			("", "page_title"): "Startseite",
			("", "cta_text"): "Besuchen Sie uns",
		}
		config = Config(cta_text="Nous visiter")
		with patch.object(translation, "_door", return_value=_door(found=found)):
			self.assertEqual(translation.language(), "de")
			self.assertEqual(translation.localize_blocks(BLOCKS, "p")[0]["innerHTML"], "Hallo")
			self.assertEqual(BLOCKS[0]["innerHTML"], "Bonjour")
			self.assertEqual(
				translation.page_text({"name": "p", "page_title": "Accueil"}, "page_title"), "Startseite"
			)
			self.assertEqual(
				translation.page_text({"name": "p", "meta_description": "Texte"}, "meta_description"), "Texte"
			)
			self.assertEqual(translation.page_label("Builder Page", "p", "Accueil"), "Startseite")
			self.assertEqual(translation.page_label("Web Page", "p", "Accueil"), "Accueil")
			translation.localize_chrome(config)
			self.assertEqual(config.cta_text, "Besuchen Sie uns")

	def test_the_chrome_is_translated_once_per_request(self):
		calls = []
		units = SimpleNamespace(
			localize_blocks=lambda blocks, found: blocks,
			localize_chrome=lambda config, found: calls.append(config.name),
		)
		config = Config()
		with patch.object(translation, "_door", return_value=_door(units=units)):
			translation.localize_chrome(config)
			translation.localize_chrome(config)
		self.assertEqual(calls, ["Site"])

	def test_the_editor_s_preview_is_never_translated(self):
		previous = getattr(frappe.local, "request", None)
		frappe.local.request = frappe._dict(for_preview=True)
		self.addCleanup(setattr, frappe.local, "request", previous)
		with patch.object(translation, "_door", return_value=_door(found={("a", "innerHTML"): "Hallo"})):
			self.assertIsNone(translation.language())
			self.assertIs(translation.localize_blocks(BLOCKS, "p"), BLOCKS)

	def test_a_failure_of_the_theme_costs_the_translation_never_the_page(self):
		def boom(*args):
			raise RuntimeError("the store is down")

		units = SimpleNamespace(localize_blocks=boom, localize_chrome=boom)
		config = Config(cta_text="Nous visiter")
		with (
			patch.object(translation, "_door", return_value=_door(units=units)),
			patch.object(frappe, "log_error") as log,
		):
			self.assertIs(translation.localize_blocks(BLOCKS, "p"), BLOCKS)
			self.assertIs(translation.localize_chrome(config), config)
		self.assertEqual(config.cta_text, "Nous visiter")
		self.assertEqual(log.call_count, 2)
		self.assertNotIn("localized_to", config.flags)

	def test_the_header_keeps_a_place_for_the_selector_only_on_a_site_with_a_language(self):
		render = "{% from 'builder/templates/includes/header_footer/macros.html' import render_icons %}{{ render_icons(icons) }}"
		self.assertIn("data-ml-slot", frappe.render_template(render, {"icons": {"languages": True}}))
		self.assertNotIn("data-ml-slot", frappe.render_template(render, {"icons": {}}))
		with patch.object(translation, "_door", return_value=_door()):
			self.assertTrue(translation.has_languages())
		with patch.object(translation, "_door", return_value=_door(language=None)):
			self.assertTrue(translation.has_languages())  # the slot depends on the site, not on the request
		with patch.object(translation, "_door", return_value=None):
			self.assertFalse(translation.has_languages())
