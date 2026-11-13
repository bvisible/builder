import os
from pathlib import Path
from unittest.mock import patch

import frappe
from babel.messages.extract import DEFAULT_KEYWORDS, extract_from_dir
from frappe.gettext.translate import get_method_map
from frappe.tests.utils import FrappeTestCase

# //// Neoffice — cockpit_catalogs: the catalogs the boot carries (test_boot_carries_only_builder_translations);
# //// nora_chat_boot, strings_of: Nora's one conversation in the Chat tab (13.11).
# //// desk_defaults: what the cards to validate read of the desk (13.11).
from builder.www._builder import cockpit_catalogs, desk_defaults, get_boot, nora_chat_boot, strings_of

FRONTEND_SRC = os.path.join("frontend", "src")


class TestI18n(FrappeTestCase):
	def test_frontend_strings_are_extractable(self):
		expected_locations = {
			"You do not have permission to access this page": {"frontend/src/router.ts"},
			"All Pages": {
				"frontend/src/components/DashboardHead.vue",
				"frontend/src/components/DashboardSidebar.vue",
				# //// Neoffice — the cockpit chrome carries the dashboard nav (All Pages /
				# //// Settings / Folders) into its own contextNav, so the same msgid is
				# //// extracted from there too (575f427e).
				"frontend/src/components/NeoCockpitBuilderSidebar.vue",
			},
			"Select (v)": {"frontend/src/components/ToolbarItems/ModeSwitcher.vue"},
			'Are you sure you want to unpublish "{0}"? It will no longer be accessible on the website.': {
				"frontend/src/stores/pageStore.ts"
			},
		}

		for message, locations in self.extract_frontend_messages().items():
			if message in expected_locations:
				self.assertEqual(locations, expected_locations.pop(message), message)

		self.assertFalse(expected_locations, f"Not extracted: {sorted(expected_locations)}")

	def extract_frontend_messages(self) -> dict[str, set[str]]:
		"""Run the POT extractors over frontend/src only, the way generate_pot does."""
		app_path = frappe.get_pymodule_path("builder", "..")
		keywords = DEFAULT_KEYWORDS.copy()
		keywords["_lt"] = None

		def is_frontend_src(dirpath) -> bool:
			relative = os.path.relpath(dirpath, app_path)
			return relative == "." or FRONTEND_SRC.startswith(relative) or relative.startswith(FRONTEND_SRC)

		messages = {}
		for filename, _, message, _, _ in extract_from_dir(
			app_path,
			get_method_map("builder") + get_method_map("frappe"),
			directory_filter=is_frontend_src,
			keywords=keywords,
		):
			if message:
				messages.setdefault(message, set()).add(filename.replace("\\", "/"))
		return messages

	def test_catalogs_carry_no_in_context_placeholders(self):
		"""Crowdin's in-context pseudo language exports `crwdns...` ids instead of translations.

		They score as fully translated, so nothing upstream rejects them, and compiling one
		shows those ids across the whole editor.
		"""
		locale_dir = Path(frappe.get_app_path("builder")) / "locale"
		polluted = [po.name for po in locale_dir.glob("*.po") if "crwdns" in po.read_text(encoding="utf-8")]

		self.assertEqual(polluted, [], f"Crowdin in-context placeholders found in: {polluted}")

	def test_boot_carries_only_builder_translations(self):
		with patch("builder.www._builder.get_translations_from_apps", return_value={}) as from_apps:
			get_boot()

		# //// Neoffice — Builder's catalog plus the Neoffice cockpit's (frappe, neoffice_theme), Builder's
		# //// last, and still never every app's: the cockpit around the editor translates its own words
		# //// through this boot (see get_boot). Upstream asserted ["builder"] alone.
		from_apps.assert_called_once_with(frappe.local.lang, cockpit_catalogs())
		self.assertEqual(cockpit_catalogs()[-1], "builder")
		self.assertLessEqual(set(cockpit_catalogs()), {"frappe", "neoffice_theme", "builder"})

	# //// Neoffice — the Chat tab draws Nora's one conversation (nora_chat_boot, 13.11).
	def test_without_nora_the_chat_tab_is_upstreams(self):
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder"]):
			self.assertIsNone(nora_chat_boot("fr"))

	def test_nora_chat_files_come_from_the_apps_own_hooks(self):
		hooks = {
			("app_include_js", "nora"): [
				"/assets/nora/js/other.js",
				"/assets/nora/js/nora_chat/nora_chat_core.js?v=9",
				# //// Neoffice — the conversation's modules (13.11)
				"/assets/nora/js/nora_chat/nora_chat_features.js?v=3",
				# //// Neoffice — the cards to validate, a module too (13.11)
				"/assets/nora/js/nora_chat/nora_chat_cards.js?v=3",
			],
			("app_include_css", "nora"): [
				"/assets/nora/css/nora_tokens.css?v=2",
				# //// Neoffice — the modules' sheet (13.11)
				"/assets/nora/css/nora_quick_chat.css?v=49",
				"/assets/nora/css/nora_chat/nora-chat-core.css?v=6",
			],
			("app_include_js", "neoffice_activity"): ["/assets/neoffice_activity/js/nora_input.js?v=2"],
		}
		with (
			patch(
				"frappe.get_installed_apps", return_value=["frappe", "neoffice_activity", "nora", "builder"]
			),
			patch(
				"frappe.get_hooks", side_effect=lambda hook, app_name=None: hooks.get((hook, app_name), [])
			),
			patch("builder.www._builder.nora_chat_messages", return_value={"Stop": "Arrêter"}),
			# //// Neoffice — the desk's defaults the cards read (13.11)
			patch(
				"builder.www._builder.desk_defaults",
				return_value={"defaults": {"currency": "CHF"}, "currency": None},
			),
		):
			boot = nora_chat_boot("fr")
		# the desk's entry before the conversation, which looks for it when it draws its own
		self.assertEqual(
			boot["scripts"],
			[
				"/assets/neoffice_activity/js/nora_input.js?v=2",
				"/assets/nora/js/nora_chat/nora_chat_core.js?v=9",
				# //// Neoffice — the conversation's modules come after it (13.11)
				"/assets/nora/js/nora_chat/nora_chat_features.js?v=3",
				# //// Neoffice — then the cards, which are one of them (13.11)
				"/assets/nora/js/nora_chat/nora_chat_cards.js?v=3",
			],
		)
		# //// Neoffice — and the modules' sheet after the conversation's (13.11)
		self.assertEqual(
			boot["styles"],
			[
				"/assets/nora/css/nora_tokens.css?v=2",
				"/assets/nora/css/nora_chat/nora-chat-core.css?v=6",
				"/assets/nora/css/nora_quick_chat.css?v=49",
			],
		)
		self.assertEqual(boot["messages"], {"Stop": "Arrêter"})
		# //// Neoffice — the cards read the desk's defaults (13.11)
		self.assertEqual(boot["desk"], {"defaults": {"currency": "CHF"}, "currency": None})

	# //// Neoffice — the cards to validate write a figure, an amount and a date as the desk does (13.11)
	def test_the_cards_read_only_the_desk_defaults_they_write_with(self):
		everything = {
			"currency": "CHF",
			"number_format": "#'###.##",
			"date_format": "dd.mm.yyyy",
			"hide_currency_symbol": "",
			"smtp_server": "mail.example.com",
		}
		record = {"name": "CHF", "symbol": "CHF", "symbol_on_right": 0, "number_format": "#'###.##"}
		with (
			patch("frappe.defaults.get_defaults", return_value=everything),
			patch("frappe.db.get_value", return_value=record) as get_value,
		):
			desk = desk_defaults()
		self.assertEqual(
			desk["defaults"], {"currency": "CHF", "number_format": "#'###.##", "date_format": "dd.mm.yyyy"}
		)
		self.assertEqual(desk["currency"], record)
		self.assertEqual(get_value.call_args.args[:2], ("Currency", "CHF"))

	def test_the_boot_carries_only_the_strings_the_conversation_says(self):
		code = '__("Stop"); __("{0} steps", [n], "Nora\'s steps"); __("Working…", null, "Nora");'
		catalog = {
			"Stop": "Arrêter",
			"{0} steps:Nora's steps": "{0} étapes",
			"Working…": "Au travail…",
			"Other": "Autre",
		}
		self.assertEqual(
			strings_of([code], catalog),
			{"Stop": "Arrêter", "{0} steps:Nora's steps": "{0} étapes", "Working…": "Au travail…"},
		)
