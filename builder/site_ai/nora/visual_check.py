# //// Neoffice — added file (no upstream equivalent): the final look at a built site, read by a vision model.
"""The final look at what was built.

Each page is rendered server-side, screenshotted and read by the vision model against
the brief: what a human sees at first glance (an empty band, a squished image, dummy
text, a brand name that is not the client's). The defects that belong to the page body
come back as revision instructions for one regeneration pass; chrome defects (header,
footer, menu) are reported, not fixed here, since the chrome is not in the page.

The rendering goes through the loopback with the site's own profile named in the query
string (neoffice_theme honours it from 127.0.0.1 only): no profile host has to resolve
for the check to see the right chrome."""

import os
import time

import frappe

from builder.site_ai.logging import ai_log

# //// Neoffice — "logo" alone is no longer a chrome word (2026-09-17): the judge's high point on a
# //// page's "Brand logos section" was dropped as chrome, and the page kept its sparse logo strip.
# //// The chrome is the header, the footer, the navigation — and the site's own logo in them.
CHROME_AREAS = ("header", "footer", "nav", "menu", "site logo", "header logo", "navbar")
IMAGE_WAIT_SECONDS = 360
IMAGE_POLL_SECONDS = 10
# //// Neoffice — the number of times a page is rewritten on what the look found before the
# //// build gives up on it (2026-09-16). It used to be ONE rewrite, unread: the reviewer refused
# //// a page, the page was rewritten once, nobody looked again, and the build published it. Now
# //// every rewrite is looked at again, and a page still refused after these is HELD, not
# //// published (see refused / site_builder's page loop).
MAX_REVISIONS = 3
# //// Neoffice — the phone width the review also looks at (2026-09-16)
PHONE_WIDTH = 375


def enabled() -> bool:
    """site_config nora_visual_check, on by default."""
    try:
        value = frappe.conf.get("nora_visual_check")
    except Exception:
        return True
    return True if value is None else bool(frappe.utils.cint(value))


def static_roots() -> dict:
    """What the loopback render must find on disk: the bench's assets and the site's
    public files (private files stay out, the review is a visitor's view). gunicorn
    serves neither; see screenshotter.static_file_for."""
    return {
        "/assets/": os.path.join(frappe.utils.get_bench_path(), "sites", "assets"),
        "/files/": os.path.abspath(frappe.get_site_path("public", "files")),
    }


# //// Neoffice — name the site by header since bench doesn't write it into /etc/hosts on every bench (a reseller site: no; osiris: yes) and frappe reads this header before the host (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
def loopback_headers() -> dict:
    """The site, named by header rather than by host: bench writes the site name into
    /etc/hosts on some benches only (osiris yes, a reseller site no, 2026-09-09), and frappe
    reads X-Frappe-Site-Name before the host anyway."""
    return {"X-Frappe-Site-Name": frappe.local.site}


def loopback_page_url(route: str, profile: str | None) -> str:
    """The page as the web server sees it from the machine itself (the loopback, the
    site named by loopback_headers), with the profile in the query string for the
    theme's host resolution."""
    port = frappe.conf.get("webserver_port") or 8000
    path = (route or "").strip("/")
    # the home route redirects to "/" and the redirect drops the query string: the
    # first run reviewed the default site's home instead of the profile's (2026-09-08)
    if path in ("home", "index"):
        path = ""
    # //// Neoffice — target 127.0.0.1 rather than the site host: the host doesn't always resolve on the bench (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
    url = f"http://127.0.0.1:{port}/{path}"
    if profile:
        from urllib.parse import quote

        url += f"?_website_profile={quote(profile)}"
    return url


def wait_for_images(job_id: str | None, timeout: int = IMAGE_WAIT_SECONDS) -> str:
    """Block until the image job is done (or the budget is spent): a screenshot with
    grey placeholders would be reviewed for its placeholders."""
    if not job_id:
        return "none"
    from builder.api import _get_generation_status

    deadline = time.time() + timeout
    while time.time() < deadline:
        status = (_get_generation_status(job_id) or {}).get("status") or "not_found"
        if status in ("completed", "failed", "not_found"):
            return status
        time.sleep(IMAGE_POLL_SECONDS)
    return "timeout"


def actionable(critique) -> list[dict]:
    """The high and medium defects that live in the page body."""
    out = []
    for issue in getattr(critique, "issues", None) or []:
        if issue.severity not in ("high", "medium"):
            continue
        if any(word in (issue.area or "").lower() for word in CHROME_AREAS):
            continue
        out.append({"area": issue.area, "severity": issue.severity, "problem": issue.problem, "fix": issue.fix})
    return out


