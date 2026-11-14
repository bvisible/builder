# //// Neoffice — added file (no upstream equivalent): the example sites of the template hub, shown when a site starts.
"""The example sites of the template hub, shown to the person who starts a site, and what the build makes of the one they chose.

Jérémy, 14.11: « quand on commence un site, on montre les sites démos que Nora modifie après ? il faudrait pouvoir voir » ; asked whether Nora
takes an example's look or the example itself: « il faut poser la question ». So the playbook shows the hub's complete sites (its `showcase`
groups, one per trade), each with its picture and a link that opens it whole, and asks the person how to start from the one they chose:
- `look`: the site is written for the person's business in the example's colours and type (its design tokens, taken as they are), its pages read
  as references, and the plan told the sections of each example page, in their order;
- `as_is`: the example's own pages are laid on the site, and every word and every photograph of them is written again for the person's
  business, the layout untouched (page_from_example). A page the example does not have is written by the writer, in the example's look.

What it never does:
- show an example's words or photographs on the person's site: every text and picture of an example page is rewritten or made again, and a text
  the model left out is emptied rather than kept;
- trust the hub: an example page that does not come is written by the writer instead, a catalogue that does not answer shows no example (and is
  not asked again for five minutes);
- state a fact nobody gave: the rewrite is told the example's figures, prices and years are the example's, never the person's.
"""

import copy
import html
import json
import re

import frappe
from pydantic import BaseModel, Field

USES = ("look", "as_is")
MAX_SHOWN = 6
DOWN_KEY = "nora_example_sites_down"
DOWN_SECONDS = 300
CONTACT_FORM = "builder/templates/includes/contact_form.html"
SITE_FORM = "builder/templates/includes/site_form.html"
PLACEHOLDER = "https://placehold.co/{w}x{h}"
REWRITE_MAX_TOKENS = 16000


# ---------------------------------------------------------------- the catalogue


def _hub_get(method: str, **params):
    from builder.api import hub_get

    return hub_get(method, **params)


def _cache():
    return frappe.cache()


def catalogue() -> list[dict]:
    """The hub's complete sites (its `showcase` groups) as the hub lists them; [] when the hub does not answer. The hub's answer is kept ten
    minutes by hub_get; a hub that does not answer is not asked again for DOWN_SECONDS (the playbook is written at every turn)."""
    cache = _cache()
    if cache.get_value(DOWN_KEY):
        return []
    try:
        groups = _hub_get("get_catalog") or []
    except Exception:
        cache.set_value(DOWN_KEY, 1, expires_in_sec=DOWN_SECONDS)
        return []
    return [g for g in groups if isinstance(g, dict) and g.get("showcase") and g.get("pages")]


def _translated(group: dict, field: str, lang: str) -> str:
    own = ((group.get("translations") or {}).get((lang or "fr")[:2]) or {}).get(field)
    return str(own or group.get(field) or "").strip()


def _slug(route: str) -> str:
    return str(route or "").strip("/").rsplit("/", 1)[-1]


def describe(group: dict, lang: str = "fr") -> dict:
    """One example as the playbook and the build read it."""
    pages = [
        {
            "name": p.get("name"),
            "title": str(p.get("page_title") or "").strip(),
            "slug": _slug(p.get("route")),
            "url": p.get("live_url") or "",
            "preview": p.get("preview") or "",
        }
        for p in group.get("pages") or []
        if p.get("name")
    ]
    return {
        "name": group.get("name"),
        "title": _translated(group, "title", lang) or group.get("name"),
        "description": _translated(group, "description", lang),
        "sector": group.get("sector") or "",
        "thumbnail": group.get("thumbnail") or (pages[0]["preview"] if pages else ""),
        "url": pages[0]["url"] if pages else "",
        "pages": pages,
        "header_footer": group.get("header_footer") or {},
    }


def examples(lang: str = "fr") -> list[dict]:
    return [describe(g, lang) for g in catalogue()][:MAX_SHOWN]


