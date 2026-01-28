# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder_ai import (
	generate_block_id,
	generate_blocks_from_context,
	get_cta_template,
	get_features_template,
	get_footer_template,
	get_hero_template,
	get_llm_config,
)


class TestBuilderAI(FrappeTestCase):
	"""Tests for Builder AI functions"""

	def test_generate_block_id(self):
		"""Test block ID generation"""
		block_id = generate_block_id()
		self.assertEqual(len(block_id), 9)
		self.assertTrue(block_id.isalnum())

		# Test uniqueness
		ids = [generate_block_id() for _ in range(100)]
		self.assertEqual(len(ids), len(set(ids)))

	def test_get_llm_config_defaults(self):
		"""Test default LLM configuration"""
		config = get_llm_config()

		self.assertIn("provider", config)
		self.assertIn("ollama_base_url", config)
		self.assertIn("ollama_model", config)
		self.assertEqual(config["ollama_base_url"], "http://localhost:11434")

	def test_get_hero_template(self):
		"""Test hero section template generation"""
		context = {
			"tagline": "Test Tagline",
			"description": "Test description",
			"style": {
				"primary_color": "#FF0000",
				"text_color": "#000000"
			},
			"sections": [
				{
					"type": "hero",
					"headline": "Welcome to Our Site",
					"cta_text": "Get Started",
					"cta_link": "/signup"
				}
			]
		}

		hero = get_hero_template(context)

		self.assertEqual(hero["element"], "section")
		self.assertEqual(hero["blockName"], "hero")
		self.assertIn("children", hero)
		self.assertIn("baseStyles", hero)
		self.assertIn("mobileStyles", hero)

		# Verify blockId exists and is valid
		self.assertEqual(len(hero["blockId"]), 9)

	def test_get_features_template(self):
		"""Test features section template generation"""
		context = {
			"style": {
				"primary_color": "#3B82F6",
				"text_color": "#171717",
				"secondary_color": "#6B7280"
			},
			"sections": [
				{
					"type": "features",
					"headline": "Our Features",
					"items": [
						{"title": "Feature 1", "description": "Desc 1"},
						{"title": "Feature 2", "description": "Desc 2"},
					]
				}
			]
		}

		features = get_features_template(context)

		self.assertEqual(features["element"], "section")
		self.assertEqual(features["blockName"], "features")

		# Find features grid in children
		container = features["children"][0]
		self.assertIsNotNone(container)

	def test_get_cta_template(self):
		"""Test CTA section template generation"""
		context = {
			"style": {
				"primary_color": "#10B981"
			},
			"sections": [
				{
					"type": "cta",
					"headline": "Ready to Start?",
					"description": "Join us today",
					"cta_text": "Sign Up",
					"cta_link": "/register"
				}
			]
		}

		cta = get_cta_template(context)

		self.assertEqual(cta["element"], "section")
		self.assertEqual(cta["blockName"], "cta")
		self.assertEqual(cta["baseStyles"]["backgroundColor"], "#10B981")

	def test_get_footer_template(self):
		"""Test footer section template generation"""
		context = {
			"business_name": "Test Company",
			"style": {
				"text_color": "#171717",
				"secondary_color": "#6B7280"
			}
		}

		footer = get_footer_template(context)

		self.assertEqual(footer["element"], "footer")
		self.assertEqual(footer["blockName"], "footer")

	def test_generate_blocks_from_context_default(self):
		"""Test block generation with default sections"""
		context = {
			"business_name": "My Company",
			"style": {}
		}

		blocks = generate_blocks_from_context(context)

		# Should have hero, features, cta, and footer
		self.assertGreaterEqual(len(blocks), 3)

		# Verify block types
		block_names = [b.get("blockName") for b in blocks]
		self.assertIn("hero", block_names)

	def test_generate_blocks_from_context_with_sections(self):
		"""Test block generation with specified sections"""
		context = {
			"business_name": "Test Co",
			"style": {
				"primary_color": "#3B82F6"
			},
			"sections": [
				{"type": "hero", "headline": "Welcome"},
				{"type": "features", "headline": "Features"},
				{"type": "cta", "headline": "Get Started"}
			]
		}

		blocks = generate_blocks_from_context(context)

		# Should have 4 blocks (hero, features, cta + auto-added footer)
		self.assertEqual(len(blocks), 4)

	def test_block_structure_validity(self):
		"""Test that generated blocks have valid structure"""
		context = {
			"business_name": "Test",
			"style": {},
			"sections": [{"type": "hero"}]
		}

		blocks = generate_blocks_from_context(context)

		for block in blocks:
			# Required fields
			self.assertIn("blockId", block)
			self.assertIn("element", block)
			self.assertIn("baseStyles", block)
			self.assertIn("children", block)

			# Valid types
			self.assertIsInstance(block["baseStyles"], dict)
			self.assertIsInstance(block["children"], list)

	def test_responsive_styles(self):
		"""Test that blocks include responsive styles"""
		context = {
			"style": {},
			"sections": [{"type": "hero"}]
		}

		blocks = generate_blocks_from_context(context)
		hero = blocks[0]

		self.assertIn("tabletStyles", hero)
		self.assertIn("mobileStyles", hero)
		self.assertIsInstance(hero["tabletStyles"], dict)
		self.assertIsInstance(hero["mobileStyles"], dict)


