# //// Neoffice — added file (no upstream equivalent): the facts a written page states that its
# //// brief never gave, found so that the page is written again without them.
"""Facts a page states that nobody gave.

A physiotherapy practice about to open, whose brief named its four services and nothing else,
came out with prices (CHF 120, 90 and 400), session lengths that differed from one page to the
next, an opening in "Octobre 2024", two years in the past, and a testimonial signed "Marie,
patiente" for a practice that had not seen a patient yet (2026-09-13). A visitor takes each for
true. The page brief forbids them (FACTS_RULE); what the model writes all the same is found
here: amounts of money, years, percentages, ratings and quantities with a unit (minutes, years,
sessions, clients...) whose number the brief does not contain, and a quotation signed by a name
the brief does not know. The page then goes back to the writer with these as issues.

Pure functions over the block tree and the page's data script."""

from __future__ import annotations

import re

FACTS_RULE = (
    "FACTS: state only what this brief gives (BRAND, POSITIONING, CATEGORIES, BUSINESS DATA). Never invent a price, "
    "a duration, a date or a year, a figure or a percentage, a rating, a testimonial or a review, a client, a partner, "
    "an award, or an insurance, legal or medical claim: a visitor takes each for true. A section that needs a fact "
    "the brief does not give is written without it (how to get a price, what a first visit covers) or left out. "
    "Never write a placeholder in brackets ([email address], [phone]): a detail the brief does not give is left "
    "out, and its label with it. Never write an e-mail address, a web address or a phone number that BUSINESS "
    "DATA does not give."
)

TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"\d[\d'’.,]*")
MONEY = re.compile(
    r"(?:\b(?:CHF|SFr\.?|Fr\.|EUR|USD|GBP)|[€$£])\s?\d[\d'’.,]*"
    r"|\b\d[\d'’.,]*\s?(?:CHF\b|francs?\b|EUR\b|euros?\b|€|\$|£)"
    r"|\b\d+\.[-–]",
    re.I,
)
QUANTITY = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:min(?:utes?|uten)?|h|heures?|hours?|stunden?|ans|années?|years?|jahren?"
    r"|séances?|sessions?|sitzungen|jours?|days?|tagen?|semaines?|weeks?|wochen|mois|months?|monaten?"
    r"|clients?|clientes?|customers?|kunden|patients?|patientes?|patienten|projets?|projects?|projekten?"
    r"|avis|reviews?|bewertungen)\b",
    re.I,
)
PERCENT = re.compile(r"\b\d+(?:[.,]\d+)?\s?%")
RATING = re.compile(r"\b\d(?:[.,]\d)?\s?/\s?(?:5|10)\b")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

# a quotation: its words in quotation marks, a blockquote, italic copy, or the quote icon beside it
QUOTE_MARKS = re.compile(r"^[«“\"„‹]|[»”\"›]$")
QUOTE_ICON = re.compile(r"data-lucide=[\"']?quote\b|lucide-quote\b")
# "Marie, patiente", "— Julien R., client", "Anna M. - Kundin": a name, then who they are
SIGNATURE = re.compile(r"^[—–-]?\s*([A-ZÀ-Ý][\w'’-]+(?:\s+[A-ZÀ-Ý][\w'’.-]*)?)\s*(?:,|—|–|\s-)\s*\w")
TITLES = ("h1", "h2", "h3")
TESTIMONIAL_KEY = re.compile(r"[\"'](?:quote|citation|t[ée]moignage|testimonial|review|avis)[\"']\s*:", re.I)
TESTIMONIAL_WORD = re.compile(r"t[ée]moign|testimonial|review|avis|bewertung", re.I)

STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'')
NOT_COPY = re.compile(r"^(?:/|https?:|#|var\(|data:)|\.(?:png|jpe?g|webp|gif|svg|avif)\b", re.I)

