# //// Neoffice — added file (no upstream equivalent): the offline-site gate of the page lookup
# //// is decided per caller, whatever the cache holds (neoffice-maintenance #280).
import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_page.builder_page import find_page_with_path


class TestOfflineGate(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Offline gate", "route": "offline-gate-test", "published": 1, "blocks": "[]"}).insert(ignore_permissions=True)
		frappe.db.commit()
		self.profile_doc_before = getattr(frappe.local, "website_profile_doc", None)
		frappe.local.website_profile_doc = {"name": "Offline test", "website_online": 0}
		find_page_with_path.clear_cache()

	def tearDown(self):
		frappe.local.website_profile_doc = self.profile_doc_before
		frappe.set_user("Administrator")
		frappe.delete_doc("Builder Page", self.page.name, force=True, ignore_permissions=True)
		frappe.db.commit()
		find_page_with_path.clear_cache()

	def _as(self, user):
		frappe.set_user(user)
		return find_page_with_path("offline-gate-test")

	def test_visitor_first_then_staff(self):
		self.assertIsNone(self._as("Guest"))
		self.assertEqual(self._as("Administrator"), self.page.name)

	def test_staff_first_then_visitor(self):
		self.assertEqual(self._as("Administrator"), self.page.name)
		self.assertIsNone(self._as("Guest"))
		# and the lookup itself is still cached for the next staff call
		self.assertEqual(self._as("Administrator"), self.page.name)

	def test_online_site_serves_everyone(self):
		frappe.local.website_profile_doc = {"name": "Online test", "website_online": 1}
		self.assertEqual(self._as("Guest"), self.page.name)
