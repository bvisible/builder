# //// Neoffice — added file (no upstream equivalent): a page whose component belongs to an app that is no
# //// longer installed still renders, and the component's own "anything to show?" check is read at render time.
"""Two defects of the same lot: what a page does with the component of an app it no longer has.

G4. A component is a `{% include "<app>/templates/includes/x.html" %}` Jinja tag laid in a block. When the app
that owns the template is removed from the site, Jinja raises TemplateNotFound, frappe turns it into a
ValidationError, and THE PUBLISHED PAGE ANSWERS AN ERROR PAGE: the whole page for one retired component.
Expected: the block is left out, the rest of the page is drawn, and the incident reaches the Error Log.

G8. The renderer drops an include "with nothing to show" through DATA_CHECKS, a table of eight file names.
The `data_check` an app declares for its own component (hooks.py `website_components`, read by the editor
and by the generator) was ignored at render time, so a component of another app drew its empty frame.
Expected: the catalogue's check applies as well, and the eight files of the table behave as they did.
"""

import itertools
import json
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response, get_response_content

from builder import api, empty_includes, missing_includes
from builder.site_ai import components
from builder.utils import Block

# an app that is nowhere: the template can never be found, on any instance
GONE = "retired_app/templates/includes/room_bar.html"
GONE_TAG = f'{{% include "{GONE}" %}}'
# a template that exists wherever the builder is installed, and is in no check table
THERE = "builder/templates/includes/contact_form.html"
THERE_TAG = f'{{% include "{THERE}" %}}'
THERE_MARK = "builder-contact-form"

_ids = itertools.count(1)


def text(words):
	return {"blockId": f"t{next(_ids)}", "element": "p", "innerHTML": words, "baseStyles": {}}


def heading(words):
	return {"blockId": f"h{next(_ids)}", "element": "h2", "innerHTML": words, "baseStyles": {}}


def tag_block(tag):
	return {"blockId": f"i{next(_ids)}", "element": "div", "innerHTML": tag, "baseStyles": {}}


def box(*children):
	return {"blockId": f"b{next(_ids)}", "element": "div", "children": list(children), "baseStyles": {}}


def texts(blocks):
	out = []

	def walk(block):
		if block.get("innerHTML"):
			out.append(block["innerHTML"])
		for child in block.get("children") or []:
			walk(child)

	for root in blocks if isinstance(blocks, list) else [blocks]:
		walk(root)
	return out


def a_page_name():
	return f"test-missing-include-{frappe.generate_hash(length=8)}"


def component(path, check="", app="frappe"):
	return components.Component(
		path=path, label="A test component", shows="a test component", app=app, data_check=check
	)


# the checks a component of another app would declare: a dotted path, `(profile)` or `()`
def shows_nothing(profile=None):
	return False


def shows_something(profile=None):
	return True


def shows_only_for_the_north(profile=None):
	return profile == "north"


def shows_nothing_without_a_profile():
	return False


def broken_check(profile=None):
	raise RuntimeError("the app this check reads is broken")


CHECKS = "builder.tests.test_missing_includes"


class TestTheTemplateOfAnAppThatIsGone(FrappeTestCase):
	def test_a_template_of_an_app_that_is_not_there_is_missing(self):
		self.assertTrue(missing_includes.template_is_missing(GONE))

	def test_a_template_that_exists_is_not_missing(self):
		self.assertFalse(missing_includes.template_is_missing(THERE))

	def test_a_path_that_climbs_out_of_the_apps_is_missing(self):
		self.assertTrue(missing_includes.template_is_missing("builder/../../etc/passwd"))

	def test_what_cannot_be_known_is_not_missing(self):
		# a template that fails to compile is the page's own error to show, never a reason to cut it out
		with patch("frappe.utils.jinja.get_jenv", side_effect=RuntimeError("no environment")):
			self.assertFalse(missing_includes.template_is_missing(THERE))