LABELS = {
    "price": "prices",
    "testimonial": "a testimonial",
    "year": "years",
    "figure": "percentages",
    "rating": "ratings",
    "quantity": "durations or quantities",
}
FIXES = {
    "price": "remove every amount: the brief gives no price; say how the price is given instead (on request, at the first appointment)",
    "testimonial": "remove the quotation and the section built around it: the brief gives no testimonial",
    "year": "remove the year, or use the one the brief gives; a month it names without a year is the next one to come",
    "figure": "remove the percentage, or write the sentence without it",
    "rating": "remove the rating",
    "quantity": "remove the number, or write the sentence without it",
}


def today_line(today: str) -> str:
    """The date the page is written on: the model's own calendar stops years earlier, and an opening
    "in October" came out as October 2024 (2026-09-13)."""
    return f"TODAY: {today}. A month the brief names without its year is the next one to come."


def _norm(number: str) -> str:
    return re.sub(r"[’'.,]", "", number).lstrip("0")


def _first_number(text: str) -> str:
    match = NUMBER.search(text)
    return _norm(match.group(0)) if match else ""


def _children(block: dict) -> list[dict]:
    return [child for child in block.get("children") or [] if isinstance(child, dict)]


def _plain(block: dict) -> str:
    """The text a block shows, its children's included, without markup or template code."""
    parts = []
    html = block.get("innerHTML")
    if isinstance(html, str) and "{%" not in html and "{{" not in html and not html.lstrip().startswith("<svg"):
        parts.append(TAG.sub(" ", html))
    parts += [_plain(child) for child in _children(block)]
    return " ".join(" ".join(parts).split())


def _copy(blocks: list):
    """Each text of the page, one block at a time (template code and icons left out)."""
    stack = [b for b in blocks if isinstance(b, dict)]
    while stack:
        block = stack.pop()
        html = block.get("innerHTML")
        if isinstance(html, str) and html.strip() and "{%" not in html and "{{" not in html and not html.lstrip().startswith("<svg"):
            yield " ".join(TAG.sub(" ", html).split())
        stack.extend(_children(block))


def _script_copy(script: str):
    """The strings of the data script that are copy, not a path, an address or an image."""
    for match in STRING.finditer(script or ""):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if value and not NOT_COPY.search(value.strip()):
            yield value


def _is_quotation(block: dict, text: str) -> bool:
    if (block.get("element") or "").lower() == "blockquote":
        return True
    if QUOTE_ICON.search(str(block.get("innerHTML") or "")):
        return True
    if len(text) < 50:
        return False
    italic = str((block.get("baseStyles") or {}).get("fontStyle") or "").lower() == "italic"
    return italic or bool(QUOTE_MARKS.search(text))


def _signed_quotations(blocks: list, known: str) -> list[str]:
    """The signatures under a quotation that name someone the brief does not know."""
    found: list[str] = []

    def visit(children: list[dict]) -> None:
        texts = [(child, _plain(child)) for child in children]
        if any(_is_quotation(child, text) for child, text in texts):
            for child, text in texts:
                if (child.get("element") or "").lower() in TITLES or not 0 < len(text) <= 60:
                    continue
                match = SIGNATURE.match(text)
                if match and match.group(1).lower() not in known:
                    found.append(text)
        for child in children:
            visit(_children(child))

    visit([b for b in blocks if isinstance(b, dict)])
    return found


