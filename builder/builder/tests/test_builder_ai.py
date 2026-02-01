# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder_ai import (
	generate_block_id,
	generate_blocks_from_context,
	generate_single_page,
	generate_site,
	get_collector_prompt,
	get_cta_template,
	get_faq_template,
	get_features_template,
	get_footer_template,
	get_gallery_template,
	get_hero_template,
	get_llm_config,
	get_navbar_template,
	get_pricing_template,
	get_process_template,
	get_product_carousel_template,
	get_requires_features,
	get_shortcode_jinja,
	get_stats_template,
	get_team_template,
	get_testimonials_template,
	validate_and_fix_blocks,
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

	def test_get_footer_template_vitrine(self):
		"""Test minimal footer for vitrine site"""
		context = {
			"business_name": "My Shop",
			"functionality_type": "vitrine",
			"style": {}
		}

		footer = get_footer_template(context)

		self.assertEqual(footer["element"], "footer")
		# Minimal footer should have just one child container
		self.assertEqual(len(footer["children"]), 1)

	def test_get_footer_template_ecommerce(self):
		"""Test mega footer for e-commerce site"""
		context = {
			"business_name": "Online Store",
			"functionality_type": "ecommerce",
			"style": {
				"primary_color": "#3B82F6"
			},
			"contact_info": {
				"email": "test@example.com"
			}
		}

		footer = get_footer_template(context)

		self.assertEqual(footer["element"], "footer")
		# E-commerce footer should have more padding
		self.assertEqual(footer["baseStyles"]["paddingTop"], "80px")

	def test_get_navbar_template_vitrine(self):
		"""Test navbar for vitrine site (no e-commerce components)"""
		context = {
			"business_name": "My Business",
			"functionality_type": "vitrine",
			"style": {
				"text_color": "#171717"
			}
		}

		navbar = get_navbar_template(context)

		self.assertEqual(navbar["element"], "header")
		self.assertEqual(navbar["blockName"], "navbar")

		# Find navbar-actions child
		actions = None
		for child in navbar["children"]:
			if child.get("blockName") == "navbar-actions":
				actions = child
				break

		self.assertIsNotNone(actions)
		# Vitrine should have no cart, wishlist, user_menu, or search
		action_names = [c.get("blockName") for c in actions.get("children", [])]
		self.assertNotIn("navbar-cart", action_names)
		self.assertNotIn("navbar-wishlist", action_names)
		self.assertNotIn("navbar-user_menu", action_names)

	def test_get_navbar_template_ecommerce(self):
		"""Test navbar for e-commerce site (all components)"""
		context = {
			"business_name": "Online Store",
			"functionality_type": "ecommerce",
			"style": {
				"primary_color": "#3B82F6",
				"text_color": "#171717"
			}
		}

		navbar = get_navbar_template(context)

		self.assertEqual(navbar["element"], "header")

		# Find navbar-actions child
		actions = None
		for child in navbar["children"]:
			if child.get("blockName") == "navbar-actions":
				actions = child
				break

		self.assertIsNotNone(actions)
		# E-commerce should have cart, wishlist, user_menu, and search
		action_names = [c.get("blockName") for c in actions.get("children", [])]
		self.assertIn("navbar-cart", action_names)
		self.assertIn("navbar-wishlist", action_names)
		self.assertIn("navbar-user_menu", action_names)
		self.assertIn("navbar-search", action_names)

	def test_get_requires_features_vitrine(self):
		"""Test feature requirements for vitrine site"""
		context = {"functionality_type": "vitrine"}
		features = get_requires_features(context)

		self.assertFalse(features["cart"])
		self.assertFalse(features["wishlist"])
		self.assertFalse(features["user_menu"])
		self.assertFalse(features["search"])
		self.assertTrue(features["mobile_menu"])

	def test_get_requires_features_ecommerce(self):
		"""Test feature requirements for e-commerce site"""
		context = {"functionality_type": "ecommerce"}
		features = get_requires_features(context)

		self.assertTrue(features["cart"])
		self.assertTrue(features["wishlist"])
		self.assertTrue(features["user_menu"])
		self.assertTrue(features["search"])
		self.assertTrue(features["mobile_menu"])

	def test_get_shortcode_jinja_defaults(self):
		"""Test default Jinja code for shortcodes"""
		cart_jinja = get_shortcode_jinja("cart")
		self.assertIn("cart_component.html", cart_jinja)

		wishlist_jinja = get_shortcode_jinja("wishlist")
		self.assertIn("wishlist_component.html", wishlist_jinja)

		user_menu_jinja = get_shortcode_jinja("user_menu")
		self.assertIn("user_header.html", user_menu_jinja)

	def test_generate_blocks_from_context_default(self):
		"""Test block generation with default sections"""
		context = {
			"business_name": "My Company",
			"style": {}
		}

		blocks = generate_blocks_from_context(context)

		# Should have hero + features + cta = 3 blocks
		# (navbar and footer are now included via webpage.html template)
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

		# Should have 3 blocks: hero + features + cta
		# (navbar and footer are now included via webpage.html template)
		self.assertEqual(len(blocks), 3)

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
		# blocks[0] is hero (navbar/footer are now in webpage.html template)
		hero = blocks[0]

		self.assertIn("tabletStyles", hero)
		self.assertIn("mobileStyles", hero)
		self.assertIsInstance(hero["tabletStyles"], dict)
		self.assertIsInstance(hero["mobileStyles"], dict)

	def test_validate_and_fix_blocks_complete(self):
		"""Test validation with complete blocks"""
		blocks = [{
			"blockId": "abc123def",
			"element": "section",
			"blockName": "test-section",
			"innerHTML": "Test content",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {"padding": "20px"},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": []
		}]

		result = validate_and_fix_blocks(blocks)

		self.assertTrue(result["valid"])
		self.assertEqual(len(result["errors"]), 0)
		self.assertEqual(len(result["fixed_blocks"]), 1)

	def test_validate_and_fix_blocks_missing_fields(self):
		"""Test validation fixes missing fields"""
		# Block missing several required fields
		blocks = [{
			"element": "div",
			"innerHTML": "Test"
		}]

		result = validate_and_fix_blocks(blocks)

		# Should be valid after auto-fixes
		self.assertTrue(result["valid"])

		# Check that missing fields were added
		fixed_block = result["fixed_blocks"][0]
		self.assertIn("blockId", fixed_block)
		self.assertEqual(len(fixed_block["blockId"]), 9)
		self.assertIn("baseStyles", fixed_block)
		self.assertIn("mobileStyles", fixed_block)
		self.assertIn("tabletStyles", fixed_block)
		self.assertIn("rawStyles", fixed_block)
		self.assertIn("attributes", fixed_block)
		self.assertIn("customAttributes", fixed_block)
		self.assertIn("classes", fixed_block)
		self.assertIn("children", fixed_block)
		self.assertIn("dataKey", fixed_block)

	def test_validate_and_fix_blocks_invalid_blockid(self):
		"""Test validation fixes invalid blockId"""
		# Invalid blockId (too short, wrong case, etc.)
		blocks = [
			{"blockId": "short", "element": "div"},
			{"blockId": "UPPERCASE1", "element": "p"},
			{"blockId": "", "element": "span"},
		]

		result = validate_and_fix_blocks(blocks)

		# All blockIds should be fixed
		for block in result["fixed_blocks"]:
			self.assertEqual(len(block["blockId"]), 9)
			self.assertTrue(block["blockId"].isalnum())
			self.assertTrue(block["blockId"].islower())

	def test_validate_and_fix_blocks_nested_children(self):
		"""Test validation fixes nested children"""
		blocks = [{
			"element": "section",
			"children": [
				{"element": "div"},
				{
					"element": "div",
					"children": [
						{"element": "p"}
					]
				}
			]
		}]

		result = validate_and_fix_blocks(blocks)

		self.assertTrue(result["valid"])

		# Check nested children are also fixed
		fixed = result["fixed_blocks"][0]
		self.assertIn("blockId", fixed)
		self.assertIn("blockId", fixed["children"][0])
		self.assertIn("blockId", fixed["children"][1])
		self.assertIn("blockId", fixed["children"][1]["children"][0])

	def test_validate_and_fix_blocks_wrong_types(self):
		"""Test validation fixes wrong field types"""
		blocks = [{
			"blockId": "abc123def",
			"element": "div",
			"baseStyles": "should be dict",  # Wrong type
			"classes": "should be list",  # Wrong type
			"children": None  # Wrong type
		}]

		result = validate_and_fix_blocks(blocks)

		fixed = result["fixed_blocks"][0]
		self.assertIsInstance(fixed["baseStyles"], dict)
		self.assertIsInstance(fixed["classes"], list)
		self.assertIsInstance(fixed["children"], list)


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

		# Cleanup - delete conversation first (it has a link to the page)
		page_name = result.get("page_name")
		conversation.delete()
		if page_name:
			frappe.delete_doc("Builder Page", page_name, force=True)

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
		page_name = None  # Initialize for cleanup in finally block

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

			# Store page name for cleanup
			page_name = result.get("page_name")

		finally:
			# Delete conversation first (it has a link to the page)
			frappe.delete_doc("Builder AI Conversation", conversation_id)
			# Then delete the page
			if page_name:
				frappe.delete_doc("Builder Page", page_name, force=True)

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


