# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder_ai import (
	generate_block_id,
	generate_blocks_from_context,
	get_collector_prompt,
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


class TestCreativitySettings(FrappeTestCase):
	"""Tests for creativity and dynamic prompt generation"""

	def test_creativity_levels(self):
		"""Test that creativity levels map to correct temperatures"""
		config = get_llm_config()

		# Verify creativity_level is present
		self.assertIn("creativity_level", config)
		self.assertIn(config["creativity_level"], ["conservative", "balanced", "creative", "experimental"])

	def test_get_collector_prompt_basic(self):
		"""Test basic collector prompt generation"""
		prompt = get_collector_prompt()

		# Verify prompt contains key elements
		self.assertIn("web designer", prompt.lower())
		self.assertIn("color", prompt.lower())
		self.assertIn("json", prompt.lower())

	def test_get_collector_prompt_with_settings(self):
		"""Test collector prompt with mock settings"""
		mock_settings = MagicMock()
		mock_settings.shortcodes = []
		mock_settings.creativity_level = "creative"
		mock_settings.default_style = "modern"
		mock_settings.use_modern_design = True
		mock_settings.default_site_type = "one_page"
		mock_settings.allow_multipage = False

		prompt = get_collector_prompt(mock_settings)

		# Verify settings are incorporated
		self.assertIn("creative", prompt.lower())
		self.assertIn("modern", prompt.lower())
		self.assertIn("one_page", prompt.lower())

	def test_get_collector_prompt_with_shortcodes(self):
		"""Test collector prompt includes shortcodes"""
		mock_shortcode = MagicMock()
		mock_shortcode.name1 = "Cart"
		mock_shortcode.category = "E-commerce"
		mock_shortcode.description = "Shopping cart icon"
		mock_shortcode.use_when = "E-commerce sites"
		mock_shortcode.shortcode = "{% include 'cart.html' %}"

		mock_settings = MagicMock()
		mock_settings.shortcodes = [mock_shortcode]
		mock_settings.creativity_level = "balanced"
		mock_settings.default_style = "modern"
		mock_settings.use_modern_design = True
		mock_settings.default_site_type = "auto"
		mock_settings.allow_multipage = True

		prompt = get_collector_prompt(mock_settings)

		# Verify shortcode is included
		self.assertIn("Cart", prompt)
		self.assertIn("E-commerce", prompt)

	def test_color_psychology_in_prompt(self):
		"""Test that color psychology is included in prompt"""
		prompt = get_collector_prompt()

		# Verify industry-specific color suggestions
		self.assertIn("florist", prompt.lower())
		self.assertIn("tech", prompt.lower())
		self.assertIn("restaurant", prompt.lower())
		self.assertIn("luxury", prompt.lower())

	def test_llm_config_includes_vision_settings(self):
		"""Test that LLM config includes vision settings"""
		config = get_llm_config()

		self.assertIn("enable_vision", config)
		self.assertIn("ollama_vision_model", config)
		self.assertIn("openai_vision_model", config)

	def test_llm_config_includes_design_settings(self):
		"""Test that LLM config includes design settings"""
		config = get_llm_config()

		self.assertIn("default_style", config)
		self.assertIn("use_modern_design", config)
		self.assertIn("default_site_type", config)
		self.assertIn("allow_multipage", config)


