# //// Neoffice — added file (no upstream equivalent): the panel's watchdog and a turn still in the queue (13.11).
"""A turn still waiting in the queue is a running turn for the panel's watchdog (turn_state).

The session lock is taken when the job starts. Behind hundreds of queued jobs, a turn sent from the editor held no lock
for minutes: the watchdog read « not running » twice and the panel dropped the turn while it was still to come.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.session import AISession
from builder.site_ai.nora.api import turn_job_id, turn_state


class TestTurnStateSeesAQueuedTurn(FrappeTestCase):
	def setUp(self):
		self.session = AISession.create({}).name

	def tearDown(self):
		frappe.cache().delete_value("builder_turn_job:" + self.session)
		frappe.db.rollback()

	def test_a_turn_in_the_queue_is_running(self):
		job_id = turn_job_id(self.session)
		with patch("frappe.utils.background_jobs.is_job_enqueued", return_value=True) as enqueued:
			self.assertTrue(turn_state(self.session)["running"])
		enqueued.assert_called_once_with(job_id)

	def test_a_turn_whose_job_has_ended_is_not(self):
		turn_job_id(self.session)
		with patch("frappe.utils.background_jobs.is_job_enqueued", return_value=False):
			self.assertFalse(turn_state(self.session)["running"])

	def test_a_chat_that_never_queued_a_turn_is_not(self):
		self.assertFalse(turn_state(self.session)["running"])

	def test_each_turn_gets_a_job_of_its_own(self):
		self.assertNotEqual(turn_job_id(self.session), turn_job_id(self.session))
