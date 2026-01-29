"""
Builder AI - AI-powered website generation for Frappe Builder

This module provides:
1. Chat-based information collection
2. Structured site context extraction
3. Block generation from context
"""

import json
import random
import string
from typing import Any

import frappe
from frappe.integrations.utils import make_post_request


def generate_block_id() -> str:
	"""Generate a unique 9-character block ID."""
	return "".join(random.choices(string.ascii_lowercase + string.digits, k=9))


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

### Style & Feel
- Color preferences OR let you suggest based on industry
- Modern/classic/minimal/bold/playful/elegant
- Any sites they like for inspiration
- Brand personality (professional, friendly, luxurious, approachable?)

### Structure
- One-page or multi-page?
- Key sections needed
- Call-to-action priorities

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
      "is_main": true,
      "sections": [...]
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
    "columns": ["about", "links", "contact", "social"]
  }},
  "contact_info": {{...}},
  "seo": {{
    "meta_title": "string",
    "meta_description": "string"
  }}
}}

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
# BLOCK TEMPLATES - Pre-built section templates for reference
# =============================================================================

def get_hero_template(context: dict) -> dict:
	"""Generate a hero section from context."""
	section = next((s for s in context.get("sections", []) if s.get("type") == "hero"), {})
	style = context.get("style", {})

	primary_color = style.get("primary_color", "#171717")
	text_color = style.get("text_color", "#171717")
	secondary_text = style.get("secondary_color", "#525252")

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
			"paddingTop": "120px",
			"paddingBottom": "120px",
			"paddingLeft": "20px",
			"paddingRight": "20px"
		},
		"tabletStyles": {},
		"mobileStyles": {
			"paddingTop": "80px",
			"paddingBottom": "80px"
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
						"innerHTML": section.get("headline", context.get("tagline", "Welcome to Our Site")),
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "56px",
							"fontWeight": "700",
							"lineHeight": "120%",
							"color": text_color,
							"letterSpacing": "-0.02em"
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
						"innerHTML": f"<p>{section.get('subheadline', section.get('description', context.get('description', 'Discover what makes us different')))}</p>",
						"attributes": {},
						"customAttributes": {},
						"classes": [],
						"dataKey": None,
						"baseStyles": {
							"fontSize": "20px",
							"fontWeight": "400",
							"lineHeight": "160%",
							"color": secondary_text,
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
									"href": section.get("cta_link", "/get-started")
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
									"fontWeight": "500",
									"paddingTop": "14px",
									"paddingBottom": "14px",
									"paddingLeft": "28px",
									"paddingRight": "28px",
									"borderRadius": "12px",
									"textDecoration": "none"
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
										"blockName": "cta-text",
										"innerHTML": section.get("cta_text", "Get Started"),
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


def get_features_template(context: dict) -> dict:
	"""Generate a features section from context."""
	section = next((s for s in context.get("sections", []) if s.get("type") == "features"), {})
	style = context.get("style", {})

	primary_color = style.get("primary_color", "#171717")
	text_color = style.get("text_color", "#171717")
	secondary_text = style.get("secondary_color", "#525252")
	bg_color = style.get("background_color", "#ffffff")

	items = section.get("items", [
		{"title": "Feature 1", "description": "Description of feature 1"},
		{"title": "Feature 2", "description": "Description of feature 2"},
		{"title": "Feature 3", "description": "Description of feature 3"}
	])

	feature_cards = []
	for item in items:
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
					"innerHTML": item.get("icon", ""),
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "32px",
						"width": "48px",
						"height": "48px",
						"display": "flex",
						"alignItems": "center",
						"justifyContent": "center",
						"backgroundColor": primary_color,
						"color": "#ffffff",
						"borderRadius": "12px"
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
					"innerHTML": item.get("title", "Feature"),
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
					"innerHTML": f"<p>{item.get('description', 'Feature description')}</p>",
					"attributes": {},
					"customAttributes": {},
					"classes": [],
					"dataKey": None,
					"baseStyles": {
						"fontSize": "16px",
						"lineHeight": "150%",
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
								"innerHTML": section.get("headline", "Features"),
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
								"innerHTML": f"<p>{section.get('subheadline', section.get('description', 'Everything you need to succeed'))}</p>",
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
	section = next((s for s in context.get("sections", []) if s.get("type") == "cta"), {})
	style = context.get("style", {})

	primary_color = style.get("primary_color", "#171717")

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
						"innerHTML": section.get("headline", "Ready to get started?"),
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
						"innerHTML": f"<p>{section.get('description', 'Join thousands of satisfied customers today.')}</p>",
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
							"href": section.get("cta_link", "/signup")
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
								"innerHTML": section.get("cta_text", "Get Started Free"),
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


def get_footer_template(context: dict) -> dict:
	"""Generate a footer section from context."""
	style = context.get("style", {})
	contact = context.get("contact_info", {})
	business_name = context.get("business_name", "Company")

	text_color = style.get("text_color", "#171717")
	secondary_text = style.get("secondary_color", "#525252")

	return {
		"blockId": generate_block_id(),
		"element": "footer",
		"blockName": "footer",
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
			"paddingTop": "60px",
			"paddingBottom": "60px",
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
		"children": [
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
						"innerHTML": f"<p>&copy; 2025 {business_name}. All rights reserved.</p>",
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
			"debug_mode": False
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

	config = {
		"enabled": settings.enabled,
		"provider": settings.ai_provider,
		"ollama_base_url": settings.ollama_base_url or "http://localhost:11434",
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


def call_ollama(messages: list[dict], model: str, temperature: float, config: dict) -> str:
	"""Make a call to Ollama API."""
	import requests

	base_url = config["ollama_base_url"].rstrip("/")
	url = f"{base_url}/api/chat"

	# Add JSON instruction to the system prompt for Ollama
	# since it doesn't support response_format natively
	enhanced_messages = []
	for msg in messages:
		if msg["role"] == "system":
			enhanced_messages.append({
				"role": "system",
				"content": msg["content"] + "\n\nIMPORTANT: You MUST respond with valid JSON only. No markdown, no explanations, just the JSON object."
			})
		else:
			enhanced_messages.append(msg)

	payload = {
		"model": model,
		"messages": enhanced_messages,
		"stream": False,
		"options": {
			"temperature": temperature
		},
		"format": "json"
	}

	timeout = config.get("ollama_timeout", 120)

	try:
		response = requests.post(
			url,
			json=payload,
			timeout=timeout
		)
		response.raise_for_status()
		result = response.json()

		content = result.get("message", {}).get("content", "")

		# Try to extract JSON if wrapped in markdown code blocks
		if "```json" in content:
			content = content.split("```json")[1].split("```")[0].strip()
		elif "```" in content:
			content = content.split("```")[1].split("```")[0].strip()

		return content

	except requests.exceptions.ConnectionError:
		frappe.throw(
			f"Cannot connect to Ollama at {base_url}. "
			"Please ensure Ollama is running (ollama serve) and the URL is correct."
		)
	except requests.exceptions.Timeout:
		frappe.throw("Ollama request timed out. The model might be loading or the request is too complex.")
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
	"""Analyze image using Ollama vision model (llava, etc.)."""
	import requests
	import base64

	base_url = config["ollama_base_url"].rstrip("/")
	vision_model = config.get("ollama_vision_model", "llava")

	# Prepare image data
	# If it's a URL, download and convert to base64
	if image_data.startswith("http"):
		try:
			response = requests.get(image_data, timeout=30)
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

	timeout = config.get("ollama_timeout", 120)

	try:
		response = requests.post(
			f"{base_url}/api/chat",
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
		return {
			"success": True,
			"provider": config["provider"],
			"model": config.get("ollama_model") if config["provider"] == "ollama" else config.get("openai_model"),
			"message": "Connection successful!"
		}
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


@frappe.whitelist()
def generate_page(conversation_id: str, page_name: str = None) -> dict:
	"""Generate a Builder page from the collected context."""
	check_ai_enabled()

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)
	site_context = json.loads(conversation.site_context or "{}")

	if not site_context:
		frappe.throw("No site context found. Please complete the conversation first.")

	# Generate blocks using templates based on sections
	blocks = generate_blocks_from_context(site_context)

	# Create the page
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
		"page_title": site_context.get("business_name", "Generated Page"),
		"route": f"/{page_name}",
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
		"blocks": blocks
	}


def generate_blocks_from_context(context: dict) -> list:
	"""Generate Frappe Builder blocks from site context."""
	blocks = []
	sections = context.get("sections", [])

	# If no sections defined, create default sections
	if not sections:
		sections = [
			{"type": "hero"},
			{"type": "features"},
			{"type": "cta"}
		]

	# Generate blocks for each section type
	section_generators = {
		"hero": get_hero_template,
		"features": get_features_template,
		"cta": get_cta_template,
		"footer": get_footer_template
	}

	for section in sections:
		section_type = section.get("type", "")
		if section_type in section_generators:
			block = section_generators[section_type](context)
			blocks.append(block)

	# Always add footer if not present
	if not any(s.get("type") == "footer" for s in sections):
		blocks.append(get_footer_template(context))

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