class TestVisionSupport(FrappeTestCase):
	"""Tests for vision/image analysis functionality"""

	@patch("requests.post")
	@patch("requests.get")
	def test_analyze_image_ollama_mock(self, mock_get, mock_post):
		"""Test image analysis with Ollama (mocked)"""
		# Mock the POST response for vision
		mock_post_response = MagicMock()
		mock_post_response.status_code = 200
		mock_post_response.json.return_value = {
			"message": {
				"content": json.dumps({
					"description": "A modern tech logo",
					"colors": ["#3B82F6", "#10B981"],
					"mood": "professional",
					"style_suggestions": ["minimal", "modern"],
					"design_insights": {
						"recommended_palette": ["#3B82F6", "#10B981", "#F3F4F6"],
						"typography_style": "sans-serif",
						"layout_suggestions": "clean, spacious"
					}
				})
			}
		}
		mock_post.return_value = mock_post_response

		from builder.builder_ai import analyze_image_ollama

		config = {
			"ollama_base_url": "http://localhost:11434",
			"ollama_vision_model": "llava",
			"ollama_timeout": 120
		}

		# Use base64 encoded test image (1x1 white pixel)
		test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

		result = analyze_image_ollama(test_image, "Analyze this logo", config)

		self.assertIn("description", result)
		self.assertIn("colors", result)
		self.assertIsInstance(result["colors"], list)
		mock_post.assert_called_once()

	def test_analyze_image_requires_vision_enabled(self):
		"""Test that image analysis requires vision to be enabled"""
		from builder.builder_ai import analyze_image_with_vision

		config = {
			"enable_vision": False,
			"provider": "ollama"
		}

		with self.assertRaises(frappe.exceptions.ValidationError):
			analyze_image_with_vision("test_image_data", "test prompt", config)

	@patch("builder.builder_ai.analyze_image_with_vision")
	@patch("builder.builder_ai.call_llm")
	def test_send_message_with_image_logo(self, mock_call_llm, mock_analyze):
		"""Test sending message with logo image"""
		# Setup mocks
		mock_analyze.return_value = {
			"colors": ["#FF5733", "#2E86AB"],
			"mood": "energetic",
			"description": "Colorful logo"
		}
		mock_call_llm.return_value = json.dumps({
			"message": "I've analyzed your logo and extracted the colors!",
			"site_context": {
				"style": {
					"primary_color": "#FF5733"
				}
			},
			"collection_complete": False
		})

		# Create test conversation
		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Vision Test",
			"status": "collecting",
			"messages": "[]",
			"site_context": "{}"
		}).insert()

		try:
			from builder.builder_ai import send_message_with_image

			# Mock config to enable vision
			with patch("builder.builder_ai.get_llm_config") as mock_config:
				mock_config.return_value = {
					"enable_vision": True,
					"provider": "ollama",
					"max_messages": 20
				}

				result = send_message_with_image(
					conversation.name,
					"Here's my company logo",
					"base64_image_data",
					"logo"
				)

				self.assertIn("message", result)
				self.assertIn("image_analysis", result)
				self.assertEqual(result["image_analysis"]["colors"], ["#FF5733", "#2E86AB"])

		finally:
			conversation.delete()


class TestShortcodes(FrappeTestCase):
	"""Tests for shortcode functionality"""

	def test_shortcode_doctype_exists(self):
		"""Test that Builder AI Shortcode doctype exists"""
		self.assertTrue(frappe.db.exists("DocType", "Builder AI Shortcode"))

	def test_create_shortcode(self):
		"""Test creating a shortcode entry"""
		# This requires the settings doc to exist
		try:
			settings = frappe.get_doc("Builder AI Settings")
		except frappe.DoesNotExistError:
			# Create settings if not exists
			settings = frappe.get_doc({
				"doctype": "Builder AI Settings",
				"enabled": True,
				"ai_provider": "ollama"
			}).insert()

		# Add a shortcode
		settings.append("shortcodes", {
			"name1": "Test Cart",
			"shortcode": "{% include 'cart.html' %}",
			"category": "E-commerce",
			"use_when": "For e-commerce sites",
			"description": "Shopping cart widget"
		})
		settings.save()

		# Verify shortcode was added
		self.assertEqual(len(settings.shortcodes), 1)
		self.assertEqual(settings.shortcodes[0].name1, "Test Cart")

		# Cleanup - remove the shortcode
		settings.shortcodes = []
		settings.save()

	def test_shortcodes_in_prompt(self):
		"""Test that shortcodes appear in the generated prompt"""
		mock_shortcode = MagicMock()
		mock_shortcode.name1 = "Mobile Menu"
		mock_shortcode.category = "Navigation"
		mock_shortcode.description = "Hamburger menu for mobile"
		mock_shortcode.use_when = "All sites on mobile"
		mock_shortcode.shortcode = "<button class='hamburger'>☰</button>"

		mock_settings = MagicMock()
		mock_settings.shortcodes = [mock_shortcode]
		mock_settings.creativity_level = "balanced"
		mock_settings.default_style = "modern"
		mock_settings.use_modern_design = True
		mock_settings.default_site_type = "auto"
		mock_settings.allow_multipage = True

		prompt = get_collector_prompt(mock_settings)

		self.assertIn("Mobile Menu", prompt)
		self.assertIn("Navigation", prompt)
		self.assertIn("hamburger", prompt.lower())


