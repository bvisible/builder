# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
import frappe.website.utils  # //// Neoffice — see seed_page_cache
from frappe.tests.utils import FrappeTestCase

PAGE_ROUTE = "test-client-script-page"


# //// Neoffice — frappe v15 caches a rendered page in the `website_page` hash, keyed by route; only v16
# //// (the branch upstream tests against) keeps one key per route, "website_page::<route>". The controllers
# //// clear through frappe.website.utils.clear_cache either way, so the test seeds and reads the cache the
# //// way the running frappe stores it.
def seed_page_cache(route):
	prefix = getattr(frappe.website.utils, "WEBSITE_PAGE_CACHE_PREFIX", None)
	if prefix:
		frappe.cache.set_value(f"{prefix}{route}", {"en": "<html>old</html>"})
	else:
		frappe.cache.hset("website_page", route, {"en": "<html>old</html>"})


def cached_page(route):
	prefix = getattr(frappe.website.utils, "WEBSITE_PAGE_CACHE_PREFIX", None)
	return frappe.cache.get_value(f"{prefix}{route}") if prefix else frappe.cache.hget("website_page", route)


class TestBuilderClientScript(FrappeTestCase):
	def test_saving_a_script_clears_the_pages_that_link_it(self):
		script = frappe.get_doc(
			{"doctype": "Builder Client Script", "script_type": "CSS", "script": ".a { color: red; }"}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Client Script Page",
				"route": "test-client-script-page",
				"client_scripts": [{"builder_script": script.name}],
			}
		).insert()
		seed_page_cache(PAGE_ROUTE)  # //// Neoffice — see seed_page_cache

		script.script = ".a { color: blue; }"
		script.save()

		self.assertIsNone(cached_page(PAGE_ROUTE))  # //// Neoffice — see seed_page_cache
