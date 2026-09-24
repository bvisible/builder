# //// Neoffice — added file (no upstream equivalent): the site's icon, one answer for every page
# //// of a site, in a format Google reads. neoffice-maintenance#691 (D27, D28), 2026-09-24.
#
# The icon is what Google prints next to a site's name in its results, and what a browser tab
# shows. Measured on 2026-09-24:
#   - a Builder page took its icon from the page or from Builder Settings, and our webpage.html
#     fell back to Neoffice's SVG: a client site with no icon of its own wore Neoffice's mark,
#     and Google does not read an SVG favicon at all (formats it lists since 2026-08-28: ICO,
#     PNG, GIF, JPEG, BMP, PPM, TIFF);
#   - the shop's pages, which frappe renders, took Website Settings' favicon instead, else
#     neoffice_theme's PNG: one domain, two icons;
#   - /favicon.ico answered 404 with a 342 KB error page.
#
# One order for every page of a site:
#   1. an icon somebody chose: the Builder page's, Builder Settings', Website Settings';
#   2. the site's own mark, when its chrome carries a picture close to a square (an emblem, a
#      monogram), trimmed and centred on a square PNG;
#   3. its initial, on the colour its buttons wear: a wordmark shrunk to 16 px is a smudge;
#   4. Neoffice's icon, for a site that has no name of its own.
# 2 to 4 are drawn here, served at /site-icon.png?v=<key> (the key changes with whatever they
# are drawn from, so the URL can be cached for a year), and /favicon.ico answers the same icon.
import hashlib
import io
import os
from urllib.parse import unquote, urlsplit

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

