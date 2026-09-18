# //// Neoffice — added file (no upstream equivalent): the browser probes are JavaScript carried
# //// in Python strings, and nothing here parses them.
#
# A probe that does not parse throws in the page, measure_layout() catches it, and the build goes
# on with an empty finding list — a gate that reports "nothing wrong" about a page it never read.
# That is the worst failure this code can have, and a syntax error is enough to cause it. So the
# probes are parsed, by the same engine that will run them.
import os
import shutil
import subprocess
import tempfile
import unittest


class TestProbesParse(unittest.TestCase):
	def _check(self, source: str, name: str) -> None:
		node = shutil.which("node") or shutil.which("nodejs")
		if not node:
			self.skipTest("node is not installed here: the probes cannot be parsed")
		with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
			# the probe is an expression (an arrow function): bind it so the file is a module
			f.write(f"const probe = {source.strip()};\nexport default probe;\n")
			path = f.name
		try:
			done = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=30)
			self.assertEqual(0, done.returncode, f"{name} does not parse:\n{done.stderr[-800:]}")
		finally:
			os.unlink(path)

	def test_the_layout_probe_parses(self):
		from builder.site_ai.inspiration.screenshotter import LAYOUT_PROBE

		self._check(LAYOUT_PROBE, "LAYOUT_PROBE")

	def test_the_photo_text_probe_parses(self):
		from builder.site_ai.inspiration.screenshotter import PHOTO_TEXT_PROBE

		self._check(PHOTO_TEXT_PROBE, "PHOTO_TEXT_PROBE")
