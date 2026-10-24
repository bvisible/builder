# //// Neoffice — added file (no upstream equivalent): a generated site links no network it was not given.
"""A real build (a fiduciary, 2026-10-24) came with Instagram, LinkedIn and YouTube icons in its footer that all went to
"#": a profile's Variant is bootstrapped with every field of the host's Single, the generator never sets a social link,
and the host's placeholders (or its real networks) travelled to every site. No model is called."""

import unittest
from unittest.mock import MagicMock, patch

from builder.site_ai.nora import site_builder
from builder.site_ai.nora.site_builder import (
	SOCIAL_LINK_FIELDS,
	apply_navigation,
	drop_inherited_social_links,
)

HOST = {"instagram_url": "https://www.instagram.com/the-host", "youtube_url": "#"}


class Config:
	"""The two methods of a chrome doc the function uses."""

	def __init__(self, **values):
		self.values = {"show_social_links": 1, **values}

	def get(self, field, default=None):
		return self.values.get(field, default)

	def set(self, field, value):
		self.values[field] = value


class TestWhichLinksStay(unittest.TestCase):
	def test_placeholders_go_and_the_row_of_icons_with_them(self):
		config = Config(instagram_url="#", linkedin_url="#", youtube_url="#")
		cleared = drop_inherited_social_links(config, {})
		self.assertEqual(sorted(cleared), ["instagram_url", "linkedin_url", "youtube_url"])
		self.assertEqual(config.values["show_social_links"], 0)
		for field in SOCIAL_LINK_FIELDS:
			self.assertFalse(config.get(field))

	def test_the_hosts_own_network_is_not_the_clients(self):
		config = Config(instagram_url=HOST["instagram_url"])
		self.assertEqual(drop_inherited_social_links(config, HOST), ["instagram_url"])
		self.assertEqual(config.values["show_social_links"], 0)

	def test_a_link_the_owner_typed_stays_and_so_do_the_icons(self):
		config = Config(instagram_url="https://www.instagram.com/the-owner", linkedin_url="#")
		self.assertEqual(drop_inherited_social_links(config, HOST), ["linkedin_url"])
		self.assertEqual(config.get("instagram_url"), "https://www.instagram.com/the-owner")
		self.assertEqual(config.values["show_social_links"], 1)

	def test_an_address_that_is_not_http_is_dropped(self):
		config = Config(facebook_url="javascript:alert(1)", twitter_url="mailto:a@b.c")
		self.assertEqual(sorted(drop_inherited_social_links(config, {})), ["facebook_url", "twitter_url"])

	def test_nothing_to_drop_changes_nothing(self):
		config = Config(instagram_url="https://www.instagram.com/the-owner")
		self.assertEqual(drop_inherited_social_links(config, {}), [])
		self.assertEqual(config.values["show_social_links"], 1)
		empty = Config()
		self.assertEqual(drop_inherited_social_links(empty, HOST), [])
		self.assertEqual(empty.values["show_social_links"], 1)


class TestTheBuildAppliesIt(unittest.TestCase):
	"""Through apply_navigation, not beside it: a rule nobody calls is not a rule."""

	def navigate(self, values, profile="A Storefront", host=None):
		config = MagicMock()
		config.menu_items = []
		config.append.side_effect = lambda field, row: config.menu_items.append(type("Row", (), row)) if field == "menu_items" else None
		stored = {"show_social_links": 1, **values}
		config.get.side_effect = lambda field, default=None: stored.get(field, default)
		config.set.side_effect = stored.__setitem__
		created = [{"name": "p1", "title": "Home", "route": "/"}, {"name": "p2", "title": "Contact", "route": "/contact"}]
		with patch.object(site_builder, "_other_business", return_value=False), patch.object(
			site_builder, "_profile_is_b2b", return_value=False
		), patch.object(site_builder, "_profile_sells", return_value=False), patch.object(
			site_builder, "legal_pages", return_value=[]
		), patch.object(site_builder, "_host_social_links", return_value=host or {}), patch.object(site_builder, "frappe") as mock_frappe:
			mock_frappe.get_installed_apps.return_value = ["frappe", "builder"]
			apply_navigation(config, created, "showcase", "a fiduciary", profile, "fr")
		return stored

	def test_a_variant_loses_the_placeholders_it_inherited(self):
		stored = self.navigate({"instagram_url": "#", "linkedin_url": "#", "youtube_url": "#"})
		self.assertEqual(stored["show_social_links"], 0)
		self.assertEqual([stored.get(f) for f in ("instagram_url", "linkedin_url", "youtube_url")], ["", "", ""])

	def test_a_variant_loses_the_hosts_network_but_keeps_its_own(self):
		stored = self.navigate(
			{"instagram_url": HOST["instagram_url"], "linkedin_url": "https://www.linkedin.com/company/the-owner"}, host=HOST
		)
		self.assertEqual(stored["instagram_url"], "")
		self.assertEqual(stored["linkedin_url"], "https://www.linkedin.com/company/the-owner")
		self.assertEqual(stored["show_social_links"], 1)
