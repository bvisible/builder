# //// Neoffice — added file (no upstream equivalent): one photo treatment for the whole site
# //// (builder/site_ai/nora/photo_treatment.py).
import unittest

from builder.site_ai.nora.photo_treatment import GRAYSCALE, grayscale_photos


def img(src, **extra):
	return {"element": "img", "attributes": {"src": src}, "baseStyles": {}, **extra}


class TestGrayscalePhotos(unittest.TestCase):
	def test_every_photograph_of_the_page_goes_grey(self):
		band = {
			"element": "section",
			"baseStyles": {"backgroundImage": "url('/files/b.jpg')"},
			"children": [],
		}
		page = [{"element": "div", "children": [img("/files/a.jpg"), band]}]
		self.assertEqual(len(grayscale_photos(page)), 2)
		self.assertEqual(page[0]["children"][0]["baseStyles"]["filter"], GRAYSCALE)
		self.assertEqual(band["baseStyles"]["filter"], GRAYSCALE)

	def test_a_photograph_already_grey_is_left_as_it_is(self):
		# the home of a monochrome build: seven photographs the model had greyed itself
		page = [img("/files/a.jpg", baseStyles={"filter": "grayscale(100%)"})]
		self.assertEqual(grayscale_photos(page), [])

	def test_inside_a_grey_block_nothing_is_added(self):
		photo = img("/files/a.jpg")
		page = [{"element": "div", "baseStyles": {"filter": "grayscale(1)"}, "children": [photo]}]
		self.assertEqual(grayscale_photos(page), [])
		self.assertNotIn("filter", photo["baseStyles"])

	def test_a_picture_the_page_data_binds_goes_grey(self):
		tile = {
			"element": "div",
			"baseStyles": {},
			"dynamicValues": [{"type": "style", "property": "backgroundImage", "key": "image"}],
		}
		self.assertEqual(len(grayscale_photos([tile])), 1)
		self.assertEqual(tile["baseStyles"]["filter"], GRAYSCALE)

	def test_the_logo_and_drawings_keep_their_colour(self):
		self.assertEqual(
			grayscale_photos([img("/files/logo.png"), img("/files/icon.svg")], keep={"/files/logo.png"}), []
		)

	def test_an_existing_filter_is_kept(self):
		photo = img("/files/a.jpg", baseStyles={"filter": "brightness(0.8)"})
		grayscale_photos([photo])
		self.assertEqual(photo["baseStyles"]["filter"], "brightness(0.8) grayscale(100%)")

	def test_a_gradient_is_not_a_photograph(self):
		band = {"element": "section", "baseStyles": {"backgroundImage": "linear-gradient(#000, #333)"}}
		self.assertEqual(grayscale_photos([band]), [])
