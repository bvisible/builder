# //// Neoffice — added file (no upstream equivalent): full-page screenshots through Playwright (also
# //// used by the visual loop). builder/site_ai/** = the Neoffice AI site generator; frappe/builder ships no
# //// such module. First commit 5c48fc99 2026-02-04.
"""
Website Screenshotter for Inspiration Module

Captures full-page screenshots of websites using Playwright.
"""

import asyncio
import io
import os
from typing import Optional
from urllib.parse import unquote, urlparse

import frappe

# //// Neoffice — the module logs through the generator's own log (see the navigation guard below).
from builder.site_ai.logging import ai_log

# Chromium's texture limit is 16384 px; a capture stays well under it
MAX_CAPTURE_HEIGHT = 12000


def static_file_for(url: str, roots: Optional[dict]) -> Optional[str]:
    """The file on disk behind a static URL of the site being rendered.

    gunicorn serves neither /assets nor /files — nginx does, in front of it — so a page
    rendered through the loopback came back without its reset stylesheet and without a
    single photo, and the vision model reviewed (and "fixed") a page no visitor sees:
    every capture of 2026-09-08. `roots` maps a URL prefix to a directory. Returns the
    file path, "" when the prefix matches but nothing is there (a 404, never a fall
    through to the app), None when the URL is not static."""
    path = unquote(urlparse(url).path)
    for prefix, root in sorted((roots or {}).items(), key=lambda item: -len(item[0])):
        if not path.startswith(prefix):
            continue
        base = os.path.normpath(root)
        candidate = os.path.normpath(os.path.join(base, path[len(prefix):]))
        if candidate == base or not candidate.startswith(base + os.sep):
            return ""
        return candidate if os.path.isfile(candidate) else ""
    return None