class TestEndToEnd(FrappeTestCase):
	"""End-to-end integration tests"""

	@patch("builder.builder_ai.call_llm")
	def test_full_conversation_flow(self, mock_call_llm):
		"""Test complete conversation from start to page generation"""
		# Step 1: Start conversation
		mock_call_llm.return_value = json.dumps({
			"message": "Hello! What website would you like?",
			"site_context": {},
			"collection_complete": False
		})

		from builder.builder_ai import generate_page, send_message, start_conversation

		result = start_conversation(title="E2E Test")
		conversation_id = result["conversation_id"]

		try:
			# Step 2: Send messages
			mock_call_llm.return_value = json.dumps({
				"message": "Great! A florist site. What colors?",
				"site_context": {
					"business_name": "Fleur de Vie",
					"industry": "florist"
				},
				"collection_complete": False
			})
			result = send_message(conversation_id, "I want a site for my florist shop called Fleur de Vie")

			self.assertEqual(result["site_context"]["business_name"], "Fleur de Vie")

			# Step 3: Complete collection
			mock_call_llm.return_value = json.dumps({
				"message": "Perfect! I have everything I need.",
				"site_context": {
					"business_name": "Fleur de Vie",
					"industry": "florist",
					"style": {
						"primary_color": "#E91E63",
						"secondary_color": "#8BC34A",
						"text_color": "#333333"
					},
					"sections": [
						{"type": "hero", "headline": "Beautiful Flowers for Every Occasion"},
						{"type": "features", "headline": "Our Services"},
						{"type": "cta", "headline": "Order Now"}
					]
				},
				"collection_complete": True
			})
			result = send_message(conversation_id, "Use pink and green colors")

			self.assertTrue(result["collection_complete"])

			# Step 4: Generate page
			result = generate_page(conversation_id)

			self.assertTrue(result["success"])
			self.assertIn("blocks", result)
			self.assertGreater(len(result["blocks"]), 0)

			# Cleanup page
			if result.get("page_name"):
				frappe.delete_doc("Builder Page", result["page_name"])

		finally:
			frappe.delete_doc("Builder AI Conversation", conversation_id)

	def test_blocks_are_valid_json(self):
		"""Test that all generated blocks can be serialized to JSON"""
		context = {
			"business_name": "Test Company",
			"style": {
				"primary_color": "#3B82F6",
				"text_color": "#171717",
				"secondary_color": "#6B7280"
			},
			"sections": [
				{"type": "hero", "headline": "Welcome"},
				{"type": "features", "headline": "Features", "items": [
					{"title": "Fast", "description": "Lightning quick"},
					{"title": "Secure", "description": "Bank-level security"}
				]},
				{"type": "cta", "headline": "Get Started"},
				{"type": "footer"}
			]
		}

		blocks = generate_blocks_from_context(context)

		# Should be JSON serializable
		try:
			json_str = json.dumps(blocks)
			parsed = json.loads(json_str)
			self.assertEqual(len(parsed), len(blocks))
		except (TypeError, json.JSONDecodeError) as e:
			self.fail(f"Blocks are not valid JSON: {e}")