class TestBuilderAIAPI(FrappeTestCase):
	"""Tests for Builder AI API endpoints"""

	def test_get_ai_config_api(self):
		"""Test get_ai_config API endpoint"""
		from builder.builder_ai import get_ai_config

		config = get_ai_config()

		self.assertIn("provider", config)
		self.assertIn(config["provider"], ["ollama", "openai"])

	@patch("builder.builder_ai.call_llm")
	def test_start_conversation_api(self, mock_call_llm):
		"""Test start_conversation API with mocked LLM"""
		mock_call_llm.return_value = json.dumps({
			"message": "Hello! What kind of website would you like to create?",
			"site_context": {},
			"collection_complete": False
		})

		from builder.builder_ai import start_conversation

		result = start_conversation(title="Test Site")

		self.assertIn("conversation_id", result)
		self.assertIn("message", result)
		self.assertFalse(result["collection_complete"])

		# Cleanup
		if result.get("conversation_id"):
			frappe.delete_doc("Builder AI Conversation", result["conversation_id"])

	@patch("builder.builder_ai.call_llm")
	def test_send_message_api(self, mock_call_llm):
		"""Test send_message API with mocked LLM"""
		# First create a conversation
		mock_call_llm.return_value = json.dumps({
			"message": "Great! What's your business name?",
			"site_context": {"site_type": "landing_page"},
			"collection_complete": False
		})

		from builder.builder_ai import send_message, start_conversation

		# Start conversation
		start_result = start_conversation(title="Test")
		conversation_id = start_result["conversation_id"]

		# Send a message
		mock_call_llm.return_value = json.dumps({
			"message": "Nice! What colors would you like?",
			"site_context": {
				"site_type": "landing_page",
				"business_name": "My Company"
			},
			"collection_complete": False
		})

		result = send_message(conversation_id, "I want a landing page for My Company")

		self.assertIn("message", result)
		self.assertEqual(result["site_context"]["business_name"], "My Company")

		# Cleanup
		frappe.delete_doc("Builder AI Conversation", conversation_id)

	def test_generate_page_api(self):
		"""Test generate_page API"""
		# Create a conversation with context
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Generate Test",
			"status": "generating",
			"messages": "[]",
			"site_context": json.dumps({
				"business_name": "Test Company",
				"tagline": "The best company",
				"style": {
					"primary_color": "#3B82F6",
					"text_color": "#171717"
				},
				"sections": [
					{"type": "hero", "headline": "Welcome"}
				]
			})
		}).insert()

		from builder.builder_ai import generate_page

		result = generate_page(conversation.name)

		self.assertTrue(result["success"])
		self.assertIn("page_name", result)
		self.assertIn("blocks", result)

		# Cleanup
		if result.get("page_name"):
			frappe.delete_doc("Builder Page", result["page_name"])
		conversation.delete()

	def test_preview_blocks_api(self):
		"""Test preview_blocks API"""
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Preview Test",
			"status": "collecting",
			"site_context": json.dumps({
				"business_name": "Preview Co",
				"style": {},
				"sections": [{"type": "hero"}]
			})
		}).insert()

		from builder.builder_ai import preview_blocks

		result = preview_blocks(conversation.name)

		self.assertIn("blocks", result)
		self.assertIn("site_context", result)
		self.assertGreater(len(result["blocks"]), 0)

		conversation.delete()


class TestOllamaIntegration(FrappeTestCase):
	"""Tests for Ollama integration (requires Ollama running)"""

	def test_ollama_config(self):
		"""Test Ollama configuration"""
		config = get_llm_config()

		if config["provider"] == "ollama":
			self.assertIsNotNone(config["ollama_base_url"])
			self.assertIsNotNone(config["ollama_model"])

	@patch("requests.post")
	def test_ollama_call_mock(self, mock_post):
		"""Test Ollama API call with mock"""
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"message": {
				"content": '{"message": "Hello!", "site_context": {}}'
			}
		}
		mock_post.return_value = mock_response

		from builder.builder_ai import call_ollama

		config = {
			"ollama_base_url": "http://localhost:11434"
		}

		result = call_ollama(
			messages=[{"role": "user", "content": "Hello"}],
			model="llama3.1",
			temperature=0.7,
			config=config
		)

		self.assertIn("message", result)
		mock_post.assert_called_once()
