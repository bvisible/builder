"""
Builder AI - AI-powered website generation for Frappe Builder

This module provides:
1. Chat-based information collection
2. Structured site context extraction
3. Block generation from context
4. AI-powered image generation
"""

import base64
import hashlib
import json
import random
import re
import string
from typing import Any, Optional, List, Literal

import frappe
import requests
from frappe import _
from frappe.integrations.utils import make_post_request

# Try to import Pydantic for structured output
try:
	from pydantic import BaseModel, Field
	PYDANTIC_AVAILABLE = True
except ImportError:
	PYDANTIC_AVAILABLE = False
	BaseModel = object  # Fallback


# =============================================================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# =============================================================================

if PYDANTIC_AVAILABLE:
	class FrappeStyles(BaseModel):
		"""CSS styles in camelCase format for Frappe Builder."""
		display: Optional[str] = None
		flexDirection: Optional[str] = None
		alignItems: Optional[str] = None
		justifyContent: Optional[str] = None
		padding: Optional[str] = None
		paddingTop: Optional[str] = None
		paddingBottom: Optional[str] = None
		paddingLeft: Optional[str] = None
		paddingRight: Optional[str] = None
		margin: Optional[str] = None
		marginTop: Optional[str] = None
		marginBottom: Optional[str] = None
		backgroundColor: Optional[str] = None
		backgroundImage: Optional[str] = None
		backgroundSize: Optional[str] = None
		backgroundPosition: Optional[str] = None
		color: Optional[str] = None
		fontSize: Optional[str] = None
		fontWeight: Optional[str] = None
		fontFamily: Optional[str] = None
		textAlign: Optional[str] = None
		lineHeight: Optional[str] = None
		letterSpacing: Optional[str] = None
		borderRadius: Optional[str] = None
		border: Optional[str] = None
		boxShadow: Optional[str] = None
		gap: Optional[str] = None
		width: Optional[str] = None
		maxWidth: Optional[str] = None
		minWidth: Optional[str] = None
		height: Optional[str] = None
		minHeight: Optional[str] = None
		maxHeight: Optional[str] = None
		position: Optional[str] = None
		top: Optional[str] = None
		left: Optional[str] = None
		right: Optional[str] = None
		bottom: Optional[str] = None
		zIndex: Optional[str] = None
		overflow: Optional[str] = None
		opacity: Optional[str] = None
		transform: Optional[str] = None
		transition: Optional[str] = None
		flexWrap: Optional[str] = None
		flexGrow: Optional[str] = None
		flexShrink: Optional[str] = None
		gridTemplateColumns: Optional[str] = None
		gridTemplateRows: Optional[str] = None
		gridGap: Optional[str] = None

	class FrappeBlockChild(BaseModel):
		"""A child block within a Frappe Builder block."""
		blockId: str = Field(description="Unique ID, 9 lowercase alphanumeric chars")
		element: str = Field(description="HTML element: div, section, h1, h2, h3, p, span, button, a, img, ul, li, nav, header, footer")
		blockName: Optional[str] = Field(default=None, description="Semantic name for the block")
		innerHTML: Optional[str] = Field(default="", description="Text content for text elements")
		attributes: Optional[dict] = Field(default_factory=dict, description="HTML attributes like href, src")
		baseStyles: Optional[dict] = Field(default_factory=dict, description="Desktop CSS styles in camelCase")
		mobileStyles: Optional[dict] = Field(default_factory=dict, description="Mobile CSS overrides")
		children: Optional[List["FrappeBlockChild"]] = Field(default_factory=list, description="Nested child blocks")

	class FrappeBlock(BaseModel):
		"""A top-level Frappe Builder block (section)."""
		blockId: str = Field(description="Unique ID, 9 lowercase alphanumeric chars")
		element: str = Field(default="section", description="Usually 'section' for top-level blocks")
		blockName: str = Field(description="Semantic name like 'hero', 'about', 'features'")
		innerHTML: Optional[str] = Field(default="", description="Text content if any")
		attributes: Optional[dict] = Field(default_factory=dict)
		customAttributes: Optional[dict] = Field(default_factory=dict)
		classes: Optional[List[str]] = Field(default_factory=list)
		dataKey: Optional[str] = Field(default=None)
		baseStyles: dict = Field(default_factory=dict, description="Desktop CSS styles")
		tabletStyles: Optional[dict] = Field(default_factory=dict, description="Tablet CSS overrides")
		mobileStyles: Optional[dict] = Field(default_factory=dict, description="Mobile CSS overrides")
		rawStyles: Optional[dict] = Field(default_factory=dict, description="Raw CSS like hover states")
		children: List[FrappeBlockChild] = Field(default_factory=list, description="Child elements")

	# Rebuild for forward references
	FrappeBlockChild.model_rebuild()
	FrappeBlock.model_rebuild()

	class SectionsList(BaseModel):
		"""List of sections to generate."""
		sections: List[str] = Field(description="List of section types like 'hero', 'about', 'features', 'contact'")


# =============================================================================
# MULTI-PASS PAGE GENERATOR
# =============================================================================

def generate_page_multipass(page_config: dict, site_context: dict) -> list:
	"""
	Generate page blocks using a multi-pass LLM approach for better reliability.

	This approach:
	1. Pass 1: Analyze requirements and list sections needed
	2. Pass 2: Generate each section one at a time with structured output
	3. Pass 3: Assemble, validate and fix all blocks

	Args:
		page_config: Page configuration with name, route, title, sections
		site_context: Full site context for styling and business info

	Returns:
		List of validated blocks, or None if generation fails
	"""
	if not PYDANTIC_AVAILABLE:
		frappe.log_error("Pydantic not available", "Multi-pass generation requires pydantic. Falling back to single-pass.")
		return generate_page_with_llm(page_config, site_context)

	title = page_config.get("title", page_config.get("name", _("Page")))
	requested_sections = page_config.get("sections", ["hero"])
	is_main = page_config.get("is_main", False)

	# Extract style info
	style = site_context.get("style", {})
	business_name = site_context.get("business_name", "Business")
	industry = site_context.get("industry", "General")
	tagline = site_context.get("tagline", "")
	primary_color = style.get("primary_color", "#171717")
	secondary_color = style.get("secondary_color", "#6B7280")
	background_color = style.get("background_color", "#ffffff")

	# Design context for all prompts
	design_context = f"""
BUSINESS CONTEXT:
- Business Name: {business_name}
- Industry: {industry}
- Tagline: {tagline}
- Page Title: {title}
- Is Homepage: {is_main}

COLOR PALETTE:
- Primary: {primary_color}
- Secondary: {secondary_color}
- Background: {background_color}

DESIGN RULES:
- Use camelCase for all CSS properties (backgroundColor, not background-color)
- Use the exact colors from the palette
- Ensure good contrast for readability
- Make designs responsive (provide mobileStyles)
- Use modern design patterns (flexbox, grid)
- Keep blockId as exactly 9 lowercase alphanumeric characters
"""

	all_blocks = []

	try:
		# Normalize sections to list of strings
		section_names = []
		for s in requested_sections:
			if isinstance(s, str):
				section_names.append(s)
			elif isinstance(s, dict):
				section_names.append(s.get("type", "content"))

		# PASS 2: Generate each section one at a time
		for section_name in section_names:
			section_block = _generate_single_section(
				section_name=section_name,
				design_context=design_context,
				site_context=site_context,
				section_index=len(all_blocks)
			)
			if section_block:
				all_blocks.append(section_block)

		if not all_blocks:
			frappe.log_error("Multi-pass generation failed", f"No blocks generated for page: {title}")
			return None

		# PASS 3: Validate and fix all blocks
		validated = validate_and_fix_blocks(all_blocks)

		if validated["errors"]:
			frappe.log_error(
				"Multi-pass validation issues",
				f"Page: {title}\nIssues: {json.dumps(validated['errors'][:10], indent=2)}"
			)

		# Fix fake image URLs
		fixed_blocks = fix_fake_image_urls_in_blocks(validated["fixed_blocks"], industry)

		return fixed_blocks

	except Exception as e:
		frappe.log_error("Multi-pass generation error", f"Page: {title}\nError: {str(e)}")
		return None


def _generate_single_section(section_name: str, design_context: str, site_context: dict, section_index: int = 0) -> dict:
	"""
	Generate a single section block using structured output.

	Args:
		section_name: Type of section (hero, about, features, etc.)
		design_context: Design rules and business context
		site_context: Full site context
		section_index: Index for unique IDs

	Returns:
		Block dictionary or None if failed
	"""
	# Section-specific prompts
	section_prompts = {
		"hero": f"""Create a HERO section with:
- Full-width background with the primary color or a gradient
- Large headline text with the business name or tagline
- A subtitle/description paragraph
- One or two call-to-action buttons
- Minimum height of 80vh for impact
- Centered content with good padding""",

		"about": f"""Create an ABOUT section with:
- A heading like "About Us" or "Our Story"
- 2-3 paragraphs of descriptive text about the business
- Optional image placeholder on one side (use flexbox row layout)
- Good padding and readable typography
- Background that contrasts with hero""",

		"services": f"""Create a SERVICES/FEATURES section with:
- A heading like "Our Services" or "What We Offer"
- 3-4 service cards in a grid or flex layout
- Each card with an icon placeholder, title, and short description
- Consistent styling across all cards
- Good spacing between cards""",

		"features": f"""Create a FEATURES section with:
- A heading highlighting key features
- 3-4 feature items with icons and descriptions
- Grid or flex layout for responsive display
- Visual hierarchy with titles and descriptions""",

		"contact": f"""Create a CONTACT section with:
- A heading like "Contact Us" or "Get in Touch"
- Contact information (placeholder text for address, phone, email)
- A simple contact form layout (just visual, with input placeholders)
- Good spacing and clear layout""",

		"testimonials": f"""Create a TESTIMONIALS section with:
- A heading like "What Our Customers Say"
- 2-3 testimonial cards with quote, author name, and role
- Styled quote marks or icons
- Grid or carousel-style layout""",

		"cta": f"""Create a CALL-TO-ACTION section with:
- Bold headline encouraging action
- Brief supporting text
- Prominent button(s)
- Eye-catching background color or gradient
- Centered layout""",

		"footer": f"""Create a FOOTER section with:
- Business name and copyright
- Navigation links placeholder
- Social media icons placeholder
- Dark background with light text
- Multi-column layout"""
	}

	# Get specific prompt or generic one
	section_specific = section_prompts.get(section_name.lower(), f"""Create a {section_name.upper()} section with:
- Appropriate heading for this section type
- Relevant content structure for {section_name}
- Good typography and spacing
- Responsive design""")

	prompt = f"""You are a professional UI designer creating Frappe Builder blocks.

{design_context}

TASK: Generate a single {section_name.upper()} section block.

{section_specific}

CRITICAL REQUIREMENTS:
1. Return a SINGLE JSON object (not an array)
2. The blockId MUST be exactly 9 lowercase alphanumeric characters (e.g., "abc123xyz")
3. Use element "section" for the outer block
4. Include children array with nested elements (h1, h2, p, button, div, etc.)
5. All CSS properties in camelCase (backgroundColor, fontSize, etc.)
6. Provide realistic text content related to {site_context.get('business_name', 'the business')}

Return ONLY the JSON object, no markdown, no explanation."""

	try:
		# Use get_llm_config() to get full config including API key
		config = get_llm_config()
		response = call_ollama_structured(
			prompt=prompt,
			schema=FrappeBlock.model_json_schema() if PYDANTIC_AVAILABLE else None,
			model=config.get("ollama_model"),
			config=config,
			temperature=0.3  # Lower for more consistent structure
		)

		if not response:
			return None

		# Parse the response
		block_dict = _parse_section_response(response, section_name, section_index)
		return block_dict

	except Exception as e:
		frappe.log_error("Section generation error", f"Section: {section_name}\nError: {str(e)}")
		return None


def _parse_section_response(response: str, section_name: str, section_index: int) -> dict:
	"""Parse LLM response into a block dictionary with error recovery."""
	if not response:
		return None

	# Clean the response
	cleaned = clean_json_comments(response)

	# Extract from markdown code blocks if present
	if "```json" in cleaned:
		match = re.search(r'```json\s*([\s\S]*?)\s*```', cleaned)
		if match:
			cleaned = match.group(1)
	elif "```" in cleaned:
		match = re.search(r'```\s*([\s\S]*?)\s*```', cleaned)
		if match:
			cleaned = match.group(1)

	# Fix newlines in strings
	def fix_newlines(s):
		result = []
		in_string = False
		escape_next = False
		for c in s:
			if escape_next:
				result.append(c)
				escape_next = False
			elif c == '\\':
				result.append(c)
				escape_next = True
			elif c == '"':
				result.append(c)
				in_string = not in_string
			elif c == '\n' and in_string:
				result.append(' ')
			else:
				result.append(c)
		return ''.join(result)

	cleaned = fix_newlines(cleaned)
	cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)

	# Repair broken URLs
	cleaned = re.sub(r'"url\(https?:[^)"]*\s+"([a-zA-Z])', r'"none", "\1', cleaned)
	cleaned = re.sub(r'"https?://[^"]*\s{2,}[^"]*"', '""', cleaned)

	try:
		block = json.loads(cleaned.strip())
	except json.JSONDecodeError:
		# Try to extract just the object if there's extra content
		match = re.search(r'\{[\s\S]*\}', cleaned)
		if match:
			try:
				block = json.loads(match.group(0))
			except json.JSONDecodeError:
				return None
		else:
			return None

	# Handle if LLM returned an array with one item
	if isinstance(block, list):
		if len(block) > 0:
			block = block[0]
		else:
			return None

	# Ensure it's a dict
	if not isinstance(block, dict):
		return None

	# Set default blockName if missing
	if not block.get("blockName"):
		block["blockName"] = f"{section_name}-{section_index}"

	return block


def call_ollama_structured(prompt: str, schema: dict, model: str, config: dict, temperature: float = 0.3) -> str:
	"""
	Call Ollama with structured output format.

	Args:
		prompt: The prompt to send
		schema: JSON schema for structured output (optional)
		model: Model name
		config: AI configuration
		temperature: Generation temperature

	Returns:
		Response content string
	"""
	base_url = config["ollama_base_url"].rstrip("/")
	api_key = config.get("ollama_api_key")
	timeout = config.get("ollama_timeout", 120)

	# Use OpenAI-compatible endpoint for remote Ollama
	use_openai_compat = bool(api_key) or "/v1" in base_url

	headers = {
		"Content-Type": "application/json",
		"User-Agent": "Mozilla/5.0 (compatible; BuilderAI/1.0)"
	}
	if api_key:
		headers["X-API-Key"] = api_key

	messages = [{"role": "user", "content": prompt}]

	if use_openai_compat:
		if not base_url.endswith("/v1"):
			base_url = f"{base_url}/v1"
		url = f"{base_url}/chat/completions"

		payload = {
			"model": model,
			"messages": messages,
			"temperature": temperature,
		}
		# Add JSON format if schema provided
		if schema:
			payload["response_format"] = {"type": "json_object"}
	else:
		url = f"{base_url}/api/chat"
		payload = {
			"model": model,
			"messages": messages,
			"stream": False,
			"options": {"temperature": temperature},
			"format": "json"
		}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=timeout)
		response.raise_for_status()
		result = response.json()

		if use_openai_compat:
			message = result.get("choices", [{}])[0].get("message", {})
			content = message.get("content", "")
			# Fallback for reasoning models
			if not content and message.get("reasoning"):
				content = message.get("reasoning", "")
		else:
			content = result.get("message", {}).get("content", "")

		return content

	except requests.exceptions.Timeout:
		frappe.log_error("Ollama timeout", f"Model: {model}, URL: {url}")
		return None
	except requests.exceptions.RequestException as e:
		frappe.log_error("Ollama request error", f"Error: {str(e)}")
		return None


def generate_block_id() -> str:
	"""Generate a unique 9-character block ID."""
	return "".join(random.choices(string.ascii_lowercase + string.digits, k=9))


# =============================================================================
# BLOCK VALIDATION
# =============================================================================

def validate_and_fix_blocks(blocks: list) -> dict:
	"""
	Validate block structure and auto-fix common issues.

	Ensures all blocks have the required fields for Builder editability:
	- blockId (9 lowercase alphanumeric chars)
	- All required dict fields (baseStyles, mobileStyles, tabletStyles, rawStyles, attributes, customAttributes)
	- All required array fields (classes, children)
	- dataKey and innerHTML fields

	Args:
		blocks: List of block dictionaries to validate

	Returns:
		Dict with:
		- valid: True if no critical errors (auto-fixes don't count as errors)
		- errors: List of issues found (informational)
		- fixed_blocks: The corrected blocks list
	"""
	errors = []

	def fix_block(block: dict, path: str = "root") -> list:
		"""Recursively validate and fix a single block."""
		issues = []

		if not isinstance(block, dict):
			issues.append(f"{path}: Block is not a dictionary")
			return issues

		# Required dictionary fields (must exist, can be empty {})
		required_dicts = ["baseStyles", "mobileStyles", "tabletStyles", "rawStyles", "attributes", "customAttributes"]
		for field in required_dicts:
			if field not in block or block[field] is None:
				block[field] = {}
				issues.append(f"{path}: Added missing {field}")
			elif not isinstance(block[field], dict):
				block[field] = {}
				issues.append(f"{path}: Fixed {field} (was not dict)")

		# Required array fields (must exist, can be empty [])
		required_arrays = ["classes", "children"]
		for field in required_arrays:
			if field not in block or block[field] is None:
				block[field] = []
				issues.append(f"{path}: Added missing {field}")
			elif not isinstance(block[field], list):
				block[field] = []
				issues.append(f"{path}: Fixed {field} (was not list)")

		# Fix blockId - must be exactly 9 lowercase alphanumeric chars
		block_id = block.get("blockId", "")
		if not block_id or not isinstance(block_id, str) or len(block_id) != 9 or not block_id.isalnum() or not block_id.islower():
			block["blockId"] = generate_block_id()
			issues.append(f"{path}: Fixed blockId")

		# Ensure element exists
		if "element" not in block or not block["element"]:
			block["element"] = "div"
			issues.append(f"{path}: Added default element 'div'")

		# Ensure dataKey exists (can be null)
		if "dataKey" not in block:
			block["dataKey"] = None

		# Ensure innerHTML exists - copy from 'text' if present (LLM often uses 'text' instead of 'innerHTML')
		if "innerHTML" not in block or not block["innerHTML"]:
			if block.get("text"):
				block["innerHTML"] = block.pop("text")
				issues.append(f"{path}: Moved text to innerHTML")
			else:
				block["innerHTML"] = ""

		# Remove 'text' field if it exists (Frappe Builder uses innerHTML)
		if "text" in block:
			block.pop("text")

		# Also copy 'styles' to 'baseStyles' if baseStyles is empty (LLM sometimes uses 'styles')
		if not block.get("baseStyles") and block.get("styles"):
			block["baseStyles"] = block.pop("styles")
			issues.append(f"{path}: Moved styles to baseStyles")

		# Remove 'style' field (singular) - copy to baseStyles
		if block.get("style"):
			if not block.get("baseStyles"):
				block["baseStyles"] = block.pop("style")
				issues.append(f"{path}: Moved style to baseStyles")
			else:
				block.pop("style")

		# Ensure blockName exists
		if "blockName" not in block or not block["blockName"]:
			block["blockName"] = f"{block['element']}-block"

		# Recursively fix children
		for i, child in enumerate(block.get("children", [])):
			child_issues = fix_block(child, f"{path}.children[{i}]")
			issues.extend(child_issues)

		return issues

	# Ensure blocks is a list
	if not isinstance(blocks, list):
		if isinstance(blocks, dict):
			blocks = [blocks]
		else:
			return {
				"valid": False,
				"errors": ["Blocks must be a list or dict"],
				"fixed_blocks": []
			}

	# Fix each block
	for i, block in enumerate(blocks):
		block_errors = fix_block(block, f"blocks[{i}]")
		errors.extend(block_errors)

	# Count actual errors vs auto-fixes
	critical_errors = [e for e in errors if "Added missing" not in e and "Fixed" not in e]

	return {
		"valid": len(critical_errors) == 0,
		"errors": errors,
		"fixed_blocks": blocks
	}


def fix_fake_image_urls_in_blocks(blocks: list, industry: str = "") -> list:
	"""
	Fix fake/placeholder image URLs in blocks by replacing them with real Unsplash URLs.

	LLM-generated blocks often contain fake image URLs like:
	- url(/files/fake-image.png)
	- /files/business-hero.jpg
	- placeholder.jpg

	This function detects these and replaces them with appropriate Unsplash images
	based on the industry context.

	Args:
		blocks: List of block dictionaries
		industry: Business industry for selecting appropriate images

	Returns:
		Blocks with fixed image URLs
	"""
	import re

	# Get Unsplash fallback URL for this industry
	fallback_url = get_unsplash_fallback(industry, "hero")

	# Additional industry-specific images for variety
	industry_images = _get_industry_image_set(industry)

	def get_image_for_context(block_name: str, section_index: int = 0) -> str:
		"""Get appropriate image URL based on block context."""
		block_name_lower = (block_name or "").lower()

		# Use different images based on block type
		if "hero" in block_name_lower:
			return industry_images.get("hero", fallback_url)
		elif "about" in block_name_lower:
			return industry_images.get("about", fallback_url)
		elif "feature" in block_name_lower or "card" in block_name_lower:
			# Rotate through feature images
			feature_imgs = industry_images.get("features", [fallback_url])
			return feature_imgs[section_index % len(feature_imgs)]
		elif "team" in block_name_lower or "avatar" in block_name_lower:
			return f"https://i.pravatar.cc/300?img={section_index + 1}"
		elif "product" in block_name_lower:
			return industry_images.get("product", fallback_url)
		elif "gallery" in block_name_lower:
			return industry_images.get("gallery", fallback_url)
		else:
			return fallback_url

	def is_fake_url(url: str) -> bool:
		"""Check if URL is likely fake/placeholder. Replace ALL /files/ URLs with Unsplash."""
		if not url:
			return False

		url_lower = url.lower().strip()

		# "none" is a placeholder from JSON repair - always replace
		if url_lower == "none":
			return True

		# Real URL patterns - NEVER replace these
		real_patterns = [
			"unsplash.com",
			"images.unsplash.com",
			"pravatar.cc",
			"picsum.photos",
			"cloudinary.com",
			"imgur.com",
		]

		for pattern in real_patterns:
			if pattern in url_lower:
				return False

		# ALL /files/ URLs are considered fake - replace with Unsplash
		# (LLM generates fake filenames that don't exist)
		if "/files/" in url_lower:
			return True

		# Other fake patterns
		fake_patterns = ["placeholder", "example.com", "fake-", "dummy", "lorem"]
		for pattern in fake_patterns:
			if pattern in url_lower:
				return True

		return False

	def fix_block(block: dict, section_index: int = 0) -> None:
		"""Recursively fix image URLs in a block."""
		if not isinstance(block, dict):
			return

		block_name = block.get("blockName", "")

		# Fix backgroundImage in styles
		for style_key in ["baseStyles", "tabletStyles", "mobileStyles"]:
			styles = block.get(style_key, {})
			if isinstance(styles, dict) and "backgroundImage" in styles:
				bg_image = styles["backgroundImage"]
				# Handle "none" directly (from JSON repair)
				if bg_image == "none" or bg_image == "url(none)":
					new_url = get_image_for_context(block_name, section_index)
					styles["backgroundImage"] = f"url({new_url})"
					continue
				# Extract URL from url(...) format
				url_match = re.search(r'url\(([^)]+)\)', bg_image)
				if url_match:
					url = url_match.group(1).strip("'\"")
					if is_fake_url(url):
						new_url = get_image_for_context(block_name, section_index)
						styles["backgroundImage"] = f"url({new_url})"

		# Fix src attribute for img elements
		attributes = block.get("attributes", {})
		if isinstance(attributes, dict) and "src" in attributes:
			src = attributes["src"]
			if is_fake_url(src):
				attributes["src"] = get_image_for_context(block_name, section_index)

		# Recursively fix children
		children = block.get("children", [])
		for i, child in enumerate(children):
			fix_block(child, i)

	# Fix all blocks
	for i, block in enumerate(blocks):
		fix_block(block, i)

	return blocks


