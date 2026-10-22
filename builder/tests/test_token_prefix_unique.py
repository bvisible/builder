# //// Neoffice — added file (no upstream equivalent): two sites of one instance never share the tokens of their colours.
"""The prefix of a site's tokens is the initials of its name, and the tokens of a prefix are the colours and the fonts of whichever
site holds it: "Chez Paul" and "Café Pierre" are both `cp`, and the build of the second rewrote the six tokens of the first
(2026-10-22; found on test profiles that shared their initials). unique_token_prefix gives a site another prefix when the chrome of
ANOTHER site holds its initials, the same one on every rebuild, and keeps the initials of a site that already holds them."""

import unittest
from unittest.mock import patch

from builder.site_ai.nora.site_builder import token_prefix, unique_token_prefix

VARIANT = "Website Header Footer Variant"
SINGLE = "Website Header Footer Config"


def run(profile, name, variants=(), single_prefix="", fail=False):
	with patch("builder.site_ai.nora.site_builder.frappe") as mock_frappe:
		mock_frappe.db.exists.return_value = True
		mock_frappe.get_all.return_value = list(variants)
		mock_frappe.db.get_single_value.return_value = single_prefix
		if fail:
			mock_frappe.get_all.side_effect = RuntimeError("no table")
		return unique_token_prefix(name, profile)


class TestAPrefixNoOtherSiteHolds(unittest.TestCase):
	def test_nobody_holds_it(self):
		self.assertEqual("cp", run("Chez Paul", "Chez Paul"))

	def test_a_site_that_holds_its_initials_keeps_them(self):
		self.assertEqual("cp", run("Chez Paul", "Chez Paul", variants=["Chez Paul"]))

	def test_the_instance_wide_chrome_keeps_its_initials_when_it_builds(self):
		self.assertEqual("cp", run(None, "Chez Paul", single_prefix="cp"))

	def test_a_database_that_cannot_answer_gives_the_initials(self):
		self.assertEqual("cp", run("Chez Paul", "Chez Paul", fail=True))


class TestAPrefixAnotherSiteHolds(unittest.TestCase):
	def test_the_second_site_takes_a_suffix_of_its_own(self):
		got = run("Café Pierre", "Café Pierre", variants=["Chez Paul"])
		self.assertTrue(got.startswith("cp") and got != "cp" and len(got) == 5, got)

	def test_the_same_site_gets_the_same_prefix_on_every_rebuild(self):
		a = run("Café Pierre", "Café Pierre", variants=["Chez Paul"])
		b = run("Café Pierre", "Café Pierre", variants=["Chez Paul"])
		self.assertEqual(a, b)

	def test_two_sites_that_collided_before_this_both_leave_the_initials(self):
		both = ["Chez Paul", "Café Pierre"]
		self.assertNotEqual("cp", run("Chez Paul", "Chez Paul", variants=both))
		self.assertNotEqual(run("Chez Paul", "Chez Paul", variants=both), run("Café Pierre", "Café Pierre", variants=both))

	def test_the_instance_wide_chrome_holding_the_initials_counts_as_another_site(self):
		self.assertNotEqual("cp", run("Café Pierre", "Café Pierre", single_prefix="cp"))

	def test_the_prefix_stays_a_token_name(self):
		got = run("Café Pierre", "Café Pierre", variants=["Chez Paul"])
		self.assertRegex(got, r"^[a-z0-9]+$")
		self.assertEqual("cp", token_prefix("Café Pierre"))


if __name__ == "__main__":
	unittest.main()
