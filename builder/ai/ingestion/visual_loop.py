"""
Visual verification loop — the second half: see → critique → FIX → re-check.

For a generated page: screenshot it server-side, critique the screenshot with a
vision model (Nora — fast/free), turn the actionable defects into a targeted
block revision (page code model), save, re-render and re-critique. Up to a few
iterations, stopping as soon as the page reads as professional.

Site-chrome defects (header/footer/logo/nav) are skipped here — they live in the
Website Header Footer Config, not in the page blocks.
"""

import json

import frappe
from frappe import _

from builder.ai.config import get_ai_settings
from builder.ai.logging import ai_log
from builder.ai.ingestion.visual_critique import critique_screenshot


# Critique areas the page-block revision cannot fix (they're site chrome).
CHROME_AREAS = ("header", "footer", "nav", "logo", "menu")


def _page_url(page_name: str) -> str:
    route = frappe.db.get_value("Builder Page", page_name, "route") or ""
    return frappe.utils.get_url().rstrip("/") + "/" + route.lstrip("/")


def _actionable(critique) -> list:
    """High/medium issues that belong to the page body (not site chrome)."""
    out = []
    for i in critique.issues:
        if i.severity not in ("high", "medium"):
            continue
        if any(c in (i.area or "").lower() for c in CHROME_AREAS):
            continue
        out.append({"area": i.area, "severity": i.severity, "problem": i.problem, "fix": i.fix})
    return out


def refine_page(page_name: str, max_iterations: int = 2, critique_with: str = "nora",
                design_brief=None, primary: str = None, secondary: str = None) -> dict:
    """Run the see→critique→fix→recheck loop on one page. Returns a report."""
    from builder.ai.generators.page_generator import PageGenerator
    from builder.ai.inspiration.screenshotter import capture_website_screenshot
    from builder.api import _blocks_fingerprint

    cfg = get_ai_settings()
    gen = PageGenerator(config=cfg)
    url = _page_url(page_name)
    report = {"page": page_name, "url": url, "iterations": [], "fixed": 0}

    for it in range(max_iterations):
        shot = capture_website_screenshot(url, full_page=False)
        frappe.db.commit()  # persist the screenshot File so the vision model can read it
        if not shot.get("success"):
            report["error"] = "screenshot failed"
            break

        critique, label = critique_screenshot(shot["file_url"], which=critique_with)
        actionable = _actionable(critique)
        report["iterations"].append({
            "iteration": it,
            "critic": label,
            "professional": critique.looks_professional,
            "issues": len(critique.issues),
            "actionable": len(actionable),
            "overall": (critique.overall or "")[:200],
            "problems": [f"[{a['severity']}] {a['area']}: {a['problem'][:90]}" for a in actionable],
        })

        if not actionable:
            break  # clean (or only chrome-level issues left)

        page = frappe.get_doc("Builder Page", page_name)
        blocks = json.loads(page.blocks or "[]")
        revised = gen.revise_blocks(blocks, actionable, design_brief=design_brief,
                                    primary=primary, secondary=secondary, page_title=page.page_title)
        new_json = json.dumps(revised, ensure_ascii=False)
        if new_json == json.dumps(blocks, ensure_ascii=False):
            ai_log("info", "Revision produced no change — stopping loop", page=page_name)
            break
        # Save via the doc so Builder regenerates the published page; keep the
        # AI stamp so the page stays "untouched AI" for the replace policy.
        page.blocks = new_json
        page.draft_blocks = new_json
        page.save(ignore_permissions=True)
        frappe.db.set_value("Builder Page", page_name, "ai_blocks_hash",
                            _blocks_fingerprint(new_json), update_modified=False)
        frappe.db.commit()
        frappe.clear_cache()
        report["fixed"] += len(actionable)

    return report


@frappe.whitelist()
def chat_refine_page(page_name: str, max_iterations: int = 2) -> dict:
    """Whitelisted entry: run the visual refinement loop on one page."""
    if not page_name:
        frappe.throw(_("page_name is required"))
    return refine_page(page_name, int(max_iterations))
