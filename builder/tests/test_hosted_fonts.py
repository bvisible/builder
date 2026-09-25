# //// Neoffice — added file (no upstream equivalent): tests of the site's own copy of its Google fonts (D-10).
"""The fonts a public page links are the site's own copy: fetched once from Google, server side,
rewritten to point at the site's files, and never linked from Google, not even when the copy
fails. No network: Google is stood in for."""

import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch

import builder
from builder import hosted_fonts

GOOGLE_URL = "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
CSS = """/* latin-ext */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/inter/v18/latin-ext.woff2) format('woff2');
  unicode-range: U+0100-02BA;
}
/* latin */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/inter/v18/latin.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}
"""


class Response:
	def __init__(self, text="", content=b"", status=200):
		self.text, self.content, self.status_code = text, content, status

	def raise_for_status(self):
		if self.status_code >= 400:
			raise RuntimeError(f"HTTP {self.status_code}")


class Google:
	"""Answers the stylesheet and its font files, and counts the calls."""

	def __init__(self, css=CSS, font_status=200):
		self.css, self.font_status = css, font_status
		self.calls = []

	def get(self, url, headers=None, timeout=None):
		self.calls.append(url)
		if url.startswith(hosted_fonts.GOOGLE_CSS):
			return Response(text=self.css)
		return Response(content=b"wOF2" + url.encode(), status=self.font_status)


class FontsTestCase(unittest.TestCase):
	def setUp(self):
		self.folder = tempfile.mkdtemp()
		self.failures = set()
		self.patches = [
			patch.object(hosted_fonts, "font_folder", return_value=self.folder),
			patch.object(hosted_fonts, "recently_failed", side_effect=lambda name: name in self.failures),
			patch.object(hosted_fonts, "remember_failure", side_effect=self.failures.add),
			patch.object(hosted_fonts.frappe, "log_error"),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()
		shutil.rmtree(self.folder, ignore_errors=True)

	def serve(self, **kw):
		google = Google(**kw)
		return google, patch("requests.get", side_effect=google.get)

	def stored(self, url: str) -> str:
		return pathlib.Path(self.folder, url.rsplit("/", 1)[1]).read_text()


class TestTheCopy(FontsTestCase):
	"""The page links the site's copy, and the copy names only the site's files."""

	def test_the_page_links_the_site_not_google(self):
		google, serving = self.serve()
		with serving:
			url = hosted_fonts.local_url(GOOGLE_URL)
		self.assertTrue(url.startswith("/files/builder_fonts/playfair-display-inter-"))
		css = self.stored(url)
		self.assertNotIn("gstatic", css)
		self.assertEqual(css.count("url(/files/builder_fonts/"), 2)
		self.assertEqual(len(google.calls), 3)
		self.assertEqual(len(list(pathlib.Path(self.folder).glob("*.woff2"))), 2)

	def test_a_stylesheet_is_copied_once(self):
		google, serving = self.serve()
		with serving:
			first = hosted_fonts.local_url(GOOGLE_URL)
			calls = len(google.calls)
			self.assertEqual(hosted_fonts.local_url(GOOGLE_URL), first)
		self.assertEqual(len(google.calls), calls)

	def test_a_font_file_already_there_is_not_fetched_again(self):
		google, serving = self.serve()
		other = GOOGLE_URL.replace("Playfair+Display", "Lora")
		with serving:
			hosted_fonts.local_url(GOOGLE_URL)
			hosted_fonts.local_url(other)
		self.assertEqual(len(google.calls), 4)


class TestWhenTheCopyFails(FontsTestCase):
	"""Nothing is linked from Google, nothing half-written is linked, and the retry waits."""

	def test_a_failed_copy_links_nothing_and_waits_before_trying_again(self):
		google, serving = self.serve(font_status=500)
		with serving:
			self.assertIsNone(hosted_fonts.local_url(GOOGLE_URL))
			calls = len(google.calls)
			self.assertIsNone(hosted_fonts.local_url(GOOGLE_URL))
		self.assertEqual(len(google.calls), calls)
		self.assertEqual(list(pathlib.Path(self.folder).glob("*.css")), [])

	def test_what_could_not_be_copied_is_dropped_and_other_urls_pass(self):
		_google, serving = self.serve(font_status=500)
		with serving:
			self.assertEqual(hosted_fonts.local_urls([GOOGLE_URL, "/files/own-font.css"]), ["/files/own-font.css"])

	def test_a_font_file_outside_google_is_refused(self):
		_google, serving = self.serve(css=CSS.replace("https://fonts.gstatic.com/s/inter/v18/latin.woff2", "https://example.com/x.woff2"))
		with serving:
			self.assertIsNone(hosted_fonts.local_url(GOOGLE_URL))
		self.assertEqual(list(pathlib.Path(self.folder).glob("*.css")), [])

	def test_a_stylesheet_without_font_files_is_refused(self):
		_google, serving = self.serve(css="/* nothing */")
		with serving:
			self.assertIsNone(hosted_fonts.local_url(GOOGLE_URL))


class TestTheChrome(FontsTestCase):
	"""The chrome asks one stylesheet for its two fonts, and links only what it is given."""

	def test_one_request_for_two_fonts(self):
		self.assertEqual(hosted_fonts.chrome_font_url("Playfair Display", "Inter"), GOOGLE_URL)

	def test_one_family_when_both_are_the_same(self):
		self.assertEqual(
			hosted_fonts.chrome_font_url("Inter", "Inter"),
			"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
		)
		self.assertEqual(hosted_fonts.chrome_font_url(None, None), hosted_fonts.chrome_font_url("Inter", "Inter"))

	def test_names_are_readable_and_stable(self):
		name = hosted_fonts.stylesheet_name(GOOGLE_URL)
		self.assertTrue(name.startswith("playfair-display-inter-") and name.endswith(".css"))
		self.assertEqual(name, hosted_fonts.stylesheet_name(GOOGLE_URL))
		self.assertNotEqual(name, hosted_fonts.stylesheet_name(GOOGLE_URL.replace("400;", "300;")))

	def test_the_chrome_links_the_site_s_copy(self):
		from builder.hf_utils import header_footer

		class Config:
			def get_theme_data(self):
				return {"heading_font": "Playfair Display", "body_font": "Inter", "background_color": "#ffffff", "text_color": "#1a1a1a", "primary_color": "#6c5ce7", "secondary_color": "#00b894"}

		with patch.object(hosted_fonts, "local_url", return_value="/files/builder_fonts/playfair-display-inter-0.css") as copy:
			css = header_footer.get_theme_css(Config())
		copy.assert_called_once_with(GOOGLE_URL)
		self.assertIn('<link rel="stylesheet" href="/files/builder_fonts/playfair-display-inter-0.css">', css)
		self.assertNotIn("https://fonts.g", css)


class TestNoPublicTemplateNamesGoogle(unittest.TestCase):
	"""A merge that brings a Google font link back into a template fails here."""

	def test_templates(self):
		root = pathlib.Path(builder.__file__).parent / "templates"
		found = [
			str(path.relative_to(root))
			for path in root.rglob("*.html")
			if "https://fonts.googleapis.com" in path.read_text() or "https://fonts.gstatic.com" in path.read_text()
		]
		self.assertEqual(found, [])
