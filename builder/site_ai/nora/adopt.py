# //// Neoffice — added file (no upstream equivalent): a site that predates the design system adopts it.
"""Adopt the design system on an existing site.

A site built before 1.33 (the old generator, or by hand) carries its palette as
hex literals in every block, and its chrome has no token prefix: the Design
Tokens do nothing for it and a retheme means editing pages. Adoption does
three things, all idempotent:

1. mint the six tokens (`<prefix>-primary … font-body`) from the chrome's own
   colour and font fields (mint_tokens, the same call the site build makes);
2. point the chrome at them (`token_prefix`), so theme_variables.html aliases
   its variables on the tokens and the Theme pane keeps them in step;
3. rewrite the pages: a literal equal to a palette colour becomes its handle
   (`#1c3d52` → `var(--gf-primary)`), a font family equal to a chrome font
   becomes its handle. Visually a no-op today; from then on the tokens drive
   the site.

Semantics are kept conservative: primary and secondary are replaced wherever
they appear, the background colour only where it paints a background, the
text colour only where it colours text. White used as copy on a dark band is
not "the background" and stays a literal.

The rewrite is a pure function (rewrite_blocks) so it is unit-tested; the
frappe parts are in adopt_design_system, run from the patch, bench execute or
the whitelisted endpoint."""

from __future__ import annotations

import json
import re

HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
BACKGROUND_PROPS = ("backgroundColor", "background", "backgroundImage", "hoverBackgroundColor")
TEXT_PROPS = ("color", "hoverColor", "textDecorationColor", "caretColor")
PALETTE_KEYS = ("primary", "secondary", "background", "text")


def normalise_hex(value: str) -> str | None:
    """#ABC / #aabbcc → #aabbcc (lower-case), None for anything else."""
    value = (value or "").strip().lower()
    if not HEX.fullmatch(value):
        return None
    if len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    return value


def _allowed_keys(prop: str) -> tuple[str, ...]:
    if prop in BACKGROUND_PROPS:
        return ("primary", "secondary", "background")
    if prop in TEXT_PROPS:
        return ("primary", "secondary", "text")
    return ("primary", "secondary")


def _first_family(value: str) -> str:
    first = (value or "").split(",")[0].strip()
    return first.strip("'\"").strip().lower()


def rewrite_styles(styles: dict, prefix: str, palette: dict[str, str], fonts: dict[str, str]) -> int:
    """Rewrite one style dict in place. `palette` maps key → normalised hex,
    `fonts` maps key (font-heading / font-body) → family name. Returns the
    number of values changed."""
    changed = 0
    by_hex = {}
    for key in PALETTE_KEYS:
        value = normalise_hex(palette.get(key, ""))
        if value:
            by_hex.setdefault(value, key)
    for prop, value in list(styles.items()):
        if not isinstance(value, str) or not value.strip():
            continue
        if prop == "fontFamily":
            family = _first_family(value)
            for key, name in fonts.items():
                if name and family == name.strip().lower():
                    rest = value.split(",", 1)
                    tail = f", {rest[1].strip()}" if len(rest) > 1 and rest[1].strip() else ""
                    styles[prop] = f"var(--{prefix}-{key}){tail}"
                    changed += 1
                    break
            continue
        if "#" not in value:
            continue
        allowed = _allowed_keys(prop)

        def swap(match: re.Match) -> str:
            nonlocal changed
            key = by_hex.get(normalise_hex(match.group(0)))
            if key and key in allowed:
                changed += 1
                return f"var(--{prefix}-{key})"
            return match.group(0)

        new_value = HEX.sub(swap, value)
        if new_value != value:
            styles[prop] = new_value
    return changed


def rewrite_blocks(blocks: list, prefix: str, palette: dict[str, str], fonts: dict[str, str]) -> int:
    """Rewrite a block tree in place; returns the number of values changed."""
    changed = 0
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        for key in STYLE_KEYS:
            styles = block.get(key)
            if isinstance(styles, dict):
                changed += rewrite_styles(styles, prefix, palette, fonts)
        changed += rewrite_blocks(block.get("children") or [], prefix, palette, fonts)
    return changed


