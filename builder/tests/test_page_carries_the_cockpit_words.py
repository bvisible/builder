# //// Neoffice — added file (no upstream equivalent).
#
# /builder carries the translations the Neoffice cockpit around the editor needs. Its boot held
# Builder's own catalog only (upstream: « the editor never looks up another app's strings »), and
# the cockpit translates its own words through the same __: « Search… », « Favorites »,
# « Collapse menu » stayed English on /builder while every other app showed them in French (07.10).
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.translate import get_translations_from_apps, get_user_translations

from builder.www import _builder


class TestTheCockpitWordsReachBuilder(FrappeTestCase):
	def boot_messages(self):
		with patch.object(frappe.local, "lang", "fr"):
			return _builder.get_boot()["translated_messages"]

	def test_the_cockpit_words_are_translated(self):
		if "neoffice_theme" not in frappe.get_installed_apps():
			self.skipTest("neoffice_theme holds the cockpit's words")
		messages = self.boot_messages()
		# The theme's catalog for the first two, frappe's for « Tools ».
		for word in ("Collapse menu", "Active module", "Tools"):
			self.assertIn(word, messages)
			self.assertNotEqual(messages[word], word, word)

	def test_builder_keeps_its_own_words(self):
		own = get_translations_from_apps("fr", ["builder"])
		users = get_user_translations("fr") or {}
		messages = self.boot_messages()
		expected = {source: users.get(source, translated) for source, translated in own.items()}
		self.assertEqual({source: messages.get(source) for source in own}, expected)