def invented_facts(blocks: list, data_script: str, known: str, today: str = "") -> list[dict]:
    """The facts of a written page that its brief (`known`: everything the writer was given about
    the business) does not contain, as [{"kind", "text"}]: prices, durations and quantities,
    percentages, ratings, years (the current and the next one pass: an opening "in October"),
    and a quotation signed by a name the brief does not know."""
    numbers = {_norm(n) for n in NUMBER.findall(known or "")}
    year = int(str(today)[:4]) if str(today)[:4].isdigit() else None
    this_year = {str(year), str(year + 1)} if year else set()
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, text: str) -> None:
        key = (kind, text.lower())
        if key not in seen:
            seen.add(key)
            found.append({"kind": kind, "text": text})

    for text in [*_copy(blocks), *_script_copy(data_script)]:
        rest = text
        for kind, pattern in (("price", MONEY), ("quantity", QUANTITY), ("figure", PERCENT), ("rating", RATING)):
            for match in pattern.finditer(rest):
                if _first_number(match.group(0)) not in numbers:
                    add(kind, match.group(0).strip())
            # a year inside an amount is the amount's: blanked before the years are read
            rest = pattern.sub(" ", rest)
        for match in YEAR.finditer(rest):
            if match.group(0) not in numbers and match.group(0) not in this_year:
                add("year", " ".join(rest[max(0, match.start() - 12) : match.end()].split()[-2:]))
    lowered = (known or "").lower()
    for signature in _signed_quotations(blocks, lowered):
        add("testimonial", signature)
    if TESTIMONIAL_KEY.search(data_script or "") and not TESTIMONIAL_WORD.search(known or ""):
        add("testimonial", "the testimonials of the page's data")
    return found


def facts_issues(found: list[dict]) -> list[dict]:
    """The facts found, as the issues a revision pass is given (visual_check.revision_instructions)."""
    issues = []
    for kind in ("price", "testimonial", "year", "figure", "rating", "quantity"):
        texts = [f["text"] for f in found if f["kind"] == kind]
        if texts:
            issues.append({
                "severity": "high",
                "area": "facts",
                "problem": f"{LABELS[kind]} the brief does not give: " + ", ".join(f"'{t}'" for t in texts[:8]),
                "fix": FIXES[kind],
            })
    return issues


def known_text(site: dict, contact_prompt: str = "") -> str:
    """Everything the page writer was given about the business: what a page may state."""
    parts = [site.get("site_name"), site.get("activity"), site.get("differentiators"), " ".join(site.get("categories") or []), " ".join(site.get("brands") or []), contact_prompt]
    return " ".join(str(part) for part in parts if part)


# //// Neoffice — a bracketed placeholder never reaches a visitor (2026-09-14). With no e-mail and no
# //// website in its business data, a contact page printed "[email address]" and "[website]" under
# //// their labels, and the build published it.
PLACEHOLDER = re.compile(r"\[\s*[^\W\d_][^\[\]<>{}|]{0,40}?\s*\]")
SEPARATOR = r"\s*(?:[·|•,–—-]\s*)?"
LABEL_ELEMENTS = {"p", "span", "div", "small", "strong", "label", "dt", "h4", "h5", "h6"}


def _text_of(block: dict) -> str:
    return " ".join(TAG.sub(" ", str(block.get("innerHTML") or "")).split())


def _is_label(block: dict) -> bool:
    """A short caption naming the detail that follows ("EMAIL", "Website:")."""
    text = _text_of(block)
    return (
        str(block.get("element") or "").lower() in LABEL_ELEMENTS
        and 0 < len(text) <= 24
        and len(text.split()) <= 3
        and not PLACEHOLDER.search(text)
        and not any(isinstance(c, dict) and _text_of(c) for c in block.get("children") or [])
    )


# //// Neoffice — a sentence that held a placeholder goes whole (2026-09-18). Cutting the
# //// placeholder alone published "Payments are processed by" on a privacy page, and the reviewer
# //// read it exactly as it was: a sentence trailing off. A sentence carrying a placeholder is
# //// there to carry the value that was missing; without it there is nothing left to say. A line
# //// with no sentence at all — "Atelier Nord Sàrl · [website] · Lausanne" — is a list, not a
# //// sentence, and there only the placeholder and its separator go.
TERMINATOR = re.compile(r"[.!?…]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])(?=\s)")


def _cut(html: str) -> str:
    """The placeholder cut out of a longer text: the whole sentence when it was written as one,
    the placeholder and the separator that tied it to the rest when the line is a list."""
    out = []
    for piece in re.split(r"(<[^>]+>)", html):
        if piece.startswith("<") or not PLACEHOLDER.search(piece):
            out.append(piece)
            continue
        if TERMINATOR.search(piece):
            out.append("".join(s for s in SENTENCE_SPLIT.split(piece) if not PLACEHOLDER.search(s)))
            continue
        cut = re.sub(SEPARATOR + PLACEHOLDER.pattern, "", piece)
        out.append(re.sub(PLACEHOLDER.pattern + SEPARATOR, "", cut))
    return "".join(out).strip()


