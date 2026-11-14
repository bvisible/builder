# //// Neoffice — added file (no upstream equivalent): a card the model wrote as text becomes a present_ui card.
"""Turn a card the model wrote as text into a real present_ui card.

Both Kimi models call present_ui for the first question of a conversation, then
write the following cards as bracketed prose ([choices: …], [buttons: Continue])
whatever the prompt says. The user cannot tap prose. When a turn ends on such a
text, the loop hands it here: the brackets are parsed into the element kinds
present_ui understands, and the card is emitted through the same handler the
tool call would have used, so the panel renders it as if the model had called
the tool. Anything unparseable stays plain text.
"""

from __future__ import annotations

import json
import re
import unicodedata

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
KINDS = ("choices", "buttons", "actions", "color_input", "input", "upload", "heading", "text", "list", "swatches", "divider")
OPEN = re.compile(r"\[(" + "|".join(KINDS) + r")(?:\s+(multi))?\s*:", re.IGNORECASE)


def looks_like_card(text: str) -> bool:
    text = _braces_to_brackets(text or "")
    return bool(text) and OPEN.search(text) is not None and "[buttons:" in text.lower() or "[choices" in (text or "").lower()


def _split_groups(text: str) -> tuple[str, list[tuple[str, bool, str]]]:
    """The lead text and the top-level [kind: body] groups, nested [colors: …]
    kept inside their option line."""
    lead_end = None
    groups = []
    pos = 0
    while True:
        m = OPEN.search(text, pos)
        if not m:
            break
        if lead_end is None:
            lead_end = m.start()
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
            i += 1
        body = text[m.end(): i - 1] if depth == 0 else text[m.end():]
        groups.append((m.group(1).lower(), bool(m.group(2)), body.strip()))
        pos = i
    lead = text[: lead_end if lead_end is not None else len(text)].strip()
    return lead, groups


def _lines(body: str) -> list[str]:
    return [line.strip() for line in body.split("\n") if line.strip()]


