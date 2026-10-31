# //// Neoffice — added file (no upstream equivalent): the hub's blocks, offered in the Builder editor's insertion panel.
"""The hub keeps a library of blocks, sections designed once (hub_blocks.py offers them to the site generator). The people who build a page by hand
are offered the same library: each block the hub keeps for the editor becomes a Block Template of the site, the card of the editor's insertion panel,
listed under its section (Hero, Features, FAQ, Pricing…) and dragged onto a page like any other.

A block is drawn here exactly as the generator draws it on a site (the recipe of hub_blocks.py, the writer's node format, page_writer's conversion
into the blocks of the editor), with two differences that suit somebody who edits:
- its colours, fonts and widths are the site's own design tokens (`var(--<prefix>-primary)`…), so the block follows the site when the person changes a
  colour in the Design Tokens;
- its words are SAMPLE words in the language of the site, which the person replaces (the generator would have written them).

What it never does:
- it never makes the editor depend on the hub: the cards are rows of the site, drawn here; a hub that does not answer changes nothing;
- it never trusts what the hub sends: every block goes through hub_blocks.accept (linted again, drawn once on sample values), and one that fails is
  left out and said;
- it never offers a block to a site that did not ask: it is off unless `builder_hub_templates` is set in site_config, and a site without design
  tokens (no generated site) is offered nothing: a block with the colours of nobody would look wrong on it;
- it never touches a template a person made: it only reads and writes the rows that carry the id of a hub block (`hub_block`);
- it never writes into the app's folder: a Block Template exports itself to the app on save (block_template.py, a developer's way of shipping a
  template), which is switched off here (`frappe.flags.in_import`), and a row that goes is deleted with the database alone.
"""

import hashlib
import json
import re
from contextlib import contextmanager

import frappe

from builder.site_ai.nora import block_format, hub_blocks
from builder.site_ai.nora import recipes as section_recipes
from builder.site_ai.nora.recipes import Ctx, Look, ground_of

CONF_KEY = "builder_hub_templates"
METHOD = "builder_hub.api.get_editor_block_catalog"
TIMEOUT = 10
RENDERER = 2  # raise it when the way a block is drawn here changes: every card is drawn again
PLACEHOLDER_PHOTO = "/assets/builder/images/fallback.png"
CTA_HREF = "/contact"
# the card is two columns wide and two rows high: the thumbnail is a wide picture
CARD_WIDTH, CARD_HEIGHT = 2, 2
DEFAULT_CATEGORY = "Content"
USER_AGENT = hub_blocks.USER_AGENT


def enabled(conf=None) -> bool:
	"""Whether this site offers the hub's blocks in its editor (`builder_hub_templates` in site_config, off unless set)."""
	try:
		conf = conf if conf is not None else frappe.conf
		return str(conf.get(CONF_KEY, 0)).strip().lower() in ("1", "true", "yes", "on")
	except Exception:
		return False


# ---------------------------------------------------------------- the hub


def fetch() -> dict | None:
	"""The hub's editor catalogue, or None when it does not answer well."""
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
	if body.get("format") not in block_format.READABLE:
		return None
	return body


# ---------------------------------------------------------------- the site


def sample_language(language: str | None) -> str:
	"""The language of the sample words for a site in this language: French for a French site, English for any other (the samples exist in two)."""
	return "fr" if str(language or "").lower().startswith("fr") else "en"


def site_design() -> tuple[dict, dict] | None:
	"""(the handles of the site's design tokens, their colours) or None when the site has no design tokens. The handles are `var(--<prefix>-primary)`
	and so on, for the tokens that exist (a site made before the grid tokens has no `container`: the block then takes the default width)."""
	from builder.site_ai.nora import capture
	from builder.site_ai.nora.site_builder import palette_values

	try:
		prefix = (frappe.db.get_single_value("Website Header Footer Config", "token_prefix") or "").strip()
	except Exception:
		return None
	if not prefix:
		return None
	handles = {
		key: f"var(--{prefix}-{key})"
		for key in capture.HANDLE_KEYS
		if frappe.db.exists("Builder Token", f"{prefix}-{key}")
	}
	if not all(key in handles for key in ("primary", "secondary", "background", "text")):
		return None
	return handles, palette_values(prefix)


def design_signature(handles: dict, palette: dict, language: str) -> str:
	"""What a card depends on in the site: the tokens it uses, their colours, the language of its sample words."""
	text = json.dumps([handles, palette, language, RENDERER], sort_keys=True)
	return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------- the sample words

