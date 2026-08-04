"""Blog management for the Studio.

The blog app's own admin interface is the Frappe desk, which the Studio hides
(`overrides.desk_redirect`). Installing the plugin would otherwise give a site
owner a blog they can read but not write. This is the thin API the Studio's
Articles screen talks to — deliberately thin: it does not reimplement the blog,
it drives the blog app's own doctypes so a post written here is the same
document `bench` or the desk would produce.

Every entry point goes through `plugins.guard("blog")`. Hiding the sidebar
button is not access control; the endpoint is still reachable by name.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from builder import plugins

PLUGIN = "blog"
ROLES = ("System Manager", "Website Manager", "Blogger")

LIST_FIELDS = (
	"name",
	"title",
	"route",
	"published",
	"published_on",
	"blog_category",
	"blogger",
	"blog_intro",
	"meta_image",
	"read_time",
	"featured",
)

# What the editor may write. Everything else on Blog Post — read_time, the SEO
# preview, the email flags — is either derived or belongs to the desk.
WRITABLE = (
	"title",
	"blog_category",
	"blog_intro",
	"content_type",
	"content",
	"content_md",
	"content_html",
	"published",
	"published_on",
	"meta_title",
	"meta_description",
	"meta_image",
	"featured",
	"disable_comments",
)


def _check():
	plugins.guard(PLUGIN)
	frappe.only_for(ROLES)


def _installed() -> bool:
	return frappe.db.exists("DocType", "Blog Post") and plugins.is_enabled(PLUGIN)


@frappe.whitelist()
def get_status() -> dict:
	"""Whether the screen can work at all, and what it needs to get going.

	A blog with no category and no blogger cannot accept a post — the fields
	are mandatory on Blog Post. Rather than fail on save, the screen offers to
	create the missing pieces.
	"""
	frappe.only_for(ROLES)
	if not _installed():
		return {"ready": False, "installed": False}

	return {
		"ready": True,
		"installed": True,
		"categories": frappe.get_all(
			"Blog Category", fields=["name", "title", "published"], order_by="title asc"
		),
		"bloggers": frappe.get_all(
			"Blogger", filters={"disabled": 0}, fields=["name", "full_name"], order_by="full_name asc"
		),
		"counts": {
			"published": frappe.db.count("Blog Post", {"published": 1}),
			"draft": frappe.db.count("Blog Post", {"published": 0}),
		},
	}


@frappe.whitelist()
def list_posts(search: str | None = None, status: str | None = None) -> list:
	_check()
	filters = {}
	if status == "published":
		filters["published"] = 1
	elif status == "draft":
		filters["published"] = 0

	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {"title": ["like", like], "blog_intro": ["like", like]}

	return frappe.get_all(
		"Blog Post",
		fields=list(LIST_FIELDS),
		filters=filters,
		or_filters=or_filters,
		order_by="published desc, published_on desc, modified desc",
		limit_page_length=200,
	)


@frappe.whitelist()
def get_post(name: str) -> dict:
	_check()
	doc = frappe.get_doc("Blog Post", name)
	data = {field: doc.get(field) for field in WRITABLE}
	data["name"] = doc.name
	data["route"] = doc.route
	return data


def _ensure_blogger() -> str:
	"""Every post needs an author. Use this user's, creating it once."""
	existing = frappe.db.get_value("Blogger", {"user": frappe.session.user}, "name")
	if existing:
		return existing

	full_name = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
	doc = frappe.new_doc("Blogger")
	doc.short_name = frappe.scrub(full_name)[:20] or "author"
	doc.full_name = full_name
	doc.user = frappe.session.user
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_category() -> str:
	"""A blog with no category cannot take a post. Seed one, once."""
	existing = frappe.db.get_value("Blog Category", {"published": 1}, "name")
	if existing:
		return existing
	existing = frappe.db.get_value("Blog Category", {}, "name")
	if existing:
		return existing

	doc = frappe.new_doc("Blog Category")
	doc.title = _("General")
	doc.published = 1
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def save_post(post) -> dict:
	"""Create or update. `post.name` decides which."""
	_check()
	if isinstance(post, str):
		post = frappe.parse_json(post)

	name = post.get("name")
	if name:
		doc = frappe.get_doc("Blog Post", name)
	else:
		doc = frappe.new_doc("Blog Post")
		doc.blogger = _ensure_blogger()

	for field in WRITABLE:
		if field in post:
			doc.set(field, post[field])

	if not doc.blog_category:
		doc.blog_category = _ensure_category()
	if not doc.blogger:
		doc.blogger = _ensure_blogger()
	if doc.published and not doc.published_on:
		doc.published_on = now_datetime()

	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "route": doc.route, "published": doc.published}


@frappe.whitelist()
def set_published(name: str, published) -> dict:
	_check()
	doc = frappe.get_doc("Blog Post", name)
	doc.published = 1 if frappe.parse_json(str(published).lower()) else 0
	if doc.published and not doc.published_on:
		doc.published_on = now_datetime()
	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "published": doc.published, "route": doc.route}


@frappe.whitelist()
def delete_post(name: str) -> dict:
	_check()
	frappe.delete_doc("Blog Post", name)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def save_category(category) -> dict:
	_check()
	if isinstance(category, str):
		category = frappe.parse_json(category)

	name = category.get("name")
	doc = frappe.get_doc("Blog Category", name) if name else frappe.new_doc("Blog Category")
	doc.title = category.get("title") or doc.title
	doc.description = category.get("description")
	doc.published = 1 if category.get("published") else 0
	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "title": doc.title, "published": doc.published}


@frappe.whitelist()
def delete_category(name: str) -> dict:
	_check()
	used = frappe.db.count("Blog Post", {"blog_category": name})
	if used:
		frappe.throw(
			_("{0} articles are still in this category.").format(used),
			title=_("Category in use"),
		)
	frappe.delete_doc("Blog Category", name)
	frappe.db.commit()
	return {"ok": True}
