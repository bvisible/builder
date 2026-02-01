"""
Ollama Provider
Implements AI generation using Ollama's local API with structured output support.

Ollama 0.5+ supports structured outputs via JSON schema constraints using GBNF grammars.
This ensures nearly 100% valid JSON output.
"""

import json
from typing import TypeVar, Optional
from pydantic import BaseModel
import frappe

from builder.ai.providers.base import (
    BaseProvider,
    GenerationError,
    ValidationError,
)

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(BaseProvider):
    """
    Ollama provider with support for:
    - Local LLM inference
    - Structured outputs via JSON schema (Ollama 0.5+)
    - Multiple models (qwen2.5, llama3.2, mistral, deepseek, etc.)

    Recommended models for JSON generation:
    - qwen2.5:7b - Best for structured output
    - qwen2.5:32b - Higher quality, slower
    - llama3.2:8b - Good all-around
    - deepseek-coder:6.7b - Good for code/structure
    """

    DEFAULT_MODEL = "qwen2.5:7b"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        num_ctx: int = 8192,
        **kwargs
    ):
        super().__init__(
            model=model or self.DEFAULT_MODEL,
            base_url=base_url or self.DEFAULT_BASE_URL,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs
        )
        self.num_ctx = num_ctx

        # Override from Frappe config if available
        if not base_url:
            self.base_url = frappe.conf.get("ollama_base_url", self.DEFAULT_BASE_URL)
        if not api_key:
            self.api_key = frappe.conf.get("ollama_api_key")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available"""
        try:
            import requests
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.base_url}/api/tags",
                headers=headers,
                timeout=5
            )
            if response.status_code != 200:
                return False

            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check for exact match or partial match (model:tag)
            base_model = self.model.split(":")[0]
            return any(
                self.model in name or base_model in name
                for name in model_names
            )
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """Generate text response"""
        messages = self._format_messages(prompt, system_prompt)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
                "num_ctx": self.num_ctx,
            },
        }

        try:
            response = self._make_request("/api/chat", payload)
            return response.get("message", {}).get("content", "")
        except Exception as e:
            raise GenerationError(f"Ollama generation failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = None,
        temperature: float = None,
    ) -> T:
        """
        Generate structured response using Ollama's JSON schema support.

        Ollama 0.5+ uses GBNF grammars to constrain output to valid JSON
        matching the provided schema. This provides near-100% valid JSON.
        """
        # Build enhanced system prompt
        schema_dict = schema.model_json_schema()
        enhanced_system = self._build_structured_system_prompt(
            system_prompt,
            schema_dict
        )

        messages = self._format_messages(prompt, enhanced_system)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema_dict,  # Ollama 0.5+ JSON schema constraint
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": self.num_ctx,
            },
        }

        try:
            response = self._make_request("/api/chat", payload)
            content = response.get("message", {}).get("content", "")

            if not content:
                raise GenerationError("Empty response from Ollama")

            return self._validate_response(content, schema)

        except ValidationError:
            raise
        except Exception as e:
            raise GenerationError(f"Ollama structured generation failed: {e}")

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
    ) -> dict:
        """
        Generate JSON response without schema validation.
        Uses Ollama's basic JSON mode.
        """
        enhanced_system = system_prompt or ""
        enhanced_system += "\n\nYou MUST respond with valid JSON only. No explanations."

        messages = self._format_messages(prompt, enhanced_system)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",  # Basic JSON mode
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": self.num_ctx,
            },
        }

        try:
            response = self._make_request("/api/chat", payload)
            content = response.get("message", {}).get("content", "")
            return json.loads(self._extract_json_from_response(content))
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON from Ollama: {e}")
        except Exception as e:
            raise GenerationError(f"Ollama JSON generation failed: {e}")

    def _build_structured_system_prompt(
        self,
        base_prompt: str,
        schema_dict: dict
    ) -> str:
        """Build system prompt optimized for structured output"""
        # Simplify schema for prompt (remove $defs, descriptions)
        simplified = self._simplify_schema_for_prompt(schema_dict)

        schema_instruction = f"""
