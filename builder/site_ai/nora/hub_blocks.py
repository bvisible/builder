# //// Neoffice — added file (no upstream equivalent): the blocks of the Builder Hub, offered to the site plan as section recipes.
"""The hub keeps a library of blocks (sections designed once, editable in the hub's own editor); this module lets a site build draw on it.

A block is a tree in the writer's node format with tokens where a site's own colour, font or width goes and `WRITE <role>:` slots where the
writer's words go (block_format.py says exactly what it may hold). Here it becomes a section recipe of the same kind as the ones written in
code (recipes.py), registered under `<family>.hub-<variant>`: the plan reads it in the catalogue and may pick it, the page brief gives its
structure to the writer, the photograph budget, the repeat rule and the removal of unfilled slots apply to it unchanged. Nothing downstream
knows a block came from the hub.

What it never does:
- it never makes a build depend on the hub. The catalogue is fetched with a short timeout and kept (an hour fresh, a month as the last one
  that worked); a hub that does not answer gives the last good catalogue, and none gives no hub block: the recipes written in code are
  the library, the hub only adds to it;
- it never trusts what the hub sends. Every block is linted again here (block_format.lint) before it is registered and drawn once on
  sample values; a block that fails either is left out and said in the log;
- it never changes a site that did not ask: it is off unless `nora_hub_blocks` is set in site_config.
"""

from dataclasses import replace

import frappe

from builder.site_ai.nora import block_format
from builder.site_ai.nora import recipes as section_recipes
from builder.site_ai.nora.recipes import Ctx, Look, Recipe, el, flow, ground_of

TIMEOUT = 6
FRESH_FOR = 3600
KEPT_FOR = 30 * 24 * 3600
FRESH_KEY = "nora_hub_blocks::fresh"
KEPT_KEY = "nora_hub_blocks::kept"
METHOD = "builder_hub.api.get_block_catalog"
HUB_MARK = ".hub-"
USER_AGENT = "Neoffice-site-builder/1.0 (+https://neoffice.me)"


def enabled(conf=None) -> bool:
	"""Whether a site build offers the hub's blocks (`nora_hub_blocks` in site_config, off unless set)."""
	try:
		conf = conf if conf is not None else frappe.conf
		return str(conf.get("nora_hub_blocks", 0)).strip().lower() in ("1", "true", "yes", "on")
	except Exception:
		return False


# ---------------------------------------------------------------- the catalogue, kept


def _cache_get(key):
	try:
		return frappe.cache.get_value(key)
	except Exception:
		return None


def _cache_set(key, value, seconds):
	try:
		frappe.cache.set_value(key, value, expires_in_sec=seconds)
	except Exception:
		pass


def fetch() -> dict | None:
	"""The hub's published blocks, or None when it does not answer well."""
	import requests

	from builder.api import hub_url

	try:
		response = requests.get(
			f"{hub_url()}/api/method/{METHOD}", headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
		)
		response.raise_for_status()
		body = (response.json() or {}).get("message")
	except Exception:
		return None
	if not isinstance(body, dict) or not isinstance(body.get("blocks"), list):
		return None
	return body


def catalogue() -> tuple[dict | None, str]:
	"""(the catalogue as the hub sent it, where it came from: "fresh", "hub", "kept" or "none")."""
	fresh = _cache_get(FRESH_KEY)
	if isinstance(fresh, dict):
		return fresh, "fresh"
	got = fetch()
	if got is not None:
		_cache_set(FRESH_KEY, got, FRESH_FOR)
		_cache_set(KEPT_KEY, got, KEPT_FOR)
		return got, "hub"
	kept = _cache_get(KEPT_KEY)
	if isinstance(kept, dict):
		return kept, "kept"
	return None, "none"


# ---------------------------------------------------------------- a block, drawn


def _values(c: Ctx) -> dict:
	"""What each token of block_format stands for, for this site and this ground."""
	k, g = c.look, c.ground
	values = {name: getattr(k, name) for name in block_format.LOOK_TOKENS}
	values.update(
		{
			"ground.background": g.bg.get("backgroundColor", "transparent"),
			"ground.ink": g.ink,
			"ground.muted": g.muted,
			"ground.hair": g.hair,
			"ground.accent": g.accent,
			"ground.button": g.button,
			"cta_href": c.cta_href,
			"include_component": '{% include "' + c.component + '" %}',
		}
	)
	for index, url in enumerate(c.photos):
		values[f"photo.{index}"] = url
	return values


def _text(value, values: dict):
	if not isinstance(value, str):
		return value
	slot = block_format.SLOT.match(value)
	if slot and slot.group(1) == "alt":
		# the alt of a photograph is the prompt of the image generator: what it may show is a rule of the generator (recipes.ALT_GUIDANCE: never a
		# person, a screen, a sign), not something a block, from another server, gets to rephrase
		return section_recipes.slot("alt", section_recipes.ALT_GUIDANCE)
	return block_format.TOKEN.sub(lambda m: str(values[m.group(1)]), value)