# a slot of a role the generator's sample table has no words for (`caption`, `phrase`: a name, a price, a detail of one to four words) gets the longest of
# these that fits the number of words its guidance allows: a block of the hub is written by people, and a role the table lacks must not turn into a
# paragraph in a plan's name
SHORT_SAMPLES = {
	"fr": ("Détail", "Un détail", "Un court libellé", "Un libellé court et précis"),
	"en": ("Detail", "A detail", "A short label", "A short and precise label"),
}
MAX_WORDS = (
	re.compile(r"(\d+)\s*(?:to|-|–|à)\s*(\d+)\s*(?:words|mots)", re.I),
	re.compile(r"(\d+)\s*(?:words?|mots?)", re.I),
)


def max_words(guidance: str) -> int | None:
	"""The most words the guidance of a slot allows (`2 to 4 words` -> 4, `1 word` -> 1), None when it says nothing."""
	for pattern in MAX_WORDS:
		found = pattern.search(guidance or "")
		if found:
			return int(found.groups()[-1])
	return None


def sample_for(text: str, language: str) -> str:
	"""The sample words for a slot (`WRITE <role>: <guidance>`): the generator's own for the roles its table knows, a short label for the others."""
	slot = block_format.SLOT.match(text)
	role = slot.group(1) if slot else "text"
	table = section_recipes.SAMPLES.get(language) or section_recipes.SAMPLES["fr"]
	if role in table:
		return table[role]
	ladder = SHORT_SAMPLES.get(language) or SHORT_SAMPLES["fr"]
	cap = max_words(text)
	fitting = [words for words in ladder if cap is None or len(words.split()) <= cap]
	return fitting[-1] if fitting else ladder[0]


def fill_slots(node, language: str) -> None:
	"""Puts sample words in place of every slot of a node, in place."""

	def visit(value):
		items = (
			value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
		)
		for key, item in list(items):
			if isinstance(item, str) and block_format.SLOT.match(item):
				value[key] = sample_for(item, language)
			else:
				visit(item)

	visit(node)


# ---------------------------------------------------------------- a block, drawn


class Left(Exception):
	"""A block that is not offered, and why."""


def draw(block: dict, handles: dict, palette: dict, language: str) -> dict:
	"""The block of the editor (the `block` of a Block Template) for a hub block, on this site's tokens and with sample words. Raises `Left`."""
	from builder.ai.page_writer import expand_page_yaml

	recipe, why = hub_blocks.accept(block)
	if recipe is None:
		raise Left(why)
	if recipe.form:
		raise Left("it carries the live contact form, which a page of the editor adds by its own component")
	look = Look(handles, palette)
	photos = [PLACEHOLDER_PHOTO] * recipe.photos
	node = recipe.build(Ctx(look, ground_of(look, recipe.ground), photos, CTA_HREF, ""))
	fill_slots(node, language)
	blocks, _script = expand_page_yaml(section_recipes.to_yaml(node), is_root=False)
	if not blocks:
		raise Left("its tree could not be turned into a block of the editor")
	return blocks[0]


def card_hash(block: dict, signature: str) -> str:
	"""What a card was drawn from: the block (its title, its version, its section, its thumbnail) and the site's design."""
	text = json.dumps(
		[
			block.get("id"),
			block.get("title"),
			block.get("version"),
			block.get("category"),
			block.get("preview"),
			signature,
		],
		sort_keys=True,
	)
	return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def plan(existing: dict, wanted: dict) -> tuple[list, list, list]:
	"""(to add, to update, to remove): block ids. `existing` maps a block id to the hash its card was drawn from, `wanted` to the hash it would be
	drawn from now; a card whose hash is the same is left alone."""
	add = [i for i in wanted if i not in existing]
	update = [i for i in wanted if i in existing and existing[i] != wanted[i]]
	remove = [i for i in existing if i not in wanted]
	return add, update, remove


def section_order(body: dict) -> dict:
	"""{section: rank} as the hub lists them."""
	sections = body.get("sections")
	return {name: i for i, name in enumerate(sections if isinstance(sections, list) else [])}


# ---------------------------------------------------------------- the rows


@contextmanager
def _no_export():
	"""A Block Template exports itself to the app's folder when it is saved, unless an import is running: here it must never."""
	before = frappe.flags.in_import
	frappe.flags.in_import = True
	try:
		yield
	finally:
		frappe.flags.in_import = before


