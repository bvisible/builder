# //// Neoffice — added file (no upstream equivalent): the thumbnail of a page is queued once per publish, and a
# //// thumbnail the engine cannot draw leaves the page as it was without writing to the Error Log
# //// (neoffice-maintenance#2368).
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import Block

PAGE = "test-preview-page"
MODULE = "builder.builder.doctype.builder_page.builder_page"


def preview_jobs(enqueue):
	return [c for c in enqueue.call_args_list if c.args[2:3] == ("generate_page_preview_image",)]


def engine_times_out(html, output_path, **kwargs):
	"""What the shared Chromium does when another render holds it: the engine logs its own timeout, then throws."""
	frappe.log_error(title="Timeout waiting for event", message="test: no event")
	frappe.throw("The PDF engine did not respond in time. Please try again.")


def error_log_is_transactional() -> bool:
	engine = frappe.db.sql(
		"select engine from information_schema.tables where table_schema = database() and table_name = 'tabError Log'"
	)
	return bool(engine) and engine[0][0] == "InnoDB"


def delete_test_pages():
	# frappe names a Builder Page itself (page-<hash>): the route is what the test knows it by
	for name in frappe.get_all("Builder Page", {"route": PAGE}, pluck="name"):
		frappe.delete_doc("Builder Page", name, force=True)


class TestBuilderPagePreview(FrappeTestCase):
	def setUp(self):
		delete_test_pages()
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Preview test",
				"route": PAGE,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="Preview")],
				).as_json(wrap_in_array=True),
			}
		).insert()

	def tearDown(self):
		delete_test_pages()

	def test_publishing_a_page_with_the_fallback_thumbnail_queues_one_preview(self):
		self.assertEqual(self.page.preview, self.page.FALLBACK_PREVIEW)
		with patch("frappe.enqueue_doc") as enqueue:
			self.page.publish()
		self.assertEqual(len(preview_jobs(enqueue)), 1)

	def test_a_thumbnail_the_engine_cannot_draw_leaves_the_page_as_it_was(self):
		self.page.db_set("preview", "/files/an-older-preview.webp", update_modified=False)
		logged = frappe.db.count("Error Log", {"method": "Timeout waiting for event"})
		with (
			patch(f"{MODULE}.generate_preview", side_effect=engine_times_out),
			patch.object(type(self.page), "get_preview_html", return_value="<html></html>"),
		):
			drawn = self.page.generate_page_preview_image()
		self.assertIs(drawn, False)
		self.assertEqual(
			frappe.db.get_value("Builder Page", self.page.name, "preview"), "/files/an-older-preview.webp"
		)
		# the failed render's own rows go back with the savepoint where the Error Log is transactional, as it is
		# on the fleet's sites (InnoDB); a site created now gets frappe's MyISAM table, which no rollback touches
		if error_log_is_transactional():
			self.assertEqual(frappe.db.count("Error Log", {"method": "Timeout waiting for event"}), logged)
		# the page itself is still there: only the failed render's rows went back
		self.assertTrue(frappe.db.exists("Builder Page", self.page.name))