def _mapping(raw, values: dict):
	return {key: _text(item, values) for key, item in raw.items()} if raw else None


def instantiate(node: dict, c: Ctx, values: dict | None = None) -> dict:
	"""A tree of the hub as the node a recipe's build returns, for this site's look. A node with a `ground` draws itself and what is under it
	on that ground."""
	if node.get("ground"):
		c = replace(c, ground=ground_of(c.look, node["ground"]))
		values = None
	values = values if values is not None else _values(c)
	style, t_style, m_style = (_mapping(node.get(k), values) for k in ("style", "t_style", "m_style"))
	attrs = _mapping(node.get("attrs"), values)
	children = [instantiate(child, c, values) for child in node.get("c") or []]
	return el(
		node["el"],
		name=node.get("name"),
		classes=node.get("classes"),
		style=flow(**style) if style else None,
		t_style=flow(**t_style) if t_style else None,
		m_style=flow(**m_style) if m_style else None,
		attrs=flow(**attrs) if attrs else None,
		text=_text(node["text"], values) if "text" in node else None,
		c=children or None,
	)


# ---------------------------------------------------------------- the registry


def recipe_id(block_id: str) -> str:
	"""`steps.rail` of the hub is `steps.hub-rail` in the catalogue the plan reads."""
	family, variant = block_id.split(".", 1)
	return f"{family}{HUB_MARK}{variant}"


def is_hub_recipe(recipe_id_: str) -> bool:
	return HUB_MARK in recipe_id_


def accept(block) -> tuple[Recipe | None, str]:
	"""(the recipe of a block, "") or (None, why it is left out)."""
	if not isinstance(block, dict):
		return None, "not a mapping"
	name = str(block.get("id") or "?")
	try:
		kinds = tuple(k for k in block.get("kinds") or [] if k in _plan_kinds())
		errors, _warnings = block_format.lint(
			block.get("tree"),
			block_id=name,
			kinds=kinds,
			photos=int(block.get("photos") or 0),
			form=bool(block.get("form")),
			motion=block.get("motion") or "None",
		)
		if errors:
			return None, errors[0]
		look = " ".join(str(block.get("look") or "").split())
		if not look:
			return None, "it has no look to tell the plan"
		tree = block["tree"]
		built = Recipe(
			recipe_id(name),
			kinds,
			look,
			lambda c, tree=tree: instantiate(tree, c),
			photos=int(block.get("photos") or 0),
			form=bool(block.get("form")),
			ground=block.get("ground") or "plain",
			motion=block.get("motion") or "None",
		)
		# drawn once on sample values: a block that cannot be drawn is found here, not in the middle of a page
		sample = Ctx(
			Look({}),
			ground_of(Look({}), built.ground),
			[f"/sample-{i}.jpg" for i in range(built.photos)],
			"/contact",
			"sample-form",
		)
		section_recipes.to_yaml(built.build(sample))
	except Exception as e:
		return None, f"{type(e).__name__}: {e}"[:200]
	return built, ""


def _plan_kinds() -> set[str]:
	from builder.site_ai.nora.site_plan import SECTION_KINDS

	return set(SECTION_KINDS)


def forget() -> int:
	"""Takes every hub recipe out of the registry. Returns how many there were."""
	gone = [i for i in section_recipes.REGISTRY if is_hub_recipe(i)]
	for i in gone:
		del section_recipes.REGISTRY[i]
	return len(gone)


def sync_registry(conf=None) -> dict:
	"""Makes the registry hold exactly the hub recipes this build is allowed: none when `nora_hub_blocks` is off (and any left from the build
	before in this worker are taken out), else the accepted blocks of the catalogue. Returns {"ids": [...], "source": ..., "left_out":
	[...]}, which the build logs."""
	forget()
	if not enabled(conf):
		return {"ids": [], "source": "off", "left_out": []}
	body, source = catalogue()
	if body is None:
		return {"ids": [], "source": source, "left_out": []}
	if body.get("format") != block_format.FORMAT:
		return {"ids": [], "source": f"{source}, format {body.get('format')} not understood", "left_out": []}
	ids, left_out = [], []
	for block in body["blocks"]:
		built, why = accept(block)
		if built is None:
			left_out.append(f"{(block or {}).get('id') if isinstance(block, dict) else '?'}: {why}")
			continue
		if built.id in section_recipes.REGISTRY:
			left_out.append(f"{block['id']}: {built.id} is already a recipe")
			continue
		section_recipes.REGISTRY[built.id] = built
		ids.append(built.id)
	return {"ids": ids, "source": source, "left_out": left_out}
