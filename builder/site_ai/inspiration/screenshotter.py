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
                await page.goto(url, timeout=timeout, wait_until="networkidle")

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
def capture_website_screenshot(url: str, full_page: bool = True, static_roots: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    """
    Convenience function to capture a website screenshot.

    Args:
        url: URL to capture
        full_page: Whether to capture full page

    Returns:
        dict with capture result
    """
    screenshotter = WebsiteScreenshotter()
    # //// Neoffice — pass headers through to capture_and_save (0445cc94 "fix(visual-check): the loopback render names its site by header, not by host")
    return screenshotter.capture_and_save(url, full_page=full_page, static_roots=static_roots, headers=headers)
