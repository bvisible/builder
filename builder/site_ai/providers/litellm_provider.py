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


# room for a thinking model's reasoning plus the JSON it is asked for (see generate_structured)
STRUCTURED_MAX_TOKENS = 40000


class LiteLLMProvider(BaseProvider):
    """`model` is a Builder AI Model name (e.g. managed/kimi-k3); routing, key and
    base URL come from its provider row. A bare model id (kimi-k3, the form the
    site_config keys and Builder Settings carry) is resolved against the enabled
    rows on first use."""

    @property
    def provider_name(self) -> str:
        return "litellm"

    def _resolve_model(self) -> str:
        from builder.ai.models import ModelRegistry, load_models

        wanted = (self.model or "").strip()
        if wanted and ModelRegistry.find(wanted):
            return wanted
        rows = load_models()
        if wanted:
            # the managed prefix first, then any row whose model_id is this bare id
            for row in rows:
                name = row.get("name") or ""
                if name == f"managed/{wanted}" or row.get("model_id") == wanted or name.endswith(f"/{wanted}"):
                    self.model = name
                    return name
        if rows:
            self.model = rows[0]["name"]
            return self.model
        raise GenerationError("No enabled AI model: configure a Builder AI Provider")

    def is_available(self) -> bool:
        """A registered, enabled Builder AI Model behind an enabled provider."""
        try:
            return bool(self._resolve_model())
        except GenerationError:
            return False

    def list_models(self) -> list[str]:
        from builder.ai.models import load_models

        return [m["name"] for m in load_models()]

    def _format_messages(self, prompt: str, system_prompt: str = None, images: list[str] = None) -> list[dict]:
        from builder.ai.models import ModelRegistry

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if images and ModelRegistry.supports_vision(self._resolve_model()):
            content = [{"type": "text", "text": prompt}]
            for url in images:
                data_url = self._image_to_data_url(url)
                if data_url:
                    content.append({"type": "image_url", "image_url": {"url": data_url}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def supports_vision(self) -> bool:
        """Whether the resolved model accepts images (Builder AI Model.supports_vision)."""
        from builder.ai.models import ModelRegistry

        try:
            return ModelRegistry.supports_vision(self._resolve_model())
        except GenerationError:
            return False

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
            self._resolve_model(),
            self._format_messages(prompt, system_prompt, images),
            self._params(temperature, max_tokens),
            stream=False,
        )

    def generate_structured(self, prompt, schema: type[T], system_prompt=None, temperature=None, images=None, **kwargs) -> T:
        """JSON mode with the full schema in the system prompt (the recipe the direct
        OpenAI-compatible provider used, which Moonshot answers reliably), pydantic
        validation, and one repair pass before the call counts as failed (the
        generators retry on failure)."""
        from builder.ai import llm

        schema_json = json.dumps(schema.model_json_schema(), indent=2, ensure_ascii=False)
        instruction = (
            "\n\nYou MUST respond with valid JSON that matches this exact schema:\n\n```json\n"
            + schema_json
            + "\n```\n\nIMPORTANT:\n- Respond ONLY with valid JSON, no explanations or markdown\n"
            "- All required fields must be present\n- Follow the exact structure and types specified: a field typed "
            "string never receives an object or a list\n- Use camelCase for all style properties (e.g., backgroundColor, not background-color)\n"
        )
        enhanced_system = f"{system_prompt}{instruction}" if system_prompt else instruction.strip()
        # a thinking model (Kimi K2.7) spends its reasoning inside max_tokens: at the
        # default 16k the design brief came back EMPTY ("Invalid JSON: EOF") whenever the
        # reasoning ran long, about one call in two (neoffice-maintenance #296)
        raw = llm.complete(
            self._resolve_model(),
            self._format_messages(prompt, enhanced_system, images),
            self._params(temperature, max(self.max_tokens or 0, STRUCTURED_MAX_TOKENS), json_mode=True),
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
                logger.warning("structured generation failed: %s / %s", str(first)[:400], str(second)[:200])
                raise GenerationError(f"Structured generation failed: {str(first)[:300]}") from second


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()