class WebsiteScreenshotter:
    """
    Captures screenshots of websites for design inspiration.

    Uses Playwright to render pages headlessly and capture full-page screenshots.
    """

    def __init__(self, viewport_width: int = 1440, viewport_height: int = 900):
        """
        Initialize the screenshotter.

        Args:
            viewport_width: Default viewport width (desktop)
            viewport_height: Default viewport height
        """
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    async def capture_async(
        self,
        url: str,
        full_page: bool = True,
        timeout: int = 30000,
        static_roots: Optional[dict] = None,
        # //// Neoffice — capture_async forwards a headers dict so the loopback render can carry X-Frappe-Site-Name (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
        headers: Optional[dict] = None,
    ) -> dict:
        """
        Capture a screenshot of the given URL asynchronously.

        Args:
            url: URL to capture
            full_page: Whether to capture the full page or just viewport
            timeout: Navigation timeout in milliseconds

        Returns:
            dict with screenshot bytes, title, and metadata
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for website screenshots. "
                "Install with: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(
                    viewport={"width": self.viewport_width, "height": self.viewport_height}
                )

                # //// Neoffice — send the headers so the loopback render is named by header, not by host (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
                # a loopback render names its site by header (visual_check.loopback_headers)
                if headers:
                    await page.set_extra_http_headers({str(k): str(v) for k, v in headers.items()})

                # a loopback render finds its stylesheets and photos on disk (static_file_for)
                if static_roots:

                    async def serve_static(route, request):
                        target = static_file_for(request.url, static_roots)
                        if target is None:
                            await route.continue_()
                        elif target == "":
                            await route.fulfill(status=404, body=b"")
                        else:
                            await route.fulfill(path=target)

                    await page.route("**/*", serve_static)

                # Navigate to URL
                # //// Neoffice — networkidle never arrives on a commercial site: trackers,
                # //// chat widgets and video keep a request in flight for as long as the page
                # //// is open, so the wait ran to the timeout and the capture was lost. Two of
                # //// six sites a client sent as references were dropped this way. The document
                # //// being parsed is what a screenshot needs; the settle below covers the rest,
                # //// and a page that never even parses still falls back to whatever has painted.
                try:
                    await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                except Exception as e:
                    if not page.url or page.url == "about:blank":
                        raise
                    ai_log("warning", "Navigation did not complete, capturing what painted", url=url, error=str(e)[:120])
                # let the fold settle: fonts, hero image, the first paint of a framework
                try:
                    await page.wait_for_load_state("load", timeout=8000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)

                # The site's pages scroll inside <body> (html and body are 100% high,
                # overflow-y auto): the document itself is one viewport tall, and a
                # full-page capture of it was the hero over a blank (2026-09-08). Let the
                # document grow instead, so the capture scrolls it like a visitor would
                # and a 100vh hero keeps the height of the viewport, not of the page.
                if full_page:
                    try:
                        await page.add_style_tag(
                            content="html,body{height:auto!important;max-height:none!important;overflow:visible!important}"
                        )
                    except Exception:
                        pass

                # Lazy images only load once scrolled into view: walk the page to the
                # bottom and back before a full-page capture, or every photo below the
                # fold is missing from the screenshot (and a reviewer reports it broken).
                if full_page:
                    try:
                        await page.evaluate(
                            """async () => {
                                const step = Math.max(400, window.innerHeight);
                                for (let y = 0; y < document.body.scrollHeight; y += step) {
                                    window.scrollTo(0, y);
                                    await new Promise(r => setTimeout(r, 120));
                                }
                                window.scrollTo(0, 0);
                            }"""
                        )
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    # A page that still scrolls inside a box of its own (a layout the
                    # style above does not reach) gets a viewport as tall as its content
                    # as a last resort; a page whose document grew keeps the real viewport,
                    # so its 100vh sections stay one screen tall (the Boutique hero came
                    # out 4 000 px high with a tall viewport, 2026-09-08).
                    try:
                        doc_height, body_height = await page.evaluate(
                            "() => [document.documentElement.scrollHeight, document.body.scrollHeight]"
                        )
                        if int(doc_height or 0) <= self.viewport_height < int(body_height or 0):
                            await page.set_viewport_size(
                                {"width": self.viewport_width, "height": min(int(body_height), MAX_CAPTURE_HEIGHT)}
                            )
                            await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass

                # Wait a bit for any animations to settle
                await page.wait_for_timeout(1000)

                # Capture screenshot. Animations are run to their end first: a section that
                # fades in as it scrolls into view keeps its `from { opacity: 0 }` outside
                # the viewport, and the full-page capture of the B2C home showed the hero
                # over 6000 px of blank (2026-09-08).
                screenshot_bytes = await page.screenshot(
                    full_page=full_page,
                    type="png",
                    animations="disabled",
                    caret="hide",
                )

                # Get page metadata
                title = await page.title()

                # Get page dimensions
                dimensions = await page.evaluate("""
                    () => ({
                        width: document.documentElement.scrollWidth,
                        height: document.documentElement.scrollHeight
                    })
                """)

                return {
                    "screenshot": screenshot_bytes,
                    "title": title,
                    "url": url,
                    "width": dimensions.get("width", self.viewport_width),
                    "height": dimensions.get("height", self.viewport_height),
                    "viewport_width": self.viewport_width,
                    "success": True,
                }

            finally:
                await browser.close()

    def capture(
        self,
        url: str,
        full_page: bool = True,
        timeout: int = 30000,
        static_roots: Optional[dict] = None,
        # //// Neoffice — capture() takes headers too, threaded down to capture_async (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
        headers: Optional[dict] = None,
    ) -> dict:
        """
        Capture a screenshot synchronously (wrapper around async method).

        Args:
            url: URL to capture
            full_page: Whether to capture the full page or just viewport
            timeout: Navigation timeout in milliseconds

        Returns:
            dict with screenshot bytes, title, and metadata
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # //// Neoffice — pass headers through to capture_async (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
        return loop.run_until_complete(
            self.capture_async(url, full_page, timeout, static_roots, headers)
        )

    def capture_and_save(
        self,
        url: str,
        doc_name: Optional[str] = None,
        full_page: bool = True,
        static_roots: Optional[dict] = None,
        # //// Neoffice — capture_and_save takes headers too, for the same loopback site-name header (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
        headers: Optional[dict] = None,
    ) -> dict:
        """
        Capture screenshot and save to Frappe File.

        Args:
            url: URL to capture
            doc_name: Optional document name to link file to
            full_page: Whether to capture the full page

        Returns:
            dict with file_url, file_doc, and capture metadata
        """
        # //// Neoffice — pass headers through to capture (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
        result = self.capture(url, full_page=full_page, static_roots=static_roots, headers=headers)

        if not result.get("success"):
            return result

        # Generate filename from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace(".", "_")
        filename = f"inspiration_{domain}_{frappe.generate_hash(length=6)}.png"

        # Save to Frappe File
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "content": result["screenshot"],
            "is_private": 0,
        })
        file_doc.save(ignore_permissions=True)

        return {
            "file_url": file_doc.file_url,
            "file_doc_name": file_doc.name,
            "title": result.get("title"),
            "url": url,
            "width": result.get("width"),
            "height": result.get("height"),
            "success": True,
        }


