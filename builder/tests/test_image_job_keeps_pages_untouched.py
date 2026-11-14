# //// Neoffice — added file (no upstream equivalent): a page the generator wrote stays its own after the image job drew its pictures.
"""The image job rewrote the blocks of the pages it drew pictures into, without their fingerprint (ai_blocks_hash): the next rebuild asked
to replace « 3 pages made by hand » that were the generator's own — exactly the ones with generated photographs (14.11, osiris).
"""

import json
import unittest
from unittest import mock

from builder import api

PLACEHOLDER = "https://placehold.co/1200x800"


def page_blocks(src: str) -> str:
	return json.dumps(
		[
			{
				"element": "div",
				"blockId": "root",
				"children": [
					{"element": "img", "blockId": "i1", "attributes": {"src": src, "alt": "an oak bench"}}
				],
			}
		]
	)


class FakePage:
	def __init__(self, blocks: str, stored: str | None):
		self.data = {"blocks": blocks, "draft_blocks": blocks, "ai_blocks_hash": stored}
		self.saved = False

	def get(self, key):
		return self.data.get(key)

	def set(self, key, value):
		self.data[key] = value

	def save(self, **kwargs):
		self.saved = True


class TestThePictureKeepsThePageUntouched(unittest.TestCase):
	def draw(self, page: FakePage) -> FakePage:
		with (
			mock.patch.object(api.frappe, "get_doc", return_value=page),
			mock.patch.object(api.frappe.db, "commit"),
		):
			api._replace_image_in_page("page-1", "i1", "/files/gen_1.png")
		return page

	def test_a_page_as_the_generator_wrote_it_stays_its_own(self):
		blocks = page_blocks(PLACEHOLDER)
		page = self.draw(FakePage(blocks, api._blocks_fingerprint(blocks)))
		self.assertIn("/files/gen_1.png", page.get("draft_blocks"))
		self.assertEqual(page.get("ai_blocks_hash"), api._blocks_fingerprint(page.get("draft_blocks")))
		self.assertTrue(api._untouched_by_hand(page), "the rebuild still sees the generator's page")

	def test_a_page_someone_edited_stays_edited(self):
		blocks = page_blocks(PLACEHOLDER)
		page = self.draw(FakePage(blocks, "fingerprint-of-an-earlier-version"))
		self.assertEqual(page.get("ai_blocks_hash"), "fingerprint-of-an-earlier-version")
		self.assertFalse(api._untouched_by_hand(page))

	def test_a_page_the_generator_never_wrote_gets_no_fingerprint(self):
		page = self.draw(FakePage(page_blocks(PLACEHOLDER), None))
		self.assertIsNone(page.get("ai_blocks_hash"))
