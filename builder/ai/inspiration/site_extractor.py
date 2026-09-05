# //// Neoffice — added file (no upstream equivalent): lifts palette, fonts, radius and copy from the
# //// client's CURRENT site. builder/ai/** = the Neoffice AI site generator; frappe/builder ships no
# //// such module. First commit 31c3e3c8 2026-06-23.
"""
Existing-site extractor — seed the brief from a client's CURRENT website.

Inspired by the AI-website-cloner inspection methodology (design-token
extraction), but for OUR goal: we don't clone pixel-for-pixel — we lift the
real signal (palette, fonts, radius, headings, copy + a screenshot) from the
client's existing site and feed it to the brief, so generation starts from
their real identity instead of inventing one.

Reuses Playwright (already used by WebsiteScreenshotter). Server-side only.
"""

import colorsys
# //// Neoffice — ipaddress/socket/urlparse and require_builder_role: the address
# //// guard and the role gate added below (this endpoint fetches a URL server-side).
import ipaddress
import re
import socket
from urllib.parse import urlparse

import frappe
from frappe import _

from builder.ai.logging import ai_log
from builder.utils import require_builder_role

# //// Neoffice — everything from here to assert_public_http_url() is ours: upstream
# //// has no site importer, so it has no address guard either.
# The server fetches this URL itself, so "http(s) and a public address" is not a
# nicety: without it the endpoint is a proxy into the private network — the
# metadata service (169.254.169.254), the bench's own redis/mysql, a neighbour
# instance on the same subnet — with the answer handed back as a screenshot and
# extracted text.
_ALLOWED_SCHEMES = ("http", "https")

# What we keep of a scraped page. The collector already slices the body text at
# 6000 chars in the browser; this is the server-side ceiling that does not
# depend on the page cooperating.
MAX_EXTRACTED_CHARS = 20000


def _is_public_address(host: str) -> bool:
    """True only if EVERY address `host` resolves to is publicly routable.

    Every address, not the first: a name that answers with one public A record
    and one 127.0.0.1 would otherwise pass here and be fetched on whichever the
    browser's own resolver picked.
    """
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local  # 169.254.0.0/16 — the cloud metadata service
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def assert_public_http_url(url: str) -> str:
    """Return `url` if the server may fetch it, otherwise refuse.

    Not `builder.utils.make_safe_get_request`'s check: that one compares the
    resolved address against string prefixes ("127", "10", "192", "172"), which
    both over-matches (172.32.x is public) and misses IPv6, 169.254.x and
    100.64/10.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        frappe.throw(_("Only http and https addresses can be imported"))
    if not _is_public_address(parsed.hostname):
        frappe.throw(_("This address is not reachable from the public internet"))
    return url


# JS run in the page to collect design tokens + content via getComputedStyle.
_COLLECT_JS = r"""
() => {
  const bg = {}, fg = {}, bd = {};
  const bump = (m, c) => {
    if (!c || c === 'transparent' || c.startsWith('rgba(0, 0, 0, 0')) return;
    m[c] = (m[c] || 0) + 1;
  };
  let n = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (n++ > 4000) break;
    const r = el.getBoundingClientRect();
    if (r.width < 3 || r.height < 3) continue;
    const s = getComputedStyle(el);
    bump(bg, s.backgroundColor); bump(fg, s.color); bump(bd, s.borderColor);
  }
  const font = (sel) => { const e = document.querySelector(sel); return e ? getComputedStyle(e).fontFamily : ''; };
  const btn = document.querySelector('button, .btn, a.button, [class*="btn"]');
  const headings = [...document.querySelectorAll('h1, h2, h3')]
    .map(h => (h.innerText || '').trim()).filter(Boolean).slice(0, 15);
  return {
    bg, fg, bd,
    headingFont: font('h1') || font('h2') || font('h3'),
    bodyFont: font('p') || font('body'),
    radius: btn ? getComputedStyle(btn).borderRadius : '',
    headings,
    title: document.title || '',
    text: (document.body.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 6000),
  };
}
"""


def _to_hex(css_color: str):
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", css_color or "")
    if not m:
        return None
    r, g, b = (int(m.group(i)) for i in (1, 2, 3))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hsl(hex_color: str):
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, lightness


def _derive_palette(color_counts: dict) -> list:
    """Pick up to 2 brand colors: most-frequent SATURATED, non-neutral colors,
    distinct in hue. Neutrals (grey/white/black) are skipped — they're chrome."""
    scored = []
    for css, count in color_counts.items():
        hexv = _to_hex(css)
        if not hexv:
            continue
        h, s, lightness = _hsl(hexv)
        if s < 0.2 or lightness > 0.92 or lightness < 0.08:
            continue  # neutral / near-white / near-black
        scored.append((count, h, hexv))
    scored.sort(reverse=True)
    palette, hues = [], []
    for _, h, hexv in scored:
        if all(min(abs(h - hh), 1 - abs(h - hh)) > 0.08 for hh in hues):
            palette.append(hexv)
            hues.append(h)
        if len(palette) >= 2:
            break
    return palette