def drop_placeholders(blocks: list) -> list[str]:
    """Takes the bracketed placeholders out of a written page. A block that shows nothing else goes,
    with the short label just before it, and a wrapper they leave empty goes too; inside a longer
    text the placeholder alone is cut. Jinja and bound text are left alone. Returns one line per
    edit."""
    edits: list[str] = []

    def clean(parent: dict) -> bool:
        """Cleans the children of `parent`; True when it had some and has none left."""
        kids = parent.get("children")
        if not isinstance(kids, list) or not kids:
            return False
        kept: list = []
        for child in kids:
            if not isinstance(child, dict):
                kept.append(child)
                continue
            html = str(child.get("innerHTML") or "")
            if html and "{%" not in html and "{{" not in html and PLACEHOLDER.search(html):
                text = _text_of(child)
                if PLACEHOLDER.fullmatch(text):
                    if kept and isinstance(kept[-1], dict) and _is_label(kept[-1]):
                        edits.append(f"label '{_text_of(kept.pop())}' dropped with its placeholder")
                    edits.append(f"'{text}' dropped")
                    continue
                child["innerHTML"] = _cut(html)
                # //// Neoffice — nothing left to show (2026-09-18): a block whose only sentence
                # //// held the placeholder goes the way a bare placeholder does, label included.
                if not _text_of(child):
                    if kept and isinstance(kept[-1], dict) and _is_label(kept[-1]):
                        edits.append(f"label '{_text_of(kept.pop())}' dropped with its placeholder")
                    edits.append(f"'{text[:48]}' dropped with the sentence that held its placeholder")
                    continue
                edits.append(f"placeholder cut from '{text[:48]}'")
            if clean(child) and not _text_of(child):
                edits.append("wrapper left empty dropped")
                continue
            kept.append(child)
        parent["children"] = kept
        return not kept

    for block in blocks or []:
        if isinstance(block, dict):
            clean(block)
    return edits


# //// Neoffice — a contact detail comes from the business data or does not appear (2026-09-14). Told to
# //// leave out a detail it did not have, the model wrote a plausible one instead: a consumer site's contact
# //// page showed an e-mail address and a website that do not exist, under the real phone number.
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
WEB = re.compile(
    r"\b(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:ch|com|net|org|io|swiss|shop|store|fr|de|it|eu|co|info|biz)\b(?:/[^\s<\"']*)?",
    re.I,
)
PHONE = re.compile(r"(?:\+|\b00)\d[\d\s().-]{7,}\d")


def _host(address: str) -> str:
    return re.sub(r"^(?:https?://)?(?:www\.)?", "", address.lower()).split("/", 1)[0]


def _digits(number: str) -> str:
    return re.sub(r"\D", "", number)[-9:]


def invented_contacts(text: str, known: str) -> list[str]:
    """The e-mail addresses, web addresses and phone numbers of `text` that `known` (what the brief
    and the business data give) does not contain."""
    emails = {e.lower() for e in EMAIL.findall(known or "")}
    hosts = {_host(w) for w in WEB.findall(known or "")} | {e.split("@", 1)[1] for e in emails}
    phones = {_digits(p) for p in PHONE.findall(known or "")}
    found: list[str] = []
    for email in EMAIL.findall(text or ""):
        if email.lower() not in emails:
            found.append(email)
    rest = EMAIL.sub(" ", text or "")
    for web in WEB.findall(rest):
        if _host(web) not in hosts:
            found.append(web)
    for phone in PHONE.findall(rest):
        if _digits(phone) not in phones:
            found.append(phone)
    return found