def _parts(text: str) -> list[str]:
    """`text` split at its commas outside parentheses and brackets: « A (x, y), B » is two options, not three. The
    question about three refused pages came cut at every comma of its descriptions, « en gardant vos tarifs) » a
    choice of its own (13.11, osiris)."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


# the tool's arguments written as a call: « Tarifs — que faire? options=[A (description: …), B (description: …)] »
PSEUDO_OPTIONS = re.compile(r"^(?P<label>.*?)\s*\boptions\s*[=:]\s*\[(?P<body>.*)\]\s*$", re.IGNORECASE | re.DOTALL)
DESCRIBED = re.compile(r"^(?P<label>.+?)\s*\(\s*description\s*[:=]\s*(?P<description>.*)\)\s*$", re.IGNORECASE | re.DOTALL)


def _pseudo_options(body: str) -> tuple[str, list[dict]] | None:
    """The label and options of a choices group written as `<question> options=[A (description: x), B]`, or None."""
    found = PSEUDO_OPTIONS.match(body.strip())
    if not found:
        return None
    options = []
    for part in _parts(found["body"]):
        described = DESCRIBED.match(part)
        if described:
            options.append({"label": described["label"].strip()[:80], "description": described["description"].strip()[:200]})
        else:
            options.append({"label": part.strip(" '\"")[:80]})
    return found["label"].strip(" ,;:"), [o for o in options if o["label"]]


def _option(line: str) -> dict:
    """'- Label: description [colors: #a, #b]' -> an option dict."""
    line = line.lstrip("-•* ").strip()
    colors = HEX.findall(line)
    line = re.sub(r"\[colors?:[^\]]*\]", "", line).strip()
    label, _, description = line.partition(":")
    if not description:
        # "Accueil — la vitrine" / "Accueil – la vitrine": the dash is the separator
        label, _, description = re.split(r"(\s[—–]\s)", line, maxsplit=1) + ["", ""][: 3 - len(re.split(r"(\s[—–]\s)", line, maxsplit=1))]
    label = label.strip() or line.strip()
    option = {"label": label[:80]}
    if description.strip():
        option["description"] = description.strip()[:200]
    if colors:
        option["colors"] = colors[:4]
    return option


BRACE_GROUP = re.compile(r"\{\s*kind\s*:\s*(" + "|".join(KINDS) + r")\s*,(.*?)\}(?=\s*(?:\{\s*kind|$))", re.IGNORECASE | re.DOTALL)
BRACE_ITEMS = re.compile(r"\{\s*label\s*:\s*([^,}]+?)\s*(?:,\s*description\s*:\s*([^,}]+?))?\s*(?:,\s*variant\s*:\s*[a-z]+)?\s*\}", re.IGNORECASE)
QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"")


def _braces_to_brackets(text: str) -> str:
    """The pseudo-JSON a model writes when it prints the present_ui arguments instead
    of calling the tool ("{kind: heading, text: Récapitulatif} {kind: list, items:
    ['Nom : X', …]} {kind: actions, buttons: [{label: Build}, {label: Change,
    variant: secondary}]}"), rewritten in the bracket form the parser reads."""
    if "{kind" not in text.replace(" ", ""):
        return text

    def one(m):
        kind, body = m.group(1).lower(), m.group(2)
        if kind in ("heading", "text"):
            value = re.search(r"text\s*:\s*(.+)$", body.strip(), re.IGNORECASE | re.DOTALL)
            return f"[{kind}: {(value.group(1) if value else body).strip().strip(chr(39)).strip(chr(34))}]"
        if kind == "list":
            items = [a or b for a, b in QUOTED.findall(body)]
            return "[list:\n" + "\n".join(f"- {i}" for i in items) + "]" if items else ""
        if kind in ("actions", "buttons"):
            labels = [lab.strip().strip(chr(39)).strip(chr(34)) for lab, _ in BRACE_ITEMS.findall(body)]
            return f"[buttons: {', '.join(labels)}]" if labels else ""
        if kind == "choices":
            label = re.search(r"label\s*:\s*([^,]+)", body, re.IGNORECASE)
            multi = re.search(r"multi\s*:\s*true", body, re.IGNORECASE)
            options = [(lab.strip().strip(chr(39)).strip(chr(34)), (desc or "").strip().strip(chr(39)).strip(chr(34))) for lab, desc in BRACE_ITEMS.findall(body)]
            lines = [f"- {lab}: {desc}" if desc else f"- {lab}" for lab, desc in options]
            head = (label.group(1).strip().strip(chr(39)).strip(chr(34)) if label else "")
            return f"[choices{' multi' if multi else ''}: {head}\n" + "\n".join(lines) + "]" if lines else ""
        return ""

    return BRACE_GROUP.sub(one, text)


JSON_OBJECT = re.compile(r'\{\s*"(?:text|ui)"\s*:')
JSON_LIST = re.compile(r'\[\s*\{\s*"kind"\s*:')
CONTROLS = ("choices", "actions", "color_input", "input", "upload")


def _json_card(text: str) -> dict | None:
    """The present_ui arguments a model printed as JSON instead of calling the tool
    ('{"text": "…", "ui": [{"kind": "heading", …}, …, {"kind": "actions", …}]}', or the
    ui list alone): the last complete one, since a model may write several drafts in a row.
    A recap came back as 61,000 characters of deliberation and JSON drafts, and the card
    was never tappable (2026-09-12). Unknown kinds (a "note" carrying the model's own tool
    arguments) are left out; without a control it is no card."""
    decoder = json.JSONDecoder()
    found = None
    starts = sorted([m.start() for m in JSON_OBJECT.finditer(text)] + [m.start() for m in JSON_LIST.finditer(text)])
    end = -1
    for start in starts:
        if start < end:
            # inside the card just read: its own ui list is not a card of its own
            continue
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(obj, list):
            obj = {"text": "", "ui": obj}
        if isinstance(obj, dict) and isinstance(obj.get("ui"), list):
            found = obj
    if not found:
        return None
    ui = []
    for element in found["ui"]:
        if not isinstance(element, dict):
            continue
        kind = str(element.get("kind") or "").lower()
        if kind == "buttons":
            element, kind = {**element, "kind": "actions"}, "actions"
        if kind in KINDS:
            ui.append(element)
    if not any(el["kind"] in CONTROLS for el in ui):
        return None
    return {"text": str(found.get("text") or "…")[:600], "ui": ui}