You are a JSON generator. You MUST respond with valid JSON matching this structure:

{json.dumps(simplified, indent=2)}

CRITICAL RULES:
1. Output ONLY valid JSON - no explanations, no markdown, no code blocks
2. Use camelCase for CSS properties (backgroundColor, not background-color)
3. All strings must be properly escaped
4. Arrays must use proper JSON syntax
5. Include all required fields
"""
        if base_prompt:
            return f"{base_prompt}\n\n{schema_instruction}"
        return schema_instruction

    def _simplify_schema_for_prompt(self, schema: dict) -> dict:
        """Simplify JSON schema for better LLM understanding"""
        # Remove verbose metadata that confuses LLMs
        keys_to_remove = ["$defs", "definitions", "description", "title", "default"]

        def clean(obj):
            if isinstance(obj, dict):
                return {
                    k: clean(v)
                    for k, v in obj.items()
                    if k not in keys_to_remove
                }
            elif isinstance(obj, list):
                return [clean(item) for item in obj]
            return obj

        return clean(schema)

    def _make_request(self, endpoint: str, payload: dict) -> dict:
        """Make HTTP request to Ollama API"""
        import requests

        url = f"{self.base_url}{endpoint}"

        # Build headers with optional API key (for Cloudflare WAF or remote servers)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                error_text = response.text[:500]
                raise GenerationError(
                    f"Ollama API error ({response.status_code}): {error_text}"
                )

            return response.json()

        except requests.exceptions.ConnectionError:
            raise GenerationError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (ollama serve)."
            )
        except requests.exceptions.Timeout:
            raise GenerationError(
                f"Ollama request timed out after {self.timeout}s. "
                "Try a smaller model or increase timeout."
            )
        except requests.exceptions.RequestException as e:
            raise GenerationError(f"Ollama request failed: {e}")

    def pull_model(self, model: str = None) -> bool:
        """
        Pull/download a model from Ollama registry.

        Args:
            model: Model name to pull (defaults to configured model)

        Returns:
            bool: True if successful
        """
        import requests

        model_to_pull = model or self.model
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_to_pull},
                headers=headers,
                timeout=600,  # Models can take a while to download
                stream=True,
            )

            if response.status_code != 200:
                return False

            # Stream the download progress
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "error" in data:
                        frappe.log_error(f"Ollama pull error: {data['error']}")
                        return False

            return True

        except Exception as e:
            frappe.log_error(f"Failed to pull model {model_to_pull}: {e}")
            return False

    def list_models(self) -> list[dict]:
        """List available models on the Ollama server"""
        import requests

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except Exception:
            return []

    def get_model_info(self, model: str = None) -> Optional[dict]:
        """Get information about a specific model"""
        import requests

        model_name = model or self.model
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None


# Recommended models for different tasks
OLLAMA_RECOMMENDED_MODELS = {
    "structured_output": {
        "best": "qwen2.5:32b",
        "balanced": "qwen2.5:7b",
        "fast": "qwen2.5:3b",
        "description": "Qwen 2.5 excels at following JSON schemas"
    },
    "creative": {
        "best": "llama3.2:8b",
        "balanced": "llama3.2:3b",
        "description": "Llama 3.2 offers good creativity"
    },
    "code": {
        "best": "deepseek-coder:33b",
        "balanced": "deepseek-coder:6.7b",
        "fast": "deepseek-coder:1.3b",
        "description": "DeepSeek Coder for code/structure tasks"
    },
    "general": {
        "best": "mistral:7b",
        "balanced": "mistral-nemo:latest",
        "description": "Mistral for general tasks"
    },
}


__all__ = [
    "OllamaProvider",
    "OLLAMA_RECOMMENDED_MODELS",
]