class TestPruningDropsTheIncludeOfAGoneApp(FrappeTestCase):
	def page(self, include=GONE_TAG):
		return [box(box(heading("Our rooms"), tag_block(include)), box(text("Contact us at the desk")))]

	def test_the_block_goes_and_the_page_keeps_the_rest(self):
		kept = empty_includes.prune_for_render(self.page(), page=a_page_name())
		words = texts(kept)
		self.assertNotIn(GONE_TAG, words)
		self.assertIn("Contact us at the desk", words)

	def test_the_heading_that_announced_it_goes_with_it(self):
		# a "Our rooms" title over a hole is the defect empty_includes exists for
		kept = empty_includes.prune_for_render(self.page(), page=a_page_name())
		self.assertNotIn("Our rooms", texts(kept))

	def test_a_tag_written_with_its_options_goes_too(self):
		tag = '{%- set limit = 3 -%}{%- set title = "Rooms" -%}' + GONE_TAG
		kept = empty_includes.prune_for_render(json.dumps(self.page(tag)), page=a_page_name())
		self.assertNotIn(GONE, json.dumps(kept))

	def test_an_include_that_is_there_stays(self):
		blocks = self.page(THERE_TAG)
		self.assertEqual(texts(empty_includes.prune_for_render(blocks, page=a_page_name())), texts(blocks))

	def test_every_include_of_a_gone_app_goes_but_only_that(self):
		blocks = [box(box(tag_block(GONE_TAG)), box(tag_block(THERE_TAG)), box(text("still here")))]
		words = texts(empty_includes.prune_for_render(blocks, page=a_page_name()))
		self.assertNotIn(GONE_TAG, words)
		self.assertIn(THERE_TAG, words)
		self.assertIn("still here", words)


class TestAnIncludeThePruningCannotSee(FrappeTestCase):
	"""A tag inside a longer text, or written by hand: it is not a block of its own, so it never reaches the pruning."""

	def test_the_tag_goes_and_the_text_around_it_stays(self):
		content = f"<p>Before</p>{GONE_TAG}<p>After</p>"
		self.assertEqual(
			missing_includes.drop_missing_includes(content, a_page_name()), "<p>Before</p><p>After</p>"
		)

	def test_every_occurrence_goes(self):
		content = f"{GONE_TAG} and {GONE_TAG}"
		self.assertNotIn(GONE, missing_includes.drop_missing_includes(content, a_page_name()))

	def test_a_tag_with_options_goes_whole(self):
		content = f'<p>x</p>{{% include "{GONE}" with context %}}<p>y</p>'
		self.assertEqual(missing_includes.drop_missing_includes(content, a_page_name()), "<p>x</p><p>y</p>")

	def test_an_include_that_is_there_is_left_exactly_as_it_is(self):
		content = f"<p>Before</p>{THERE_TAG}<p>After</p>"
		self.assertEqual(missing_includes.drop_missing_includes(content, a_page_name()), content)

	def test_an_include_that_says_it_may_be_missing_is_left_to_jinja(self):
		content = f'{{% include "{GONE}" ignore missing %}}'
		self.assertEqual(missing_includes.drop_missing_includes(content, a_page_name()), content)

	def test_an_include_by_name_is_left_alone(self):
		# the name is a variable: nothing says which template it will be
		content = "{% include partial_name %}"
		self.assertEqual(missing_includes.drop_missing_includes(content, a_page_name()), content)

	def test_a_text_without_any_include_is_returned_as_it_is(self):
		for content in ("", None, "<p>No Jinja here</p>", "{{ a_value }}"):
			self.assertEqual(missing_includes.drop_missing_includes(content, a_page_name()), content)