def _row_values(block: dict, drawn: dict, hash_: str, rank: int) -> dict:
	return {
		"block": frappe.as_json(drawn, indent=0),
		"preview": block["preview"],
		"preview_width": CARD_WIDTH,
		"preview_height": CARD_HEIGHT,
		"category": block.get("category") or DEFAULT_CATEGORY,
		"description": (block.get("look") or "")[:400],
		"sort_order": rank,
		"hub_block": block["id"],
		"hub_hash": hash_,
	}


def _name_for(block: dict, current: str | None = None) -> str:
	"""The name of the card of this block: its title, and the title with the id when another template (a person's, or another block's) already has it.
	`current` is the name the card has now, which is never taken by somebody else."""
	name = (block.get("title") or block["id"]).strip()[:120]
	if (
		name != current
		and frappe.db.exists("Block Template", name)
		and frappe.db.get_value("Block Template", name, "hub_block") != block["id"]
	):
		name = f"{name} ({block['id']})"[:140]
	return name


def _write(existing_name: str | None, block: dict, values: dict) -> None:
	name = _name_for(block, existing_name)
	values = {**values, "template_name": name}
	if existing_name:
		if name != existing_name:
			# a block the hub renamed: the card follows it (the name is the document's, so it is renamed, not edited)
			with _no_export():
				frappe.rename_doc("Block Template", existing_name, name, force=True)
		frappe.db.set_value("Block Template", name, values)
		return
	with _no_export():
		frappe.get_doc({"doctype": "Block Template", **values}).insert(ignore_permissions=True)


def sync(conf=None) -> dict:
	"""Brings the cards of the editor's insertion panel in line with the hub's catalogue. Returns {"state": ..., "added": [...], "updated": [...],
	"removed": [...], "left_out": [...]}: nothing changes when the site did not ask, when the hub does not answer, or when the site has no design
	tokens."""
	if not enabled(conf):
		return {"state": "off"}
	body = fetch()
	if body is None:
		return {"state": "the hub does not answer well: nothing changed"}
	design = site_design()
	if design is None:
		return {"state": "the site has no design tokens: nothing offered"}
	handles, palette = design
	language = sample_language(frappe.db.get_single_value("System Settings", "language"))
	signature = design_signature(handles, palette, language)

	ranks = section_order(body)
	per_section: dict[str, int] = {}
	wanted, blocks, left_out = {}, {}, []
	for block in body["blocks"]:
		if not isinstance(block, dict) or not block.get("id") or not block.get("preview"):
			left_out.append(f"{block.get('id') if isinstance(block, dict) else '?'}: no id or no thumbnail")
			continue
		wanted[block["id"]] = card_hash(block, signature)
		blocks[block["id"]] = block

	rows = frappe.get_all(
		"Block Template", filters={"hub_block": ("!=", "")}, fields=["name", "hub_block", "hub_hash"]
	)
	names = {r.hub_block: r.name for r in rows}
	add, update, remove = plan({r.hub_block: r.hub_hash for r in rows}, wanted)

	done = {"added": [], "updated": [], "removed": []}
	for block_id in [*add, *update]:
		block = blocks[block_id]
		category = block.get("category") or DEFAULT_CATEGORY
		per_section[category] = per_section.get(category, 0) + 1
		rank = ranks.get(category, len(ranks)) * 1000 + per_section[category]
		try:
			drawn = draw(block, handles, palette, language)
			_write(names.get(block_id), block, _row_values(block, drawn, wanted[block_id], rank))
		except Left as why:
			left_out.append(f"{block_id}: {why}")
			continue
		except Exception as e:
			frappe.log_error(f"Hub block {block_id} not offered", f"{type(e).__name__}: {e}"[:500])
			left_out.append(f"{block_id}: {type(e).__name__}")
			continue
		done["added" if block_id in add else "updated"].append(block_id)
	for block_id in remove:
		frappe.db.delete("Block Template", {"name": names[block_id]})
		done["removed"].append(block_id)
	frappe.db.commit()
	return {"state": "ok", **done, "left_out": left_out}


def sync_quietly() -> None:
	"""The hook form of `sync` (a migrate, the daily job): whatever goes wrong is logged, never raised."""
	try:
		sync()
	except Exception as e:
		frappe.log_error("Hub blocks not synced to the editor", f"{type(e).__name__}: {e}"[:500])


@frappe.whitelist()
def sync_now() -> dict:
	"""Brings the editor's cards in line with the hub right now (System Manager)."""
	frappe.only_for("System Manager")
	return sync()