def find(value, lang: str = "fr") -> dict | None:
    """The example the person chose, by its name, its title or the address of its picture (a choice with a picture answers with it)."""
    wanted = str(value or "").strip()
    if not wanted:
        return None
    key = wanted.lower()
    for group in catalogue():
        shown = describe(group, lang)
        names = {str(shown["name"] or "").lower(), shown["title"].lower(), str(group.get("title") or "").lower()}
        pictures = {shown["thumbnail"], *(p["preview"] for p in shown["pages"])}
        if key in names or wanted in pictures:
            return shown
    return None


# ---------------------------------------------------------------- the playbook


def playbook_line(lang: str = "fr") -> str:
    """Steps 1c and 1d of the site playbook: the examples shown, then how to start from the one chosen. "" when the hub shows none."""
    shown = examples(lang)
    if not shown:
        return ""
    listing = "\n".join(
        f"  - name '{e['name']}': « {e['title']} » (trade: {e['sector'] or 'any'}), image {e['thumbnail']}, link {e['url']}, "
        f"pages: {', '.join(p['title'] for p in e['pages'])}"
        for e in shown
    )
    return (
        "1c. Starting from an example. Right after step 1b (after step 1 when 1b is not asked), show ONCE the complete example sites below, "
        "with ONE present_ui card, in the person's language: first a `text` element that links each example by its title in markdown, so the "
        "person can open it whole in a new tab (for example « Voir les exemples en entier : [Garage](https://…) · [Restaurant](https://…) »), "
        "then ONE single-select `choices` group with one option per example — its `label` the title, its `description` its pages, its `image` "
        "its image address — the example whose trade is the closest to the business FIRST, and a last option without an image, « Sans "
        "exemple » (the site is written from the answers alone). The examples:\n"
        f"{listing}\n"
        "1d. When the person picked an example, ask ONCE, with ONE present_ui card holding a single-select choices group of two options, in "
        "their language, how to start from it: « Reprendre son allure » (description: your site is written in its colours, its type and the "
        "layout of its sections, with your words and your photographs) and « Le reprendre tel quel » (description: its pages are laid on your "
        "site, and every word and every photograph of them is replaced by yours). With an example, step 2 is the same card as always (ONE "
        "multi-select choices group, an option per page with its one-line description, then a Continue button), its first options the "
        "example's pages, in its order and under its titles, then the other pages that suit the business; step 3 is NOT asked (the colours "
        "and the type are the example's); the recap names the example and how it is used; generate_site takes example_site=<its name> and "
        "example_use='look' or 'as_is'. Without an example, go on with step 2 as usual."
    )


def shown(session_id: str | None, lang: str = "fr") -> bool:
    """Whether the conversation showed the person the example sites (step 1c): a card of Nora's that carries an example's picture or link, or
    a reply that picked one."""
    if not session_id:
        return True
    marks = {m for e in examples(lang) for m in (e["thumbnail"], e["url"]) if m}
    if not marks:
        return True
    from builder.ai.session import AISession

    rows = frappe.get_all(AISession.MESSAGE_DOCTYPE, filters={"session": session_id}, fields=["content", "metadata_json"])
    return any(mark in f"{row.content or ''} {row.metadata_json or ''}" for row in rows for mark in marks)


def first_site(profile: str | None) -> bool:
    """Whether the site has no published page yet: a site being made, not one rebuilt."""
    filters = {"published": 1, "is_template": 0}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        filters["neo_website_profile"] = profile if profile else ("is", "not set")
    return not frappe.db.count("Builder Page", filters)


EXAMPLES_FIRST = (
    "NOT BUILT: the person has not seen the example sites (step 1c of the playbook). Show them now, with ONE present_ui card as step 1c "
    "says (the links to open each one whole, then the choices with their pictures and « Sans exemple »), ask step 1d if they pick one, then "
    "call generate_site again with the same arguments plus example_site and example_use — or as they are when they chose no example."
)


# ---------------------------------------------------------------- what an example looks like


def bundle(page_name: str) -> dict | None:
    """One page of an example as the hub ships it (its blocks, its components, the group's tokens); None when it does not come."""
    try:
        found = _hub_get("get_template_bundle", page=page_name)
    except Exception:
        return None
    return found if isinstance(found, dict) and found.get("page") else None