class TestTheIncidentReachesTheErrorLog(FrappeTestCase):
	def rows(self, page):
		frappe.deferred_insert.save_to_db()
		return frappe.get_all(
			"Error Log",
			filters={"method": ["like", "Missing page include%"], "error": ["like", f"%{page}%"]},
			fields=["method", "error"],
		)

	def test_the_title_comes_first_and_the_message_apart(self):
		with patch.object(frappe, "log_error") as log_error:
			missing_includes.report_missing_include(GONE, a_page_name())
		log_error.assert_called_once()
		title, message = log_error.call_args.args
		self.assertLessEqual(len(title), 140)
		self.assertIn(GONE, title)
		self.assertNotIn("\n", title)
		self.assertIn(GONE, message)
		self.assertNotEqual(title, message)

	def test_a_very_long_path_cannot_overflow_the_title(self):
		with patch.object(frappe, "log_error") as log_error:
			missing_includes.report_missing_include(
				"retired_app/templates/" + "x/" * 200 + "room.html", a_page_name()
			)
		self.assertLessEqual(len(log_error.call_args.args[0]), 140)

	def test_the_line_is_in_the_error_log_and_names_the_page(self):
		page = a_page_name()
		missing_includes.report_missing_include(GONE, page)
		rows = self.rows(page)
		self.assertEqual(len(rows), 1)
		self.assertIn(GONE, rows[0].method)

	def test_a_page_seen_again_does_not_flood_the_log(self):
		page = a_page_name()
		for _ in range(5):
			missing_includes.report_missing_include(GONE, page)
		self.assertEqual(len(self.rows(page)), 1)

	def test_another_page_or_another_template_has_its_own_line(self):
		first, second = a_page_name(), a_page_name()
		missing_includes.report_missing_include(GONE, first)
		missing_includes.report_missing_include(GONE, second)
		missing_includes.report_missing_include("other_app/templates/includes/x.html", first)
		self.assertEqual(len(self.rows(first)), 2)
		self.assertEqual(len(self.rows(second)), 1)

	def test_a_log_that_fails_never_fails_the_page(self):
		with patch.object(frappe, "log_error", side_effect=RuntimeError("the database is gone")):
			missing_includes.report_missing_include(GONE, a_page_name())


ROUTE = "test-missing-include-page"


def delete_test_pages():
	# frappe names a Builder Page itself (page-<hash>): the route is what the test knows it by
	for name in frappe.get_all("Builder Page", {"route": ROUTE}, pluck="name"):
		frappe.delete_doc("Builder Page", name, force=True)


def publish(*children):
	return frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": "Rooms",
			"published": 1,
			"route": ROUTE,
			"blocks": Block(
				element="div",
				originalElement="body",
				children=[Block(**child) for child in children],
			).as_json(wrap_in_array=True),
		}
	).insert()


def section(*children):
	return {"element": "section", "children": [Block(**c) for c in children]}


def paragraph(words):
	return {"element": "p", "innerHTML": words}


def title(words):
	return {"element": "h2", "innerHTML": words}


def include_block(tag):
	return {"element": "div", "innerHTML": tag}


def as_a_visitor(path):
	"""What the page answers a person who is not signed in; the call the site's search index makes, too."""
	frappe.set_user("Guest")
	before = getattr(frappe.local, "no_cache", False)
	try:
		set_request(method="GET", path=path)
		frappe.local.no_cache = True
		return get_response(path)
	finally:
		frappe.local.no_cache = before
		frappe.set_user("Administrator")


