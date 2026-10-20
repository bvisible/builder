# //// Neoffice — added file (no upstream equivalent): a vision model reviews a screenshot of a generated
# //// page and lists visible defects. builder/site_ai/** = the Neoffice AI site generator; frappe/builder
# //// ships no such module. First commit 631deed3 2026-06-23.
"""
Visual verification loop — a vision model reviews a SCREENSHOT of a generated
page and reports concrete visible problems, so the generator can fix them
("the LLM sees what it made").

Screenshots are captured server-side via WebsiteScreenshotter (Playwright +
chromium-headless-shell — see deployment deps). The critique runs on the Olares
"nora" vision model when configured (fast + free); pass which="kimi" to use
Kimi K2.6 instead — better-calibrated judgement, kept as the fallback / for the
critique step if nora proves too weak at design critique.
"""


from builder.site_ai.config import get_ai_settings
from builder.site_ai.logging import ai_log
from builder.site_ai.providers import get_provider
from builder.site_ai.schemas.page_critique import PageCritique

# //// Neoffice — 300 (2026-09-16): the judge thinks before it answers (K3 at "high" read a page in ~50 s;
# //// a long page with two pictures may take twice that), and the timeout now reaches the call
CRITIQUE_TIMEOUT = 300

_CRITIQUE_SYSTEM = (
    "You are a senior web designer doing a final review of a SCREENSHOT of a "
    "generated web page before it goes live for a client. Judge it as a human "
    "would at first glance. Report ONLY real, visible problems: empty or "
    "unbalanced areas, placeholder/dummy/wrong text, a brand name that doesn't "
    "match the business, broken or squished/stretched images, unreadable text "
    "or poor contrast, misalignment, content that clearly doesn't belong. Be "
    "concrete and specific to what you actually SEE. If it looks good, return "
    "few or no issues."
)


# //// Neoffice — the instructions of a judge that is not a large hosted model (2026-10-20). The local model read the
# //// pages with the instructions above and refused half of the good ones, on faults it invented (a word it "saw"
# //// misspelled, written correctly on the page), on text it found small, and on the plain blocks it was told to
# //// ignore. Measured on 23 pages read twice, then on 28 pages it had not been tuned on (Obsidian
# //// Neoffice/Builder/Projet-Builder-v15/14, section 8): this version, on the reasoning lane, refuses 21 % of the good
# //// reads instead of 50 % and none of the 14 pages a large model wrote, and still refuses the 16 pages damaged on
# //// purpose. What changed: the verdict starts from "professional", the judge does not proof-read (another tool
# //// does), and a point must quote what the judge reads on the page.
EVIDENCE_SYSTEM = (
    "You are a senior web designer doing a final review of SCREENSHOTS of a generated web page before it goes live "
    "for a client. Judge it as a visitor would at first glance. The default verdict is PROFESSIONAL: call the page "
    "not professional only for a defect a visitor would notice at once and a designer would refuse to ship: the page "
    "looks broken or half empty, text overlaps or is cut off, text cannot be read against its background, pictures "
    "are stretched or missing where the layout depends on them, or the content is about another business. "
    "Do NOT proof-read: spelling, grammar and wording are checked by another tool, so never report a typo or a "
    "sentence you find awkward. Do not report text that is merely small or light unless you cannot read it at all. "
    "Do not report the header, the navigation or the footer. Plain coloured blocks where a photo would go are "
    "deliberate. Every issue must name the visible element and quote the exact words you can read on it (leave the "
    "quote empty only for a problem that is not text, such as a gap or an overlap): if you cannot quote it, do not "
    "report it. Prefer a few certain issues to many doubtful ones; a page without such a defect has no issues."
)
SYSTEMS = {"default": _CRITIQUE_SYSTEM, "evidence": EVIDENCE_SYSTEM}


def _critique_provider(which: str = "auto"):
    """Return (provider, label). 'nora' = Olares vision (fast/free); 'kimi' =
    Kimi K2.6 (general/brief model); 'auto' = nora when configured else kimi."""
    from builder.site_ai.managed import nora_vision_model

    cfg = get_ai_settings()
    vision = nora_vision_model() if which in ("nora", "auto") else None
    if vision:
        return get_provider("litellm", model=vision, temperature=0.2, timeout=CRITIQUE_TIMEOUT), "nora"
    return get_provider(
        "litellm",
        model=cfg.model,
        temperature=0.3,
        timeout=CRITIQUE_TIMEOUT,
    ), cfg.model


# //// Neoffice — room for the reasoning plus a short JSON, not the brief's 40 000 (2026-09-15)
CRITIQUE_MAX_TOKENS = 8000


def critique_screenshot(screenshot_url: str, which: str = "auto", model: str | None = None, context: str = "", extra_images: list[str] | None = None, style: str = "default"):
    """Critique a page screenshot. Returns (PageCritique, model_label). `model` names a
    vision-capable registry model to use instead of the nora/kimi choice (the site build
    reviews with its page model, Kimi K2.7 reads images since 2026-09-08); `context` is
    what the reviewer should know before judging (the brief, what is still being generated)."""
    if model:
        llm, label = get_provider("litellm", model=model, temperature=0.3, timeout=CRITIQUE_TIMEOUT), model
    else:
        llm, label = _critique_provider(which)
    prompt = (
        "Review this web page screenshot. Give a one-line overall impression, "
        "whether it looks professional, and the concrete visible problems "
        "(area, severity, problem, fix), most important first."
    )
    # //// Neoffice — the phone view travels with the desktop one (2026-09-16): what breaks first
    # //// breaks at 375 px, and a review that never saw it passed a title wrapped letter by letter.
    if extra_images:
        prompt += (
            f"\n\nThere are {1 + len(extra_images)} pictures: the page on a desktop screen first, then the SAME page "
            "on a phone (375 px wide). Judge both: a page that breaks on the phone is not professional."
        )
    if context:
        prompt += "\n\nContext: " + context.strip()
    # //// Neoffice — a short answer asks for a short ceiling (2026-09-15): a critique is a line
    # //// and a handful of issues, and this model bills its reasoning as output. Every structured
    # //// call used to ask for 40 000 tokens of room, the figure the design brief needs.
    critique = llm.generate_structured(
        prompt=prompt,
        schema=PageCritique,
        # //// Neoffice — `style` picks the instructions (SYSTEMS): "evidence" for a judge that is not a large hosted model
        system_prompt=SYSTEMS.get(style, _CRITIQUE_SYSTEM),
        images=[screenshot_url, *(extra_images or [])],
        max_tokens=CRITIQUE_MAX_TOKENS,
        think=False,
    )
    ai_log("info", "Page critique done", model=label,
           issues=len(critique.issues), professional=critique.looks_professional)
    return critique, label