def revision_instructions(issues: list[dict], gate: list[dict] | None = None) -> str:
    """What the page writer gets on the revision pass: the measured facts first (they are not
    opinions), then the designer's points."""
    lines = [
        "REVISION (the page was rendered, measured in the browser at 1440, 768 and 375 px, and a designer reviewed "
        "its screenshots; fix exactly these points and keep everything else, the structure, the copy and the photos "
        "included):"
    ]
    # //// Neoffice — the gate's findings lead (2026-09-16): a number the browser measured beats a
    # //// sentence a model wrote, and the writer must not argue with it.
    lines += [f"- [measured, {g['severity']}] at {g.get('width')}px, {g['where']}: {g['detail']}" for g in (gate or [])]
    lines += [f"- [{i['severity']}] {i['area']}: {i['problem']} -> {i['fix']}" for i in issues]
    return "\n".join(lines)


# //// Neoffice ▼▼▼ — the reviewer's authority (2026-09-16). Three things were missing on the day a
# //// client's B2B site shipped with three pages its own reviewer had called unprofessional:
# //// a judge that is not the writer, a measured gate before the model's opinion, and a verdict
# //// that decides what is published. They live here.
def judge_model(page_model: str) -> str:
    """The model that READS the pages: never the one that wrote them when a stronger reader is
    registered. `nora_review_model` in site_config names it; otherwise the strongest managed
    Kimi that reads images (K3), else the page model itself.

    A model judging its own work is the softest judge there is (self-preference, and mostly
    judge uncertainty: it does not see what it did not think of). The reading costs a fraction
    of the writing — 22 k in / 32 k out for a whole site — so the best reader is affordable."""
    from builder.ai.models import ModelRegistry

    def usable(name: str | None) -> bool:
        if not name:
            return False
        try:
            info = ModelRegistry.find(name)
            return bool(info) and bool(ModelRegistry.supports_vision(name))
        except Exception:
            return False

    try:
        wanted = str(frappe.conf.get("nora_review_model") or "").strip()
    except Exception:
        wanted = ""
    for candidate in (wanted, f"managed/{wanted}" if wanted and "/" not in wanted else "", "managed/kimi-k3"):
        if candidate and candidate != page_model and usable(candidate):
            return candidate
    return page_model


def dedupe_findings(measured: dict) -> list[dict]:
    """The gate's findings across the widths, each reported once (the widest screen it was seen
    on first, so a defect of every width reads as one), with the width it was seen at."""
    seen, out = set(), []
    for width in sorted((measured.get("widths") or {}).keys(), reverse=True):
        for finding in (measured["widths"][width] or {}).get("findings") or []:
            key = (finding.get("kind"), finding.get("where"))
            if key in seen:
                continue
            seen.add(key)
            out.append({**finding, "width": width})
    return out


def contract_findings(measured: dict, is_home: bool, background_mode: str = "auto") -> tuple[list[dict], list[dict]]:
    """What the facts of the rendered page say against the site's own rules: (page findings,
    chrome findings). The page's: an interior page opens under the site's title band, never with
    an h1 of its own, and never with both. The chrome's: the header carries a logo. The chrome's
    findings are the BUILD's to act on, not the page writer's."""
    widths = measured.get("widths") or {}
    if not widths:
        return [], []
    facts = (widths[max(widths.keys())] or {}).get("facts") or {}
    page, chrome = [], []
    if not is_home and facts:
        if not facts.get("band"):
            page.append({"kind": "band-missing", "severity": "high", "width": facts.get("width"), "where": "top of the page",
                         "detail": "the site's title band is missing: the page opens with an h1 of its own, and the band steps aside for it. "
                                   "Remove that h1 (the band shows the page title); the page starts with its first content section"})
        elif int(facts.get("body_h1") or 0) > 0:
            page.append({"kind": "double-title", "severity": "high", "width": facts.get("width"), "where": "top of the page",
                         "detail": "the page repeats its title: the site's band shows it, and the page carries another h1. Remove the page's h1"})
    if facts and not facts.get("header_logo") and not (facts.get("header_text") or "").strip():
        chrome.append({"kind": "logo-missing", "severity": "high", "width": facts.get("width"), "where": "header", "detail": "the header shows neither a logo nor the site's name"})
    # //// Neoffice — the ground the client asked for is measured (2026-09-17): "fond clair partout"
    # //// was in the brief and in the plan, and a revision still came back "sombre et stylisée".
    if background_mode == "light":
        for dark in (facts.get("dark_sections") or [])[:3]:
            page.append({"kind": "dark-ground", "severity": "high", "width": facts.get("width"), "where": dark.get("where") or "section",
                         "detail": f"a section painted dark ({dark.get('height')}px tall) on a site whose ground must be LIGHT everywhere: "
                                   "give it a white or off-white background and dark ink; the accent goes to rules, buttons and small marks"})
    return page, chrome


