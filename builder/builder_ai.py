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

COLLECTOR_SYSTEM_PROMPT = """You are a friendly website design assistant helping users create their perfect website. Your role is to have a natural conversation to understand what they want to build.

## Your Responsibilities:
1. Understand the type of website they want (landing page, portfolio, business site, etc.)
2. Learn about their brand (colors, style preferences, tone)
3. Gather content for each section (headings, descriptions, CTAs)
4. Understand their target audience

## Conversation Guidelines:
- Be conversational and friendly, not robotic
- Ask ONE question at a time to avoid overwhelming the user
- Provide suggestions and examples when helpful
- If the user is unsure, offer 2-3 options to choose from
- Acknowledge their choices positively before moving on

## Information to Collect:
1. **Site Type**: What kind of site (landing page, portfolio, blog, business, etc.)
2. **Business/Project Info**: Name, tagline, description
3. **Sections Needed**: Hero, features, testimonials, pricing, contact, etc.
4. **Content**: Headlines, descriptions, button text for each section
5. **Style Preferences**: Colors, modern/classic, minimal/detailed
6. **Images**: Descriptions of images they want (we'll use placeholders)

## Response Format:
Always respond with a JSON object containing:
{
  "message": "Your friendly response to the user",
  "site_context": {
    // Updated site information collected so far
    // Include ALL previously collected info plus any new info
  },
  "collection_complete": false,  // Set to true when you have enough info
  "next_question_topic": "brief description of what you'll ask next"
}

## Site Context Schema:
{
  "site_type": "landing_page|portfolio|business|blog|ecommerce",
  "business_name": "string",
  "tagline": "string",
  "description": "string",
  "target_audience": "string",
  "style": {
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex",
    "background_color": "#hex",
    "text_color": "#hex",
    "style_preference": "modern|classic|minimal|bold|playful",
    "font_style": "sans-serif|serif|modern|classic"
  },
  "sections": [
    {
      "type": "hero|features|testimonials|pricing|contact|about|cta|footer|navbar",
      "headline": "string",
      "subheadline": "string",
      "description": "string",
      "cta_text": "string",
      "cta_link": "string",
      "items": [
        // For features, testimonials, pricing, etc.
        {
          "title": "string",
          "description": "string",
          "icon": "description of icon needed",
          "price": "for pricing items",
          "author": "for testimonials"
        }
      ],
      "image_description": "description of the image needed"
    }
  ],
  "contact_info": {
    "email": "string",
    "phone": "string",
    "address": "string",
    "social_links": {}
  }
}

Start by greeting the user and asking what kind of website they want to create."""


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

def get_llm_config() -> dict:
	"""Get LLM configuration from site config.

	Configuration options in site_config.json:
	- ai_provider: "ollama" or "openai" (default: "ollama")
	- ollama_base_url: Ollama API URL (default: "http://localhost:11434")
	- ollama_model: Model to use with Ollama (default: "llama3.1" or "mistral")
	- openai_api_key: OpenAI API key (required if using openai)
	- openai_model: Model to use with OpenAI (default: "gpt-4o-mini")
	"""
	return {
		"provider": frappe.conf.get("ai_provider", "ollama"),
		"ollama_base_url": frappe.conf.get("ollama_base_url", "http://localhost:11434"),
		"ollama_model": frappe.conf.get("ollama_model", "llama3.1"),
		"openai_api_key": frappe.conf.get("openai_api_key"),
		"openai_model": frappe.conf.get("openai_model", "gpt-4o-mini"),
	}


# =============================================================================
# LLM API FUNCTIONS
# =============================================================================

def call_llm(messages: list[dict], model: str = None, temperature: float = 0.7) -> str:
	"""Make a call to the LLM API (Ollama or OpenAI)."""
	config = get_llm_config()
	provider = config["provider"]

	if provider == "ollama":
		return call_ollama(messages, model or config["ollama_model"], temperature, config)
	else:
		return call_openai(messages, model or config["openai_model"], temperature, config)


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

	try:
		response = requests.post(
			url,
			json=payload,
			timeout=120
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
	api_key = config["openai_api_key"]
	if not api_key:
		frappe.throw("OpenAI API Key not set in site config. Please add 'openai_api_key' to your site_config.json")

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
		})
	)

	return response["choices"][0]["message"]["content"]


@frappe.whitelist()
def get_ai_config() -> dict:
	"""Get current AI configuration (for frontend display)."""
	config = get_llm_config()
	return {
		"provider": config["provider"],
		"ollama_base_url": config["ollama_base_url"] if config["provider"] == "ollama" else None,
		"ollama_model": config["ollama_model"] if config["provider"] == "ollama" else None,
		"openai_configured": bool(config["openai_api_key"]) if config["provider"] == "openai" else None,
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
			"model": config["ollama_model"] if config["provider"] == "ollama" else config["openai_model"],
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
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to use AI Builder.")

	conversation = frappe.get_doc({
		"doctype": "Builder AI Conversation",
		"title": title,
		"status": "collecting",
		"messages": "[]",
		"site_context": "{}",
		"generated_blocks": "[]"
	})
	conversation.insert()

	# Get initial greeting from LLM
	initial_message = {
		"role": "system",
		"content": COLLECTOR_SYSTEM_PROMPT
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
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to use AI Builder.")

	conversation = frappe.get_doc("Builder AI Conversation", conversation_id)

	# Get existing messages and context
	messages = json.loads(conversation.messages or "[]")
	site_context = json.loads(conversation.site_context or "{}")

	# Add user message
	messages.append({
		"role": "user",
		"content": message
	})

	# Build LLM messages with system prompt and context
	llm_messages = [
		{
			"role": "system",
			"content": COLLECTOR_SYSTEM_PROMPT + f"\n\nCurrent site context collected so far:\n{json.dumps(site_context, indent=2)}"
		}
	]

	# Add conversation history (last 20 messages to avoid token limits)
	for msg in messages[-20:]:
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
def generate_page(conversation_id: str, page_name: str = None) -> dict:
	"""Generate a Builder page from the collected context."""
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to create pages.")

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
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to use AI Builder.")

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