ICON_SIZE = 192  # a multiple of 48, as Google asks of a favicon
SQUARE_ENOUGH = 1.5  # a mark wider (or taller) than this reads as a smudge once made square
MARK_PADDING = 0.1  # of the side, around a mark
LETTER_HEIGHT = 0.56  # of the side, for an initial
LETTER_WIDTH = 0.72  # of the side, at most (a W, an M)
# Bump when the drawing changes: every key, hence every icon URL, changes with it.
DRAWING = "1"
CACHE_SECONDS = 30 * 24 * 3600
ROUTES = ("favicon.ico", "site-icon.png")
# A placeholder or the software's own name is no name: such a site gets Neoffice's icon.
GENERIC_NAMES = {"", "my site", "frappe", "erpnext", "neoffice"}
DRAWABLE = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
FALLBACK_MARKS = (
	("neoffice_theme", ("public", "images", "neoffice_icon.png")),
	# a bench without neoffice_theme (the CI, a standalone Builder): what set_favicon used
	# before this file (3acfd7d6)
	("builder", ("public", "frontend", "builder_logo.png")),
)
FONTS = (
	"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
	"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
MIME_TYPES = {
	".png": "image/png",
	".ico": "image/x-icon",
	".svg": "image/svg+xml",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".gif": "image/gif",
	".webp": "image/webp",
	".bmp": "image/bmp",
}


def site_icon(page_favicon: str | None = None) -> frappe._dict:
	"""The icon of the site being served: href, type, sizes, and where it comes from
	("chosen", "mark", "initial" or "fallback")."""
	chosen = chosen_icon(page_favicon)
	if chosen:
		return frappe._dict(href=chosen, type=_mime(chosen), sizes="", source="chosen")
	spec = drawn_icon()
	if not spec:
		return frappe._dict(href="", type="", sizes="", source="none")
	return frappe._dict(
		href=f"/site-icon.png?v={spec.key}",
		type="image/png",
		sizes=f"{ICON_SIZE}x{ICON_SIZE}",
		source=spec.source,
	)


def chosen_icon(page_favicon: str | None = None) -> str:
	"""An icon somebody picked: the page's own, then Builder Settings', then Website Settings'.
	Used as it is, whatever its format: somebody chose it."""
	for url in (page_favicon, _builder_setting("favicon"), _website_setting("favicon")):
		url = (url or "").strip()
		# "attach_files:" is what an emptied Attach field can hold (frappe skips it too)
		if url and url != "attach_files:":
			return url
	return ""


def drawn_icon(config=None) -> frappe._dict | None:
	"""What the site's icon is drawn from when nobody chose one, and the key of that drawing."""
	if config is None:
		from builder.hf_utils.header_footer import get_header_footer_config

		config = get_header_footer_config()
	if config:
		for url in logo_urls(config):
			path = _public_file(url)
			if path and _square_enough(path):
				return _spec("mark", path=path)
		letter = initial(site_name(config))
		if letter:
			from builder.hf_utils.header_footer import button_colours

			colours = button_colours(config.get_theme_data())
			return _spec("initial", letter=letter, background=colours["cta_hex"], ink=colours["cta_text"])
	for app, parts in FALLBACK_MARKS:
		if app in frappe.get_installed_apps():
			path = frappe.get_app_path(app, *parts)
			if os.path.isfile(path):
				return _spec("fallback", path=path)
	return None


def logo_urls(config) -> list[str]:
	"""The chrome's pictures, the footer's first: Nora asks the client for a second mark there
	(an emblem, a monogram), the header's being the wordmark."""
	urls = []
	if config.get("footer_logo_type") == "Image" and config.get("footer_logo_image"):
		urls.append(config.get("footer_logo_image"))
	if (config.get("logo_type") or "Image") == "Image" and config.get("logo_image"):
		urls.append(config.get("logo_image"))
	return urls


def site_name(config) -> str:
	"""The name the site goes by: its chrome's (the header's text, the logo's alternative
	text), else Website Settings'."""
	for name in (config.get("logo_text"), _website_setting("app_name")):
		name = (name or "").strip()
		if name.lower() not in GENERIC_NAMES:
			return name
	return ""


def initial(name: str) -> str:
	return next((char.upper() for char in name or "" if char.isalnum()), "")


def icon_png(spec: frappe._dict) -> bytes:
	"""The drawing, kept in the cache under its key: it only changes when its key does."""
	cache_key = f"site_icon_png::{spec.key}"
	png = frappe.cache.get_value(cache_key)
	if png is None:
		png = _draw(spec)
		frappe.cache.set_value(cache_key, png, expires_in_sec=CACHE_SECONDS)
	return png


def apply(context):
	"""update_website_context: every page of the site names the same icon. A Builder page has set
	it already (set_favicon, its own favicon first); the desk keeps Neoffice's."""
	if context.get("site_icon"):
		return
	request = getattr(frappe.local, "request", None)
	path = (getattr(request, "path", None) or "").strip("/")
	if path == "app" or path.startswith("app/"):
		return
	try:
		icon = site_icon()
	except Exception:
		frappe.log_error("Site icon: could not be resolved", frappe.get_traceback())
		return
	if icon.href:
		context.site_icon = icon
		context.favicon = icon.href


class SiteIconRenderer(BaseRenderer):
	"""/favicon.ico and /site-icon.png: the icon the site's pages name. Browsers and crawlers ask
	for /favicon.ico whatever the page says; it answered 404 with a full error page."""

	def can_render(self):
		return self.path in ROUTES

	def render(self):
		chosen = chosen_icon()
		if chosen:
			# The pages link a chosen icon directly: only /favicon.ico, or a page cached before
			# somebody chose one, lands here.
			response = Response(status=302)
			response.headers["Location"] = chosen
			response.headers["Cache-Control"] = "public, max-age=3600"
			return response
		spec = drawn_icon()
		if not spec:
			return Response(status=404)
		response = Response(icon_png(spec), mimetype="image/png")
		# The URL the pages print carries the key: that one can be kept for a year.
		versioned = frappe.form_dict.get("v") == spec.key
		response.headers["Cache-Control"] = (
			"public, max-age=31536000, immutable" if versioned else "public, max-age=86400"
		)
		return response


def _builder_setting(fieldname: str):
	return frappe.get_cached_value("Builder Settings", "Builder Settings", fieldname)


def _website_setting(fieldname: str):
	return frappe.db.get_single_value("Website Settings", fieldname, cache=True)


def _spec(source: str, path: str | None = None, **fields) -> frappe._dict:
	parts = [DRAWING, source]
	if path:
		stat = os.stat(path)
		parts += [path, str(stat.st_size), str(int(stat.st_mtime))]
	parts += [f"{name}={value}" for name, value in sorted(fields.items())]
	key = hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]
	return frappe._dict(source=source, path=path, key=key, **fields)


def _mime(url: str) -> str:
	return MIME_TYPES.get(os.path.splitext(urlsplit(url).path)[1].lower(), "")