BARE_BUTTONS = re.compile(r"(?:^|\n)[ \t]*((?:\[[^\[\]\n:]{2,40}\][ \t]*){1,4})\s*$")


def _bare_buttons(text: str) -> str:
    """'[Build the site] [Change something]' closing a message: the buttons of a card the
    model wrote as text without the kind the parser reads, so the recap came with nothing to
    tap (2026-09-13). Rewritten '[buttons: Build the site, Change something]'. A footnote
    ([1]) or a kind group ([choices: …]) is not a button."""
    m = BARE_BUTTONS.search(text or "")
    if not m:
        return text
    labels = [label.strip() for label in re.findall(r"\[([^\[\]\n:]{2,40})\]", m.group(1))]
    if not labels or any(not re.search(r"[^\W\d_]", label) or label.split()[0].lower() in KINDS for label in labels):
        return text
    return text[: m.start(1)] + "[buttons: " + ", ".join(labels) + "]"


# //// Neoffice ▼▼▼ — a question followed by a plain bullet list (2026-09-16). The bracketed and
# //// brace shapes above are what the models write when they half-remember the tool; this is what
# //// they write when they forget it entirely — ordinary markdown. Seen live on the page question:
# ////     Quelles pages veux-tu sur le site ? (plusieurs choix possibles)
# ////     - Accueil — vitrine avec le carrousel de marques
# ////     - Nos marques — présentation de 9 marques distribuées
# //// The user sees a list they cannot tick and the build stalls. Read as a choices group.
BULLET = re.compile(r"^[ \t]*[-*•–][ \t]+(.{2,120})$")
# a label and its explanation, separated by an em/en dash or a colon
OPTION_SPLIT = re.compile(r"\s+[—–]\s+|:\s+")
MULTI_HINT = re.compile(r"plusieurs choix|choix multiples|multi[- ]?select|select all|mehrere", re.IGNORECASE)
# a bullet that is really a fact, not an option: it names a route or a URL
NOT_AN_OPTION = re.compile(r"https?://|(?:^|\s)/[a-z0-9\-/]+")


def _bullet_choices(text: str, minimum: int = 3) -> dict | None:
    """A question line followed by at least three option bullets (`minimum`), as a choices card.

    Deliberately narrow: without the question mark this is a report, and turning a summary's
    bullet list into a card would put a control under a sentence that asked nothing. Two bullets
    are enough only where the text says more (_listed_above: they sit right over the card's buttons)."""
    lines = [line.rstrip() for line in (text or "").split("\n")]
    # //// the first bullet, then the nearest question above it: the question line often trails a
    # //// parenthesis ("… ? (plusieurs choix possibles)"), so it is not enough to end on "?"
    first_bullet = next((i for i, line in enumerate(lines) if BULLET.match(line)), None)
    if first_bullet is None:
        return None
    question_at = next(
        (i for i in range(first_bullet - 1, -1, -1) if "?" in lines[i] and lines[i].strip()),
        None,
    )
    if question_at is None:
        return None
    options = []
    for line in lines[first_bullet:]:
        if not line.strip():
            if options:
                break
            continue
        found = BULLET.match(line)
        if not found:
            break
        body = found.group(1).strip()
        if NOT_AN_OPTION.search(body):
            return None
        parts = OPTION_SPLIT.split(body, maxsplit=1)
        option = {"label": parts[0].strip()}
        if len(parts) > 1 and parts[1].strip():
            option["description"] = parts[1].strip()
        options.append(option)
    if len(options) < minimum:
        return None
    question = lines[question_at].strip()
    return {
        "text": question,
        "ui": [
            {"kind": "choices", "label": question, "multi": bool(MULTI_HINT.search(text or "")), "options": options},
            {"kind": "actions", "buttons": [{"label": "Continue"}]},
        ],
    }
