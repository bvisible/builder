# //// Neoffice — added file (no upstream equivalent): after a No on a confirm card, the resumed turn is told
# //// that the person refused the action, so the agent does not ask for it again (neoffice-maintenance#2636).
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.models import ModelRegistry
from builder.ai.session import AISession
from builder.ai.test_llm import OPENROUTER_MODEL as MODEL

# the person who answers the card: a website manager, the role the editor's assistant serves, not Administrator
MANAGER = "builder-2636-manager@yopmail.com"
PROPOSAL = "Make « À propos » the home page of the site?"


def website_manager() -> str:
	if not frappe.db.exists("User", MANAGER):
		frappe.get_doc(
			{"doctype": "User", "email": MANAGER, "first_name": "Card test", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", MANAGER).add_roles("Website Manager")
	frappe.clear_cache(user=MANAGER)
	return MANAGER


class TestARefusedCard(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		user = website_manager()
		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Card test 2636"}).insert()
		self.session = (
			frappe.get_doc({"doctype": "Builder AI Session", "session_user": user, "page": page.name})
			.insert(ignore_permissions=True)
			.name
		)
		self.card = AISession.try_append_message(
			self.session,
			"assistant",
			PROPOSAL,
			message_type="clarification",
			task_type="agent",
			metadata={"status": "pending_action", "kind": "home_page", "payload": {"page": page.name}},
		)
		frappe.set_user(user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.clear_cache(user=MANAGER)

	def answer(self, decision: str):
		with (
			patch.object(ModelRegistry, "find", return_value=MODEL),
			patch("builder.ai.api.resolve_api_key", return_value="sk-test"),
			patch("builder.ai.agent.pending.apply_pending_action", return_value="Applied.") as applied,
			patch("frappe.enqueue") as enqueue,
		):
			result = api.confirm_pending_settings(self.card, decision=decision)
		enqueue.assert_called_once()
		return result, enqueue.call_args.kwargs["prompt"], applied

	def test_a_no_tells_the_agent_it_was_refused_and_not_to_ask_again(self):
		result, prompt, applied = self.answer("skip")

		self.assertEqual(result["status"], "skipped")
		applied.assert_not_called()
		self.assertIn("answered No", prompt)
		self.assertIn(PROPOSAL, prompt)
		self.assertIn("do not propose it again", prompt)
		# the approval's words would send the agent back to the plan it was on, the refused action first
		self.assertNotIn("Continue with what you were doing", prompt)

	def test_a_yes_still_carries_on_with_the_plan(self):
		result, prompt, applied = self.answer("apply")

		self.assertEqual(result["status"], "applied")
		applied.assert_called_once()
		self.assertTrue(prompt.startswith("Applied."))
		self.assertIn("Continue with what you were doing", prompt)
		self.assertNotIn("answered No", prompt)

	def test_the_card_is_marked_skipped_and_nothing_is_applied(self):
		self.answer("skip")
		self.assertEqual(
			frappe.db.get_value(AISession.MESSAGE_DOCTYPE, self.card, "status"), "action_skipped"
		)