def drop_invented_contacts(blocks: list, known: str) -> list[str]:
    """Takes out of a written page the contact details the brief does not give. A block that shows
    nothing else goes, with the short label just before it; inside a longer text the detail is cut,
    with its link. Jinja and bound text are left alone. Returns one line per edit."""
    edits: list[str] = []

    def clean(parent: dict) -> bool:
        kids = parent.get("children")
        if not isinstance(kids, list) or not kids:
            return False
        kept: list = []
        for child in kids:
            if not isinstance(child, dict):
                kept.append(child)
                continue
            html = str(child.get("innerHTML") or "")
            if html and "{%" not in html and "{{" not in html:
                text = _text_of(child)
                invented = invented_contacts(text, known)
                if invented:
                    rest = text
                    for item in invented:
                        rest = rest.replace(item, " ")
                    if len(re.sub(r"[\W_]+", "", rest)) < 3:
                        if kept and isinstance(kept[-1], dict) and _is_label(kept[-1]):
                            edits.append(f"label '{_text_of(kept.pop())}' dropped with its contact")
                        edits.append(f"'{text[:48]}' dropped: not in the business data")
                        continue
                    for item in invented:
                        html = re.sub(r"<a\b[^>]*>[^<]*" + re.escape(item) + r"[^<]*</a>", "", html)
                        html = re.sub(SEPARATOR + re.escape(item), "", html).replace(item, "")
                    child["innerHTML"] = html.strip()
                    edits.append(f"{', '.join(invented)} cut: not in the business data")
            if clean(child) and not _text_of(child):
                edits.append("wrapper left empty dropped")
                continue
            kept.append(child)
        parent["children"] = kept
        return not kept

    for block in blocks or []:
        if isinstance(block, dict):
            clean(block)
    return edits

# //// Neoffice — added 2026-09-18: a local picture that does not exist is not a picture.
# //// Shown nine brand names and a folder of files called marque-<brand>.jpg, the writer filled
# //// the gap by inventing the one it lacked: <img src="/files/marque-west_snowboards.jpg"> for a
# //// file nobody ever uploaded. It reached the published home as a broken frame, the gate saw it
# //// (broken-image), and the only thing that could repair it was another model call. A path that
# //// resolves to nothing is checked here instead, before the page is written.
IMG_SRC = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>', re.I)
LOCAL_FILE = re.compile(r"^/(?:files|private/files)/")


def _file_is_there(url: str) -> bool:
    """Whether a /files path resolves on this site. Anything not local is left alone."""
    if not LOCAL_FILE.match(url or ""):
        return True
    clean = (url or "").split("?")[0]
    try:
        import os

        import frappe

        if frappe.db.exists("File", {"file_url": clean}):
            return True
        if clean.startswith("/files/"):
            return os.path.exists(frappe.get_site_path("public", "files", clean[len("/files/"):]))
        return os.path.exists(frappe.get_site_path("private", "files", clean[len("/private/files/"):]))
    except Exception:
        # unknowable here: never drop a picture on a doubt
        return True


def drop_missing_pictures(blocks: list) -> list[str]:
    """Takes out every <img> whose local file is not there, and the wrapper it leaves empty.
    Returns one line per edit."""
    edits: list[str] = []

    def clean(parent: dict) -> None:
        kids = parent.get("children")
        if not isinstance(kids, list) or not kids:
            return
        kept: list = []
        for child in kids:
            if not isinstance(child, dict):
                kept.append(child)
                continue
            src = ((child.get("attributes") or {}).get("src") or "").strip()
            if str(child.get("element") or "").lower() == "img" and src and not _file_is_there(src):
                edits.append(f"picture dropped, no such file: {src[:70]}")
                continue
            html = child.get("innerHTML")
            if isinstance(html, str) and "<img" in html:
                missing = [u for u in IMG_SRC.findall(html) if not _file_is_there(u)]
                for url in missing:
                    html = IMG_SRC.sub(lambda m: "" if m.group(1) == url else m.group(0), html)
                    edits.append(f"picture dropped, no such file: {url[:70]}")
                if missing:
                    child["innerHTML"] = html
            clean(child)
            kept.append(child)
        parent["children"] = kept

    for block in blocks or []:
        if isinstance(block, dict):
            clean(block)
    return edits

