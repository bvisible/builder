"""Image search — real photos for pages instead of drawn SVGs.

Providers, best first: Pexels (site_config `pexels_api_key`), Unsplash
(site_config `unsplash_access_key`), then keyless Openverse as the
zero-config fallback. Each result carries a full-size `url` (for page
blocks / generation briefs) and a `thumb` (for present_ui image options).
"""

import frappe
import requests

from builder.ai.agent.registry import Tool

SEARCH_TIMEOUT = 10
MAX_RESULTS = 6
ORIENTATIONS = ("landscape", "portrait", "square")


def search_pexels(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = orientation
	r = requests.get(
		"https://api.pexels.com/v1/search",
		params=params,
		headers={"Authorization": key},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	return [
		{
			"url": p["src"]["large2x"],
			"thumb": p["src"]["medium"],
			"description": p.get("alt") or "",
			"credit": p.get("photographer") or "Pexels",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("photos", [])
	]


def search_unsplash(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = "squarish" if orientation == "square" else orientation
	r = requests.get(
		"https://api.unsplash.com/search/photos",
		params=params,
		headers={"Authorization": f"Client-ID {key}"},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	return [
		{
			"url": p["urls"]["regular"],
			"thumb": p["urls"]["small"],
			"description": p.get("alt_description") or "",
			"credit": (p.get("user") or {}).get("name") or "Unsplash",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("results", [])
	]


def search_openverse(query: str, orientation: str | None) -> list[dict]:
	params = {"q": query, "page_size": MAX_RESULTS, "license_type": "commercial"}
	if orientation:
		params["aspect_ratio"] = (
			"wide" if orientation == "landscape" else ("tall" if orientation == "portrait" else "square")
		)
	r = requests.get("https://api.openverse.org/v1/images/", params=params, timeout=SEARCH_TIMEOUT)
	r.raise_for_status()
	return [
		{
			"url": p.get("url") or "",
			"thumb": p.get("thumbnail") or p.get("url") or "",
			"description": p.get("title") or "",
			"credit": p.get("creator") or "Openverse",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("results", [])
		if p.get("url")
	]


def providers() -> list[tuple[str, callable]]:
	out: list[tuple[str, callable]] = []
	if frappe.conf.pexels_api_key:
		out.append(("Pexels", lambda q, o: search_pexels(q, o, frappe.conf.pexels_api_key)))
	if frappe.conf.unsplash_access_key:
		out.append(("Unsplash", lambda q, o: search_unsplash(q, o, frappe.conf.unsplash_access_key)))
	out.append(("Openverse", search_openverse))
	return out


def run_search_images(ctx, args: dict) -> str:
	query = (args.get("query") or "").strip()
	if not query:
		return "query is required."
	orientation = args.get("orientation") if args.get("orientation") in ORIENTATIONS else None
	for name, search in providers():
		try:
			results = search(query, orientation)
		except Exception as e:
			frappe.logger("builder.ai").warning(f"search_images via {name} failed: {e}")
			continue
		if results:
			# Hand the generator the results directly (see artifact.generate_page_markup).
			# Copying urls into the brief by hand is how photos went missing — and how
			# one arrived with two digits transposed, 404ing the whole turn.
			remember_for_generation(ctx, query, results)
			return render_results(name, results)
	return (
		f"No images found for '{query}'. Try a simpler, more visual query (subject + setting, "
		"e.g. 'running shoe studio'), or fall back to a CSS composition."
	)


MAX_REMEMBERED_IMAGES = 24


def remember_for_generation(ctx, query: str, results: list[dict]) -> None:
	found = getattr(ctx, "found_images", None)
	if found is None:
		return
	for r in results:
		if len(found) >= MAX_REMEMBERED_IMAGES:
			return
		found.append({**r, "query": query})


def render_results(provider: str, results: list[dict]) -> str:
	lines = [f"{provider} results — `url` goes in page blocks/briefs, `thumb` in present_ui image options:"]
	for i, p in enumerate(results, 1):
		desc = p["description"][:120] or "(no description)"
		lines.append(
			f"{i}. {desc} — by {p['credit']}, {p['size']}\n   url: {p['url']}\n   thumb: {p['thumb']}"
		)
	return "\n".join(lines)


search_images = Tool(
	name="search_images",
	side="server",
	handler=run_search_images,
	description=(
		"Search stock photo libraries for REAL photographs (products, food, people, places, "
		"textures). Use this instead of drawing real-world subjects as SVG. Returns direct "
		"image URLs: put `url` in blocks/briefs (img src, meta_image), and `thumb` on "
		"present_ui choices options (option.image) when offering the user a pick. Search "
		"with a concrete visual query (subject + setting + mood), not a brand name."
	),
	parameters={
		"type": "object",
		"properties": {
			"query": {
				"type": "string",
				"description": "Visual description, e.g. 'white running shoe on dark background'.",
			},
			"orientation": {"type": "string", "enum": list(ORIENTATIONS)},
		},
		"required": ["query"],
	},
)

# //// Neoffice — added (2026-11-18): the editor's assistant draws a picture with the site's own image service. Only the site build
# //// drew pictures: once a site existed, a person who asked the assistant for « an image of a switchboard being repaired » was told
# //// it could not, and offered stock photos they found wrong.
GENERATED_SIZES = {"landscape": (1344, 768), "portrait": (832, 1216), "square": (1024, 1024)}
MAX_GENERATED = 2


def image_generation_available() -> bool:
	"""Whether this site can draw pictures (ComfyUI pointed at a server, or the legacy generator switched on)."""
	from builder.api import _image_backend_available

	try:
		return bool(_image_backend_available())
	except Exception:
		return False


def run_generate_image(ctx, args: dict) -> str:
	description = (args.get("description") or "").strip()
	if not description:
		return "description is required: what the picture shows (subject, setting, light), never the business's name."
	if not image_generation_available():
		return (
			"Image generation is not set up on this site. Offer search_images (real photographs) or the person's own picture "
			"(an upload element on a present_ui card) instead."
		)
	from builder.api import _build_image_prompt, generate_one_image

	orientation = args.get("orientation") if args.get("orientation") in GENERATED_SIZES else "landscape"
	width, height = GENERATED_SIZES[orientation]
	count = min(max(int(args.get("count") or 1), 1), MAX_GENERATED)
	prompt = _build_image_prompt(description, is_background=bool(args.get("background")))
	made, failed = [], ""
	for _ in range(count):
		try:
			made.append(generate_one_image(prompt, width=width, height=height))
		except Exception as e:
			failed = str(e)[:160]
			frappe.logger("builder.ai").warning(f"generate_image failed: {failed}")
			break
	if not made:
		return f"The image service did not draw the picture ({failed or 'no answer'}). Tell the person, and offer to try again or search_images."
	results = [{"url": url, "thumb": url, "description": description, "credit": "generated", "size": f"{width}x{height}"} for url in made]
	remember_for_generation(ctx, description, results)
	lines = [
		f"Drew {len(made)} picture(s) for '{description}'. They are NOT on the page yet: show them to the person on ONE present_ui "
		"choices card (each option's `image` = its url, plus an option to draw another), and place only the one they pick, with "
		"edit_page (the img block's src, or the section's background image)."
	]
	lines += [f"{i}. url: {url}" for i, url in enumerate(made, 1)]
	return "\n".join(lines)


generate_image = Tool(
	name="generate_image",
	side="server",
	handler=run_generate_image,
	description=(
		"Draw a NEW picture with the site's own image service (a photograph-like image, about 20 to 60 seconds each), when the "
		"person asks you to create, draw or generate an image, or when no real photograph fits. Describe what the picture shows "
		"concretely (subject, setting, light, framing), never the business's name nor text to letter in it. Returns /files/ urls: "
		"show them with present_ui before anything is placed."
	),
	parameters={
		"type": "object",
		"properties": {
			"description": {"type": "string", "description": "What the picture shows, e.g. 'an electrician repairing a switchboard in a bright workshop'."},
			"orientation": {"type": "string", "enum": list(GENERATED_SIZES)},
			"count": {"type": "integer", "minimum": 1, "maximum": MAX_GENERATED, "description": "How many versions to offer (1 or 2)."},
			"background": {"type": "boolean", "description": "true when the picture goes behind a section's text (an atmosphere, few details)."},
		},
		"required": ["description"],
	},
)

TOOLS = [search_images]