def _get_industry_image_set(industry: str) -> dict:
	"""
	Get a set of Unsplash images appropriate for the industry.

	Returns dict with keys: hero, about, features (list), product, gallery
	"""
	industry_lower = (industry or "").lower()

	# Curated image sets by industry
	image_sets = {
		"boulangerie": {
			"hero": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=600&h=400&fit=crop&q=80",  # Bread
				"https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&h=400&fit=crop&q=80",  # Croissants
				"https://images.unsplash.com/photo-1517433670267-30f0c89a2a5a?w=600&h=400&fit=crop&q=80",  # Pastries
			],
			"product": "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1486427944544-364c4e1a2103?w=800&h=600&fit=crop&q=80",
		},
		"bakery": {
			"hero": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1517433670267-30f0c89a2a5a?w=600&h=400&fit=crop&q=80",
			],
			"product": "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1486427944544-364c4e1a2103?w=800&h=600&fit=crop&q=80",
		},
		"fleuriste": {
			"hero": "https://images.unsplash.com/photo-1487530811176-3780de880c2d?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1487530811176-3780de880c2d?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1561181286-d3fee7d55364?w=600&h=400&fit=crop&q=80",
			],
			"product": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1487530811176-3780de880c2d?w=800&h=600&fit=crop&q=80",
		},
		"restaurant": {
			"hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&h=400&fit=crop&q=80",
			],
			"product": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&h=600&fit=crop&q=80",
		},
		"assurance": {
			"hero": "https://images.unsplash.com/photo-1560472354651-f29a5a94f6e5?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1560472354651-f29a5a94f6e5?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=600&h=400&fit=crop&q=80",
			],
			"product": "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=600&fit=crop&q=80",
		},
		"artisan": {
			"hero": "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?w=1600&h=900&fit=crop&q=80",
			"about": "https://images.unsplash.com/photo-1473188588951-80fc9c4bf5a8?w=1600&h=900&fit=crop&q=80",
			"features": [
				"https://images.unsplash.com/photo-1452860606245-08befc0ff44b?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1473188588951-80fc9c4bf5a8?w=600&h=400&fit=crop&q=80",
				"https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=600&h=400&fit=crop&q=80",
			],
			"product": "https://images.unsplash.com/photo-1473188588951-80fc9c4bf5a8?w=600&h=600&fit=crop&q=80",
			"gallery": "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?w=800&h=600&fit=crop&q=80",
		},
	}

	# Find matching industry
	for key, images in image_sets.items():
		if key in industry_lower:
			return images

	# Default professional images
	return {
		"hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&h=900&fit=crop&q=80",
		"about": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&h=900&fit=crop&q=80",
		"features": [
			"https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&h=400&fit=crop&q=80",
			"https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&h=400&fit=crop&q=80",
			"https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=400&fit=crop&q=80",
		],
		"product": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&h=600&fit=crop&q=80",
		"gallery": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=600&fit=crop&q=80",
	}


# =============================================================================
# IMAGE GENERATION
# =============================================================================

def get_image_generation_config() -> dict:
	"""Get configuration for image generation from settings."""
	settings = frappe.get_single("Builder AI Settings")

	config = {
		"enabled": False,
		"base_url": "",
		"api_key": None,
		"model": "x/flux2-klein",
	}

	if settings.ai_provider == "ollama":
		config["base_url"] = (settings.ollama_base_url or "").rstrip("/")
		# Remove /v1 suffix for native Ollama API
		if config["base_url"].endswith("/v1"):
			config["base_url"] = config["base_url"][:-3]

		try:
			config["api_key"] = settings.get_password("ollama_api_key")
		except Exception:
			pass

		# Check if image model is available
		config["enabled"] = bool(config["base_url"])

	return config


def generate_image_with_ollama(prompt: str, model: str = None) -> str | None:
	"""
	Generate an image using Ollama's image generation API.

	Args:
		prompt: Text prompt describing the image to generate
		model: Model to use (default: x/flux2-klein)

	Returns:
		Base64 encoded image data or None if generation fails
	"""
	config = get_image_generation_config()

	if not config["enabled"]:
		frappe.log_error("Image generation disabled", "Ollama not configured for image generation")
		return None

	model = model or config["model"]
	base_url = config["base_url"]
	api_key = config["api_key"]

	# Build request
	url = f"{base_url}/api/generate"
	headers = {
		"Content-Type": "application/json",
		"User-Agent": "Mozilla/5.0 (compatible; BuilderAI/1.0)"
	}

	if api_key:
		headers["X-API-Key"] = api_key

	payload = {
		"model": model,
		"prompt": prompt,
		"stream": False
	}

	try:
		response = requests.post(
			url,
			headers=headers,
			json=payload,
			timeout=180  # Image generation can take time
		)
		response.raise_for_status()

		data = response.json()
		image_base64 = data.get("image")

		if image_base64:
			return image_base64

		frappe.log_error("No image in response", f"Ollama response: {str(data)[:500]}")
		return None

	except requests.exceptions.Timeout:
		frappe.log_error("Image generation timeout", f"Prompt: {prompt[:100]}")
		return None
	except requests.exceptions.RequestException as e:
		frappe.log_error("Image generation failed", str(e))
		return None
	except Exception as e:
		frappe.log_error("Image generation error", str(e))
		return None


def save_generated_image(image_base64: str, filename: str = None) -> str | None:
	"""
	Save a base64 encoded image to Frappe Files.

	Args:
		image_base64: Base64 encoded image data
		filename: Optional filename (default: auto-generated)

	Returns:
		File URL or None if save fails
	"""
	try:
		# Decode image
		image_data = base64.b64decode(image_base64)

		# Generate filename if not provided
		if not filename:
			# Create hash-based filename
			hash_str = hashlib.md5(image_data[:1000]).hexdigest()[:8]
			filename = f"ai-generated-{hash_str}.png"

		# Save to Frappe Files
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": filename,
			"content": image_data,
			"is_private": 0  # Public file for website use
		})
		file_doc.insert(ignore_permissions=True)

		return file_doc.file_url

	except Exception as e:
		frappe.log_error("Failed to save image", str(e))
		return None


def get_image_prompt_for_section(industry: str, section_type: str, context: dict = None) -> str:
	"""
	Generate an appropriate image prompt based on industry and section type.

	Args:
		industry: Business industry (e.g., "bakery", "restaurant")
		section_type: Type of section ("hero", "about", "feature")
		context: Optional additional context

	Returns:
		Optimized prompt for image generation
	"""
	industry_lower = (industry or "").lower()
	business_name = (context or {}).get("business_name", "")

	# Base style for all images
	base_style = "professional photography, high quality, well-lit, clean composition"

	# Industry-specific prompts
	if "boulangerie" in industry_lower or "bakery" in industry_lower or "pain" in industry_lower:
		if section_type == "hero":
			return f"Beautiful French bakery interior with fresh bread and croissants on display, warm morning light through window, rustic wooden shelves, golden tones, inviting atmosphere, {base_style}"
		elif section_type == "about":
			return f"Artisan baker kneading dough in traditional bakery, flour-dusted wooden table, warm ambient lighting, authentic craftsmanship, {base_style}"
		else:
			return f"Fresh baked artisan bread loaves and pastries on rustic wooden board, warm golden lighting, {base_style}"

	elif "patisserie" in industry_lower or "pastry" in industry_lower:
		if section_type == "hero":
			return f"Elegant French patisserie display with colorful macarons, eclairs and tarts, soft lighting, luxurious presentation, {base_style}"
		elif section_type == "about":
			return f"Pastry chef decorating an elaborate cake, professional kitchen, artistic precision, {base_style}"
		else:
			return f"Assortment of French pastries and desserts, artistic arrangement, {base_style}"

	elif "restaurant" in industry_lower or "cuisine" in industry_lower:
		if section_type == "hero":
			return f"Elegant restaurant interior with warm ambient lighting, set tables with white linens, sophisticated atmosphere, {base_style}"
		elif section_type == "about":
			return f"Professional chef plating a gourmet dish, modern kitchen, culinary artistry, {base_style}"
		else:
			return f"Beautifully plated gourmet dish, fine dining presentation, {base_style}"

	elif "cafe" in industry_lower or "coffee" in industry_lower:
		if section_type == "hero":
			return f"Cozy coffee shop interior with exposed brick, comfortable seating, warm lighting, coffee cups and plants, {base_style}"
		elif section_type == "about":
			return f"Barista crafting latte art, coffee preparation, artisanal coffee making, {base_style}"
		else:
			return f"Artisan coffee cup with latte art, coffee beans, warm atmosphere, {base_style}"

	elif "fleuriste" in industry_lower or "florist" in industry_lower or "fleur" in industry_lower:
		if section_type == "hero":
			return f"Beautiful flower shop interior with colorful bouquets, natural light, elegant vases, romantic atmosphere, {base_style}"
		elif section_type == "about":
			return f"Florist arranging a beautiful bouquet, surrounded by fresh flowers, artistic composition, {base_style}"
		else:
			return f"Elegant floral arrangement with roses and seasonal flowers, {base_style}"

	elif "tech" in industry_lower or "saas" in industry_lower or "software" in industry_lower:
		if section_type == "hero":
			return f"Modern tech office with sleek design, large monitors, collaborative workspace, blue accent lighting, {base_style}"
		elif section_type == "about":
			return f"Diverse team collaborating around laptop, modern office, innovation and teamwork, {base_style}"
		else:
			return f"Clean laptop on minimal desk, modern technology workspace, {base_style}"

	elif "immobilier" in industry_lower or "real estate" in industry_lower:
		if section_type == "hero":
			return f"Stunning modern house exterior with beautiful landscaping, blue sky, architectural photography, {base_style}"
		elif section_type == "about":
			return f"Real estate agent showing property to happy couple, professional interaction, {base_style}"
		else:
			return f"Beautiful home interior, modern living room with natural light, {base_style}"

	elif "spa" in industry_lower or "wellness" in industry_lower or "beauté" in industry_lower:
		if section_type == "hero":
			return f"Luxurious spa interior with candles, zen stones, orchids, peaceful atmosphere, soft lighting, {base_style}"
		elif section_type == "about":
			return f"Relaxing spa treatment room, massage table, calming environment, {base_style}"
		else:
			return f"Spa products arrangement, natural elements, wellness atmosphere, {base_style}"

	# Default business prompts
	if section_type == "hero":
		return f"Modern professional business environment, clean and welcoming, natural lighting, {base_style}"
	elif section_type == "about":
		return f"Professional team in modern office, collaboration and expertise, {base_style}"
	else:
		return f"Clean professional workspace, modern business aesthetic, {base_style}"


def generate_section_image(industry: str, section_type: str, context: dict = None) -> str | None:
	"""
	Generate and save an image for a website section.

	Args:
		industry: Business industry
		section_type: Type of section
		context: Additional context

	Returns:
		File URL of generated image or None
	"""
	# Generate prompt
	prompt = get_image_prompt_for_section(industry, section_type, context)

	# Generate image
	image_base64 = generate_image_with_ollama(prompt)

	if not image_base64:
		return None

	# Save image
	business_name = (context or {}).get("business_name", "site")
	safe_name = frappe.scrub(business_name).replace("_", "-")[:20]
	filename = f"{safe_name}-{section_type}-{generate_block_id()[:4]}.png"

	file_url = save_generated_image(image_base64, filename)

	return file_url


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

def get_collector_prompt(settings=None) -> str:
	"""Generate the collector prompt with dynamic settings."""

	# Get shortcodes if available
	shortcodes_info = ""
	if settings and hasattr(settings, 'shortcodes') and settings.shortcodes:
		shortcodes_list = []
		for sc in settings.shortcodes:
			shortcodes_list.append(f"- **{sc.name1}** ({sc.category}): {sc.description or 'No description'}\n  Use when: {sc.use_when or 'As appropriate'}\n  Code: `{sc.shortcode}`")
		if shortcodes_list:
			shortcodes_info = f"""
## Available Components/Shortcodes
You have access to these pre-built components. Use them when appropriate based on the site type:

{chr(10).join(shortcodes_list)}

IMPORTANT: When generating the site, you MUST use these shortcodes where appropriate. For example:
- E-commerce sites MUST include the cart shortcode in the header
- Sites with user accounts MUST include the user shortcode
- Sites with search functionality MUST include the search shortcode
"""

	# Get design preferences
	design_info = ""
	if settings:
		style = getattr(settings, 'default_style', 'modern')
		creativity = getattr(settings, 'creativity_level', 'balanced')
		design_info = f"""
## Design Approach
- Default style: {style}
- Creativity level: {creativity}
- Use modern design: {getattr(settings, 'use_modern_design', True)}
"""

	# Get site type preferences
	site_type_info = ""
	if settings:
		default_type = getattr(settings, 'default_site_type', 'auto')
		allow_multipage = getattr(settings, 'allow_multipage', True)
		site_type_info = f"""
## Site Structure
- Default site type: {default_type}
- Multi-page sites allowed: {allow_multipage}
"""

	return f"""You are an expert web designer and creative director with 15+ years of experience creating stunning, unique websites. You're having a friendly conversation to understand what the user wants to build.

## Your Personality
- Enthusiastic and creative, but professional
- You suggest bold, innovative ideas while respecting user preferences
- You understand that every business is unique and deserves a unique design
- You think about user experience, not just aesthetics

## Your Creative Approach
1. **Understand the Business Context**: What industry? What's their unique value proposition? Who are their competitors?
2. **Feel the Brand**: What emotions should the site evoke? What's the brand personality?
3. **Think About the User Journey**: What actions should visitors take? What story does the site tell?
4. **Design with Intent**: Every design choice should have a purpose

## Conversation Guidelines
- Ask ONE focused question at a time
- Be genuinely curious - dig deeper into their business
- Suggest creative ideas based on their industry (e.g., "For a florist, we could use organic shapes and warm, natural colors...")
- If they're unsure about colors, suggest palettes that match their industry and mood
- Don't just collect data - collaborate on the creative vision
{shortcodes_info}
{design_info}
{site_type_info}
## Information to Gather (Organically)

### Essential (Must Have)
- Business/project name
- What they do (in their words)
- Target audience
- Main goal of the site (sell, inform, showcase, generate leads?)

### Site Functionality Type (IMPORTANT!)
Determine which type of site they need based on their goals:

1. **vitrine** (Showcase/Brochure site):
   - Simple informational site
   - No user accounts needed
   - Contact form only
   - Example: Local bakery, portfolio, small business

2. **vitrine_with_login** (Showcase with user accounts):
   - Informational site WITH user registration/login
   - Members area, restricted content
   - Example: Professional services, membership site

3. **ecommerce** (Online store):
   - Product catalog and shopping
   - Shopping cart, wishlist, checkout
   - User accounts for orders
   - Example: Online shop, marketplace

Ask about their needs naturally:
- "Will customers need to create accounts?"
- "Do you plan to sell products online?"
- "Will you need a shopping cart?"

### Style & Feel
- Color preferences OR let you suggest based on industry
- Modern/classic/minimal/bold/playful/elegant
- Any sites they like for inspiration
- Brand personality (professional, friendly, luxurious, approachable?)

### Structure (CRITICAL - Always determine this!)
Determine if the site should be one-page or multi-page:

**One-Page Sites** (all content on a single scrolling page):
- Good for: Simple businesses, portfolios, event pages, landing pages
- Navigation uses anchor links (#about, #services, #contact)
- Faster to load, simpler user experience

**Multi-Page Sites** (separate pages with their own URLs):
- Good for: Businesses with lots of content, e-commerce, professional services
- Navigation uses real URLs (/about, /services, /contact)
- Better for SEO, more organized content

For multi-page sites, you MUST ask:
1. "Which pages do you need?" (home, about, services, portfolio, contact, blog, etc.)
2. "What content should be on each page?"
3. "Which page should be your homepage?"

Default pages by functionality_type:
- **vitrine**: home, about (optional), contact
- **vitrine_with_login**: home, about, services, contact
- **ecommerce**: home, shop/products, about, contact

### Key Sections - BE CREATIVE!
**CRITICAL: Every page should look DIFFERENT. Avoid cookie-cutter layouts!**

Available section types:
- **hero**: ONLY for homepage! Large, impactful banner with background image (80vh height). Never use on secondary pages.
- **page_header**: Simple title header for secondary pages. Much smaller, cleaner. Use variants: "simple", "gradient", "with_image".
- **features**: Feature cards/grid showcasing benefits or services
- **about**: About section with text and optional image
- **contact**: Contact form and info (use shortcodes when available)
- **cta**: Call-to-action banner
- **testimonials**: Customer reviews
- **pricing**: Pricing tables
- **gallery**: Image gallery
- **team**: Team members grid (use shortcode when available)
- **faq**: Frequently asked questions
- **stats**: Numbers/statistics section
- **process**: Step-by-step process visualization

**Layout Rules for Visual Variety:**
1. Homepage: Can start with "hero" (big, impressive, full-height)
2. Secondary pages (About, Services, Contact): Start with "page_header" NOT "hero"
3. Each page should have a UNIQUE combination of sections
4. Don't repeat the same section order on multiple pages

### Call-to-Action Priorities
- Primary CTA (most important action)
- Secondary CTAs

### Content Direction
- Headlines (or let you write them)
- Key messages to convey
- Unique selling points

## Creative Color Psychology
Use this knowledge to suggest colors when users don't have preferences:
- **Florists/Nature**: Warm greens, soft pinks, earthy tones
- **Tech/SaaS**: Blues, purples, clean whites
- **Restaurants/Food**: Warm oranges, reds, appetizing colors
- **Luxury/Fashion**: Black, gold, deep jewel tones
- **Health/Wellness**: Calming blues, greens, soft gradients
- **Finance**: Navy blue, green (trust), sophisticated grays
- **Creative Agencies**: Bold, unexpected color combinations
- **Kids/Education**: Bright, playful, primary colors

## Response Format
Always respond with a JSON object:
{{
  "message": "Your conversational response",
  "site_context": {{
    // All collected information - be comprehensive
  }},
  "collection_complete": false,
  "next_question_topic": "what you'll explore next",
  "creative_notes": "internal notes about design direction"
}}

## Site Context Schema
{{
  "site_type": "one_page|multi_page",
  "page_structure": "landing|portfolio|business|ecommerce|blog|saas",
  "functionality_type": "vitrine|vitrine_with_login|ecommerce",
  "requires_features": {{
    "cart": false,
    "wishlist": false,
    "user_menu": false,
    "search": false,
    "mobile_menu": true
  }},
  "business_name": "string",
  "industry": "string",
  "tagline": "string",
  "description": "string",
  "unique_value_proposition": "string",
  "target_audience": {{
    "description": "string",
    "age_range": "string",
    "interests": ["string"]
  }},
  "brand_personality": ["professional", "friendly", "luxurious", "innovative", "trustworthy"],
  "style": {{
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex",
    "background_color": "#hex",
    "text_color": "#hex",
    "gradient": "optional gradient definition",
    "style_preference": "modern|classic|minimal|bold|playful|elegant|corporate",
    "mood": "description of the overall feel",
    "inspiration_sites": ["urls or descriptions"]
  }},
  "pages": [
    {{
      "name": "home",
      "route": "/",
      "is_main": true,
      "title": "Accueil",
      "sections": ["hero", "features", "testimonials", "cta"]
    }},
    {{
      "name": "about",
      "route": "/about",
      "is_main": false,
      "title": "À propos",
      "sections": ["page_header", "about", "team", "stats"]
    }},
    {{
      "name": "services",
      "route": "/services",
      "is_main": false,
      "title": "Nos Services",
      "sections": ["page_header", "features", "process", "cta"]
    }},
    {{
      "name": "contact",
      "route": "/contact",
      "is_main": false,
      "title": "Contact",
      "sections": ["page_header", "contact"]
    }}
  ],
  "sections": [
    {{
      "type": "hero|features|testimonials|pricing|contact|about|cta|gallery|team|faq|stats|process",
      "layout_variant": "centered|split|asymmetric|full-width",
      "headline": "string",
      "subheadline": "string",
      "description": "string",
      "cta_primary": {{"text": "string", "link": "string"}},
      "cta_secondary": {{"text": "string", "link": "string"}},
      "items": [...],
      "background_style": "solid|gradient|image|pattern",
      "special_effects": ["parallax", "animation", "glassmorphism"]
    }}
  ],
  "header": {{
    "style": "transparent|solid|sticky",
    "includes_search": false,
    "includes_cart": false,
    "includes_user_menu": false,
    "shortcodes_to_use": ["list of shortcode names"]
  }},
  "footer": {{
    "style": "minimal|detailed|mega",
    "columns": ["about", "links", "contact", "social"],
    "includes_newsletter": false,
    "includes_payment_icons": false,
    "includes_social": true
  }},
  "contact_info": {{...}},
  "seo": {{
    "meta_title": "string",
    "meta_description": "string"
  }}
}}

## Feature Mapping Rules
Based on functionality_type, set requires_features as follows:

**vitrine (Showcase)**:
- cart: false, wishlist: false, user_menu: false, search: false, mobile_menu: true

**vitrine_with_login (Showcase + Login)**:
- cart: false, wishlist: false, user_menu: true, search: false, mobile_menu: true

**ecommerce (Online Store)**:
- cart: true, wishlist: true, user_menu: true, search: true, mobile_menu: true

## Multi-Page Generation Rules (CRITICAL!)
When site_type is "multi_page", you MUST:
1. Define ALL pages in the "pages" array with complete structure
2. Each page MUST have: name, route, is_main, title, sections
3. Exactly ONE page must have is_main: true (this will have route "/")
4. For one-page sites, still create a single page entry in the "pages" array

Page routing rules:
- Homepage (is_main: true): route = "/" or business name slug
- Other pages: route = "/page-name" (e.g., "/about", "/services", "/contact")

**CRITICAL - Page Layout Variety:**
- **Homepage ONLY**: Use "hero" section (big, impressive, 80vh)
- **ALL secondary pages**: Use "page_header" (simple title, compact) - NEVER "hero"!
- This creates visual variety and professional distinction between pages
- Each page should tell its own visual story

Section assignment examples (BE CREATIVE - these are just examples!):
- Homepage: hero, features, testimonials, cta (impressive and engaging)
- About page: page_header, about, team, stats (informative and personal)
- Services page: page_header, features, process, pricing, cta (detailed and persuasive)
- Contact page: page_header, contact (simple and functional)
- Portfolio/Gallery: page_header, gallery, testimonials (visual showcase)

**REMEMBER**: The AI should be FREE to choose different section combinations!
Don't create identical pages - each should have its own character.

Start with a warm, enthusiastic greeting and ask what kind of website they're dreaming of!"""


