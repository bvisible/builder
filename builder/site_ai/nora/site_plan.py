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

from pydantic import BaseModel, Field, field_validator

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
# //// Neoffice — the pages a plan lacks are asked for in small batches (2026-10-20), see complete_plan
PLAN_PAGES_PER_COMPLETION = 3
PLAN_COMPLETION_ROUNDS = 3


class PlannedSection(BaseModel):
    kind: SectionKind = Field(description="the section's type, from the list")
    purpose: str = Field(default="", description="one sentence: what this section does for the visitor")
    copy: str = Field(default="", description="the copy direction: headline intent, tone, the facts it states (only facts the material gives)")
    layout: str = Field(default="", description="the geometry, concretely: columns and their widths, alignment, background (light / dark / photograph), height, spacing")
    photos: list[str] = Field(default_factory=list, description="URLs of the client's photographs used here, copied exactly from the list given; empty when none fits")
    component: str = Field(default="", description="the include path of the live component that carries this section, exactly as offered, or empty")
    # //// Neoffice — a section recipe proposed by the plan (recipes.py, 2026-10-21); empty when the plan designs the section itself
    recipe: str = Field(default="", description="the id of a section recipe from the SECTION RECIPES catalogue that this section starts from, or empty when you design it yourself (say in `layout` what you change in a recipe)")

    # //// Neoffice — a model that answers `recipe: null` for a section it designs itself is not a failed plan
    @field_validator("recipe", mode="before")
    @classmethod
    def recipe_is_text(cls, value):
        return value.strip() if isinstance(value, str) else ""


class PlannedPage(BaseModel):
    route: str = Field(description="the page's route, exactly as given")
    title: str = Field(description="the page's title, exactly as given")
    sections: list[PlannedSection] = Field(default_factory=list)
    notes: str = Field(default="", description="what the writer of this page must know that the sections do not say")

    # //// Neoffice — a plan cut at the model's output ceiling (4 096 tokens on the local lane) ends in a half-written
    # //// section, which json repair closes as a list or a bare word: the whole plan then failed validation and the
    # //// site was written with the static plans (2026-10-20). Only whole sections are kept.
    @field_validator("sections", mode="before")
    @classmethod
    def keep_whole_sections(cls, value):
        if not isinstance(value, list):
            return []
        return [v for v in value if isinstance(v, PlannedSection) or (isinstance(v, dict) and v.get("kind") in SECTION_KINDS)]


def keep_pages(value) -> list:
    """The entries of a `pages` list that are pages: a cut answer can end in a bare word or a half object."""
    if not isinstance(value, list):
        return []
    return [
        v
        for v in value
        if isinstance(v, PlannedPage) or (isinstance(v, dict) and isinstance(v.get("route"), str) and isinstance(v.get("title"), str))
    ]


class SitePlan(BaseModel):
    direction: str = Field(default="", description="3-5 sentences: the art direction made concrete — colour by role, type, spacing, how photographs are treated, what the site must never do")
    signature_move: str = Field(default="", description="ONE device carried on every page, described as geometry and CSS a page can execute (a 2px accent rule above every h2, a 12px offset shadow on cards...). Never a shape that leaves its section")
    interior_top: str = Field(default="", description="what every interior page opens with, the site's title band being drawn ABOVE it by the site: the shape of the first content section (never a hero, never an h1)")
    rhythm: str = Field(default="", description="section padding scale, the content's maximum width, the grid, how backgrounds alternate")
    logo_notes: str = Field(default="", description="what the logo imposes: its colours, the header background it reads on, whether the wordmark is wide or tall")
    pages: list[PlannedPage] = Field(default_factory=list)

    @field_validator("pages", mode="before")
    @classmethod
    def keep_whole_pages(cls, value):
        return keep_pages(value)

    class Config:
        extra = "ignore"


