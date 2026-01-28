# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBuilderAIConversation(FrappeTestCase):
	def test_create_conversation(self):
		"""Test creating a new AI conversation"""
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Test Conversation",
			"status": "collecting",
			"messages": "[]",
			"site_context": "{}",
			"generated_blocks": "[]"
		}).insert()

		self.assertEqual(conversation.title, "Test Conversation")
		self.assertEqual(conversation.status, "collecting")
		self.assertEqual(conversation.messages, "[]")

		conversation.delete()

	def test_update_messages(self):
		"""Test updating conversation messages"""
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Message Test",
			"status": "collecting",
		}).insert()

		messages = [
			{"role": "assistant", "content": "Hello!"},
			{"role": "user", "content": "I want a landing page"}
		]
		conversation.messages = json.dumps(messages)
		conversation.save()

		# Reload and verify
		conversation.reload()
		loaded_messages = json.loads(conversation.messages)
		self.assertEqual(len(loaded_messages), 2)
		self.assertEqual(loaded_messages[0]["role"], "assistant")

		conversation.delete()

	def test_update_site_context(self):
		"""Test updating site context"""
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Context Test",
			"status": "collecting",
		}).insert()

		site_context = {
			"site_type": "landing_page",
			"business_name": "Test Company",
			"style": {
				"primary_color": "#3B82F6",
				"text_color": "#171717"
			}
		}
		conversation.site_context = json.dumps(site_context)
		conversation.save()

		# Reload and verify
		conversation.reload()
		loaded_context = json.loads(conversation.site_context)
		self.assertEqual(loaded_context["site_type"], "landing_page")
		self.assertEqual(loaded_context["business_name"], "Test Company")

		conversation.delete()

	def test_status_transitions(self):
		"""Test conversation status transitions"""
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Status Test",
			"status": "collecting",
		}).insert()

		self.assertEqual(conversation.status, "collecting")

		conversation.status = "generating"
		conversation.save()
		self.assertEqual(conversation.status, "generating")

		conversation.status = "completed"
		conversation.save()
		self.assertEqual(conversation.status, "completed")

		conversation.delete()

	def test_link_to_page(self):
		"""Test linking conversation to generated page"""
		# Create a test page
		page = frappe.get_doc({
			"doctype": "Builder Page",
			"page_title": "AI Generated Test",
			"route": "/ai-test-page",
			"blocks": "[]"
		}).insert()

		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Page Link Test",
			"status": "completed",
			"page": page.name
		}).insert()

		self.assertEqual(conversation.page, page.name)

		conversation.delete()
		page.delete()
