# //// Neoffice — added file (no upstream equivalent): a page whose include belongs to an app that is gone still renders.
"""An include of a template that no longer exists must not take the page down (SP1, G4).

A component is a `{% include "<app>/templates/includes/x.html" %}` Jinja tag laid in a block (site_ai/components.py,
Component.tag). The page is rendered by `render_template(content, context)` in BuilderPage.get_context. When the app
that owns the template is removed from the site, Jinja raises TemplateNotFound, frappe/utils/jinja.py turns it into a
ValidationError, and the published route answers an error page: the whole page lost for one retired component. Search
indexing, the editor's preview and the preview image render the very same way and failed the same way.

Two layers, one rule: what cannot be found is left out, the rest of the page is drawn, and the incident goes to the
Error Log, once an hour per page and template (a page that is not cached would otherwise write a row per visit).

  * prune_for_render (empty_includes.py) takes a block that is nothing but such an include out of the page, with the
    short heading that announced it: an empty frame under a title is what that module exists to avoid, and a template
    that cannot be found has nothing to show as much as a record that is empty.
  * drop_missing_includes takes the tag itself out of the text just before it is rendered: the safety net for an
    include that shares its block with other markup, or was written by hand, which the pruning cannot see.

Nothing is cut when the template can be found, when it only fails to compile (that is the page's own error to show),
or when the tag says `ignore missing` (Jinja already tolerates it).
"""

import re

import frappe

# `{% include "path" %}` with a literal path, and whatever options follow it (`with context`, `ignore missing`)
INCLUDE_TAG = re.compile(r"""\{%-?\s*include\s+(['"])([^'"{}]+)\1([^%]*?)-?%\}""")
IGNORE_MISSING = re.compile(r"\bignore\s+missing\b")

# the Error Log keeps the title of an entry in a field of this length
TITLE_MAX = 140
# one line per page and template in this time, however many visits the page gets
REPORT_SECONDS = 3600


def template_is_missing(path) -> bool:
	"""Whether the template at `path` cannot be found by the loader the render uses (frappe's own: the templates of
	the apps installed on this site). False when that cannot be known: a template that is there but does not
	compile, or an environment that does not start, is left to the render to say."""
	if not path or not isinstance(path, str):
		return False
	try:
		from frappe.utils.jinja import get_jenv
		from jinja2 import TemplateNotFound

		try:
			get_jenv().get_template(path)
		except TemplateNotFound:
			return True
	except Exception:
		return False
	return False


def report_missing_include(path, page=None) -> None:
	"""Writes the incident to the Error Log: the title first (the template, 140 characters at most), the message
	apart. Deferred: a visitor's request is a GET, whose writes frappe takes back, and a line that vanishes with the
	request is no record. Never raises: a log that fails must not be the reason a page fails."""
	try:
		key = f"builder_missing_include:{page or ''}:{path}"
		if frappe.cache.get_value(key, expires=True):
			return
		frappe.cache.set_value(key, 1, expires_in_sec=REPORT_SECONDS)
		frappe.log_error(
			f"Missing page include: {path}"[:TITLE_MAX],
			f"The Builder page {page or '(unknown)'} carries the include {path}, and no template is found there: "
			"the app that owns it is not installed on this site (any more).\n\n"
			"The block was left out and the rest of the page was drawn. Install the app again, or take the "
			"component out of the page.\n\n"
			f"One line per page and template every {REPORT_SECONDS // 60} minutes.",
			defer_insert=True,
		)
	except Exception:
		try:
			frappe.logger("builder").warning(
				f"Missing page include {path} (page {page}): the Error Log line failed", exc_info=True
			)
		except Exception:
			pass


def drop_missing_includes(content, page=None):
	"""`content` without the include tags whose template cannot be found, each reported. Returned as it is when
	there is nothing to drop and on any error: this runs on every page view and must never be the reason a page fails."""
	if not isinstance(content, str) or "include" not in content:
		return content
	checked = {}

	def drop(match):
		path = match.group(2)
		if IGNORE_MISSING.search(match.group(3)):
			return match.group(0)
		if path not in checked:
			checked[path] = template_is_missing(path)
		if not checked[path]:
			return match.group(0)
		report_missing_include(path, page)
		return ""

	try:
		return INCLUDE_TAG.sub(drop, content)
	except Exception:
		frappe.log_error("Missing includes: page rendered without the check", frappe.get_traceback())
		return content