COLLECTOR_SYSTEM_PROMPT = get_collector_prompt()  # Default without settings


GENERATOR_SYSTEM_PROMPT = """You are a Frappe Builder block generator. Your task is to convert a site context JSON into properly structured Frappe Builder blocks.

## Block Structure:
Each block must follow this exact structure:
{
  "blockId": "9_char_id",
  "element": "section|div|h1|h2|h3|p|a|button|img|span|form|input|textarea|nav|footer|header|ul|li",
  "blockName": "semantic_name",
  "innerHTML": "text content or empty string",
  "attributes": {
    "href": "for links",
    "src": "for images",
    "placeholder": "for inputs"
  },
  "customAttributes": {},
  "classes": [],
  "baseStyles": {
    // Desktop styles in camelCase
  },
  "tabletStyles": {
    // Tablet overrides
  },
  "mobileStyles": {
    // Mobile overrides
  },
  "rawStyles": {
    // Pseudo-selectors like "hover:backgroundColor"
  },
  "children": [],
  "dataKey": null
}

## Style Guidelines:
1. Use flexbox for layouts: display: "flex", flexDirection, gap, alignItems, justifyContent
2. Use semantic HTML elements (section, header, nav, footer, h1-h6, p, a, button)
3. Apply responsive styles: baseStyles for desktop, tabletStyles for tablet, mobileStyles for mobile
4. Use hover states in rawStyles: "hover:backgroundColor", "hover:color", etc.
5. Use CSS variables for theme colors when appropriate: var(--primary-color)

## Common Patterns:

### Container:
{
  "baseStyles": {
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "maxWidth": "1200px",
    "width": "100%",
    "margin": "0 auto",
    "padding": "0 20px"
  }
}

### Hero Section:
- Full width section with centered content
- Large heading (h1), subheading (p), CTA buttons
- paddingTop/Bottom: "100px" to "200px"

### Feature Cards:
- Grid or flex layout with gap
- Card with padding, border-radius, optional shadow
- Icon/image, heading (h3), description (p)

### Buttons:
- Primary: dark background (#171717), white text, border-radius: "12px"
- Secondary: light background (#F3F3F3), dark text
- Add hover states in rawStyles

### Typography:
- h1: fontSize "48px", fontWeight "700", lineHeight "120%"
- h2: fontSize "36px", fontWeight "600"
- h3: fontSize "24px", fontWeight "600"
- p: fontSize "16px", lineHeight "150%"
- Responsive: reduce sizes by ~20-25% for mobile

## Placeholder Images:
Use these placeholder URLs:
- Hero images: "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&h=600&fit=crop"
- Feature icons: use emoji or simple SVG data URLs
- Testimonial avatars: "https://i.pravatar.cc/150?img=X" (X = 1-70)
- Product images: "https://images.unsplash.com/photo-[id]?w=400&h=300&fit=crop"

## Output Format:
Return a JSON array of blocks representing the complete page structure.
The root should be a body element containing all sections.

IMPORTANT:
- Generate ONLY valid JSON, no explanations
- Every block must have a unique blockId (9 characters)
- Ensure all style property names are in camelCase
- Include responsive styles for a professional look"""


# =============================================================================
# PAGE GENERATOR PROMPT - For creative LLM-based page generation
# =============================================================================

PAGE_GENERATOR_PROMPT = """You are a creative web designer generating Frappe Builder blocks.
Your goal is to create UNIQUE, CREATIVE designs - not cookie-cutter templates.

## CRITICAL: Block Structure (ALL fields required for editability)
Every block MUST have these exact fields for Builder to recognize it:
{
  "blockId": "ab12cd34e",    // EXACTLY 9 lowercase alphanumeric chars
  "element": "section",       // Valid HTML tag
  "blockName": "my-section",  // Semantic name for the block
  "innerHTML": "",            // Text content (can be empty string)
  "attributes": {},           // href, src, placeholder, etc.
  "customAttributes": {},     // data-* attributes
  "classes": [],              // CSS classes array (usually empty)
  "dataKey": null,            // For dynamic content (usually null)
  "baseStyles": {},           // Desktop styles (REQUIRED even if empty)
  "tabletStyles": {},         // Tablet overrides (REQUIRED even if empty)
  "mobileStyles": {},         // Mobile overrides (REQUIRED even if empty)
  "rawStyles": {},            // hover:, etc. (REQUIRED even if empty)
  "children": []              // Child blocks array
}

## Valid HTML Elements
section, div, h1, h2, h3, h4, h5, h6, p, span, a, button, img, form, input, textarea, ul, ol, li, nav, header, footer

## Style Properties (MUST be camelCase!)
- Layout: display, flexDirection, alignItems, justifyContent, gap, flexWrap, gridTemplateColumns
- Spacing: padding, paddingTop, paddingBottom, paddingLeft, paddingRight, margin, marginTop, marginBottom
- Size: width, height, maxWidth, minHeight, flex
- Typography: fontSize, fontWeight, lineHeight, letterSpacing, textAlign, color, textTransform
- Background: backgroundColor, backgroundImage, backgroundSize, backgroundPosition
- Border: borderRadius, border, borderColor, boxShadow
- Position: position, top, left, right, bottom, zIndex

## Responsive Breakpoints
- Desktop: baseStyles (>= 768px)
- Tablet: tabletStyles (< 768px)
- Mobile: mobileStyles (< 576px)

## Example: Complete Hero Section
[
  {
    "blockId": "hero00001",
    "element": "section",
    "blockName": "hero",
    "innerHTML": "",
    "attributes": {},
    "customAttributes": {},
    "classes": [],
    "dataKey": null,
    "baseStyles": {
      "display": "flex",
      "flexDirection": "column",
      "alignItems": "center",
      "justifyContent": "center",
      "minHeight": "80vh",
      "paddingTop": "120px",
      "paddingBottom": "120px",
      "paddingLeft": "20px",
      "paddingRight": "20px",
      "backgroundColor": "#f8f9fa"
    },
    "tabletStyles": {"paddingTop": "80px", "paddingBottom": "80px"},
    "mobileStyles": {"minHeight": "60vh", "paddingTop": "60px"},
    "rawStyles": {},
    "children": [
      {
        "blockId": "herohead1",
        "element": "h1",
        "blockName": "hero-title",
        "innerHTML": "Welcome to Our Site",
        "attributes": {},
        "customAttributes": {},
        "classes": [],
        "dataKey": null,
        "baseStyles": {
          "fontSize": "56px",
          "fontWeight": "700",
          "lineHeight": "120%",
          "color": "#171717",
          "textAlign": "center",
          "margin": "0"
        },
        "tabletStyles": {"fontSize": "44px"},
        "mobileStyles": {"fontSize": "32px"},
        "rawStyles": {},
        "children": []
      },
      {
        "blockId": "herosub01",
        "element": "p",
        "blockName": "hero-subtitle",
        "innerHTML": "Discover what makes us unique",
        "attributes": {},
        "customAttributes": {},
        "classes": [],
        "dataKey": null,
        "baseStyles": {
          "fontSize": "20px",
          "lineHeight": "160%",
          "color": "#6B7280",
          "textAlign": "center",
          "maxWidth": "600px",
          "marginTop": "24px"
        },
        "tabletStyles": {"fontSize": "18px"},
        "mobileStyles": {"fontSize": "16px"},
        "rawStyles": {},
        "children": []
      },
      {
        "blockId": "herocta01",
        "element": "a",
        "blockName": "hero-cta",
        "innerHTML": "Get Started",
        "attributes": {"href": "#contact"},
        "customAttributes": {},
        "classes": [],
        "dataKey": null,
        "baseStyles": {
          "display": "inline-flex",
          "alignItems": "center",
          "justifyContent": "center",
          "backgroundColor": "#171717",
          "color": "#ffffff",
          "paddingTop": "16px",
          "paddingBottom": "16px",
          "paddingLeft": "32px",
          "paddingRight": "32px",
          "borderRadius": "8px",
          "fontSize": "16px",
          "fontWeight": "600",
          "textDecoration": "none",
          "marginTop": "32px",
          "cursor": "pointer"
        },
        "tabletStyles": {},
        "mobileStyles": {"width": "100%"},
        "rawStyles": {"hover:opacity": "0.9"},
        "children": []
      }
    ]
  }
]

## Example: Feature Card
{
  "blockId": "feat00001",
  "element": "div",
  "blockName": "feature-card",
  "innerHTML": "",
  "attributes": {},
  "customAttributes": {},
  "classes": [],
  "dataKey": null,
  "baseStyles": {
    "display": "flex",
    "flexDirection": "column",
    "padding": "32px",
    "backgroundColor": "#ffffff",
    "borderRadius": "16px",
    "boxShadow": "0 4px 20px rgba(0,0,0,0.08)"
  },
  "tabletStyles": {},
  "mobileStyles": {"padding": "24px"},
  "rawStyles": {"hover:boxShadow": "0 8px 30px rgba(0,0,0,0.12)"},
  "children": [
    {
      "blockId": "featico01",
      "element": "span",
      "blockName": "feature-icon",
      "innerHTML": "🚀",
      "attributes": {},
      "customAttributes": {},
      "classes": [],
      "dataKey": null,
      "baseStyles": {"fontSize": "48px", "marginBottom": "16px"},
      "tabletStyles": {},
      "mobileStyles": {},
      "rawStyles": {},
      "children": []
    },
    {
      "blockId": "feattit1",
      "element": "h3",
      "blockName": "feature-title",
      "innerHTML": "Fast & Reliable",
      "attributes": {},
      "customAttributes": {},
      "classes": [],
      "dataKey": null,
      "baseStyles": {"fontSize": "24px", "fontWeight": "600", "color": "#171717", "marginBottom": "12px"},
      "tabletStyles": {},
      "mobileStyles": {"fontSize": "20px"},
      "rawStyles": {},
      "children": []
    },
    {
      "blockId": "featdes1",
      "element": "p",
      "blockName": "feature-description",
      "innerHTML": "Experience lightning-fast performance with our optimized solutions.",
      "attributes": {},
      "customAttributes": {},
      "classes": [],
      "dataKey": null,
      "baseStyles": {"fontSize": "16px", "lineHeight": "160%", "color": "#6B7280"},
      "tabletStyles": {},
      "mobileStyles": {},
      "rawStyles": {},
      "children": []
    }
  ]
}

## Your Creative Freedom
BE CREATIVE! You decide:
- Layouts: Hero doesn't have to be 80vh, features don't need cards
- Colors: Use the provided palette creatively
- Spacing: Vary padding and margins for visual rhythm
- Typography: Mix font sizes and weights for hierarchy
- Effects: Add subtle shadows, gradients, hover states
- Structure: Experiment with asymmetric layouts, overlapping elements

## CRITICAL Rules
1. EVERY block MUST have ALL required fields (blockId, element, baseStyles, tabletStyles, mobileStyles, rawStyles, attributes, customAttributes, classes, children, dataKey)
2. blockId MUST be exactly 9 lowercase alphanumeric characters
3. Style properties MUST be camelCase (backgroundColor, NOT background-color)
4. Return ONLY valid JSON array - no markdown, no explanations
5. Empty objects {} and arrays [] are valid - but the fields MUST exist

## Images - CRITICAL!
NEVER use fake URLs like "/files/image.png" - they don't exist!
Use ONLY these real image services:

### Background Images (backgroundImage style)
Format: "url(https://images.unsplash.com/photo-ID?w=1600&h=900&fit=crop&q=80)"

Industry-specific Unsplash photo IDs:
- Bakery/Boulangerie: photo-1509440159596-0249088772ff (bread)
- Restaurant/Cafe: photo-1517248135467-4c7edcad34c4 (restaurant)
- Florist/Fleuriste: photo-1487530811176-3780de880c2d (flowers)
- Professional/Office: photo-1497366216548-37526070297c (office)
- Insurance/Assurance: photo-1560472354651-f29a5a94f6e5 (building)
- Artisan/Craft: photo-1452860606245-08befc0ff44b (craftsman)

### Avatar Images
Use: "https://i.pravatar.cc/150?img=X" (X = 1-70)

### Icons
Use emoji in innerHTML: 🥖 🥐 🍰 💐 🏢 ⭐ 💡 🎯 etc.
DO NOT use fake icon URLs!

Example for bakery hero:
"backgroundImage": "url(https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&h=900&fit=crop&q=80)"
"""


# =============================================================================
# BLOCK TEMPLATES - Pre-built section templates for reference
# =============================================================================

def get_section_image(industry: str, section_type: str = "hero", context: dict = None, use_ai: bool = False) -> str:
	"""
	Get an image for a section.

	By default, uses Unsplash for speed. Set use_ai=True for AI generation (slower).

	Args:
		industry: Business industry
		section_type: Type of section (hero, about, etc.)
		context: Additional context for image generation
		use_ai: If True, try AI generation first (default: False for speed)

	Returns:
		Image URL (Unsplash or generated file URL)
	"""
	# Only try AI generation if explicitly requested
	if use_ai:
		try:
			config = get_image_generation_config()
			if config.get("enabled"):
				file_url = generate_section_image(industry, section_type, context)
				if file_url:
					# Verify the file actually exists on disk before using it
					if file_url.startswith("/files/"):
						file_name = file_url.replace("/files/", "")
						# Check DB and also verify file content
						file_doc = frappe.db.get_value("File", {"file_name": file_name}, ["name", "file_size"], as_dict=True)
						if file_doc and file_doc.get("file_size", 0) > 1000:
							# File exists and has content
							return file_url
						# File doesn't exist or is empty, fall through to Unsplash
					else:
						# External URL, use it directly
						return file_url
		except Exception as e:
			frappe.log_error("AI image generation failed", str(e))

	# Default: Use Unsplash - always returns a valid, reliable URL
	return get_unsplash_fallback(industry, section_type)


def get_unsplash_fallback(industry: str, section_type: str = "hero") -> str:
	"""
	Get a fallback background image URL based on industry.

	Uses curated Unsplash photo IDs for consistent, high-quality images.
	Falls back to picsum.photos if no industry match.
	"""
	# Curated Unsplash photo IDs for each industry (direct image URLs)
	# Format: https://images.unsplash.com/photo-{ID}?w=1600&h=900&fit=crop
	industry_photos = {
		# Food & Beverage
		"boulangerie": "1509440159596-0249088772ff",  # Fresh bread
		"bakery": "1509440159596-0249088772ff",
		"patisserie": "1486427944544-364c4e1a2103",  # Pastries
		"restaurant": "1517248135467-4c7edcad34c4",  # Restaurant interior
		"cafe": "1495474472287-4d71bcdd2085",  # Coffee shop
		"coffee": "1495474472287-4d71bcdd2085",

		# Flowers & Nature
		"fleuriste": "1487530811176-3780de880c2d",  # Flower shop
		"florist": "1487530811176-3780de880c2d",
		"fleurs": "1490750967868-88aa4486c946",  # Flowers bouquet
		"flowers": "1490750967868-88aa4486c946",

		# Professional Services
		"assurance": "1560472354651-f29a5a94f6e5",  # Office building
		"insurance": "1560472354651-f29a5a94f6e5",
		"avocat": "1589829545856-d10d557cf95f",  # Law office
		"legal": "1589829545856-d10d557cf95f",
		"consulting": "1497366216548-37526070297c",  # Business meeting
		"cabinet": "1497366216548-37526070297c",

		# Tech
		"tech": "1518770660439-4636190af475",  # Technology
		"saas": "1551288049-bebda4e38f71",  # Software
		"startup": "1559136555-9303baea8ebd",  # Startup office

		# Real Estate
		"immobilier": "1560518883-ce09059eeffa",  # Modern house
		"real estate": "1560518883-ce09059eeffa",

		# Lifestyle
		"fitness": "1534438327276-14e5300c3a48",  # Gym
		"spa": "1540555700478-4be289fbec6e",  # Spa
		"hotel": "1566073771259-6a8506099945",  # Hotel lobby
		"beauty": "1522335789203-aabd1fc54bc9",  # Beauty salon

		# Retail
		"fashion": "1441984904996-e0b6ba687e04",  # Fashion store
		"mode": "1441984904996-e0b6ba687e04",
		"boutique": "1441984904996-e0b6ba687e04",

		# Artisan & Craft
		"artisan": "1452860606245-08befc0ff44b",  # Craftsman
		"maroquinerie": "1473188588951-80fc9c4bf5a8",  # Leather goods
		"cuir": "1473188588951-80fc9c4bf5a8",

		# Default
		"default": "1497366216548-37526070297c"  # Professional office
	}

	# Find matching photo ID
	industry_lower = (industry or "").lower()
	photo_id = industry_photos.get("default")

	for key, pid in industry_photos.items():
		if key in industry_lower:
			photo_id = pid
			break

	# Return direct Unsplash image URL with proper sizing
	return f"https://images.unsplash.com/photo-{photo_id}?w=1600&h=900&fit=crop&q=80"


def get_hero_template(context: dict) -> dict:
	"""Generate a hero section from context."""
	# Get section-specific data if available
	section = context.get("section_hero", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "hero"), {})

	style = context.get("style", {})
	industry = context.get("industry", "")

	# Extract colors with proper fallbacks
	primary_color = style.get("primary_color") or "#171717"
	text_color = style.get("text_color") or "#171717"
	bg_color = style.get("background_color") or "#ffffff"

	# Build headline from context
	business_name = context.get("business_name", "")
	tagline = context.get("tagline", "")

	headline = section.get("headline", "")
	if not headline:
		if business_name:
			headline = f"Bienvenue chez {business_name}"
		elif tagline:
			headline = tagline
		else:
			headline = "Bienvenue"

	# Build subheadline
	subheadline = section.get("subheadline", "") or section.get("description", "")
	if not subheadline:
		subheadline = tagline if tagline and headline != tagline else context.get("description", "")
	if not subheadline:
		subheadline = context.get("unique_value_proposition", "Découvrez ce qui nous rend unique")

	# Get CTA info
	cta_primary = section.get("cta_primary", {})
	cta_text = cta_primary.get("text", "") if isinstance(cta_primary, dict) else ""
	cta_link = cta_primary.get("link", "") if isinstance(cta_primary, dict) else ""
	if not cta_text:
		cta_text = "Découvrir"
	if not cta_link:
		cta_link = "#contact"

	# Get background image (AI-generated if available, otherwise Unsplash fallback)
	bg_image = get_section_image(industry, "hero", context)

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "hero",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"justifyContent": "center",
			"width": "100%",
			"minHeight": "80vh",
			"paddingTop": "120px",
			"paddingBottom": "120px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundImage": f"linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url({bg_image})",
			"backgroundSize": "cover",
			"backgroundPosition": "center"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "80px",
			"paddingBottom": "80px",
			"minHeight": "70vh"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "hero-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "24px",
					"maxWidth": "800px",
					"width": "100%",
					"textAlign": "center"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h1",
						"blockName": "hero-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "56px",
							"fontWeight": "700",
							"lineHeight": "120%",
							"color": "#ffffff",
							"letterSpacing": "-0.02em",
							"textShadow": "0 2px 4px rgba(0,0,0,0.3)"
						},
						"tabletStyles": {
							"fontSize": "44px"
						},
						"mobileStyles": {
							"fontSize": "36px"
						},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "p",
						"blockName": "hero-subheadline",
						"innerHTML": f"<p>{subheadline}</p>",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "20px",
							"fontWeight": "400",
							"lineHeight": "160%",
							"color": "rgba(255,255,255,0.9)",
							"maxWidth": "600px"
						},
						"tabletStyles": {
							"fontSize": "18px"
						},
						"mobileStyles": {
							"fontSize": "16px"
						},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "hero-actions",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "row",
							"gap": "16px",
							"marginTop": "16px"
						},
						"tabletStyles": {},
						"mobileStyles": {
							"flexDirection": "column",
							"width": "100%"
						},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "a",
								"blockName": "primary-cta",
								"innerHTML": "",
								"attributes": {
									"href": cta_link
								},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"display": "flex",
									"alignItems": "center",
									"justifyContent": "center",
									"backgroundColor": primary_color,
									"color": "#ffffff",
									"fontSize": "16px",
									"fontWeight": "600",
									"paddingTop": "16px",
									"paddingBottom": "16px",
									"paddingLeft": "32px",
									"paddingRight": "32px",
									"borderRadius": "12px",
									"textDecoration": "none",
									"boxShadow": "0 4px 14px rgba(0,0,0,0.25)"
								},
								"tabletStyles": {},
								"mobileStyles": {
									"width": "100%"
								},
								"rawStyles": {
									"hover:opacity": "0.9",
									"hover:transform": "translateY(-2px)",
									"transition": "all 0.2s ease"
								},
								"children": [
									{
										"blockId": generate_block_id(),
										"element": "span",
										"blockName": "cta-text",
										"innerHTML": cta_text,
										"attributes": {},
										"customAttributes": {},
										"classes": [],
										"dataKey": None,
										"baseStyles": {},
										"tabletStyles": {},
										"mobileStyles": {},
										"rawStyles": {},
										"children": []
									}
								]
							}
						]
					}
				]
			}
		]
	}


