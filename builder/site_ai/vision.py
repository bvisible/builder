# //// Neoffice — added file (no upstream equivalent): one call that describes a photo for its alt
# //// text (SEO / GEO plan, D-11). The webshop proposes an alt text for each product photo and the
# //// merchant decides; this is the one place that picks the model that reads the photo.
"""Describe a photo in one sentence, for its alt text.

Nora Vision reads first: the host's own endpoint, free and fast (about 3 s a photo against 57 s
for Kimi K2.6, measured on osiris). Without it, the builder's general model reads, provided it
sees images. Call it from a background job: a fallback model can think for a minute.

Under the provider, two drops are silent, and each would have the model describe a photo it never
received: an image that cannot be loaded is left out of the message, and a model that cannot see
gets the prompt alone. Both are checked here before the call, and every way of coming back
without a description raises its own exception, so the caller can tell the merchant which one.

Not an endpoint: the caller decides which images reach it. A /private/files/ path is read from
disk, so pass only images the person asking may see."""

from __future__ import annotations

import re
import time

import frappe

from builder.site_ai.logging import ai_log

#: Screen readers read an alt text in one go; the usual advice is to stay near 125 characters.
ALT_TARGET_LENGTH = 125
#: Beyond this, the answer is cut at a word: an alt text is one sentence, never a paragraph.
ALT_MAX_LENGTH = 180
#: Nora answers in seconds; a fallback model thinks before it answers.
VISION_TIMEOUT = 120

SYSTEM_PROMPT = (
    "You write the alt text of photos on a website, for people who cannot see them.\n"
    "- Say what the photo shows: the object, its colour and material, how it is seen, "
    "and what is happening if anything is.\n"
    "- Name the product with the words the shop gives you. Never add a brand, a model, "
    "a text or a detail that the photo does not show.\n"
    f"- One sentence of at most {ALT_TARGET_LENGTH} characters. No \"photo of\" or "
    "\"image of\", no praise, no price, no quotation marks.\n"
    "- Answer with the alt text alone."
)

_LABEL = re.compile(r"^(alt(ernative)?(\s+text)?|texte\s+alternatif|description)\s*:\s*", re.IGNORECASE)
_QUOTES = "\"'“”„«»‘’`"


class DescribeImageError(Exception):
    """Why no description came back. `reason` is a stable code: the caller maps it to its own
    sentence for the merchant."""

    reason = "failed"


class NoVisionModel(DescribeImageError):
    """No registered model on this site reads images: every photo comes back the same."""

    reason = "no_vision_model"


class ImageUnreadable(DescribeImageError):
    """This photo could not be loaded: a missing file, a dead link, a format nobody reads."""

    reason = "image_unreadable"


class DescriptionFailed(DescribeImageError):
    """The model was asked and gave nothing usable: an error, a timeout, an empty answer."""

    reason = "model_failed"


def describe_image(image: str, context: str = "", language: str | None = None) -> str:
    """One sentence that says what the photo shows, for its alt text.

    `image`: a file of the site (/files/…, /private/files/… or its absolute URL), an http(s)
    URL or a data: URL. `context`: what the caller knows about the subject (product name,
    brand, colour); the model names the product from it and describes only what it sees.
    `language`: an ISO code ("fr"); the site's language when omitted.

    Raises NoVisionModel, ImageUnreadable or DescriptionFailed, all DescribeImageError."""
    provider, model = vision_provider()
    data_url = encode_image(image)
    language = (language or site_language()).strip()
    started = time.monotonic()
    try:
        answer = provider.generate(describe_prompt(context, language), system_prompt=SYSTEM_PROMPT, images=[data_url])
    except Exception as e:
        ai_log("warning", "Image not described", reason=DescriptionFailed.reason, model=model, error=str(e)[:160])
        raise DescriptionFailed(str(e)[:160]) from e
    text = clean_alt_text(answer)
    if not text:
        ai_log("warning", "Image not described", reason=DescriptionFailed.reason, model=model, error="empty answer")
        raise DescriptionFailed("empty answer")
    ai_log("info", "Image described", model=model, language=language, chars=len(text), seconds=round(time.monotonic() - started, 1))
    return text


def vision_provider():
    """(provider, model name) of the first model that reads images: Nora Vision, then the
    builder's general model. NoVisionModel when neither sees."""
    from builder.site_ai.config import get_ai_settings
    from builder.site_ai.managed import nora_vision_model
    from builder.site_ai.providers import get_provider

    candidates = [nora_vision_model()]
    try:
        candidates.append(get_ai_settings().model)
    except Exception as e:
        ai_log("warning", "AI settings not read for vision", error=str(e)[:160])
    for model in candidates:
        if not model:
            continue
        provider = get_provider("litellm", model=model, temperature=0.2, timeout=VISION_TIMEOUT)
        if provider.supports_vision():
            return provider, model
    ai_log("warning", "Image not described", reason=NoVisionModel.reason, tried=", ".join(m for m in candidates if m) or "none")
    raise NoVisionModel("no registered model reads images")


def encode_image(image: str) -> str:
    """The photo as a data URL, read before the call: the provider would drop an unreadable
    image without a word and send the prompt alone."""
    from builder.site_ai.providers.base import BaseProvider

    data_url = BaseProvider._image_to_data_url(image) if image else None
    if not data_url:
        ai_log("warning", "Image not described", reason=ImageUnreadable.reason, image=str(image)[:160])
        raise ImageUnreadable(f"could not read {str(image)[:160]}")
    return data_url


def site_language() -> str:
    """The site's language (System Settings), English when unset."""
    return frappe.db.get_single_value("System Settings", "language") or "en"


def describe_prompt(context: str, language: str) -> str:
    """The request: the language, by name and code, and what the shop knows about the subject."""
    name = frappe.db.get_value("Language", language, "language_name") or language
    prompt = f"Write the alt text of this photo in {name} (language code: {language})."
    context = (context or "").strip()
    if context:
        prompt += f"\n\nWhat the shop knows about it, to name the product:\n{context[:1000]}"
    return prompt


def clean_alt_text(answer) -> str:
    """The answer as one clean sentence: the first line that says something, without a label or
    surrounding quotes, cut at a word past ALT_MAX_LENGTH."""
    for line in str(answer or "").splitlines():
        text = " ".join(_LABEL.sub("", line.strip()).split())
        if len(text) > 1 and text[0] in _QUOTES and text[-1] in _QUOTES:
            text = text[1:-1].strip()
        if text:
            break
    else:
        return ""
    if len(text) > ALT_MAX_LENGTH:
        text = text[:ALT_MAX_LENGTH].rsplit(" ", 1)[0].rstrip(" ,;:-–—")
    return text