def points_to_fix(report: dict) -> list[dict]:
    """The reviewer's actionable points, as the revision reads them."""
    return list(report.get("issues") or [])


def accepted(report: dict, lenient: bool = False) -> bool:
    """Whether the page passes: read, called professional, nothing measured against it, no high
    point left. A page that could not be read is not accepted — it is unknown.

    //// Neoffice — `lenient` (2026-09-17): the judge's MEDIUM points are fixed once, not chased.
    On the first full run a home went through three revisions on medium points that changed at
    every look (a watermark cut, then tiles "unfinished", then pillars "redundant"): each pass
    fixed the last look's taste and earned the next one's. A medium point blocks the first
    verdict, so it is revised once; after that, a page the judge calls professional with no
    high point and nothing measured against it is accepted, and the leftovers are said."""
    if report.get("error"):
        return False
    if report.get("professional") is not True:
        return False
    if any(g.get("severity") == "high" for g in report.get("gate") or []):
        return False
    issues = report.get("issues") or []
    if any(i.get("severity") == "high" for i in issues):
        return False
    return lenient or not issues


def refused(report: dict) -> bool:
    """Whether the page is REFUSED — not merely imperfect: the designer called it unprofessional,
    or the browser measured it broken (something sticks out, a text is starved, a component is
    empty, a picture is missing, the band is gone), or it could not be rendered at all."""
    if report.get("http_error"):
        return True
    if report.get("professional") is False:
        return True
    return any(g.get("severity") == "high" for g in report.get("gate") or [])


def why_refused(report: dict) -> str:
    """The refusal in one line, for the journal and the summary."""
    parts = []
    if report.get("http_error"):
        parts.append(f"the page answered {report['http_error']}")
    if report.get("professional") is False:
        parts.append("the designer: " + (report.get("overall") or "not professional")[:160])
    for g in [g for g in report.get("gate") or [] if g.get("severity") == "high"][:3]:
        parts.append(f"measured at {g.get('width')}px: {g['where']} — {g['detail'][:110]}")
    return "; ".join(parts) or "refused"
# //// Neoffice ▲▲▲


# //// Neoffice — tells the vision critic that a plain colour block where a photo would be is
# //// deliberate (image generation off), not a defect to flag (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
REVIEW_CONTEXT = (
    "This is a page of a site for '{site_name}' ({activity}). The header, the navigation and the footer are the "
    "site's shared chrome and are reviewed separately: do not report them. Grey or empty photo boxes and images "
    # //// Neoffice — see the block marker above: plain colour blocks called deliberate
    "that did not load are photos still being generated, and plain colour blocks in the site's palette where a "
    "photo would be are deliberate: ignore them, judge the layout, the copy and the typography of THIS page."
)

# //// Neoffice — what is deliberate on a legal page (2026-09-15). The reviewer read the bracketed
# //// blanks of a privacy policy as "unfinished placeholders", called the page unprofessional and
# //// spent a revision erasing them — undoing the rule that put them there, which exists so the
# //// model states nothing nobody gave it, and losing the merchant's list of what to fill in.
LEGAL_CONTEXT = (
    " This page is a LEGAL document (terms, privacy policy, legal notice). Text in square brackets — "
    "'[to be completed: …]' — is DELIBERATE: it marks what only the merchant can supply, and it must "
    "stay. Do not report it, and do not judge the page unfinished because of it."
)


# the web server may be restarting when a page's turn comes (a deployment, a restart by
# another hand): a refused connection is waited out, not taken for the page's failure; two
# of four pages went unreviewed that way (2026-09-13)
TRANSIENT_ERRORS = ("ERR_CONNECTION_REFUSED", "ERR_CONNECTION_RESET", "ERR_CONNECTION_CLOSED", "ERR_EMPTY_RESPONSE")
SERVER_RETRIES = 9
SERVER_RETRY_SECONDS = 10