# //// Neoffice ▲▲▲


def _listed_above(lead: str) -> tuple[str, dict] | None:
    """The text above a card's buttons without its closing bullet list, and that list as a choices group, or None. Bullets
    that carry the tool's arguments cut at their commas (copied from an earlier card that came out broken) are joined
    back first: « * Tarifs — que faire? options=[A (description: x » / « * y) » is one question with its choices."""
    lines = [line.rstrip() for line in (lead or "").split("\n")]
    first = next((i for i, line in enumerate(lines) if BULLET.match(line)), None)
    if first is None or any(line.strip() and not BULLET.match(line) for line in lines[first:]):
        return None  # the bullets close the text, right above the buttons
    head = "\n".join(lines[:first]).strip()
    bullets = [BULLET.match(line).group(1).strip() for line in lines[first:] if line.strip()]
    pseudo = _pseudo_options(", ".join(bullets))
    if pseudo and len(pseudo[1]) >= 2:
        label, options = pseudo
        element = {"kind": "choices", "options": options[:12]}
        if label:
            element["label"] = label[:120]
        return head, element
    # a question of two answers is a question too, once its bullets sit right over the buttons: « this site is the
    # company's / another business's » stayed raw text over « [buttons: Continuer] » (14.11, osiris)
    card = _bullet_choices(lead, minimum=2)
    if not card:
        return None
    # the question stays the card's text, said once
    return head, {"kind": "choices", "options": card["ui"][0]["options"][:12]}