# //// Neoffice — added 2026-09-18: a name the business gave is spelled the way the business gave
# //// it. Handed the exact list of the nine brands it distributes, a writer published one of them
# //// with a single letter changed — on a partner's name, in the section that exists to name them.
# //// A near miss of a given name is a typo, not a choice.
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][\wÀ-ÖØ-öø-ÿ'’-]*")


def _distance(a: str, b: str, ceiling: int = 3) -> int:
    """Levenshtein, stopped at `ceiling`: past it the two words are not the same name."""
    if abs(len(a) - len(b)) > ceiling:
        return ceiling + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        if min(current) > ceiling:
            return ceiling + 1
        previous = current
    return previous[-1]


def _protected(chunk: str, given: list[str]) -> list[tuple[int, int]]:
    """Where the chunk already spells a given name exactly. Nothing inside is a misspelling.

    //// Neoffice — 2026-09-18, found on a client site the same hour the rule shipped: the brands
    included a two-word name whose SECOND word was also a category on its own, one letter apart in
    the plural. The one-word category rewrote the inside of the brand, and five published pages
    lost a partner's name. A span inside a name that is already right is never a near miss."""
    spans = []
    for name in sorted(given, key=len, reverse=True):
        for found in re.finditer(re.escape(name), chunk, re.I):
            spans.append((found.start(), found.end()))
    return spans


def _respell(chunk: str, given: list[str], lowered: set[str], edits: list[str]) -> str:
    """One text chunk, with every near miss of a given name put right."""
    tokens = list(WORD.finditer(chunk))
    if not tokens:
        return chunk
    safe = _protected(chunk, given)
    plurals = {f"{n}s" for n in lowered} | {f"{n}es" for n in lowered}
    swaps = []
    taken: set[int] = set()
    for name in given:
        count = len(name.split())
        # a short name is a typo only one letter away; a long one may be two
        limit = 1 if len(name) < 8 else 2
        for i in range(len(tokens) - count + 1):
            if taken & set(range(i, i + count)):
                continue
            start, end = tokens[i].start(), tokens[i + count - 1].end()
            if any(a <= start and end <= b for a, b in safe):
                continue
            found = chunk[start:end]
            if not found[:1].isupper() or found == name:
                continue
            low = found.lower()
            if low == name.lower() or low in lowered:
                continue
            # //// Neoffice — a plural is not a typo: a page naming the category in the plural is
            # //// writing French, not misspelling the business's word (2026-09-18)
            if low in plurals:
                continue
            if _distance(low, name.lower(), limit) > limit:
                continue
            swaps.append((start, end, name, found))
            taken.update(range(i, i + count))
    for start, end, name, found in sorted(swaps, reverse=True):
        chunk = chunk[:start] + name + chunk[end:]
        edits.append(f"'{found}' spelled as the business gave it: '{name}'")
    return chunk


def spell_names_as_given(blocks: list, names: list[str]) -> list[str]:
    """Puts every near miss of a name the business gave (its brands, its categories) back to the
    spelling it was given, in the copy only — never inside a tag. Returns one line per edit."""
    given = [n.strip() for n in dict.fromkeys(names or []) if len(n.strip()) >= 4]
    if not given:
        return []
    lowered = {n.lower() for n in given}
    edits: list[str] = []

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        html = block.get("innerHTML")
        if isinstance(html, str) and html and "{%" not in html and "{{" not in html:
            pieces = re.split(r"(<[^>]+>)", html)
            rebuilt = [p if p.startswith("<") else _respell(p, given, lowered, edits) for p in pieces]
            joined = "".join(rebuilt)
            if joined != html:
                block["innerHTML"] = joined
        for child in block.get("children") or []:
            walk(child)

    for block in blocks or []:
        walk(block)
    return edits
