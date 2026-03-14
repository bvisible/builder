"""
OpenAI Provider
Implements AI generation using OpenAI's API with structured output support.
Also supports OpenAI-compatible APIs (Moonshot, etc.) via custom base_url.
"""

import json
from typing import TypeVar
from pydantic import BaseModel
import frappe
from frappe.utils import cint

from builder.ai.providers.base import (
    BaseProvider,
    GenerationError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider with support for:
    - GPT-4o, GPT-4o-mini, GPT-3.5-turbo
    - OpenAI-compatible APIs (Moonshot, etc.) via base_url
    - Structured outputs with JSON mode
    - Response format enforcement
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_API_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        timeout: int = None,
        **kwargs
    ):
        # Detect if using a custom API (not native OpenAI)
        cleaned_base_url = (base_url or "").rstrip("/") if base_url else None
        is_custom_api = bool(cleaned_base_url) and "openai.com" not in (cleaned_base_url or "")

        # Higher defaults for custom APIs (Moonshot pages = large JSON)
        default_max_tokens = 32768 if is_custom_api else 4096
        default_timeout = 900 if is_custom_api else 120

        super().__init__(
            model=model or self.DEFAULT_MODEL,
            api_key=api_key,
            base_url=cleaned_base_url,
            temperature=temperature,
            max_tokens=max_tokens or default_max_tokens,
            timeout=timeout or default_timeout,
            **kwargs
        )

        # Get API key from config if not provided
        if not self.api_key:
            self.api_key = frappe.conf.get("openai_api_key")

    @property
    def _api_url(self) -> str:
        """Get the chat completions endpoint URL."""
        base = self.base_url or self.DEFAULT_API_URL
        return f"{base}/chat/completions"

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.api_key)

    @property
    def _is_reasoning_model(self) -> bool:
        """Check if model supports thinking/reasoning mode (kimi-k2.5, kimi-k2)."""
        reasoning_models = ["kimi-k2.5", "kimi-k2"]
        model_lower = (self.model or "").lower()
        return any(m in model_lower for m in reasoning_models)

    @property
    def _fixed_temperature(self) -> bool:
        """Check if model requires fixed temperature (reasoning models)."""
        return self._is_reasoning_model

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        think: bool | str = None,
    ) -> str:
        """Generate text response"""
        if not self.is_available():
            raise AuthenticationError("OpenAI API key not configured")

        messages = self._format_messages(prompt, system_prompt)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 1 if self._fixed_temperature else (temperature or self.temperature),
            "max_tokens": max_tokens or self.max_tokens,
        }

        # Enable thinking for reasoning models (kimi-k2.5, kimi-k2)
        if self._is_reasoning_model and think is not False:
            payload["think"] = True

        try:
            response = self._make_request(payload)
            message = response["choices"][0]["message"]
            content = message.get("content") or ""
            # Reasoning models may put all output in reasoning_content when max_tokens is too low
            if not content.strip() and message.get("reasoning_content"):
                content = message["reasoning_content"]
            return content
        except Exception as e:
            raise GenerationError(f"OpenAI generation failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = None,
        temperature: float = None,
        think: bool | str = None,
    ) -> T:
        """
        Generate structured response using JSON mode.

        For native OpenAI models (gpt-4o, gpt-4o-mini), uses response_format with JSON schema.
        For custom APIs (Moonshot/kimi), uses JSON mode with schema in prompt.
        Reasoning models (kimi-k2.5) get thinking enabled for deeper analysis.
        """
        if not self.is_available():
            raise AuthenticationError("OpenAI API key not configured")

        # Build enhanced system prompt with schema
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        enhanced_system = self._build_structured_system_prompt(
            system_prompt,
            schema_json
        )

        messages = self._format_messages(prompt, enhanced_system)

        # Determine if model supports structured outputs
        supports_structured = self._supports_structured_outputs()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 1 if self._fixed_temperature else (temperature or self.temperature),
            "max_tokens": self.max_tokens,
        }

        # Enable thinking for reasoning models (kimi-k2.5, kimi-k2)
        if self._is_reasoning_model and think is not False:
            payload["think"] = True

        if supports_structured:
            # Use OpenAI's native JSON schema support
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                }
            }
        else:
            # Fallback to JSON mode (works with Moonshot and other compatible APIs)
            payload["response_format"] = {"type": "json_object"}

        try:
            response = self._make_request(payload)
            content = response["choices"][0]["message"]["content"]
            return self._validate_response(content, schema)
        except ValidationError:
            raise
        except Exception as e:
            raise GenerationError(f"OpenAI structured generation failed: {e}")

    def _supports_structured_outputs(self) -> bool:
        """Check if current model supports strict JSON schema in response_format."""
        # Only native OpenAI models support strict JSON schema
        if self.base_url and "openai.com" not in self.base_url:
            return False

        structured_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4o-2024",
            "gpt-4-turbo",
        ]
        return any(m in self.model for m in structured_models)

    def _build_structured_system_prompt(
        self,
        base_prompt: str,
        schema_json: str
    ) -> str:
        """Build system prompt with JSON schema instructions"""
        schema_instruction = f"""
You MUST respond with valid JSON that matches this exact schema:

```json
{schema_json}
```

IMPORTANT:
- Respond ONLY with valid JSON, no explanations or markdown
- All required fields must be present
- Follow the exact structure and types specified
- Use camelCase for all style properties (e.g., backgroundColor, not background-color)
"""
        if base_prompt:
            return f"{base_prompt}\n\n{schema_instruction}"
        return schema_instruction

    def _make_request(self, payload: dict) -> dict:
        """Make HTTP request to OpenAI-compatible API"""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self._api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            elif response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", response.text)
                raise GenerationError(f"API error ({response.status_code}): {error_msg}")

            return response.json()

        except requests.exceptions.Timeout:
            raise GenerationError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise GenerationError(f"Request failed: {e}")

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (4 chars per token average)"""
        return len(text) // 4


__all__ = ["OpenAIProvider"]