class TestAPublishedPageWithAnIncludeOfAGoneApp(FrappeTestCase):
	def setUp(self):
		delete_test_pages()
		self.page = publish(
			section(paragraph("Welcome to the house")),
			section(title("Our rooms"), include_block(GONE_TAG)),
			section(paragraph("Open every day")),
		)

	def tearDown(self):
		delete_test_pages()

	def test_the_page_answers_200_and_draws_the_rest(self):
		response = as_a_visitor(f"/{ROUTE}")
		html = str(response.data, "utf-8")
		self.assertEqual(response.status_code, 200)
		self.assertIn("Welcome to the house", html)
		self.assertIn("Open every day", html)

	def test_the_block_is_empty_and_the_title_over_it_is_gone(self):
		html = str(as_a_visitor(f"/{ROUTE}").data, "utf-8")
		self.assertNotIn("retired_app", html)
		self.assertNotIn("Our rooms", html)
		self.assertNotIn("There was an error while rendering", html)

	def test_one_line_reaches_the_error_log_however_many_visits(self):
		for _ in range(3):
			as_a_visitor(f"/{ROUTE}")
		frappe.deferred_insert.save_to_db()
		rows = frappe.get_all(
			"Error Log",
			filters={"method": ["like", "Missing page include%"], "error": ["like", f"%{self.page.name}%"]},
		)
		self.assertEqual(len(rows), 1)

	def test_the_search_index_sees_the_page_instead_of_skipping_it(self):
		# frappe.search.website_search renders each route as Guest, in a try that drops the page on any error
		frappe.set_user("Guest")
		before = getattr(frappe.local, "no_cache", False)
		try:
			set_request(method="GET", path=f"/{ROUTE}")
			frappe.local.no_cache = True
			content = get_response_content(f"/{ROUTE}")
		finally:
			frappe.local.no_cache = before
			frappe.set_user("Administrator")
		self.assertIn("Welcome to the house", content)

	def test_the_html_the_preview_image_is_drawn_from_is_the_page_without_the_block(self):
		# generate_page_preview_image renders the page itself when it is not handed the html
		html = frappe.get_doc("Builder Page", self.page.name).get_preview_html()
		self.assertIn("Welcome to the house", html)
		self.assertNotIn("retired_app", html)

	def test_the_editors_preview_of_the_page_draws_it_too(self):
		set_request(method="GET", path="/")
		with patch.object(frappe, "enqueue_doc"):
			response = api.get_page_preview_html(self.page.name)
		html = str(response.data, "utf-8")
		self.assertEqual(response.status_code, 200)
		self.assertIn("Welcome to the house", html)
		self.assertNotIn("retired_app", html)


class TestTheSamePageUnderTheCacheOfAClientSite(FrappeTestCase):
	"""osiris runs with developer_mode and never caches a page; a client site does, for an anonymous visitor.
	`force_website_cache` is frappe's own switch for the rule of a production site."""

	def setUp(self):
		delete_test_pages()
		self.page = publish(
			section(paragraph("Welcome to the house")),
			section(title("Our rooms"), include_block(GONE_TAG)),
			section(paragraph("Open every day")),
		)
		frappe.flags.force_website_cache = True

	def tearDown(self):
		frappe.flags.force_website_cache = False
		frappe.local.no_cache = False
		frappe.set_user("Administrator")
		delete_test_pages()

	def visit(self):
		frappe.set_user("Guest")
		set_request(method="GET", path=f"/{ROUTE}")
		frappe.local.no_cache = False
		frappe.local.response = frappe._dict()
		response = get_response(f"/{ROUTE}")
		return (
			response.status_code,
			str(response.data, "utf-8"),
			bool(frappe.local.response.get("from_cache")),
		)

	def test_the_page_that_is_cached_is_the_page_without_the_block_and_costs_one_line(self):
		status, html, _ = self.visit()
		self.assertEqual(status, 200)
		self.assertIn("Open every day", html)
		self.assertNotIn("retired_app", html)
		status, html, from_cache = self.visit()
		self.assertTrue(from_cache, "the second visit should be answered from the cache of pages")
		self.assertEqual(status, 200)
		self.assertIn("Welcome to the house", html)
		self.assertNotIn("retired_app", html)
		# the scheduler writes the deferred lines as Administrator, not as the visitor
		frappe.set_user("Administrator")
		frappe.deferred_insert.save_to_db()
		rows = frappe.get_all(
			"Error Log",
			filters={"method": ["like", "Missing page include%"], "error": ["like", f"%{self.page.name}%"]},
		)
		self.assertEqual(len(rows), 1)