class PlannedPages(BaseModel):
    """The pages of a plan, asked for on their own when the first answer left some out."""

    pages: list[PlannedPage] = Field(default_factory=list)

    @field_validator("pages", mode="before")
    @classmethod
    def keep_whole_pages(cls, value):
        return keep_pages(value)

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
        # //// Neoffice — where the site generates photographs (site["images_on"]), a photo slot is a real photograph made after the build, not a plain block
        if site.get("images_on"):
            lines.append(
                "PHOTOGRAPHS: none from the client. The site GENERATES a photograph for every photo slot after the build (a minute each: use them where "
                "the photograph is the point of a section, not everywhere). A photo slot is a place for a real photograph of this business, never a plain "
                "coloured block and never a label; say in `layout` what the photograph shows."
            )
        else:
            lines.append("PHOTOGRAPHS: none from the client. Plan sections that do not depend on photographs; a photo slot is a plain block in the palette.")
    lines.append("")
    lines.append("PAGES to plan, in order, with the live components each may carry (a component draws the site's REAL data — products, brands, hours, posts — and is the only way to show it):")
    for page in pages:
        offered = includes_by_route.get(page["route"]) or []
        lines.append(f"- '{page['title']}' at /{page['route']} (type {page['type']})" + (": components " + "; ".join(offered) if offered else ": no live component"))
    # //// Neoffice — the catalogue of section recipes (recipes.py, 2026-10-21): proposals the plan picks from or leaves
    from builder.site_ai.nora import recipes

    if recipes.enabled():
        lines += ["", *recipes.catalogue_lines(seed=str(site.get("site_name") or ""), material=recipes.site_material(site))]
    lines += [
        "",
        "RULES OF THE PLAN:",
        "- The home opens with a hero; every INTERIOR page opens with a content section under the site's title band: never a hero, never an h1 of its own, and all interior pages open with the SAME shape (say it in interior_top).",
        "- 4 to 7 sections per page (a legal page: intro, then one 'legal-text'), no two consecutive sections of the same kind, and a rhythm a visitor feels: a tall section, then a short one.",
        # //// Neoffice — a page made to be written to (page_form.py): a booking page planned without its form had to be given one after the writer
        "- A page made to be written to (its title says book, reserve, quote or contact) carries a 'contact-form' section with the form component offered to it, right after its opening section.",
        "- Every section's layout is geometry a writer can execute: columns and widths (text columns at least 18rem), alignment, background, height. A photograph is placed by URL. A live component is named by its include path and takes the section on its own.",
        "- The signature move is ONE device, described as CSS, inside its section: never a shape, a mark or a layer that leaves the section or the page.",
        "- Only facts the material gives. A section that would need a fact nobody gave (a price, a figure, a review, an opening hour) is not planned.",
        "- Copy is written in the site's language, in the client's words for categories and brands.",
        "- Everything reads at rest: no marquee, no auto-scrolling strip, no content that only appears on hover or on scroll. A brand row is a static row of names or logos.",
        "- No section is a heading over nothing: each section carries the content it announces, written in full.",
    ]
    return "\n".join(lines)


MIN_PLANNED_SECTIONS = 3


def is_planned(page: PlannedPage) -> bool:
    """A page is planned when it carries at least MIN_PLANNED_SECTIONS sections, or, for a legal page, its text: a
    page the plan stopped in the middle of (a cut answer) is asked for again."""
    if any(s.kind == "legal-text" for s in page.sections):
        return True
    return len(page.sections) >= MIN_PLANNED_SECTIONS


def missing_routes(plan: SitePlan, pages: list[dict]) -> list[dict]:
    """The pages to plan that the plan has no whole page for, in the site's order."""
    planned = {p.route.strip("/") for p in plan.pages if is_planned(p)}
    return [p for p in pages if p["route"].strip("/") not in planned]


def completion_prompt(plan: SitePlan, site: dict, brief, lacking: list[dict], includes_by_route: dict[str, list[str]], photos: list[dict], language: str, background_mode: str) -> str:
    """The prompt that asks for the pages a plan left out: the decisions already taken, then only those pages."""
    used = {url for page in plan.pages for section in page.sections for url in section.photos}
    free = [p for p in photos if p.get("url") not in used]
    decided = [
        "THE PLAN OF THE SITE IS ALREADY DECIDED and must not change. Plan ONLY the pages listed under PAGES below, in the same hand, "
        "and answer with `pages` only: one entry per listed page, each with its sections, its route and its title exactly as given.",
        f"- art direction: {plan.direction}",
        f"- signature move, on every page: {plan.signature_move}",
        f"- every interior page opens with: {plan.interior_top}",
        f"- rhythm: {plan.rhythm}",
    ]
    if plan.logo_notes:
        decided.append(f"- logo: {plan.logo_notes}")
    already = [f"'{p.title}' ({', '.join(s.kind for s in p.sections)})" for p in plan.pages if p.sections]
    if already:
        decided.append("- pages already planned (do not repeat their shape): " + "; ".join(already))
    return "\n".join(decided) + "\n\n" + plan_prompt(site, brief, lacking, includes_by_route, free, language, background_mode)