def get_page_header_template(context: dict) -> dict:
	"""
	Generate a simple page header for secondary pages.

	Unlike the full hero section, this is a compact header with just:
	- Page title (h1)
	- Optional subtitle/description
	- Optional decorative background (but not full-height)

	Use this for secondary pages (About, Services, Contact, etc.)
	to create visual variety instead of repeating the same big hero on every page.
	"""
	# Get section-specific data
	section = context.get("section_page_header", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "page_header"), {})

	style = context.get("style", {})
	page_title = context.get("current_page_title", "")

	# Extract colors
	primary_color = style.get("primary_color") or "#171717"
	text_color = style.get("text_color") or "#171717"
	bg_color = style.get("background_color") or "#f8f8f8"
	accent_color = style.get("accent_color") or style.get("secondary_color") or "#6366f1"

	# Get title and subtitle
	title = section.get("title", "") or section.get("headline", "") or page_title or _("Page")
	subtitle = section.get("subtitle", "") or section.get("description", "")

	# Choose variant: "simple" (just title), "with_image", "gradient"
	variant = section.get("variant", "simple")

	# Base styles for all variants
	base_section_styles = {
		"display": "flex",
		"flexDirection": "column",
		"alignItems": "center",
		"justifyContent": "center",
		"width": "100%",
		"paddingTop": "100px",
		"paddingBottom": "60px",
		"paddingLeft": "20px",
		"paddingRight": "20px",
		"textAlign": "center",
	}

	# Apply variant-specific styling
	if variant == "gradient":
		base_section_styles["background"] = f"linear-gradient(135deg, {primary_color}15 0%, {accent_color}10 100%)"
	elif variant == "with_image":
		industry = context.get("industry", "")
		bg_image = get_section_image(industry, "about", context)
		base_section_styles["backgroundImage"] = f"linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)), url({bg_image})"
		base_section_styles["backgroundSize"] = "cover"
		base_section_styles["backgroundPosition"] = "center"
	else:
		# Simple solid background
		base_section_styles["backgroundColor"] = bg_color

	children = [
		{
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "page-header-container",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"alignItems": "center",
				"gap": "16px",
				"maxWidth": "800px",
				"width": "100%"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "h1",
					"blockName": "page-header-title",
					"innerHTML": title,
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "42px",
						"fontWeight": "700",
						"lineHeight": "120%",
						"color": text_color,
						"letterSpacing": "-0.02em",
						"margin": "0"
					},
					"tabletStyles": {
						"fontSize": "36px"
					},
					"mobileStyles": {
						"fontSize": "28px"
					},
					"rawStyles": {},
					"children": []
				}
			]
		}
	]

	# Add subtitle if present
	if subtitle:
		children[0]["children"].append({
			"blockId": generate_block_id(),
			"element": "p",
			"blockName": "page-header-subtitle",
			"innerHTML": subtitle,
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"fontSize": "18px",
				"fontWeight": "400",
				"lineHeight": "160%",
				"color": text_color,
				"opacity": "0.7",
				"maxWidth": "600px",
				"margin": "0"
			},
			"tabletStyles": {},
			"mobileStyles": {
				"fontSize": "16px"
			},
			"rawStyles": {},
			"children": []
		})

	# Add decorative element for visual interest
	children[0]["children"].append({
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "page-header-decoration",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"width": "60px",
			"height": "4px",
			"backgroundColor": primary_color,
			"borderRadius": "2px",
			"marginTop": "8px"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": []
	})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "page-header",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": base_section_styles,
		"tabletStyles": {
			"paddingTop": "80px",
			"paddingBottom": "50px"
		},
		"mobileStyles": {
			"paddingTop": "70px",
			"paddingBottom": "40px"
		},
		"rawStyles": {},
		"children": children
	}


def get_industry_features(industry: str, business_name: str) -> list:
	"""Generate default features based on industry."""
	industry_lower = (industry or "").lower()

	if "boulangerie" in industry_lower or "patisserie" in industry_lower or "bakery" in industry_lower:
		return [
			{"icon": "🥖", "title": "Pain Artisanal", "text": "Nos pains sont pétris et cuits chaque jour selon des recettes traditionnelles."},
			{"icon": "🥐", "title": "Viennoiseries Fraîches", "text": "Croissants, pains au chocolat et brioches préparés avec du beurre de qualité."},
			{"icon": "🎂", "title": "Pâtisseries Maison", "text": "Des créations gourmandes pour tous vos moments de plaisir."},
		]
	elif "restaurant" in industry_lower or "cafe" in industry_lower:
		return [
			{"icon": "👨‍🍳", "title": "Chef Passionné", "text": "Une cuisine créative préparée avec des produits frais et de saison."},
			{"icon": "🍽️", "title": "Cadre Chaleureux", "text": "Un espace accueillant pour vos repas en famille ou entre amis."},
			{"icon": "🌿", "title": "Produits Locaux", "text": "Nous privilégions les producteurs locaux pour une qualité optimale."},
		]
	elif "fleuriste" in industry_lower or "florist" in industry_lower:
		return [
			{"icon": "💐", "title": "Bouquets Sur Mesure", "text": "Des compositions florales uniques créées selon vos envies."},
			{"icon": "🌸", "title": "Fleurs Fraîches", "text": "Un approvisionnement quotidien pour une fraîcheur garantie."},
			{"icon": "🎁", "title": "Livraison Express", "text": "Livraison le jour même pour toutes vos occasions spéciales."},
		]
	elif "tech" in industry_lower or "saas" in industry_lower:
		return [
			{"icon": "⚡", "title": "Performance", "text": "Une solution rapide et fiable pour optimiser votre productivité."},
			{"icon": "🔒", "title": "Sécurité", "text": "Vos données sont protégées avec les meilleurs standards."},
			{"icon": "🎯", "title": "Simplicité", "text": "Une interface intuitive pour une prise en main immédiate."},
		]
	else:
		return [
			{"icon": "✨", "title": "Qualité", "text": "Un engagement constant pour l'excellence dans tout ce que nous faisons."},
			{"icon": "💪", "title": "Expertise", "text": "Une équipe passionnée et expérimentée à votre service."},
			{"icon": "❤️", "title": "Service Client", "text": "Votre satisfaction est notre priorité absolue."},
		]


def get_features_template(context: dict) -> dict:
	"""Generate a features section from context."""
	# Get section-specific data
	section = context.get("section_features", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "features"), {})

	style = context.get("style", {})
	industry = context.get("industry", "")
	business_name = context.get("business_name", "")

	# Extract colors with proper fallbacks
	primary_color = style.get("primary_color") or "#171717"
	text_color = style.get("text_color") or "#171717"
	secondary_text = style.get("secondary_color") or "#525252"
	bg_color = style.get("background_color") or "#ffffff"

	# Get headline
	headline = section.get("headline", "")
	if not headline:
		headline = "Pourquoi nous choisir" if business_name else "Nos Services"

	# Get items from section or generate defaults based on industry
	items = section.get("items", [])
	if not items:
		items = get_industry_features(industry, business_name)

	feature_cards = []
	for item in items:
		# Support both "text" and "description" keys
		description = item.get("text") or item.get("description", "")
		icon = item.get("icon", "✨")

		feature_cards.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "feature-card",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "12px",
				"padding": "32px",
				"backgroundColor": "#f9fafb",
				"borderRadius": "16px",
				"flex": "1",
				"minWidth": "280px"
			},
			"tabletStyles": {},
			"mobileStyles": {
				"padding": "24px"
			},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "feature-icon",
					"innerHTML": icon,
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "40px",
						"width": "64px",
						"height": "64px",
						"display": "flex",
						"alignItems": "center",
						"justifyContent": "center",
						"backgroundColor": f"{primary_color}15",
						"borderRadius": "16px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "h3",
					"blockName": "feature-title",
					"innerHTML": item.get("title", "Service"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "20px",
						"fontWeight": "600",
						"color": text_color,
						"marginTop": "8px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "p",
					"blockName": "feature-description",
					"innerHTML": f"<p>{description}</p>",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"lineHeight": "160%",
						"color": secondary_text
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "features",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": bg_color
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "features-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "features-header",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"alignItems": "center",
							"gap": "16px",
							"textAlign": "center",
							"maxWidth": "600px"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "h2",
								"blockName": "features-headline",
								"innerHTML": headline,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "40px",
									"fontWeight": "700",
									"color": text_color,
									"lineHeight": "120%"
								},
								"tabletStyles": {
									"fontSize": "32px"
								},
								"mobileStyles": {
									"fontSize": "28px"
								},
								"rawStyles": {},
								"children": []
							},
							{
								"blockId": generate_block_id(),
								"element": "p",
								"blockName": "features-subheadline",
								"innerHTML": f"<p>{section.get('subheadline') or section.get('description') or 'Découvrez ce qui nous rend uniques'}</p>",
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "18px",
									"color": secondary_text,
									"lineHeight": "150%"
								},
								"tabletStyles": {},
								"mobileStyles": {
									"fontSize": "16px"
								},
								"rawStyles": {},
								"children": []
							}
						]
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "features-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "row",
							"flexWrap": "wrap",
							"gap": "24px",
							"width": "100%",
							"justifyContent": "center"
						},
						"tabletStyles": {},
						"mobileStyles": {
							"flexDirection": "column"
						},
						"rawStyles": {},
						"children": feature_cards
					}
				]
			}
		]
	}


def get_cta_template(context: dict) -> dict:
	"""Generate a CTA section from context."""
	# Get section-specific data
	section = context.get("section_cta", {})
	if not section:
		section = context.get("section_contact", {})  # Fallback to contact section
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") in ["cta", "contact"]), {})

	style = context.get("style", {})
	business_name = context.get("business_name", "")
	contact_info = context.get("contact_info", {})

	primary_color = style.get("primary_color") or "#171717"

	# Build CTA content
	headline = section.get("headline", "")
	if not headline:
		headline = f"Venez nous rendre visite" if business_name else "Contactez-nous"

	description = section.get("description", "")
	if not description and contact_info:
		parts = []
		if contact_info.get("address"):
			parts.append(contact_info.get("address"))
		if contact_info.get("hours"):
			parts.append(f"Horaires: {contact_info.get('hours')}")
		description = " | ".join(parts) if parts else "Nous serons ravis de vous accueillir."
	if not description:
		description = "Nous serons ravis de vous accueillir."

	# Get CTA button info
	cta_primary = section.get("cta_primary", {})
	cta_text = cta_primary.get("text", "") if isinstance(cta_primary, dict) else ""
	cta_link = cta_primary.get("link", "") if isinstance(cta_primary, dict) else ""
	if not cta_text:
		if contact_info.get("phone"):
			cta_text = "Nous appeler"
			cta_link = f"tel:{contact_info.get('phone')}"
		else:
			cta_text = "Nous contacter"
			cta_link = "#contact"

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "cta",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"justifyContent": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": primary_color
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "cta-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "24px",
					"maxWidth": "600px",
					"width": "100%",
					"textAlign": "center"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "cta-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": "#ffffff",
							"lineHeight": "120%"
						},
						"tabletStyles": {
							"fontSize": "32px"
						},
						"mobileStyles": {
							"fontSize": "28px"
						},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "p",
						"blockName": "cta-description",
						"innerHTML": f"<p>{description}</p>",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "18px",
							"color": "rgba(255, 255, 255, 0.8)",
							"lineHeight": "150%"
						},
						"tabletStyles": {},
						"mobileStyles": {
							"fontSize": "16px"
						},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "a",
						"blockName": "cta-button",
						"innerHTML": "",
						"attributes": {
							"href": cta_link
						},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"alignItems": "center",
							"justifyContent": "center",
							"backgroundColor": "#ffffff",
							"color": primary_color,
							"fontSize": "16px",
							"fontWeight": "600",
							"paddingTop": "16px",
							"paddingBottom": "16px",
							"paddingLeft": "32px",
							"paddingRight": "32px",
							"borderRadius": "12px",
							"textDecoration": "none",
							"marginTop": "8px"
						},
						"tabletStyles": {},
						"mobileStyles": {
							"width": "100%"
						},
						"rawStyles": {
							"hover:opacity": "0.9",
							"transition": "all 0.2s ease"
						},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "span",
								"blockName": "cta-button-text",
								"innerHTML": cta_text,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {},
								"tabletStyles": {},
								"mobileStyles": {},
								"rawStyles": {},
								"children": []
							}
						]
					}
				]
			}
		]
	}


def get_about_template(context: dict) -> dict:
	"""Generate an about section from context."""
	# Get section-specific data
	section = context.get("section_about", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "about"), {})

	style = context.get("style", {})
	business_name = context.get("business_name", "")
	industry = context.get("industry", "")
	tagline = context.get("tagline", "")
	description = context.get("description", "")

	# Extract colors
	primary_color = style.get("primary_color") or "#171717"
	text_color = style.get("text_color") or "#171717"
	secondary_text = style.get("secondary_color") or "#525252"
	bg_color = style.get("secondary_color") or "#f9fafb"

	# Build content
	headline = section.get("headline", "")
	if not headline:
		headline = "Notre Histoire" if business_name else "À Propos"

	about_description = section.get("description", "")
	if not about_description:
		about_description = description or context.get("unique_value_proposition", "")
	if not about_description:
		about_description = f"Bienvenue chez {business_name}. Nous sommes passionnés par ce que nous faisons et nous mettons tout en œuvre pour vous offrir le meilleur service."

	# Get background image (AI-generated if available, otherwise Unsplash fallback)
	bg_image = get_section_image(industry, "about", context)

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "about",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "row",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff",
			"gap": "60px"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"flexDirection": "column",
			"paddingTop": "60px",
			"paddingBottom": "60px",
			"gap": "40px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "about-image",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"flex": "1",
					"minHeight": "400px",
					"backgroundImage": f"url({bg_image})",
					"backgroundSize": "cover",
					"backgroundPosition": "center",
					"borderRadius": "24px"
				},
				"tabletStyles": {},
				"mobileStyles": {
					"minHeight": "250px",
					"width": "100%"
				},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "about-content",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"flex": "1",
					"display": "flex",
					"flexDirection": "column",
					"gap": "24px",
					"maxWidth": "500px"
				},
				"tabletStyles": {},
				"mobileStyles": {
					"maxWidth": "100%"
				},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "about-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": text_color,
							"lineHeight": "120%"
						},
						"tabletStyles": {
							"fontSize": "32px"
						},
						"mobileStyles": {
							"fontSize": "28px"
						},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "p",
						"blockName": "about-description",
						"innerHTML": f"<p>{about_description}</p>",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "18px",
							"lineHeight": "170%",
							"color": secondary_text
						},
						"tabletStyles": {},
						"mobileStyles": {
							"fontSize": "16px"
						},
						"rawStyles": {},
						"children": []
					}
				]
			}
		]
	}


def get_contact_template(context: dict) -> dict:
	"""
	Generate a contact section using Jinja shortcodes.

	Uses the contact_info and contact_form shortcodes which read from
	Frappe's "Contact Us Settings" DocType for dynamic content.
	"""
	section = context.get("section_contact", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "contact"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	bg_color = style.get("background_color") or "#f9fafb"
	primary_color = style.get("primary_color") or "#3B82F6"

	headline = section.get("headline", _("Contact Us"))

	# Get shortcode Jinja includes
	contact_info_jinja = get_shortcode_jinja("contact_info")
	contact_form_jinja = get_shortcode_jinja("contact_form")

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "contact",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": bg_color,
			"--primary-color": primary_color
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "contact-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1000px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					# Headline
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "contact-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": text_color,
							"lineHeight": "120%",
							"textAlign": "center",
							"marginBottom": "16px"
						},
						"tabletStyles": {
							"fontSize": "32px"
						},
						"mobileStyles": {
							"fontSize": "28px"
						},
						"rawStyles": {},
						"children": []
					},
					# Two-column grid: info + form
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "contact-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": "1fr 1fr",
							"gap": "48px",
							"width": "100%"
						},
						"tabletStyles": {},
						"mobileStyles": {
							"gridTemplateColumns": "1fr",
							"gap": "32px"
						},
						"rawStyles": {},
						"children": [
							# Contact info shortcode (left column)
							{
								"blockId": generate_block_id(),
								"element": "div",
								"blockName": "contact-info-wrapper",
								"innerHTML": contact_info_jinja,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"color": text_color
								},
								"tabletStyles": {},
								"mobileStyles": {},
								"rawStyles": {},
								"children": []
							},
							# Contact form shortcode (right column)
							{
								"blockId": generate_block_id(),
								"element": "div",
								"blockName": "contact-form-wrapper",
								"innerHTML": contact_form_jinja,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"color": text_color
								},
								"tabletStyles": {},
								"mobileStyles": {},
								"rawStyles": {},
								"children": []
							}
						]
					}
				]
			}
		]
	}


def get_team_template(context: dict) -> dict:
	"""
	Generate a team section using Jinja shortcode.

	Uses the team_grid shortcode which reads from Frappe's
	"About Us Settings" DocType for dynamic team member data.
	"""
	section = context.get("section_team", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "team"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	bg_color = style.get("background_color") or "#ffffff"

	headline = section.get("headline", _("Our Team"))
	description = section.get("description", _("Meet the people behind our success"))

	# Get shortcode Jinja include
	team_grid_jinja = get_shortcode_jinja("team_grid")

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "team",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": bg_color
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "team-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					# Header with headline and description
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "team-header",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"alignItems": "center",
							"gap": "16px",
							"textAlign": "center",
							"maxWidth": "600px"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "h2",
								"blockName": "team-headline",
								"innerHTML": headline,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "40px",
									"fontWeight": "700",
									"color": text_color,
									"lineHeight": "120%"
								},
								"tabletStyles": {"fontSize": "32px"},
								"mobileStyles": {"fontSize": "28px"},
								"rawStyles": {},
								"children": []
							},
							{
								"blockId": generate_block_id(),
								"element": "p",
								"blockName": "team-description",
								"innerHTML": description,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "18px",
									"color": secondary_color,
									"lineHeight": "150%"
								},
								"tabletStyles": {},
								"mobileStyles": {"fontSize": "16px"},
								"rawStyles": {},
								"children": []
							}
						]
					},
					# Team grid shortcode (reads from About Us Settings)
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "team-grid-wrapper",
						"innerHTML": team_grid_jinja,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"width": "100%",
							"color": text_color
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": []
					}
				]
			}
		]
	}


def get_testimonials_template(context: dict) -> dict:
	"""Generate a testimonials section from context."""
	section = context.get("section_testimonials", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "testimonials"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	headline = section.get("headline", _("What Our Clients Say"))

	# Get testimonials from section or defaults
	testimonials = section.get("items", [])
	if not testimonials:
		testimonials = [
			{
				"quote": _("Excellent service and outstanding quality. Highly recommended!"),
				"author": "Jean-Pierre L.",
				"role": _("Customer"),
				"image": "https://i.pravatar.cc/100?img=11"
			},
			{
				"quote": _("A professional team that truly listens to their clients."),
				"author": "Marie D.",
				"role": _("Customer"),
				"image": "https://i.pravatar.cc/100?img=12"
			},
			{
				"quote": _("I've been a loyal customer for years. Always satisfied!"),
				"author": "Philippe M.",
				"role": _("Customer"),
				"image": "https://i.pravatar.cc/100?img=13"
			}
		]

	# Build testimonial cards
	testimonial_blocks = []
	for i, testimonial in enumerate(testimonials):
		testimonial_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "testimonial-card",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "20px",
				"padding": "32px",
				"backgroundColor": "#f9fafb",
				"borderRadius": "16px"
			},
			"tabletStyles": {},
			"mobileStyles": {"padding": "24px"},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "p",
					"blockName": "testimonial-quote",
					"innerHTML": f'"{testimonial.get("quote", "Great experience!")}"',
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "18px",
						"color": text_color,
						"lineHeight": "160%",
						"fontStyle": "italic"
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "16px"},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "testimonial-author",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"alignItems": "center",
						"gap": "12px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "img",
							"blockName": "author-image",
							"innerHTML": "",
							"attributes": {
								"src": testimonial.get("image", f"https://i.pravatar.cc/100?img={i+10}"),
								"alt": testimonial.get("author", "Author")
							},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"width": "48px",
								"height": "48px",
								"borderRadius": "50%",
								"objectFit": "cover"
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						},
						{
							"blockId": generate_block_id(),
							"element": "div",
							"blockName": "author-info",
							"innerHTML": "",
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"display": "flex",
								"flexDirection": "column",
								"gap": "4px"
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": [
								{
									"blockId": generate_block_id(),
									"element": "span",
									"blockName": "author-name",
									"innerHTML": testimonial.get("author", "Client"),
									"attributes": {},
									"customAttributes": {},
									"classes": [],
									"dataKey": None,
									"baseStyles": {
										"fontSize": "16px",
										"fontWeight": "600",
										"color": text_color
									},
									"tabletStyles": {},
									"mobileStyles": {},
									"rawStyles": {},
									"children": []
								},
								{
									"blockId": generate_block_id(),
									"element": "span",
									"blockName": "author-role",
									"innerHTML": testimonial.get("role", _("Customer")),
									"attributes": {},
									"customAttributes": {},
									"classes": [],
									"dataKey": None,
									"baseStyles": {
										"fontSize": "14px",
										"color": secondary_color
									},
									"tabletStyles": {},
									"mobileStyles": {},
									"rawStyles": {},
									"children": []
								}
							]
						}
					]
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "testimonials",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "testimonials-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "testimonials-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": text_color,
							"lineHeight": "120%",
							"textAlign": "center"
						},
						"tabletStyles": {"fontSize": "32px"},
						"mobileStyles": {"fontSize": "28px"},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "testimonials-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": f"repeat({min(len(testimonial_blocks), 3)}, 1fr)",
							"gap": "24px",
							"width": "100%"
						},
						"tabletStyles": {"gridTemplateColumns": "1fr"},
						"mobileStyles": {},
						"rawStyles": {},
						"children": testimonial_blocks
					}
				]
			}
		]
	}


def get_pricing_template(context: dict) -> dict:
	"""Generate a pricing section from context."""
	section = context.get("section_pricing", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "pricing"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	headline = section.get("headline", _("Our Pricing"))
	description = section.get("description", _("Choose the plan that fits your needs"))

	# Get pricing plans from section or defaults
	plans = section.get("items", [])
	if not plans:
		plans = [
			{
				"name": _("Basic"),
				"price": "29€",
				"period": _("/month"),
				"features": [_("Feature 1"), _("Feature 2"), _("Feature 3")],
				"cta": _("Get Started"),
				"highlighted": False
			},
			{
				"name": _("Pro"),
				"price": "59€",
				"period": _("/month"),
				"features": [_("All Basic features"), _("Feature 4"), _("Feature 5"), _("Priority support")],
				"cta": _("Get Started"),
				"highlighted": True
			},
			{
				"name": _("Enterprise"),
				"price": _("Custom"),
				"period": "",
				"features": [_("All Pro features"), _("Custom integrations"), _("Dedicated support"), _("SLA")],
				"cta": _("Contact Us"),
				"highlighted": False
			}
		]

	# Build pricing cards
	pricing_blocks = []
	for plan in plans:
		is_highlighted = plan.get("highlighted", False)

		# Build feature list
		feature_items = []
		for feature in plan.get("features", []):
			feature_items.append({
				"blockId": generate_block_id(),
				"element": "li",
				"blockName": "pricing-feature",
				"innerHTML": f"✓ {feature}",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "14px",
					"color": "#ffffff" if is_highlighted else secondary_color,
					"paddingTop": "8px",
					"paddingBottom": "8px"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			})

		pricing_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "pricing-card",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"padding": "32px",
				"backgroundColor": primary_color if is_highlighted else "#f9fafb",
				"borderRadius": "16px",
				"border": f"2px solid {primary_color}" if is_highlighted else "none",
				"transform": "scale(1.05)" if is_highlighted else "none"
			},
			"tabletStyles": {"transform": "none"},
			"mobileStyles": {"padding": "24px"},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "h3",
					"blockName": "plan-name",
					"innerHTML": plan.get("name", "Plan"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "24px",
						"fontWeight": "600",
						"color": "#ffffff" if is_highlighted else text_color,
						"marginBottom": "16px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "plan-price",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"alignItems": "baseline",
						"gap": "4px",
						"marginBottom": "24px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "span",
							"blockName": "price-amount",
							"innerHTML": plan.get("price", "0€"),
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "48px",
								"fontWeight": "700",
								"color": "#ffffff" if is_highlighted else text_color
							},
							"tabletStyles": {"fontSize": "40px"},
							"mobileStyles": {"fontSize": "36px"},
							"rawStyles": {},
							"children": []
						},
						{
							"blockId": generate_block_id(),
							"element": "span",
							"blockName": "price-period",
							"innerHTML": plan.get("period", ""),
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "16px",
								"color": "rgba(255,255,255,0.8)" if is_highlighted else secondary_color
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						}
					]
				},
				{
					"blockId": generate_block_id(),
					"element": "ul",
					"blockName": "plan-features",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"listStyle": "none",
						"padding": "0",
						"margin": "0",
						"marginBottom": "32px",
						"flexGrow": "1"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": feature_items
				},
				{
					"blockId": generate_block_id(),
					"element": "a",
					"blockName": "plan-cta",
					"innerHTML": plan.get("cta", _("Get Started")),
					"attributes": {"href": "#contact"},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"alignItems": "center",
						"justifyContent": "center",
						"padding": "16px 24px",
						"backgroundColor": "#ffffff" if is_highlighted else primary_color,
						"color": primary_color if is_highlighted else "#ffffff",
						"fontSize": "16px",
						"fontWeight": "600",
						"borderRadius": "12px",
						"textDecoration": "none"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {
						"hover:opacity": "0.9",
						"transition": "all 0.2s ease"
					},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "pricing",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "pricing-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "pricing-header",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"alignItems": "center",
							"gap": "16px",
							"textAlign": "center"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "h2",
								"blockName": "pricing-headline",
								"innerHTML": headline,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "40px",
									"fontWeight": "700",
									"color": text_color,
									"lineHeight": "120%"
								},
								"tabletStyles": {"fontSize": "32px"},
								"mobileStyles": {"fontSize": "28px"},
								"rawStyles": {},
								"children": []
							},
							{
								"blockId": generate_block_id(),
								"element": "p",
								"blockName": "pricing-description",
								"innerHTML": description,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "18px",
									"color": secondary_color,
									"lineHeight": "150%"
								},
								"tabletStyles": {},
								"mobileStyles": {"fontSize": "16px"},
								"rawStyles": {},
								"children": []
							}
						]
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "pricing-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": f"repeat({min(len(pricing_blocks), 3)}, 1fr)",
							"gap": "24px",
							"width": "100%",
							"alignItems": "center"
						},
						"tabletStyles": {"gridTemplateColumns": "1fr"},
						"mobileStyles": {},
						"rawStyles": {},
						"children": pricing_blocks
					}
				]
			}
		]
	}