class TestAPageWithAnIncludeInsideALongerText(FrappeTestCase):
	"""A tag the pruning cannot see (it shares its block with other markup) must not break the page either."""

	def setUp(self):
		delete_test_pages()
		publish(
			section(paragraph("Welcome to the house")),
			section({"element": "div", "innerHTML": f"<p>Book here</p>{GONE_TAG}<p>or at the desk</p>"}),
		)

	def tearDown(self):
		delete_test_pages()

	def test_the_page_answers_200_and_keeps_the_text_around_the_tag(self):
		response = as_a_visitor(f"/{ROUTE}")
		html = str(response.data, "utf-8")
		self.assertEqual(response.status_code, 200)
		self.assertIn("Book here", html)
		self.assertIn("or at the desk", html)
		self.assertNotIn("retired_app", html)


class TestAComponentTheEditorCannotDraw(FrappeTestCase):
	def test_the_editors_card_for_a_component_whose_template_is_gone_does_not_raise(self):
		gone = component(GONE)
		with patch.object(components, "catalogue", return_value=[gone]):
			answer = api.render_component_preview(GONE_TAG)
		# the canvas stands in with its own card, or says there is nothing to show; it never fails
		self.assertIn(answer["state"], ("empty", "error"))
		self.assertEqual(answer["html"], "")


class TestTheCataloguesDataCheckIsReadAtRenderTime(FrappeTestCase):
	"""A component of another app (a hotel's rooms, a salon's services) declares `data_check` in hooks.py."""

	PATH = "frappe/templates/includes/hotel_rooms.html"

	def catalogue(self, check):
		return patch.object(components, "catalogue", return_value=[component(self.PATH, check)])

	def test_a_check_that_says_nothing_to_show_is_read(self):
		with self.catalogue(f"{CHECKS}.shows_nothing"):
			self.assertIs(empty_includes.include_has_data(self.PATH), False)

	def test_a_check_that_says_something_to_show_is_read(self):
		with self.catalogue(f"{CHECKS}.shows_something"):
			self.assertIs(empty_includes.include_has_data(self.PATH), True)

	def test_the_check_gets_the_profile_of_the_site(self):
		with self.catalogue(f"{CHECKS}.shows_only_for_the_north"):
			self.assertIs(empty_includes.include_has_data(self.PATH, "north"), True)
			self.assertIs(empty_includes.include_has_data(self.PATH, "south"), False)

	def test_a_check_without_a_parameter_is_called_without_one(self):
		with self.catalogue(f"{CHECKS}.shows_nothing_without_a_profile"):
			self.assertIs(empty_includes.include_has_data(self.PATH, "north"), False)

	def test_a_check_that_fails_counts_as_nothing_to_show(self):
		with self.catalogue(f"{CHECKS}.broken_check"):
			self.assertIs(empty_includes.include_has_data(self.PATH), False)

	def test_a_component_with_no_check_is_drawn_as_before(self):
		with self.catalogue(""):
			self.assertIsNone(empty_includes.include_has_data(self.PATH))

	def test_a_path_the_catalogue_does_not_hold_is_drawn_as_before(self):
		with self.catalogue(f"{CHECKS}.shows_nothing"):
			self.assertIsNone(empty_includes.include_has_data("frappe/templates/includes/another.html"))

	def test_the_component_is_found_by_its_whole_path_not_by_its_file_name(self):
		# two apps may both ship a rooms.html: the check of one is not the other's
		with self.catalogue(f"{CHECKS}.shows_nothing"):
			self.assertIsNone(
				empty_includes.include_has_data("other_app/templates/includes/hotel_rooms.html")
			)

	def in_a_page(self):
		# the include is a template that exists: what takes it out must be the check, not a missing file
		return [box(box(heading("Our rooms"), tag_block(THERE_TAG)), box(text("Open every day")))]

	def test_the_renderer_drops_the_block_of_a_component_that_has_nothing_to_show(self):
		with patch.object(
			components, "catalogue", return_value=[component(THERE, f"{CHECKS}.shows_nothing", app="builder")]
		):
			words = texts(empty_includes.prune_for_render(self.in_a_page(), "north", page=a_page_name()))
		self.assertEqual(words, ["Open every day"])

	def test_the_renderer_keeps_the_block_of_a_component_that_has_something_to_show(self):
		with patch.object(
			components,
			"catalogue",
			return_value=[component(THERE, f"{CHECKS}.shows_something", app="builder")],
		):
			words = texts(empty_includes.prune_for_render(self.in_a_page(), "north", page=a_page_name()))
		self.assertEqual(words, ["Our rooms", THERE_TAG, "Open every day"])

	def test_the_check_is_asked_the_profile_of_the_site_being_rendered(self):
		with patch.object(
			components,
			"catalogue",
			return_value=[component(THERE, f"{CHECKS}.shows_only_for_the_north", app="builder")],
		):
			north = texts(empty_includes.prune_for_render(self.in_a_page(), "north", page=a_page_name()))
			south = texts(empty_includes.prune_for_render(self.in_a_page(), "south", page=a_page_name()))
		self.assertIn(THERE_TAG, north)
		self.assertNotIn(THERE_TAG, south)


