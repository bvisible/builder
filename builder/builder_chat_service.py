# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""
Builder Chat Service
AI-guided conversational interface for collecting site generation parameters.
Uses existing builder/ai/providers and builder/api.generate_complete_site().
"""

import frappe
from frappe import _
import json
import re
from typing import Any, Dict, List, Optional


# Available themes with descriptions for suggestion buttons
THEMES = {
	"modern": "Clean, professional",
	"neobrutalist": "Bold, high contrast",
	"glassmorphism": "Frosted glass effects",
	"minimal": "Ultra-clean, simple",
	"corporate": "Professional, serious",
	"creative": "Artistic, colorful",
}

# Available site types (primary types first, secondary available via conversation)
SITE_TYPES = {
	"vitrine": "Showcase website (multi-page)",
	"one_page": "Single page website",
	"ecommerce": "Online store",
	"vitrine_user": "Showcase + user login",
	# Secondary (still available via conversation)
	"blog": "Blog / content site",
	"ecommerce_search": "Online store + search",
	"saas": "Software product",
	"portfolio": "Portfolio / showcase",
}

# Color palettes for suggestions
COLOR_PALETTES = [
	{"label": "Ocean", "primary": "#0ea5e9", "secondary": "#06b6d4"},
	{"label": "Forest", "primary": "#16a34a", "secondary": "#65a30d"},
	{"label": "Sunset", "primary": "#f97316", "secondary": "#ef4444"},
	{"label": "Royal", "primary": "#7c3aed", "secondary": "#6366f1"},
	{"label": "Rose", "primary": "#e11d48", "secondary": "#f43f5e"},
	{"label": "Midnight", "primary": "#1e293b", "secondary": "#3b82f6"},
]

# Steps configuration
STEPS = ["description", "style", "pages", "generation"]
STEPS_FULL_SITE = STEPS
STEPS_SINGLE_PAGE = ["page_request", "generation"]

# Required fields per step
REQUIRED_FIELDS = {
	"description": ["site_description", "site_name", "site_type"],
	"style": ["theme", "primary_color"],
	"pages": [],  # auto-populated
}


class BuilderChatService:
	"""Service for managing AI-guided builder chat conversations."""

	def __init__(self):
		self._ai_settings = None

	def _get_ai_settings(self):
		"""Get AI settings (cached per request)."""
		if not self._ai_settings:
			from builder.ai.config import get_ai_settings
			self._ai_settings = get_ai_settings()
		return self._ai_settings

	def _get_provider(self):
		"""Get configured AI provider."""
		settings = self._get_ai_settings()
		from builder.ai.providers import get_provider
		return get_provider(
			settings.provider,
			model=settings.model,
			api_key=settings.api_key,
			base_url=settings.base_url,
		)

	def start_session(self, user: Optional[str] = None) -> Dict:
		"""Start a new builder chat session."""
		try:
			# Abandon existing active sessions
			existing = frappe.get_all(
				"Builder Chat Session",
				filters={"user": user or frappe.session.user, "status": "Active"},
				pluck="name"
			)
			for session_name in existing:
				frappe.db.set_value("Builder Chat Session", session_name, "status", "Abandoned")
			if existing:
				frappe.db.commit()

			# Create new session
			session = frappe.get_doc({
				"doctype": "Builder Chat Session",
				"user": user or frappe.session.user,
				"status": "Active",
				"current_step": "description",
			})
			session.insert(ignore_permissions=True)

			# Generate welcome message
			welcome = self._generate_welcome_message()
			session.add_message(
				role="assistant",
				content=welcome["content"],
				buttons=welcome.get("buttons")
			)
			session.save(ignore_permissions=True)

			return {
				"success": True,
				"session_id": session.session_id,
				"is_resumed": False,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"messages": self._format_messages(session.messages),
				"missing_fields": session.get_missing_fields(),
				"generation_mode": session.generation_mode,
			}

		except Exception as e:
			frappe.log_error("Builder Chat: Start session error", str(e))
			return {"success": False, "message": _("Failed to start chat session")}

	def _generate_welcome_message(self) -> Dict:
		"""Generate the initial welcome message with mode choice."""
		first_name = self._get_user_first_name()
		greeting = _("Hello {name}!").format(name=first_name) if first_name else _("Hello!")

		intro = _("I'm **Builder AI**, your website creation assistant.")
		question = _("**What would you like to do?**")

		content = f"{greeting} {intro}\n\n{question}"

		buttons = [
			{"label": _("Generate a full site"), "value": "__MODE_FULL_SITE__"},
			{"label": _("Add a page to my site"), "value": "__MODE_SINGLE_PAGE__"},
		]

		return {"content": content, "buttons": buttons}

	def _generate_full_site_intro(self) -> Dict:
		"""Generate the full-site mode intro with site type choices."""
		question = _("**What type of website do you want to create?** Briefly describe your business or project, and I'll take care of the rest.")

		buttons = [
			{"label": _("Showcase site"), "value": _("I want a multi-page showcase website")},
			{"label": _("Single page site"), "value": _("I want a single page website")},
			{"label": _("Online store"), "value": _("I want an online store to sell products")},
			{"label": _("Site with login"), "value": _("I want a showcase site with user login")},
		]

		return {"content": question, "buttons": buttons}

	def _analyze_existing_site(self) -> Dict:
		"""Analyze the existing site to extract theme, colors, fonts for single-page generation."""
		context = {}

		# 1. Read Website Header Footer Config for current theme
		try:
			config = frappe.get_single("Website Header Footer Config")
			theme_data = config.get_theme_data()
			context.update(theme_data)
		except Exception:
			pass

		# 2. Check Builder Site Config for previous AI generation (design brief)
		try:
			site_configs = frappe.get_all(
				"Builder Site Config",
				fields=["name", "theme", "primary_color", "secondary_color", "design_brief_json"],
				order_by="modified desc",
				limit=1
			)
			if site_configs:
				sc = site_configs[0]
				if sc.get("theme"):
					context["theme"] = sc["theme"]
				if sc.get("primary_color") and not context.get("primary_color"):
					context["primary_color"] = sc["primary_color"]
				if sc.get("secondary_color") and not context.get("secondary_color"):
					context["secondary_color"] = sc["secondary_color"]
				if sc.get("design_brief_json"):
					context["has_design_brief"] = True
					context["design_brief_json"] = sc["design_brief_json"]
		except Exception:
			pass

		# 3. List existing published Builder Pages
		try:
			context["existing_pages"] = frappe.get_all(
				"Builder Page",
				filters={"published": 1},
				fields=["name", "page_title", "route"],
				order_by="route asc"
			)
		except Exception:
			context["existing_pages"] = []

		# 4. Default theme if nothing found
		if not context.get("theme"):
			context["theme"] = "modern"

		return context

	def _generate_single_page_intro(self, site_context: Dict) -> Dict:
		"""Generate the intro message for single-page mode, showing detected site info."""
		pages = site_context.get("existing_pages", [])
		pages_str = ", ".join([p.get("page_title") or p.get("name") for p in pages]) if pages else _("none detected")

		detected_info = []
		if site_context.get("primary_color"):
			detected_info.append(_("Primary color: {0}").format(site_context["primary_color"]))
		if site_context.get("heading_font") and site_context.get("heading_font") != "Inter":
			detected_info.append(_("Font: {0}").format(site_context["heading_font"]))
		if site_context.get("theme"):
			detected_info.append(_("Theme: {0}").format(site_context["theme"]))
		detected_str = "\n".join([f"- {info}" for info in detected_info]) if detected_info else _("- Default style")

		content = _("I've analyzed your existing site.") + "\n\n"
		content += _("**Existing pages**: {0}").format(pages_str) + "\n\n"
		content += _("**Detected style**:") + "\n" + detected_str + "\n\n"
		content += _("**What kind of page would you like to add?** Describe it and I'll generate it matching your current design.")

		buttons = [
			{"label": _("About page"), "value": _("Generate an About page for my site")},
			{"label": _("Services page"), "value": _("Generate a Services page for my site")},
			{"label": _("Contact page"), "value": _("Generate a Contact page for my site")},
			{"label": _("FAQ page"), "value": _("Generate a FAQ page for my site")},
		]

		return {"content": content, "buttons": buttons}

	def process_message(self, session_id: str, user_message: str) -> Dict:
		"""Process a user message and generate AI response."""
		try:
			session = frappe.get_doc("Builder Chat Session", {"session_id": session_id})

			# Handle special commands
			if user_message.startswith("__"):
				return self._handle_special_command(session, user_message)

			# Add user message
			session.add_message(role="user", content=user_message)

			# Try to extract data from message (regex-based)
			extracted = self._extract_data_regex(user_message, session)

			# Build context and call AI
			context = self._build_ai_context(session)
			ai_response = self._call_ai(context, user_message, session)

			# Parse AI response for extracted data and buttons
			parsed = self._parse_ai_response(ai_response)

			# Merge AI-extracted data
			ai_extracted = parsed.get("extracted_data", {})
			if ai_extracted:
				extracted.update(ai_extracted)

			# Process inspiration URLs if found
			if extracted.get("inspiration_urls"):
				self._process_inspiration_urls(session, extracted.pop("inspiration_urls"))

			# Update session with extracted data
			if extracted:
				session.update_extracted_data(extracted)

			response_content = parsed.get("content", ai_response)

			# Add assistant message
			session.add_message(
				role="assistant",
				content=response_content,
				buttons=parsed.get("buttons"),
				extracted_data=extracted if extracted else None
			)

			# Check step transition
			self._check_step_transition(session)

			session.save(ignore_permissions=True)

			return {
				"success": True,
				"session_id": session.session_id,
				"response": response_content,
				"buttons": parsed.get("buttons"),
				"extracted_data": extracted,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
				"is_ready": len(session.get_missing_fields()) == 0 and session.site_description,
				"generation_mode": session.generation_mode,
			}

		except Exception as e:
			frappe.log_error("Builder Chat: Process message error", str(e))
			return {
				"success": False,
				"message": _("Failed to process message: {0}").format(str(e))
			}

	def upload_logo(self, session_id: str, file_url: str) -> Dict:
		"""Handle logo upload."""
		try:
			session = frappe.get_doc("Builder Chat Session", {"session_id": session_id})
			session.logo_image = file_url
			session.add_message(role="user", content=_("(Logo uploaded)"))

			logo_msg = _("Logo received! I'll use it for your site generation.")
			next_q = self._get_next_question(session)
			response = f"{logo_msg}\n\n{next_q}"

			session.add_message(role="assistant", content=response)
			session.save(ignore_permissions=True)

			return {
				"success": True,
				"response": response,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
			}

		except Exception as e:
			frappe.log_error("Builder Chat: Upload logo error", str(e))
			return {"success": False, "message": _("Failed to process logo")}

	def trigger_generation(self, session_id: str) -> Dict:
		"""Trigger site or page generation with collected parameters."""
		try:
			session = frappe.get_doc("Builder Chat Session", {"session_id": session_id})

			# Validate readiness
			is_ready, missing = session.is_ready_for_generation()
			if not is_ready:
				missing_labels = [f["label"] for f in missing]
				return {
					"success": False,
					"message": _("Missing required fields: {0}").format(", ".join(missing_labels))
				}

			# Update session status
			session.status = "Generating"
			session.current_step = "generation"

			# Branch based on generation mode
			if session.generation_mode == "single_page":
				return self._trigger_single_page_generation(session)

			# Full-site mode: call the existing generate_complete_site API
			from builder.api import generate_complete_site

			# Enrich prompt with inspiration data if available
			generation_prompt = session.site_description
			if session.inspiration_urls:
				try:
					inspirations = json.loads(session.inspiration_urls)
					inspiration_names = [item.get("name") for item in inspirations if item.get("name")]
					if inspiration_names:
						from builder.api import analyze_inspirations_for_generation
						analysis = analyze_inspirations_for_generation(
							inspiration_names=json.dumps(inspiration_names)
						)
						if analysis and isinstance(analysis, dict):
							# Append style hints from inspiration analysis
							style_hints = []
							if analysis.get("dominant_colors"):
								colors = [c.get("hex", "") for c in analysis["dominant_colors"][:3]]
								style_hints.append(f"Inspiration colors: {', '.join(colors)}")
							if analysis.get("style_keywords"):
								style_hints.append(f"Style: {', '.join(analysis['style_keywords'][:5])}")
							if style_hints:
								generation_prompt += "\n\n" + "\n".join(style_hints)
				except Exception as e:
					frappe.log_error("Builder Chat: Inspiration analysis error", str(e))

			# Parse social_links if present
			social_links_str = None
			if session.social_links:
				social_links_str = session.social_links if isinstance(session.social_links, str) else json.dumps(session.social_links)

			result = generate_complete_site(
				prompt=generation_prompt,
				site_name=session.site_name,
				site_type=session.site_type or "vitrine",
				theme=session.theme or "modern",
				primary_color=session.primary_color,
				secondary_color=session.secondary_color,
				logo_text=session.logo_text or session.site_name,
				logo_image=session.logo_image,
				cta_text=session.cta_text or "Contact",
				cta_url=session.cta_url or "/contact",
				social_links=social_links_str,
			)

			if result and result.get("job_id"):
				session.job_id = result["job_id"]
				session.generation_status = "queued"
				session.save(ignore_permissions=True)

				return {
					"success": True,
					"job_id": result["job_id"],
					"status": "queued",
					"completion_percentage": session.completion_percentage,
				}
			else:
				session.status = "Failed"
				session.save(ignore_permissions=True)
				return {"success": False, "message": _("Failed to start generation")}

		except Exception as e:
			frappe.log_error("Builder Chat: Trigger generation error", str(e))
			return {"success": False, "message": _("Failed to trigger generation: {0}").format(str(e))}

	def get_session(self, session_id: str) -> Dict:
		"""Get full session data."""
		try:
			session = frappe.get_doc("Builder Chat Session", {"session_id": session_id})
			return {
				"success": True,
				"session_id": session.session_id,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"messages": self._format_messages(session.messages),
				"missing_fields": session.get_missing_fields(),
				"is_ready": len(session.get_missing_fields()) == 0 and session.site_description,
			}
		except frappe.DoesNotExistError:
			return {"success": False, "message": _("Session not found")}
		except Exception as e:
			frappe.log_error("Builder Chat: Get session error", str(e))
			return {"success": False, "message": _("Failed to get session")}

	# =========================================================================
	# AI INTERACTION
	# =========================================================================

	def _build_ai_context(self, session) -> str:
		"""Build the system prompt for the AI."""
		# Gather current session state
		collected = {}
		for field in ["site_description", "site_name", "site_type", "theme",
					   "primary_color", "secondary_color", "heading_font",
					   "body_font", "logo_text", "logo_image",
					   "cta_text", "cta_url"]:
			val = session.get(field)
			if val:
				collected[field] = val

		missing = session.get_missing_fields()
		missing_str = ", ".join([f["label"] for f in missing]) if missing else "None"

		# Single-page mode: simplified prompt
		if session.generation_mode == "single_page":
			return f"""You are Builder AI, an assistant that helps users add a new page to their existing website.