def parse_card(text: str) -> dict | None:
    """The present_ui arguments for a card written as text (JSON, braces or brackets, or a
    question followed by a bullet list), or None when the text carries no card."""
    card = _json_card(text or "")
    if card:
        return card
    lead, groups = _split_groups(_braces_to_brackets(_bare_buttons(text or "")))
    if not groups:
        # //// Neoffice — no bracket, no brace: the plain markdown a model writes when it
        # //// forgets the tool altogether (see _bullet_choices)
        return _bullet_choices(text or "")
    ui: list[dict] = []
    has_control = False
    for kind, multi, body in groups:
        lines = _lines(body)
        if kind == "choices":
            label = None
            options: list[dict] = []
            pseudo = _pseudo_options(" ".join(lines))
            if pseudo:
                label, options = pseudo
                lines = []
            if lines and not lines[0].startswith(("-", "•", "*")):
                head = lines[0]
                # '[choices multi: A, B, C]' on one line, or a question followed by options
                if len(lines) == 1 and "," in head:
                    options = [{"label": part} for part in _parts(head)]
                else:
                    label = head.rstrip(":").strip()
                    lines = lines[1:]
                    # heads the models write instead of the tool arguments:
                    # "label: Pages; multi: true" and "Palette, single-select"
                    m = re.match(r"^label:\s*(.+?)\s*;\s*multi:\s*(true|false)$", label, re.IGNORECASE)
                    if m:
                        label, multi = m.group(1), multi or m.group(2).lower() == "true"
                    m = re.match(r"^(.+?)\s*[,(]\s*(multi|single)[- ]select\)?$", label, re.IGNORECASE)
                    if m:
                        label, multi = m.group(1).strip(), multi or m.group(2).lower() == "multi"
            if not options:
                for line in lines:
                    bare = line.lstrip("-•* ").strip().lower()
                    if bare.startswith("[colors") and options:
                        # a palette line belongs to the option written just above it
                        options[-1].setdefault("colors", HEX.findall(line)[:4])
                        continue
                    if bare.startswith(("options:", "choices:", "valeurs:")) and "," in line:
                        # "options: A, B, C" is a list on one line, not one option
                        options += [{"label": part} for part in _parts(line.split(":", 1)[1])]
                        continue
                    options.append(_option(line))
                options = [o for o in options if o.get("label")]
                if len(options) == 1 and "," in options[0].get("label", "") and not options[0].get("description"):
                    # a single "A, B, C" line under a label is the list itself
                    options = [{"label": part} for part in _parts(options[0]["label"])]
            if not options:
                continue
            element = {"kind": "choices", "options": options[:12]}
            if multi or (label and "(multi)" in label.lower()):
                element["multi"] = True
                if label:
                    label = label.replace("(multi)", "").strip()
            if label:
                element["label"] = label[:120]
            ui.append(element)
            has_control = True
        elif kind in ("buttons", "actions"):
            labels = []
            for line in lines:
                # "Build the site, Change something" or "Créer le site / Modifier un élément"
                labels += [part.strip() for part in re.split(r",|\s/\s", line.lstrip("-•* ")) if part.strip()]
            buttons = [{"label": lbl[:40]} for lbl in labels[:4]]
            if buttons:
                if len(buttons) > 1:
                    buttons[-1]["variant"] = "secondary"
                ui.append({"kind": "actions", "buttons": buttons})
                has_control = True
        elif kind == "color_input":
            label = lines[0].rstrip(":").strip() if lines and not lines[0].startswith(("-", "•", "*")) else None
            slots = []
            for line in lines[1:] if label else lines:
                item = _option(line)
                slot = {"label": item["label"]}
                if item.get("description"):
                    slot["hint"] = HEX.sub("", item["description"]).strip(" ,")[:120]
                slots.append(slot)
            element = {"kind": "color_input", "colors": slots[:4] or [{"label": "Primary"}, {"label": "Secondary"}]}
            if label:
                element["label"] = label[:120]
            ui.append(element)
            has_control = True
        elif kind in ("input", "upload"):
            element = {"kind": kind}
            if lines:
                element["label"] = lines[0].rstrip(":").strip()[:120]
            ui.append(element)
            has_control = True
        elif kind == "heading":
            ui.append({"kind": "heading", "text": " ".join(lines)[:200]})
        elif kind == "text":
            ui.append({"kind": "text", "text": "\n".join(lines)[:1000]})
        elif kind == "list":
            ui.append({"kind": "list", "items": [line.lstrip("-•* ").strip()[:200] for line in lines][:12]})
        elif kind == "swatches":
            colors = HEX.findall(body)
            if colors:
                ui.append({"kind": "swatches", "colors": colors[:8]})
        elif kind == "divider":
            ui.append({"kind": "divider"})
    # //// Neoffice — a question and its bullets written ABOVE the card's buttons: the bullets are its choices. Left in the
    # //// text, present_ui bounced the card (one button under listed choices) and the raw text stayed, « [buttons:
    # //// Continuer] » on screen (13.11, osiris).
    if not any(el.get("kind") == "choices" for el in ui):
        listed = _listed_above(lead)
        if listed:
            lead, element = listed
            ui.insert(0, element)
            has_control = True
    if not has_control:
        return None
    # a card with inputs or multi-select needs a submit button; the model's own is used first
    if not any(el.get("kind") == "actions" for el in ui):
        ui.append({"kind": "actions", "buttons": [{"label": "Continue"}]})
    return {"text": lead[:600] or "…", "ui": ui}


def materialise_text_card(ctx, text: str) -> bool:
    """Emit the card the model wrote as text through present_ui's own handler.
    Returns True when a card was emitted (the caller then drops the plain text)."""
    spec = parse_card(text)
    if not spec:
        return False
    from builder.ai.agent.tools.conversation import run_present_ui

    failed = run_present_ui(ctx, spec)
    return not failed