# //// Neoffice — module-level helper takes headers too, for the loopback site-name header (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
def capture_website_screenshot(url: str, full_page: bool = True, static_roots: Optional[dict] = None, headers: Optional[dict] = None, viewport_width: Optional[int] = None) -> dict:
    """
    Convenience function to capture a website screenshot.

    Args:
        url: URL to capture
        full_page: Whether to capture full page

    Returns:
        dict with capture result
    """
    # //// Neoffice — viewport_width: the review also looks at the page on a phone (2026-09-16).
    # //// A review that only ever saw the 1440 px capture shipped a contact page whose title
    # //// wrapped letter by letter on a narrow column: what breaks first breaks on the phone.
    screenshotter = WebsiteScreenshotter(viewport_width=viewport_width) if viewport_width else WebsiteScreenshotter()
    # //// Neoffice — pass headers through to capture_and_save (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
    return screenshotter.capture_and_save(url, full_page=full_page, static_roots=static_roots, headers=headers)


# //// Neoffice ▼▼▼ — the measured look at a rendered page (2026-09-16). A vision model reading a
# //// screenshot misses what a ruler catches: a heading wrapped letter by letter in a 90 px column,
# //// an ornament 120 px outside the page, a carousel with nothing in it, a picture that never
# //// loaded, the site's title band missing because the page opened with its own h1. None of
# //// these is a matter of taste: each is a number the browser already knows. So they are read
# //// off the rendered page, at three widths, before any model is asked its opinion — for the
# //// price of a page load, no tokens at all — and what they find goes into the revision as
# //// facts, and into the verdict as a refusal when the page is broken.
LAYOUT_PROBE = r"""
() => {
  const vw = window.innerWidth;
  const out = [];
  const text = (el) => ((el && (el.innerText || el.textContent)) || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const chrome = (el) => !!el.closest('header, footer, nav, .site-page-header, .navbar, #navbar, [data-chrome]');
  const clipped = (el) => {
    for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (/hidden|clip|auto|scroll/.test(s.overflow + ' ' + s.overflowX)) return true;
    }
    return false;
  };
  const where = (el) => el.tagName.toLowerCase() + (text(el) ? ' "' + text(el) + '"' : (el.className && typeof el.className === 'string' ? ' .' + el.className.trim().split(/\s+/)[0] : ''));
  const body = document.body;

  // 1. the page is wider than the screen: a horizontal scrollbar for the visitor
  const sw = Math.max(document.documentElement.scrollWidth, body.scrollWidth);
  if (sw > vw + 2) out.push({kind: 'overflow', severity: 'high', where: 'page', detail: 'the page is ' + sw + 'px wide on a ' + vw + 'px screen: something sticks out and the visitor gets a horizontal scrollbar'});

  // 2. what sticks out of the screen: with nothing to clip it, anything; clipped, only what
  // carries content (a tile with a caption cut at the edge is a defect, a bleeding ornament
  // inside an overflow-hidden section is a choice)
  // the nearest ancestor that clips, and whether it scrolls instead of hiding
  const clipper = (el) => {
    for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      const o = s.overflowX + ' ' + s.overflow;
      if (/hidden|clip/.test(o)) return {el: p, scrolls: false};
      if (/auto|scroll/.test(o)) return {el: p, scrolls: true};
    }
    return null;
  };
  let stuck = 0, cut = 0;
  const reported = [];
  for (const el of body.querySelectorAll('*')) {
    if (stuck >= 4 && cut >= 4) break;
    if (chrome(el) || !visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (reported.some(p => p.contains(el))) continue;
    const c = clipper(el);
    if (!c) {
      if (!(r.right > vw + 8 || r.left < -8) || stuck >= 4) continue;
      stuck++; reported.push(el);
      out.push({kind: 'sticks-out', severity: 'high', where: where(el), detail: 'spans ' + Math.round(r.left) + 'px to ' + Math.round(r.right) + 'px on a ' + vw + 'px screen, outside the page; an ornament that bleeds must sit inside a section with overflow hidden, and nothing else may leave the page'});
      continue;
    }
    // clipped: a defect only when CONTENT is cut by the clipping box (a tile with its caption
    // cut at the container's edge, seen on a home 2026-09-16); a bleeding ornament is a choice
    const box = c.el.getBoundingClientRect();
    if (!(r.right > box.right + 8 || r.left < box.left - 8)) continue;
    if (text(el).length < 3 || r.width < 80 || cut >= 4) continue;
    cut++; reported.push(el);
    out.push({kind: 'content-cut', severity: c.scrolls ? 'medium' : 'high', where: where(el), detail: 'spans ' + Math.round(r.left) + 'px to ' + Math.round(r.right) + 'px but its container ends at ' + Math.round(box.right) + 'px' + (c.scrolls ? ' and only scrolls sideways: the visitor sees it cut unless they scroll' : ': it is cut at the edge') + ' — a row wider than its container (fixed tile widths, a grid that does not wrap); make the row fit or wrap'});
  }

  // 3. a text starved of width: a heading wrapped letter by letter, a paragraph in a sliver
  let starved = 0;
  for (const el of body.querySelectorAll('h1, h2, h3, p, li, a, span, td')) {
    if (starved >= 6) break;
    if (chrome(el) || !visible(el)) continue;
    const t = text(el);
    if (t.length < 12) continue;
    if ([...el.children].some(c => /^(h1|h2|h3|p|div|ul|ol|section|table)$/i.test(c.tagName))) continue;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    const lh = parseFloat(s.lineHeight) || (parseFloat(s.fontSize) || 16) * 1.3;
    const lines = r.height / lh;
    const heading = /^h[1-3]$/i.test(el.tagName);
    // a heading is starved when its column holds fewer than ~7 of its own characters per
    // line: a 90px display headline in a 200px track wraps word by word (seen on a home,
    // 2026-09-16), and 200px is plenty for a 20px h3
    const fs = parseFloat(s.fontSize) || 16;
    if ((heading && r.width < Math.max(200, fs * 7) && lines > 2.5) || (!heading && r.width < 130 && lines > 4)) {
      starved++;
      out.push({kind: 'starved-text', severity: 'high', where: where(el), detail: Math.round(r.width) + 'px wide for a ' + Math.round(fs) + 'px type, wrapped on ' + Math.round(lines) + ' lines: its column is starved (a grid track of minmax(0, 1fr) or a fixed narrow width); give the text a real minimum width, or stack the columns at this screen size'});
    }
  }

  // 4. a live component with nothing to show
  const seen = new Set();
  for (const el of body.querySelectorAll('[class*="carousel"], [class*="listing"], [class*="-grid"], [class*="products"], [class*="brands"]')) {
    if (chrome(el) || !visible(el) || seen.has(el)) continue;
    if ([...seen].some(p => p.contains(el))) continue;
    seen.add(el);
    const t = text(el);
    if (!el.querySelector('img, a, .card, li') && (/aucun|no .* (available|found)|nothing|vide|empty/i.test(t) || t.length < 3)) {
      out.push({kind: 'empty-component', severity: 'high', where: where(el), detail: 'shows nothing (no item, no picture' + (t ? ', reads "' + t + '"' : '') + '): a heading over an empty block; drop the section or give the component the parameters that fill it'});
    }
  }

  // 5. a picture that never loaded
  let broken = 0;
  for (const img of body.querySelectorAll('img')) {
    if (broken >= 4 || chrome(img)) continue;
    const src = img.getAttribute('src') || '';
    if (img.complete && img.naturalWidth === 0 && /^\/(files|assets)\//.test(src)) {
      broken++;
      out.push({kind: 'broken-image', severity: 'high', where: 'img ' + src.slice(0, 80), detail: 'the picture did not load: the file is missing or the path is wrong'});
    }
  }

  // 5b. a photograph rendered as a thumbnail: its box collapsed (a 30px picture where a hero photo was meant, 2026-09-16)
  let tiny = 0;
  for (const img of body.querySelectorAll('img')) {
    if (tiny >= 3 || chrome(img) || !visible(img)) continue;
    const r = img.getBoundingClientRect();
    if (img.naturalWidth >= 400 && r.width < 64 && r.height < 64) {
      tiny++;
      out.push({kind: 'collapsed-image', severity: 'high', where: 'img ' + (img.getAttribute('src') || '').slice(0, 80), detail: 'a ' + img.naturalWidth + 'px photograph rendered ' + Math.round(r.width) + 'px wide: its box collapsed (no width, no height, or a flex child with no basis); give the picture its size'});
    }
  }

  // 5c. text unreadable on the solid background behind it (a photograph or a gradient behind
  // it is left to the judge: the probe cannot know what a picture paints)
  const rgba = (v) => { const m = (v || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = (c) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ground = (el) => {
    for (let p = el; p && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      const c = rgba(s.backgroundColor);
      if (c && c.a > 0.9) return c;
      // a veil (a translucent tint over a picture): what shows through is unknowable here
      if (c && c.a > 0.15) return null;
    }
    return {r: 255, g: 255, b: 255, a: 1};
  };
  // a label ON a photograph (the picture is a sibling under it, not an ancestor): the probe
  // called "SNOW" over a snow photograph white-on-white (2026-09-17); a picture behind the
  // text is the judge's to read
  const pictures = [...body.querySelectorAll('img, video, svg')].filter(i => visible(i) && i.getBoundingClientRect().width > 80).map(i => i.getBoundingClientRect());
  const onPicture = (r) => { const cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2; return pictures.some(b => cx >= b.left && cx <= b.right && cy >= b.top && cy <= b.bottom); };
  let faint = 0;
  for (const el of body.querySelectorAll('h1, h2, h3, p, a, li, span')) {
    if (faint >= 4 || chrome(el) || !visible(el)) continue;
    const t = text(el);
    if (t.length < 3 || [...el.children].some(c => /^(h1|h2|h3|p|div|ul|ol|section)$/i.test(c.tagName))) continue;
    const s = getComputedStyle(el);
    if (onPicture(el.getBoundingClientRect())) continue;
    const ink = rgba(s.color); const back = ground(el);
    if (!ink || !back || ink.a < 0.5) continue;
    const l1 = lum(ink), l2 = lum(back);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const fs = parseFloat(s.fontSize) || 16;
    const large = fs >= 24 || (fs >= 19 && parseInt(s.fontWeight, 10) >= 700);
    if (ratio < (large ? 3 : 4.5)) {
      faint++;
      // below 2.5:1 the text is invisible (white on white): refused; above it, a colour
      // that fails the accessibility ratio (an accent word on white): a point to fix
      out.push({kind: 'unreadable-text', severity: ratio < 2.5 ? 'high' : 'medium', where: where(el), detail: 'contrast ' + ratio.toFixed(1) + ':1 between ' + s.color + ' and the background ' + `rgb(${back.r}, ${back.g}, ${back.b})` + ' (needs ' + (large ? '3' : '4.5') + ':1): ' + (ratio < 2.5 ? 'the text cannot be read; use the text token on this ground' : 'hard to read; darken the colour or enlarge the text')});
    }
  }

  // 6. a section with nothing in it
  for (const sec of body.querySelectorAll('section')) {
    if (chrome(sec) || !visible(sec)) continue;
    const r = sec.getBoundingClientRect();
    if (r.height < 24 && !text(sec) && !sec.querySelector('img, svg')) out.push({kind: 'empty-section', severity: 'medium', where: 'section', detail: 'an empty section of ' + Math.round(r.height) + 'px: nothing in it, remove it'});
  }

  // what the page is made of, for the rules the caller knows (the route, the site)
  const band = document.querySelector('.site-page-header');
  const bodyH1 = [...body.querySelectorAll('h1')].filter(h => !chrome(h)).length;
  const headerLogo = !!document.querySelector('header img, header svg, .navbar-brand img, .site-header img, [class*="logo"] img');
  const headerText = text(document.querySelector('header [class*="logo"], .navbar-brand, .site-header [class*="brand"]'));
  const sample = ((body.innerText || '')).replace(/\s+/g, ' ').slice(0, 6000);
  return {findings: out, facts: {band: !!band, body_h1: bodyH1, header_logo: headerLogo, header_text: headerText, width: vw, height: Math.max(document.documentElement.scrollHeight, body.scrollHeight), title: document.title, text_sample: sample}};
}
"""