def adopt_design_system(website_profile: str | None = None, dry_run: bool = False) -> dict:
    """Mint the tokens from the chrome, set its token_prefix, rewrite its pages.
    Returns a report. Safe to run again: the tokens are refreshed to the chrome
    values, an already-rewritten page changes nothing."""
    import frappe

    from builder.api import _blocks_fingerprint, _get_site_chrome_config
    from builder.site_ai.nora.site_builder import _color, mint_tokens, palette_values, token_prefix

    config = _get_site_chrome_config(website_profile)
    palette = {
        "primary": _color(config.get("primary_color"), fallback=""),
        "secondary": _color(config.get("secondary_color"), fallback=""),
        "background": _color(config.get("background_color"), fallback=""),
        "text": _color(config.get("text_color"), fallback=""),
    }
    if not palette["primary"]:
        return {"profile": website_profile, "skipped": "no primary colour on the chrome"}
    label = website_profile or config.get("logo_text") or frappe.db.get_single_value("Website Settings", "app_name") or "site"
    prefix = (config.get("token_prefix") or "").strip() or token_prefix(label)
    fonts = {"font-heading": config.get("heading_font") or "", "font-body": config.get("body_font") or ""}

    class _Brief:  # what mint_tokens reads: the chrome's own values
        primary_color = palette["primary"]
        secondary_color = palette["secondary"]
        section_backgrounds = [palette["background"]] if palette["background"] else []
        body_color = palette["text"]
        heading_color = palette["text"]
        heading_font = fonts["font-heading"]
        body_font = fonts["font-body"]

    if not dry_run:
        mint_tokens(prefix, label, _Brief(), palette["primary"], palette["secondary"])
        if (config.get("token_prefix") or "") != prefix:
            config.token_prefix = prefix
            config.flags.skip_token_sync = True
            config.flags.ignore_permissions = True
            config.save()
        palette = {k: v for k, v in ((key, palette_values(prefix).get(f"{prefix}-{key}")) for key in PALETTE_KEYS) if v}

    filters = {"is_template": 0}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        filters["neo_website_profile"] = website_profile if website_profile else ("is", "not set")
    pages = frappe.get_all("Builder Page", filters=filters, fields=["name", "ai_generated_at"])
    report = {"profile": website_profile, "prefix": prefix, "palette": palette, "fonts": fonts, "pages": 0, "pages_changed": 0, "values": 0, "dry_run": dry_run}
    for page in pages:
        report["pages"] += 1
        page_changed = 0
        updates = {}
        for field in ("blocks", "draft_blocks"):
            raw = frappe.db.get_value("Builder Page", page.name, field)
            if not raw:
                continue
            try:
                blocks = json.loads(raw)
            except ValueError:
                continue
            n = rewrite_blocks(blocks if isinstance(blocks, list) else [blocks], prefix, palette, fonts)
            if n:
                page_changed += n
                updates[field] = json.dumps(blocks, ensure_ascii=False)
        if page_changed:
            report["pages_changed"] += 1
            report["values"] += page_changed
            if not dry_run:
                if page.ai_generated_at and updates.get("draft_blocks" if "draft_blocks" in updates else "blocks"):
                    stored = updates.get("draft_blocks") or updates.get("blocks")
                    updates["ai_blocks_hash"] = _blocks_fingerprint(stored)
                frappe.db.set_value("Builder Page", page.name, updates, update_modified=False)
    if not dry_run:
        frappe.db.commit()
        try:
            config.clear_website_cache()
        except Exception:
            pass
    return report


def adopt_everywhere(dry_run: bool = False) -> list[dict]:
    """The main site, then every profile that has a chrome variant."""
    import frappe

    reports = [adopt_design_system(None, dry_run=dry_run)]
    if frappe.db.exists("DocType", "Website Header Footer Variant"):
        for name in frappe.get_all("Website Header Footer Variant", pluck="name"):
            reports.append(adopt_design_system(name, dry_run=dry_run))
    return reports
