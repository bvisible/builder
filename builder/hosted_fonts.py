# //// Neoffice — added file (no upstream equivalent): the site serves its own copy of the Google
# //// fonts it uses (SEO / GEO plan, D-10). A public page that linked fonts.googleapis.com handed
# //// every visitor's IP address to Google; the files now come from the site itself.
"""The site's own copy of the Google fonts its pages use.

Every font stylesheet a public page links goes through `local_urls()`: the Google stylesheet is
fetched once, server side, the font files it names are stored beside it in the site's public
files, and the page links the copy. A visitor's browser never meets Google.

The copy is made by the first page that asks for it (under a second in general, once per
stylesheet and per site) and kept for good: a stylesheet URL always names the same files, so no
cache clear, restart or migrate has to touch them. When Google cannot be reached, the family is
left out, the text falls back on the next font of its stack, and the copy is tried again ten
minutes later rather than on every page.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, quote_plus, urlparse

import frappe

GOOGLE_CSS = "https://fonts.googleapis.com/"
GOOGLE_FILES = "https://fonts.gstatic.com/"
FONT_DIR = "builder_fonts"
#: Google answers each browser with the format it reads: a current Chrome gets woff2 split by
#: unicode-range, which every browser the sites support reads as well.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
#: (connect, read): the first page to ask waits for the copy, so an unreachable Google must fail fast.
FETCH_TIMEOUT = (3.05, 10)
RETRY_AFTER = 600
#: The chrome's weights, the four theme_variables.html has always loaded.
CHROME_WEIGHTS = "400;500;600;700"

_FONT_URL = re.compile(r"url\((['\"]?)(https://[^)'\"]+)\1\)")


def local_urls(urls) -> list[str]:
	"""The site's own copies of these stylesheet URLs, in order. A Google stylesheet the site could
	not copy is left out, never linked from Google; any other URL passes unchanged."""
	out = []
	for url in urls or []:
		local = local_url(url) if str(url).startswith(GOOGLE_CSS) else url
		if local:
			out.append(local)
	return out


def local_url(google_url: str) -> str | None:
	"""The URL of the site's copy of one Google stylesheet, made on the first request; None when it
	cannot be made now."""
	name = stylesheet_name(google_url)
	folder = font_folder()
	if os.path.exists(os.path.join(folder, name)):
		return f"/files/{FONT_DIR}/{name}"
	if recently_failed(name):
		return None
	try:
		copy_stylesheet(google_url, folder, name)
	except Exception as e:
		remember_failure(name)
		frappe.log_error("Google font not copied to the site", f"{google_url}\n\n{e}")
		return None
	return f"/files/{FONT_DIR}/{name}"


def chrome_stylesheets(theme: dict | None) -> list[str]:
	"""The chrome's heading and body fonts, as the site's own copy."""
	theme = theme or {}
	return local_urls([chrome_font_url(theme.get("heading_font"), theme.get("body_font"))])


def chrome_font_url(heading_font: str | None, body_font: str | None) -> str:
	"""The chrome's two fonts in one Google request, as theme_variables.html built it: the heading
	font, then the body font when it differs, four weights each."""
	families = [heading_font or "Inter"]
	if (body_font or "Inter") != families[0]:
		families.append(body_font or "Inter")
	query = "&".join(f"family={quote_plus(family)}:wght@{CHROME_WEIGHTS}" for family in families)
	return f"{GOOGLE_CSS}css2?{query}&display=swap"


def stylesheet_name(google_url: str) -> str:
	"""A readable and stable file name: the families, then a digest of the whole URL."""
	families = [family.split(":")[0] for family in parse_qs(urlparse(google_url).query).get("family", [])]
	slug = re.sub(r"[^a-z0-9]+", "-", "-".join(families).lower()).strip("-")[:60] or "font"
	return f"{slug}-{hashlib.sha1(google_url.encode()).hexdigest()[:12]}.css"


def font_folder() -> str:
	folder = frappe.get_site_path("public", "files", FONT_DIR)
	os.makedirs(folder, exist_ok=True)
	return folder


def copy_stylesheet(google_url: str, folder: str, name: str) -> None:
	"""Fetch the stylesheet and every font file it names, and rewrite it to point at them. The
	stylesheet is written last: its presence says that every file it names is there."""
	import requests

	headers = {"User-Agent": USER_AGENT}
	response = requests.get(google_url, headers=headers, timeout=FETCH_TIMEOUT)
	response.raise_for_status()
	files = {}

	def to_local(match):
		remote = match.group(2)
		if not remote.startswith(GOOGLE_FILES):
			raise ValueError(f"a font file outside {GOOGLE_FILES}: {remote}")
		extension = os.path.splitext(urlparse(remote).path)[1] or ".woff2"
		files[remote] = hashlib.sha1(remote.encode()).hexdigest()[:16] + extension
		return f"url(/files/{FONT_DIR}/{files[remote]})"

	css = _FONT_URL.sub(to_local, response.text)
	if not files:
		raise ValueError("the stylesheet names no font file")
	missing = [(remote, os.path.join(folder, file_name)) for remote, file_name in files.items()]
	missing = [(remote, target) for remote, target in missing if not os.path.exists(target)]

	def fetch(item):
		remote, target = item
		font = requests.get(remote, headers=headers, timeout=FETCH_TIMEOUT)
		font.raise_for_status()
		write_file(target, font.content)

	if missing:
		with ThreadPoolExecutor(max_workers=min(8, len(missing))) as pool:
			list(pool.map(fetch, missing))
	write_file(os.path.join(folder, name), css.encode())


def write_file(path: str, content: bytes) -> None:
	"""Through a temporary file and a rename: two workers copying the same font at once never
	leave a half-written file behind."""
	temporary = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
	with open(temporary, "wb") as f:
		f.write(content)
	os.replace(temporary, path)


def recently_failed(name: str) -> bool:
	return bool(frappe.cache.get_value(f"builder_fonts_failed|{name}"))


def remember_failure(name: str) -> None:
	frappe.cache.set_value(f"builder_fonts_failed|{name}", 1, expires_in_sec=RETRY_AFTER)