class TestMultiPageGeneration(FrappeTestCase):
	"""Tests for multi-page site generation"""

	def test_generate_single_page_basic(self):
		"""Test single page generation with basic config"""
		from builder.builder_ai import generate_single_page

		page_config = {
			"name": "test-about",
			"route": "/about",
			"is_main": False,
			"title": "About Us",
			"sections": ["hero", "about", "cta"]
		}

		site_context = {
			"business_name": "Test Company",
			"style": {
				"primary_color": "#3B82F6",
				"text_color": "#171717"
			}
		}

		page_name = generate_single_page(page_config, site_context)

		# Verify page was created
		self.assertTrue(frappe.db.exists("Builder Page", page_name))

		# Check page properties
		page = frappe.get_doc("Builder Page", page_name)
		self.assertEqual(page.page_title, "About Us")
		self.assertEqual(page.route, "about")  # Route without leading /

		# Verify blocks
		blocks = json.loads(page.blocks or "[]")
		self.assertEqual(len(blocks), 3)  # hero, about, cta

		# Cleanup
		frappe.delete_doc("Builder Page", page_name)

	def test_generate_single_page_main(self):
		"""Test main page generation uses business name as route"""
		from builder.builder_ai import generate_single_page

		page_config = {
			"name": "home",
			"route": "/",
			"is_main": True,
			"title": "Home",
			"sections": ["hero", "features"]
		}

		site_context = {
			"business_name": "Awesome Corp",
			"style": {}
		}

		page_name = generate_single_page(page_config, site_context)

		page = frappe.get_doc("Builder Page", page_name)
		# Main page should use business name slug as route
		self.assertEqual(page.route, "awesome-corp")

		# Cleanup
		frappe.delete_doc("Builder Page", page_name)

	def test_generate_site_multi_page(self):
		"""Test full multi-page site generation"""
		from builder.builder_ai import generate_site

		# Create conversation with multi-page context
		site_context = {
			"business_name": "Multi Page Test",
			"site_type": "multi_page",
			"functionality_type": "vitrine",
			"style": {
				"primary_color": "#10B981"
			},
			"pages": [
				{
					"name": "home",
					"route": "/",
					"is_main": True,
					"title": "Accueil",
					"sections": ["hero", "features", "cta"]
				},
				{
					"name": "about",
					"route": "/about",
					"is_main": False,
					"title": "À propos",
					"sections": ["hero", "about"]
				},
				{
					"name": "contact",
					"route": "/contact",
					"is_main": False,
					"title": "Contact",
					"sections": ["hero", "contact"]
				}
			]
		}

		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Multi Page Test",
			"status": "collecting",
			"messages": "[]",
			"site_context": json.dumps(site_context)
		}).insert()

		try:
			result = generate_site(conversation.name)

			self.assertTrue(result["success"])
			self.assertEqual(result["total_pages"], 3)
			self.assertEqual(len(result["pages"]), 3)

			# Verify each page exists
			for page_info in result["pages"]:
				self.assertTrue(frappe.db.exists("Builder Page", page_info["name"]))

			# Verify main page
			self.assertIsNotNone(result["main_page"])

			# Cleanup pages
			for page_info in result["pages"]:
				frappe.delete_doc("Builder Page", page_info["name"], force=True)

		finally:
			conversation.delete()

	def test_generate_site_fallback_single_page(self):
		"""Test generate_site creates single page when no pages array"""
		from builder.builder_ai import generate_site

		# Context without pages array
		site_context = {
			"business_name": "Single Page Fallback",
			"style": {},
			"sections": [
				{"type": "hero"},
				{"type": "cta"}
			]
		}

		conversation = frappe.get_doc({
			"doctype": "Builder AI Conversation",
			"title": "Fallback Test",
			"status": "collecting",
			"messages": "[]",
			"site_context": json.dumps(site_context)
		}).insert()

		try:
			result = generate_site(conversation.name)

			self.assertTrue(result["success"])
			self.assertEqual(result["total_pages"], 1)

			# Cleanup
			for page_info in result["pages"]:
				frappe.delete_doc("Builder Page", page_info["name"], force=True)

		finally:
			conversation.delete()

	def test_navbar_links_match_pages(self):
		"""Test navbar menu items are built from pages array"""
		context = {
			"business_name": "Nav Test",
			"functionality_type": "vitrine",
			"site_type": "multi_page",
			"style": {},
			"pages": [
				{"name": "home", "route": "/", "is_main": True, "title": "Accueil"},
				{"name": "services", "route": "/services", "is_main": False, "title": "Nos Services"},
				{"name": "contact", "route": "/contact", "is_main": False, "title": "Contact"}
			]
		}

		navbar = get_navbar_template(context)

		# Find navbar-menu child to get menu items
		nav_menu = None
		for child in navbar["children"]:
			if child.get("blockName") == "navbar-menu":
				nav_menu = child
				break

		self.assertIsNotNone(nav_menu)

		# Extract links from menu items
		menu_links = []
		for item in nav_menu.get("children", []):
			if item.get("element") == "a":
				href = item.get("attributes", {}).get("href", "")
				menu_links.append(href)

		# Verify all page routes are in menu
		self.assertIn("/", menu_links)
		self.assertIn("/services", menu_links)
		self.assertIn("/contact", menu_links)

	def test_navbar_one_page_uses_anchors(self):
		"""Test navbar uses anchor links for one-page sites"""
		context = {
			"business_name": "One Page",
			"functionality_type": "vitrine",
			"site_type": "one_page",
			"style": {}
			# No pages array - should use default anchor links
		}

		navbar = get_navbar_template(context)

		# Find navbar-menu
		nav_menu = None
		for child in navbar["children"]:
			if child.get("blockName") == "navbar-menu":
				nav_menu = child
				break

		self.assertIsNotNone(nav_menu)

		# Extract links
		menu_links = []
		for item in nav_menu.get("children", []):
			if item.get("element") == "a":
				href = item.get("attributes", {}).get("href", "")
				menu_links.append(href)

		# Should have anchor links
		anchor_links = [link for link in menu_links if link.startswith("#")]
		self.assertGreater(len(anchor_links), 0, "One-page site should have anchor links")

	def test_collector_prompt_includes_multipage_instructions(self):
		"""Test collector prompt has multi-page instructions"""
		prompt = get_collector_prompt()

		# Check for multi-page related content
		self.assertIn("multi_page", prompt.lower())
		self.assertIn("route", prompt.lower())
		self.assertIn("is_main", prompt.lower())

	def test_page_schema_in_prompt(self):
		"""Test that page schema in prompt has required fields"""
		prompt = get_collector_prompt()

		# Check schema includes route and title
		self.assertIn('"route":', prompt)
		self.assertIn('"title":', prompt)
		self.assertIn('"is_main":', prompt)


