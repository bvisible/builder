# //// Neoffice — added file (no upstream equivalent): the site plan, decided once by the strong model.
"""The site plan: what every page is made of, decided ONCE for the whole site, by the model
that thinks best, from everything the client gave — the logo, the reference sites and
pictures, their own photographs and what the vision read in them, the categories and brands
they named — and from the design brief already written.

Why it exists (2026-09-16). The brief was a contract of STYLE — concept, signature element,
tone, colours, buttons, type — and the sections of each page came from a fixed list in the
code. The page writer received prose ("soft editorial, a sage arch behind the headlines")
and had to invent the geometry of every page on its own, one page at a time, without
seeing the others. That is the hardest task of the whole pipeline, and it was given to the
step that reasons least. Six page tops came out six ways; a contact page starved its own
title; the same ornament bled out of three sections.

The plan puts the thinking where it pays: per page, an ordered list of sections with a
TYPE from a closed vocabulary, what each says, how it is laid out, which of the client's
photographs it takes and which live component carries it; and for the site, the concrete
geometry of the signature move, the rhythm, and what every interior page opens with. The
writer then executes a plan instead of designing a page. When the plan cannot be written
the static plans of site_builder apply, as before.
"""

from __future__ import annotations

import json
from typing import Literal, get_args

from pydantic import BaseModel, Field

from builder.site_ai.logging import ai_log

SectionKind = Literal[
    "hero",
    "statement",
    "intro",
    "feature-grid",
    "cards",
    "photo-tiles",
    "two-column",
    "product-row",
    "brand-row",
    "story",
    "steps",
    "figures",
    "testimonials",
    "faq",
    "team",
    "pricing",
    "gallery",
    "contact-details",
    "contact-form",
    "map",
    "hours",
    "cta",
    "text",
    "legal-text",
]
SECTION_KINDS = get_args(SectionKind)

# the plan's reader is a vision model: this many of the client's photographs are shown to it
# (the rest are described in words), and this many reference pictures
PLAN_PHOTOS_SHOWN = 6
PLAN_INSPIRATIONS_SHOWN = 3
PLAN_MAX_TOKENS = 24000


class PlannedSection(BaseModel):
    kind: SectionKind = Field(description="the section's type, from the list")
    purpose: str = Field(default="", description="one sentence: what this section does for the visitor")
    copy: str = Field(default="", description="the copy direction: headline intent, tone, the facts it states (only facts the material gives)")
    layout: str = Field(default="", description="the geometry, concretely: columns and their widths, alignment, background (light / dark / photograph), height, spacing")
    photos: list[str] = Field(default_factory=list, description="URLs of the client's photographs used here, copied exactly from the list given; empty when none fits")
    component: str = Field(default="", description="the include path of the live component that carries this section, exactly as offered, or empty")


class PlannedPage(BaseModel):
    route: str = Field(description="the page's route, exactly as given")
    title: str = Field(description="the page's title, exactly as given")
    sections: list[PlannedSection] = Field(default_factory=list)
    notes: str = Field(default="", description="what the writer of this page must know that the sections do not say")


class SitePlan(BaseModel):
    direction: str = Field(default="", description="3-5 sentences: the art direction made concrete — colour by role, type, spacing, how photographs are treated, what the site must never do")
    signature_move: str = Field(default="", description="ONE device carried on every page, described as geometry and CSS a page can execute (a 2px accent rule above every h2, a 12px offset shadow on cards...). Never a shape that leaves its section")
    interior_top: str = Field(default="", description="what every interior page opens with, the site's title band being drawn ABOVE it by the site: the shape of the first content section (never a hero, never an h1)")
    rhythm: str = Field(default="", description="section padding scale, the content's maximum width, the grid, how backgrounds alternate")
    logo_notes: str = Field(default="", description="what the logo imposes: its colours, the header background it reads on, whether the wordmark is wide or tall")
    pages: list[PlannedPage] = Field(default_factory=list)

    class Config:
        extra = "ignore"


PLAN_SYSTEM = (
    "You are the art director and lead designer of a small studio known for sites that look designed, not "
    "generated. You plan a whole site ONCE, before a page is written, so that every page is executed from your "
    "plan by a page writer who follows instructions well but must not have to design. Your plan is concrete: "
    "geometry, widths, backgrounds, which photograph goes where, which live component carries a section. "
    "You only state facts the material gives — never a price, a figure, a testimonial, an address or a date "
    "that nobody gave. You never plan an ornament that leaves its section, a text column narrower than 18rem, "
    "or a page that opens with its own title: the site draws a title band above every interior page."
)