def get_gallery_template(context: dict) -> dict:
	"""Generate a gallery section from context."""
	section = context.get("section_gallery", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "gallery"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	industry = context.get("industry", "business")

	headline = section.get("headline", _("Gallery"))

	# Get images from section or defaults based on industry
	images = section.get("items", [])
	if not images:
		# Default gallery images
		images = [
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 1")},
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 2")},
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 3")},
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 4")},
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 5")},
			{"src": get_unsplash_fallback(industry, "gallery"), "alt": _("Gallery image 6")},
		]

	# Build gallery items
	gallery_blocks = []
	for i, img in enumerate(images[:12]):  # Limit to 12 images
		gallery_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "gallery-item",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"position": "relative",
				"aspectRatio": "1",
				"overflow": "hidden",
				"borderRadius": "12px"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "img",
					"blockName": "gallery-image",
					"innerHTML": "",
					"attributes": {
						"src": img.get("src", f"https://source.unsplash.com/400x400/?{industry}"),
						"alt": img.get("alt", f"Gallery image {i+1}")
					},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"width": "100%",
						"height": "100%",
						"objectFit": "cover"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {
						"hover:transform": "scale(1.05)",
						"transition": "transform 0.3s ease"
					},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "gallery",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "gallery-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "gallery-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": text_color,
							"lineHeight": "120%",
							"textAlign": "center"
						},
						"tabletStyles": {"fontSize": "32px"},
						"mobileStyles": {"fontSize": "28px"},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "gallery-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": "repeat(3, 1fr)",
							"gap": "16px",
							"width": "100%"
						},
						"tabletStyles": {"gridTemplateColumns": "repeat(2, 1fr)"},
						"mobileStyles": {"gridTemplateColumns": "1fr"},
						"rawStyles": {},
						"children": gallery_blocks
					}
				]
			}
		]
	}


def get_faq_template(context: dict) -> dict:
	"""Generate a FAQ section from context."""
	section = context.get("section_faq", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "faq"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	headline = section.get("headline", _("Frequently Asked Questions"))

	# Get FAQ items from section or defaults
	faqs = section.get("items", [])
	if not faqs:
		faqs = [
			{
				"question": _("What are your opening hours?"),
				"answer": _("We are open Monday to Friday from 9am to 6pm, and Saturday from 10am to 4pm.")
			},
			{
				"question": _("Do you offer delivery?"),
				"answer": _("Yes, we offer delivery within a 20km radius. Delivery is free for orders over 50€.")
			},
			{
				"question": _("How can I contact you?"),
				"answer": _("You can reach us by phone, email, or through our contact form. We typically respond within 24 hours.")
			},
			{
				"question": _("What payment methods do you accept?"),
				"answer": _("We accept credit cards (Visa, MasterCard), bank transfers, and cash payments.")
			}
		]

	# Build FAQ items (accordion-style)
	faq_blocks = []
	for faq in faqs:
		faq_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "faq-item",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "12px",
				"padding": "24px",
				"backgroundColor": "#f9fafb",
				"borderRadius": "12px",
				"borderLeft": f"4px solid {primary_color}"
			},
			"tabletStyles": {},
			"mobileStyles": {"padding": "20px"},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "h4",
					"blockName": "faq-question",
					"innerHTML": faq.get("question", "Question?"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "18px",
						"fontWeight": "600",
						"color": text_color,
						"lineHeight": "140%"
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "16px"},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "p",
					"blockName": "faq-answer",
					"innerHTML": faq.get("answer", "Answer."),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"color": secondary_color,
						"lineHeight": "160%"
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "14px"},
					"rawStyles": {},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "faq",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "faq-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "800px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h2",
						"blockName": "faq-headline",
						"innerHTML": headline,
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "40px",
							"fontWeight": "700",
							"color": text_color,
							"lineHeight": "120%",
							"textAlign": "center"
						},
						"tabletStyles": {"fontSize": "32px"},
						"mobileStyles": {"fontSize": "28px"},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "faq-list",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"gap": "16px",
							"width": "100%"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": faq_blocks
					}
				]
			}
		]
	}


def get_stats_template(context: dict) -> dict:
	"""Generate a stats/numbers section from context."""
	section = context.get("section_stats", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "stats"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	# Get stats from section or defaults
	stats = section.get("items", [])
	if not stats:
		stats = [
			{"value": "10+", "label": _("Years of Experience")},
			{"value": "500+", "label": _("Happy Clients")},
			{"value": "1000+", "label": _("Projects Completed")},
			{"value": "24/7", "label": _("Support Available")},
		]

	# Build stat items
	stat_blocks = []
	for stat in stats:
		stat_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "stat-item",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"alignItems": "center",
				"gap": "8px",
				"textAlign": "center"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "span",
					"blockName": "stat-value",
					"innerHTML": stat.get("value", "0"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "48px",
						"fontWeight": "700",
						"color": primary_color,
						"lineHeight": "100%"
					},
					"tabletStyles": {"fontSize": "40px"},
					"mobileStyles": {"fontSize": "36px"},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "span",
					"blockName": "stat-label",
					"innerHTML": stat.get("label", "Stat"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"color": secondary_color,
						"fontWeight": "500"
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "14px"},
					"rawStyles": {},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "stats",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "80px",
			"paddingBottom": "80px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#f9fafb"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "stats-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "grid",
					"gridTemplateColumns": f"repeat({min(len(stat_blocks), 4)}, 1fr)",
					"gap": "48px",
					"maxWidth": "1000px",
					"width": "100%"
				},
				"tabletStyles": {"gridTemplateColumns": "repeat(2, 1fr)", "gap": "32px"},
				"mobileStyles": {"gridTemplateColumns": "repeat(2, 1fr)", "gap": "24px"},
				"rawStyles": {},
				"children": stat_blocks
			}
		]
	}


def get_process_template(context: dict) -> dict:
	"""Generate a process/steps section from context."""
	section = context.get("section_process", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "process"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	headline = section.get("headline", _("How It Works"))
	description = section.get("description", _("Simple steps to get started"))

	# Get steps from section or defaults
	steps = section.get("items", [])
	if not steps:
		steps = [
			{"title": _("Contact Us"), "description": _("Reach out to discuss your needs")},
			{"title": _("Get a Quote"), "description": _("We'll provide a detailed estimate")},
			{"title": _("We Deliver"), "description": _("Sit back while we handle everything")},
		]

	# Build step items
	step_blocks = []
	for i, step in enumerate(steps):
		step_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "process-step",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"alignItems": "center",
				"gap": "16px",
				"textAlign": "center",
				"position": "relative"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "step-number",
					"innerHTML": str(i + 1),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"alignItems": "center",
						"justifyContent": "center",
						"width": "48px",
						"height": "48px",
						"backgroundColor": primary_color,
						"color": "#ffffff",
						"fontSize": "20px",
						"fontWeight": "700",
						"borderRadius": "50%"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "h4",
					"blockName": "step-title",
					"innerHTML": step.get("title", f"Step {i+1}"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "20px",
						"fontWeight": "600",
						"color": text_color
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "18px"},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "p",
					"blockName": "step-description",
					"innerHTML": step.get("description", "Description"),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"color": secondary_color,
						"lineHeight": "150%",
						"maxWidth": "250px"
					},
					"tabletStyles": {},
					"mobileStyles": {"fontSize": "14px"},
					"rawStyles": {},
					"children": []
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "process",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#ffffff"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "process-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1000px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "process-header",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"alignItems": "center",
							"gap": "16px",
							"textAlign": "center"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "h2",
								"blockName": "process-headline",
								"innerHTML": headline,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "40px",
									"fontWeight": "700",
									"color": text_color,
									"lineHeight": "120%"
								},
								"tabletStyles": {"fontSize": "32px"},
								"mobileStyles": {"fontSize": "28px"},
								"rawStyles": {},
								"children": []
							},
							{
								"blockId": generate_block_id(),
								"element": "p",
								"blockName": "process-description",
								"innerHTML": description,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "18px",
									"color": secondary_color,
									"lineHeight": "150%"
								},
								"tabletStyles": {},
								"mobileStyles": {"fontSize": "16px"},
								"rawStyles": {},
								"children": []
							}
						]
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "process-steps",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": f"repeat({min(len(step_blocks), 4)}, 1fr)",
							"gap": "32px",
							"width": "100%"
						},
						"tabletStyles": {"gridTemplateColumns": "repeat(2, 1fr)"},
						"mobileStyles": {"gridTemplateColumns": "1fr"},
						"rawStyles": {},
						"children": step_blocks
					}
				]
			}
		]
	}


def get_product_carousel_template(context: dict) -> dict:
	"""Generate a product carousel section for e-commerce sites."""
	section = context.get("section_product_carousel", {})
	if not section:
		section = next((s for s in context.get("sections", []) if s.get("type") == "product_carousel"), {})

	style = context.get("style", {})
	text_color = style.get("text_color") or "#171717"
	secondary_color = style.get("secondary_color") or "#6B7280"
	primary_color = style.get("primary_color") or "#171717"

	headline = section.get("headline", _("Featured Products"))
	description = section.get("description", _("Discover our best sellers"))

	# Get products from section or defaults
	products = section.get("items", [])
	if not products:
		products = [
			{"name": _("Product 1"), "price": "29.99€", "image": "https://source.unsplash.com/300x300/?product"},
			{"name": _("Product 2"), "price": "49.99€", "image": "https://source.unsplash.com/300x300/?fashion"},
			{"name": _("Product 3"), "price": "39.99€", "image": "https://source.unsplash.com/300x300/?accessories"},
			{"name": _("Product 4"), "price": "59.99€", "image": "https://source.unsplash.com/300x300/?electronics"},
		]

	# Build product cards
	product_blocks = []
	for product in products[:8]:  # Limit to 8 products
		product_blocks.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "product-card",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "12px",
				"backgroundColor": "#ffffff",
				"borderRadius": "12px",
				"overflow": "hidden",
				"boxShadow": "0 2px 8px rgba(0,0,0,0.08)"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {
				"hover:boxShadow": "0 4px 16px rgba(0,0,0,0.12)",
				"transition": "box-shadow 0.3s ease"
			},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "product-image-wrapper",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"position": "relative",
						"aspectRatio": "1",
						"overflow": "hidden"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "img",
							"blockName": "product-image",
							"innerHTML": "",
							"attributes": {
								"src": product.get("image", "https://source.unsplash.com/300x300/?product"),
								"alt": product.get("name", "Product")
							},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"width": "100%",
								"height": "100%",
								"objectFit": "cover"
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {
								"hover:transform": "scale(1.05)",
								"transition": "transform 0.3s ease"
							},
							"children": []
						}
					]
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "product-info",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "column",
						"gap": "8px",
						"padding": "16px"
					},
					"tabletStyles": {},
					"mobileStyles": {"padding": "12px"},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "h4",
							"blockName": "product-name",
							"innerHTML": product.get("name", "Product"),
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "16px",
								"fontWeight": "600",
								"color": text_color
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						},
						{
							"blockId": generate_block_id(),
							"element": "span",
							"blockName": "product-price",
							"innerHTML": product.get("price", "0€"),
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "18px",
								"fontWeight": "700",
								"color": primary_color
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						}
					]
				}
			]
		})

	return {
		"blockId": generate_block_id(),
		"element": "section",
		"blockName": "product-carousel",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "100px",
			"paddingBottom": "100px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#f9fafb"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "60px",
			"paddingBottom": "60px"
		},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "products-container",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"alignItems": "center",
					"gap": "48px",
					"maxWidth": "1200px",
					"width": "100%"
				},
				"tabletStyles": {},
				"mobileStyles": {"gap": "32px"},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "products-header",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"flexDirection": "column",
							"alignItems": "center",
							"gap": "16px",
							"textAlign": "center"
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": [
							{
								"blockId": generate_block_id(),
								"element": "h2",
								"blockName": "products-headline",
								"innerHTML": headline,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "40px",
									"fontWeight": "700",
									"color": text_color,
									"lineHeight": "120%"
								},
								"tabletStyles": {"fontSize": "32px"},
								"mobileStyles": {"fontSize": "28px"},
								"rawStyles": {},
								"children": []
							},
							{
								"blockId": generate_block_id(),
								"element": "p",
								"blockName": "products-description",
								"innerHTML": description,
								"attributes": {},
								"customAttributes": {},
								"classes": [],
								"dataKey": None,
								"baseStyles": {
									"fontSize": "18px",
									"color": secondary_color,
									"lineHeight": "150%"
								},
								"tabletStyles": {},
								"mobileStyles": {"fontSize": "16px"},
								"rawStyles": {},
								"children": []
							}
						]
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "products-grid",
						"innerHTML": "",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "grid",
							"gridTemplateColumns": f"repeat({min(len(product_blocks), 4)}, 1fr)",
							"gap": "24px",
							"width": "100%"
						},
						"tabletStyles": {"gridTemplateColumns": "repeat(2, 1fr)"},
						"mobileStyles": {"gridTemplateColumns": "1fr"},
						"rawStyles": {},
						"children": product_blocks
					},
					{
						"blockId": generate_block_id(),
						"element": "a",
						"blockName": "view-all-products",
						"innerHTML": _("View All Products"),
						"attributes": {"href": "/all-products"},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"display": "flex",
							"alignItems": "center",
							"justifyContent": "center",
							"padding": "16px 32px",
							"backgroundColor": primary_color,
							"color": "#ffffff",
							"fontSize": "16px",
							"fontWeight": "600",
							"borderRadius": "12px",
							"textDecoration": "none"
						},
						"tabletStyles": {},
						"mobileStyles": {"width": "100%"},
						"rawStyles": {
							"hover:opacity": "0.9",
							"transition": "all 0.2s ease"
						},
						"children": []
					}
				]
			}
		]
	}


def get_footer_template(context: dict) -> dict:
	"""
	Generate a footer section from context.

	Supports three footer styles based on functionality_type:
	- vitrine: Minimal footer (brand + copyright)
	- vitrine_with_login: Standard footer (brand + links + contact)
	- ecommerce: Extended footer (newsletter + payment icons + social + multiple columns)
	"""
	style = context.get("style", {})
	contact = context.get("contact_info", {})
	business_name = context.get("business_name", "")
	footer_config = context.get("footer", {})
	functionality_type = context.get("functionality_type", "vitrine")

	text_color = style.get("text_color") or "#171717"
	secondary_text = style.get("secondary_color") or "#525252"
	primary_color = style.get("primary_color") or "#171717"

	# Determine footer style based on functionality type
	footer_style = footer_config.get("style")
	if not footer_style:
		footer_style = {
			"vitrine": "minimal",
			"vitrine_with_login": "detailed",
			"ecommerce": "mega"
		}.get(functionality_type, "minimal")

	# Build footer children based on style
	footer_children = []

	if footer_style == "mega":
		# E-commerce mega footer with multiple columns
		footer_children = _build_mega_footer(context, text_color, secondary_text, primary_color)
	elif footer_style == "detailed":
		# Detailed footer with links and contact
		footer_children = _build_detailed_footer(context, text_color, secondary_text)
	else:
		# Minimal footer - just brand and copyright
		footer_children = _build_minimal_footer(context, text_color, secondary_text)

	return {
		"blockId": generate_block_id(),
		"element": "footer",
		"blockName": "footer",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": ["site-footer"],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"width": "100%",
			"paddingTop": "60px" if footer_style == "minimal" else "80px",
			"paddingBottom": "60px" if footer_style == "minimal" else "40px",
			"paddingLeft": "20px",
			"paddingRight": "20px",
			"backgroundColor": "#f9fafb",
			"borderTop": "1px solid #e5e7eb"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "40px",
			"paddingBottom": "40px"
		},
		"rawStyles": {},
		"children": footer_children
	}


def _build_minimal_footer(context: dict, text_color: str, secondary_text: str) -> list:
	"""Build minimal footer with brand and copyright only."""
	business_name = context.get("business_name", "")

	return [{
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "footer-container",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"alignItems": "center",
			"gap": "24px",
			"maxWidth": "1200px",
			"width": "100%",
			"textAlign": "center"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "p",
				"blockName": "footer-brand",
				"innerHTML": f"<p><strong>{business_name}</strong></p>",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "18px",
					"fontWeight": "600",
					"color": text_color
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "p",
				"blockName": "footer-copyright",
				"innerHTML": f"<p>&copy; 2025 {business_name}. Tous droits réservés.</p>",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "14px",
					"color": secondary_text
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			}
		]
	}]


def _build_detailed_footer(context: dict, text_color: str, secondary_text: str) -> list:
	"""Build detailed footer with links and contact info."""
	business_name = context.get("business_name", "")
	contact_info = context.get("contact_info", {})
	description = context.get("description", "")

	# Build link columns
	link_blocks = []

	# About column
	about_text = description[:150] + "..." if len(description) > 150 else description
	if not about_text:
		about_text = f"{business_name} - Votre partenaire de confiance."

	link_blocks.append({
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "footer-about",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			"flex": "1",
			"minWidth": "200px"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "h4",
				"blockName": "footer-about-title",
				"innerHTML": business_name,
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "16px",
					"fontWeight": "600",
					"color": text_color
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "p",
				"blockName": "footer-about-text",
				"innerHTML": f"<p>{about_text}</p>",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "14px",
					"lineHeight": "160%",
					"color": secondary_text
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			}
		]
	})

	# Contact column if contact info exists
	if contact_info:
		contact_items = []
		if contact_info.get("address"):
			contact_items.append(f"<p>{contact_info.get('address')}</p>")
		if contact_info.get("phone"):
			contact_items.append(f"<p>{contact_info.get('phone')}</p>")
		if contact_info.get("email"):
			contact_items.append(f"<p>{contact_info.get('email')}</p>")

		if contact_items:
			link_blocks.append({
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "footer-contact",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"gap": "16px",
					"flex": "1",
					"minWidth": "200px"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "h4",
						"blockName": "footer-contact-title",
						"innerHTML": "Contact",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "16px",
							"fontWeight": "600",
							"color": text_color
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": []
					},
					{
						"blockId": generate_block_id(),
						"element": "div",
						"blockName": "footer-contact-info",
						"innerHTML": "".join(contact_items),
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "14px",
							"lineHeight": "180%",
							"color": secondary_text
						},
						"tabletStyles": {},
						"mobileStyles": {},
						"rawStyles": {},
						"children": []
					}
				]
			})

	return [
		{
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "footer-container",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "48px",
				"maxWidth": "1200px",
				"width": "100%"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "footer-columns",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "row",
						"flexWrap": "wrap",
						"gap": "48px",
						"width": "100%"
					},
					"tabletStyles": {},
					"mobileStyles": {
						"flexDirection": "column",
						"gap": "32px"
					},
					"rawStyles": {},
					"children": link_blocks
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "footer-bottom",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "row",
						"justifyContent": "center",
						"paddingTop": "24px",
						"borderTop": "1px solid #e5e7eb",
						"width": "100%"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "p",
							"blockName": "footer-copyright",
							"innerHTML": f"<p>&copy; 2025 {business_name}. Tous droits réservés.</p>",
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "14px",
								"color": secondary_text
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						}
					]
				}
			]
		}
	]


