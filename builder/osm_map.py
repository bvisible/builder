# //// Neoffice — added file (no upstream equivalent): where the map of a site draws its marker.
"""The map of a site is OpenStreetMap's embed (templates/includes/google_map.html), and that embed is given a point, not an address. The point
is looked up once, with Nominatim (OpenStreetMap's own search), and kept:

- when a page is built, `pin_maps` writes the point of every map the page includes right next to the include (`{% set lat = … %}{% set lon = … %}`),
  so the page carries it for good and a rebuilt cache costs it nothing;
- when a page has none (written before, or by hand), the template asks `geocode_address`, which answers from the cache for a month and looks
  the address up at most once a day while it cannot be found. The lookup has a short timeout: a visitor never waits on it for long, and the
  template then shows the address and a link instead of an empty frame.

Nominatim's policy is one request a second with an identifying user agent and no bulk use: one address, a few attempts, a pause between them."""

import hashlib
import re
import time

import frappe

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Neoffice-site-builder/1.0 (+https://neoffice.me)"
TIMEOUT = 5
PAUSE = 1.1
FOUND_FOR = 30 * 24 * 3600
MISSED_FOR = 24 * 3600

INCLUDE = re.compile(r"\{%-?\s*include\s+['\"]builder/templates/includes/google_map\.html['\"]\s*-?%\}")
ADDRESS = re.compile(r"\{%-?\s*set\s+address\s*=\s*(['\"])(.*?)\1\s*-?%\}")
POINT = re.compile(r"\{%-?\s*set\s+lat\s*=")


def _clean(address: str) -> str:
	return " ".join(str(address or "").split())


def candidates(address: str) -> list[str]:
	"""What to ask, most exact first: the address as written, then without its street (a village of the Alps that has no street of that name
	in the data), then its last two parts (the postcode and the town)."""
	address = _clean(address)
	parts = [p.strip() for p in address.split(",") if p.strip()]
	asked = [address]
	if len(parts) > 2:
		asked.append(", ".join(parts[1:]))
	if len(parts) > 3:
		asked.append(", ".join(parts[-2:]))
	return list(dict.fromkeys(a for a in asked if a))


def look_up(address: str, timeout: float = TIMEOUT) -> tuple[float, float] | None:
	"""The point of an address, from Nominatim; None when it cannot be reached or does not know it."""
	import requests

	for index, asked in enumerate(candidates(address)):
		if index:
			time.sleep(PAUSE)
		try:
			response = requests.get(
				NOMINATIM,
				params={"q": asked, "format": "jsonv2", "limit": 1},
				headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
				timeout=timeout,
			)
			response.raise_for_status()
			found = response.json()
			if found:
				return float(found[0]["lat"]), float(found[0]["lon"])
		except Exception:
			return None
	return None


def _key(address: str) -> str:
	return "neo_geocode::" + hashlib.sha1(_clean(address).lower().encode()).hexdigest()


def geocode_address(address: str):
	"""[lat, lon] of an address, or None. Cached: a month when found, a day when not (a Jinja method of the site, hooks.py)."""
	address = _clean(address)
	if not address:
		return None
	key = _key(address)
	try:
		cached = frappe.cache.get_value(key)
	except Exception:
		cached = None
	if cached is not None:
		return list(cached) or None
	point = look_up(address)
	try:
		frappe.cache.set_value(key, list(point) if point else [], expires_in_sec=FOUND_FOR if point else MISSED_FOR)
	except Exception:
		pass
	return list(point) if point else None


def _walk(blocks):
	stack = list(blocks or [])
	while stack:
		block = stack.pop()
		if isinstance(block, dict):
			yield block
			stack.extend(block.get("children") or [])


def pin_maps(blocks: list, default_address: str = "") -> list[str]:
	"""Write, in place, the point of every map the page includes beside its include. The address is the one the include sets, else
	`default_address` (the business's, which the template falls back to). A map that already has a point is left as it is. Returns one
	line per map."""
	edits = []
	for block in _walk(blocks):
		html = block.get("innerHTML")
		if not isinstance(html, str) or "google_map.html" not in html or POINT.search(html) or not INCLUDE.search(html):
			continue
		found = ADDRESS.search(html)
		address = _clean(found.group(2) if found else default_address)
		if not address:
			continue
		point = geocode_address(address)
		if not point:
			edits.append(f"no point found for {address}")
			continue
		pin = f'{{% set lat = "{point[0]:.6f}" %}}{{% set lon = "{point[1]:.6f}" %}}'
		block["innerHTML"] = INCLUDE.sub(lambda match: pin + match.group(0), html, count=1)
		edits.append(f"{address} -> {point[0]:.5f}, {point[1]:.5f}")
	return edits