def _photo_lines(photos: list[dict]) -> str:
    lines = []
    for i, photo in enumerate(photos, 1):
        shows = (photo.get("shows") or "").strip()
        lines.append(f"{i}. {photo.get('url')}" + (f" — {shows}" if shows else "") + (" (landscape)" if photo.get("landscape") else " (portrait)"))
    return "\n".join(lines)


def plan_prompt(site: dict, brief, pages: list[dict], includes_by_route: dict[str, list[str]], photos: list[dict], language: str, background_mode: str = "auto") -> str:
    """The plan's prompt: the brief, the material, the pages and what each may carry."""
    lines = [
        f"SITE: {site.get('site_name')} — {site.get('activity')}",
        f"POSITIONING: {site.get('differentiators') or 'derive it from the activity'}",
        f"SITE TYPE: {site.get('site_type')}; the site {'SELLS online (it has a shop)' if site.get('sells') else 'does not sell online'}.",
        f"LANGUAGE of every text: {language}.",
        "",
        "DESIGN BRIEF already decided (keep it, make it concrete):",
        f"- concept: {getattr(brief, 'design_concept', '') or ''}",
        f"- signature element: {getattr(brief, 'signature_element', '') or ''}",
        f"- tone: {getattr(brief, 'site_tone', '') or ''}; hero style: {getattr(brief, 'hero_style', '') or ''}",
        f"- colours: primary {getattr(brief, 'primary_color', '')}, secondary {getattr(brief, 'secondary_color', '')}; fonts: {getattr(brief, 'heading_font', '')} / {getattr(brief, 'body_font', '')}",
        f"- ground: {'LIGHT everywhere: no dark or saturated section fill, dark only in a photograph' if background_mode == 'light' else 'DARK everywhere' if background_mode == 'dark' else 'your call, consistent'}",
        f"- copy density: {site.get('copy_density') or 'standard'}",
    ]
    if site.get("inspiration"):
        lines.append("INSPIRATIONS the client likes (echo the palette and the mood, never copy): " + " | ".join(site["inspiration"]))
    if site.get("categories"):
        lines.append("CATEGORIES in the client's words, in this order: " + ", ".join(site["categories"]))
    if site.get("brands"):
        lines.append("BRANDS the business carries: " + ", ".join(site["brands"]))
    if photos:
        lines.append(f"THE CLIENT'S PHOTOGRAPHS ({len(photos)}), with what the vision read in each; use each at most once across the site, by its exact URL:\n" + _photo_lines(photos))
    else:
        lines.append("PHOTOGRAPHS: none from the client. Plan sections that do not depend on photographs; a photo slot is a plain block in the palette.")
    lines.append("")
    lines.append("PAGES to plan, in order, with the live components each may carry (a component draws the site's REAL data — products, brands, hours, posts — and is the only way to show it):")
    for page in pages:
        offered = includes_by_route.get(page["route"]) or []
        lines.append(f"- '{page['title']}' at /{page['route']} (type {page['type']})" + (": components " + "; ".join(offered) if offered else ": no live component"))
    lines += [
        "",
        "RULES OF THE PLAN:",
        "- The home opens with a hero; every INTERIOR page opens with a content section under the site's title band: never a hero, never an h1 of its own, and all interior pages open with the SAME shape (say it in interior_top).",
        "- 4 to 7 sections per page (a legal page: intro, then one 'legal-text'), no two consecutive sections of the same kind, and a rhythm a visitor feels: a tall section, then a short one.",
        "- Every section's layout is geometry a writer can execute: columns and widths (text columns at least 18rem), alignment, background, height. A photograph is placed by URL. A live component is named by its include path and takes the section on its own.",
        "- The signature move is ONE device, described as CSS, inside its section: never a shape, a mark or a layer that leaves the section or the page.",
        "- Only facts the material gives. A section that would need a fact nobody gave (a price, a figure, a review, an opening hour) is not planned.",
        "- Copy is written in the site's language, in the client's words for categories and brands.",
        "- Everything reads at rest: no marquee, no auto-scrolling strip, no content that only appears on hover or on scroll. A brand row is a static row of names or logos.",
        "- No section is a heading over nothing: each section carries the content it announces, written in full.",
    ]
    return "\n".join(lines)


