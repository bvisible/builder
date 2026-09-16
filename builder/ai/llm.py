"""Consolidated LLM adapter for Builder AI.

This is the ONLY place that knows about provider-specific quirks. The agent
loop and tools talk to LLMs exclusively through the functions defined here.
"""

import json
import logging
# //// Neoffice — for _loggable, which names a picture by its weight instead of logging its bytes
import re

import frappe
import litellm

from builder.ai.models import ModelRegistry

litellm.drop_params = True

logger = frappe.logger("builder.ai.llm")
logger.setLevel(logging.INFO)


# Transient failures worth retrying a streaming round: rate limits, 5xx, and
# connection/stream drops (incl. mid-stream resets). Matched by class name across the
# exception's MRO so subclasses — and both litellm and raw httpx transport errors — are
# covered without version-pinning exact types. Permanent errors (auth, bad request,
# content policy, not found) are deliberately absent: retrying them only burns tokens.
TRANSIENT_ERROR_NAMES = frozenset(
	{
		"RateLimitError",
		"Timeout",
		"TimeoutError",
		"APITimeoutError",
		"APIConnectionError",
		"InternalServerError",
		"ServiceUnavailableError",
		"RemoteProtocolError",
		"ReadError",
		"ReadTimeout",
		"ConnectError",
		"ConnectionError",
		"ChunkedEncodingError",
		"ProtocolError",
	}
)


def is_retryable(exc: BaseException) -> bool:
	"""True if this exception looks like a transient network/provider hiccup worth
	retrying. Walks the class MRO and matches by name (see TRANSIENT_ERROR_NAMES)."""
	return any(cls.__name__ in TRANSIENT_ERROR_NAMES for cls in type(exc).__mro__)


def loads_tolerant(raw: str) -> tuple[object | None, bool]:
	"""Parse tool-call argument JSON, tolerating the malformed JSON weaker models emit
	(single-quote delimiters, unescaped quotes, trailing commas, truncated/missing
	brackets). Strict json.loads first; on failure fall back to json_repair if available.
	Returns (parsed_or_None, was_repaired)."""
	raw = (raw or "").strip()
	if not raw:
		return None, False
	try:
		return json.loads(raw), False
	except json.JSONDecodeError:
		pass
	try:
		from json_repair import repair_json

		obj = repair_json(raw, return_objects=True)
		if obj not in ("", None, [], {}):
			return obj, True
	except Exception:
		pass
	return None, False


# Token/temperature budgets per task tier.
TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 40000, "temperature": 0.7},
	"clarify": {"max_tokens": 700, "temperature": 0.1},
	# 0.7 (not 0.3): the agent tier also composes the creative option cards
	# (layout directions, font pairings) — at 0.3 every session got the same
	# three flat options and the same famous fonts. Matches the "complex"
	# generation tier, which already proves 0.7 is safe for structured output.
	"agent": {"max_tokens": 16000, "temperature": 0.7},
}


def patch_messages_for_provider(model: str, messages: list[dict]) -> None:
	"""Anthropic via OpenRouter reads cache_control from INSIDE a content block, not
	from the message level (a message-level marker is silently ignored → full input
	price every turn). Relocate each marker set by the agent loop into the message's
	last content block for Claude models; strip markers entirely for other providers
	(their caching is implicit). Mutates in place."""
	claude = "claude-" in model
	for m in messages:
		marker = m.pop("cache_control", None)
		if not marker or not claude:
			continue
		content = m.get("content")
		if isinstance(content, str) or content is None:
			m["content"] = [{"type": "text", "text": content or "", "cache_control": marker}]
		elif isinstance(content, list) and content:
			content[-1] = {**content[-1], "cache_control": marker}


def provider_kwargs(model: str) -> dict:
	"""Pin Claude calls to the Anthropic route on OpenRouter: a fallback provider
	would silently drop the cache breakpoints and re-bill the whole prefix at full
	input price on every round."""
	if model.startswith("openrouter/") and "claude-" in model:
		return {"extra_body": {"provider": {"order": ["anthropic"], "allow_fallbacks": False}}}
	return {}


