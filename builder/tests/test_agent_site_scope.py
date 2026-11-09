# //// Neoffice — added file (no upstream equivalent): the agent's read tools know which site of the
# //// instance they work for, so a page of another site is never taken for the site's own
# //// (neoffice-maintenance#474).
"""The agent's read tools on an instance that hosts two sites.

Two sites, A and B, both have a home page on the route "/" titled "Accueil"; B's is the more
recently touched. Before this guard `resolve_page_reference("/")` answered with B's page for an
agent working on A, `query_records` listed B's pages as if they were A's, and the agent once told
the operator to delete another client's home page.

The tests need no site and no Website Profile column: the few frappe calls the tools make are
answered by an in-memory table of Builder Pages (the column does not exist on a bench without
neoffice_theme).
"""

import json
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.ai.agent.tools import data, query

SITE_A = "Site A"
SITE_B = "Site B"
OTHER_SITE_KEY = "belongs_to_another_site"
WARNING = "THIS PAGE BELONGS TO ANOTHER SITE"

PAGES = {
	"page-a-home": {
		"page_title": "Accueil",
		"route": "/",
		"published": 1,
		"modified": 1,
		"neo_website_profile": SITE_A,
	},
	"page-a-about": {
		"page_title": "A propos",
		"route": "a-propos",
		"published": 1,
		"modified": 1,
		"neo_website_profile": SITE_A,
	},
	# the more recently touched home page: the one an unscoped lookup returns
	"page-b-home": {
		"page_title": "Accueil",
		"route": "/",
		"published": 1,
		"modified": 2,
		"neo_website_profile": SITE_B,
	},
	"page-b-team": {
		"page_title": "Equipe",
		"route": "equipe",
		"published": 1,
		"modified": 1,
		"neo_website_profile": SITE_B,
	},
	# untagged: shared, serves everywhere
	"page-shared": {
		"page_title": "Index",
		"route": "index",
		"published": 1,
		"modified": 0,
		"neo_website_profile": None,
	},
}


class Row(dict):
	__getattr__ = dict.get


class FakeBuilderPages:
	"""An in-memory Builder Page table behind the frappe calls the agent's read tools make."""

	def __init__(self, has_column=True):
		self.has_column = has_column
		self.listed_with = []

	def matches(self, row, filters):
		for key, wanted in (filters or {}).items():
			have = row.get(key)
			if isinstance(wanted, (tuple, list)):
				operator, value = wanted
				if operator == "in":
					found = have in value
				elif operator == "is" and value == "not set":
					found = not have
				else:
					raise AssertionError(f"filter operator not faked: {wanted}")
			else:
				found = have == wanted
			if not found:
				return False
		return True

	def select(self, filters):
		rows = [Row(name=name, **row) for name, row in PAGES.items() if self.matches(row, filters)]
		# the order the tools ask for: published first, then the most recently touched
		return sorted(rows, key=lambda r: (r["published"], r["modified"]), reverse=True)

	# --- the frappe calls -------------------------------------------------------

	def exists(self, doctype, name=None):
		return True if doctype == "DocType" else name in PAGES

	def get_value(self, doctype, filters=None, fieldname="name", ignore=None, as_dict=False, **kwargs):
		if isinstance(filters, str):
			row = PAGES.get(filters)
			if row is None:
				return None
			if as_dict:
				return Row(**row)
			if isinstance(fieldname, (list, tuple)):
				return tuple(row.get(f) for f in fieldname)
			return row.get(fieldname)
		found = self.select(filters)
		return found[0][fieldname] if found else None

	def get_all(self, doctype, filters=None, order_by=None, limit=None, pluck=None, **kwargs):
		found = self.select(filters)[: limit or None]
		return [row["name"] for row in found] if pluck == "name" else found

	def get_list(self, doctype, filters=None, fields=None, limit=None):
		self.listed_with.append(fields)
		columns = None if "*" in fields else fields
		return [
			Row({k: v for k, v in row.items() if columns is None or k in columns})
			for row in self.select(filters)
		]

	def patches(self, profile_of_the_request=None):
		stack = ExitStack()
		stack.enter_context(patch.object(frappe.db, "has_column", return_value=self.has_column))
		stack.enter_context(patch.object(frappe.db, "exists", side_effect=self.exists))
		stack.enter_context(patch.object(frappe.db, "get_value", side_effect=self.get_value))
		stack.enter_context(patch.object(frappe, "get_all", side_effect=self.get_all))
		stack.enter_context(patch.object(frappe, "get_list", side_effect=self.get_list))
		stack.enter_context(patch.object(frappe, "get_meta", return_value=SimpleNamespace(fields=[])))
		stack.enter_context(
			patch.object(frappe.local, "website_profile", profile_of_the_request, create=True)
		)
		return stack


