# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class BuilderAISettings(Document):
	def validate(self):
		if self.ai_provider == "ollama":
			if not self.ollama_base_url:
				frappe.throw("Ollama Base URL is required when using Ollama provider")
			if not self.ollama_model:
				frappe.throw("Ollama Model is required when using Ollama provider")

		if self.ai_provider == "openai":
			if not self.openai_api_key:
				frappe.throw("OpenAI API Key is required when using OpenAI provider")

		if self.default_temperature and (self.default_temperature < 0 or self.default_temperature > 2):
			frappe.throw("Temperature must be between 0 and 2")

	@frappe.whitelist()
	def test_ollama_connection(self):
		"""Test connection to Ollama server"""
		import requests

		if not self.ollama_base_url:
			frappe.throw("Please set Ollama Base URL first")

		base_url = self.ollama_base_url.rstrip("/")

		try:
			# First check if Ollama is running
			response = requests.get(f"{base_url}/api/tags", timeout=10)
			response.raise_for_status()

			models = response.json().get("models", [])
			model_names = [m.get("name", "").split(":")[0] for m in models]

			# Check if the configured model is available
			configured_model = self.ollama_model.split(":")[0] if self.ollama_model else ""

			if configured_model and configured_model not in model_names:
				frappe.msgprint(
					f"Connection successful! However, model '{self.ollama_model}' is not installed. "
					f"Available models: {', '.join(model_names) or 'None'}. "
					f"Run 'ollama pull {self.ollama_model}' to install it.",
					title="Warning",
					indicator="orange"
				)
			else:
				frappe.msgprint(
					f"Connection successful! Model '{self.ollama_model}' is available.",
					title="Success",
					indicator="green"
				)

			return {"success": True, "models": model_names}

		except requests.exceptions.ConnectionError:
			frappe.throw(
				f"Cannot connect to Ollama at {base_url}. "
				"Please ensure Ollama is running (ollama serve)."
			)
		except Exception as e:
			frappe.throw(f"Connection failed: {str(e)}")

	@frappe.whitelist()
	def test_openai_connection(self):
		"""Test connection to OpenAI API"""
		if not self.openai_api_key:
			frappe.throw("Please set OpenAI API Key first")

		try:
			from frappe.integrations.utils import make_post_request

			response = make_post_request(
				"https://api.openai.com/v1/chat/completions",
				headers={
					"Content-Type": "application/json",
					"Authorization": f"Bearer {self.get_password('openai_api_key')}"
				},
				data=json.dumps({
					"model": self.openai_model or "gpt-4o-mini",
					"messages": [{"role": "user", "content": "Hi"}],
					"max_tokens": 5
				})
			)

			if response.get("choices"):
				frappe.msgprint(
					f"Connection successful! Model '{self.openai_model}' is working.",
					title="Success",
					indicator="green"
				)
				return {"success": True}

		except Exception as e:
			error_msg = str(e)
			if "401" in error_msg:
				frappe.throw("Invalid API key. Please check your OpenAI API key.")
			elif "429" in error_msg:
				frappe.throw("Rate limit exceeded. Please try again later.")
			elif "model" in error_msg.lower():
				frappe.throw(f"Model '{self.openai_model}' is not available. Please check the model name.")
			else:
				frappe.throw(f"Connection failed: {error_msg}")


def get_ai_settings():
	"""Get AI settings with caching"""
	settings = frappe.get_cached_doc("Builder AI Settings")
	return settings


@frappe.whitelist()
def get_ai_configuration():
	"""Get AI configuration for frontend"""
	settings = get_ai_settings()

	return {
		"enabled": settings.enabled,
		"provider": settings.ai_provider,
		"ollama_base_url": settings.ollama_base_url if settings.ai_provider == "ollama" else None,
		"ollama_model": settings.ollama_model if settings.ai_provider == "ollama" else None,
		"openai_model": settings.openai_model if settings.ai_provider == "openai" else None,
		"openai_configured": bool(settings.openai_api_key) if settings.ai_provider == "openai" else None,
		"auto_generate_preview": settings.auto_generate_preview,
		"allow_website_manager": settings.allow_website_manager,
	}
