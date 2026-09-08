# //// Neoffice — added file (no upstream equivalent): the sites and images a client likes, read
# //// for the site build. builder/site_ai/** = the Neoffice AI site generator.
"""Inspirations: the sites and images the client likes.

The old modal collected them (Builder Site Inspiration rows fed the brief); the Nora
playbook lost them in the move to the agent, and a link pasted in the chat reached
nobody (2026-09-08). They come back as tool arguments: every URL is screenshotted,
every picture read for its dominant colours, and the brief receives the pictures (the
vision pass) plus one line of findings per source. Each source is also kept as a
Builder Site Inspiration row, which the brief view lists."""

from __future__ import annotations

import json

import frappe
from frappe.utils import now

from builder.site_ai.logging import ai_log

MAX_SOURCES = 3
MAX_COLOURS = 4


def clean_list(value) -> list[str]:
    """Tool arguments arrive as a list, a JSON string or a comma-separated line."""
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                value = json.loads(text)
            except ValueError:
                value = [text]
        else:
            value = [part for part in text.replace("\n", ",").split(",")]
    out = []
    for item in value if isinstance(value, (list, tuple)) else [value]:
        item = str(item or "").strip().strip("<>")
        if item and item.lower() not in ("none", "null", "aucun", "skip", "-") and item not in out:
            out.append(item)
    return out


def _notes(analysis: dict) -> str:
    colours = [c.get("hex") for c in (analysis or {}).get("dominant_colors") or [] if c.get("hex")][:MAX_COLOURS]
    parts = []
    if colours:
        parts.append("colours " + ", ".join(colours))
    if (analysis or {}).get("is_dark_theme") is not None:
        parts.append("dark" if analysis.get("is_dark_theme") else "light")
    return ", ".join(parts)


def _analyse(file_url: str) -> dict:
    from builder.site_ai.inspiration.analyzer import DesignAnalyzer

    try:
        return DesignAnalyzer().analyze_from_file_url(file_url)
    except Exception as e:
        ai_log("warning", "Inspiration image not analysed", file=file_url, error=str(e)[:120])
        return {}


def read_url(url: str) -> dict:
    """A site the client likes: its above-the-fold look as a screenshot, and the colours."""
    from builder.site_ai.inspiration.screenshotter import capture_website_screenshot
    from builder.site_ai.inspiration.site_extractor import assert_public_http_url

    url = assert_public_http_url(url)
    shot = capture_website_screenshot(url, full_page=False)
    if not shot.get("success") or not shot.get("file_url"):
        raise RuntimeError(str(shot.get("error") or "screenshot failed"))
    analysis = _analyse(shot["file_url"])
    return {"kind": "URL", "source": url, "image": shot["file_url"], "analysis": analysis, "title": shot.get("title") or ""}


def read_image(file_url: str) -> dict:
    """A picture the client likes (uploaded through a card, or attached to a message)."""
    if not file_url.startswith(("/files/", "/private/files/")):
        raise ValueError("not a site file")
    return {"kind": "Image", "source": file_url, "image": file_url, "analysis": _analyse(file_url), "title": ""}


def _record(item: dict) -> None:
    """Keep the source as a Builder Site Inspiration row (best effort: the build must
    not fail on bookkeeping)."""
    try:
        if not frappe.db.exists("DocType", "Builder Site Inspiration"):
            return
        doc = frappe.get_doc(
            {
                "doctype": "Builder Site Inspiration",
                "source_type": item["kind"],
                "url": item["source"] if item["kind"] == "URL" else None,
                "image": item["source"] if item["kind"] == "Image" else None,
                "screenshot": item["image"] if item["kind"] == "URL" else None,
                "sentiment": "like",
                "status": "captured",
                "captured_at": now(),
                "analysis": json.dumps(item.get("analysis") or {}),
            }
        )
        doc.insert(ignore_permissions=True)
    except Exception as e:
        ai_log("warning", "Inspiration not recorded", source=item.get("source"), error=str(e)[:120])


def gather(urls: list[str], images: list[str], record: bool = True) -> dict:
    """Read every source (at most MAX_SOURCES of each kind). Returns the pictures for the
    vision pass, one line of findings per source, and the sources that could not be read."""
    found, failed = [], []
    for url in clean_list(urls)[:MAX_SOURCES]:
        try:
            found.append(read_url(url))
        except Exception as e:
            failed.append(f"{url} ({str(e)[:80]})")
            ai_log("warning", "Inspiration site not read", url=url, error=str(e)[:120])
    for image in clean_list(images)[:MAX_SOURCES]:
        try:
            found.append(read_image(image))
        except Exception as e:
            failed.append(f"{image} ({str(e)[:80]})")
    if record:
        for item in found:
            _record(item)
    notes = []
    for item in found:
        label = item["source"] if item["kind"] == "URL" else "picture"
        line = _notes(item.get("analysis"))
        notes.append(f"{label}: {line}" if line else label)
    return {"images": [item["image"] for item in found], "notes": notes, "failed": failed, "sources": found}


def describe(found: dict, model: str | None = None) -> str:
    """What the assistant can say about the sources: the measured colours, and when a
    vision model is at hand, three lines on the style of each picture."""
    lines = []
    for i, item in enumerate(found.get("sources") or [], 1):
        head = item["source"] if item["kind"] == "URL" else f"picture {item['source']}"
        note = _notes(item.get("analysis"))
        lines.append(f"{i}. {head}" + (f" — {note}" if note else ""))
    for failure in found.get("failed") or []:
        lines.append(f"Could not read {failure}.")
    if found.get("images") and model:
        try:
            from builder.site_ai.providers.litellm_provider import LiteLLMProvider

            provider = LiteLLMProvider(model=model)
            if provider.supports_vision():
                text = provider.generate(
                    "For each attached picture, in this order, give three short lines: palette (hex), typography feel, "
                    "layout pattern and mood. Number them. No preamble.",
                    images=found["images"][:MAX_SOURCES],
                    max_tokens=600,
                )
                if text and text.strip():
                    lines.append("Style read from the pictures:\n" + text.strip())
        except Exception as e:
            ai_log("warning", "Inspiration description failed", error=str(e)[:120])
    if not lines:
        return "No inspiration could be read."
    return "\n".join(lines) + "\nKeep these for generate_site (inspiration_urls / inspiration_images)."
