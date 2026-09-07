"""The site engine on upstream's LLM layer.

Every model call of the site engine (brief, page copy) goes through
`builder.ai.llm`, the same litellm route the editor agent uses, so a managed
instance, an OpenRouter key or a self-hosted gateway configure ONE thing: the
Builder AI Provider rows. This adapter keeps the BaseProvider contract the
generators were written against; the older direct providers stay only until
their last caller is gone.
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

import frappe
from pydantic import BaseModel, ValidationError

from builder.site_ai.providers.base import BaseProvider, GenerationError

T = TypeVar("T", bound=BaseModel)
logger = frappe.logger("builder.site_ai.litellm")
logger.setLevel(logging.INFO)


class LiteLLMProvider(BaseProvider):
    """`model` is a Builder AI Model name (e.g. managed/kimi-k3); routing, key and
    base URL come from its provider row."""

    @property
    def provider_name(self) -> str:
        return "litellm"

    def is_available(self) -> bool:
        """A registered, enabled Builder AI Model behind an enabled provider."""
        from builder.ai.models import ModelRegistry

        return bool(self.model and ModelRegistry.find(self.model))

    def list_models(self) -> list[str]:
        from builder.ai.models import load_models

        return [m["name"] for m in load_models()]

    def _format_messages(self, prompt: str, system_prompt: str = None, images: list[str] = None) -> list[dict]:
        from builder.ai.models import ModelRegistry

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if images and ModelRegistry.supports_vision(self.model):
            content = [{"type": "text", "text": prompt}]
            for url in images:
                data_url = self._image_to_data_url(url)
                if data_url:
                    content.append({"type": "image_url", "image_url": {"url": data_url}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _params(self, temperature: float = None, max_tokens: int = None, json_mode: bool = False) -> dict:
        params = {
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}
        return params

    def generate(self, prompt, system_prompt=None, temperature=None, max_tokens=None, images=None, **kwargs) -> str:
        from builder.ai import llm

        return llm.complete(
            self.model,
            self._format_messages(prompt, system_prompt, images),
            self._params(temperature, max_tokens),
            stream=False,
        )

    def generate_structured(self, prompt, schema: type[T], system_prompt=None, temperature=None, images=None, **kwargs) -> T:
        """JSON mode plus pydantic validation; a lightly broken document is repaired
        once before the call counts as failed (the generators retry on failure)."""
        from builder.ai import llm

        hint = (
            "\n\nReturn ONLY a JSON object matching this schema (no prose, no fences):\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)[:6000]
        )
        raw = llm.complete(
            self.model,
            self._format_messages(prompt + hint, system_prompt, images),
            self._params(temperature, None, json_mode=True),
            stream=False,
        )
        text = _strip_fences(raw)
        try:
            return schema.model_validate_json(text)
        except (ValidationError, ValueError) as first:
            try:
                import json_repair

                return schema.model_validate(json_repair.loads(text))
            except Exception as second:
                logger.warning("structured generation failed: %s / %s", str(first)[:200], str(second)[:200])
                raise GenerationError(f"Structured generation failed: {str(first)[:300]}") from second


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()