def complete_plan(llm, plan: SitePlan, site: dict, brief, pages: list[dict], includes_by_route: dict[str, list[str]], photos: list[dict], language: str, background_mode: str = "auto") -> SitePlan:
    """The plan with the pages it left out planned too. //// Neoffice (2026-10-20): the local model, whose answer is
    cut at 4 096 tokens, planned two pages of seven in one run (eight sections, against thirty-two for the strong
    model); the five others were written with no plan and came out thin. The missing pages are asked for in
    batches of PLAN_PAGES_PER_COMPLETION, the decisions already taken in front, for at most PLAN_COMPLETION_ROUNDS
    rounds. Never raises: a batch that fails leaves its pages to the static plans, as before."""
    for round_number in range(PLAN_COMPLETION_ROUNDS):
        lacking = missing_routes(plan, pages)
        if not lacking:
            break
        batch = lacking[:PLAN_PAGES_PER_COMPLETION]
        try:
            extra = llm.generate_structured(
                prompt=completion_prompt(plan, site, brief, batch, includes_by_route, photos, language, background_mode),
                schema=PlannedPages,
                system_prompt=PLAN_SYSTEM,
                images=None,
                max_tokens=PLAN_MAX_TOKENS,
            )
        except Exception as e:
            ai_log("warning", "Site plan completion failed", round=round_number + 1, pages=[p["route"] for p in batch], error=str(e)[:200])
            continue
        asked = {p["route"].strip("/") for p in batch}
        held = {p.route.strip("/"): len(p.sections) for p in plan.pages}
        # a page replaces the one the plan holds (half of it, or none) only when it is whole and fuller
        added = [
            p
            for p in extra.pages
            if p.route.strip("/") in asked and is_planned(p) and len(p.sections) > held.get(p.route.strip("/"), 0)
        ]
        replaced = {p.route.strip("/") for p in added}
        plan.pages = [p for p in plan.pages if p.sections and p.route.strip("/") not in replaced] + added
        ai_log("info", "Site plan completed", round=round_number + 1, asked=sorted(asked), added=[p.route for p in added])
    return plan


# //// Neoffice — the plan may only use the photographs it was given (2026-10-21): told "none from the client", the local planner still wrote
# //// `photos: [https://picsum.photos/seed/auberge-interior/800/1000]` on sections, and a writer given a recipe with that address kept it
def keep_offered_photos(plan: SitePlan, photos: list[dict]) -> int:
    """Takes out of every section the photograph addresses that are not among the ones offered to the plan. Returns how many."""
    offered = {p.get("url") for p in photos or []}
    removed = 0
    for page in plan.pages:
        for section in page.sections:
            kept = [u for u in section.photos if u in offered]
            removed += len(section.photos) - len(kept)
            section.photos = kept
    return removed


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
                "\n\nPICTURES ATTACHED, in this order: "
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
        plan = complete_plan(llm, plan, site, brief, pages, includes_by_route, photos, language, background_mode)  # //// Neoffice — see complete_plan
        invented = keep_offered_photos(plan, photos)  # //// Neoffice — see keep_offered_photos
        if invented:
            ai_log("info", "Photograph addresses the plan made up removed", count=invented)
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


def section_lines(page: PlannedPage, hero_dressed: bool = False, recipes: dict | None = None) -> list[str]:
    """The page's sections as the writer reads them, one line each. `hero_dressed`: the page brief carries a HERO BACKGROUND
    recipe, so the plan's own layout and photos for the hero are left out (they described a flat centred block again and the
    writer, reading the plan first, followed it over the recipe: 2026-10-20)."""
    out = []
    for index, section in enumerate(page.sections):
        parts = [f"[{section.kind}] {section.purpose or ''}".strip()]
        if section.copy:
            parts.append(f"copy: {section.copy}")
        # //// Neoffice — a section with a recipe starts from its structure (recipes.brief_lines): the plan's own layout words
        # //// become the adaptations of that structure, and its photographs and component sit in the structure
        if recipes and index in recipes:
            parts.append(f"starts from the recipe {recipes[index].recipe.id}, given below (photographs and component included)")
            if section.layout:
                parts.append(f"adaptations the plan decided (they win over the structure where they differ): {section.layout}")
            out.append(" — ".join(parts))
            continue
        if hero_dressed and section.kind == "hero":
            # //// Neoffice — the recipe decides the background, the composition and the photograph of the home's hero (hero.py)
            parts.append("layout: as the HERO BACKGROUND line says (its background, its photograph, how its copy sits)")
            out.append(" — ".join(parts))
            continue
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
