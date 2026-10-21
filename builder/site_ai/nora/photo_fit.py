# //// Neoffice — added file (no upstream equivalent): which of the photographs a user brings belong on THEIR site, and what the build says of them.
"""A user who hands over ten photographs expects the assistant to understand them, keep the ones that belong, lay them where they
serve, and say where it put each. Measured on a build with the local model (2026-10-21): the vision read all ten correctly in under a
minute (what each shows, its section, orientation, quality), and the pages used nine, then ten: the tenth, a modern home office
brought among the photographs of a mountain restaurant, was placed on the booking page because the picker falls back to "whatever is
left", and the summary said "10 of 10 photographs laid into the pages" with no word on where, so the assistant had nothing to tell.

  - unusable_photos: one call on the descriptions the vision already wrote (no picture is sent again), which asks which of them do
    not belong on this site (another trade, a generic interior, a document); a failure, or a verdict that discards everything, leaves
    every photograph in;
  - photo_plan: the lines of the tool result that say, photo by photo, what it shows, where it is used (page and section) or why it was
    left out, so that the assistant tells the user.
"""

from pydantic import BaseModel, Field

from builder.site_ai.logging import ai_log

FIT_MAX_TOKENS = 1500
FIT_SYSTEM = (
	"You help a business choose, among the photographs its owner sent, the ones that belong on THEIR website. "
	"You are given the business and a numbered list of descriptions of the photographs (written by a vision model). "
	"List ONLY the photographs that do NOT belong: the subject has nothing to do with this business (another trade, a generic "
	"home or office interior, a stock scene with no link to it), or the photograph is a document, a screenshot or a logo. "
	"Be conservative: a photograph of the place, its surroundings, its people, its products or dishes, an event it holds, is "
	"usable, even when it is ordinary. Answer with the numbers and a short reason in the language of the business description."
)


class Unusable(BaseModel):
	n: int
	reason: str = ""

	model_config = {"extra": "ignore"}


class FitVerdict(BaseModel):
	unusable: list[Unusable] = Field(default_factory=list)

	model_config = {"extra": "ignore"}


def _line(i: int, photo: dict) -> str:
	return f"{i}. {(photo.get('text') or photo.get('shows') or '').strip()[:260]}"


def unusable_photos(
	model: str, site_name: str, activity: str, library: list[dict], provider=None
) -> dict[str, str]:
	"""{url: reason} for the photographs that do not belong on this site, from the descriptions the vision wrote.
	Never raises; {} when nothing is to be left out, when there are fewer than two photographs (the user chose that one) or when the
	verdict would discard them all."""
	if len(library) < 2:
		return {}
	try:
		if provider is None:
			from builder.site_ai.providers import get_provider

			provider = get_provider("litellm", model=model, temperature=0.1, timeout=180)
		prompt = f"BUSINESS: {site_name}. {activity}\n\nPHOTOGRAPHS:\n" + "\n".join(
			_line(i, p) for i, p in enumerate(library, 1)
		)
		verdict = provider.generate_structured(
			prompt=prompt, schema=FitVerdict, system_prompt=FIT_SYSTEM, images=None, max_tokens=FIT_MAX_TOKENS
		)
	except Exception as e:
		ai_log("warning", "Photograph fit not judged", error=str(e)[:200])
		return {}
	left_out = {}
	for item in verdict.unusable:
		if 1 <= item.n <= len(library):
			left_out[library[item.n - 1]["url"]] = (item.reason or "does not fit this business").strip()[:160]
	if len(left_out) >= len(library):
		ai_log("warning", "Photograph fit verdict discarded every photograph, kept all", photos=len(library))
		return {}
	return left_out


def usable_assets(assets: list[dict], exclude=None) -> list[dict]:
	"""The library rows the matcher may place, without the files the build left out."""
	gone = set(exclude or ())
	return [a for a in assets if a.get("file") not in gone]


def _walk(node: dict, title: str, section: str, uses: dict[str, list[str]], top: bool = True) -> None:
	from builder.site_ai.nora.layout import _photos_of

	name = str(node.get("blockName") or node.get("originalElement") or node.get("element") or "")
	for url in _photos_of(node):
		where = f"{title} ({section or name})"
		if where not in uses.setdefault(url, []):
			uses[url].append(where)
	for child in node.get("children") or []:
		# the top-level sections of the page are what a person calls "the hero", "the menu band"
		_walk(
			child,
			title,
			section or (str(child.get("blockName") or child.get("element") or "") if top else section),
			uses,
			top=False,
		)


def where_used(pages: list[tuple[str, list]]) -> dict[str, list[str]]:
	"""{photo url: ["Page title (section)", ...]} from the final blocks of each page [(title, blocks)]."""
	uses: dict[str, list[str]] = {}
	for title, blocks in pages:
		for root in blocks if isinstance(blocks, list) else [blocks]:
			if isinstance(root, dict):
				_walk(root, title, "", uses)
	return uses


def photo_plan(library: list[dict], left_out: dict[str, str], pages: list[tuple[str, list]]) -> list[str]:
	"""The lines of the tool result that tell, photo by photo, what it shows and where it went."""
	uses = where_used(pages)
	lines = []
	for photo in library:
		url = photo["url"]
		name = url.rsplit("/", 1)[-1]
		shows = (photo.get("shows") or photo.get("text") or "").strip().rstrip(".")[:110]
		if url in left_out:
			lines.append(f"- {name} ({shows}): NOT USED, {left_out[url]}")
		elif uses.get(url):
			lines.append(f"- {name} ({shows}): used on " + "; ".join(uses[url][:3]))
		else:
			lines.append(f"- {name} ({shows}): not placed, no section needed it")
	if not lines:
		return []
	return [
		"PHOTO PLAN: tell the user, in a short list, what each of their photographs shows, where it is used, and which were left out "
		"and why (this is the real placement, do not invent another):",
		*lines,
	]
