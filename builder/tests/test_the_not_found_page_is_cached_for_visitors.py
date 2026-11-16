# //// Neoffice — added file (no upstream equivalent): the not-found page goes into frappe's page cache for an
# //// anonymous visitor, and only for one (neoffice-maintenance#2727).
"""The not-found page and frappe's page cache (neoffice-maintenance#2727).

builder/www/404.py kept every not-found page out of the cache: each robot probe (/.env, /wp-login.php…) rendered the
whole site chrome again, about 200 ms of a worker, on every instance and every tenant of the shared host. The page
depends on the address only on a site where an app of RESERVED is missing; otherwise on the language and the website
profile, which the cache key of our frappe fork carries. A signed-in person's rendering is never written.
"""

import importlib
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response

page = importlib.import_module("builder.www.404")

PROBES = ("/.env", "/wp-admin/setup-config.php", "/an-address-that-never-existed-2727")
USER = "notfound-cache-2727@example.com"
FULL_NAME = "Zephyrine Quarzazate"


def _context(path, installed):
	set_request(method="GET", path=path)
	# create=True: the page before #2727 had no such helper, and the test must fail on it, not stop
	with patch.object(page, "_installed_apps", return_value=set(installed), create=True):
		return page.get_context(frappe._dict())


def _like_production(no_cache=False):
	"""frappe.website.utils.can_cache on a site without developer_mode (every client, every tenant)."""
	if frappe.conf.disable_website_cache:
		return False
	if getattr(frappe.local, "no_cache", False):
		return False
	return not no_cache


def _render(path):
	set_request(method="GET", path=path)
	frappe.local.response = frappe._dict()
	response = get_response(path)
	return response.status_code, str(response.data, "utf-8"), bool(frappe.local.response.get("from_cache"))


class TestTheNotFoundPageDecidesItsCache(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_wrong_address_goes_into_the_cache_for_a_visitor(self):
		frappe.set_user("Guest")
		for path in PROBES:
			context = _context(path, installed={"frappe", "builder", "webshop"})
			self.assertFalse(context.no_cache, path)
			self.assertFalse(context.is_reserved, path)

	def test_a_reserved_route_whose_app_is_missing_stays_out_of_the_cache(self):
		frappe.set_user("Guest")
		context = _context("/cart", installed={"frappe", "builder"})
		self.assertTrue(context.is_reserved)
		self.assertTrue(context.no_cache)

	def test_no_wrong_address_is_cached_while_a_reserved_app_is_missing(self):
		# the one cached page would then also answer /cart, which must say « Coming soon »
		frappe.set_user("Guest")
		context = _context("/.env", installed={"frappe", "builder"})
		self.assertFalse(context.is_reserved)
		self.assertTrue(context.no_cache)

	def test_a_signed_in_persons_rendering_is_never_cached(self):
		frappe.set_user("Administrator")
		context = _context("/.env", installed={"frappe", "builder", "webshop"})
		self.assertTrue(context.no_cache)

	def test_the_page_module_declares_no_blanket_no_cache(self):
		self.assertFalse(getattr(page, "no_cache", 0))


class TestACachedNotFoundPageHoldsNothingOfASignedInPerson(FrappeTestCase):
	"""Rendered end to end, under the cache rule of a production site."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": USER,
					"first_name": FULL_NAME.split()[0],
					"last_name": FULL_NAME.split()[1],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.delete_doc("User", USER, force=True, ignore_permissions=True)
		super().tearDownClass()

	def setUp(self):
		self._forget()
		self.patches = [
			patch("frappe.website.utils.can_cache", _like_production),
			patch("frappe.website.page_renderers.not_found_page.can_cache", _like_production),
			patch.object(page, "_installed_apps", return_value={"frappe", "builder", "webshop"}, create=True),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in self.patches:
			p.stop()
		self._forget()
		frappe.set_user("Administrator")

	def _forget(self):
		frappe.cache.hdel("website_page", "404")
		# the addresses frappe remembers as not found (NotFoundPage.can_cache_404)
		frappe.cache.delete_value("website_404")

	def test_a_signed_in_rendering_writes_nothing_and_a_visitor_then_gets_no_trace_of_it(self):
		frappe.set_user(USER)
		status, html, _ = _render(PROBES[0])
		self.assertEqual(status, 404)
		self.assertIn(FULL_NAME.split()[0], frappe.db.get_value("User", USER, "full_name"))
		self.assertFalse(
			frappe.cache.hget("website_page", "404"), "a signed-in rendering went into the page cache"
		)

		frappe.set_user("Guest")
		status, html, from_cache = _render(PROBES[1])
		self.assertEqual(status, 404)
		self.assertFalse(from_cache)
		self.assertTrue(
			frappe.cache.hget("website_page", "404"), "a visitor's rendering did not go into the cache"
		)
		for trace in (USER, FULL_NAME.split()[0], FULL_NAME.split()[1]):
			self.assertNotIn(trace, html)

	def test_a_second_probe_is_served_from_the_cache(self):
		frappe.set_user("Guest")
		first = _render(PROBES[0])
		second = _render(PROBES[2])
		self.assertEqual((first[0], second[0]), (404, 404))
		self.assertFalse(first[2])
		self.assertTrue(
			second[2], "the second not-found page was rendered again instead of read from the cache"
		)

	def test_what_the_cache_hands_a_signed_in_person_was_written_by_a_visitor(self):
		frappe.set_user("Guest")
		_render(PROBES[0])
		frappe.set_user(USER)
		status, html, from_cache = _render(PROBES[1])
		self.assertEqual(status, 404)
		self.assertTrue(from_cache)
		self.assertNotIn(USER, html)