def _build_mega_footer(context: dict, text_color: str, secondary_text: str, primary_color: str) -> list:
	"""Build mega footer for e-commerce with newsletter, payment icons, and social."""
	business_name = context.get("business_name", "")
	contact_info = context.get("contact_info", {})
	description = context.get("description", "")
	footer_config = context.get("footer", {})

	# About text
	about_text = description[:150] + "..." if len(description) > 150 else description
	if not about_text:
		about_text = f"{business_name} - Votre boutique en ligne de confiance."

	# Build columns
	columns = []

	# Column 1: About + Social
	columns.append({
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "footer-col-about",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"gap": "20px",
			"flex": "2",
			"minWidth": "250px"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "h4",
				"blockName": "footer-brand-title",
				"innerHTML": business_name,
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "18px",
					"fontWeight": "700",
					"color": text_color
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "p",
				"blockName": "footer-about-desc",
				"innerHTML": f"<p>{about_text}</p>",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "14px",
					"lineHeight": "160%",
					"color": secondary_text
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			}
		]
	})

	# Column 2: Shop Links
	columns.append({
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "footer-col-shop",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			"flex": "1",
			"minWidth": "150px"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "h4",
				"blockName": "footer-shop-title",
				"innerHTML": "Boutique",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "16px",
					"fontWeight": "600",
					"color": text_color
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "nav",
				"blockName": "footer-shop-links",
				"innerHTML": """
					<a href="/shop">Tous les produits</a>
					<a href="/shop?category=new">Nouveautés</a>
					<a href="/shop?category=promo">Promotions</a>
				""",
				"attributes": {},
				"customAttributes": {},
				"classes": ["footer-links"],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"gap": "12px",
					"fontSize": "14px",
					"color": secondary_text
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			}
		]
	})

	# Column 3: Account Links
	columns.append({
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "footer-col-account",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": [],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			"flex": "1",
			"minWidth": "150px"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": [
			{
				"blockId": generate_block_id(),
				"element": "h4",
				"blockName": "footer-account-title",
				"innerHTML": "Mon compte",
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"dataKey": None,
				"baseStyles": {
					"fontSize": "16px",
					"fontWeight": "600",
					"color": text_color
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			},
			{
				"blockId": generate_block_id(),
				"element": "nav",
				"blockName": "footer-account-links",
				"innerHTML": """
					<a href="/me">Mon profil</a>
					<a href="/orders">Mes commandes</a>
					<a href="/wishlist">Ma liste d'envies</a>
				""",
				"attributes": {},
				"customAttributes": {},
				"classes": ["footer-links"],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "column",
					"gap": "12px",
					"fontSize": "14px",
					"color": secondary_text
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": []
			}
		]
	})

	# Column 4: Contact
	if contact_info:
		contact_html = ""
		if contact_info.get("address"):
			contact_html += f"<p>{contact_info.get('address')}</p>"
		if contact_info.get("phone"):
			contact_html += f"<p>{contact_info.get('phone')}</p>"
		if contact_info.get("email"):
			contact_html += f"<p>{contact_info.get('email')}</p>"

		columns.append({
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "footer-col-contact",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "16px",
				"flex": "1",
				"minWidth": "180px"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "h4",
					"blockName": "footer-contact-title",
					"innerHTML": "Contact",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"fontWeight": "600",
						"color": text_color
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "footer-contact-info",
					"innerHTML": contact_html,
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "14px",
						"lineHeight": "180%",
						"color": secondary_text
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				}
			]
		})

	# Newsletter section (optional for e-commerce)
	newsletter_section = []
	if footer_config.get("includes_newsletter", True):
		newsletter_section = [{
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "footer-newsletter",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"alignItems": "center",
				"gap": "16px",
				"paddingBottom": "40px",
				"marginBottom": "40px",
				"borderBottom": "1px solid #e5e7eb",
				"width": "100%",
				"textAlign": "center"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": [
				{
					"blockId": generate_block_id(),
					"element": "h4",
					"blockName": "newsletter-title",
					"innerHTML": "Restez informé",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "18px",
						"fontWeight": "600",
						"color": text_color
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "p",
					"blockName": "newsletter-desc",
					"innerHTML": "<p>Inscrivez-vous pour recevoir nos offres exclusives et nos nouveautés.</p>",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "14px",
						"color": secondary_text,
						"maxWidth": "400px"
					},
					"tabletStyles": {},
					"mobileStyles": {},
					"rawStyles": {},
					"children": []
				},
				{
					"blockId": generate_block_id(),
					"element": "form",
					"blockName": "newsletter-form",
					"innerHTML": """
						<input type="email" placeholder="Votre email" style="padding: 12px 16px; border: 1px solid #d1d5db; border-radius: 8px 0 0 8px; flex: 1; min-width: 200px;" />
						<button type="submit" style="padding: 12px 24px; background-color: #171717; color: white; border: none; border-radius: 0 8px 8px 0; font-weight: 600; cursor: pointer;">S'inscrire</button>
					""",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "row",
						"maxWidth": "450px",
						"width": "100%"
					},
					"tabletStyles": {},
					"mobileStyles": {
						"flexDirection": "column",
						"gap": "8px"
					},
					"rawStyles": {},
					"children": []
				}
			]
		}]

	return [
		{
			"blockId": generate_block_id(),
			"element": "div",
			"blockName": "footer-container",
			"innerHTML": "",
			"attributes": {},
			"customAttributes": {},
			"classes": [],
			"dataKey": None,
			"baseStyles": {
				"display": "flex",
				"flexDirection": "column",
				"gap": "0",
				"maxWidth": "1200px",
				"width": "100%"
			},
			"tabletStyles": {},
			"mobileStyles": {},
			"rawStyles": {},
			"children": newsletter_section + [
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "footer-columns",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "row",
						"flexWrap": "wrap",
						"gap": "48px",
						"width": "100%",
						"marginBottom": "40px"
					},
					"tabletStyles": {},
					"mobileStyles": {
						"flexDirection": "column",
						"gap": "32px"
					},
					"rawStyles": {},
					"children": columns
				},
				{
					"blockId": generate_block_id(),
					"element": "div",
					"blockName": "footer-bottom",
					"innerHTML": "",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"display": "flex",
						"flexDirection": "row",
						"justifyContent": "space-between",
						"alignItems": "center",
						"paddingTop": "24px",
						"borderTop": "1px solid #e5e7eb",
						"width": "100%"
					},
					"tabletStyles": {},
					"mobileStyles": {
						"flexDirection": "column",
						"gap": "16px",
						"textAlign": "center"
					},
					"rawStyles": {},
					"children": [
						{
							"blockId": generate_block_id(),
							"element": "p",
							"blockName": "footer-copyright",
							"innerHTML": f"<p>&copy; 2025 {business_name}. Tous droits réservés.</p>",
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"fontSize": "14px",
								"color": secondary_text
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						},
						{
							"blockId": generate_block_id(),
							"element": "div",
							"blockName": "footer-payment-icons",
							"innerHTML": """
								<span style="font-size: 24px;">💳</span>
								<span style="font-size: 24px;">🏦</span>
							""",
							"attributes": {},
							"customAttributes": {},
							"classes": [],
							"dataKey": None,
							"baseStyles": {
								"display": "flex",
								"flexDirection": "row",
								"gap": "12px",
								"alignItems": "center"
							},
							"tabletStyles": {},
							"mobileStyles": {},
							"rawStyles": {},
							"children": []
						}
					]
				}
			]
		}
	]


# =============================================================================
# NAVBAR TEMPLATES WITH SHORTCODE INTEGRATION
# =============================================================================

def get_requires_features(context: dict) -> dict:
	"""
	Get required features based on functionality_type.

	Returns a dict with boolean flags for each feature.
	"""
	functionality_type = context.get("functionality_type", "vitrine")

	# Default feature mapping based on functionality type
	feature_maps = {
		"vitrine": {
			"cart": False,
			"wishlist": False,
			"user_menu": False,
			"search": False,
			"mobile_menu": True
		},
		"vitrine_with_login": {
			"cart": False,
			"wishlist": False,
			"user_menu": True,
			"search": False,
			"mobile_menu": True
		},
		"ecommerce": {
			"cart": True,
			"wishlist": True,
			"user_menu": True,
			"search": True,
			"mobile_menu": True
		}
	}

	# Use the mapped features or fall back to context-provided requires_features
	features = feature_maps.get(functionality_type, feature_maps["vitrine"])

	# Allow context to override specific features
	context_features = context.get("requires_features", {})
	if context_features:
		features.update(context_features)

	return features


def get_shortcode_jinja(shortcode_name: str, settings=None) -> str:
	"""
	Get the Jinja code for a shortcode from settings.

	Args:
		shortcode_name: Name of the shortcode (e.g., "cart", "wishlist")
		settings: Builder AI Settings document (optional)

	Returns:
		Jinja include directive string
	"""
	# Default shortcode mappings
	default_jinja = {
		# Navbar shortcodes
		"cart": "{% include 'webshop/templates/includes/cart_component.html' %}",
		"wishlist": "{% include 'webshop/templates/includes/wishlist_component.html' %}",
		"user_menu": "{% include 'webshop/templates/includes/user_header.html' %}",
		"search": "{% include 'webshop/templates/includes/search_box.html' %}",
		"mobile_menu": "{% include 'webshop/templates/includes/mobile_menu.html' %}",
		# Content shortcodes
		"contact_form": "{% include 'builder/templates/includes/contact_form.html' %}",
		"contact_info": "{% include 'builder/templates/includes/contact_info.html' %}",
		"team_grid": "{% include 'builder/templates/includes/team_grid.html' %}",
		"company_timeline": "{% include 'builder/templates/includes/company_timeline.html' %}"
	}

	# Try to get from settings if available
	if settings and hasattr(settings, 'shortcodes') and settings.shortcodes:
		for sc in settings.shortcodes:
			if sc.shortcode == shortcode_name and sc.jinja_code:
				return sc.jinja_code

	return default_jinja.get(shortcode_name, "")


def get_navbar_action_block(shortcode_name: str, context: dict, settings=None) -> dict:
	"""
	Generate a navbar action block containing a shortcode.

	Args:
		shortcode_name: Name of the shortcode (cart, wishlist, user_menu, search)
		context: Site context
		settings: Builder AI Settings (optional)

	Returns:
		Block dict with Jinja innerHTML
	"""
	jinja_code = get_shortcode_jinja(shortcode_name, settings)

	return {
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": f"navbar-{shortcode_name}",
		"innerHTML": jinja_code,
		"attributes": {},
		"customAttributes": {},
		"classes": [f"navbar-action-{shortcode_name}"],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"alignItems": "center",
			"justifyContent": "center"
		},
		"tabletStyles": {},
		"mobileStyles": {},
		"rawStyles": {},
		"children": []
	}


def get_navbar_template(context: dict, settings=None) -> dict:
	"""
	Generate a navbar block with appropriate shortcodes based on site type.

	Args:
		context: Site context with functionality_type and requires_features
		settings: Builder AI Settings (optional)

	Returns:
		Complete navbar block structure
	"""
	style = context.get("style", {})
	business_name = context.get("business_name", "")
	header_config = context.get("header", {})

	# Extract colors
	primary_color = style.get("primary_color") or "#171717"
	text_color = style.get("text_color") or "#171717"
	bg_color = style.get("background_color") or "#ffffff"

	# Get required features
	features = get_requires_features(context)

	# Build menu items from context
	menu_items = context.get("menu_items", [])

	# If no explicit menu_items, build from pages array or sections
	if not menu_items:
		pages = context.get("pages", [])
		site_type = context.get("site_type", "one_page")
		functionality_type = context.get("functionality_type", "vitrine")

		# For one-page sites, use anchor links based on sections
		if site_type == "one_page" or (len(pages) == 1 and pages[0].get("is_main", False)):
			# Get sections from the main page or context
			sections = []
			if pages and pages[0].get("sections"):
				sections = pages[0].get("sections", [])
			else:
				sections = [s.get("type") for s in context.get("sections", [])]

			# Build anchor links from sections
			menu_items = [{"label": _("Home"), "link": "/"}]

			# Map section types to menu labels
			section_labels = {
				"hero": None,  # Skip hero, it's at the top
				"features": _("Services"),
				"services": _("Services"),
				"about": _("About"),
				"team": _("Team"),
				"testimonials": _("Testimonials"),
				"cta": None,  # Skip CTA, not a navigation target
				"contact": _("Contact"),
				"faq": _("FAQ"),
				"pricing": _("Pricing"),
				"gallery": _("Gallery")
			}

			for section in sections:
				section_type = section if isinstance(section, str) else section.get("type", "")
				label = section_labels.get(section_type)
				if label:
					menu_items.append({"label": label, "link": f"#{section_type}"})

			# Ensure Contact is always present for vitrine
			if not any(item.get("link") == "#contact" for item in menu_items):
				menu_items.append({"label": _("Contact"), "link": "#contact"})

		elif pages and len(pages) > 1:
			# Multi-page site: Build menu from pages array
			for page in pages:
				route = page.get("route", f"/{page.get('name', '')}")
				title = page.get("title", page.get("name", "Page"))

				# Ensure route format is correct
				if route == "/" or page.get("is_main", False):
					link = "/"
				else:
					# Ensure route starts with / for multi-page
					link = route if route.startswith("/") else f"/{route}"

				menu_items.append({
					"label": _(title),
					"link": link
				})

			# For e-commerce, add shop link if not already present
			if functionality_type == "ecommerce":
				has_shop = any(item.get("link") in ["/all-products", "/shop", "/products"] for item in menu_items)
				if not has_shop:
					# Insert shop link after home
					menu_items.insert(1, {"label": _("Shop"), "link": "/all-products"})

		else:
			# Fallback to default menu items based on site type
			if functionality_type == "ecommerce":
				# E-commerce: real page links for multi-page site
				menu_items = [
					{"label": _("Home"), "link": "/"},
					{"label": _("Shop"), "link": "/all-products"},
					{"label": _("Contact"), "link": "/contact-us"}
				]
			elif functionality_type == "vitrine_with_login":
				# Showcase with login: mix of pages and anchors
				menu_items = [
					{"label": _("Home"), "link": "/"},
					{"label": _("Services"), "link": "#services"},
					{"label": _("About"), "link": "#about"},
					{"label": _("Contact"), "link": "/contact-us"}
				]
			elif site_type == "multi_page":
				# Multi-page vitrine: real page links
				menu_items = [
					{"label": _("Home"), "link": "/"},
					{"label": _("About"), "link": "/about"},
					{"label": _("Services"), "link": "/services"},
					{"label": _("Contact"), "link": "/contact"}
				]
			else:
				# Basic showcase (one-page): anchor links
				menu_items = [
					{"label": _("Home"), "link": "/"},
					{"label": _("Services"), "link": "#services"},
					{"label": _("Contact"), "link": "#contact"}
				]

	# Generate menu item blocks
	menu_blocks = []
	for item in menu_items:
		menu_blocks.append({
			"blockId": generate_block_id(),
			"element": "a",
			"blockName": "nav-link",
			"innerHTML": item.get("label", ""),
			"attributes": {
				"href": item.get("link", "#")
			},
			"customAttributes": {},
			"classes": ["nav-link"],
			"dataKey": None,
			"baseStyles": {
				"color": text_color,
				"textDecoration": "none",
				"fontSize": "15px",
				"fontWeight": "500",
				"padding": "8px 16px",
				"borderRadius": "8px"
			},
			"tabletStyles": {},
			"mobileStyles": {
				"display": "none"
			},
			"rawStyles": {
				"hover:backgroundColor": "#f3f4f6",
				"transition": "background-color 0.2s ease"
			},
			"children": []
		})

	# Build navbar actions (shortcodes)
	action_blocks = []

	if features.get("search"):
		action_blocks.append(get_navbar_action_block("search", context, settings))

	if features.get("wishlist"):
		action_blocks.append(get_navbar_action_block("wishlist", context, settings))

	if features.get("cart"):
		action_blocks.append(get_navbar_action_block("cart", context, settings))

	if features.get("user_menu"):
		action_blocks.append(get_navbar_action_block("user_menu", context, settings))

	# Mobile menu toggle (always included for responsive)
	mobile_menu_block = {
		"blockId": generate_block_id(),
		"element": "div",
		"blockName": "navbar-mobile-toggle",
		"innerHTML": get_shortcode_jinja("mobile_menu", settings) if features.get("mobile_menu") else """
			<button class="mobile-menu-toggle" aria-label="Menu">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<line x1="3" y1="6" x2="21" y2="6"></line>
					<line x1="3" y1="12" x2="21" y2="12"></line>
					<line x1="3" y1="18" x2="21" y2="18"></line>
				</svg>
			</button>
		""",
		"attributes": {},
		"customAttributes": {},
		"classes": ["mobile-menu-container"],
		"dataKey": None,
		"baseStyles": {
			"display": "none"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"display": "flex",
			"alignItems": "center"
		},
		"rawStyles": {},
		"children": []
	}

	# Determine header style
	header_style = header_config.get("style", "solid")
	header_bg = "transparent" if header_style == "transparent" else bg_color

	return {
		"blockId": generate_block_id(),
		"element": "header",
		"blockName": "navbar",
		"innerHTML": "",
		"attributes": {},
		"customAttributes": {},
		"classes": ["site-navbar"],
		"dataKey": None,
		"baseStyles": {
			"display": "flex",
			"flexDirection": "row",
			"alignItems": "center",
			"justifyContent": "space-between",
			"width": "100%",
			"paddingTop": "16px",
			"paddingBottom": "16px",
			"paddingLeft": "24px",
			"paddingRight": "24px",
			"backgroundColor": header_bg,
			"position": "sticky" if header_style == "sticky" else "relative",
			"top": "0" if header_style == "sticky" else "auto",
			"zIndex": "1000" if header_style == "sticky" else "auto",
			"borderBottom": "1px solid #e5e7eb" if header_style != "transparent" else "none"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingLeft": "16px",
			"paddingRight": "16px"
		},
		"rawStyles": {},
		"children": [
			# Logo/Brand - Always use logo image
			{
				"blockId": generate_block_id(),
				"element": "a",
				"blockName": "navbar-brand",
				"innerHTML": "",
				"attributes": {
					"href": "/"
				},
				"customAttributes": {},
				"classes": ["navbar-brand"],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"alignItems": "center",
					"textDecoration": "none"
				},
				"tabletStyles": {},
				"mobileStyles": {},
				"rawStyles": {},
				"children": [
					{
						"blockId": generate_block_id(),
						"element": "img",
						"blockName": "navbar-logo",
						"innerHTML": "",
						"attributes": {
							"src": "/files/logo-default.png",
							"alt": business_name or "Logo"
						},
						"customAttributes": {},
						"classes": ["navbar-logo"],
						"dataKey": None,
						"baseStyles": {
							"height": "40px",
							"width": "auto",
							"objectFit": "contain"
						},
						"tabletStyles": {
							"height": "36px"
						},
						"mobileStyles": {
							"height": "32px"
						},
						"rawStyles": {},
						"children": []
					}
				]
			},
			# Navigation menu
			{
				"blockId": generate_block_id(),
				"element": "nav",
				"blockName": "navbar-menu",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": ["navbar-menu"],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "row",
					"alignItems": "center",
					"gap": "8px"
				},
				"tabletStyles": {},
				"mobileStyles": {
					"display": "none"
				},
				"rawStyles": {},
				"children": menu_blocks
			},
			# Actions container (search, cart, wishlist, user menu)
			{
				"blockId": generate_block_id(),
				"element": "div",
				"blockName": "navbar-actions",
				"innerHTML": "",
				"attributes": {},
				"customAttributes": {},
				"classes": ["navbar-actions"],
				"dataKey": None,
				"baseStyles": {
					"display": "flex",
					"flexDirection": "row",
					"alignItems": "center",
					"gap": "16px"
				},
				"tabletStyles": {
					"gap": "12px"
				},
				"mobileStyles": {
					"gap": "8px"
				},
				"rawStyles": {},
				"children": action_blocks + [mobile_menu_block]
			}
		]
	}


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

def get_ai_settings():
	"""Get AI settings from Builder AI Settings doctype with caching."""
	try:
		return frappe.get_cached_doc("Builder AI Settings")
	except frappe.DoesNotExistError:
		# Return default settings if doctype doesn't exist yet
		return frappe._dict({
			"enabled": True,
			"ai_provider": "ollama",
			"ollama_base_url": "http://localhost:11434",
			"ollama_model": "llama3.1",
			"ollama_timeout": 120,
			"openai_api_key": None,
			"openai_model": "gpt-4o-mini",
			"openai_timeout": 60,
			"default_temperature": 0.7,
			"max_conversation_messages": 20,
			"auto_generate_preview": True,
			"allow_website_manager": True,
			"rate_limit_per_hour": 0,
			"custom_system_prompt": "",
			"debug_mode": False,
			"use_llm_generation": False  # Creative LLM generation disabled by default
		})


def get_llm_config() -> dict:
	"""Get LLM configuration from Builder AI Settings doctype."""
	settings = get_ai_settings()

	# Map creativity level to temperature adjustments
	creativity_temps = {
		"conservative": 0.5,
		"balanced": 0.7,
		"creative": 0.9,
		"experimental": 1.1
	}
	creativity_level = getattr(settings, 'creativity_level', 'balanced')
	base_temp = settings.default_temperature if settings.default_temperature else creativity_temps.get(creativity_level, 0.7)

	# Get Ollama API key for Cloudflare WAF authentication
	ollama_api_key = None
	try:
		ollama_api_key = settings.get_password("ollama_api_key")
	except Exception:
		pass

	config = {
		"enabled": settings.enabled,
		"provider": settings.ai_provider,
		"ollama_base_url": settings.ollama_base_url or "http://localhost:11434",
		"ollama_api_key": ollama_api_key,
		"ollama_model": settings.ollama_model or "llama3.1",
		"ollama_vision_model": getattr(settings, 'ollama_vision_model', None) or "llava",
		"ollama_timeout": settings.ollama_timeout or 120,
		"openai_model": settings.openai_model or "gpt-4o-mini",
		"openai_vision_model": getattr(settings, 'openai_vision_model', None) or "gpt-4o",
		"openai_timeout": settings.openai_timeout or 60,
		"temperature": base_temp,
		"max_messages": settings.max_conversation_messages or 20,
		"custom_prompt": settings.custom_system_prompt or "",
		"debug_mode": settings.debug_mode,
		# Vision settings
		"enable_vision": getattr(settings, 'enable_vision', False),
		# Design settings
		"creativity_level": creativity_level,
		"default_style": getattr(settings, 'default_style', 'modern'),
		"use_modern_design": getattr(settings, 'use_modern_design', True),
		"default_site_type": getattr(settings, 'default_site_type', 'auto'),
		"allow_multipage": getattr(settings, 'allow_multipage', True),
		"design_guidelines": getattr(settings, 'design_guidelines', '') or "",
	}

	# Get OpenAI API key securely
	if settings.ai_provider == "openai":
		try:
			config["openai_api_key"] = settings.get_password("openai_api_key")
		except Exception:
			config["openai_api_key"] = None

	return config


def check_ai_enabled():
	"""Check if AI Builder is enabled and user has permission."""
	settings = get_ai_settings()

	if not settings.enabled:
		frappe.throw("AI Builder is disabled. Please enable it in Builder AI Settings.")

	# Check permissions
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to use AI Builder.")

	# Check role-based access
	if not settings.allow_website_manager:
		if "Website Manager" in frappe.get_roles() and "System Manager" not in frappe.get_roles():
			frappe.throw("AI Builder is not available for Website Manager role.")


# =============================================================================
# LLM API FUNCTIONS
# =============================================================================

def call_llm(messages: list[dict], model: str = None, temperature: float = None) -> str:
	"""Make a call to the LLM API (Ollama or OpenAI)."""
	config = get_llm_config()
	provider = config["provider"]

	# Use configured temperature if not specified
	if temperature is None:
		temperature = config.get("temperature", 0.7)

	# Add custom system prompt if configured
	if config.get("custom_prompt"):
		messages = add_custom_prompt(messages, config["custom_prompt"])

	# Debug logging
	if config.get("debug_mode"):
		frappe.log_error(
			message=f"LLM Request:\nProvider: {provider}\nModel: {model}\nMessages: {json.dumps(messages, indent=2)}",
			title="AI Builder Debug - Request"
		)

	if provider == "ollama":
		result = call_ollama(messages, model or config["ollama_model"], temperature, config)
	else:
		result = call_openai(messages, model or config["openai_model"], temperature, config)

	# Debug logging
	if config.get("debug_mode"):
		frappe.log_error(
			message=f"LLM Response:\n{result[:1000]}...",
			title="AI Builder Debug - Response"
		)

	return result


def add_custom_prompt(messages: list[dict], custom_prompt: str) -> list[dict]:
	"""Add custom prompt to system message."""
	enhanced_messages = []
	for msg in messages:
		if msg["role"] == "system":
			enhanced_messages.append({
				"role": "system",
				"content": msg["content"] + f"\n\nAdditional Instructions:\n{custom_prompt}"
			})
		else:
			enhanced_messages.append(msg)
	return enhanced_messages


