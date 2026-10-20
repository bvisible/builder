# //// Neoffice — added file (no upstream equivalent): the chrome's logo measured against the ground it sits on.
"""A dark logo on a dark footer is a barely visible rectangle (neoffice-maintenance #1766).

The contrast pass of a build (contrast.py) works on the page's blocks, never on the chrome, and
the chrome puts the site's logo image in the header and in the footer whatever colour the brief
gave them. This measures the two against each other when the chrome is set, at the end of a
build: the logo's ink (the opaque pixels of the file, as the browser paints them) against the
ground, with the same bar contrast.py uses for UI components. Below it, the site's name takes
the logo's place as text, which is what the header already shows when a site has no logo.

The logo image is kept on the config, parked: the next build measures it again against the
new ground, and keeps_own_logo (site_builder.py) does not mistake it for the host's.
"""

from __future__ import annotations

from collections.abc import Callable

from builder.site_ai.nora.contrast import MIN_RATIO, contrast, parse_color

#: the share of the logo's ink that must stand out from the ground for the logo to be seen: the
#: logo's dominant luminance is the majority's, a mark half lost in its ground is still lost
MIN_INK_SHARE = 0.5

#: a logo that fills its file edge to edge (a photograph, a square on its own plate) carries its
#: ground along and is seen against that, not against the page's
OWN_GROUND_SHARE = 0.95

#: the doctype's own defaults when a colour is empty (get_header_colors, get_footer_colors)
HEADER_DEFAULT_GROUND = "#1a1a1a"
FOOTER_DEFAULT_GROUND = "#ffffff"

THUMB = 64

Rgb = tuple[int, int, int]


def ink_of(image) -> list[Rgb] | None:
	"""The colours of the logo's visible pixels (a PIL image), or None when there is nothing to
	measure against a ground: an image that carries its own, or an empty one."""
	from PIL import Image

	rgba = image.convert("RGBA")
	# a box filter averages: the default one rings around an edge and invents colours the mark never had
	rgba.thumbnail((THUMB, THUMB), resample=getattr(Image, "Resampling", Image).BOX)
	data = rgba.tobytes()
	ink: list[Rgb] = []
	solid = 0
	total = len(data) // 4
	for i in range(0, len(data), 4):
		r, g, b, a = data[i], data[i + 1], data[i + 2], data[i + 3]
		if a >= 250:
			solid += 1
		# the half-transparent fringe of an anti-aliased edge is not the mark's colour
		if a >= 128:
			ink.append((r, g, b))
	if not total or not ink or solid / total >= OWN_GROUND_SHARE:
		return None
	# a few specks of ink are no logo (a stray pixel in a transparent canvas)
	if len(ink) / total < 0.005:
		return None
	return ink


def ink_of_file(file_url: str) -> list[Rgb] | None:
	"""ink_of() of a site file (/files/… or /private/files/…); None when the file cannot be read as
	a raster image (a vector logo, a remote URL, a missing file): nothing is known about it."""
	import frappe

	url = str(file_url or "").split("?")[0]
	if url.startswith("/files/"):
		path = frappe.get_site_path("public", url.lstrip("/"))
	elif url.startswith("/private/files/"):
		path = frappe.get_site_path(url.lstrip("/"))
	else:
		return None
	try:
		from PIL import Image

		with Image.open(path) as image:
			image.load()
			return ink_of(image)
	except Exception:
		return None


def ink_stands_out(
	ink: list[Rgb], ground: tuple, minimum: float = MIN_RATIO, share: float = MIN_INK_SHARE
) -> bool:
	"""Whether the majority of the ink contrasts with the ground by at least `minimum`."""
	# each colour weighs its pixels, and is measured once
	counts: dict[Rgb, int] = {}
	for rgb in ink:
		counts[rgb] = counts.get(rgb, 0) + 1
	seen = sum(n for rgb, n in counts.items() if contrast((*rgb, 1.0), ground) >= minimum)
	return seen / len(ink) >= share


def logo_reads(
	logo_image: str | None,
	ground: str | None,
	palette: dict[str, str] | None = None,
	measure: Callable[[str], list[Rgb] | None] = ink_of_file,
) -> bool | None:
	"""Whether the logo can be seen on this ground: True or False, None when it cannot be told (a
	ground that is not a flat opaque colour, a logo that carries its own ground or cannot be read)."""
	if not logo_image or not ground:
		return None
	colour = parse_color(ground, palette or {})
	if colour is None or colour[3] < 0.9:
		return None
	ink = measure(logo_image)
	if not ink:
		return None
	return ink_stands_out(ink, colour)


def settle_chrome_logos(
	config,
	palette: dict[str, str] | None = None,
	measure: Callable[[str], list[Rgb] | None] = ink_of_file,
) -> list[str]:
	"""Header and footer logos against the grounds the chrome ended up with. A logo that cannot be
	seen on its ground becomes the site's name as text; its file stays on the config. Returns what
	was changed, one line each, for the build's log.

	The footer is read first: a footer set to "Same as Header" follows the header's logo as it was
	before this pass.
	"""
	changes: list[str] = []
	header_ground = config.get("header_bg_color") or HEADER_DEFAULT_GROUND
	footer_ground = config.get("footer_bg_color") or config.get("header_bg_color") or FOOTER_DEFAULT_GROUND

	header_image = str(config.get("logo_image") or "").strip()
	if config.get("show_footer_logo"):
		footer_type = config.get("footer_logo_type")
		footer_image = str(config.get("footer_logo_image") or "").strip()
		if footer_type == "Same as Header":
			# the header's own logo, as get_footer_logo_data renders it
			footer_image = header_image if config.get("logo_type") == "Image" else ""
		elif footer_type != "Image":
			footer_image = ""
		if footer_image and logo_reads(footer_image, footer_ground, palette, measure) is False:
			config.footer_logo_type = "Text"
			changes.append(
				f"footer logo {footer_image} cannot be seen on {footer_ground}: the site name is shown instead"
			)

	if (
		config.get("logo_type") == "Image"
		and header_image
		and logo_reads(header_image, header_ground, palette, measure) is False
	):
		config.logo_type = "Text"
		changes.append(
			f"header logo {header_image} cannot be seen on {header_ground}: the site name is shown instead"
		)
	return changes
