# //// Neoffice — added file (no upstream equivalent): what a client hands over — the sites
# //// they point at, the pictures they like, and their own photographs.
import unittest
from unittest.mock import MagicMock, patch

from builder.site_ai.nora.inspiration import MAX_IMAGES, MAX_URLS, chroma, coloured_share, is_neutral, monochrome

# measured on two real reference sites: pages of large photographs, no colour at all
PHOTO_PAGE = {
	"dominant_colors": [
		{"hex": "#3a332f", "percentage": 35.6},
		{"hex": "#645a54", "percentage": 27.7},
		{"hex": "#888580", "percentage": 19.5},
		{"hex": "#c1bbb7", "percentage": 12.9},
		{"hex": "#f1efee", "percentage": 4.3},
	]
}
INK_AND_PAPER = {
	"dominant_colors": [
		{"hex": "#f7f5f8", "percentage": 28.4},
		{"hex": "#b3b2a4", "percentage": 21.4},
		{"hex": "#3a3c3c", "percentage": 17.7},
		{"hex": "#020504", "percentage": 16.1},
	]
}
BRANDED = {"dominant_colors": [{"hex": "#e578d1", "percentage": 40.0}, {"hex": "#1b1f24", "percentage": 30.0}]}
# measured too: a page of warm photography, and a page whose only pigment is its brand mark
WARM_PHOTOGRAPHY = {
	"dominant_colors": [
		{"hex": "#ece3d9", "percentage": 42.6},
		{"hex": "#88827d", "percentage": 21.8},
		{"hex": "#b8b0a8", "percentage": 15.4},
		{"hex": "#1e1d18", "percentage": 10.5},
		{"hex": "#72533e", "percentage": 9.7},
	]
}
ONE_ORANGE_MARK = {
	"dominant_colors": [
		{"hex": "#fefefe", "percentage": 74.2},
		{"hex": "#313434", "percentage": 10.9},
		{"hex": "#875d5d", "percentage": 7.6},
		{"hex": "#c0b5b5", "percentage": 5.8},
		{"hex": "#f67012", "percentage": 1.6},
	]
}


class TestNoColour(unittest.TestCase):
	def test_chroma_reads_distance_from_grey(self):
		for grey in ("#000000", "#ffffff", "#888888", "#3a3c3c"):
			self.assertLess(chroma(grey), 0.05, grey)
		self.assertGreater(chroma("#e578d1"), 0.4)
		self.assertEqual(chroma("not a colour"), 0.0)

	def test_a_page_of_photographs_reads_as_no_colour(self):
		"""Its browns and greys are the photography, not a palette: what decides is how
		much of the page is chromatic, not whether one swatch is."""
		self.assertTrue(is_neutral(PHOTO_PAGE))
		self.assertTrue(is_neutral(INK_AND_PAPER))
		self.assertTrue(is_neutral(WARM_PHOTOGRAPHY))
		self.assertTrue(is_neutral(ONE_ORANGE_MARK))
		self.assertFalse(is_neutral(BRANDED))
		self.assertFalse(is_neutral({}))

	def test_the_coloured_share_is_what_is_measured(self):
		# skin and wood in the pictures, plus a brand mark: under a tenth of the page
		self.assertLess(coloured_share(WARM_PHOTOGRAPHY), 15)
		self.assertLess(coloured_share(ONE_ORANGE_MARK), 15)
		self.assertGreater(coloured_share(BRANDED), 15)
		self.assertEqual(coloured_share(PHOTO_PAGE), 0)

	def test_monochrome_needs_every_source_to_agree(self):
		self.assertTrue(monochrome({"sources": [{"analysis": PHOTO_PAGE}, {"analysis": INK_AND_PAPER}, {"analysis": WARM_PHOTOGRAPHY}, {"analysis": ONE_ORANGE_MARK}]}))
		# one coloured reference and the client has not asked for black and white
		self.assertFalse(monochrome({"sources": [{"analysis": PHOTO_PAGE}, {"analysis": BRANDED}]}))
		self.assertFalse(monochrome({"sources": []}))