MEASURE_WIDTHS = (1440, 768, 375)


async def _measure_async(url: str, widths=MEASURE_WIDTHS, static_roots: Optional[dict] = None, headers: Optional[dict] = None, timeout: int = 30000) -> dict:
    """The page loaded once per width, and LAYOUT_PROBE run on it. Returns
    {"status": <http status>, "widths": {width: {"findings": [...], "facts": {...}}}}."""
    from playwright.async_api import async_playwright

    result: dict = {"status": None, "widths": {}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={"width": widths[0], "height": 900})
            if headers:
                await page.set_extra_http_headers({str(k): str(v) for k, v in headers.items()})
            if static_roots:

                async def serve_static(route, request):
                    target = static_file_for(request.url, static_roots)
                    if target is None:
                        await route.continue_()
                    elif target == "":
                        await route.fulfill(status=404, body=b"")
                    else:
                        await route.fulfill(path=target)

                await page.route("**/*", serve_static)
            response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            result["status"] = response.status if response else None
            try:
                await page.wait_for_load_state("load", timeout=8000)
            except Exception:
                pass
            # the pages scroll inside <body>: let the document grow so the measures see the
            # whole page, as the capture does (see capture_async)
            try:
                await page.add_style_tag(content="html,body{height:auto!important;max-height:none!important;overflow:visible!important}")
            except Exception:
                pass
            for width in widths:
                try:
                    await page.set_viewport_size({"width": int(width), "height": 900})
                    await page.wait_for_timeout(400)
                    result["widths"][int(width)] = await page.evaluate(LAYOUT_PROBE)
                except Exception as e:
                    result["widths"][int(width)] = {"findings": [], "facts": {}, "error": str(e)[:160]}
        finally:
            await browser.close()
    return result


def measure_layout(url: str, widths=MEASURE_WIDTHS, static_roots: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    """Synchronous wrapper of _measure_async. Never raises: a page that cannot be measured
    reports the error, and the caller decides what an unmeasured page is worth."""
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(_measure_async(url, widths, static_roots, headers))
    except Exception as e:
        return {"status": None, "widths": {}, "error": str(e)[:200]}
# //// Neoffice ▲▲▲


