# //// Neoffice — added file (no upstream equivalent): a template hub that cannot answer is
# //// written to the Error Log once an hour and is not called at every page load.
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import api

HUB = "https://hub.test"


class TestAHubThatCannotAnswer(FrappeTestCase):
	"""Upstream prefetches the template gallery at every opening of the editor and of the
	dashboard. A hub without the builder_hub app (HTTP 417) or unreachable is never cached,
	so each load called it again and wrote an Error Log row. The gallery is empty either way."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.hub_url = patch.object(api, "hub_url", return_value=HUB)
		self.hub_url.start()
		self.addCleanup(self.hub_url.stop)
		self.forget_both()
		self.addCleanup(self.forget_both)

	def forget_hub_down(self):
		frappe.cache().delete_value(f"{api.TEMPLATE_HUB_DOWN_KEY}:{HUB}")

	def forget_both(self):
		self.forget_hub_down()
		frappe.cache().delete_value(api.TEMPLATE_HUB_ERROR_LOGGED_KEY)

	def test_three_page_loads_write_one_row_and_call_the_hub_once(self):
		with (
			patch.object(api, "hub_get", side_effect=Exception("417 builder_hub is not installed")) as hub,
			patch("frappe.log_error") as log_error,
		):
			answers = [api.get_template_groups() for _ in range(3)]

		self.assertEqual(answers, [[], [], []])
		self.assertEqual(hub.call_count, 1)
		self.assertEqual(log_error.call_count, 1)
		self.assertEqual(log_error.call_args.args[0], "Failed to fetch templates from hub")

	def test_the_hub_is_asked_again_after_the_wait_but_the_row_waits_an_hour(self):
		with (
			patch.object(api, "hub_get", side_effect=Exception("unreachable")) as hub,
			patch("frappe.log_error") as log_error,
		):
			api.get_template_groups()
			self.forget_hub_down()  # the wait is over, the hour is not
			self.assertEqual(api.get_template_groups(), [])

		self.assertEqual(hub.call_count, 2)
		self.assertEqual(log_error.call_count, 1)

	def test_a_failure_that_lasts_is_written_again_the_next_hour(self):
		with (
			patch.object(api, "hub_get", side_effect=Exception("unreachable")),
			patch("frappe.log_error") as log_error,
		):
			api.get_template_groups()
			self.forget_both()  # an hour later
			api.get_template_groups()

		self.assertEqual(log_error.call_count, 2)

	def test_a_hub_that_answers_writes_nothing_and_is_not_held_back(self):
		groups = [{"group_name": "Landing pages", "templates": []}]
		with (
			patch.object(api, "hub_get", return_value=groups) as hub,
			patch("frappe.log_error") as log_error,
		):
			first = api.get_template_groups()
			second = api.get_template_groups()

		self.assertEqual((first, second), (groups, groups))
		self.assertEqual(hub.call_count, 2)
		log_error.assert_not_called()

	def test_a_hub_that_comes_back_is_asked_once_the_wait_is_over(self):
		groups = [{"group_name": "Landing pages", "templates": []}]
		with patch.object(api, "hub_get", side_effect=Exception("down")), patch("frappe.log_error"):
			self.assertEqual(api.get_template_groups(), [])

		with patch.object(api, "hub_get", return_value=groups) as hub:
			self.assertEqual(api.get_template_groups(), [])  # still within the wait
			hub.assert_not_called()
			self.forget_hub_down()
			self.assertEqual(api.get_template_groups(), groups)

	def test_changing_the_hub_address_does_not_wait_for_the_old_hub(self):
		groups = [{"group_name": "Landing pages", "templates": []}]
		with patch.object(api, "hub_get", side_effect=Exception("down")), patch("frappe.log_error"):
			api.get_template_groups()

		with (
			patch.object(api, "hub_url", return_value="https://other-hub.test"),
			patch.object(api, "hub_get", return_value=groups),
		):
			self.assertEqual(api.get_template_groups(), groups)
