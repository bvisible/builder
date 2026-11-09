# //// Neoffice — added file (no upstream equivalent): which site the agent works for.
"""Which site (Website Profile) the agent's reads belong to.

An instance can host several sites, and a Builder Page is tagged for one of them
(`neo_website_profile`; a page with no tag is shared and serves everywhere). The agent's read
tools used to see every page of the instance with nothing to tell whose it was, so the
agent reasoned on another site's pages as if they were its own and once told the operator to
delete another client's home page (neoffice-maintenance#474).

The pages of other sites are LABELLED, not hidden: "why does this route answer elsewhere?"
(neoffice-maintenance#473) needs them. And with no site resolved (a one-site instance, the
editor on an untagged page) nothing changes: everything is visible and nothing is labelled.
"""

import frappe

PROFILE_FIELD = "neo_website_profile"
OTHER_SITE_KEY = "belongs_to_another_site"


def has_profile_field() -> bool:
	try:
		return bool(frappe.db.has_column("Builder Page", PROFILE_FIELD))
	except Exception:
		return False


def current_profile(ctx=None) -> str | None:
	"""The site the agent works for: the profile of the page open in the editor, else the one
	resolved for the request. None on an instance without Website Profiles, or when neither
	resolves (then every read stays exactly as it was)."""
	if not has_profile_field():
		return None
	if page_id := getattr(ctx, "page_id", None):
		if profile := frappe.db.get_value("Builder Page", page_id, PROFILE_FIELD):
			return profile
	return getattr(frappe.local, "website_profile", None) or None


def other_site_of(page_id: str | None, ctx=None) -> str | None:
	"""The profile a page is tagged for when that is NOT the site the agent works for, else None
	(its own site's page, a shared page, no site resolved)."""
	if not page_id or not (current := current_profile(ctx)):
		return None
	owner = frappe.db.get_value("Builder Page", page_id, PROFILE_FIELD) or None
	return owner if owner and owner != current else None


def mark_other_site(record: dict, current: str, owner: str | None) -> dict:
	"""`record` with the mark added when `owner` is another site's profile. A shared record
	(no owner) and the site's own are returned untouched."""
	if owner and owner != current:
		record[OTHER_SITE_KEY] = owner
	return record


def label_rows(rows, current: str, drop_owner_field: bool) -> list[dict]:
	"""A listing's rows as plain dicts, each marked when it belongs to another site. The owner
	column is dropped again when the caller did not ask for it."""
	labelled = []
	for row in rows:
		record = dict(row)
		owner = record.pop(PROFILE_FIELD, None) if drop_owner_field else record.get(PROFILE_FIELD)
		labelled.append(mark_other_site(record, current, owner))
	return labelled


def scope_listing(ctx, doctype: str, fields, filters) -> tuple[str | None, bool]:
	"""Decide whether a query_records listing is labelled. Returns (current profile, whether the
	profile column had to be added to the query to know each row's owner); the profile is None
	when the listing stays as it was: not Builder Pages, no site resolved, a caller filtering on
	the profile itself, or a field list the column cannot be added to safely (an aggregate)."""
	if doctype != "Builder Page":
		return None, False
	if not isinstance(fields, (list, tuple)) or any(not isinstance(f, str) or "(" in f for f in fields):
		return None, False
	if isinstance(filters, dict) and PROFILE_FIELD in filters:
		return None, False
	if not (current := current_profile(ctx)):
		return None, False
	return current, not any(f in ("*", PROFILE_FIELD) for f in fields)


def own_site_filters(profile: str) -> tuple[dict, ...]:
	"""Page filters in the order a reference should resolve: this site's own pages, then the
	shared (untagged) ones. Another site's pages come last, from the caller's unscoped lookup."""
	return ({PROFILE_FIELD: profile}, {PROFILE_FIELD: ("is", "not set")})