CURRENT STATE:
- Step: {session.current_step}
- Collected data: {json.dumps(collected, ensure_ascii=False)}
- Existing site colors: primary={session.primary_color}, secondary={session.secondary_color}
- Existing site fonts: heading={session.heading_font}, body={session.body_font}

YOUR TASK:
- Understand what kind of page the user wants to add
- Extract: site_description (what the page should contain/be about)
- The user does NOT need to choose theme/colors/fonts — those come from the existing site
- Once you understand the page request, confirm and tell the user to click "Generate Page"

RULES:
- Be concise and friendly
- Respond in the SAME LANGUAGE as the user's message
- ONE question at a time
- Use markdown for formatting

DATA EXTRACTION:
<extracted_data>{{"site_description": "Description of the page to generate"}}</extracted_data>

SUGGESTION BUTTONS:
<buttons>[{{"label": "Option 1", "value": "value1"}}]</buttons>

When the page description is clear, congratulate the user and tell them to click "Generate Page"."""

		# Full-site mode: original prompt
		themes_str = "\n".join([f"- {k}: {v}" for k, v in THEMES.items()])
		site_types_str = "\n".join([f"- {k}: {v}" for k, v in SITE_TYPES.items()])
		palettes_str = "\n".join([f"- {p['label']}: {p['primary']} / {p['secondary']}" for p in COLOR_PALETTES])

		# Inspiration context
		inspiration_str = ""
		if session.inspiration_urls:
			try:
				inspirations = json.loads(session.inspiration_urls)
				if inspirations:
					urls_list = [item.get("url", "") for item in inspirations]
					inspiration_str = "\n".join([f"- {u}" for u in urls_list])
			except (json.JSONDecodeError, TypeError):
				pass

		inspiration_block = ""
		if inspiration_str:
			inspiration_block = f"""
