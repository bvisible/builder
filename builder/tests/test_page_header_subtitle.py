# //// Neoffice — added file (no upstream equivalent): the band over a Builder page never repeats
# //// a line the page prints (neoffice-maintenance#393).
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from builder import page_header
from builder.page_header import _page_prints

LINE = "We answer every message within two working days."
OTHER = "A small studio for people who move, in the middle of the old town."
BLOCKS = [
	{
		"element": "section",
		"children": [
			{"element": "h2", "innerHTML": "Write to us"},
			{
				"element": "p",
				"innerHTML": "<span>We answer every message within two&nbsp;working days.</span>",
			},
			{"element": "div", "innerHTML": "{% include 'builder/templates/includes/contact_form.html' %}"},
		],
	}
]


class TestPagePrints(unittest.TestCase):
	def test_a_line_one_block_prints_is_a_repeat(self):
		self.assertTrue(_page_prints(BLOCKS, LINE))

	def test_the_stored_json_reads_the_same(self):
		self.assertTrue(_page_prints(json.dumps(BLOCKS), LINE))

	def test_a_line_the_page_does_not_print_is_not_a_repeat(self):
		self.assertFalse(_page_prints(BLOCKS, OTHER))

	def test_a_line_cut_on_an_ellipsis_is_still_a_repeat(self):
		# builder.api._shorten_for_footer ends a cut on "…"
		self.assertTrue(_page_prints(BLOCKS, "We answer every message within two…"))

	def test_a_few_words_are_never_called_a_repeat(self):
		self.assertFalse(_page_prints(BLOCKS, "Write to us"))

	def test_blocks_that_cannot_be_read_repeat_nothing(self):
		for blocks in ("not json", None, {"element": "div"}):
			self.assertFalse(_page_prints(blocks, LINE))


class TestBuilderPageBandSubtitle(unittest.TestCase):
	"""What render_builder_page_header hands the band as its subtitle (render() is stubbed)."""

	def band(self, **fields):
		doc = frappe._dict(route="contact", page_title="Contact", blocks=json.dumps(BLOCKS), **fields)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(
				page_header, "render", side_effect=lambda context: context.page_header_subtitle or "(none)"
			),
		):
			return page_header.render_builder_page_header(doc)

	def test_a_description_the_page_prints_stays_out_of_the_band(self):
		self.assertEqual(self.band(meta_description=LINE), "(none)")

	def test_a_description_of_its_own_is_the_subtitle(self):
		self.assertEqual(self.band(meta_description=OTHER), OTHER)

	def test_a_subtitle_written_for_the_band_is_kept(self):
		self.assertEqual(self.band(meta_description=LINE, page_header_subtitle=LINE), LINE)

	def test_a_preview_judges_the_draft(self):
		draft = json.dumps([{"element": "p", "innerHTML": OTHER}])
		previous = getattr(frappe.local, "request", None)
		frappe.local.request = SimpleNamespace(for_preview=True)
		try:
			self.assertEqual(self.band(meta_description=OTHER, draft_blocks=draft), "(none)")
			self.assertEqual(self.band(meta_description=LINE, draft_blocks=draft), LINE)
		finally:
			frappe.local.request = previous