class TestTheEightFilesOfTheTableAreNotTouched(FrappeTestCase):
	def test_each_one_is_still_decided_by_the_table_and_never_asks_the_catalogue(self):
		decided = {name: (lambda profile: True) for name in empty_includes.DATA_CHECKS}
		catalogue = MagicMock(return_value=[])
		with (
			patch.dict(empty_includes.DATA_CHECKS, decided),
			patch.object(components, "catalogue", catalogue),
		):
			for name in empty_includes.DATA_CHECKS:
				with self.subTest(name):
					self.assertIs(
						empty_includes.include_has_data(f"some_app/templates/includes/{name}"), True
					)
		catalogue.assert_not_called()

	def test_a_catalogue_entry_cannot_overrule_the_table(self):
		name = "google_map.html"
		entry = component(f"builder/templates/includes/{name}", f"{CHECKS}.shows_something")
		with (
			patch.dict(empty_includes.DATA_CHECKS, {name: lambda profile: False}),
			patch.object(components, "catalogue", return_value=[entry]),
		):
			self.assertIs(empty_includes.include_has_data(entry.path), False)

	def test_the_table_still_lists_exactly_the_eight_files(self):
		self.assertEqual(
			set(empty_includes.DATA_CHECKS),
			{
				"google_map.html",
				"opening_hours.html",
				"team_grid.html",
				"company_timeline.html",
				"product_carousel.html",
				"brand_carousel.html",
				"blog_listing.html",
				"contact_info.html",
			},
		)


class TestAPageWhoseComponentHasNothingToShow(FrappeTestCase):
	"""The same decision on a real page, by the include's real template: the contact form."""

	def setUp(self):
		delete_test_pages()
		# a text after the include: a short text right before a block that goes would be taken for its heading
		publish(
			section(paragraph("Welcome to the house")),
			section(include_block(THERE_TAG)),
			section(paragraph("Open every day")),
		)

	def tearDown(self):
		delete_test_pages()

	def render(self, check):
		entry = component(THERE, check, app="builder")
		with patch.object(components, "catalogue", return_value=[entry]):
			return str(as_a_visitor(f"/{ROUTE}").data, "utf-8")

	def test_a_component_with_something_to_show_is_drawn(self):
		html = self.render(f"{CHECKS}.shows_something")
		self.assertIn("Welcome to the house", html)
		self.assertIn(THERE_MARK, html)

	def test_a_component_with_nothing_to_show_is_left_out_and_the_page_stays(self):
		html = self.render(f"{CHECKS}.shows_nothing")
		self.assertIn("Welcome to the house", html)
		self.assertIn("Open every day", html)
		self.assertNotIn(THERE_MARK, html)


if __name__ == "__main__":
	unittest.main()