class TestSectionTemplates(FrappeTestCase):
	"""Tests for all section template generators"""

	def setUp(self):
		"""Set up test context"""
		self.base_context = {
			"business_name": "Test Company",
			"industry": "technology",
			"style": {
				"primary_color": "#3B82F6",
				"secondary_color": "#6B7280",
				"text_color": "#171717",
				"background_color": "#ffffff"
			}
		}

	def test_get_team_template(self):
		"""Test team section template generation"""
		context = self.base_context.copy()
		context["section_team"] = {
			"headline": "Our Amazing Team",
			"items": [
				{"name": "John Doe", "role": "CEO", "image": "https://i.pravatar.cc/300?img=1"},
				{"name": "Jane Smith", "role": "CTO", "image": "https://i.pravatar.cc/300?img=2"},
			]
		}

		team = get_team_template(context)

		self.assertEqual(team["element"], "section")
		self.assertEqual(team["blockName"], "team")
		self.assertIn("children", team)

		# Find team grid
		container = team["children"][0]
		team_grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "team-grid":
				team_grid = child
				break

		self.assertIsNotNone(team_grid)
		# Should have 2 team members
		self.assertEqual(len(team_grid.get("children", [])), 2)

	def test_get_testimonials_template(self):
		"""Test testimonials section template generation"""
		context = self.base_context.copy()
		context["section_testimonials"] = {
			"headline": "What Clients Say",
			"items": [
				{"quote": "Great service!", "author": "Client A", "role": "CEO"},
				{"quote": "Highly recommend!", "author": "Client B", "role": "Manager"},
			]
		}

		testimonials = get_testimonials_template(context)

		self.assertEqual(testimonials["element"], "section")
		self.assertEqual(testimonials["blockName"], "testimonials")

		# Find testimonials grid
		container = testimonials["children"][0]
		grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "testimonials-grid":
				grid = child
				break

		self.assertIsNotNone(grid)
		self.assertEqual(len(grid.get("children", [])), 2)

	def test_get_pricing_template(self):
		"""Test pricing section template generation"""
		context = self.base_context.copy()
		context["section_pricing"] = {
			"headline": "Our Plans",
			"items": [
				{"name": "Basic", "price": "10€", "features": ["Feature 1"]},
				{"name": "Pro", "price": "29€", "features": ["Feature 1", "Feature 2"], "highlighted": True},
			]
		}

		pricing = get_pricing_template(context)

		self.assertEqual(pricing["element"], "section")
		self.assertEqual(pricing["blockName"], "pricing")

		# Find pricing grid
		container = pricing["children"][0]
		grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "pricing-grid":
				grid = child
				break

		self.assertIsNotNone(grid)
		self.assertEqual(len(grid.get("children", [])), 2)

	def test_get_gallery_template(self):
		"""Test gallery section template generation"""
		context = self.base_context.copy()
		context["section_gallery"] = {
			"headline": "Our Gallery",
			"items": [
				{"src": "https://example.com/img1.jpg", "alt": "Image 1"},
				{"src": "https://example.com/img2.jpg", "alt": "Image 2"},
				{"src": "https://example.com/img3.jpg", "alt": "Image 3"},
			]
		}

		gallery = get_gallery_template(context)

		self.assertEqual(gallery["element"], "section")
		self.assertEqual(gallery["blockName"], "gallery")

		# Find gallery grid
		container = gallery["children"][0]
		grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "gallery-grid":
				grid = child
				break

		self.assertIsNotNone(grid)
		self.assertEqual(len(grid.get("children", [])), 3)

	def test_get_faq_template(self):
		"""Test FAQ section template generation"""
		context = self.base_context.copy()
		context["section_faq"] = {
			"headline": "FAQ",
			"items": [
				{"question": "Question 1?", "answer": "Answer 1"},
				{"question": "Question 2?", "answer": "Answer 2"},
			]
		}

		faq = get_faq_template(context)

		self.assertEqual(faq["element"], "section")
		self.assertEqual(faq["blockName"], "faq")

		# Find FAQ list
		container = faq["children"][0]
		faq_list = None
		for child in container.get("children", []):
			if child.get("blockName") == "faq-list":
				faq_list = child
				break

		self.assertIsNotNone(faq_list)
		self.assertEqual(len(faq_list.get("children", [])), 2)

	def test_get_stats_template(self):
		"""Test stats section template generation"""
		context = self.base_context.copy()
		context["section_stats"] = {
			"items": [
				{"value": "100+", "label": "Clients"},
				{"value": "50+", "label": "Projects"},
			]
		}

		stats = get_stats_template(context)

		self.assertEqual(stats["element"], "section")
		self.assertEqual(stats["blockName"], "stats")

		# Find stats container
		container = stats["children"][0]
		self.assertEqual(len(container.get("children", [])), 2)

	def test_get_process_template(self):
		"""Test process section template generation"""
		context = self.base_context.copy()
		context["section_process"] = {
			"headline": "Our Process",
			"items": [
				{"title": "Step 1", "description": "First step"},
				{"title": "Step 2", "description": "Second step"},
				{"title": "Step 3", "description": "Third step"},
			]
		}

		process = get_process_template(context)

		self.assertEqual(process["element"], "section")
		self.assertEqual(process["blockName"], "process")

		# Find process steps
		container = process["children"][0]
		steps = None
		for child in container.get("children", []):
			if child.get("blockName") == "process-steps":
				steps = child
				break

		self.assertIsNotNone(steps)
		self.assertEqual(len(steps.get("children", [])), 3)

	def test_get_product_carousel_template(self):
		"""Test product carousel section template generation"""
		context = self.base_context.copy()
		context["section_product_carousel"] = {
			"headline": "Featured Products",
			"items": [
				{"name": "Product 1", "price": "29€", "image": "https://example.com/p1.jpg"},
				{"name": "Product 2", "price": "49€", "image": "https://example.com/p2.jpg"},
			]
		}

		carousel = get_product_carousel_template(context)

		self.assertEqual(carousel["element"], "section")
		self.assertEqual(carousel["blockName"], "product-carousel")

		# Find products grid
		container = carousel["children"][0]
		grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "products-grid":
				grid = child
				break

		self.assertIsNotNone(grid)
		self.assertEqual(len(grid.get("children", [])), 2)

	def test_all_templates_have_required_structure(self):
		"""Test that all section templates have required block structure"""
		templates = [
			get_team_template,
			get_testimonials_template,
			get_pricing_template,
			get_gallery_template,
			get_faq_template,
			get_stats_template,
			get_process_template,
			get_product_carousel_template,
		]

		for template_fn in templates:
			block = template_fn(self.base_context)

			# Required fields
			self.assertIn("blockId", block, f"{template_fn.__name__} missing blockId")
			self.assertIn("element", block, f"{template_fn.__name__} missing element")
			self.assertIn("blockName", block, f"{template_fn.__name__} missing blockName")
			self.assertIn("baseStyles", block, f"{template_fn.__name__} missing baseStyles")
			self.assertIn("children", block, f"{template_fn.__name__} missing children")

			# Block ID should be 9 characters
			self.assertEqual(len(block["blockId"]), 9, f"{template_fn.__name__} has invalid blockId length")

			# Element should be section
			self.assertEqual(block["element"], "section", f"{template_fn.__name__} element should be section")

	def test_templates_use_context_colors(self):
		"""Test that templates use colors from context.style"""
		context = self.base_context.copy()
		context["style"]["primary_color"] = "#FF5733"
		context["style"]["text_color"] = "#111111"

		# Test a template that uses primary_color prominently
		pricing = get_pricing_template(context)

		# The highlighted plan should use primary_color
		container = pricing["children"][0]
		grid = None
		for child in container.get("children", []):
			if child.get("blockName") == "pricing-grid":
				grid = child
				break

		# Find a card with backgroundColor matching primary
		found_primary = False
		for card in grid.get("children", []):
			bg = card.get("baseStyles", {}).get("backgroundColor", "")
			if bg == "#FF5733":
				found_primary = True
				break

		self.assertTrue(found_primary, "Pricing template should use primary_color")

	def test_section_generators_include_new_templates(self):
		"""Test that generate_blocks_from_context uses all new templates"""
		context = self.base_context.copy()
		context["sections"] = [
			{"type": "hero"},
			{"type": "team"},
			{"type": "testimonials"},
			{"type": "pricing"},
			{"type": "faq"},
			{"type": "stats"},
			{"type": "process"},
			{"type": "gallery"},
		]

		blocks = generate_blocks_from_context(context)

		# Should have 8 blocks
		self.assertEqual(len(blocks), 8)

		# Check block names
		block_names = [b.get("blockName") for b in blocks]
		self.assertIn("hero", block_names)
		self.assertIn("team", block_names)
		self.assertIn("testimonials", block_names)
		self.assertIn("pricing", block_names)
		self.assertIn("faq", block_names)
		self.assertIn("stats", block_names)
		self.assertIn("process", block_names)
		self.assertIn("gallery", block_names)