def _screenshot(url: str, title: str) -> dict:
    """Full page first; a long page can exceed Chromium's screenshot deadline (Services,
    30 s on osiris), and the viewport alone is still a review where a skipped page is none.
    A server that refuses the connection is waited for, SERVER_RETRIES times."""
    from builder.site_ai.inspiration.screenshotter import capture_website_screenshot

    # //// Neoffice — thread the loopback header (X-Frappe-Site-Name) alongside static_roots so the screenshot names the right site without a host entry (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
    roots, headers = static_roots(), loopback_headers()
    error = ""
    for attempt in range(SERVER_RETRIES + 1):
        try:
            # //// Neoffice — see the block marker above: header threaded into the capture
            shot = capture_website_screenshot(url, full_page=True, static_roots=roots, headers=headers)
            if shot.get("success"):
                return shot
            error = str(shot.get("error") or "screenshot failed")
        except Exception as e:
            error = str(e)
        if attempt == SERVER_RETRIES or not any(code in error for code in TRANSIENT_ERRORS):
            break
        ai_log("info", "Web server not answering, waiting", page=title, attempt=attempt + 1)
        time.sleep(SERVER_RETRY_SECONDS)
    ai_log("warning", "Full-page screenshot failed, viewport only", page=title, error=error[:120])
    # //// Neoffice — see the block marker above: header threaded into the viewport fallback too
    return capture_website_screenshot(url, full_page=False, static_roots=roots, headers=headers)


# //// Neoffice ▼▼▼ — the screenshot, sized for a model to READ (2026-09-15). Wide enough that a
# //// heading and a button are legible, tall enough to show the composition, and light enough not
# //// to cost more than writing the page did. Measured on a real home: 2 105 kB of lossless PNG
# //// against 166 kB here.
READ_WIDTH = 900
READ_MAX_HEIGHT = 3600
READ_QUALITY = 68


