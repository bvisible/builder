# //// Neoffice — added file (no upstream equivalent): whose business a site is, asked once by Nora and kept on the site's record.
"""Whose business a site is decides what it may show: the instance company's contact details, team, history, opening hours and shop.

« A site with Nora » names the site's record after the site, and the guess of _other_business took every site created that way
for a brand of the instance's company: a beauty institute's test site showed the test company's name, telephone and address, and
a sports centre's classes (13.11, osiris). The name cannot tell a brand of the company from another business; the person can, once
(Jérémy, 14.11: « Nora le demande »).
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from builder.site_ai.nora import prompts, site_builder
from builder.site_ai.nora.site_builder import ANOTHER_BUSINESS, OUR_COMPANY


class Kept(Exception):
	"""Stops a build right after the answer was kept: what follows is the whole pipeline."""


def records(**profiles):
	"""frappe.db.get_value over Website Profile records given as {name: {field: value}}."""
	return lambda doctype, name, field: (profiles.get(name) or {}).get(field)


class TestWhoseBusiness(unittest.TestCase):
	def patched(self, profiles, company="Dupont & Fils SA", column=True):
		return mock.patch.multiple(
			site_builder.frappe.db,
			get_value=mock.Mock(side_effect=records(**profiles)),
			get_single_value=mock.Mock(return_value=company),
			has_column=mock.Mock(return_value=column),
		)

	def test_the_persons_answer_decides_before_the_name(self):
		profiles = {
			"Lumiere": {"title": "Lumiere", "site_business": ANOTHER_BUSINESS},
			"Sport": {"title": "Sport", "site_business": OUR_COMPANY},
		}
		with self.patched(profiles):
			# named after its record, it passed for a brand of the company: the answer says it is not
			self.assertTrue(site_builder._other_business("Lumiere", "Lumiere"))
			# a brand whose name is neither the company's nor its record's: the answer says it is one
			self.assertFalse(site_builder._other_business("Sport", "Le Club du Lac"))

	def test_a_site_never_asked_keeps_the_guess(self):
		with self.patched({"Beacons": {"title": "The 5 Beacons"}, "Test": {"title": "Test"}}):
			self.assertFalse(site_builder._other_business("Beacons", "The 5 Beacons"))
			self.assertTrue(site_builder._other_business("Test", "Acme Industrie SA"))

	def test_nora_asks_only_what_nobody_answered(self):
		profiles = {
			"Main": {"is_default": 1},
			"Lumiere": {"title": "Lumiere"},
			"Answered": {"title": "Answered", "site_business": ANOTHER_BUSINESS},
		}
		with self.patched(profiles):
			self.assertIsNone(site_builder.business_to_ask(None, "Lumiere"))
			self.assertIsNone(
				site_builder.business_to_ask("Main", "Lumiere"), "the default site is the company's"
			)
			self.assertIsNone(site_builder.business_to_ask("Answered", "Answered"), "asked once, never again")
			self.assertIsNone(
				site_builder.business_to_ask("Lumiere", "Dupont & Fils Sàrl"),
				"a site named as the company is its own",
			)
			self.assertEqual(site_builder.business_to_ask("Lumiere", "Institut Lumière"), "Dupont & Fils SA")
			self.assertEqual(site_builder.business_to_ask("Lumiere", ""), "Dupont & Fils SA")
		with self.patched({"Lumiere": {"title": "Lumiere"}}, company=""):
			self.assertEqual(
				site_builder.business_to_ask("Lumiere", "Institut Lumière"),
				"",
				"no company: asked all the same",
			)
		with self.patched({"Lumiere": {"title": "Lumiere"}}, column=False):
			self.assertIsNone(
				site_builder.business_to_ask("Lumiere", "Institut Lumière"),
				"a record that cannot keep it: no question",
			)

	def test_the_answer_is_read_in_any_form_the_model_gives_it(self):
		read = site_builder.instance_business_answer
		for value, expected in (
			(True, True),
			("true", True),
			("Oui", True),
			(False, False),
			("false", False),
			("non", False),
		):
			self.assertIs(read(value), expected, value)
		for value in (None, "", "maybe"):
			self.assertIsNone(read(value), value)

	def test_the_answer_is_kept_on_the_sites_record(self):
		with (
			mock.patch.object(site_builder.frappe.db, "has_column", return_value=True),
			mock.patch.object(site_builder.frappe.db, "set_value") as set_value,
		):
			site_builder.keep_business_answer("Lumiere", False)
			site_builder.keep_business_answer("Sport", True)
		set_value.assert_any_call("Website Profile", "Lumiere", "site_business", ANOTHER_BUSINESS)
		set_value.assert_any_call("Website Profile", "Sport", "site_business", OUR_COMPANY)


SPEC = {
	"site_name": "Institut Lumière",
	"activity": "Soins du visage à Vevey",
	"website_profile": "Lumiere",
	"pages": [],
}


class TestTheBuildAsksFirst(unittest.TestCase):
	def build(self, spec):
		with (
			mock.patch.object(site_builder.frappe.db, "exists", return_value=True),
			mock.patch.object(site_builder, "business_to_ask", return_value="Dupont & Fils SA"),
			mock.patch.object(site_builder, "keep_business_answer", side_effect=Kept) as kept,
		):
			try:
				return site_builder.build_site(SimpleNamespace(page_id=None, session_id=None), spec), kept
			except Kept:
				return None, kept

	def test_a_site_never_asked_is_not_built(self):
		answer, kept = self.build(dict(SPEC))
		self.assertTrue(answer.startswith("CONFIRM_NEEDED:"), answer)
		for words in (
			"« Institut Lumière »",
			"« Oui, Dupont & Fils SA »",
			"never « Institut Lumière »",
			"instance_business=true or false",
			"« Non, une autre entreprise »",
		):
			self.assertIn(words, answer)
		kept.assert_not_called()

	def test_the_answer_is_kept_before_the_build_goes_on(self):
		answer, kept = self.build({**SPEC, "instance_business": False})
		self.assertIsNone(answer, "the build went on past the question")
		kept.assert_called_once_with("Lumiere", False)


class TestThePlaybookAsks(unittest.TestCase):
	def line(self, company):
		with (
			mock.patch.object(prompts, "page_profile", return_value="Lumiere"),
			mock.patch.object(site_builder, "business_to_ask", return_value=company),
		):
			return prompts.business_line("page-1")

	def test_the_question_is_in_the_playbook_while_it_is_open(self):
		line = self.line("Dupont & Fils SA")
		# the company is named in the question and in its first answer, never the business just described (14.11)
		self.assertIn("This instance belongs to the company Dupont & Fils SA.", line)
		self.assertIn("« Oui, Dupont & Fils SA »", line)
		self.assertIn("never the business the person described", line)
		self.assertIn("instance_business=true or false", line)
		self.assertIn("Right after step 1", line)
		self.assertIn("go on with step 2", line)

	def test_the_question_comes_after_the_business_never_before_the_recap(self):
		# placed before the recap as « one last thing », it made the model jump over the logo and photographs card (14.11)
		with mock.patch.object(prompts, "business_line", return_value="1b. WHOSE"):
			text = prompts.site_playbook("page-1")
		self.assertLess(text.index("1. The business."), text.index("1b. WHOSE"))
		self.assertLess(text.index("1b. WHOSE"), text.index("2. The pages."))

	def test_nothing_is_asked_once_it_is_known(self):
		self.assertEqual(self.line(None), "")

	def test_the_tool_takes_the_answer(self):
		from builder.site_ai.nora import tools

		self.assertEqual(tools.generate_site.parameters["properties"]["instance_business"]["type"], "boolean")
