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


def parse_card(text: str) -> dict | None:
    """The present_ui arguments for a card written as text (JSON, braces or brackets), or
    None when the text carries no card."""
    card = _json_card(text or "")
    if card:
        return card
    lead, groups = _split_groups(_braces_to_brackets(text or ""))
    if not groups:
        return None
    ui: list[dict] = []
    has_control = False
    for kind, multi, body in groups:
        lines = _lines(body)
        if kind == "choices":
            label = None
            options: list[dict] = []
            if lines and not lines[0].startswith(("-", "•", "*")):
                head = lines[0]
                # '[choices multi: A, B, C]' on one line, or a question followed by options
                if len(lines) == 1 and "," in head:
                    options = [{"label": part.strip()} for part in head.split(",") if part.strip()]
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
                        options += [{"label": part.strip()} for part in line.split(":", 1)[1].split(",") if part.strip()]
                        continue
                    options.append(_option(line))
                options = [o for o in options if o.get("label")]
                if len(options) == 1 and "," in options[0].get("label", "") and not options[0].get("description"):
                    # a single "A, B, C" line under a label is the list itself
                    options = [{"label": part.strip()} for part in options[0]["label"].split(",") if part.strip()]
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