def clean_json_comments(json_str: str) -> str:
	"""
	Remove JavaScript-style comments from JSON string.

	LLMs sometimes generate JSON with comments like:
	{
		"color": "#8B4513",  // Brown
		"name": "test"
	}

	This function removes those comments to allow proper JSON parsing.
	"""
	import re
	# Remove single-line comments (// ...)
	json_str = re.sub(r'//[^\n]*', '', json_str)
	# Remove trailing commas before closing brackets (common LLM error)
	json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
	return json_str


def call_ollama(messages: list[dict], model: str, temperature: float, config: dict) -> str:
	"""
	Make a call to Ollama API.

	Supports two modes:
	1. Local Ollama: Uses native /api/chat endpoint
	2. Remote Ollama with Cloudflare WAF: Uses OpenAI-compatible /v1/chat/completions endpoint
	   with X-API-Key header for authentication

	The mode is auto-detected based on:
	- If ollama_api_key is set, use OpenAI-compatible mode
	- If base_url contains /v1, use OpenAI-compatible mode
	"""
	import requests

	base_url = config["ollama_base_url"].rstrip("/")
	api_key = config.get("ollama_api_key")
	timeout = config.get("ollama_timeout", 120)

	# Detect if we should use OpenAI-compatible mode (for Cloudflare WAF proxy)
	use_openai_compat = bool(api_key) or "/v1" in base_url

	# Build headers
	headers = {
		"Content-Type": "application/json",
		# User-Agent to avoid Cloudflare bot detection
		"User-Agent": "Mozilla/5.0 (compatible; BuilderAI/1.0; +https://frappe.io)"
	}
	if api_key:
		headers["X-API-Key"] = api_key

	# Add JSON instruction to the system prompt
	enhanced_messages = []
	for msg in messages:
		if msg["role"] == "system":
			enhanced_messages.append({
				"role": "system",
				"content": msg["content"] + "\n\nIMPORTANT: You MUST respond with valid JSON only. No markdown, no explanations, just the JSON object."
			})
		else:
			enhanced_messages.append(msg)

	if use_openai_compat:
		# OpenAI-compatible mode (for Cloudflare WAF protected Ollama)
		# Ensure URL ends with /v1 for OpenAI compatibility
		if not base_url.endswith("/v1"):
			base_url = f"{base_url}/v1"
		url = f"{base_url}/chat/completions"

		payload = {
			"model": model,
			"messages": enhanced_messages,
			"temperature": temperature,
			"response_format": {"type": "json_object"}
		}
	else:
		# Native Ollama mode (local)
		url = f"{base_url}/api/chat"

		payload = {
			"model": model,
			"messages": enhanced_messages,
			"stream": False,
			"options": {
				"temperature": temperature
			},
			"format": "json"
		}

	try:
		response = requests.post(
			url,
			headers=headers,
			json=payload,
			timeout=timeout
		)
		response.raise_for_status()
		result = response.json()

		# Extract content based on response format
		if use_openai_compat:
			# OpenAI format: response.choices[0].message.content
			message = result.get("choices", [{}])[0].get("message", {})
			content = message.get("content", "")

			# Fallback for "reasoning" models (kimi-k2.5, glm-4.7-flash, etc.)
			# These models return content in "reasoning" field instead of "content"
			if not content and message.get("reasoning"):
				content = message.get("reasoning", "")
				# Log this for debugging
				frappe.log_error(
					"LLM reasoning fallback used",
					f"Model: {model}\nReasoning content length: {len(content)}"
				)
		else:
			# Ollama format: response.message.content
			content = result.get("message", {}).get("content", "")

		# Try to extract JSON if wrapped in markdown code blocks
		if "```json" in content:
			content = content.split("```json")[1].split("```")[0].strip()
		elif "```" in content:
			content = content.split("```")[1].split("```")[0].strip()

		# Clean JSON comments (LLMs sometimes add // comments)
		content = clean_json_comments(content)

		# Log debug info if content is empty (helps diagnose reasoning model issues)
		if not content:
			frappe.log_error(
				"LLM returned empty content",
				f"Model: {model}\nURL: {url}\nRaw response keys: {list(result.keys())}\n"
				f"Message keys: {list(result.get('choices', [{}])[0].get('message', {}).keys()) if use_openai_compat else list(result.get('message', {}).keys())}"
			)

		return content

	except requests.exceptions.ConnectionError:
		frappe.throw(
			f"Cannot connect to Ollama at {base_url}. "
			"Please ensure Ollama is running and the URL is correct."
		)
	except requests.exceptions.Timeout:
		frappe.throw("Ollama request timed out. The model might be loading or the request is too complex.")
	except requests.exceptions.HTTPError as e:
		# Better error message for Cloudflare WAF blocks
		if e.response.status_code == 403:
			frappe.throw(
				f"Access denied (403). If using Cloudflare WAF, check that the API Key is correct."
			)
		elif e.response.status_code == 401:
			frappe.throw(
				f"Authentication failed (401). Check the API Key in Builder AI Settings."
			)
		frappe.throw(f"Ollama API error: {str(e)}")
	except Exception as e:
		frappe.throw(f"Ollama API error: {str(e)}")


def call_openai(messages: list[dict], model: str, temperature: float, config: dict) -> str:
	"""Make a call to OpenAI API."""
	api_key = config.get("openai_api_key")
	if not api_key:
		frappe.throw("OpenAI API Key not set. Please configure it in Builder AI Settings.")

	timeout = config.get("openai_timeout", 60)

	response = make_post_request(
		"https://api.openai.com/v1/chat/completions",
		headers={
			"Content-Type": "application/json",
			"Authorization": f"Bearer {api_key}"
		},
		data=json.dumps({
			"model": model,
			"messages": messages,
			"temperature": temperature,
			"response_format": {"type": "json_object"}
		}),
		timeout=timeout
	)

	return response["choices"][0]["message"]["content"]


# =============================================================================
# VISION SUPPORT FUNCTIONS
# =============================================================================

def analyze_image_with_vision(image_data: str, prompt: str, config: dict = None) -> dict:
	"""
	Analyze an image using vision-capable LLM.

	Args:
		image_data: Base64-encoded image data or URL
		prompt: Analysis prompt
		config: LLM config (optional, will be fetched if not provided)

	Returns:
		Analysis results as dict
	"""
	if config is None:
		config = get_llm_config()

	if not config.get("enable_vision"):
		frappe.throw("Vision is not enabled. Please enable it in Builder AI Settings.")

	provider = config["provider"]

	if provider == "ollama":
		return analyze_image_ollama(image_data, prompt, config)
	else:
		return analyze_image_openai(image_data, prompt, config)


def analyze_image_ollama(image_data: str, prompt: str, config: dict) -> dict:
	"""
	Analyze image using Ollama vision model (llava, etc.).

	Supports both local Ollama and Cloudflare WAF protected Ollama servers.
	"""
	import requests
	import base64

	base_url = config["ollama_base_url"].rstrip("/")
	api_key = config.get("ollama_api_key")
	vision_model = config.get("ollama_vision_model", "llava")
	timeout = config.get("ollama_timeout", 120)

	# Build headers (same as call_ollama for consistency)
	headers = {
		"Content-Type": "application/json",
		"User-Agent": "Mozilla/5.0 (compatible; BuilderAI/1.0; +https://frappe.io)"
	}
	if api_key:
		headers["X-API-Key"] = api_key

	# Prepare image data
	# If it's a URL, download and convert to base64
	if image_data.startswith("http"):
		try:
			download_headers = {"User-Agent": headers["User-Agent"]}
			if api_key:
				download_headers["X-API-Key"] = api_key
			response = requests.get(image_data, headers=download_headers, timeout=30)
			response.raise_for_status()
			image_data = base64.b64encode(response.content).decode("utf-8")
		except Exception as e:
			frappe.throw(f"Failed to download image: {str(e)}")

	# Remove data URI prefix if present
	if "base64," in image_data:
		image_data = image_data.split("base64,")[1]

	vision_prompt = f"""{prompt}

Analyze this image and return a JSON object with:
{{
  "description": "Brief description of what you see",
  "colors": ["list of dominant colors as hex codes"],
  "mood": "the mood/feeling the image conveys",
  "style_suggestions": ["design style suggestions based on the image"],
  "design_insights": {{
    "recommended_palette": ["primary", "secondary", "accent colors"],
    "typography_style": "suggested font style",
    "layout_suggestions": "layout recommendations"
  }}
}}

IMPORTANT: Return only valid JSON, no other text."""

	# Native Ollama API for vision (images are handled differently)
	payload = {
		"model": vision_model,
		"messages": [
			{
				"role": "user",
				"content": vision_prompt,
				"images": [image_data]
			}
		],
		"stream": False,
		"format": "json"
	}

	try:
		response = requests.post(
			f"{base_url}/api/chat",
			headers=headers,
			json=payload,
			timeout=timeout
		)
		response.raise_for_status()
		result = response.json()

		content = result.get("message", {}).get("content", "{}")

		# Try to parse JSON
		try:
			return json.loads(content)
		except json.JSONDecodeError:
			# Try to extract JSON from content
			if "{" in content and "}" in content:
				start = content.find("{")
				end = content.rfind("}") + 1
				return json.loads(content[start:end])
			return {"description": content, "colors": [], "mood": "unknown", "style_suggestions": []}

	except requests.exceptions.ConnectionError:
		frappe.throw(f"Cannot connect to Ollama at {base_url}. Please ensure Ollama is running.")
	except requests.exceptions.HTTPError as e:
		if e.response.status_code == 403:
			frappe.throw("Access denied (403). Check the API Key for Cloudflare WAF.")
		frappe.throw(f"Vision analysis failed: {str(e)}")
	except Exception as e:
		frappe.throw(f"Vision analysis failed: {str(e)}")


def analyze_image_openai(image_data: str, prompt: str, config: dict) -> dict:
	"""Analyze image using OpenAI vision model (gpt-4o, etc.)."""
	api_key = config.get("openai_api_key")
	if not api_key:
		frappe.throw("OpenAI API Key not set. Please configure it in Builder AI Settings.")

	vision_model = config.get("openai_vision_model", "gpt-4o")

	# Prepare image URL or base64
	if image_data.startswith("http"):
		image_content = {"type": "image_url", "image_url": {"url": image_data}}
	else:
		# Assume base64, add data URI if needed
		if not image_data.startswith("data:"):
			image_data = f"data:image/jpeg;base64,{image_data}"
		image_content = {"type": "image_url", "image_url": {"url": image_data}}

	vision_prompt = f"""{prompt}

Analyze this image and return a JSON object with:
{{
  "description": "Brief description of what you see",
  "colors": ["list of dominant colors as hex codes"],
  "mood": "the mood/feeling the image conveys",
  "style_suggestions": ["design style suggestions based on the image"],
  "design_insights": {{
    "recommended_palette": ["primary", "secondary", "accent colors"],
    "typography_style": "suggested font style",
    "layout_suggestions": "layout recommendations"
  }}
}}"""

	messages = [
		{
			"role": "user",
			"content": [
				{"type": "text", "text": vision_prompt},
				image_content
			]
		}
	]

	timeout = config.get("openai_timeout", 60)

	response = make_post_request(
		"https://api.openai.com/v1/chat/completions",
		headers={
			"Content-Type": "application/json",
			"Authorization": f"Bearer {api_key}"
		},
		data=json.dumps({
			"model": vision_model,
			"messages": messages,
			"response_format": {"type": "json_object"},
			"max_tokens": 1000
		}),
		timeout=timeout
	)

	content = response["choices"][0]["message"]["content"]
	return json.loads(content)


@frappe.whitelist()
def analyze_logo(image_data: str) -> dict:
	"""
	Analyze a logo image and extract design insights for website generation.

	Args:
		image_data: Base64-encoded logo image or URL

	Returns:
		Design insights from the logo
	"""
	check_ai_enabled()

	config = get_llm_config()
	if not config.get("enable_vision"):
		frappe.throw("Vision is not enabled. Please enable it in Builder AI Settings.")

	prompt = """This is a company logo. Analyze it to extract:
1. The dominant colors and their hex codes
2. The style/mood (modern, classic, playful, professional, etc.)
3. Design recommendations for a website that would complement this logo"""

	result = analyze_image_with_vision(image_data, prompt, config)

	return {
		"success": True,
		"analysis": result
	}


@frappe.whitelist()
def analyze_reference_image(image_data: str, context: str = "") -> dict:
	"""
	Analyze a reference/inspiration image for website design.

	Args:
		image_data: Base64-encoded image or URL
		context: Additional context about what the user wants

	Returns:
		Design insights from the reference
	"""
	check_ai_enabled()

	config = get_llm_config()
	if not config.get("enable_vision"):
		frappe.throw("Vision is not enabled. Please enable it in Builder AI Settings.")

	prompt = f"""This is a design reference/inspiration image for a website.
{f'Context: {context}' if context else ''}

Analyze this image to extract:
1. Layout structure and arrangement
2. Color palette used
3. Typography style
4. Visual effects and design patterns
5. Overall mood and aesthetic
6. Specific elements that could be replicated"""

	result = analyze_image_with_vision(image_data, prompt, config)

	return {
		"success": True,
		"analysis": result
	}


@frappe.whitelist()
def get_ai_config() -> dict:
	"""Get current AI configuration (for frontend display)."""
	config = get_llm_config()
	settings = get_ai_settings()

	return {
		"enabled": config.get("enabled", True),
		"provider": config["provider"],
		"ollama_base_url": config.get("ollama_base_url") if config["provider"] == "ollama" else None,
		"ollama_model": config.get("ollama_model") if config["provider"] == "ollama" else None,
		"ollama_api_key_configured": bool(config.get("ollama_api_key")) if config["provider"] == "ollama" else None,
		"openai_model": config.get("openai_model") if config["provider"] == "openai" else None,
		"openai_configured": bool(config.get("openai_api_key")) if config["provider"] == "openai" else None,
		"auto_generate_preview": settings.auto_generate_preview if hasattr(settings, 'auto_generate_preview') else True,
		# Vision settings
		"enable_vision": config.get("enable_vision", False),
		"vision_model": config.get("ollama_vision_model") if config["provider"] == "ollama" else config.get("openai_vision_model"),
		# Design settings
		"creativity_level": config.get("creativity_level", "balanced"),
		"default_style": config.get("default_style", "modern"),
		"use_modern_design": config.get("use_modern_design", True),
		"allow_multipage": config.get("allow_multipage", True),
	}


@frappe.whitelist()
def test_llm_connection() -> dict:
	"""Test the LLM connection."""
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to test AI connection.")

	config = get_llm_config()

	try:
		response = call_llm([
			{"role": "system", "content": "You are a helpful assistant. Respond with JSON only."},
			{"role": "user", "content": "Say hello in JSON format with a 'message' key."}
		])
		json.loads(response)  # Validate JSON

		# Build result with auth info
		result = {
			"success": True,
			"provider": config["provider"],
			"model": config.get("ollama_model") if config["provider"] == "ollama" else config.get("openai_model"),
			"message": "Connection successful!"
		}

		# Add auth info for Ollama
		if config["provider"] == "ollama":
			if config.get("ollama_api_key"):
				result["auth"] = "X-API-Key (Cloudflare WAF)"
			else:
				result["auth"] = "None (local)"

		return result

	except Exception as e:
		return {
			"success": False,
			"provider": config["provider"],
			"error": str(e)
		}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@frappe.whitelist()
def start_conversation(title: str = "New Website") -> dict:
	"""Start a new AI conversation for website generation."""
	check_ai_enabled()

	conversation = frappe.get_doc({
		"doctype": "Builder AI Conversation",
		"title": title,
		"status": "collecting",
		"messages": "[]",
		"site_context": "{}",
		"generated_blocks": "[]"
	})
	conversation.insert()

	# Get settings and generate dynamic prompt
	settings = get_ai_settings()
	system_prompt = get_collector_prompt(settings)

	# Get initial greeting from LLM
	initial_message = {
		"role": "system",
		"content": system_prompt
	}

	response = call_llm([initial_message])
	response_data = json.loads(response)

	# Store the assistant's greeting
	messages = [{
		"role": "assistant",
		"content": response_data.get("message", "Hello! I'm here to help you create your website. What kind of website would you like to build?")
	}]

	conversation.messages = json.dumps(messages)
	conversation.site_context = json.dumps(response_data.get("site_context", {}))
	conversation.save()

	return {
		"conversation_id": conversation.name,
		"message": response_data.get("message"),
		"site_context": response_data.get("site_context", {}),
		"collection_complete": False
	}


@frappe.whitelist()
def send_message(conversation_id: str, message: str) -> dict:
	"""Send a message to the AI conversation and get a response."""
	check_ai_enabled()

	config = get_llm_config()
	settings = get_ai_settings()
	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)

	# Get existing messages and context
	messages = json.loads(conversation.messages or "[]")
	site_context = json.loads(conversation.site_context or "{}")

	# Add user message
	messages.append({
		"role": "user",
		"content": message
	})

	# Generate dynamic prompt with settings
	system_prompt = get_collector_prompt(settings)

	# Build LLM messages with system prompt and context
	llm_messages = [
		{
			"role": "system",
			"content": system_prompt + f"\n\nCurrent site context collected so far:\n{json.dumps(site_context, indent=2)}"
		}
	]

	# Add conversation history (use configured max messages)
	max_messages = config.get("max_messages", 20)
	for msg in messages[-max_messages:]:
		llm_messages.append({
			"role": msg["role"],
			"content": msg["content"] if msg["role"] == "user" else json.dumps({"message": msg["content"]})
		})

	# Get LLM response
	response = call_llm(llm_messages)
	response_data = json.loads(response)

	# Add assistant response to messages
	assistant_message = response_data.get("message", "")
	messages.append({
		"role": "assistant",
		"content": assistant_message
	})

	# Update conversation
	conversation.messages = json.dumps(messages)
	conversation.site_context = json.dumps(response_data.get("site_context", {}))

	if response_data.get("collection_complete"):
		conversation.status = "generating"

	conversation.save()

	return {
		"conversation_id": conversation_id,
		"message": assistant_message,
		"site_context": response_data.get("site_context", {}),
		"collection_complete": response_data.get("collection_complete", False),
		"next_topic": response_data.get("next_question_topic")
	}


@frappe.whitelist()
def send_message_with_image(conversation_id: str, message: str, image_data: str, image_type: str = "reference") -> dict:
	"""
	Send a message with an image attachment to the AI conversation.

	Args:
		conversation_id: Conversation ID
		message: User message
		image_data: Base64-encoded image or URL
		image_type: Type of image - 'logo', 'reference', or 'content'

	Returns:
		AI response with design insights from the image
	"""
	check_ai_enabled()

	config = get_llm_config()
	settings = get_ai_settings()

	if not config.get("enable_vision"):
		frappe.throw("Vision is not enabled. Please enable it in Builder AI Settings.")

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)

	# Get existing messages and context
	messages = json.loads(conversation.messages or "[]")
	site_context = json.loads(conversation.site_context or "{}")

	# Analyze the image first
	image_prompt = {
		"logo": "This is the company logo. Extract colors, style, and branding insights.",
		"reference": "This is a design reference. Extract layout, colors, and design patterns the user likes.",
		"content": "This is content for the website. Describe what you see for use in the design."
	}.get(image_type, "Analyze this image for website design insights.")

	try:
		image_analysis = analyze_image_with_vision(image_data, image_prompt, config)
	except Exception as e:
		image_analysis = {"error": str(e), "description": "Could not analyze image"}

	# Add user message with image context
	user_message_content = f"{message}\n\n[User attached a {image_type} image]"
	messages.append({
		"role": "user",
		"content": user_message_content,
		"has_image": True,
		"image_type": image_type
	})

	# Update site context with image analysis
	if image_type == "logo" and "colors" in image_analysis:
		if "style" not in site_context:
			site_context["style"] = {}
		# Suggest colors from logo
		colors = image_analysis.get("colors", [])
		if colors:
			site_context["style"]["suggested_colors_from_logo"] = colors
			if len(colors) >= 1:
				site_context["style"]["primary_color"] = site_context["style"].get("primary_color") or colors[0]
			if len(colors) >= 2:
				site_context["style"]["secondary_color"] = site_context["style"].get("secondary_color") or colors[1]
		if "mood" in image_analysis:
			site_context["style"]["logo_mood"] = image_analysis["mood"]

	elif image_type == "reference" and "design_insights" in image_analysis:
		if "style" not in site_context:
			site_context["style"] = {}
		site_context["style"]["reference_insights"] = image_analysis.get("design_insights", {})
		if "style_suggestions" in image_analysis:
			site_context["style"]["inspiration_styles"] = image_analysis["style_suggestions"]

	# Generate dynamic prompt
	system_prompt = get_collector_prompt(settings)

	# Build LLM messages including image analysis context
	llm_messages = [
		{
			"role": "system",
			"content": system_prompt + f"""

Current site context collected so far:
{json.dumps(site_context, indent=2)}

Image Analysis Results ({image_type}):
{json.dumps(image_analysis, indent=2)}

IMPORTANT: Incorporate the insights from the image analysis into your response and the site_context.
If it's a logo, use the detected colors as the primary palette suggestion.
If it's a reference, acknowledge the design elements the user likes."""
		}
	]

	# Add conversation history
	max_messages = config.get("max_messages", 20)
	for msg in messages[-max_messages:]:
		content = msg["content"] if msg["role"] == "user" else json.dumps({"message": msg["content"]})
		llm_messages.append({
			"role": msg["role"],
			"content": content
		})

	# Get LLM response
	response = call_llm(llm_messages)
	response_data = json.loads(response)

	# Merge image-based style updates with LLM response
	if "site_context" in response_data:
		# Preserve our image-derived styles
		if "style" in site_context:
			if "style" not in response_data["site_context"]:
				response_data["site_context"]["style"] = {}
			for key in ["suggested_colors_from_logo", "logo_mood", "reference_insights", "inspiration_styles"]:
				if key in site_context.get("style", {}):
					response_data["site_context"]["style"][key] = site_context["style"][key]

	# Add assistant response to messages
	assistant_message = response_data.get("message", "")
	messages.append({
		"role": "assistant",
		"content": assistant_message
	})

	# Update conversation
	conversation.messages = json.dumps(messages)
	conversation.site_context = json.dumps(response_data.get("site_context", site_context))

	if response_data.get("collection_complete"):
		conversation.status = "generating"

	conversation.save()

	return {
		"conversation_id": conversation_id,
		"message": assistant_message,
		"site_context": response_data.get("site_context", site_context),
		"collection_complete": response_data.get("collection_complete", False),
		"image_analysis": image_analysis
	}


# =============================================================================
# NAVBAR/FOOTER BUILDER PAGE GENERATION
# =============================================================================

