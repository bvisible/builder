# //// Neoffice — added file (no upstream equivalent): no entry of our catalogues says again, in
# //// English, a word a core app of the bench translates (neoffice-maintenance#1651).
"""A catalogue entry of this app that repeats its English source hides the core's word.

Frappe merges the catalogue of every app into ONE flat dictionary, the last app loaded winning. An
entry `msgid "Notes"` / `msgstr "Notes"` is therefore not "nothing": it replaces the word the core
gives ("Remarques") on every screen of the desk, and the night translator never touches it, since an
entry with a translation looks done.

So a bare entry (no context) whose translation is its own source must not exist when frappe,
erpnext or neoffice_theme translate that msgid to something else: leave it empty and the core's word
shows. An identity entry on a word no core app translates is fine (Contact, Message, a brand name).

The catalogues are read from source, with no site and no import of the apps. A core app that is not
in the bench is skipped; with none of them, the test has nothing to compare against.
"""

import ast
import os
import re
import tempfile
import unittest

import frappe

LOCALE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale")
CORE_APPS = ("frappe", "erpnext", "neoffice_theme")
LANGUAGES = ("fr", "de")

# (language, msgid) -> why the identity entry stays although a core app says the word differently.
DELIBERATE_IDENTITIES = {
	("de", "Letter"): (
		"the label of the letter spacing in the typography panel; the core's 'Brief' is a mail letter"
	),
}

FIELD = re.compile(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")\s*$')


def read_po(path: str) -> list[dict]:
	"""The live entries of a PO file as {msgctxt, msgid, msgid_plural, msgstr} dicts. Obsolete
	entries (#~) are comments to the loader and are not read."""
	entries: list[dict] = []
	entry: dict = {}
	field = None

	def flush():
		nonlocal entry, field
		if "msgid" in entry:
			entries.append(entry)
		entry, field = {}, None

	with open(path, encoding="utf-8") as f:
		for raw in f:
			line = raw.strip()
			if not line:
				flush()
			elif line.startswith("#"):
				continue
			elif match := FIELD.match(line):
				if match.group(1) == "msgid" and "msgid" in entry:
					flush()
				field = match.group(1)
				entry[field] = ast.literal_eval(match.group(2))
			elif line.startswith('"') and field:
				entry[field] += ast.literal_eval(line)
	flush()
	return entries


def bare(entry: dict) -> bool:
	return bool(entry.get("msgid")) and not entry.get("msgctxt") and "msgid_plural" not in entry


def core_catalogue(app: str, lang: str) -> str | None:
	"""The path of an installed core app's PO file for `lang`, or None when the bench lacks it."""
	try:
		path = frappe.get_app_path(app, "locale", f"{lang}.po")
	except Exception:
		return None
	return path if os.path.isfile(path) else None


def core_words(lang: str) -> dict[str, dict[str, str]]:
	"""{bare msgid: {app: its translation}} over the core apps of the bench."""
	words: dict[str, dict[str, str]] = {}
	for app in CORE_APPS:
		if not (path := core_catalogue(app, lang)):
			continue
		for entry in read_po(path):
			if bare(entry) and entry.get("msgstr"):
				words.setdefault(entry["msgid"], {})[app] = entry["msgstr"]
	return words


class TestLocaleIdentity(unittest.TestCase):
	def test_no_entry_repeats_its_source_where_a_core_app_translates_it(self):
		compared = 0
		for lang in LANGUAGES:
			core = core_words(lang)
			if not core:
				continue
			compared += 1
			own = read_po(os.path.join(LOCALE, f"{lang}.po"))
			hiding = {
				entry["msgid"]: {
					app: word for app, word in core[entry["msgid"]].items() if word != entry["msgid"]
				}
				for entry in own
				if bare(entry)
				and entry.get("msgstr") == entry["msgid"]
				and (lang, entry["msgid"]) not in DELIBERATE_IDENTITIES
				and any(word != entry["msgid"] for word in core.get(entry["msgid"], {}).values())
			}
			self.assertEqual(
				hiding,
				{},
				f"{lang}.po repeats the English source of words the core translates; empty the msgstr "
				"(and list the msgid in keep_empty.txt) so the core's word shows",
			)
		if not compared:
			self.skipTest("no core app catalogue in this bench to compare with")

	def test_the_reader_keeps_contexts_plurals_and_continuations_apart(self):
		sample = (
			'msgid ""\nmsgstr ""\n"Language: fr\\n"\n\n'
			'#: a.py:1\nmsgid "Notes"\nmsgstr "Notes"\n\n'
			'msgctxt "tab"\nmsgid "Notes"\nmsgstr "Notes"\n\n'
			'msgid "Long"\nmsgstr ""\n"Une "\n"phrase"\n\n'
			'msgid "Day"\nmsgid_plural "Days"\nmsgstr[0] "Jour"\nmsgstr[1] "Jours"\n\n'
			'#~ msgid "Gone"\n#~ msgstr "Gone"\n'
		)
		with tempfile.TemporaryDirectory() as folder:
			path = os.path.join(folder, "sample.po")
			with open(path, "w", encoding="utf-8") as f:
				f.write(sample)
			entries = read_po(path)

		self.assertEqual(
			[(e["msgid"], bare(e)) for e in entries],
			[("", False), ("Notes", True), ("Notes", False), ("Long", True), ("Day", False)],
		)
		self.assertEqual(entries[3]["msgstr"], "Une phrase")
