# //// Neoffice — added file (no upstream equivalent): the editor's chat and the Website tab's conversations (13.11).
"""The editor's chat never reopens, lists nor writes into a conversation of the Website tab.

Both anchor their conversations on a page: the tab on the site's home page, the editor on the page it edits. Opened on
the home page, the editor reopened the page's latest conversation, which was the tab's, and a question asked in the
editor went into it (13.11).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.session import AISession
from builder.site_ai.nora.site_chat import editor_session, site_session_names


class TestTheEditorKeepsOutOfTheSiteTabsChats(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Editor and the site's tab"}
		).insert()
		self.editor = self.chat("Raccourcis le titre", {})
		self.tab = self.chat("Change la photo de l'accueil", {"siteChat": "test-site"})
		# the tab's conversation is the page's latest
		frappe.db.set_value(
			AISession.DOCTYPE,
			self.tab,
			"last_interaction_on",
			frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=5),
		)

	def tearDown(self):
		frappe.db.rollback()

	def chat(self, text: str, metadata: dict) -> str:
		session = AISession.create({"page": self.page.name})
		session.append_message("user", text, message_type="chat", task_type="agent", metadata=metadata)
		return session.name

	def test_the_tabs_conversations_are_told_apart(self):
		self.assertEqual(site_session_names(self.page.name), [self.tab])

	def test_the_editor_reopens_its_own_conversation_not_the_tabs_latest(self):
		self.assertEqual(api.get_ai_session(self.page.name)["session_id"], self.editor)

	def test_asked_for_the_tabs_conversation_the_editor_reopens_its_own(self):
		self.assertEqual(api.get_ai_session(self.page.name, session_id=self.tab)["session_id"], self.editor)

	def test_the_tabs_conversations_are_not_in_the_editors_list(self):
		names = [row["name"] for row in api.list_page_ai_sessions(self.page.name)]
		self.assertIn(self.editor, names)
		self.assertNotIn(self.tab, names)

	def test_a_turn_sent_to_the_tabs_conversation_starts_one_of_its_own(self):
		self.assertIsNone(editor_session(self.tab))
		self.assertEqual(editor_session(self.editor), self.editor)
		self.assertIsNone(editor_session(None))
