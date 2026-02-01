"""
Base Provider Interface
Abstract base class for all AI providers.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Optional
from pydantic import BaseModel
import json

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass


class AuthenticationError(ProviderError):
    """Authentication failed"""
    pass


class GenerationError(ProviderError):
    """Generation failed"""
    pass


class ValidationError(ProviderError):
    """Response validation failed"""
    pass


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.
    All providers must implement these methods.
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra_config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'ollama')"""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        Generate a text response from the model.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            str: Generated text response
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = None,
        temperature: float = None,
    ) -> T:
        """
        Generate a structured response matching the Pydantic schema.

        Args:
            prompt: User prompt
            schema: Pydantic model class for response structure
            system_prompt: Optional system prompt
            temperature: Override default temperature

        Returns:
            T: Validated Pydantic model instance
        """
        pass

    def generate_with_retry(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = None,
        max_retries: int = 3,
        temperature_increment: float = 0.15,
    ) -> T:
        """
        Generate with automatic retry on failure.
        Temperature increases with each retry for more diverse outputs.

        Args:
            prompt: User prompt
            schema: Pydantic model class
            system_prompt: Optional system prompt
            max_retries: Maximum retry attempts
            temperature_increment: Temperature increase per retry

        Returns:
            T: Validated Pydantic model instance

        Raises:
            GenerationError: If all retries fail
        """
        last_error = None
        base_temp = self.temperature

        for attempt in range(max_retries):
            try:
                # Increase temperature slightly with each retry
                temp = min(base_temp + (attempt * temperature_increment), 1.0)
                return self.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=system_prompt,
                    temperature=temp,
                )
            except (ValidationError, GenerationError) as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                continue

        raise GenerationError(
            f"Generation failed after {max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _format_messages(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> list[dict]:
        """Format prompt into message list"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON from a response that might contain markdown code blocks.

        Args:
            response: Raw response text

        Returns:
            str: Cleaned JSON string
        """
        text = response.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            # Find the end of the first line (language specifier)
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]

            # Remove closing ```
            if text.endswith("```"):
                text = text[:-3]

        text = text.strip()

        # Try to find JSON object or array
        if not (text.startswith("{") or text.startswith("[")):
            # Look for JSON in the text
            start_obj = text.find("{")
            start_arr = text.find("[")

            if start_obj == -1 and start_arr == -1:
                raise ValidationError(f"No JSON found in response: {text[:200]}")

            if start_obj == -1:
                start = start_arr
            elif start_arr == -1:
                start = start_obj
            else:
                start = min(start_obj, start_arr)

            text = text[start:]

        return text

    def _validate_response(self, response: str, schema: type[T]) -> T:
        """
        Validate and parse response into Pydantic model.

        Args:
            response: JSON response string
            schema: Pydantic model class

        Returns:
            T: Validated model instance

        Raises:
            ValidationError: If validation fails
        """
        try:
            cleaned = self._extract_json_from_response(response)
            return schema.model_validate_json(cleaned)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValidationError(f"Validation failed: {e}")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass

    def get_info(self) -> dict:
        """Get provider information"""
        return {
            "provider": self.provider_name,
            "model": self.model,
            "base_url": self.base_url,
            "available": self.is_available(),
        }


__all__ = [
    "BaseProvider",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "GenerationError",
    "ValidationError",
]