class TestEverySourceIsRead(unittest.TestCase):
	def test_the_caps_hold_a_whole_email_of_references(self):
		"""A client names their references by the handful; three of eight silently dropped
		the rest."""
		from builder.site_ai.nora import inspiration

		urls = [f"https://example{i}.test/" for i in range(12)]
		images = [f"/files/ref{i}.png" for i in range(12)]
		with patch.object(inspiration, "read_url", side_effect=lambda u: {"kind": "URL", "source": u, "image": u, "analysis": {}}), patch.object(
			inspiration, "read_image", side_effect=lambda i: {"kind": "Image", "source": i, "image": i, "analysis": {}}
		), patch.object(inspiration, "_record"):
			found = inspiration.gather(urls, images, record=False)
		read = [s["source"] for s in found["sources"]]
		self.assertEqual(len([r for r in read if r.startswith("http")]), MAX_URLS)
		self.assertEqual(len([r for r in read if r.startswith("/files/")]), MAX_IMAGES)
		self.assertGreaterEqual(MAX_URLS, 8)


class TestClientLibrary(unittest.TestCase):
	def _run(self, files, known=None, understood=True):
		from builder.site_ai.ingestion import content_understanding as cu

		inserted = []

		def new_doc(doctype):
			doc = MagicMock()
			doc.name = f"asset-{len(inserted)}"
			doc.insert.side_effect = lambda **k: inserted.append(doc)
			return doc

		def get_all(doctype, **kwargs):
			return list(known or [])

		with patch.object(cu.frappe, "new_doc", side_effect=new_doc), patch.object(
			cu.frappe, "get_all", side_effect=get_all
		), patch.object(cu.frappe.db, "commit"), patch.object(
			cu, "understand_asset", return_value={"status": "understood" if understood else "failed"}
		):
			result = cu.ingest_and_understand("session-1", files)
		return result, inserted

	def test_a_batch_of_photographs_is_taken_in_and_read(self):
		result, inserted = self._run(["/files/shop.jpg", {"file_url": "/files/team.jpg"}])
		self.assertEqual(result, {"taken": 2, "understood": 2})
		self.assertEqual([d.file for d in inserted], ["/files/shop.jpg", "/files/team.jpg"])

	def test_what_is_not_a_site_file_is_refused(self):
		result, inserted = self._run(["https://example.test/photo.jpg", "", None, "../../etc/passwd"])
		self.assertEqual(result, {"taken": 0, "understood": 0})
		self.assertEqual(inserted, [])

	def test_the_same_photograph_is_not_taken_in_twice(self):
		result, _ = self._run(["/files/shop.jpg", "/files/shop.jpg", "/files/new.jpg"], known=["/files/shop.jpg"])
		self.assertEqual(result["taken"], 1)

	def test_a_photograph_the_model_could_not_read_still_counts_as_taken(self):
		result, _ = self._run(["/files/shop.jpg"], understood=False)
		self.assertEqual(result, {"taken": 1, "understood": 0})


class TestPlacingPhotographs(unittest.TestCase):
	def test_the_file_name_counts_as_keywords(self):
		"""A client names their pictures after what is in them, and it is the only reading
		left when the vision pass fails."""
		from builder.site_ai.ingestion.image_matcher import _score

		slot = {"section": "generic", "slot_type": "gallery", "orientation": "landscape", "context": "snowboard rider in action"}
		named = {"original_filename": "snowboard-rider-action-2026.jpg", "orientation": "landscape"}
		anonymous = {"original_filename": "IMG_4821.jpg", "orientation": "landscape"}
		self.assertGreater(_score(slot, named, 0), _score(slot, anonymous, 0))

	def test_the_same_photograph_is_not_used_everywhere(self):
		from builder.site_ai.ingestion.image_matcher import _score

		slot = {"section": "generic", "slot_type": "gallery", "orientation": "landscape", "context": ""}
		asset = {"original_filename": "shop.jpg", "orientation": "landscape", "quality": "high"}
		self.assertGreater(_score(slot, asset, 0), _score(slot, asset, 2))