INSPIRATION:
- Users can share website URLs as design inspiration
- When a URL is shared, acknowledge it as a reference for style/colors
- These sites won't be copied, they serve as style references
- Current inspirations:
{inspiration_str}
"""

		system_prompt = f"""You are Builder AI, an assistant that guides users to create a website.
Your goal is to collect the required parameters through a natural conversation.

CURRENT STATE:
- Step: {session.current_step}
- Collected data: {json.dumps(collected, ensure_ascii=False)}
- Missing fields: {missing_str}

REQUIRED FIELDS (collect in order):
1. DESCRIPTION STEP: site_description (what the site is about), site_name (business/project name), site_type (type of site)
2. STYLE STEP: theme (visual theme), primary_color (hex color), secondary_color (optional hex)
3. PAGES STEP: auto-populated based on site_type, but can ask about CTA text/url, social links

AVAILABLE OPTIONS:
Themes: {themes_str}
Site types: {site_types_str}
Color palettes: {palettes_str}
{inspiration_block}
RULES:
- Ask ONE question at a time
- Be concise and friendly
- When the user describes their business, extract site_description, site_name, and suggest a site_type
- When a field is collected, move to the next missing field
- Use markdown for formatting (bold for important words)
- Respond in the SAME LANGUAGE as the user's message
- Users can share website URLs as design inspiration at any time — acknowledge them positively

