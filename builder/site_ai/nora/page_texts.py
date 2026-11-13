# //// Neoffice — added file (no upstream equivalent): the words of a site's pages, kept for the site rebuilt over them.
"""The words of the pages a site build replaces, when the person asked to keep them (neoffice-maintenance#2624).

A site that already has its pages (an Accueil, an À propos, a Contact, its Services, written by the client or by a first
build) was rebuilt from the brief alone: « Créer mon site avec Nora » replaced the pages without reading them, and their
prices, years, people and testimonials were gone (and the facts pass would have taken them out anyway, as facts the brief
does not give). Jérémy, 13.11: Nora asks whether to keep the texts of the current pages, and if so the new site is written
from them.

The playbook asks (existing_pages_line), generate_site reads the pages it is about to replace (read_pages, before they are
deleted), every new page is given the words of the page it replaces (words_for, matched by route or title), and all of them
are known text for the facts pass (site_builder: client_words).
"""

from __future__ import annotations

import html
import json
import re
import unicodedata

TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
# a page's words given to the writer: enough for a long About, not a whole catalogue
MAX_PAGE_CHARS = 4000
# a playbook line names a few pages, not the whole site
MAX_LISTED = 8
HOME_KEYS = {"", "home", "accueil", "index", "start", "startseite", "inizio"}


def _texts(block: dict, out: list[str]) -> None:
    if not isinstance(block, dict):
        return
    raw = block.get("innerHTML")
    if raw:
        text = SPACE.sub(" ", html.unescape(TAG.sub(" ", str(raw)))).strip()
        # an include or a template expression is the site's machinery, not the client's words
        # a text said twice on a page (a block repeated for another width) is given once
        if text and "{%" not in text and "{{" not in text and text not in out:
            out.append(text)
    for child in block.get("children") or []:
        _texts(child, out)


def text_of_blocks(raw) -> str:
    """The words of a page's blocks (a Builder Page's draft_blocks or blocks, JSON or already parsed), one per line."""
    if not raw:
        return ""
    try:
        blocks = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return ""
    out: list[str] = []
    for block in blocks if isinstance(blocks, list) else [blocks]:
        _texts(block, out)
    text = "\n".join(out)
    return text[:MAX_PAGE_CHARS].rstrip()


def page_key(value) -> str:
    """A route or a title, compared: no accent, no case, words joined by -, the home under one name."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    key = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return "home" if key in HOME_KEYS else key


def words_for(page: dict, texts: list[dict]) -> str:
    """The words of the old page the new `page` replaces: same route, else same title; '' when none matches."""
    keys = {page_key(page.get("route")), page_key(page.get("title"))} - {""}
    for old in texts or []:
        if {page_key(old.get("route")), page_key(old.get("title"))} & keys:
            return old.get("text") or ""
    return ""


def all_words(texts: list[dict]) -> str:
    """Every kept page's words, for the facts pass: what a page may state."""
    return "\n".join(t.get("text") or "" for t in texts or [])


def read_pages(names: list[str]) -> list[dict]:
    """[{name, route, title, text}] of these Builder Pages, the draft first (what the person sees in the editor); a page
    with no words of its own is left out."""
    import frappe

    if not names:
        return []
    rows = frappe.get_all(
        "Builder Page",
        filters={"name": ["in", list(names)]},
        fields=["name", "route", "page_title", "draft_blocks", "blocks"],
    )
    pages = []
    for row in rows:
        text = text_of_blocks(row.draft_blocks or row.blocks)
        if text:
            pages.append({"name": row.name, "route": row.route or "", "title": row.page_title or "", "text": text})
    return pages


def existing_pages_line(page_id: str | None, profile: str | None) -> str:
    """The playbook's question, when the site the open page belongs to already has pages with words: keep them?"""
    import frappe

    filters = {"is_template": 0}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        filters["neo_website_profile"] = profile if profile else ("is", "not set")
    rows = frappe.get_all("Builder Page", filters=filters, fields=["name", "page_title", "project_folder", "draft_blocks", "blocks"])
    # read at every turn of the playbook: the pages of one site, a few tens of milliseconds next to a turn of the model
    titles = [
        r.page_title or r.name
        for r in rows
        if not (r.project_folder or "").startswith("Hub Inbox") and text_of_blocks(r.draft_blocks or r.blocks)
    ]
    if not titles:
        return ""
    shown = ", ".join(titles[:MAX_LISTED]) + (f" and {len(titles) - MAX_LISTED} more" if len(titles) > MAX_LISTED else "")
    return (
        f"This site already has {len(titles)} page(s) with words of their own ({shown}). Before the recap, ask with ONE present_ui "
        "confirm card, in the person's language: keep the texts of these pages? Say in its one line that the new site is then "
        "written from them (their prices, dates, names, people and testimonials kept) and that the pages themselves are "
        "replaced. Buttons: 'Keep my texts' / 'Start from scratch'. Pass keep_texts=true or false to generate_site, and name the "
        "choice in the recap. Never ask it on a site with no such page."
    )
