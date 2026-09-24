# //// Neoffice — added file (no upstream equivalent): the site's icon (builder/site_icon.py).
# //// neoffice-maintenance#691 (D27, D28), 2026-09-24.
#
# Every page of a site names one icon, in a format Google reads: the one somebody chose, else a
# PNG drawn from the site's mark or initial, else Neoffice's. Before this, a Builder page fell
# back to Neoffice's SVG, the shop's pages of the same domain to another icon, and /favicon.ico
# answered 404.
import io
import json
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from PIL import Image

from builder import site_icon
from builder.hf_utils.header_footer import button_colours

THEME = {
	"primary_color": "#1d4ed8",
	"secondary_color": "#f59e0b",
	"background_color": "#ffffff",
	"text_color": "#1a1a1a",
}
SETTINGS = {"favicon": None, "app_name": "Frappe"}


class _Chrome(dict):
	"""Enough of a Website Header Footer Config for the icon: its fields and its theme."""

	def __init__(self, theme=None, **fields):
		super().__init__(fields)
		self.theme = theme or THEME

	def get_theme_data(self):
		return self.theme


class _SiteFiles:
	"""Pictures written to the site's public files for one test, removed after it."""

	def __init__(self):
		self.paths = []

	def picture(self, name, size, ink_box=None, ink=(200, 30, 30, 255), ground=(0, 0, 0, 0)):
		"""A PNG of `size`, `ground` everywhere and `ink` inside `ink_box`."""
		directory = frappe.get_site_path("public", "files")
		os.makedirs(directory, exist_ok=True)
		path = os.path.join(directory, name)
		image = Image.new("RGBA", size, ground)
		if ink_box:
			image.paste(ink, ink_box)
		image.save(path)
		self.paths.append(path)
		return f"/files/{name}"

	def remove(self):
		for path in self.paths:
			if os.path.exists(path):
				os.remove(path)


def _settings(**values):
	merged = {**SETTINGS, **values}
	return patch("builder.site_icon._website_setting", side_effect=lambda fieldname: merged.get(fieldname))


def _no_builder_icon():
	return patch("builder.site_icon._builder_setting", return_value=None)


def _png(data):
	return Image.open(io.BytesIO(data)).convert("RGBA")


class TestChosenIcon(unittest.TestCase):
	def test_the_page_then_builder_settings_then_website_settings(self):
		with (
			patch("builder.site_icon._builder_setting", return_value="/files/builder.png"),
			_settings(favicon="/files/website.png"),
		):
			self.assertEqual(site_icon.chosen_icon("/files/page.png"), "/files/page.png")
			self.assertEqual(site_icon.chosen_icon(None), "/files/builder.png")
		with _no_builder_icon(), _settings(favicon="/files/website.png"):
			self.assertEqual(site_icon.chosen_icon(None), "/files/website.png")
		with _no_builder_icon(), _settings(favicon="attach_files:"):
			self.assertEqual(site_icon.chosen_icon(None), "")

	def test_a_chosen_icon_is_linked_as_it_is(self):
		with _no_builder_icon(), _settings(favicon="/files/brand.ico"):
			icon = site_icon.site_icon()
		self.assertEqual(icon.href, "/files/brand.ico")
		self.assertEqual(icon.type, "image/x-icon")
		self.assertEqual(icon.source, "chosen")


