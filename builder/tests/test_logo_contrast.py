# //// Neoffice — added file (no upstream equivalent): the chrome's logo is measured against its ground (neoffice-maintenance #1766).
"""A dark navy mark on a deep brown footer was a barely visible rectangle on the home pages of four test
builds (2026-10-20). The build now measures the logo against the ground and shows the site's name when
the logo cannot be seen. No model is called, no file of the site is read: logos are drawn in memory."""

import unittest
from types import SimpleNamespace

from builder.site_ai.nora.logo_contrast import ink_of, logo_reads, settle_chrome_logos

try:
	from PIL import Image, ImageDraw
except ImportError:  # the pure rules below still run
	Image = None

NAVY = (24, 38, 82)
CREAM = (245, 238, 222)
MID_GREY = (128, 128, 128)  # relative luminance 0.22: 3.9:1 on white, 4.4:1 on #1a1a1a
BROWN = "#2b1a12"
PAPER = "#faf7f2"
MID_GROUND = "#808080"


def flat(colour, n=100):
	return [colour] * n


def near(colour, wanted, spread=6):
	return all(abs(a - b) <= spread for a, b in zip(colour, wanted, strict=True))


def drawn(colour, background=(0, 0, 0, 0), box=(20, 10, 100, 30)):
	"""A 120x40 file with a rectangle of ink in it, on a transparent canvas unless told otherwise."""
	image = Image.new("RGBA", (120, 40), background)
	ImageDraw.Draw(image).rectangle(box, fill=(*colour, 255))
	return image


