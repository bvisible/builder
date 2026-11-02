# //// Neoffice — added file (no upstream equivalent): no dialog of the editor speaks an API frappe-ui removed.
"""frappe-ui 1.0 dropped the `options` prop and the `#body` slot of Dialog, with no error and no warning: the Theme and Media screens opened as an empty box
from the merge of upstream 1.36.1 on, and the question before removing a plugin lost its text. Both are ours, so nobody upstream had to port them."""

import re
import unittest
from pathlib import Path

SOURCES = Path(__file__).resolve().parents[2] / "frontend" / "src"
DIALOG = re.compile(r"<Dialog\b(?!Root)[^<]*?(?:/>|>)", re.DOTALL)


@unittest.skipUnless(SOURCES.is_dir(), "the frontend sources are not on this bench")
class TestDialogsSpeakTheCurrentApi(unittest.TestCase):
	def test_no_dialog_uses_the_options_prop_or_the_body_slot(self):
		spoken = []
		for path in SOURCES.rglob("*.vue"):
			text = path.read_text(encoding="utf-8")
			if any(":options" in tag for tag in DIALOG.findall(text)):
				spoken.append(f"{path.name}: options")
			if "frappe-ui" in text and "Dialog" in text and re.search(r"<template #body\b", text):
				spoken.append(f"{path.name}: #body")
		self.assertEqual([], spoken)