def _public_file(url: str) -> str | None:
	"""The file on disk behind a public picture of this site; None for another host, a private
	file, or a format Pillow does not draw (an SVG)."""
	parts = urlsplit(url or "")
	path = unquote(parts.path)
	if parts.netloc or not path.startswith("/files/") or ".." in path:
		return None
	if os.path.splitext(path)[1].lower() not in DRAWABLE:
		return None
	full = frappe.get_site_path("public", path.lstrip("/"))
	return full if os.path.isfile(full) else None


def _square_enough(path: str) -> bool:
	"""Whether what the picture draws, once its margins are cut, is close enough to a square to
	survive being an icon. Measured once per version of the file."""
	stat = os.stat(path)
	cache_key = f"site_icon_ratio::{path}|{stat.st_size}|{int(stat.st_mtime)}"
	ratio = frappe.cache.get_value(cache_key)
	if ratio is None:
		ratio = _ink_ratio(path)
		frappe.cache.set_value(cache_key, ratio, expires_in_sec=CACHE_SECONDS)
	return bool(ratio) and 1 / SQUARE_ENOUGH <= ratio <= SQUARE_ENOUGH


def _ink_ratio(path: str) -> float:
	from PIL import Image

	try:
		with Image.open(path) as source:
			picture = source.convert("RGBA")
	except Exception:
		return 0.0
	picture.thumbnail((512, 512))
	box = _ink_box(picture)
	if not box:
		return 0.0
	left, top, right, bottom = box
	return (right - left) / max(bottom - top, 1)


def _ink_box(picture):
	"""Where an RGBA picture actually draws: what is not see-through when it has transparency,
	else what differs from its top-left corner (a logo on a white ground)."""
	from PIL import Image, ImageChops

	alpha = picture.getchannel("A")
	if alpha.getextrema()[0] < 250:
		return alpha.point(lambda value: 255 if value > 16 else 0).getbbox()
	ground = Image.new("RGB", picture.size, picture.getpixel((0, 0))[:3])
	difference = ImageChops.difference(picture.convert("RGB"), ground).convert("L")
	return difference.point(lambda value: 255 if value > 24 else 0).getbbox()


def _draw(spec: frappe._dict) -> bytes:
	if spec.source == "initial":
		picture = _draw_initial(spec.letter, spec.background, spec.ink)
	else:
		# the fallback is an icon already, drawn to its own edges
		picture = _draw_mark(spec.path, MARK_PADDING if spec.source == "mark" else 0)
	out = io.BytesIO()
	picture.save(out, "PNG", optimize=True)
	return out.getvalue()


def _draw_mark(path: str, padding: float):
	from PIL import Image, ImageOps

	with Image.open(path) as source:
		picture = source.convert("RGBA")
	transparent = picture.getchannel("A").getextrema()[0] < 250
	# a picture on a plain ground keeps that ground around it, never a see-through frame
	ground = (0, 0, 0, 0) if transparent else picture.getpixel((0, 0))
	box = _ink_box(picture)
	if box:
		picture = picture.crop(box)
	inner = round(ICON_SIZE * (1 - 2 * padding))
	picture = ImageOps.contain(picture, (inner, inner), Image.Resampling.LANCZOS)
	canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), ground)
	canvas.alpha_composite(picture, ((ICON_SIZE - picture.width) // 2, (ICON_SIZE - picture.height) // 2))
	return canvas


def _draw_initial(letter: str, background: str, ink: str):
	"""The letter centred on its ink, not on its line: a capital sits in the middle of the tile."""
	from PIL import Image, ImageDraw

	canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), background)
	draw = ImageDraw.Draw(canvas)
	size = round(ICON_SIZE * LETTER_HEIGHT * 1.4)
	font = _font(size)
	left, top, right, bottom = draw.textbbox((0, 0), letter, font=font)
	scale = min(
		ICON_SIZE * LETTER_HEIGHT / max(bottom - top, 1),
		ICON_SIZE * LETTER_WIDTH / max(right - left, 1),
	)
	font = _font(max(8, round(size * scale)))
	left, top, right, bottom = draw.textbbox((0, 0), letter, font=font)
	position = ((ICON_SIZE - (right - left)) / 2 - left, (ICON_SIZE - (bottom - top)) / 2 - top)
	draw.text(position, letter, font=font, fill=ink)
	return canvas


def _font(size: int):
	from PIL import ImageFont

	for path in FONTS:
		if os.path.isfile(path):
			return ImageFont.truetype(path, size)
	try:
		# Pillow >= 10.1 ships a scalable font of its own
		return ImageFont.load_default(size=size)
	except TypeError:
		return ImageFont.load_default()