def generate_navbar_page(context: dict, settings=None) -> str | None:
	"""
	Create or update a Builder Page with route 'navbar' for the webshop template system.

	The webshop templates (navbar.html, footer.html) check for Builder Pages with
	routes 'navbar' and 'footer', and render them if they exist.

	Args:
		context: Site context with functionality_type and style info
		settings: Builder AI Settings (optional)

	Returns:
		Page name if created/updated, None if skipped
	"""
	try:
		# Get navbar template block
		navbar_block = get_navbar_template(context, settings)

		# Check if navbar page already exists
		existing = frappe.db.exists("Builder Page", {"route": "navbar"})

		if existing:
			# Update existing navbar page
			page = frappe.get_doc("Builder Page", existing)
			page.draft_blocks = json.dumps([navbar_block])
			page.blocks = json.dumps([navbar_block])
			page.published = 1
			page.save(ignore_permissions=True)
			frappe.db.commit()
			return page.name
		else:
			# Create new navbar page
			page = frappe.get_doc({
				"doctype": "Builder Page",
				"page_name": "navbar",
				"page_title": "Site Navigation",
				"route": "navbar",
				"published": 1,
				"draft_blocks": json.dumps([navbar_block]),
				"blocks": json.dumps([navbar_block])
			})
			page.insert(ignore_permissions=True)
			frappe.db.commit()
			return page.name

	except Exception as e:
		frappe.log_error("Navbar page generation failed", str(e))
		return None


def generate_footer_page(context: dict) -> str | None:
	"""
	Create or update a Builder Page with route 'footer' for the webshop template system.

	Args:
		context: Site context with functionality_type and style info

	Returns:
		Page name if created/updated, None if skipped
	"""
	try:
		# Get footer template block
		footer_block = get_footer_template(context)

		# Check if footer page already exists
		existing = frappe.db.exists("Builder Page", {"route": "footer"})

		if existing:
			# Update existing footer page
			page = frappe.get_doc("Builder Page", existing)
			page.draft_blocks = json.dumps([footer_block])
			page.blocks = json.dumps([footer_block])
			page.published = 1
			page.save(ignore_permissions=True)
			frappe.db.commit()
			return page.name
		else:
			# Create new footer page
			page = frappe.get_doc({
				"doctype": "Builder Page",
				"page_name": "footer",
				"page_title": "Site Footer",
				"route": "footer",
				"published": 1,
				"draft_blocks": json.dumps([footer_block]),
				"blocks": json.dumps([footer_block])
			})
			page.insert(ignore_permissions=True)
			frappe.db.commit()
			return page.name

	except Exception as e:
		frappe.log_error("Footer page generation failed", str(e))
		return None


def generate_page_with_llm(page_config: dict, site_context: dict) -> list:
	"""
	Generate page blocks using LLM with creative freedom.

	This function uses the PAGE_GENERATOR_PROMPT to let the LLM
	create unique, creative designs instead of using fixed templates.

	Args:
		page_config: Page configuration with name, route, title, sections
		site_context: Full site context for styling and business info

	Returns:
		List of validated and fixed blocks, or None if generation fails
	"""
	title = page_config.get("title", page_config.get("name", _("Page")))
	sections = page_config.get("sections", ["hero"])
	is_main = page_config.get("is_main", False)

	# Extract style info
	style = site_context.get("style", {})
	primary_color = style.get("primary_color", "#171717")
	secondary_color = style.get("secondary_color", "#6B7280")
	background_color = style.get("background_color", "#ffffff")
	text_color = style.get("text_color", "#171717")

	# Build the user prompt with page-specific context
	page_prompt = f"""Create blocks for a webpage with the following specifications:

## Page Information
- Title: {title}
- Is Homepage: {is_main}
- Sections to include: {', '.join(sections) if isinstance(sections[0], str) else ', '.join([s.get('type', 'unknown') for s in sections])}

## Business Context
- Business Name: {site_context.get('business_name', 'Business')}
- Industry: {site_context.get('industry', 'General')}
- Tagline: {site_context.get('tagline', '')}
- Description: {site_context.get('description', '')}
- Unique Value Proposition: {site_context.get('unique_value_proposition', '')}

## Color Palette
- Primary Color: {primary_color}
- Secondary Color: {secondary_color}
- Background Color: {background_color}
- Text Color: {text_color}

## Design Guidelines
- Style Preference: {style.get('style_preference', 'modern')}
- Mood: {style.get('mood', 'professional')}

## Section-Specific Content
"""
	# Add section-specific content if available
	for section in sections:
		if isinstance(section, dict):
			section_type = section.get("type", "")
			page_prompt += f"\n### {section_type.title()} Section\n"
			if section.get("headline"):
				page_prompt += f"- Headline: {section['headline']}\n"
			if section.get("subheadline"):
				page_prompt += f"- Subheadline: {section['subheadline']}\n"
			if section.get("description"):
				page_prompt += f"- Description: {section['description']}\n"
			if section.get("items"):
				page_prompt += f"- Items: {len(section['items'])} items\n"

	page_prompt += """

## Important Reminders
1. Return ONLY a valid JSON array of blocks
2. Every block MUST have ALL required fields (blockId, element, blockName, innerHTML, attributes, customAttributes, classes, dataKey, baseStyles, tabletStyles, mobileStyles, rawStyles, children)
3. blockId must be exactly 9 lowercase alphanumeric characters
4. BE CREATIVE with layouts and styling while respecting the color palette
5. Ensure responsive styles (mobile should look good too)
"""

	# Build LLM messages
	llm_messages = [
		{"role": "system", "content": PAGE_GENERATOR_PROMPT},
		{"role": "user", "content": page_prompt}
	]

	try:
		# Call LLM with higher temperature for creativity
		response = call_llm(llm_messages, temperature=0.7)

		# Clean and parse JSON
		cleaned_response = clean_json_comments(response)

		# Try to extract JSON from markdown code blocks if present
		if "```json" in cleaned_response:
			import re
			json_match = re.search(r'```json\s*([\s\S]*?)\s*```', cleaned_response)
			if json_match:
				cleaned_response = json_match.group(1)
		elif "```" in cleaned_response:
			import re
			json_match = re.search(r'```\s*([\s\S]*?)\s*```', cleaned_response)
			if json_match:
				cleaned_response = json_match.group(1)

		# Clean control characters that can break JSON parsing
		import re

		# Fix LLM output issues: newlines inside JSON strings break parsing
		# Replace newlines that appear inside strings (between quotes) with spaces
		def fix_newlines_in_strings(json_str):
			"""Fix newlines that appear inside JSON string values."""
			result = []
			in_string = False
			escape_next = False
			i = 0
			while i < len(json_str):
				char = json_str[i]
				if escape_next:
					result.append(char)
					escape_next = False
				elif char == '\\':
					result.append(char)
					escape_next = True
				elif char == '"':
					result.append(char)
					in_string = not in_string
				elif char == '\n' and in_string:
					# Replace newline inside string with space
					result.append(' ')
				else:
					result.append(char)
				i += 1
			return ''.join(result)

		cleaned_response = fix_newlines_in_strings(cleaned_response)

		# Remove remaining control characters (except newlines outside strings and tabs)
		cleaned_response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned_response)

		# Parse JSON with error recovery
		def repair_broken_json(json_str):
			"""Repair JSON that has truncated URLs or other issues from LLM output."""
			import re

			# Pattern 1: "url(https:     "key" -> "none", "key"
			# URL was truncated and next key started on same line
			json_str = re.sub(
				r'"url\(https?:[^)"]*\s+"([a-zA-Z])',
				r'"none", "\1',
				json_str
			)

			# Pattern 2: "url(http..." without closing ) and "
			json_str = re.sub(
				r'"url\(https?:[^)]*$',
				'"none"',
				json_str,
				flags=re.MULTILINE
			)

			# Pattern 3: Incomplete URLs "https://     " followed by next key
			json_str = re.sub(
				r'"https?://[^"]*\s{2,}([^"]*)"',
				'""',
				json_str
			)

			# Pattern 4: Fix missing commas between key-value pairs
			# }" -> },"  or ]" -> ],"
			json_str = re.sub(r'(\})\s*"([a-zA-Z])', r'\1, "\2', json_str)
			json_str = re.sub(r'(\])\s*"([a-zA-Z])', r'\1, "\2', json_str)

			return json_str

		try:
			parsed = json.loads(cleaned_response.strip())
		except json.JSONDecodeError as first_error:
			# Try to repair and parse again
			repaired = repair_broken_json(cleaned_response.strip())
			try:
				parsed = json.loads(repaired)
			except json.JSONDecodeError as second_error:
				# If it's a single block object, try wrapping in array
				if repaired.strip().startswith('{') and "blockId" in repaired:
					try:
						test_parsed = json.loads(repaired)
						if isinstance(test_parsed, dict) and "blockId" in test_parsed:
							parsed = [test_parsed]
						else:
							raise second_error
					except json.JSONDecodeError:
						raise second_error
				else:
					raise second_error

		# Handle both array format and object format {"blocks": [...]} or {"sections": [...]}
		if isinstance(parsed, list):
			blocks = parsed
		elif isinstance(parsed, dict):
			# LLM might return {"blocks": [...]}, {"sections": [...]}, or {"children": [...]}
			blocks = parsed.get("blocks") or parsed.get("sections") or parsed.get("children") or []
			if not blocks and len(parsed) == 1:
				# Single key object - try to get the value (whatever key name LLM used)
				first_value = list(parsed.values())[0]
				blocks = first_value if isinstance(first_value, list) else []
		else:
			blocks = []

		# Log if blocks are empty (helps diagnose LLM response issues)
		if not blocks:
			frappe.log_error(
				"LLM returned empty blocks",
				f"Page: {title}\nResponse length: {len(response) if response else 0}\n"
				f"Cleaned response (first 500 chars): {cleaned_response[:500] if cleaned_response else 'None'}"
			)

		# Validate and fix blocks
		validated = validate_and_fix_blocks(blocks)

		if validated["errors"]:
			# Log validation issues for debugging
			frappe.log_error(
				"LLM block validation",
				f"Page: {title}\nIssues: {json.dumps(validated['errors'][:20], indent=2)}"
			)

		# Fix fake image URLs with real Unsplash images based on industry
		industry = site_context.get("industry", "")
		fixed_blocks = fix_fake_image_urls_in_blocks(validated["fixed_blocks"], industry)

		return fixed_blocks

	except json.JSONDecodeError as e:
		frappe.log_error("LLM JSON parse error", f"Page: {title}\nError: {str(e)}\nResponse: {response[:500] if response else 'No response'}")
		return None
	except Exception as e:
		frappe.log_error("LLM generation error", f"Page: {title}\nError: {str(e)}")
		return None


def generate_single_page(page_config: dict, site_context: dict, use_llm: bool = None) -> str:
	"""
	Generate a single Builder page from page configuration.

	Supports two generation modes:
	1. Template-based (default): Uses pre-built Python templates for consistent results
	2. LLM-based (creative): Uses AI to generate unique, creative designs

	The mode is controlled by the 'use_llm' parameter or the 'use_llm_generation'
	setting in Builder AI Settings.

	Args:
		page_config: Page configuration with name, route, title, sections
		site_context: Full site context for styling and business info
		use_llm: Override for LLM generation mode (None = use settings)

	Returns:
		The created page name
	"""
	# Extract page configuration
	page_name = page_config.get("name", "page")
	page_name = frappe.scrub(page_name).replace("_", "-")
	route = page_config.get("route", f"/{page_name}")
	title = page_config.get("title", page_config.get("name", _("Page")))
	sections = page_config.get("sections", ["hero"])
	is_main = page_config.get("is_main", False)

	# For the main page, use business name as route or leave empty for root
	if is_main:
		business_name = site_context.get("business_name", "")
		if business_name:
			page_name = frappe.scrub(business_name).replace("_", "-")
			route = page_name  # Main page gets business name as route
		else:
			route = page_name

	# Normalize route - remove leading slash for Builder Page route field
	route = route.lstrip("/") if route != "/" else page_name

	# Determine if we should use LLM generation
	if use_llm is None:
		settings = get_ai_settings()
		use_llm = getattr(settings, 'use_llm_generation', False)

	blocks = None

	# Try LLM generation if enabled
	if use_llm:
		try:
			# Use multi-pass approach for better reliability (if Pydantic available)
			if PYDANTIC_AVAILABLE:
				blocks = generate_page_multipass(page_config, site_context)
			else:
				blocks = generate_page_with_llm(page_config, site_context)
			if blocks:
				# LLM generation successful
				pass
		except Exception as e:
			frappe.log_error("LLM generation exception", f"Page: {title}\nError: {str(e)}")
			blocks = None

	# Fallback to template-based generation if LLM fails or is disabled
	if not blocks:
		# Build enriched context with section data from page_config
		enriched_context = site_context.copy()

		# Add current page info to context (useful for page_header template)
		enriched_context["current_page_title"] = title
		enriched_context["current_page_name"] = page_name
		enriched_context["current_page_is_main"] = is_main

		# If page_config has section-specific data, add it to context
		for section in page_config.get("sections_data", []):
			section_type = section.get("type", "")
			if section_type:
				enriched_context[f"section_{section_type}"] = section

		# Section generators for content
		section_generators = {
			"hero": get_hero_template,
			"page_header": get_page_header_template,  # Simple header for secondary pages
			"features": get_features_template,
			"about": get_about_template,
			"contact": get_contact_template,
			"cta": get_cta_template,
			"team": get_team_template,
			"testimonials": get_testimonials_template,
			"pricing": get_pricing_template,
			"gallery": get_gallery_template,
			"faq": get_faq_template,
			"stats": get_stats_template,
			"process": get_process_template,
			"product_carousel": get_product_carousel_template,
		}

		# Generate blocks for this page's sections
		blocks = []
		for section_type in sections:
			if isinstance(section_type, str) and section_type in section_generators:
				block = section_generators[section_type](enriched_context)
				blocks.append(block)
			elif isinstance(section_type, dict):
				# Section with type and additional data
				s_type = section_type.get("type", "")
				if s_type in section_generators:
					# Temporarily add section data to context
					enriched_context[f"section_{s_type}"] = section_type
					block = section_generators[s_type](enriched_context)
					blocks.append(block)

	# Ensure unique page name
	base_name = page_name
	counter = 1
	while frappe.db.exists("Builder Page", page_name):
		page_name = f"{base_name}-{counter}"
		counter += 1

	# Create the page
	page = frappe.get_doc({
		"doctype": "Builder Page",
		"page_name": page_name,
		"page_title": title,
		"route": route,
		"published": 1,
		"draft_blocks": json.dumps(blocks),
		"blocks": json.dumps(blocks)
	})
	page.insert(ignore_permissions=True)

	return page.name


@frappe.whitelist()
def generate_site(conversation_id: str) -> dict:
	"""
	Generate a complete multi-page site from the conversation context.

	This is the main entry point for site generation. It:
	1. Generates shared navbar and footer pages (once)
	2. Generates all content pages defined in context.pages[]
	3. Updates the conversation status

	Args:
		conversation_id: The Builder AI Conversation ID

	Returns:
		Dict with success status and generated pages info
	"""
	check_ai_enabled()

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)
	site_context = json.loads(conversation.site_context or "{}")

	if not site_context:
		frappe.throw(_("No site context found. Please complete the conversation first."))

	# Get AI settings for shortcodes
	settings = get_ai_settings()

	# Generate shared navbar and footer pages (once for all pages)
	navbar_page = generate_navbar_page(site_context, settings)
	footer_page = generate_footer_page(site_context)

	# Get pages from context
	pages = site_context.get("pages", [])

	# If no pages defined, create a default single page structure
	if not pages:
		# Fallback to old behavior - create single page from sections
		pages = [{
			"name": site_context.get("business_name", "home"),
			"route": "/",
			"is_main": True,
			"title": site_context.get("business_name", _("Home")),
			"sections": [s.get("type") for s in site_context.get("sections", [{"type": "hero"}, {"type": "features"}, {"type": "cta"}])]
		}]

	# Generate each page
	generated_pages = []
	main_page_name = None

	for page_config in pages:
		try:
			page_name = generate_single_page(page_config, site_context)
			generated_pages.append({
				"name": page_name,
				"route": page_config.get("route", "/"),
				"title": page_config.get("title", page_config.get("name")),
				"is_main": page_config.get("is_main", False)
			})

			if page_config.get("is_main", False):
				main_page_name = page_name

		except Exception as e:
			frappe.log_error("Page generation failed", f"Page: {page_config.get('name')}, Error: {str(e)}")

	# If no main page was designated, use the first one
	if not main_page_name and generated_pages:
		main_page_name = generated_pages[0]["name"]

	# Update conversation
	conversation.status = "completed"
	conversation.page = main_page_name  # Store main page reference
	conversation.generated_blocks = json.dumps([])  # Blocks are now per-page
	conversation.save()

	frappe.db.commit()

	return {
		"success": True,
		"pages": generated_pages,
		"main_page": main_page_name,
		"navbar_page": navbar_page,
		"footer_page": footer_page,
		"total_pages": len(generated_pages)
	}


@frappe.whitelist()
def generate_page(conversation_id: str, page_name: str = None) -> dict:
	"""Generate a Builder page from the collected context.

	DEPRECATED: Use generate_site() for multi-page generation.
	This function is kept for backward compatibility and generates only
	the main page.

	Also generates shared navbar and footer Builder Pages that are automatically
	included by the webpage.html template on all Builder Pages.
	"""
	check_ai_enabled()

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)
	site_context = json.loads(conversation.site_context or "{}")

	if not site_context:
		frappe.throw(_("No site context found. Please complete the conversation first."))

	# Get AI settings for shortcodes
	settings = get_ai_settings()

	# Generate shared navbar and footer pages (if they don't exist or update them)
	# These are automatically included by the webpage.html template
	navbar_page = generate_navbar_page(site_context, settings)
	footer_page = generate_footer_page(site_context)

	# Generate content blocks (without navbar/footer - they come from shared pages)
	blocks = generate_blocks_from_context(site_context)

	# Create the main content page
	if not page_name:
		page_name = site_context.get("business_name", "ai-generated-page")
		page_name = frappe.scrub(page_name).replace("_", "-")

	# Ensure unique page name
	base_name = page_name
	counter = 1
	while frappe.db.exists("Builder Page", page_name):
		page_name = f"{base_name}-{counter}"
		counter += 1

	page = frappe.get_doc({
		"doctype": "Builder Page",
		"page_name": page_name,
		"page_title": site_context.get("business_name", _("Generated Page")),
		"route": page_name,
		"draft_blocks": json.dumps(blocks),
		"blocks": json.dumps(blocks)
	})
	page.insert()

	# Update conversation
	conversation.status = "completed"
	conversation.page = page.name
	conversation.generated_blocks = json.dumps(blocks)
	conversation.save()

	return {
		"success": True,
		"page_name": page.name,
		"page_route": page.route,
		"blocks": blocks,
		"navbar_page": navbar_page,
		"footer_page": footer_page
	}


def generate_blocks_from_context(context: dict) -> list:
	"""
	Generate Frappe Builder blocks from site context.

	Note: Navbar and footer are now automatically included by the webpage.html template
	from Builder Pages with routes 'navbar' and 'footer'. This function only generates
	the main content blocks.
	"""
	blocks = []

	# Extract sections from pages structure (LLM returns pages[0].sections)
	sections = context.get("sections", [])
	if not sections:
		pages = context.get("pages", [])
		if pages and isinstance(pages, list) and len(pages) > 0:
			main_page = pages[0]
			sections = main_page.get("sections", [])

	# Flatten section data into context for templates
	# This makes section-specific data available to templates
	enriched_context = context.copy()
	for section in sections:
		section_type = section.get("type", "")
		if section_type:
			enriched_context[f"section_{section_type}"] = section

	# If no sections defined, create default sections
	if not sections:
		sections = [
			{"type": "hero"},
			{"type": "features"},
			{"type": "cta"}
		]

	# Section generators for main content
	section_generators = {
		"hero": get_hero_template,
		"features": get_features_template,
		"about": get_about_template,
		"contact": get_contact_template,
		"cta": get_cta_template,
		"team": get_team_template,
		"testimonials": get_testimonials_template,
		"pricing": get_pricing_template,
		"gallery": get_gallery_template,
		"faq": get_faq_template,
		"stats": get_stats_template,
		"process": get_process_template,
		"product_carousel": get_product_carousel_template,
	}

	for section in sections:
		section_type = section.get("type", "")
		if section_type in section_generators:
			block = section_generators[section_type](enriched_context)
			blocks.append(block)

	return blocks


@frappe.whitelist()
def generate_blocks_with_llm(conversation_id: str) -> dict:
	"""Generate blocks using LLM for more creative/custom layouts."""
	check_ai_enabled()

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)
	site_context = json.loads(conversation.site_context or "{}")

	if not site_context:
		frappe.throw("No site context found. Please complete the conversation first.")

	# Use LLM to generate blocks
	llm_messages = [
		{
			"role": "system",
			"content": GENERATOR_SYSTEM_PROMPT
		},
		{
			"role": "user",
			"content": f"""Generate Frappe Builder blocks for this website:

Site Context:
{json.dumps(site_context, indent=2)}

Generate a complete page with all sections. Return ONLY a JSON array of blocks."""
		}
	]

	# Use default model from config (works for both Ollama and OpenAI)
	response = call_llm(llm_messages, temperature=0.5)

	try:
		response_data = json.loads(response)
		# Handle both direct array and object with blocks key
		if isinstance(response_data, list):
			blocks = response_data
		else:
			blocks = response_data.get("blocks", [])
	except json.JSONDecodeError:
		frappe.throw("Failed to parse LLM response. Please try again.")

	return {
		"blocks": blocks,
		"site_context": site_context
	}


@frappe.whitelist()
def get_conversation(conversation_id: str) -> dict:
	"""Get conversation details."""
	if not frappe.has_permission("Builder Page", ptype="read"):
		frappe.throw("You do not have permission to view this conversation.")

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)

	return {
		"conversation_id": conversation.name,
		"title": conversation.title,
		"status": conversation.status,
		"messages": json.loads(conversation.messages or "[]"),
		"site_context": json.loads(conversation.site_context or "{}"),
		"generated_blocks": json.loads(conversation.generated_blocks or "[]"),
		"page": conversation.page
	}


@frappe.whitelist()
def list_conversations() -> list:
	"""List all AI conversations for the current user."""
	if not frappe.has_permission("Builder Page", ptype="read"):
		frappe.throw("You do not have permission to view conversations.")

	conversations = frappe.get_all(
		"Builder AI Conversation",
		filters={"owner": frappe.session.user},
		fields=["name", "title", "status", "page", "creation", "modified"],
		order_by="modified desc",
		limit=50
	)

	return conversations


@frappe.whitelist()
def update_site_context(conversation_id: str, site_context: dict | str) -> dict:
	"""Manually update the site context."""
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to update conversations.")

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)

	if isinstance(site_context, str):
		site_context = json.loads(site_context)

	conversation.site_context = json.dumps(site_context)
	conversation.save()

	return {
		"success": True,
		"site_context": site_context
	}


@frappe.whitelist()
def preview_blocks(conversation_id: str) -> dict:
	"""Preview generated blocks without creating a page."""
	if not frappe.has_permission("Builder Page", ptype="read"):
		frappe.throw("You do not have permission to preview blocks.")

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)
	site_context = json.loads(conversation.site_context or "{}")

	blocks = generate_blocks_from_context(site_context)

	return {
		"blocks": blocks,
		"site_context": site_context
	}