def _first_font(font_family: str) -> str:
    if not font_family:
        return ""
    first = font_family.split(",")[0].strip().strip('"').strip("'")
    return first


def _radius_style(radius: str) -> str:
    m = re.match(r"(\d+)", radius or "")
    if not m:
        return ""
    px = int(m.group(1))
    if px >= 9999 or px >= 40:
        return "pill"
    if px >= 10:
        return "rounded"
    if px >= 3:
        return "subtle"
    return "none"


def extract_site(url: str, timeout: int = 30000) -> dict:
    """Load a live site and extract brand tokens + content + a screenshot.

    Returns: {palette[], heading_font, body_font, radius_style, headings[],
    text, screenshot (bytes), title}. Raises on Playwright/browser errors.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError("Playwright required: pip install playwright && playwright install chromium")

    # //// Neoffice — the URL is checked here too, not only at the whitelisted entry:
    # //// extract_site is called from bench and from the chat's URL handler as well.
    assert_public_http_url(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            # //// Neoffice — every request the browser makes is re-checked, not just the URL
            # //// we typed. Chromium follows redirects itself: a public URL answering 302 →
            # //// http://169.254.169.254/ would be fetched with the first check already
            # //// passed and long forgotten. A route handler is the only place that sees
            # //// each hop. Resolutions are memoised so a page of 80 assets does not do 80
            # //// DNS lookups.
            seen: dict[str, bool] = {}

            def _gate(route, request):
                host = urlparse(request.url).hostname or ""
                allowed = seen.get(host)
                if allowed is None:
                    allowed = urlparse(request.url).scheme in _ALLOWED_SCHEMES and _is_public_address(host)
                    seen[host] = allowed
                if allowed:
                    route.continue_()
                else:
                    ai_log("warning", "Blocked non-public request during site extraction", host=host)
                    route.abort()

            page.route("**/*", _gate)
            page.goto(url, timeout=timeout, wait_until="networkidle")
            page.wait_for_timeout(800)
            data = page.evaluate(_COLLECT_JS)
            shot = page.screenshot(full_page=False, type="png")
        finally:
            browser.close()

    all_colors = {}
    for bucket in ("bg", "fg", "bd"):
        for css, cnt in (data.get(bucket) or {}).items():
            all_colors[css] = all_colors.get(css, 0) + cnt

    result = {
        "url": url,
        "title": data.get("title", ""),
        "palette": _derive_palette(all_colors),
        "heading_font": _first_font(data.get("headingFont", "")),
        "body_font": _first_font(data.get("bodyFont", "")),
        "radius_style": _radius_style(data.get("radius", "")),
        "headings": data.get("headings", []),
        "text": data.get("text", ""),
        "screenshot": shot,
    }
    ai_log("info", "Existing-site extraction",
           url=url, palette=result["palette"],
           heading_font=result["heading_font"], chars=len(result["text"]))
    return result


@frappe.whitelist()
# //// Neoffice — builder role required: this makes the SERVER load an arbitrary URL in a
# //// headless browser and hands back what it saw. It was a bare whitelist, so any
# //// authenticated account had a scanner into the private network. See require_builder_role.
def import_existing_site(url: str, session_id: str = None) -> dict:
    """Whitelisted: extract a client's existing site and seed the session brief
    (palette + fonts) + store its content as a Builder Content Asset + the
    screenshot as design inspiration. The 'we already have a site' path."""
    # //// Neoffice — the role gate (see the marker above the decorator).
    require_builder_role()

    if not url:
        frappe.throw(_("A site URL is required"))
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    # //// Neoffice — refuse before launching a browser at all (extract_site re-checks, and
    # //// checks every redirect hop): a refusal must not cost a Chromium start-up.
    assert_public_http_url(url)

    data = extract_site(url)

    # 1) Screenshot → private File (design reference / brief vision)
    screenshot_url = None
    try:
        fdoc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"existing_site_{frappe.generate_hash(length=6)}.png",
            # //// Neoffice — private (was is_private: 0). This is a photograph of a page the
            # //// server fetched on someone's behalf, saved under a guessable-ish name in
            # //// /files/: on a public site it was world-readable. Nothing published needs
            # //// it — it feeds the brief and the vision model server-side — and its owner
            # //// (the importer) still reads it in the chat, which is what File's own
            # //// has_permission grants.
            "is_private": 1,
            "content": data["screenshot"],
        }).insert(ignore_permissions=True)
        screenshot_url = fdoc.file_url
    except Exception as e:
        ai_log("warning", "Existing-site screenshot save failed", error=str(e)[:150])

    # 2) Content → a Builder Content Asset (Document, already understood)
    if session_id and data.get("text"):
        # //// Neoffice — the session must be the caller's own: without this, a builder user
        # //// seeded somebody else's brief with a site of their choosing (and with text that
        # //// then reaches the generation prompt).
        from builder.builder_chat_service import get_owned_chat_session

        get_owned_chat_session(session_id)
        asset = frappe.new_doc("Builder Content Asset")
        asset.session_id = session_id
        asset.asset_type = "Document"
        asset.original_filename = f"{data.get('title') or url}"
        asset.status = "understood"
        asset.suggested_section = "home"
        asset.summary = (data.get("title") or "")[:240]
        # //// Neoffice — capped at MAX_EXTRACTED_CHARS (was 140000, i.e. no real cap). This
        # //// text is scraped from a page we do not control and lands in the generation
        # //// prompt; 140 KB of it is a bill, a context overflow, and a bigger place to hide
        # //// an instruction. The collector's own 6000-char slice runs in the scraped page's
        # //// JS context, so it is the page's promise, not ours.
        asset.extracted_text = (
            "\n".join(data.get("headings", [])) + "\n\n" + data.get("text", "")
        )[:MAX_EXTRACTED_CHARS]
        asset.tags = "existing-site"
        if screenshot_url:
            asset.file = screenshot_url
        asset.insert(ignore_permissions=True)

    # 3) Seed brief palette/fonts on the session (set-if-absent — don't clobber
    #    explicit user choices made earlier in the chat)
    if session_id:
        # //// Neoffice — owner-scoped, like the asset above (see get_owned_chat_session).
        from builder.builder_chat_service import get_owned_chat_session

        sess = get_owned_chat_session(session_id)
        palette = data.get("palette") or []
        if palette and not sess.primary_color:
            sess.primary_color = palette[0]
        if len(palette) >= 2 and not sess.secondary_color:
            sess.secondary_color = palette[1]
        if data.get("heading_font") and not sess.heading_font:
            sess.heading_font = data["heading_font"]
        if data.get("body_font") and not sess.body_font:
            sess.body_font = data["body_font"]
        if screenshot_url:
            existing = frappe.parse_json(sess.inspiration_urls) if sess.inspiration_urls else []
            existing.append({"url": screenshot_url, "name": data.get("title") or url, "type": "existing_site"})
            sess.inspiration_urls = frappe.as_json(existing)
        sess.save(ignore_permissions=True)
        frappe.db.commit()

    return {
        "success": True,
        "title": data.get("title"),
        "palette": data.get("palette"),
        "heading_font": data.get("heading_font"),
        "body_font": data.get("body_font"),
        "radius_style": data.get("radius_style"),
        "headings": data.get("headings", [])[:8],
        "text_chars": len(data.get("text", "")),
        "screenshot_url": screenshot_url,
    }
