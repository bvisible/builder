"""
AI Settings DocType
Manages AI provider configurations for Builder.
"""

import frappe
from frappe.model.document import Document


class AISettings(Document):
    def validate(self):
        """Validate AI settings"""
        self.validate_provider_config()
        self.validate_temperature()

    def validate_provider_config(self):
        """Ensure the selected provider is properly configured"""
        if self.default_provider == "ollama":
            if self.ollama_enabled and not self.ollama_base_url:
                frappe.throw("Ollama Base URL is required when Ollama is enabled")
            if self.ollama_enabled and not self.ollama_model:
                frappe.throw("Ollama Model is required when Ollama is enabled")

        elif self.default_provider == "openai":
            if self.openai_enabled and not self.openai_api_key:
                frappe.throw("OpenAI API Key is required when OpenAI is enabled")

        elif self.default_provider == "anthropic":
            if self.anthropic_enabled and not self.anthropic_api_key:
                frappe.throw("Anthropic API Key is required when Anthropic is enabled")

    def validate_temperature(self):
        """Ensure temperature is within valid range"""
        if self.temperature is not None:
            if self.temperature < 0 or self.temperature > 2:
                frappe.throw("Temperature must be between 0 and 2")

    def get_provider_config(self):
        """Get configuration for the current provider"""
        config = {
            "provider": self.default_provider,
            "temperature": self.temperature or 0.7,
            "max_retries": self.max_retries or 3,
        }

        if self.default_provider == "ollama":
            config.update({
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
                "num_ctx": self.ollama_num_ctx or 8192,
                "timeout": self.ollama_timeout or 120,
            })
        elif self.default_provider == "openai":
            config.update({
                "api_key": self.get_password("openai_api_key"),
                "model": self.openai_model,
                "organization": self.openai_organization,
            })
        elif self.default_provider == "anthropic":
            config.update({
                "api_key": self.get_password("anthropic_api_key"),
                "model": self.anthropic_model,
            })

        return config

    def get_generation_config(self):
        """Get generation-specific settings"""
        return {
            "enable_multi_pass": self.enable_multi_pass,
            "enable_rag": self.enable_rag,
            "enable_auto_fix": self.enable_auto_fix,
            "max_generation_retries": self.max_generation_retries or 3,
            "default_theme": self.default_theme or "modern",
            "default_site_type": self.default_site_type or "multi_page",
            "custom_system_prompt": self.custom_system_prompt,
            "debug_mode": self.debug_mode,
        }


@frappe.whitelist()
def test_ollama_connection():
    """Test connection to Ollama server"""
    settings = frappe.get_single("AI Settings")

    if not settings.ollama_enabled:
        return {"success": False, "message": "Ollama is not enabled"}

    try:
        from builder.ai.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

        if provider.is_available():
            models = provider.list_models()
            model_names = [m.get("name", "") for m in models]
            return {
                "success": True,
                "message": f"Connected to Ollama. Available models: {', '.join(model_names[:5])}",
                "models": model_names,
            }
        else:
            return {
                "success": False,
                "message": f"Ollama is running but model '{settings.ollama_model}' is not available. "
                           f"Run: ollama pull {settings.ollama_model}",
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to Ollama: {str(e)}",
        }


@frappe.whitelist()
def test_openai_connection():
    """Test connection to OpenAI API"""
    settings = frappe.get_single("AI Settings")

    if not settings.openai_enabled:
        return {"success": False, "message": "OpenAI is not enabled"}

    try:
        from builder.ai.providers.openai_provider import OpenAIProvider

        provider = OpenAIProvider(
            api_key=settings.get_password("openai_api_key"),
            model=settings.openai_model,
        )

        if provider.is_available():
            # Try a simple generation to verify
            response = provider.generate("Say 'Hello' in one word.", temperature=0)
            return {
                "success": True,
                "message": f"Connected to OpenAI. Model: {settings.openai_model}",
            }
        else:
            return {
                "success": False,
                "message": "OpenAI API key is not configured",
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to OpenAI: {str(e)}",
        }


@frappe.whitelist()
def pull_ollama_model(model: str = None):
    """Pull/download an Ollama model"""
    settings = frappe.get_single("AI Settings")
    model_to_pull = model or settings.ollama_model

    try:
        from builder.ai.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
        )

        success = provider.pull_model(model_to_pull)

        if success:
            return {
                "success": True,
                "message": f"Successfully pulled model: {model_to_pull}",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to pull model: {model_to_pull}",
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error pulling model: {str(e)}",
        }


@frappe.whitelist()
def get_available_models():
    """Get list of available models for each provider"""
    from builder.ai.config import RECOMMENDED_MODELS

    result = {
        "recommended": RECOMMENDED_MODELS,
        "ollama_available": [],
    }

    # Get Ollama models if enabled
    settings = frappe.get_single("AI Settings")
    if settings.ollama_enabled:
        try:
            from builder.ai.providers.ollama_provider import OllamaProvider

            provider = OllamaProvider(base_url=settings.ollama_base_url)
            models = provider.list_models()
            result["ollama_available"] = [m.get("name", "") for m in models]
        except Exception:
            pass

    return result