class Chrome(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


def chrome(**fields):
	base = {
		"header_bg_color": PAPER,
		"footer_bg_color": BROWN,
		"logo_type": "Image",
		"logo_image": "/files/logo-default.png",
		"show_footer_logo": 1,
		"footer_logo_type": "Image",
		"footer_logo_image": "/files/logo-default.png",
	}
	base.update(fields)
	return Chrome(**base)


class TestLogoAgainstItsGround(unittest.TestCase):
	def test_a_dark_logo_on_a_dark_ground_is_lost(self):
		self.assertIs(logo_reads("/f.png", BROWN, measure=lambda url: flat(NAVY)), False)

	def test_a_light_logo_on_a_light_ground_is_lost(self):
		self.assertIs(logo_reads("/f.png", PAPER, measure=lambda url: flat(CREAM)), False)

	def test_a_logo_of_the_opposite_tone_is_seen(self):
		self.assertIs(logo_reads("/f.png", PAPER, measure=lambda url: flat(NAVY)), True)
		self.assertIs(logo_reads("/f.png", BROWN, measure=lambda url: flat(CREAM)), True)

	def test_a_mid_tone_logo_is_seen_on_a_dark_and_on_a_light_ground_but_not_on_its_own_tone(self):
		self.assertIs(logo_reads("/f.png", "#1a1a1a", measure=lambda url: flat(MID_GREY)), True)
		self.assertIs(logo_reads("/f.png", "#ffffff", measure=lambda url: flat(MID_GREY)), True)
		self.assertIs(logo_reads("/f.png", MID_GROUND, measure=lambda url: flat(MID_GREY)), False)

	def test_the_majority_of_the_ink_decides(self):
		two_tone = lambda navy, cream: (lambda url: flat(NAVY, navy) + flat(CREAM, cream))  # noqa: E731
		self.assertIs(logo_reads("/f.png", BROWN, measure=two_tone(70, 30)), False)
		self.assertIs(logo_reads("/f.png", BROWN, measure=two_tone(30, 70)), True)

	def test_what_cannot_be_told_is_not_called_lost(self):
		seen = lambda url: flat(NAVY)  # noqa: E731
		self.assertIsNone(logo_reads("/f.png", "var(--unknown)", measure=seen))
		self.assertIsNone(logo_reads("/f.png", "transparent", measure=seen))
		self.assertIsNone(logo_reads("/f.png", "rgba(0,0,0,0.3)", measure=seen))
		self.assertIsNone(logo_reads("/f.png", BROWN, measure=lambda url: None))
		self.assertIsNone(logo_reads("", BROWN, measure=seen))
		self.assertIsNone(logo_reads("/f.png", "", measure=seen))

	def test_a_palette_variable_is_resolved(self):
		self.assertIs(
			logo_reads("/f.png", "var(--tb-primary)", {"tb-primary": BROWN}, measure=lambda url: flat(NAVY)),
			False,
		)


@unittest.skipIf(Image is None, "Pillow is not installed here")
class TestLogoInk(unittest.TestCase):
	def test_the_ink_is_the_colour_of_the_mark_not_of_the_empty_canvas(self):
		ink = ink_of(drawn(NAVY))
		self.assertTrue(ink)
		self.assertTrue(all(near(c, NAVY) for c in ink), set(ink))

	def test_a_logo_on_its_own_plate_carries_its_ground(self):
		self.assertIsNone(ink_of(drawn(NAVY, background=(*CREAM, 255), box=(40, 10, 80, 30))))

	def test_an_empty_file_has_nothing_to_measure(self):
		self.assertIsNone(ink_of(Image.new("RGBA", (120, 40), (0, 0, 0, 0))))

	def test_a_stray_pixel_is_no_logo(self):
		image = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
		image.putpixel((3, 3), (*NAVY, 255))
		self.assertIsNone(ink_of(image))

	def test_the_dark_mark_of_a_transparent_file_is_lost_on_a_dark_footer(self):
		ink = ink_of(drawn(NAVY))
		self.assertIs(logo_reads("/f.png", BROWN, measure=lambda url: ink), False)
		self.assertIs(logo_reads("/f.png", PAPER, measure=lambda url: ink), True)

	def test_the_black_pixels_stored_under_transparency_are_not_ink(self):
		"""An RGBA file stores a colour under a transparent pixel (often black); counting it made every
		transparent logo look dark."""
		ink = ink_of(drawn(CREAM))
		self.assertTrue(ink)
		self.assertTrue(all(near(c, CREAM) for c in ink), set(ink))


class TestSettlingTheChrome(unittest.TestCase):
	"""Light header, dark footer: the shape of the four test builds."""

	def test_a_dark_logo_leaves_a_dark_footer_for_the_site_name_and_stays_in_the_light_header(self):
		config = chrome()
		changes = settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(config.footer_logo_type, "Text")
		self.assertEqual(config.logo_type, "Image")
		self.assertEqual(len(changes), 1)
		self.assertIn("footer", changes[0])

	def test_the_logo_file_stays_on_the_config(self):
		config = chrome()
		settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(config.footer_logo_image, "/files/logo-default.png")

	def test_a_dark_logo_on_a_dark_header_is_replaced_in_the_header_too(self):
		config = chrome(header_bg_color=BROWN)
		changes = settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Text", "Text"))
		self.assertEqual(len(changes), 2)

	def test_a_light_logo_on_a_light_footer_is_replaced(self):
		config = chrome(footer_bg_color=PAPER)
		settle_chrome_logos(config, measure=lambda url: flat(CREAM))
		self.assertEqual(config.footer_logo_type, "Text")

	def test_a_logo_that_reads_everywhere_is_left_alone(self):
		config = chrome()
		self.assertEqual(settle_chrome_logos(config, measure=lambda url: flat(MID_GREY)), [])
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Image", "Image"))

	def test_an_unreadable_file_is_left_alone(self):
		config = chrome()
		self.assertEqual(settle_chrome_logos(config, measure=lambda url: None), [])
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Image", "Image"))

	def test_an_empty_footer_ground_is_the_header_s_then_white(self):
		"""get_footer_colors: footer_bg_color, else header_bg_color, else white."""
		config = chrome(footer_bg_color="", header_bg_color=BROWN)
		settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(config.footer_logo_type, "Text")
		config = chrome(footer_bg_color="", header_bg_color="")
		settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(config.footer_logo_type, "Image")
		self.assertEqual(config.logo_type, "Text", "an empty header is the doctype's #1a1a1a")

	def test_a_footer_that_follows_the_header_is_measured_on_its_own_ground(self):
		config = chrome(footer_logo_type="Same as Header", footer_logo_image="")
		settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(config.footer_logo_type, "Text")
		self.assertEqual(config.logo_type, "Image")

	def test_the_footer_s_own_mark_is_measured_not_the_header_s(self):
		marks = {"/files/wordmark.png": flat(NAVY), "/files/emblem.png": flat(CREAM)}
		config = chrome(logo_image="/files/wordmark.png", footer_logo_image="/files/emblem.png")
		settle_chrome_logos(config, measure=marks.get)
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Image", "Image"))

	def test_a_text_logo_or_a_hidden_footer_logo_has_nothing_to_measure(self):
		config = chrome(logo_type="Text", footer_logo_type="Text")
		self.assertEqual(settle_chrome_logos(config, measure=lambda url: flat(NAVY)), [])
		config = chrome(show_footer_logo=0)
		self.assertEqual(settle_chrome_logos(config, measure=lambda url: flat(NAVY)), [])
		self.assertEqual(config.footer_logo_type, "Image")

	def test_settling_twice_changes_nothing_more(self):
		config = chrome(header_bg_color=BROWN)
		settle_chrome_logos(config, measure=lambda url: flat(NAVY))
		self.assertEqual(settle_chrome_logos(config, measure=lambda url: flat(NAVY)), [])