def ctx_on(page_id):
	return SimpleNamespace(page_id=page_id, page_read_count=0)


def listing(ctx, **args):
	return {r["name"]: r for r in json.loads(data.query_records(ctx, {"doctype": "Builder Page", **args}))}


class TestListingsMarkAnotherSitesPages(unittest.TestCase):
	def test_a_page_of_another_site_is_listed_and_marked(self):
		with FakeBuilderPages().patches():
			rows = listing(ctx_on("page-a-home"), fields=["name", "route"])

		# labelled, not hidden: "why does this route answer elsewhere?" needs the foreign rows
		self.assertEqual(set(rows), set(PAGES))
		self.assertEqual(rows["page-b-home"][OTHER_SITE_KEY], SITE_B)
		self.assertEqual(rows["page-b-team"][OTHER_SITE_KEY], SITE_B)
		self.assertNotIn(OTHER_SITE_KEY, rows["page-a-home"])
		self.assertNotIn(OTHER_SITE_KEY, rows["page-a-about"])
		# a shared page (no tag) belongs to everyone
		self.assertNotIn(OTHER_SITE_KEY, rows["page-shared"])

	def test_the_owner_column_is_not_leaked_when_it_was_not_asked_for(self):
		fake = FakeBuilderPages()
		with fake.patches():
			rows = listing(ctx_on("page-a-home"), fields=["name", "route"])

		self.assertNotIn("neo_website_profile", rows["page-a-home"])
		self.assertNotIn("neo_website_profile", rows["page-b-home"])
		self.assertEqual(rows["page-b-home"]["route"], "/")

	def test_the_owner_column_stays_when_the_caller_asked_for_it(self):
		with FakeBuilderPages().patches():
			rows = listing(ctx_on("page-a-home"), fields=["name", "neo_website_profile"])

		self.assertEqual(rows["page-b-home"]["neo_website_profile"], SITE_B)
		self.assertEqual(rows["page-b-home"][OTHER_SITE_KEY], SITE_B)
		self.assertEqual(rows["page-a-home"]["neo_website_profile"], SITE_A)

	def test_the_site_of_the_request_is_used_when_the_open_page_has_no_tag(self):
		with FakeBuilderPages().patches(profile_of_the_request=SITE_A):
			rows = listing(ctx_on("page-shared"), fields=["name"])

		self.assertEqual(rows["page-b-home"][OTHER_SITE_KEY], SITE_B)
		self.assertNotIn(OTHER_SITE_KEY, rows["page-a-home"])

	def test_a_caller_filtering_on_the_site_is_left_alone(self):
		fake = FakeBuilderPages()
		with fake.patches():
			rows = listing(ctx_on("page-a-home"), fields=["name"], filters={"neo_website_profile": SITE_B})

		self.assertEqual(set(rows), {"page-b-home", "page-b-team"})
		self.assertNotIn(OTHER_SITE_KEY, rows["page-b-home"])
		self.assertEqual(fake.listed_with, [["name"]])

	def test_an_aggregate_query_is_not_given_an_extra_column(self):
		fake = FakeBuilderPages()
		with fake.patches():
			data.query_records(
				ctx_on("page-a-home"), {"doctype": "Builder Page", "fields": ["count(name) as n"]}
			)

		self.assertEqual(fake.listed_with, [["count(name) as n"]])

	def test_other_doctypes_are_listed_as_they_were(self):
		fake = FakeBuilderPages()
		with fake.patches():
			data.query_records(ctx_on("page-a-home"), {"doctype": "Builder Component", "fields": ["name"]})

		self.assertEqual(fake.listed_with, [["name"]])


class TestOneSiteInstanceIsUnchanged(unittest.TestCase):
	"""No site resolved (a one-site instance, the editor on an untagged page): every read stays as it was."""

	def test_no_row_is_marked_and_the_query_is_the_callers(self):
		fake = FakeBuilderPages()
		with fake.patches():
			rows = listing(ctx_on("page-shared"), fields=["name", "route"])

		self.assertEqual(set(rows), set(PAGES))
		self.assertFalse(any(OTHER_SITE_KEY in row for row in rows.values()))
		self.assertEqual(fake.listed_with, [["name", "route"]])

	def test_no_context_at_all_is_a_plain_listing(self):
		fake = FakeBuilderPages()
		with fake.patches():
			rows = listing(None, fields=["name"])

		self.assertFalse(any(OTHER_SITE_KEY in row for row in rows.values()))
		self.assertEqual(fake.listed_with, [["name"]])

	def test_an_instance_without_the_site_column_is_untouched(self):
		fake = FakeBuilderPages(has_column=False)
		with fake.patches(profile_of_the_request=SITE_A):
			rows = listing(ctx_on("page-a-home"), fields=["name"])

		self.assertFalse(any(OTHER_SITE_KEY in row for row in rows.values()))
		self.assertEqual(fake.listed_with, [["name"]])

	def test_a_reference_resolves_to_the_most_recent_published_page_as_before(self):
		with FakeBuilderPages().patches():
			self.assertEqual(query.resolve_page_reference("/"), ("page-b-home", ""))
			self.assertEqual(query.resolve_page_reference("Accueil"), ("page-b-home", ""))

	def test_reading_a_page_carries_no_warning(self):
		with FakeBuilderPages().patches(), patch("builder.ai.page_writer.load_page_root", return_value=None):
			out = query.run_read_page(ctx_on("page-shared"), {"page_id": "page-b-home"})

		self.assertNotIn(WARNING, out)
		self.assertIn("has no blocks yet", out)