def reasoning_effort() -> str:
	"""//// Neoffice — how hard Kimi K3 thinks, from site_config `nora_reasoning_effort`
	(low / high / max). Measured on one page brief (2026-09-16): at its default "max" K3
	thought for 465 s before its first line and wrote the page in 550 s; at "high" 187 s and
	244 s, for the same four sections and fewer defects than the fast K2.7; at "low" 48 s but
	a thin page. "high" is the default: the site is built once, and it is built to be right."""
	try:
		value = str(frappe.conf.get("nora_reasoning_effort") or "").strip().lower()
	except Exception:
		value = ""
	return value if value in ("low", "high", "max") else "high"


def patch_params_for_provider(model: str, params: dict) -> dict:
	"""Moonshot's Kimi rejects every temperature but 1, so coerce it instead of
	failing the whole turn over a tuning knob."""
	if "kimi" in model and params.get("temperature") not in (None, 1):
		params = {**params, "temperature": 1}
	# //// Neoffice — K3's thinking is set per request (`reasoning_effort`, see reasoning_effort()
	# //// above); K2.x's `thinking` parameter is refused by K3, so nothing else is sent.
	if "kimi-k3" in model:
		extra = dict(params.get("extra_body") or {})
		extra.setdefault("reasoning_effort", reasoning_effort())
		params = {**params, "extra_body": extra}
	return params


# --- provider routing --------------------------------------------------------


def provider_overrides(info: dict) -> dict:
	"""The api_base configured on the model's Builder AI Provider, if any."""
	return {"api_base": info["api_base"]} if info.get("api_base") else {}


def route(model: str, api_key: str | None) -> tuple[str, dict, str | None]:
	"""Rewrite a registry model name into the call litellm should make.

	The name is `<route prefix>/<model id>`; the provider says which litellm
	provider to hand it to and where. OpenRouter maps to itself; any
	OpenAI-compatible gateway (OpenCode, Ollama, vLLM, a private proxy) maps to
	`openai/<id>` against the provider's api_base. Unknown models pass through
	untouched, so a hand-typed name still reaches litellm.
	"""
	info = ModelRegistry.find(model)
	if not info:
		return model, {}, api_key
	prefix = info.get("route_prefix") or ""
	model_id = model[len(prefix) + 1 :] if prefix and model.startswith(f"{prefix}/") else model
	litellm_provider = info.get("litellm_provider") or prefix
	overrides = provider_overrides(info)
	return f"{litellm_provider}/{model_id}", overrides, provider_api_key(info) or api_key


def codex_route(model: str) -> tuple[str, str] | None:
	"""(provider row, remote model id) when this model rides the ChatGPT Codex
	backend. That backend is OAuth plus Responses SSE, which litellm cannot
	speak, so complete()/complete_with_tools() hand these to builder.ai.codex."""
	info = ModelRegistry.find(model)
	if not info or (info.get("litellm_provider") or "").lower() != "codex":
		return None
	prefix = info.get("route_prefix") or ""
	model_id = model[len(prefix) + 1 :] if prefix and model.startswith(f"{prefix}/") else model
	return info["provider"], model_id


def provider_api_key(info: dict) -> str | None:
	"""The provider's own key, when it has one. Without one it falls back to the
	caller's (the OpenRouter key in Builder Settings)."""
	provider = info.get("provider")
	if not provider:
		return None
	try:
		return frappe.get_cached_doc("Builder AI Provider", provider).resolved_key()
	except Exception:
		return None


# //// Neoffice ▼▼▼ — an image is logged by its weight, not by its bytes (2026-09-15). Every call
# //// wrote the full prompt to disk, and a vision prompt carries its pictures as base64: one day's
# //// builds left 2.9 MB of rotated log, most of it a picture nobody will ever read from a text
# //// file. The size stays, because that is the part worth reading.
_BASE64_IMAGE = re.compile(r"data:(image/[a-z+]+);base64,([A-Za-z0-9+/=]+)")


