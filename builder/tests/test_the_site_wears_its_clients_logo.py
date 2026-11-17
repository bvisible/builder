# //// Neoffice — added file (no upstream equivalent): a site whose chrome has no logo picked wears the business's own
# //// logo (the file provisioning keeps at the stable path), not Neoffice's (found 2026-11-17: the header of a client's
# //// public site showed Neoffice's mark while the client's logo sat in the ERP).
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.builder.doctype.website_header_footer_config.website_header_footer_config import (
	WebsiteHeaderFooterConfig as Config,
)

NEOFFICE_LOGO = "/assets/neoffice_theme/images/neoffice_logo.svg"
STABLE_PATH = "/files/logo-default.png"


def header(**fields):
	chrome = {"logo_type": "Image", "logo_text": "A site", "logo_image": None}
	chrome.update(fields)
	return Config.get_logo_data(SimpleNamespace(**chrome))


def footer(**fields):
	chrome = {"footer_logo_type": "Image", "footer_logo_text": "A site", "footer_logo_image": None}
	chrome.update(fields)
	return Config.get_footer_logo_data(SimpleNamespace(**chrome))


class TestTheSiteWearsItsClientsLogo(unittest.TestCase):
	def setUp(self):
		self.folder = tempfile.mkdtemp()
		self.logo_file = os.path.join(self.folder, "logo-default.png")
		patcher = patch("builder.branding.logo_disk_path", return_value=self.logo_file)
		patcher.start()
		self.addCleanup(patcher.stop)

	def put_the_clients_logo(self, content=b"\x89PNG client logo"):
		with open(self.logo_file, "wb") as f:
			f.write(content)

	def test_without_a_logo_picked_the_header_wears_the_clients_logo(self):
		self.put_the_clients_logo()
		image = header()["image"]
		self.assertTrue(image.startswith(STABLE_PATH + "?v="), image)

	def test_the_footer_follows_the_same_order(self):
		self.put_the_clients_logo()
		self.assertTrue(footer()["image"].startswith(STABLE_PATH + "?v="))

	def test_a_logo_picked_in_the_chrome_still_wins(self):
		self.put_the_clients_logo()
		self.assertEqual("/files/picked.png", header(logo_image="/files/picked.png")["image"])
		self.assertEqual("/files/picked.png", footer(footer_logo_image="/files/picked.png")["image"])

	def test_with_no_logo_file_the_site_keeps_neoffices_mark(self):
		"""A site that has no logo of its own anywhere keeps what it wore before."""
		self.assertEqual(NEOFFICE_LOGO, header()["image"])
		self.assertEqual(NEOFFICE_LOGO, footer()["image"])

	def test_an_empty_logo_file_is_no_logo(self):
		self.put_the_clients_logo(b"")
		self.assertEqual(NEOFFICE_LOGO, header()["image"])

	def test_a_text_logo_keeps_its_type_and_text(self):
		self.put_the_clients_logo()
		data = header(logo_type="Text", logo_text="A name")
		self.assertEqual(("Text", "A name"), (data["type"], data["text"]))
