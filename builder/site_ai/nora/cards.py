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

import re

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
KINDS = ("choices", "buttons", "actions", "color_input", "input", "upload", "heading", "text", "list", "swatches", "divider")
OPEN = re.compile(r"\[(" + "|".join(KINDS) + r")(?:\s+(multi))?\s*:", re.IGNORECASE)


def looks_like_card(text: str) -> bool:
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
    label = label.strip() or line.strip()
    option = {"label": label[:80]}
    if description.strip():
        option["description"] = description.strip()[:200]
    if colors:
        option["colors"] = colors[:4]
    return option


def parse_card(text: str) -> dict | None:
    """The present_ui arguments for a bracket-written card, or None when the text
    carries no card."""
    lead, groups = _split_groups(text or "")
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
            if not options:
                for line in lines:
                    bare = line.lstrip("-•* ").strip().lower()
                    if bare.startswith("[colors") and options:
                        # a palette line belongs to the option written just above it
                        options[-1].setdefault("colors", HEX.findall(line)[:4])
                        continue
                    options.append(_option(line))
                options = [o for o in options if o.get("label")]
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
