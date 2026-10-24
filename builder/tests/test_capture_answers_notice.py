# //// Neoffice — added file (no upstream equivalent): the generator's captures answer the cookie notice first.
"""The cookie notice is fixed at the foot of the viewport. On a full-page capture of a short page it sat over the last lines of the
article, and the reviewer revised a restaurant's terms page to fix it (2026-10-24). A visitor closes the notice once; the loopback
captures of the generator do the same, with the key the template reads. No browser is started here."""

import inspect
import re
import unittest
from pathlib import Path

from builder.site_ai.inspiration import screenshotter

TEMPLATE = Path(screenshotter.__file__).parents[2] / "templates" / "includes" / "data_notice.html"


class TestTheCaptureAnswersTheNotice(unittest.TestCase):
	def test_the_key_is_the_one_the_template_reads(self):
		key = re.search(r'var KEY = "([^"]+)"', TEMPLATE.read_text()).group(1)
		self.assertIn(f"'{key}'", screenshotter.NOTICE_ANSWERED_SCRIPT)
		self.assertIn("setItem", screenshotter.NOTICE_ANSWERED_SCRIPT)

	def test_the_script_cannot_break_a_page(self):
		"""A page that forbids storage must still be captured."""
		self.assertTrue(screenshotter.NOTICE_ANSWERED_SCRIPT.startswith("try {"))
		self.assertIn("catch", screenshotter.NOTICE_ANSWERED_SCRIPT)

	def test_both_loopback_paths_use_it_and_only_with_headers(self):
		"""The page capture and the layout measure render our own site through the loopback (headers); a reference site of a client
		does not pass headers and must be left exactly as it is."""
		for function in (screenshotter.WebsiteScreenshotter.capture_async, screenshotter._measure_async):
			lines = inspect.getsource(function).splitlines()
			start = next(n for n, line in enumerate(lines) if line.strip() == "if headers:")
			indent = len(lines[start]) - len(lines[start].lstrip())
			body = []
			for line in lines[start + 1 :]:
				if line.strip() and len(line) - len(line.lstrip()) <= indent:
					break
				body.append(line)
			self.assertTrue(any("add_init_script(NOTICE_ANSWERED_SCRIPT)" in line for line in body), function.__qualname__)
			self.assertEqual(sum("NOTICE_ANSWERED_SCRIPT" in line for line in lines), 1, function.__qualname__)