def _loggable(content) -> str:
	"""The message as it goes to the log: pictures named by their weight."""
	text = str(content)
	return _BASE64_IMAGE.sub(lambda m: f"data:{m.group(1)};base64,<{len(m.group(2)) // 1024} kB elided>", text)


def complete(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	"""Plain completion. Returns the response iterator when streaming, else the
	text content. Transient failures are retried by litellm (and, for streaming
	rounds, by the agent loop's own retry layer — litellm can't fall back mid-stream)."""
	if target := codex_route(model):
		from builder.ai import codex

		return codex.complete(target[1], messages, params, provider=target[0], stream=stream)
	model, overrides, api_key = route(model, api_key)
	patch_messages_for_provider(model, messages)
	params = patch_params_for_provider(model, params)
	# //// Neoffice — a caller's own timeout wins (2026-09-16): a non-streamed call to a thinking
	# //// model (the site plan, the design brief) is minutes of reasoning before one answer, and
	# //// 120 s cut it every time. The provider passes what it was configured with (litellm_provider._params).
	timeout = int(params.pop("timeout", 0) or 0) or 120
	# //// Neoffice — _loggable: a vision prompt carries its pictures as base64, and logging those
	# //// bytes left megabytes of rotated log per build (2026-09-15)
	logger.info(
		f"LLM | model={model} stream={stream} params={params} timeout={timeout}\n"
		+ "\n".join(f"[{m['role']}] {_loggable(m['content'])}" for m in messages)
	)
	resp = litellm.completion(
		model=model,
		messages=messages,
		stream=stream,
		api_key=api_key,
		num_retries=1,
		# Read timeout (max stall between bytes, not total duration): a wedged
		# provider connection otherwise blocks the worker forever — the loop only
		# checks cancellation between chunks, so a silent stall is uncancellable.
		timeout=timeout,
		# Emit a final usage chunk while streaming so the loop can tally tokens per
		# turn (dropped automatically for providers that don't support it).
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**provider_kwargs(model),
		**overrides,
		**params,
	)
	if not stream:
		content = resp.choices[0].message.content or ""
		# //// Neoffice — every non-streamed call is counted here (builder/ai/meter.py, 2026-09-15):
		# //// this is the one place they all pass through, so it is the one place that can answer
		# //// "what did that build cost?". Streamed calls are added by their reader, which is the
		# //// only one that sees the final usage chunk.
		from builder.ai import meter

		meter.add(model, getattr(resp, "usage", None))
		logger.info(f"LLM response | length={len(content)}\n{content}")
		return content
	return resp


def complete_with_tools(
	model: str,
	messages: list,
	tools: list,
	params: dict,
	*,
	api_key: str | None = None,
	stream: bool = False,
):
	"""Tool-calling completion. Returns the raw response (iterator when streaming)."""
	if target := codex_route(model):
		from builder.ai import codex

		return codex.complete(target[1], messages, params, provider=target[0], tools=tools, stream=stream)
	model, overrides, api_key = route(model, api_key)
	patch_messages_for_provider(model, messages)
	params = patch_params_for_provider(model, params)
	# //// Neoffice — see complete(): a caller's timeout wins (2026-09-16)
	timeout = int(params.pop("timeout", 0) or 0) or 120
	logger.info(
		f"LLM tools | model={model} stream={stream} tools={[t['function']['name'] for t in tools]}\n"
		+ "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
	)
	resp = litellm.completion(
		model=model,
		messages=messages,
		tools=tools,
		stream=stream,
		api_key=api_key,
		num_retries=1,
		timeout=timeout,  # //// Neoffice — the caller's, see above  # see complete() — a stalled connection must fail, not wedge the turn
		# Final usage chunk while streaming — see complete().
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**provider_kwargs(model),
		**overrides,
		**params,
	)
	return resp
