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


class ChromeDoc(Chrome):
	"""What apply_navigation asks of the chrome document, with the attributes it writes."""

	def set(self, key, value):
		setattr(self, key, value)

	def append(self, field, row):
		getattr(self, field).append(SimpleNamespace(**row))

	def save(self, **kwargs):
		self.saved = True


class Navigates:
	"""Drives apply_navigation, the last step of a build, on a stand-in for the chrome document."""

	def navigate(self, config, profile=None, single=None):
		"""`single` is what the host's Single (Website Header Footer Config) holds, read by the build
		to tell the logos a profile's Variant inherited from the ones the client chose."""
		from unittest.mock import patch

		from builder.site_ai.nora.site_builder import apply_navigation

		created = [
			{"name": "p1", "title": "Accueil", "route": "/"},
			{"name": "p2", "title": "La carte", "route": "/la-carte"},
		]
		with (
			patch("builder.site_ai.nora.site_builder._other_business", return_value=False),
			patch("builder.site_ai.nora.site_builder._profile_is_b2b", return_value=False),
			patch("builder.site_ai.nora.site_builder._profile_sells", return_value=False),
			patch("builder.site_ai.nora.site_builder.frappe") as frappe_mock,
			patch("builder.site_ai.logging.ai_log") as log,
			patch("builder.site_ai.nora.logo_contrast.ink_of_file", return_value=flat(NAVY)),
		):
			frappe_mock.db.get_single_value.side_effect = lambda doctype, field: (single or {}).get(field)
			apply_navigation(config, created, "vitrine", "a restaurant", profile, "fr", site_name="Test")
		return log

	def doc(self, **fields):
		return ChromeDoc(
			**{
				**vars(chrome(logo_text="Test", footer_logo_text="Test")),
				"menu_items": [],
				"footer_links": [],
				"footer_description": "",
				**fields,
			}
		)


class TestTheBuildSettlesTheLogos(Navigates, unittest.TestCase):
	"""The wiring: apply_navigation, the last step of a build, measures the logo it has just copied
	into the footer. The first real build after #1766's commit stopped on a NameError raised by the
	log line of this very branch, which no pure test reaches."""

	def test_a_dark_logo_copied_into_a_dark_footer_becomes_the_site_name_and_is_logged(self):
		config = self.doc()
		log = self.navigate(config)
		self.assertEqual(config.footer_logo_type, "Text")
		self.assertEqual(config.footer_logo_image, "/files/logo-default.png")
		self.assertEqual(config.logo_type, "Image")
		self.assertTrue(config.saved)
		self.assertIn("Chrome logo replaced by the site name", [call.args[1] for call in log.call_args_list])

	def test_a_footer_on_which_the_logo_reads_keeps_it(self):
		config = self.doc(footer_bg_color=PAPER)
		log = self.navigate(config)
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Image", "Image"))
		log.assert_not_called()


HOST_WORDMARK = "/files/logo-default.png"
HOST_EMBLEM = "/files/host-emblem.png"


class TestTheHostLogoNeverReachesAnotherSite(Navigates, unittest.TestCase):
	"""neoffice-maintenance #1773: a profile's Variant is bootstrapped from the host's Single, logos
	included. A build asked for no logo wipes the header's (step 2 of the build); the footer's, which
	differed from the wiped header's, then passed for a mark the client had chosen and stayed: the
	host's identity in the foot of another site, six times out of six on a throwaway profile."""

	def inherited(self, single, **fields):
		"""A Variant as `_get_site_chrome_config` bootstraps it from the Single, then as step 2 of the
		build leaves its header when the site has no logo of its own."""
		from builder.site_ai.nora.site_builder import keeps_own_logo

		variant = self.doc(
			**{
				"logo_type": "Image",
				"logo_image": single["logo_image"],
				"footer_logo_type": "Image",
				"footer_logo_image": single["footer_logo_image"],
				**fields,
			}
		)
		if not keeps_own_logo(variant.logo_type, variant.logo_image, single["logo_image"]):
			variant.logo_type, variant.logo_image = "Text", None
		return variant

	def test_a_variant_built_without_a_logo_of_its_own_ends_with_no_host_logo_anywhere(self):
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_WORDMARK}
		config = self.inherited(single)
		self.navigate(config, profile="A Profile", single=single)
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Text", "Text"))
		self.assertFalse(config.logo_image)
		self.assertFalse(config.footer_logo_image)
		self.assertTrue(config.saved)

	def test_a_host_with_a_wordmark_and_an_emblem_leaves_neither_in_the_variant(self):
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_EMBLEM}
		config = self.inherited(single)
		self.navigate(config, profile="A Profile", single=single)
		self.assertEqual((config.logo_type, config.footer_logo_type), ("Text", "Text"))
		self.assertEqual((config.logo_image or "", config.footer_logo_image or ""), ("", ""))

	def test_the_host_logo_parked_in_the_footer_by_an_earlier_build_is_cleared_too(self):
		"""The #1766 check parks a logo it cannot see ("Text", the file stays): a rebuild must not take
		the parked host file for the client's."""
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_WORDMARK}
		config = self.inherited(single, footer_logo_type="Text")
		self.navigate(config, profile="A Profile", single=single)
		self.assertEqual((config.footer_logo_type, config.footer_logo_image or ""), ("Text", ""))

	def test_nothing_is_left_for_the_contrast_check_to_replace(self):
		"""The contrast check measures what the footer carries; the footer no longer carries the host's
		logo, so it has nothing to measure and logs nothing."""
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_WORDMARK}
		config = self.inherited(single)
		log = self.navigate(config, profile="A Profile", single=single)
		self.assertNotIn(
			"Chrome logo replaced by the site name", [call.args[1] for call in log.call_args_list]
		)

	def test_a_logo_the_client_chose_for_the_header_is_shown_in_the_footer_instead_of_the_host_s(self):
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_WORDMARK}
		config = self.inherited(single, logo_image="/files/client-wordmark.svg", footer_bg_color=PAPER)
		self.navigate(config, profile="A Profile", single=single)
		self.assertEqual(config.logo_image, "/files/client-wordmark.svg")
		self.assertEqual(
			(config.footer_logo_type, config.footer_logo_image), ("Image", "/files/client-wordmark.svg")
		)

	def test_an_emblem_the_client_chose_for_the_footer_stays(self):
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_WORDMARK}
		config = self.inherited(single, footer_logo_image="/files/client-emblem.svg", footer_bg_color=PAPER)
		self.navigate(config, profile="A Profile", single=single)
		self.assertEqual(
			(config.footer_logo_type, config.footer_logo_image), ("Image", "/files/client-emblem.svg")
		)

	def test_the_host_s_own_site_keeps_its_logos(self):
		"""No profile: the chrome IS the Single's, and its logo is the client's own."""
		single = {"logo_image": HOST_WORDMARK, "footer_logo_image": HOST_EMBLEM}
		config = self.doc(
			logo_image=HOST_WORDMARK,
			footer_logo_image=HOST_EMBLEM,
			footer_bg_color=PAPER,
		)
		self.navigate(config, profile=None, single=single)
		self.assertEqual((config.logo_type, config.logo_image), ("Image", HOST_WORDMARK))
		self.assertEqual((config.footer_logo_type, config.footer_logo_image), ("Image", HOST_EMBLEM))