def says_the_same(first: str, second: str) -> bool:
    """Whether two short texts say the same thing: most words of the shorter one are in the
    other. The model wrote "Deux pages existantes ont été retouchées à la main… Tu
    confirmes ?" as its message, then again as the card's text, and the panel showed the
    question twice (2026-09-13). A text of fewer than five words is never judged."""

    def words(text: str) -> list[str]:
        plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
        return [w for w in re.findall(r"[a-z0-9]+", plain) if len(w) > 1]

    a, b = words(first), words(second)
    if min(len(a), len(b)) < 5:
        return False
    shorter, longer = (a, set(b)) if len(a) <= len(b) else (b, set(a))
    return sum(1 for w in shorter if w in longer) / len(shorter) >= 0.7


# a build button on a card: "Build the site", "Construire le site", "Créer le site", "Site erstellen"
BUILD_BUTTON = re.compile(
    r"\b(?:build|rebuild|construire|reconstruire|cr[ée]er|g[ée]n[ée]rer|erstellen|bauen|costruire|creare|crea)\b.{0,20}"
    r"\b(?:site|website|webseite|sito)\b|\b(?:site|website|webseite|sito)\b.{0,20}\b(?:erstellen|bauen)\b",
    re.I,
)


def recap_names_the_site(ui: list[dict], text: str, site: str | None) -> list[dict]:
    """A recap that ends on a build button says which site the build is for. The playbook asks
    for it, and the recap of a practice's site listed its name, pages and colours but not the
    site it would be built on (2026-09-13). The line joins the card's list, in the list's own
    form ("Label : value" or "Label: value"); a card that already names the site, or an
    instance with a single site (no profile), is left as it is."""
    if not site or not any(
        el.get("kind") == "actions" and any(BUILD_BUTTON.search(str(b.get("label") or "")) for b in el.get("buttons") or [])
        for el in ui
    ):
        return ui
    shown = " ".join([text or "", *(str(item) for el in ui for item in (el.get("items") or []))]).lower()
    if site.lower() in shown:
        return ui
    lists = [el for el in ui if el.get("kind") == "list"]
    separator = " : " if any(" : " in str(item) for el in lists for item in el.get("items") or []) else ": "
    line = f"Site{separator}{site}"
    if lists:
        lists[0]["items"] = [*(lists[0].get("items") or []), line]
        return ui
    at = next((i for i, el in enumerate(ui) if el.get("kind") == "actions"), len(ui))
    return [*ui[:at], {"kind": "list", "items": [line]}, *ui[at:]]


# //// Neoffice — the playbook's button labels the model copies as they are written there (13.11, osiris: a French recap
# //// ended on « Build the site » / « Change something », the photographs card on « Continue »). Said in the person's
# //// language when the label is exactly one of them; a label the model wrote itself is left as it is. Each build label still
# //// matches BUILD_BUTTON, which tells a recap.
BUTTON_WORDS = {
    "fr": {"build the site": "Construire le site", "change something": "Changer quelque chose", "continue": "Continuer", "skip": "Passer"},
    "de": {"build the site": "Website erstellen", "change something": "Etwas ändern", "continue": "Weiter", "skip": "Überspringen"},
    "it": {"build the site": "Crea il sito", "change something": "Cambia qualcosa", "continue": "Continua", "skip": "Salta"},
}


def buttons_in_the_persons_language(ui: list[dict], lang: str | None) -> list[dict]:
    words = BUTTON_WORDS.get((lang or "")[:2].lower())
    if not words:
        return ui
    for element in ui:
        if isinstance(element, dict) and element.get("kind") == "actions":
            for button in element.get("buttons") or []:
                label = str((button or {}).get("label") or "").strip().lower()
                if label in words:
                    button["label"] = words[label]
    return ui