class TestDrawnIcon(unittest.TestCase):
	def setUp(self):
		self.files = _SiteFiles()
		for patcher in (_no_builder_icon(), _settings()):
			patcher.start()
			self.addCleanup(patcher.stop)
		self.addCleanup(self.files.remove)

	def test_a_square_mark_in_the_footer_is_the_icon(self):
		emblem = self.files.picture("test-site-icon-emblem.png", (300, 300), (40, 40, 260, 260))
		wordmark = self.files.picture("test-site-icon-wordmark.png", (800, 200), (0, 0, 800, 200))
		chrome = _Chrome(
			footer_logo_type="Image", footer_logo_image=emblem, logo_type="Image", logo_image=wordmark
		)
		spec = site_icon.drawn_icon(chrome)
		self.assertEqual(spec.source, "mark")
		self.assertTrue(spec.path.endswith("test-site-icon-emblem.png"))

	def test_a_square_picture_drawing_a_wide_mark_is_not_a_mark(self):
		# a wordmark centred on a square transparent canvas: the ink is what counts
		logo = self.files.picture("test-site-icon-padded.png", (400, 400), (0, 150, 400, 250))
		chrome = _Chrome(logo_type="Image", logo_image=logo, logo_text="atelier nord")
		spec = site_icon.drawn_icon(chrome)
		self.assertEqual(spec.source, "initial")
		self.assertEqual(spec.letter, "A")

	def test_a_wordmark_gives_way_to_the_initial_on_the_button_colour(self):
		logo = self.files.picture("test-site-icon-wide.png", (900, 220), (0, 0, 900, 220))
		chrome = _Chrome(logo_type="Image", logo_image=logo, logo_text="  2 Rives & Co")
		spec = site_icon.drawn_icon(chrome)
		colours = button_colours(THEME)
		self.assertEqual((spec.source, spec.letter), ("initial", "2"))
		self.assertEqual((spec.background, spec.ink), (colours["cta_hex"], colours["cta_text"]))

	def test_a_site_with_no_name_of_its_own_gets_the_fallback(self):
		logo = self.files.picture("test-site-icon-wide2.png", (900, 220), (0, 0, 900, 220))
		for name in ("My Site", "", "Neoffice"):
			with self.subTest(name=name):
				spec = site_icon.drawn_icon(_Chrome(logo_type="Image", logo_image=logo, logo_text=name))
				self.assertEqual(spec.source, "fallback")
				self.assertTrue(os.path.isfile(spec.path))

	def test_the_website_settings_name_is_the_last_name(self):
		with _settings(app_name="Maison Test"):
			spec = site_icon.drawn_icon(_Chrome(logo_type="Text", logo_text=""))
		self.assertEqual((spec.source, spec.letter), ("initial", "M"))

	def test_a_picture_of_another_host_an_svg_or_a_private_file_is_not_drawn(self):
		for url in (
			"https://cdn.example.com/files/logo.png",
			"/files/logo.svg",
			"/private/files/logo.png",
			"/files/../site_config.json",
		):
			with self.subTest(url=url):
				self.assertIsNone(site_icon._public_file(url))

	def test_the_key_follows_the_file_and_the_colours(self):
		url = self.files.picture("test-site-icon-key.png", (200, 200), (20, 20, 180, 180))
		chrome = _Chrome(logo_type="Image", logo_image=url)
		before = site_icon.drawn_icon(chrome).key
		self.files.picture("test-site-icon-key.png", (240, 240), (20, 20, 220, 220))
		self.assertNotEqual(site_icon.drawn_icon(chrome).key, before)

		red = site_icon.drawn_icon(
			_Chrome(theme={**THEME, "primary_color": "#b91c1c"}, logo_type="Text", logo_text="Nord")
		)
		blue = site_icon.drawn_icon(_Chrome(logo_type="Text", logo_text="Nord"))
		self.assertNotEqual(red.key, blue.key)


class TestDrawing(unittest.TestCase):
	def setUp(self):
		self.files = _SiteFiles()
		self.addCleanup(self.files.remove)

	def test_an_initial_is_a_filled_square_with_its_letter_in_the_middle(self):
		spec = site_icon._spec("initial", letter="N", background="#1d4ed8", ink="#ffffff")
		picture = _png(site_icon._draw(spec))
		self.assertEqual(picture.size, (site_icon.ICON_SIZE, site_icon.ICON_SIZE))
		self.assertEqual(picture.getpixel((0, 0)), (0x1D, 0x4E, 0xD8, 255))
		letter = Image.eval(picture.convert("L"), lambda value: 255 if value > 200 else 0).getbbox()
		self.assertIsNotNone(letter)
		left, top, right, bottom = letter
		middle = site_icon.ICON_SIZE / 2
		self.assertLessEqual(abs((left + right) / 2 - middle), 4)
		self.assertLessEqual(abs((top + bottom) / 2 - middle), 4)
		self.assertGreater(bottom - top, site_icon.ICON_SIZE * 0.4)

	def test_a_mark_is_trimmed_and_centred(self):
		# drawn in the top-left corner of a large transparent canvas
		url = self.files.picture("test-site-icon-corner.png", (600, 600), (0, 0, 100, 100))
		spec = site_icon._spec("mark", path=site_icon._public_file(url))
		picture = _png(site_icon._draw(spec))
		self.assertEqual(picture.getpixel((0, 0))[3], 0)
		left, top, right, bottom = picture.getchannel("A").getbbox()
		expected = round(site_icon.ICON_SIZE * (1 - 2 * site_icon.MARK_PADDING))
		self.assertLessEqual(abs((right - left) - expected), 2)
		self.assertLessEqual(abs((left + right) / 2 - site_icon.ICON_SIZE / 2), 2)
		self.assertLessEqual(abs((top + bottom) / 2 - site_icon.ICON_SIZE / 2), 2)

	def test_a_mark_on_a_plain_ground_keeps_that_ground(self):
		url = self.files.picture(
			"test-site-icon-ground.png",
			(300, 300),
			(100, 100, 200, 200),
			ink=(20, 60, 200, 255),
			ground=(255, 255, 255, 255),
		)
		spec = site_icon._spec("mark", path=site_icon._public_file(url))
		picture = _png(site_icon._draw(spec))
		self.assertEqual(picture.getpixel((0, 0)), (255, 255, 255, 255))
		self.assertEqual(picture.getpixel((96, 96)), (20, 60, 200, 255))