def _readable_data_url(shot: dict) -> str | None:
    """The capture as a data URL a vision model can actually read, or None to fall back to the
    file. Never raises: a review on the plain file beats no review."""
    raw = (shot or {}).get("screenshot")
    if not raw:
        return None
    try:
        import base64
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(raw)).convert("RGB")
        if image.width > READ_WIDTH:
            image = image.resize((READ_WIDTH, round(image.height * READ_WIDTH / image.width)), Image.LANCZOS)
        if image.height > READ_MAX_HEIGHT:
            # the top of a page is what a visitor judges; the tail is cropped rather than
            # squashed, which would make every section unreadable
            image = image.crop((0, 0, image.width, READ_MAX_HEIGHT))
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=READ_QUALITY, optimize=True)
        data = out.getvalue()
        ai_log("info", "Review picture sized", kb=len(data) // 1024, width=image.width, height=image.height)
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    except Exception as e:
        ai_log("warning", "Review picture not sized, sending the file", error=str(e)[:120])
        return None
# //// Neoffice ▲▲▲


def _plain(text: str) -> str:
    import re

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip().lower()


def rendered_the_page(measured: dict, expect: list[str] | None) -> bool | None:
    """Whether the render is the page that was written: at least one of its own headlines is in
    the text the browser saw. None when nothing is expected or nothing was measured."""
    lines = [_plain(e) for e in (expect or []) if _plain(e)]
    widths = measured.get("widths") or {}
    if not lines or not widths:
        return None
    sample = _plain(((widths[max(widths.keys())] or {}).get("facts") or {}).get("text_sample") or "")
    if not sample:
        return None
    return any(line[:80] in sample for line in lines)


def forget_page_caches(route: str) -> None:
    """Every cache that can hand the loopback render ANOTHER page than the one just written:
    the route lookup (a deleted page's name, or an untagged fallback taken before this
    profile's page existed, kept for an hour), and frappe's rendered-page cache."""
    try:
        from builder.builder.doctype.builder_page.builder_page import find_page_with_path

        find_page_with_path.clear_cache()
    except Exception:
        pass
    try:
        from frappe.website.utils import clear_website_cache

        clear_website_cache((route or "").strip("/") or "index")
    except Exception:
        pass
    try:
        frappe.cache.delete_value("website_page")
    except Exception:
        pass


def review_page(page: dict, profile: str | None, model: str, site_name: str = "", activity: str = "", expect: list[str] | None = None) -> dict:
    """Measure one page in the browser, screenshot it on a desktop and on a phone, and have the
    judge read it. Never raises: a page that cannot be reviewed is reported as such.

    `expect` names lines the page must show (its own headlines): the render is checked to be
    THIS page before anyone judges it."""
    from builder.site_ai.ingestion.visual_critique import critique_screenshot

    report = {"name": page["name"], "title": page["title"], "route": page["route"], "professional": None, "issues": [], "error": None, "overall": "", "gate": [], "chrome": [], "http_error": None}
    url = loopback_page_url(page["route"], profile)
    shot, phone = None, None
    # //// Neoffice — the measured gate runs first (2026-09-16, see screenshotter.LAYOUT_PROBE): a
    # //// page that answers an error, sticks out of the screen, starves a text or shows an empty
    # //// component is refused on the measure — the judge's opinion is asked all the same, so the
    # //// revision gets both.
    try:
        is_home = str(page.get("route") or "").strip("/") in ("", "home", "index")
        # //// Neoffice — the render is checked to be the page we wrote (2026-09-17). A home written
        # //// into a profile whose old home had just been deleted was measured and judged on the
        # //// DEFAULT profile's home — a route lookup cached for an hour had answered with another
        # //// page — and the judge refused it for "content of a completely different business".
        # //// The caches are forgotten before the look, and a render that shows none of the page's
        # //// own headlines is looked at once more, then reported unread rather than judged.
        forget_page_caches(page["route"])
        measured = measure_page(url)
        if rendered_the_page(measured, expect) is False:
            ai_log("warning", "The render served another page, looking again", page=page["title"], route=page["route"],
                   saw=(((measured.get("widths") or {}).get(1440) or {}).get("facts") or {}).get("title"))
            forget_page_caches(page["route"])
            time.sleep(2)
            measured = measure_page(url)
            if rendered_the_page(measured, expect) is False:
                report["error"] = "the render served another page (a stale route cache): not judged"
                ai_log("warning", "Visual check skipped: the render is not this page", page=page["title"], route=page["route"])
                return report
        status = measured.get("status")
        if status and int(status) >= 400:
            report["http_error"] = int(status)
        findings = dedupe_findings(measured)
        page_rules, chrome_rules = contract_findings(measured, is_home, str(page.get("background_mode") or "auto"))
        report["gate"] = findings + page_rules
        report["chrome"] = chrome_rules
        if measured.get("error"):
            ai_log("warning", "Layout not measured", page=page["title"], error=measured["error"][:120])
        elif report["gate"] or report["chrome"] or report["http_error"]:
            ai_log("info", "Layout measured", page=page["title"], status=status,
                   findings=[f"{g['kind']}@{g.get('width')} {g['where'][:50]}" for g in report["gate"]][:8],
                   chrome=[c["kind"] for c in report["chrome"]])
        else:
            ai_log("info", "Layout measured", page=page["title"], status=status, findings=[])
    except Exception as e:
        ai_log("warning", "Layout gate failed", page=page["title"], error=str(e)[:160])
    if report["http_error"]:
        report["error"] = f"the page answered HTTP {report['http_error']}"
        ai_log("warning", "Visual check refused on HTTP status", page=page["title"], status=report["http_error"])
        return report
    try:
        shot = _screenshot(url, page["title"])
        frappe.db.commit()  # the screenshot File must be visible to the model's read
        if not shot.get("success"):
            report["error"] = "screenshot failed"
            return report
        # //// Neoffice — the phone view, best effort (2026-09-16): its absence never blocks the review
        try:
            phone = capture_phone(url)
        except Exception as e:
            ai_log("warning", "Phone capture failed", page=page["title"], error=str(e)[:120])
        # //// Neoffice — the picture is handed over already sized for reading, as a data URL
        # //// (2026-09-15). Two reasons. The provider's generic downscaler caps the LONGEST side at
        # //// 1280 px, and on a full-page capture that side is the HEIGHT: a 1440 x 4219 page
        # //// reached the model 437 px wide, a ribbon in which no text is legible — the review was
        # //// paying for a picture it could not read. And a data URL passes through
        # //// _image_to_data_url untouched, so what we sized is what is sent.
        phone_picture = _readable_data_url(phone) if phone and phone.get("success") else None
        critique, label = critique_screenshot(
            _readable_data_url(shot) or shot["file_url"],
            model=model,
            context=REVIEW_CONTEXT.format(site_name=site_name, activity=activity[:160])
            + (LEGAL_CONTEXT if str(page.get("type") or "") == "legal" else ""),
            extra_images=[phone_picture] if phone_picture else None,
        )
        report["professional"] = bool(critique.looks_professional)
        report["overall"] = (critique.overall or "")[:200]
        report["issues"] = actionable(critique)
        report["all_issues"] = len(critique.issues or [])
        ai_log("info", "Visual check", page=page["title"], professional=report["professional"], issues=report["all_issues"], actionable=len(report["issues"]), model=label)
        # //// Neoffice — the judge's WORDS go to the journal (2026-09-16). It kept `issues=3` and
        # //// never a sentence: nobody could read what the reviewer had seen, so nobody could
        # //// tell a judge that was right from one that was not.
        ai_log("info", "Reviewer words", page=page["title"], overall=report["overall"],
               issues=[f"[{i.severity}] {i.area}: {i.problem} -> {i.fix}"[:220] for i in (critique.issues or [])][:8])
    except Exception as e:
        report["error"] = str(e)[:200]
        ai_log("warning", "Visual check failed", page=page["title"], error=report["error"])
    finally:
        _drop_capture(shot)
        _drop_capture(phone)
    return report


def capture_phone(url: str) -> dict:
    """The page as a phone shows it (PHONE_WIDTH), full length, for the judge's second picture."""
    from builder.site_ai.inspiration.screenshotter import capture_website_screenshot

    return capture_website_screenshot(url, full_page=True, static_roots=static_roots(), headers=loopback_headers(), viewport_width=PHONE_WIDTH)


def measure_page(url: str) -> dict:
    """The page measured in the browser at the three widths (screenshotter.measure_layout),
    served from disk and named by header like every loopback render."""
    from builder.site_ai.inspiration.screenshotter import measure_layout

    return measure_layout(url, static_roots=static_roots(), headers=loopback_headers())


def _drop_capture(shot: dict | None) -> None:
    """The screenshot is read once, by the critique, and then removed: every build left one public
    PNG per page reviewed among the site's files (78 on a test instance in three days,
    2026-09-13). Never raises."""
    url = (shot or {}).get("file_url")
    if not url:
        return
    try:
        for name in frappe.get_all("File", filters={"file_url": url}, pluck="name"):
            frappe.delete_doc("File", name, ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()
    except Exception as e:
        ai_log("warning", "Screenshot not removed", url=url, error=str(e)[:120])


def summary_lines(reviews: list[dict], revised: dict[str, int], held: list[dict] | None = None) -> list[str]:
    """The lines the tool returns, for the assistant to relay."""
    if not reviews and not held:
        return []
    lines = ["Visual check (each page measured in the browser at three widths, then its desktop and phone screenshots reviewed by the judge):"]
    held_names = {h["name"] for h in (held or [])}
    for r in reviews:
        if r["name"] in held_names:
            continue
        if r.get("error"):
            lines.append(f"- {r['title']}: not reviewed ({r['error']})")
            continue
        verdict = "looks professional" if r["professional"] else "needs work"
        fixed = revised.get(r["name"])
        detail = "; ".join(f"{i['area']}: {i['problem'][:70]}" for i in r["issues"][:3])
        measured = "; ".join(f"{g['where'][:40]}: {g['detail'][:60]}" for g in (r.get("gate") or [])[:2])
        if measured:
            detail = (detail + "; " if detail else "") + "measured: " + measured
        if fixed:
            lines.append(f"- {r['title']}: {verdict}; {fixed} point(s) fixed in a revision pass ({detail})")
        elif r["issues"] or measured:
            lines.append(f"- {r['title']}: {verdict}; left as is ({detail})")
        else:
            lines.append(f"- {r['title']}: {verdict}")
    # //// Neoffice — the pages the build refused (2026-09-16): said plainly, with the judge's words,
    # //// and handed to the user as a question — never published as if they had passed.
    for h in held or []:
        state = "published but flagged (the site needs it)" if h.get("essential") else "NOT published and NOT in the menu"
        lines.append(f"- {h['title']}: REFUSED after {h.get('attempts', 1)} look(s), {state}: {h.get('why', '')[:300]}")
    if held:
        lines.append(
            "Ask the user, with ONE present_ui choices card, what to do with each refused page: rebuild it with a different "
            "direction (call generate_site with scope='pages', that page alone, and their words), publish it as it is, or "
            "leave it for them to finish in the editor. Do not decide for them, and do not publish a refused page yourself."
        )
    return lines