class TestAReferenceResolvesInTheSitesOwnPages(unittest.TestCase):
	def test_a_route_shared_by_two_sites_resolves_to_this_sites_page(self):
		with FakeBuilderPages().patches(profile_of_the_request=SITE_A):
			self.assertEqual(query.resolve_page_reference("/"), ("page-a-home", ""))
			self.assertEqual(query.resolve_page_reference("Accueil"), ("page-a-home", ""))

	def test_the_open_pages_site_decides_when_the_request_has_none(self):
		with FakeBuilderPages().patches():
			self.assertEqual(query.resolve_page_reference("/", ctx_on("page-a-home")), ("page-a-home", ""))
			self.assertEqual(query.resolve_page_reference("/", ctx_on("page-b-home")), ("page-b-home", ""))

	def test_a_shared_page_answers_before_another_sites(self):
		with FakeBuilderPages().patches(profile_of_the_request=SITE_B):
			self.assertEqual(query.resolve_page_reference("index"), ("page-shared", ""))

	def test_another_sites_page_still_answers_when_this_site_has_none(self):
		# a diagnosis ("why does this route answer elsewhere?") needs it; read_page says whose it is
		with FakeBuilderPages().patches(profile_of_the_request=SITE_A):
			self.assertEqual(query.resolve_page_reference("equipe"), ("page-b-team", ""))
			self.assertEqual(query.resolve_page_reference("Equipe"), ("page-b-team", ""))

	def test_an_id_stays_resolvable_whatever_the_site(self):
		with FakeBuilderPages().patches(profile_of_the_request=SITE_A):
			self.assertEqual(query.resolve_page_reference("page-b-home"), ("page-b-home", ""))


class TestReadPageSaysWhoseItIs(unittest.TestCase):
	def read(self, page_id, open_page="page-a-home"):
		with FakeBuilderPages().patches(), patch("builder.ai.page_writer.load_page_root", return_value=None):
			return query.run_read_page(ctx_on(open_page), {"page_id": page_id})

	def test_a_page_of_another_site_opens_with_the_warning(self):
		out = self.read("page-b-team")

		self.assertTrue(out.startswith(WARNING), out)
		self.assertIn(f"({SITE_B})", out.splitlines()[0])
		self.assertIn("never propose to change, move or delete it", out)

	def test_a_route_that_only_another_site_has_is_read_with_the_warning(self):
		with FakeBuilderPages().patches(), patch("builder.ai.page_writer.load_page_root", return_value=None):
			out = query.run_read_page(ctx_on("page-a-home"), {"page_id": "equipe"})

		self.assertTrue(out.startswith(WARNING), out)

	def test_the_sites_own_page_and_a_shared_page_carry_none(self):
		self.assertNotIn(WARNING, self.read("page-a-about"))
		self.assertNotIn(WARNING, self.read("page-shared"))


class TestTheOpenPageContext(unittest.TestCase):
	def context(self, page_id, profile_of_the_request=None):
		from builder.ai.agent.loop import AgentRunner

		runner = SimpleNamespace(page_id=page_id, canvas_theme=None)
		with FakeBuilderPages().patches(profile_of_the_request):
			return AgentRunner.build_open_page_context(runner)

	def test_a_page_of_a_site_says_so_and_forbids_touching_the_others(self):
		out = self.context("page-a-home")

		self.assertIn("id page-a-home", out)
		self.assertIn(f"belongs to the site '{SITE_A}'", out)
		self.assertIn(OTHER_SITE_KEY, out)
		self.assertIn("never propose to change, move or delete it", out)

	def test_an_untagged_page_adds_nothing(self):
		out = self.context("page-shared")

		self.assertNotIn("belongs to the site", out)
		self.assertNotIn(OTHER_SITE_KEY, out)