def tokens(example: dict) -> tuple[str, list[dict]]:
    """The example's design tokens, read from the bundle of its first page: (their prefix, [{suffix, type, value}])."""
    for page in example.get("pages") or []:
        found = bundle(page["name"])
        rows = [v for v in (found or {}).get("variables") or [] if isinstance(v, dict) and "-" in str(v.get("name") or "")]
        if not rows:
            continue
        prefix = str(rows[0]["name"]).split("-", 1)[0]
        own = [v for v in rows if str(v["name"]).startswith(prefix + "-")]
        return prefix, [{"suffix": str(v["name"])[len(prefix) + 1 :], "type": v.get("type") or "Color", "value": v.get("value")} for v in own]
    return "", []


def _luminance(hex_colour: str) -> float | None:
    found = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(hex_colour or "").strip())
    if not found:
        return None
    r, g, b = (int(found.group(1)[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def look(example: dict, rows: list[dict] | None = None) -> dict:
    """The example's colours, type and ground, from its tokens (the header's design when the tokens do not come)."""
    if rows is None:
        rows = tokens(example)[1]
    values = {r["suffix"]: r["value"] for r in rows}
    chrome = example.get("header_footer") or {}
    background = values.get("background") or chrome.get("background_color") or ""
    shade = _luminance(background)
    return {
        "primary": values.get("primary") or chrome.get("primary_color") or "",
        "secondary": values.get("secondary") or chrome.get("secondary_color") or "",
        "background": background,
        "text": values.get("text") or chrome.get("text_color") or "",
        "heading_font": values.get("font-heading") or chrome.get("heading_font") or "",
        "body_font": values.get("font-body") or chrome.get("body_font") or "",
        "background_mode": "" if shade is None else ("dark" if shade < 0.35 else "light"),
    }


def adopt_tokens(rows: list[dict], prefix: str, group: str, write) -> list[str]:
    """The example's tokens written as this site's own (`<prefix>-<suffix>`), over the ones the build minted: its colours, type, container and
    gutters, as they are. `write` is site_builder._write_token. Returns the tokens written."""
    written = []
    for row in rows:
        if row.get("value") in (None, ""):
            continue
        doc_id = f"{prefix}-{row['suffix']}"
        write(doc_id, f"{group} {row['suffix'].replace('-', ' ').title()}", row.get("type") or "Color", row["value"], group)
        written.append(doc_id)
    return written


def sections(blocks: list) -> list[tuple[str, int]]:
    """The sections of a page in order (their name, the photographs in them), the dividers and a navigation of its own left out."""
    root = blocks[0] if blocks and isinstance(blocks[0], dict) else {}
    found = []
    for child in root.get("children") or []:
        name = str(child.get("blockName") or child.get("element") or "section")
        if "divider" in name or child.get("element") in ("nav", "footer", "header") or any(w in name.lower() for w in ("navbar", "footer")):
            continue
        found.append((name, json.dumps(child).count('"element": "img"')))
    return found


def _blocks_of(found: dict) -> list:
    raw = (found.get("page") or {}).get("blocks")
    try:
        blocks = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return []
    return blocks if isinstance(blocks, list) else []


def plan_lines(example: dict) -> str:
    """What the site plan is told of the example whose look the site takes: its pages and the sections of each, in order."""
    lines = []
    for page in example.get("pages") or []:
        found = bundle(page["name"])
        if not found:
            continue
        parts = [f"{name}" + (f" ({count} photograph{'s' if count > 1 else ''})" if count else "") for name, count in sections(_blocks_of(found))]
        if parts:
            lines.append(f"- « {page['title']} »: " + ", ".join(parts))
    head = (
        f"EXAMPLE SITE the client chose to start from, « {example['title']} »: this site takes its LOOK (its colours and type are already the "
        "site's tokens, its pages are among the reference pictures). Plan every page with the kinds of sections the example's page of the same "
        "purpose has, in the same order and with the same rhythm, and the photographs where it has them; the copy is this business's, never the "
        "example's (its figures, prices, years and names are the example's own)."
    )
    return head + ("\nThe example's pages and their sections, in order:\n" + "\n".join(lines) if lines else "")


# ---------------------------------------------------------------- an example page laid on the site


def _norm(text: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def matching_page(example: dict, page: dict) -> dict | None:
    """The example page a page of the site is made from: the same title, else the same address, else the home for the home."""
    pages = example.get("pages") or []
    title, route = _norm(page.get("title")), _norm(str(page.get("route") or "").replace("-", " "))
    for candidate in pages:
        if _norm(candidate["title"]) == title:
            return candidate
    for candidate in pages:
        if _norm(candidate["slug"].replace("_", " ")) == route:
            return candidate
    if str(page.get("route") or "").strip("/") in ("home", "index", "") and pages:
        return pages[0]
    return None


def route_map(example: dict, pages: list[dict]) -> dict[str, str]:
    """The example's page addresses (its relative links: `prendre_rendez_vous`, `accueil`) to this site's."""
    mapped = {}
    for page in pages:
        candidate = matching_page(example, page)
        if candidate:
            route = str(page.get("route") or "").strip("/")
            mapped[candidate["slug"]] = "/" if route in ("home", "index", "") else f"/{route}"
    if example.get("pages"):
        mapped.setdefault(example["pages"][0]["slug"], "/")
    return mapped


def _walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for child in node.get("children") or []:
            _walk(child, visit)
    elif isinstance(node, list):
        for child in node:
            _walk(child, visit)


def lay_example(found: dict, from_prefix: str, to_prefix: str, links: dict[str, str]) -> list:
    """The blocks of an example page, made this site's: its tokens renamed to the site's, its own navigation left out, its form the site's
    contact form (adopt_contact_forms makes it the site's own form), its links to the example's pages pointed at the site's."""
    from builder.api import _strip_template_navigation

    text = json.dumps(_blocks_of(found), ensure_ascii=False)
    if from_prefix and to_prefix and from_prefix != to_prefix:
        text = text.replace(f"--{from_prefix}-", f"--{to_prefix}-")
    text = text.replace(SITE_FORM, CONTACT_FORM)
    blocks = json.loads(text)
    blocks = _strip_template_navigation(blocks, found.get("components") or []) or blocks

    def relink(block: dict) -> None:
        attrs = block.get("attributes") or {}
        href = str(attrs.get("href") or "")
        if href and not re.match(r"^(https?:|mailto:|tel:|#)", href):
            target = links.get(_slug(href)) or links.get(href.strip("/"))
            if target:
                attrs["href"] = target

    _walk(blocks, relink)
    return blocks


# ---------------------------------------------------------------- its words and photographs, written again


TAG = re.compile(r"<[^>]+>")


class NewText(BaseModel):
    id: str = Field(description="the id of the text, exactly as given")
    text: str = Field(description="the new text, in the site's language, with the same inline tags as the example's")


class NewPicture(BaseModel):
    id: str = Field(description="the id of the picture, exactly as given")
    photo: str = Field(default="", description="the address of ONE of the client's photographs, copied exactly from the list, when one fits this place")
    shows: str = Field(default="", description="when none of the client's photographs fits: what the photograph to make for this place shows, in the site's language, one sentence (it is the picture's alt text too)")


class Rewrite(BaseModel):
    texts: list[NewText] = Field(default_factory=list)
    pictures: list[NewPicture] = Field(default_factory=list)


def slots(blocks: list) -> tuple[list[dict], list[dict]]:
    """The words and the pictures of a page: (texts, pictures), each with the block that holds it. A text holding a template tag (a live
    component) is not one of them."""
    texts, pictures = [], []

    def visit(block: dict, where: str) -> None:
        element = str(block.get("element") or "").lower()
        if element == "img":
            pictures.append({"block": block, "section": where, "alt": str((block.get("attributes") or {}).get("alt") or "")})
            return
        inner = str(block.get("innerHTML") or "")
        if inner.strip() and "{%" not in inner and "{{" not in inner and TAG.sub("", inner).strip():
            texts.append({"block": block, "section": where, "element": element or "div", "html": inner})

    def walk(node, where):
        if isinstance(node, dict):
            name = str(node.get("blockName") or "")
            here = name if node.get("element") == "section" and name else where
            visit(node, here)
            for child in node.get("children") or []:
                walk(child, here)
        elif isinstance(node, list):
            for child in node:
                walk(child, where)

    walk(blocks, "")
    for i, item in enumerate(texts):
        item["id"] = f"t{i}"
    for i, item in enumerate(pictures):
        item["id"] = f"p{i}"
    return texts, pictures


# a section's numbering (« 01 », « /03 »): a lone figure (« 0 », « 48 ») is a quantity, and the example's « 0 » stayed on a page (14.11)
NUMBERING = re.compile(r"^/?0\d\.?$|^/\d{1,2}$")


def _plain(text: str) -> str:
    return " ".join(TAG.sub(" ", str(text or "")).split())


def suspect(new: str, original: str, facts: str) -> str:
    """Why a written text is asked again, or "": the example's own words kept (beyond a short label), or a number the business never gave (a
    section's numbering, « /01 », kept as it is). After the second answer a missing text is emptied, a number taken out, and the example's
    words kept: they then fit this business too."""
    plain, before = _plain(new), _plain(original)
    if not plain:
        return "missing"
    if NUMBERING.match(plain) and plain == before:
        return ""
    if len(plain) > 12 and plain.lower() == before.lower():
        return "the example's own words"
    given = set(re.findall(r"\d+", facts or ""))
    invented = [n for n in quantities(plain) if n not in given]
    return f"a number nobody gave ({', '.join(invented)})" if invented else ""


NOT_A_QUANTITY = re.compile(r"\b\d+\s*[dD]\b|\b\d+\s*[x×]\s*\d+\b")


def quantities(text: str) -> list[str]:
    """The numbers a text states, a dimension (« 3D ») or a format (« 4x4 ») left out: those are names, not quantities."""
    return re.findall(r"\d+", NOT_A_QUANTITY.sub(" ", str(text or "")))


def safe_text(new: str, original: str) -> str:
    """The new text, with the inline tags the example's text had kept and any other tag dropped (its words kept)."""
    # a structured answer sometimes closes a string on the brace of its object: « … adaptée    } »
    new = re.sub(r"\s+[}\]]+\s*$", "", str(new or ""))
    allowed = set(TAG.findall(original or "")) | {"<br>", "<br/>", "<br />"}
    out, last = [], 0
    for found in TAG.finditer(new or ""):
        out.append(html.escape(new[last : found.start()], quote=False))
        tag = found.group(0)
        # a tag the example's text did not have is dropped: written as text, « <em> » showed on the page (14.11)
        out.append(tag if tag in allowed else "")
        last = found.end()
    out.append(html.escape((new or "")[last:], quote=False))
    return "".join(out).strip()


def _size(block: dict) -> tuple[int, int]:
    styles = {**(block.get("baseStyles") or {})}
    ratio = str(styles.get("aspectRatio") or "")
    found = re.match(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$", ratio)
    if found and float(found.group(2)):
        return 1200, max(300, int(1200 * float(found.group(2)) / float(found.group(1))))
    return 1200, 800


def rewrite_prompt(texts: list[dict], pictures: list[dict], page: dict, facts: str, language: str, photos: list[dict], notes: str = "") -> str:
    lines = [
        f"PAGE: « {page.get('title')} » of the site described below. LANGUAGE of every text: {language}.",
        "",
        "THE BUSINESS (the only facts you may state):",
        facts,
        "",
        "Every text below is the text of an EXAMPLE site of another business, laid on this page as it is. Write each one again for THIS business: "
        "the same role (a kicker stays a kicker, a heading a heading, a button a button), about the same length (never more than a third longer), "
        "the same inline tags in the same places (an <em> on the word to stress, a <br> where the line breaks), and no tag the example's text "
        "does not have. Never keep the example's words, names, places, figures, prices, years or reviews: they are the example's. Its services, "
        "equipment, delays, guarantees, team and history are the example's too: state only what THE BUSINESS gave — a list of the example's "
        "services becomes a list of this business's services as given, never the example's kept or reworded. A figure, a price, a delay, a "
        "guarantee or a year nobody gave is never stated, in digits or in words: it becomes a short phrase without a number (« Sur mesure », "
        "« Agréé par les assurances »). A text whose role this business has nothing to say for is still written, short and true.",
        "",
        "TEXTS (id, section, element, the example's text; FIGURE marks a text whose number is the example's):",
        *[
            f"{t['id']} | {t['section'] or '-'} | {t['element']} | {t['html']}"
            + (" | FIGURE: no digit and no number in words unless the business gave it" if quantities(_plain(t['html'])) and not NUMBERING.match(_plain(t['html'])) else "")
            for t in texts
        ],
    ]
    if pictures:
        lines += [
            "",
            "PICTURES of the example (id, section, what the example's picture showed). For each, give the address of ONE of the client's "
            "photographs that fits this place (each at most once), else say in `shows` what the photograph to make shows for this business — "
            "a place, premises, tools or products, never a person:",
            *[f"{p['id']} | {p['section'] or '-'} | {p['alt'] or '-'}" for p in pictures],
            "",
            "THE CLIENT'S PHOTOGRAPHS: "
            + ("none." if not photos else "\n" + "\n".join(f"- {p['url']} — {p.get('shows') or 'a photograph of the business'}" for p in photos)),
        ]
    if notes:
        lines += ["", "THE PAGE WAS LOOKED AT; fix these points with the words alone (shorter, plainer) where they are about the text:", notes]
    lines += ["", "Answer with EVERY text id and EVERY picture id."]
    return "\n".join(lines)


REWRITE_SYSTEM = (
    "You write the words of a website page for a business, in a layout that was designed for another business. You keep the layout's "
    "roles and lengths exactly, and you never state a fact the business did not give."
)


def rewrite(blocks: list, page: dict, facts: str, language: str, model: str, photos: list[dict], notes: str = "", call=None) -> dict | None:
    """Every word and picture of an example page written again for the business, in place. `call(prompt, system)` returns a Rewrite (the
    model by default). Returns what was done: {texts, pictures, photos, made, emptied}; None when the model gave nothing (nothing changed)."""
    texts, pictures = slots(blocks)
    if not texts and not pictures:
        return {"texts": 0, "pictures": 0, "photos": 0, "made": 0, "emptied": []}
    call = call or (lambda prompt, system: _ask(model, prompt, system))
    prompt = rewrite_prompt(texts, pictures, page, facts, language, photos, notes)
    answer = call(prompt, REWRITE_SYSTEM)
    if answer is None:
        # no words came: the page is not laid at all (the writer writes it), rather than laid empty or with the example's words
        return None
    new_texts = {t.id: t.text for t in (answer.texts if answer else [])}
    new_pictures = {p.id: p for p in (answer.pictures if answer else [])}
    wrong = {t["id"]: suspect(new_texts.get(t["id"]), t["html"], facts) for t in texts}
    wrong = {k: why for k, why in wrong.items() if why}
    if wrong:
        # once more for the texts it left out, kept from the example or gave a number to: an example's word is never left on the page
        retry = [{**t, "html": t["html"]} for t in texts if t["id"] in wrong]
        again = call(
            rewrite_prompt(retry, [], page, facts, language, photos, notes)
            + "\nThese texts came back wrong the first time: "
            + "; ".join(f"{k}: {why}" for k, why in wrong.items())
            + ". Write them again: new words for this business, and no number it did not give.",
            REWRITE_SYSTEM,
        )
        for text in again.texts if again else []:
            if text.id in wrong and not suspect(text.text, next(t["html"] for t in texts if t["id"] == text.id), facts):
                new_texts[text.id] = text.text
                wrong.pop(text.id)
        numbered = [k for k, why in wrong.items() if why.startswith("a number")]
        if numbered:
            # a figure kept twice: asked once more, with no digit at all, before its number is taken out
            last = call(
                rewrite_prompt([t for t in texts if t["id"] in numbered], [], page, facts, language, photos, notes)
                + "\nThese texts still state a number this business never gave: write each one with NO DIGIT at all and no number in words, a "
                "short phrase that says what the business does give (« Rapide », « Sur rendez-vous », « Agréé par les assurances »).",
                REWRITE_SYSTEM,
            )
            for text in last.texts if last else []:
                if text.id in wrong and not suspect(text.text, next(t["html"] for t in texts if t["id"] == text.id), facts):
                    new_texts[text.id] = text.text
                    wrong.pop(text.id)
    emptied = []
    for item in texts:
        written = str(new_texts.get(item["id"]) or "").strip()
        why = wrong.get(item["id"]) or ""
        if why == "missing":
            # never the example's text for a text that did not come: an empty one, which the look of the page then shows
            emptied.append(_plain(item["html"])[:40])
            written = ""
        elif why == "the example's own words":
            # asked again and kept: a label that fits this business too (« Devis annoncé » on a garage and a body shop), never emptied — an
            # emptied label left a price list with holes the look of the page refused three times (14.11)
            pass
        elif why:
            # a number nobody gave, twice: the text without it
            # a dimension (« 3D ») is kept aside under a mark with no digit in it, the numbers taken out, then it is put back
            kept = {m.group(0): f"\x00{chr(0xE000 + i)}\x00" for i, m in enumerate(NOT_A_QUANTITY.finditer(_plain(written)))}
            plain = _plain(written)
            for name, mark in kept.items():
                plain = plain.replace(name, mark)
            plain = re.sub(r"\d[\d'’.,]*\s*(?:%|h\b)?", "", plain)
            for name, mark in kept.items():
                plain = plain.replace(mark, name)
            written = re.sub(r"\s{2,}", " ", plain).strip()
            emptied.append(f"number dropped: {_plain(item['html'])[:30]}")
        item["block"]["innerHTML"] = safe_text(written, item["html"]) if written else ""
    offered = {p["url"]: str(p.get("shows") or "").strip() for p in photos}
    used, placed, made = set(), 0, 0
    for item in pictures:
        attrs = item["block"].setdefault("attributes", {})
        chosen = new_pictures.get(item["id"])
        photo = str(getattr(chosen, "photo", "") or "").strip()
        if photo in offered and photo not in used:
            attrs["src"] = photo
            # the example's alt described the example's picture: the client's photograph is described by what it shows
            attrs["alt"] = offered[photo] or str(getattr(chosen, "shows", "") or "").strip() or str(page.get("title") or "")
            used.add(photo)
            placed += 1
            continue
        w, h = _size(item["block"])
        attrs["src"] = PLACEHOLDER.format(w=w, h=h)
        attrs["alt"] = str(getattr(chosen, "shows", "") or "").strip() or f"{page.get('title')}, the premises of the business"
        made += 1
    return {"texts": len(texts), "pictures": len(pictures), "photos": placed, "made": made, "emptied": emptied}


def _ask(model: str, prompt: str, system: str):
    from builder.site_ai.providers import get_provider

    try:
        llm = get_provider("litellm", model=model, temperature=0.6, timeout=600)
        return llm.generate_structured(prompt=prompt, schema=Rewrite, system_prompt=system, max_tokens=REWRITE_MAX_TOKENS)
    except Exception as e:
        frappe.log_error("Example page words not rewritten", str(e))
        return None


def page_from_example(found: dict, from_prefix: str, to_prefix: str, links: dict[str, str], page: dict, facts: str, language: str, model: str,
                      photos: list[dict], notes: str = "", call=None) -> tuple[list, dict]:
    """An example page laid on the site and written again for the business: (its blocks, what was done); ([], None) when its words could not be
    written again, and the writer then writes the page."""
    blocks = lay_example(found, from_prefix, to_prefix, links)
    done = rewrite(blocks, page, facts, language, model, photos, notes, call=call)
    return (blocks, done) if done is not None else ([], None)
