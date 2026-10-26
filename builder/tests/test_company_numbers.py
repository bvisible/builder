# //// Neoffice — added file (no upstream equivalent): the identification and VAT numbers of the company reach the legal pages.
"""A legal notice said "[à compléter : numéro IDE et TVA]" for numbers the company record holds (2026-10-26). What is pinned here: the Swiss
UID is read from the UID-BFS field, else from the Tax ID when it is one, and written the way it is printed; a company liable to VAT states its
VAT number (the UID, with its suffix), one that is not does not; a site that names itself under another legal name states none of the
company's; the page writer is given the numbers and told never to leave a blank. No model, no database: the company record is replaced."""

import unittest
from unittest.mock import patch

import frappe

from builder import api


def company(**values):
	base = {"company_name": "Atelier Test Sàrl", "tax_id": "", "ch_uid_bfs": "", "is_vat_company": 0, "phone_no": "", "email": "", "website": "", "company_logo": ""}
	return frappe._dict({**base, **values})


def context(record, chrome=None):
	"""get_site_contact_context with the company record and the site's chrome replaced."""
	from unittest.mock import MagicMock

	db = MagicMock()
	db.get_default.return_value = record.company_name
	db.get_value.return_value = None
	with (
		patch.object(api.frappe, "db", db),
		patch.object(api.frappe, "get_doc", return_value=record),
		patch.object(api, "_get_site_chrome_config", return_value=frappe._dict(chrome or {})),
	):
		return api.get_site_contact_context()


class TestTheSwissNumber(unittest.TestCase):
	def test_it_is_written_the_way_it_is_printed(self):
		for written in ("CHE-123.456.789", "CHE123456789", "che 123 456 789", "CHE-123.456.789 TVA", " CHE-123.456.789 MWST "):
			self.assertEqual("CHE-123.456.789", api.swiss_uid(written), written)

	def test_what_is_not_a_swiss_number_is_not_one(self):
		for other in ("", None, "FR12345678901", "123.456.789", "CHE-123.456", "CHE-123.456.789.1", "see the register", 0):
			self.assertEqual("", api.swiss_uid(other), repr(other))


class TestTheContactDataCarriesThem(unittest.TestCase):
	def test_the_tax_id_is_the_number_when_it_is_one(self):
		data = context(company(tax_id="CHE-123.456.789", is_vat_company=1))
		self.assertEqual("CHE-123.456.789", data["uid"])
		self.assertIs(True, data["vat_registered"])

	def test_the_uid_field_wins_over_the_tax_id(self):
		data = context(company(tax_id="CHE-111.111.111", ch_uid_bfs="CHE-222.222.222"))
		self.assertEqual("CHE-222.222.222", data["uid"])

	def test_a_company_that_owes_no_vat_states_no_vat(self):
		data = context(company(tax_id="CHE-123.456.789", is_vat_company=0))
		self.assertEqual("CHE-123.456.789", data["uid"])
		self.assertNotIn("vat_registered", data)

	def test_a_tax_id_that_is_not_a_swiss_number_gives_none(self):
		data = context(company(tax_id="FR12345678901", is_vat_company=1))
		self.assertNotIn("uid", data)
		self.assertNotIn("vat_registered", data, "a VAT number is the UID's: without it there is none to state")

	def test_a_site_under_another_legal_name_states_none_of_the_companys(self):
		data = context(company(tax_id="CHE-123.456.789", is_vat_company=1), chrome={"business_name": "A Shop SA"})
		self.assertEqual("A Shop SA", data["company_name"])
		self.assertNotIn("uid", data)
		self.assertNotIn("vat_registered", data)


class TestTheWriterIsGivenThem(unittest.TestCase):
	def test_the_numbers_are_in_the_business_data(self):
		text = api._contact_context_prompt({"company_name": "X", "uid": "CHE-123.456.789", "vat_registered": True})
		self.assertIn("Company identification number (UID): CHE-123.456.789", text)
		self.assertIn("VAT number: CHE-123.456.789 TVA", text)

	def test_a_company_that_owes_no_vat_gets_no_vat_line(self):
		text = api._contact_context_prompt({"company_name": "X", "uid": "CHE-123.456.789"})
		self.assertIn("UID", text)
		self.assertNotIn("VAT number", text)

	def test_the_writer_is_never_offered_a_placeholder(self):
		text = api._contact_context_prompt({"company_name": "X"})
		self.assertIn("never a placeholder", text)
		self.assertNotIn("neutral placeholder", text)

	def test_the_legal_page_instruction_forbids_a_blank_and_gives_the_host(self):
		import inspect

		from builder.site_ai.nora import site_builder

		source = inspect.getsource(site_builder.page_brief_text)
		self.assertIn("NEVER leave a placeholder, a blank, a square bracket", source)
		self.assertNotIn("à compléter", source)
		self.assertNotIn("to be completed", source)
		self.assertIn("SUBPROCESSORS", source)


if __name__ == "__main__":
	unittest.main()
