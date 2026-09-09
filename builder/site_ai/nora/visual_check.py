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

CHROME_AREAS = ("header", "footer", "nav", "logo", "menu")
IMAGE_WAIT_SECONDS = 360
IMAGE_POLL_SECONDS = 10
MAX_REVISIONS = 3


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


# //// Neoffice — name the site by header since bench doesn't write it into /etc/hosts on every bench (The League: no; osiris: yes) and frappe reads this header before the host (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
def loopback_headers() -> dict:
    """The site, named by header rather than by host: bench writes the site name into
    /etc/hosts on some benches only (osiris yes, The League no, 2026-09-09), and frappe
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


def revision_instructions(issues: list[dict]) -> str:
    """What the page writer gets on the revision pass."""
    lines = [
        "REVISION (a designer reviewed a screenshot of the rendered page; fix exactly these points and keep "
        "everything else, the structure, the copy and the photos included):"
    ]
    lines += [f"- [{i['severity']}] {i['area']}: {i['problem']} -> {i['fix']}" for i in issues]
    return "\n".join(lines)


REVIEW_CONTEXT = (
    "This is a page of a site for '{site_name}' ({activity}). The header, the navigation and the footer are the "
    "site's shared chrome and are reviewed separately: do not report them. Grey or empty photo boxes and images "
    "that did not load are photos still being generated: ignore them, judge the layout, the copy and the "
    "typography of THIS page."
)


def _screenshot(url: str, title: str) -> dict:
    """Full page first; a long page can exceed Chromium's screenshot deadline (Services,
    30 s on osiris), and the viewport alone is still a review where a skipped page is none."""
    from builder.site_ai.inspiration.screenshotter import capture_website_screenshot

    # //// Neoffice — thread the loopback header (X-Frappe-Site-Name) alongside static_roots so the screenshot names the right site without a host entry (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
    roots, headers = static_roots(), loopback_headers()
    try:
        # //// Neoffice — see the block marker above: header threaded into the capture
        shot = capture_website_screenshot(url, full_page=True, static_roots=roots, headers=headers)
        if shot.get("success"):
            return shot
        raise RuntimeError(str(shot.get("error") or "screenshot failed"))
    except Exception as e:
        ai_log("warning", "Full-page screenshot failed, viewport only", page=title, error=str(e)[:120])
        # //// Neoffice — see the block marker above: header threaded into the viewport fallback too
        return capture_website_screenshot(url, full_page=False, static_roots=roots, headers=headers)


def review_page(page: dict, profile: str | None, model: str, site_name: str = "", activity: str = "") -> dict:
    """Screenshot one page and read it. Never raises: a page that cannot be reviewed
    is reported as such."""
    from builder.site_ai.ingestion.visual_critique import critique_screenshot

    report = {"name": page["name"], "title": page["title"], "route": page["route"], "professional": None, "issues": [], "error": None, "overall": ""}
    url = loopback_page_url(page["route"], profile)
    try:
        shot = _screenshot(url, page["title"])
        frappe.db.commit()  # the screenshot File must be visible to the model's read
        if not shot.get("success"):
            report["error"] = "screenshot failed"
            return report
        critique, label = critique_screenshot(shot["file_url"], model=model, context=REVIEW_CONTEXT.format(site_name=site_name, activity=activity[:160]))
        report["professional"] = bool(critique.looks_professional)
        report["overall"] = (critique.overall or "")[:200]
        report["issues"] = actionable(critique)
        report["all_issues"] = len(critique.issues or [])
        ai_log("info", "Visual check", page=page["title"], professional=report["professional"], issues=report["all_issues"], actionable=len(report["issues"]), model=label)
    except Exception as e:
        report["error"] = str(e)[:200]
        ai_log("warning", "Visual check failed", page=page["title"], error=report["error"])
    return report


def summary_lines(reviews: list[dict], revised: dict[str, int]) -> list[str]:
    """The lines the tool returns, for the assistant to relay."""
    if not reviews:
        return []
    lines = ["Visual check (each page rendered and reviewed by the vision model):"]
    for r in reviews:
        if r.get("error"):
            lines.append(f"- {r['title']}: not reviewed ({r['error']})")
            continue
        verdict = "looks professional" if r["professional"] else "needs work"
        fixed = revised.get(r["name"])
        detail = "; ".join(f"{i['area']}: {i['problem'][:70]}" for i in r["issues"][:3])
        if fixed:
            lines.append(f"- {r['title']}: {verdict}; {fixed} point(s) fixed in a revision pass ({detail})")
        elif r["issues"]:
            lines.append(f"- {r['title']}: {verdict}; left as is ({detail})")
        else:
            lines.append(f"- {r['title']}: {verdict}")
    return lines
