# //// Neoffice — added file (no upstream equivalent): whether the site being rendered is a shop (site_legal.sells).
"""A profile of kind Showcase does not sell: the account menu of its signed-in visitors holds no orders and no wishlist. A profile of
another kind does, a gated profile does whatever its kind, and the host site, which has no profile, does as it always did. No database."""

import unittest
from unittest.mock import MagicMock, patch

from builder import site_legal


def sells(profile, kind=None, gated=0, known=True):
	db = MagicMock()
	db.exists.return_value = known
	db.get_value.return_value = (kind, gated)
	with patch.object(site_legal.frappe, "db", db):
		return site_legal._sells(profile)


class TestWhetherTheSiteIsAShop(unittest.TestCase):
	def test_a_showcase_profile_does_not_sell(self):
		self.assertFalse(sells("A site", "Showcase"))

	def test_a_storefront_profile_sells(self):
		self.assertTrue(sells("A site", "B2C"))
		self.assertTrue(sells("A site", "B2B"))

	def test_a_gated_profile_sells_whatever_its_kind(self):
		self.assertTrue(sells("A site", "Showcase", gated=1))

	def test_the_host_site_has_no_profile_and_sells_as_before(self):
		self.assertTrue(sells(None))
		self.assertTrue(sells(""))

	def test_a_profile_that_is_not_found_or_has_no_kind_sells_as_before(self):
		self.assertTrue(sells("A site", "Showcase", known=False))
		self.assertTrue(sells("A site", None))

	def test_a_database_that_fails_does_not_fail_the_page(self):
		db = MagicMock()
		db.exists.side_effect = RuntimeError("down")
		with patch.object(site_legal.frappe, "db", db):
			self.assertTrue(site_legal._sells("A site"))


if __name__ == "__main__":
	unittest.main()