def plan_site(model: str, site: dict, brief, pages: list[dict], includes_by_route: dict[str, list[str]], photos: list[dict], language: str, logo_image: str | None = None, inspiration_images: list[str] | None = None, background_mode: str = "auto") -> SitePlan | None:
    """The plan, written by `model` from the brief and the material, or None when it could not be
    written (the caller then keeps the static plans). Never raises."""
    from builder.site_ai.providers import get_provider

    try:
        llm = get_provider("litellm", model=model, temperature=0.7, timeout=900)
        images = []
        if logo_image:
            images.append(logo_image)
        images += list(inspiration_images or [])[:PLAN_INSPIRATIONS_SHOWN]
        images += [p["url"] for p in photos[:PLAN_PHOTOS_SHOWN] if p.get("url")]
        prompt = plan_prompt(site, brief, pages, includes_by_route, photos, language, background_mode)
        if images:
            prompt += (
                f"\n\nPICTURES ATTACHED, in this order: "
                + ("the client's LOGO first — read its colours and its proportions, and say in logo_notes what they impose; " if logo_image else "")
                + (f"{min(len(inspiration_images or []), PLAN_INSPIRATIONS_SHOWN)} reference picture(s) the client likes; " if inspiration_images else "")
                + (f"then {min(len(photos), PLAN_PHOTOS_SHOWN)} of the client's photographs, in the order of the list above." if photos else "")
            )
        can_see = getattr(llm, "supports_vision", None)
        plan = llm.generate_structured(
            prompt=prompt,
            schema=SitePlan,
            system_prompt=PLAN_SYSTEM,
            images=images if images and callable(can_see) and can_see() else None,
            max_tokens=PLAN_MAX_TOKENS,
        )
        planned = {p.route.strip("/") for p in plan.pages}
        wanted = {p["route"].strip("/") for p in pages}
        ai_log("info", "Site plan written", model=model, pages=len(plan.pages), missing=sorted(wanted - planned),
               sections=sum(len(p.sections) for p in plan.pages), interior_top=(plan.interior_top or "")[:160], signature=(plan.signature_move or "")[:160])
        return plan
    except Exception as e:
        ai_log("warning", "Site plan not written, the static plans apply", model=model, error=str(e)[:200])
        return None


def page_of(plan: SitePlan | None, route: str) -> PlannedPage | None:
    """The plan's page for `route`, or None."""
    if not plan:
        return None
    wanted = (route or "").strip("/")
    return next((p for p in plan.pages if (p.route or "").strip("/") == wanted and p.sections), None)


def section_lines(page: PlannedPage) -> list[str]:
    """The page's sections as the writer reads them, one line each."""
    out = []
    for section in page.sections:
        parts = [f"[{section.kind}] {section.purpose or ''}".strip()]
        if section.copy:
            parts.append(f"copy: {section.copy}")
        if section.layout:
            parts.append(f"layout: {section.layout}")
        if section.photos:
            parts.append("photos: " + ", ".join(section.photos))
        if section.component:
            parts.append(f"component: {{% include \"{section.component}\" %}} (the include IS the section, nothing drawn by hand)")
        out.append(" — ".join(parts))
    return out


def contract_lines(plan: SitePlan | None, is_home: bool) -> list[str]:
    """The site-wide lines of the plan every page brief carries."""
    if not plan:
        return []
    lines = []
    if plan.direction:
        lines.append(f"ART DIRECTION (decided for the whole site): {plan.direction}")
    if plan.signature_move:
        lines.append(f"SIGNATURE MOVE, exactly this on every page: {plan.signature_move}")
    if plan.rhythm:
        lines.append(f"RHYTHM: {plan.rhythm}")
    if plan.interior_top and not is_home:
        lines.append(f"THIS PAGE OPENS WITH (the site's title band is drawn above it): {plan.interior_top}")
    if plan.logo_notes:
        lines.append(f"LOGO: {plan.logo_notes}")
    return lines


def as_json(plan: SitePlan | None) -> str:
    return plan.model_dump_json() if plan else ""


def from_json(text: str) -> SitePlan | None:
    try:
        return SitePlan.model_validate_json(text) if text else None
    except Exception:
        try:
            return SitePlan.model_validate(json.loads(text))
        except Exception:
            return None