DATA EXTRACTION:
When you identify data from the user's message, include it in your response using this format:
<extracted_data>{{"field_name": "value", ...}}</extracted_data>

For example, if the user says "I have a bakery called Sweet Dreams":
<extracted_data>{{"site_description": "A bakery called Sweet Dreams", "site_name": "Sweet Dreams", "site_type": "vitrine"}}</extracted_data>

SUGGESTION BUTTONS:
When offering choices, include buttons using this format:
<buttons>[{{"label": "Option 1", "value": "value1"}}, {{"label": "Option 2", "value": "value2"}}]</buttons>

When asking about themes, offer theme buttons.
When asking about colors, offer palette buttons.
When all required fields are collected, congratulate the user and tell them they can click "Generate Site"."""

		return system_prompt

	def _call_ai(self, system_prompt: str, user_message: str, session) -> str:
		"""Call the AI provider with conversation history.

		Uses the provider's internal HTTP methods to support multi-turn conversation.
		The base provider only has generate(prompt, system_prompt) which formats
		a single user message, so we call the HTTP layer directly for multi-turn.
		"""
		try:
			provider = self._get_provider()

			# Build messages list for multi-turn conversation
			messages = [{"role": "system", "content": system_prompt}]

			# Add conversation history (last 20 messages max)
			history = session.get_conversation_history(include_system=False)
			messages.extend(history[-20:])

			# Ensure the current user message is included
			if not history or history[-1].get("content") != user_message:
				messages.append({"role": "user", "content": user_message})

			# Use provider's HTTP method directly for multi-turn support
			if hasattr(provider, '_generate_with_http'):
				# Ollama provider - use HTTP streaming
				response = provider._generate_with_http(
					messages=messages,
					temperature=0.7,
					max_tokens=1024,
				)
			elif hasattr(provider, '_make_streaming_request'):
				# Fallback: build payload manually
				payload = {
					"model": provider.model,
					"messages": messages,
					"stream": True,
					"options": {
						"temperature": 0.7,
						"num_predict": 1024,
						"num_ctx": getattr(provider, 'num_ctx', 32768),
					},
				}
				response = provider._make_streaming_request("/api/chat", payload)
			else:
				# Final fallback: use simple generate with concatenated context
				context = "\n".join([
					f"[{m['role']}]: {m['content']}"
					for m in messages[1:]  # Skip system
				])
				response = provider.generate(
					prompt=context,
					system_prompt=system_prompt,
					temperature=0.7,
					max_tokens=1024,
				)

			if isinstance(response, str):
				return response
			elif isinstance(response, dict):
				return response.get("content", response.get("message", str(response)))
			else:
				return str(response)

		except Exception as e:
			frappe.log_error("Builder Chat: AI call error", str(e))
			# Fallback: generate a simple response based on missing fields
			return self._generate_fallback_response(session)

	def _generate_fallback_response(self, session) -> str:
		"""Generate a response without AI (fallback)."""
		missing = session.get_missing_fields()
		if not missing:
			return _("All required information has been collected! You can now click **Generate Site** to create your website.")

		next_field = missing[0]
		field = next_field.get("field", "")
		label = next_field.get("label", "")

		prompts = {
			"site_description": _("Could you describe your website project? What is your business or activity about?"),
			"site_name": _("What is the name of your business or project?"),
			"site_type": _("What type of site would you like?"),
			"theme": _("Which visual theme do you prefer for your site?"),
			"primary_color": _("What main color would you like for your site?"),
		}

		question = prompts.get(field, _("Could you provide: **{0}**?").format(label))

		# Add buttons for specific fields
		buttons_str = ""
		if field == "site_type":
			btns = [{"label": v, "value": k} for k, v in SITE_TYPES.items()]
			buttons_str = f"\n\n<buttons>{json.dumps(btns)}</buttons>"
		elif field == "theme":
			btns = [{"label": f"{k} ({v})", "value": k} for k, v in THEMES.items()]
			buttons_str = f"\n\n<buttons>{json.dumps(btns)}</buttons>"
		elif field == "primary_color":
			btns = [{"label": p["label"], "value": p["primary"]} for p in COLOR_PALETTES]
			buttons_str = f"\n\n<buttons>{json.dumps(btns)}</buttons>"

		return question + buttons_str

	# =========================================================================
	# RESPONSE PARSING
	# =========================================================================

	def _parse_ai_response(self, response: str) -> Dict:
		"""Parse AI response to extract data and buttons."""
		result = {
			"content": response,
			"extracted_data": {},
			"buttons": None,
		}

		# Extract <extracted_data>...</extracted_data>
		data_match = re.search(r"<extracted_data>(.*?)</extracted_data>", response, re.DOTALL)
		if data_match:
			try:
				result["extracted_data"] = json.loads(data_match.group(1))
			except json.JSONDecodeError:
				pass
			# Remove tag from content
			result["content"] = re.sub(r"<extracted_data>.*?</extracted_data>", "", result["content"], flags=re.DOTALL).strip()

		# Extract <buttons>...</buttons>
		btn_match = re.search(r"<buttons>(.*?)</buttons>", response, re.DOTALL)
		if btn_match:
			try:
				result["buttons"] = json.loads(btn_match.group(1))
			except json.JSONDecodeError:
				pass
			# Remove tag from content
			result["content"] = re.sub(r"<buttons>.*?</buttons>", "", result["content"], flags=re.DOTALL).strip()

		return result

	def _extract_data_regex(self, message: str, session) -> Dict:
		"""Extract data from user message using regex patterns."""
		extracted = {}
		msg_lower = message.lower().strip()

		# Extract hex colors
		hex_match = re.findall(r"#[0-9a-fA-F]{6}\b", message)
		if hex_match:
			if not session.primary_color:
				extracted["primary_color"] = hex_match[0]
				if len(hex_match) > 1:
					extracted["secondary_color"] = hex_match[1]
			elif not session.secondary_color:
				extracted["secondary_color"] = hex_match[0]

		# Check for palette names
		for palette in COLOR_PALETTES:
			if palette["label"].lower() in msg_lower:
				if not session.primary_color:
					extracted["primary_color"] = palette["primary"]
					extracted["secondary_color"] = palette["secondary"]
				break

		# Check for theme names
		for theme_name in THEMES:
			if theme_name.lower() in msg_lower:
				if not session.theme or theme_name.lower() in msg_lower:
					extracted["theme"] = theme_name
				break

		# Check for site type names
		for st_name in SITE_TYPES:
			# Match both key and common synonyms
			if st_name.lower() in msg_lower:
				extracted["site_type"] = st_name
				break

		# Common site type synonyms
		type_synonyms = {
			"vitrine": ["showcase", "vitrine", "presentation", "multi-page", "plusieurs pages"],
			"one_page": ["single page", "one page", "une page", "une seule page", "landing", "mono"],
			"ecommerce": ["shop", "store", "e-commerce", "ecommerce", "boutique", "sell", "vendre"],
			"vitrine_user": ["login", "connexion", "user account", "compte utilisateur", "espace client"],
			"blog": ["blog", "articles", "news"],
			"portfolio": ["portfolio", "gallery", "projects"],
			"saas": ["saas", "software", "app", "platform"],
		}
		if "site_type" not in extracted:
			for st, synonyms in type_synonyms.items():
				if any(s in msg_lower for s in synonyms):
					extracted["site_type"] = st
					break

		# Detect URLs for inspiration
		url_pattern = r'https?://[^\s<>"\')\]]+'
		urls = re.findall(url_pattern, message)
		if urls:
			extracted["inspiration_urls"] = urls

		return extracted

	# =========================================================================
	# STEP MANAGEMENT
	# =========================================================================

	def _check_step_transition(self, session):
		"""Check if we should advance to the next step."""
		current = session.current_step
		missing = session.get_missing_fields()
		steps = STEPS_SINGLE_PAGE if session.generation_mode == "single_page" else STEPS_FULL_SITE

		# Get missing fields for current step
		current_missing = [f for f in missing if f.get("step") == current]

		if not current_missing:
			# Current step complete, advance
			idx = steps.index(current) if current in steps else 0
			if idx < len(steps) - 1:
				next_step = steps[idx + 1]
				# Skip pages step if it has no required fields
				if next_step == "pages":
					# Auto-populate pages_config based on site_type
					self._auto_populate_pages(session)
					# Check if we should skip to generation
					pages_missing = [f for f in missing if f.get("step") == "pages"]
					if not pages_missing:
						session.current_step = next_step
				else:
					session.current_step = next_step

	def _auto_populate_pages(self, session):
		"""Auto-populate pages_config based on site_type."""
		if session.pages_config:
			return  # Already set

		from builder.api import DEFAULT_PAGES_BY_SITE_TYPE
		site_type = session.site_type or "vitrine"
		pages = DEFAULT_PAGES_BY_SITE_TYPE.get(site_type, DEFAULT_PAGES_BY_SITE_TYPE.get("vitrine", []))
		session.pages_config = json.dumps(pages)

	def _get_next_question(self, session) -> str:
		"""Get the next question to ask based on missing fields."""
		missing = session.get_missing_fields()
		if not missing:
			if session.generation_mode == "single_page":
				return _("All set! Click **Generate Page** when you're ready.")
			return _("All information collected! Click **Generate Site** when you're ready.")

		next_field = missing[0]["field"]
		prompts = {
			"site_description": _("What is your website about?"),
			"site_name": _("What is the name of your business?"),
			"site_type": _("What type of site would you like?"),
			"theme": _("Which visual theme do you prefer?"),
			"primary_color": _("What main color would you like?"),
		}
		return prompts.get(next_field, _("Let's continue with the next step."))

	# =========================================================================
	# SPECIAL COMMANDS
	# =========================================================================

	def _handle_special_command(self, session, command: str) -> Dict:
		"""Handle special commands (button values starting with __)."""

		if command == "__MODE_FULL_SITE__":
			session.generation_mode = "full_site"
			session.current_step = "description"
			response = self._generate_full_site_intro()
			session.add_message(role="user", content=_("(Generate a full site)"))
			session.add_message(role="assistant", content=response["content"], buttons=response.get("buttons"))
			session.calculate_completion()
			session.update_missing_fields()
			session.save(ignore_permissions=True)
			return {
				"success": True,
				"response": response["content"],
				"buttons": response.get("buttons"),
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
				"generation_mode": session.generation_mode,
			}

		elif command == "__MODE_SINGLE_PAGE__":
			session.generation_mode = "single_page"
			session.current_step = "page_request"
			# Analyze existing site
			site_context = self._analyze_existing_site()
			# Pre-fill session with existing theme data
			for field in ("primary_color", "secondary_color", "heading_font", "body_font", "theme"):
				if site_context.get(field) and not session.get(field):
					session.set(field, site_context[field])
			response = self._generate_single_page_intro(site_context)
			session.add_message(role="user", content=_("(Add a page to my site)"))
			session.add_message(role="assistant", content=response["content"], buttons=response.get("buttons"))
			session.calculate_completion()
			session.update_missing_fields()
			session.save(ignore_permissions=True)
			return {
				"success": True,
				"response": response["content"],
				"buttons": response.get("buttons"),
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
				"generation_mode": session.generation_mode,
			}

		elif command == "__UPLOAD_LOGO__":
			response = _("Please upload your logo using the upload button or drag & drop.")
			session.add_message(role="assistant", content=response)
			session.save(ignore_permissions=True)
			return {
				"success": True,
				"response": response,
				"await_upload": True,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
			}

		elif command == "__SKIP_LOGO__":
			skip_msg = _("No problem, we'll skip the logo for now.")
			next_q = self._get_next_question(session)
			response = f"{skip_msg}\n\n{next_q}"
			session.add_message(role="user", content=_("(Skip logo)"))
			session.add_message(role="assistant", content=response)
			session.save(ignore_permissions=True)
			return {
				"success": True,
				"response": response,
				"current_step": session.current_step,
				"completion_percentage": session.completion_percentage,
				"missing_fields": session.get_missing_fields(),
			}

		# Default: treat as regular message
		return self.process_message(session.session_id, command.strip("_"))

	# =========================================================================
	# SINGLE PAGE GENERATION
	# =========================================================================

	def _trigger_single_page_generation(self, session) -> Dict:
		"""Generate a single page synchronously using existing site theme."""
		try:
			from builder.ai.generators.page_generator import PageGenerator

			# Build design brief from existing site data
			design_brief = self._build_design_brief_from_existing(session)

			# Generate the page blocks
			gen = PageGenerator()
			blocks = gen.generate_page(
				prompt=session.site_description,
				theme=session.theme or "modern",
				primary_color=session.primary_color,
				secondary_color=session.secondary_color,
				font_family=None,
				page_title=None,
				page_type=None,
				design_brief=design_brief,
			)

			if not blocks:
				session.status = "Failed"
				session.save(ignore_permissions=True)
				return {"success": False, "message": _("Failed to generate page blocks")}

			# Wrap blocks in a root body element
			root_block = {
				"blockId": f"root-{frappe.generate_hash(length=8)}",
				"element": "body",
				"baseStyles": {},
				"children": blocks,
			}

			# Determine page title and route from the description
			page_title = self._extract_page_title(session.site_description)
			route = re.sub(r"[^a-z0-9-]", "", frappe.scrub(page_title).replace("_", "-"))

			# Create the Builder Page
			page = frappe.new_doc("Builder Page")
			page.page_title = page_title
			page.blocks = json.dumps([root_block])
			page.draft_blocks = json.dumps([root_block])
			page.published = 1
			page.insert(ignore_permissions=True)

			# Set clean route
			frappe.db.set_value("Builder Page", page.name, "route", route)
			frappe.db.commit()

			# Add to menu
			from builder.hf_utils.menu_integration import update_menu_after_page_creation
			update_menu_after_page_creation(page)

			# Update session
			session.status = "Completed"
			session.generated_pages = json.dumps([{
				"name": page.name,
				"title": page_title,
				"route": f"/{route}",
			}])
			session.save(ignore_permissions=True)

			return {
				"success": True,
				"status": "completed",
				"pages_created": [{
					"name": page.name,
					"title": page_title,
					"route": f"/{route}",
					"page_name": page.name,
				}],
				"completion_percentage": 100,
			}

		except Exception as e:
			frappe.log_error("Builder Chat: Single page generation error", str(e))
			session.status = "Failed"
			session.save(ignore_permissions=True)
			return {"success": False, "message": _("Failed to generate page: {0}").format(str(e))}

	def _build_design_brief_from_existing(self, session):
		"""Build a DesignBrief from existing site data for single-page generation."""
		from builder.ai.generators.brief_generator import get_default_brief

		# 1. Check for stored design brief from previous AI generation
		try:
			site_configs = frappe.get_all(
				"Builder Site Config",
				fields=["design_brief_json"],
				order_by="modified desc",
				limit=1
			)
			if site_configs and site_configs[0].get("design_brief_json"):
				from builder.ai.schemas.design_brief import DesignBrief
				brief_data = json.loads(site_configs[0]["design_brief_json"])
				# Override with current session values if present
				if session.primary_color:
					brief_data["primary_color"] = session.primary_color
				if session.secondary_color:
					brief_data["secondary_color"] = session.secondary_color
				if session.heading_font:
					brief_data["heading_font"] = session.heading_font
				if session.body_font:
					brief_data["body_font"] = session.body_font
				return DesignBrief(**brief_data)
		except Exception:
			pass

		# 2. Fallback: build default brief with existing colors/fonts
		brief = get_default_brief(
			theme=session.theme or "modern",
			primary_color=session.primary_color,
			secondary_color=session.secondary_color,
		)
		if session.heading_font:
			brief.heading_font = session.heading_font
		if session.body_font:
			brief.body_font = session.body_font
		return brief

	def _extract_page_title(self, description: str) -> str:
		"""Extract a page title from the description."""
		patterns = [
			# "Generate a Services page" -> "Services"
			r"(?:Generate|Create|Générer|Créer)\s+(?:an?|une?)\s+(.+?)\s+page",
			# "A Services page showcasing..." -> "Services"
			r"^(?:An?\s+)(.+?)\s+page\b",
			# "page de contact pour..." -> "Contact"
			r"(?:page\s+(?:de|d'|des)\s+)(.+?)(?:\s+(?:pour|for|de|d'|showcasing|with|that)\s|$)",
		]
		for pattern in patterns:
			match = re.search(pattern, description, re.IGNORECASE)
			if match:
				title = match.group(1).strip().title()
				if 2 < len(title) < 50:
					return title
		# Fallback: use first 3 words, cleaned
		words = description.split()[:3]
		return " ".join(words).title() if words else _("New Page")

	# =========================================================================
	# UTILITIES
	# =========================================================================

	def _process_inspiration_urls(self, session, urls: List[str]):
		"""Capture inspiration URLs and store references in session."""
		from builder.api import capture_inspiration

		existing = []
		if session.inspiration_urls:
			try:
				existing = json.loads(session.inspiration_urls)
			except (json.JSONDecodeError, TypeError):
				existing = []

		for url in urls:
			# Skip already captured URLs
			if any(item.get("url") == url for item in existing):
				continue
			try:
				result = capture_inspiration(url=url, sentiment="like")
				if result and result.get("name"):
					existing.append({"url": url, "name": result["name"]})
			except Exception as e:
				frappe.log_error("Builder Chat: Inspiration capture error", str(e))

		session.inspiration_urls = json.dumps(existing)

	def _get_user_first_name(self) -> str:
		"""Get the current user's first name."""
		try:
			user = frappe.session.user
			if user and user != "Guest":
				user_doc = frappe.get_doc("User", user)
				if user_doc.first_name:
					return user_doc.first_name
				if user_doc.full_name:
					return user_doc.full_name.split()[0]
		except Exception:
			pass
		return ""

	def _format_messages(self, messages) -> List[Dict]:
		"""Format messages for frontend consumption."""
		formatted = []
		for msg in messages:
			entry = {
				"role": msg.role,
				"content": msg.content,
				"timestamp": str(msg.timestamp) if msg.timestamp else None,
				"attachment": msg.attachment,
			}
			# Parse buttons JSON
			if msg.buttons:
				try:
					entry["buttons"] = json.loads(msg.buttons)
				except (json.JSONDecodeError, TypeError):
					entry["buttons"] = None
			else:
				entry["buttons"] = None
			formatted.append(entry)
		return formatted