class TestRoutes(unittest.TestCase):
	def setUp(self):
		self.form_dict = frappe.local.form_dict
		frappe.local.form_dict = frappe._dict()
		self.addCleanup(setattr, frappe.local, "form_dict", self.form_dict)

	def test_favicon_ico_and_site_icon_png_are_answered_here(self):
		for path, answered in (
			("favicon.ico", True),
			("/site-icon.png", True),
			("about", False),
			("icon.png", False),
		):
			with self.subTest(path=path):
				self.assertEqual(site_icon.SiteIconRenderer(path=path).can_render(), answered)

	def test_a_drawn_icon_is_served_as_a_png(self):
		spec = site_icon._spec("initial", letter="T", background="#0f766e", ink="#ffffff")
		with (
			patch("builder.site_icon.chosen_icon", return_value=""),
			patch("builder.site_icon.drawn_icon", return_value=spec),
		):
			response = site_icon.SiteIconRenderer(path="favicon.ico").render()
			self.assertEqual(response.status_code, 200)
			self.assertEqual(response.mimetype, "image/png")
			self.assertTrue(response.get_data().startswith(b"\x89PNG"))
			self.assertEqual(response.headers["Cache-Control"], "public, max-age=86400")

			frappe.local.form_dict = frappe._dict(v=spec.key)
			response = site_icon.SiteIconRenderer(path="site-icon.png").render()
			self.assertIn("immutable", response.headers["Cache-Control"])

	def test_a_chosen_icon_is_a_redirect(self):
		with patch("builder.site_icon.chosen_icon", return_value="/files/brand.ico"):
			response = site_icon.SiteIconRenderer(path="favicon.ico").render()
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.headers["Location"], "/files/brand.ico")


class TestPages(unittest.TestCase):
	ICON = frappe._dict(href="/site-icon.png?v=abc", type="image/png", sizes="192x192", source="initial")

	def setUp(self):
		self.request = getattr(frappe.local, "request", None)
		self.addCleanup(setattr, frappe.local, "request", self.request)

	def test_every_website_page_names_the_site_icon(self):
		frappe.local.request = SimpleNamespace(path="/all-products")
		context = frappe._dict(favicon="/assets/neoffice_theme/images/neoffice_icon.png")
		with patch("builder.site_icon.site_icon", return_value=self.ICON):
			site_icon.apply(context)
		self.assertEqual(context.favicon, self.ICON.href)

	def test_the_desk_keeps_its_own_icon(self):
		frappe.local.request = SimpleNamespace(path="/app/item")
		context = frappe._dict(favicon="/assets/neoffice_theme/images/neoffice_icon.png")
		with patch("builder.site_icon.site_icon", return_value=self.ICON):
			site_icon.apply(context)
		self.assertEqual(context.favicon, "/assets/neoffice_theme/images/neoffice_icon.png")

	def test_a_builder_page_icon_is_not_replaced(self):
		chosen = frappe._dict(href="/files/page.png", type="image/png", sizes="", source="chosen")
		context = frappe._dict(site_icon=chosen, favicon=chosen.href)
		with patch("builder.site_icon.site_icon", return_value=self.ICON):
			site_icon.apply(context)
		self.assertEqual(context.favicon, "/files/page.png")

	def test_a_builder_page_takes_its_own_favicon_first(self):
		page = frappe.new_doc("Builder Page")
		page.favicon = "/files/page-icon.png"
		context = frappe._dict()
		page.set_favicon(context)
		self.assertEqual(context.favicon, "/files/page-icon.png")
		self.assertEqual(context.site_icon.source, "chosen")

		page.favicon = None
		context = frappe._dict()
		with (
			patch("builder.site_icon.chosen_icon", return_value=""),
			patch(
				"builder.site_icon.drawn_icon",
				return_value=site_icon._spec("initial", letter="B", background="#000000", ink="#ffffff"),
			),
		):
			page.set_favicon(context)
		self.assertTrue(context.favicon.startswith("/site-icon.png?v="))


class TestWebpageTemplate(unittest.TestCase):
	"""The icon lines of webpage.html, rendered alone (the page needs far more context)."""

	def render(self, **context):
		from jinja2.sandbox import SandboxedEnvironment

		import builder

		path = os.path.join(os.path.dirname(builder.__file__), "templates", "generators", "webpage.html")
		with open(path) as template:
			source = template.read()
		lines = re.search(r"\{%- set icon = .*?apple-touch-icon[^\n]*", source, re.S)
		self.assertIsNotNone(lines, "webpage.html no longer carries the site icon lines")
		return SandboxedEnvironment().from_string(lines.group(0)).render(**context)

	def test_a_drawn_icon_is_named_as_a_png(self):
		html = self.render(
			site_icon=frappe._dict(href="/site-icon.png?v=abc", type="image/png", sizes="192x192")
		)
		self.assertIn('<link rel="icon" href="/site-icon.png?v=abc" type="image/png" sizes="192x192"/>', html)
		self.assertIn('<link rel="apple-touch-icon" href="/site-icon.png?v=abc"/>', html)
		self.assertNotIn("svg", html)

	def test_without_a_resolved_icon_the_page_still_names_a_png(self):
		html = self.render(site_icon=None, favicon=None)
		self.assertIn('href="/assets/neoffice_theme/images/neoffice_icon.png"', html)
		self.assertNotIn("svg", html)


if __name__ == "__main__":
	unittest.main()
