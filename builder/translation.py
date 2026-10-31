# //// Neoffice — added file (no upstream equivalent): the door of the site's translations (multilingual lot 4,
# //// neoffice-maintenance#2032).
"""A Builder page is written in the site's language and shown in the others by projection, not by copy.

When a request asks for another language of the site (``/de/...``), the page renders exactly as it does in the site's own
language, then each of its texts is replaced by its translation, found by the identifier of the block it sits in. Structure,
styles, pictures and links are the original's, so a change to any of them is in every language at once; only a text the
merchant edited in the site's language waits for its translation, and its previous translation stays on show meanwhile.

The translations live in ``neoffice_theme`` (the store, the translator, the address prefix). This module is the whole of what
Builder knows of them, and it does nothing on a bench without the theme, on a site with no additional language, and in the
editor's preview: a site that enabled nothing renders byte for byte as before. A failure here costs the translation, never
the page.
"""

import frappe

PAGE = "Builder Page"


def _door():
	"""``(localized, units)`` of the theme, or None where the theme is not installed."""
	try:
		from neoffice_theme import localized
		from neoffice_theme.translation import units
	except ImportError:
		return None
	return localized, units


def language() -> str | None:
	"""The additional language this request is rendered in, or None (the site's own language, an editor's preview)."""
	if getattr(getattr(frappe.local, "request", None), "for_preview", None):
		return None
	door = _door()
	if door is None:
		return None
	try:
		return door[0].content_language()
	except Exception:
		frappe.log_error("Translation: the language of the request is unreadable", frappe.get_traceback())
		return None


def has_languages() -> bool:
	"""Whether the site being served has an additional language: the header then keeps a place for the selector."""
	door = _door()
	if door is None:
		return False
	try:
		return bool(door[0].site_languages())
	except Exception:
		frappe.log_error("Translation: the languages of the site are unreadable", frappe.get_traceback())
		return False


def language_tag() -> str | None:
	"""The ``hreflang`` of the additional language of this request (``de-CH``), or None: what ``inLanguage`` says."""
	lang = language()
	if not lang:
		return None
	try:
		return (_door()[0].site_languages().get(lang) or {}).get("hreflang") or lang
	except Exception:
		return lang


def _translations(ref_doctype, ref_name, lang) -> dict:
	return _door()[0].get_document_translations(ref_doctype, ref_name, lang)


def localize_blocks(blocks, page_name):
	"""The page's blocks with their texts in the language of the request (the blocks given when it is the site's own)."""
	lang = language()
	if not lang or not page_name:
		return blocks
	try:
		return _door()[1].localize_blocks(blocks, _translations(PAGE, page_name, lang))
	except Exception:
		frappe.log_error("Translation: the blocks of a page could not be translated", frappe.get_traceback())
		return blocks


def page_text(page, fieldname):
	"""A text of the page itself (title, search description, subtitle) in the language of the request, else the source's."""
	source = page.get(fieldname) if hasattr(page, "get") else getattr(page, fieldname, None)
	lang = language()
	name = page.get("name") if hasattr(page, "get") else getattr(page, "name", None)
	if not lang or not source or not name:
		return source
	try:
		return _translations(PAGE, name, lang).get(("", fieldname)) or source
	except Exception:
		frappe.log_error("Translation: a page text could not be translated", frappe.get_traceback())
		return source


def page_label(doctype, name, source):
	"""The title of a page named in a list (the footer's legal links, a trail), in the language of the request."""
	if doctype != PAGE or not name or not source:
		return source
	lang = language()
	if not lang:
		return source
	try:
		return _translations(PAGE, name, lang).get(("", "page_title")) or source
	except Exception:
		frappe.log_error("Translation: a page title could not be translated", frappe.get_traceback())
		return source


def localize_chrome(config):
	"""The site chrome (header, footer, menus) with its texts in the language of the request, on the document in hand.

	The document is the request's own copy (never the cached one), so changing it here changes nothing for another request.
	"""
	lang = language()
	if not lang or config is None or config.flags.get("localized_to") == lang:
		return config
	try:
		found = _translations(config.doctype, config.name, lang)
		_door()[1].localize_chrome(config, found)
		config.flags.localized_to = lang
	except Exception:
		frappe.log_error("Translation: the chrome could not be translated", frappe.get_traceback())
	return config
