"""
OpenAI Provider
Implements AI generation using OpenAI's API with structured output support.
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
    - Structured outputs with JSON mode
    - Response format enforcement
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        **kwargs
    ):
        super().__init__(
            model=model or self.DEFAULT_MODEL,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs
        )

        # Get API key from config if not provided
        if not self.api_key:
            self.api_key = frappe.conf.get("openai_api_key")

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        think: str = None,  # Ignored for OpenAI (no thinking mode)
    ) -> str:
        """Generate text response"""
        if not self.is_available():
            raise AuthenticationError("OpenAI API key not configured")

        messages = self._format_messages(prompt, system_prompt)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        try:
            response = self._make_request(payload)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            raise GenerationError(f"OpenAI generation failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = None,
        temperature: float = None,
        think: str = None,  # Ignored for OpenAI (no thinking mode)
    ) -> T:
        """
        Generate structured response using OpenAI's JSON mode.

        For newer models (gpt-4o, gpt-4o-mini), uses response_format with JSON schema.
        For older models, uses JSON mode with schema in prompt.
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
            "temperature": temperature or self.temperature,
            "max_tokens": self.max_tokens,
        }

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
            # Fallback to JSON mode
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
        """Check if current model supports structured outputs"""
        # Models that support JSON schema in response_format
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
        """Make HTTP request to OpenAI API"""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid OpenAI API key")
            elif response.status_code == 429:
                raise RateLimitError("OpenAI rate limit exceeded")
            elif response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", response.text)
                raise GenerationError(f"OpenAI API error ({response.status_code}): {error_msg}")

            return response.json()

        except requests.exceptions.Timeout:
            raise GenerationError(f"OpenAI request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise GenerationError(f"OpenAI request failed: {e}")

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (4 chars per token average)"""
        return len(text) // 4


__all__ = ["OpenAIProvider"]
