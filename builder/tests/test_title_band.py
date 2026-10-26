# //// Neoffice — added file (no upstream equivalent): a chrome with no title band gets one when a site is built.
"""A real instance whose chrome said `page_header_template = None` (the older ones do) built a site whose interior pages were written
under a title band the site did not draw: the layout check refused each of them after four revisions ("the site's title band is
missing") and the build un-published them, the contact page included (2026-10-26, a rehearsal of a client's regeneration). No model is
called."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from builder import api
from builder.api import apply_brief_site_chrome, title_band_for


class TestWhichBandStays(unittest.TestCase):
	def test_a_chrome_with_a_band_keeps_it(self):
		for current in ("Standard", "Minimal", "Centered", "Split", "Builder"):
			self.assertIsNone(title_band_for(current, "Split"), current)

	def test_a_chrome_with_none_takes_the_briefs(self):
		for current in ("None", None, ""):
			self.assertEqual(title_band_for(current, "Centered"), "Centered", repr(current))

	def test_the_band_is_never_none_itself(self):
		for wanted in ("None", None, ""):
			self.assertEqual(title_band_for("None", wanted), "Standard", repr(wanted))


class Config:
	"""The part of a chrome doc that apply_brief_site_chrome uses."""

	doctype = "Website Header Footer Variant"

	def __init__(self, **values):
		self.values = values
		self.saved = False
		self.meta = SimpleNamespace(get_field=lambda name: None, has_field=lambda name: True)

	def get(self, name, default=None):
		return self.values.get(name, default)

	def set(self, name, value):
		self.values[name] = value

	def save(self, **kwargs):
		self.saved = True


class TestTheBuildAppliesIt(unittest.TestCase):
	"""Through apply_brief_site_chrome, not beside it."""

	def apply(self, config, brief):
		with patch.object(api, "_get_site_chrome_config", return_value=config), patch.object(api, "frappe", MagicMock()):
			return apply_brief_site_chrome(brief, website_profile="A profile")

	def test_a_chrome_with_no_band_gets_the_briefs_and_is_saved(self):
		config = Config(page_header_template="None")
		applied = self.apply(config, SimpleNamespace(page_header_template="Centered"))
		self.assertEqual(config.values["page_header_template"], "Centered")
		self.assertIn("page_header_template", applied)
		self.assertTrue(config.saved)

	def test_a_chrome_with_a_band_is_left_alone(self):
		config = Config(page_header_template="Minimal")
		applied = self.apply(config, SimpleNamespace(page_header_template="Split"))
		self.assertEqual(config.values["page_header_template"], "Minimal")
		self.assertNotIn("page_header_template", applied)

	def test_a_brief_that_says_none_still_leaves_a_band(self):
		config = Config(page_header_template="None")
		self.apply(config, SimpleNamespace(page_header_template="None"))
		self.assertEqual(config.values["page_header_template"], "Standard")
