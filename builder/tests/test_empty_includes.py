# //// Neoffice — added file (no upstream equivalent): an include with nothing to show on the
# //// site is not drawn, nor the short heading that announces it (builder/empty_includes.py).
import copy
import itertools
import json
import os
import unittest
from unittest.mock import patch

from builder.empty_includes import (
	ANNOUNCEMENT_MAX_CHARS,
	DATA_CHECKS,
	include_has_data,
	prune_empty_includes,
	prune_for_render,
)

HOURS = "{% include 'webshop/templates/includes/opening_hours.html' %}"
MAP = "{% include 'builder/templates/includes/google_map.html' %}"
TEAM = "{% include 'builder/templates/includes/team_grid.html' %}"
TIMELINE = "{% include 'builder/templates/includes/company_timeline.html' %}"
FORM = "{% include 'builder/templates/includes/contact_form.html' %}"

_ids = itertools.count(1)


def text(element, words, **extra):
	return {"blockId": f"t{next(_ids)}", "element": element, "innerHTML": words, "baseStyles": {}, **extra}


def box(*children, **extra):
	return {
		"blockId": f"b{next(_ids)}",
		"element": "div",
		"children": list(children),
		"baseStyles": {},
		**extra,
	}


def include(tag):
	return {"blockId": f"i{next(_ids)}", "element": "div", "innerHTML": tag, "baseStyles": {}}


def photo():
	return text("img", "", attributes={"src": "/files/shop.jpg"})


def nothing(path):
	# every include that draws a record finds it empty; any other is not a record include
	return False if path.rsplit("/", 1)[-1] in DATA_CHECKS else None


def texts(blocks):
	out = []

	def walk(block):
		if block.get("innerHTML"):
			out.append(block["innerHTML"])
		for child in block.get("children") or []:
			walk(child)

	for block in blocks:
		walk(block)
	return out


class TestPruneEmptyIncludes(unittest.TestCase):
	def test_the_label_over_empty_hours_goes_with_them(self):
		# a contact section: the details, a photo, then "Hours" over the hours include
		details = box(text("p", "Address"), text("p", "Main Street 1, 1000 Town"))
		shop = photo()
		hours = box(text("p", "Hours"), include(HOURS))
		section = box(details, shop, hours)
		self.assertEqual(prune_empty_includes([box(section)], nothing), 1)
		# the group they sat in went with them; the rest of the section stays
		self.assertEqual(section["children"], [details, shop])

	def test_an_intro_with_a_photo_stays_when_the_team_goes(self):
		intro = box(text("h2", "The team"), text("p", "Six people who ride."), photo())
		section = box(intro, include(TEAM), element="section")
		prune_empty_includes([box(section)], nothing)
		self.assertEqual(section["children"], [intro])

	def test_a_section_that_only_announced_the_timeline_goes(self):
		before = box(text("h2", "Our story"), text("p", "x" * 300), element="section")
		heading = box(
			text("p", "04"), text("h2", "Milestones"), text("p", "A few dates that tell our story.")
		)
		root = box(before, box(heading, include(TIMELINE), element="section"))
		prune_empty_includes([root], nothing)
		self.assertEqual(root["children"], [before])

	def test_a_longer_text_says_something_of_its_own(self):
		lede = text("p", "We are a small team of riders. " * 6)
		self.assertGreater(len(lede["innerHTML"].strip()), ANNOUNCEMENT_MAX_CHARS)
		section = box(lede, include(TEAM))
		prune_empty_includes([box(section)], nothing)
		self.assertEqual(section["children"], [lede])

	def test_a_heading_over_more_than_the_include_stays(self):
		heading, after = text("h2", "Visit us"), text("p", "Or call us on weekdays.")
		group = box(heading, include(MAP), after)
		prune_empty_includes([box(group)], nothing)
		self.assertEqual(group["children"], [heading, after])

	def test_a_photo_after_the_include_does_not_keep_its_heading(self):
		heading = box(text("h2", "Milestones"), text("p", "Dates that tell our story."))
		picture = box(photo())
		section = box(heading, include(TIMELINE), picture)
		prune_empty_includes([box(section)], nothing)
		self.assertEqual(section["children"], [picture])

	def test_the_grey_frame_of_a_map_goes_with_it(self):
		words = box(text("h2", "Find us"), text("p", "y" * 200))
		frame = box(include(MAP), baseStyles={"backgroundColor": "#f0f0f0", "minHeight": "400px"})
		row = box(words, frame)
		prune_empty_includes([box(row)], nothing)
		self.assertEqual(row["children"], [words])

	def test_a_block_with_a_background_photo_stays(self):
		section = box(
			text("p", "Hours"), include(HOURS), baseStyles={"backgroundImage": "url('/files/x.jpg')"}
		)
		root = box(section)
		prune_empty_includes([root], nothing)
		self.assertEqual(root["children"], [section])
		self.assertEqual(section["children"], [])

	def test_the_announcement_budget_is_shared(self):
		far = text("p", "z" * 120)
		group = box(far, text("p", "Hours"), text("p", "Come and see us."), include(HOURS))
		prune_empty_includes([box(group, text("p", "after"))], nothing)
		self.assertEqual(group["children"], [far])

	def test_a_link_is_not_an_announcement(self):
		link = text("a", "Opening times", attributes={"href": "/hours"})
		group = box(link, include(HOURS))
		prune_empty_includes([box(group, text("p", "other"))], nothing)
		self.assertEqual(group["children"], [link])

	def test_an_include_with_its_record_or_unknown_stays(self):
		page = [box(box(text("p", "Hours"), include(HOURS)), box(text("p", "Write to us"), include(FORM)))]
		before = copy.deepcopy(page)
		self.assertEqual(
			prune_empty_includes(page, lambda path: True if "opening_hours" in path else None), 0
		)
		self.assertEqual(page, before)

	def test_an_include_written_with_parameters_stays(self):
		page = [box(box(text("p", "Hours"), include('{%- set display = "compact" -%}' + HOURS)))]
		before = copy.deepcopy(page)
		self.assertEqual(prune_empty_includes(page, nothing), 0)
		self.assertEqual(page, before)

	def test_a_top_level_block_is_never_removed(self):
		page = [box(text("p", "Hours"), include(HOURS))]
		prune_empty_includes(page, nothing)
		self.assertEqual(len(page), 1)
		self.assertEqual(page[0]["children"], [])


class TestIncludeHasData(unittest.TestCase):
	def test_an_include_that_draws_no_record_is_not_judged(self):
		self.assertIsNone(include_has_data("builder/templates/includes/contact_form.html"))

	def test_each_record_include_asks_its_record(self):
		with (
			patch("builder.empty_includes.site_has_address", return_value=False),
			patch("builder.empty_includes.opening_hours_configured", return_value=True),
			patch("builder.empty_includes.about_us_rows", side_effect=lambda field: field == "team_members"),
		):
			self.assertFalse(include_has_data("builder/templates/includes/google_map.html"))
			self.assertTrue(include_has_data("webshop/templates/includes/opening_hours.html"))
			self.assertTrue(include_has_data("builder/templates/includes/team_grid.html"))
			self.assertFalse(include_has_data("builder/templates/includes/company_timeline.html"))

	def test_a_failing_check_counts_as_nothing_to_show(self):
		with patch("builder.empty_includes.opening_hours_configured", side_effect=ImportError("no shop app")):
			self.assertFalse(include_has_data("webshop/templates/includes/opening_hours.html"))


class TestPruneForRender(unittest.TestCase):
	def test_a_page_without_includes_is_returned_as_is(self):
		blocks = json.dumps([box(text("p", "Hello"))])
		self.assertIs(prune_for_render(blocks), blocks)

	def test_a_page_is_untouched_when_nothing_goes(self):
		blocks = json.dumps([box(text("p", "Write to us"), include(FORM))])
		self.assertIs(prune_for_render(blocks), blocks)

	def test_the_stored_page_is_pruned_as_its_records_say(self):
		blocks = json.dumps([box(box(text("p", "Hours"), include(HOURS)), text("p", "Write to us"))])
		with patch("builder.empty_includes.opening_hours_configured", return_value=False):
			self.assertEqual(texts(prune_for_render(blocks)), ["Write to us"])
		with patch("builder.empty_includes.opening_hours_configured", return_value=True):
			self.assertIs(prune_for_render(blocks), blocks)

	def test_a_failure_leaves_the_page_as_it_was(self):
		blocks = json.dumps([box(text("p", "Hours"), include(HOURS))])
		with (
			patch("builder.empty_includes.prune_empty_includes", side_effect=RuntimeError("boom")),
			patch("frappe.log_error") as log,
		):
			self.assertIs(prune_for_render(blocks), blocks)
		log.assert_called_once()


class TestRenderedPage(unittest.TestCase):
	"""The renderer and Jinja as a page view runs them, with the record patched."""

	def test_the_team_and_its_heading_are_not_drawn_without_members(self):
		from frappe.utils.jinja import render_template

		from builder.builder.doctype.builder_page.builder_page import get_block_html

		page = [
			box(
				box(text("h2", "Our team"), include(TEAM), element="section"),
				box(text("p", "Write to us"), element="section"),
			)
		]

		def render():
			return render_template(get_block_html(prune_for_render(json.dumps(page)))[0], {})

		with patch("builder.empty_includes.about_us_rows", return_value=False):
			empty = render()
		with patch("builder.empty_includes.about_us_rows", return_value=True):
			full = render()
		self.assertNotIn("Our team", empty)
		self.assertNotIn("builder-team-grid", empty)
		self.assertIn("Write to us", empty)
		self.assertIn("Our team", full)
		self.assertIn("builder-team-grid", full)

	def test_a_page_view_prunes(self):
		import frappe

		page = frappe.new_doc("Builder Page")
		page.route = "empty-includes-test"
		page.page_title = "Empty includes"
		page.blocks = json.dumps([box(box(text("p", "Hours"), include(HOURS)), text("p", "Write to us"))])
		context = frappe._dict(favicon=None)
		with patch("builder.empty_includes.opening_hours_configured", return_value=False):
			page.get_context(context)
		self.assertIn("Write to us", context["__content"])
		self.assertNotIn("Hours", context["__content"])


class TestMapTemplate(unittest.TestCase):
	"""google_map.html, rendered alone: an instance whose cached hooks predate site_map_address
	must draw no map rather than fail the page (a contact page answered 417, 2026-09-13)."""

	def render(self, **context):
		from jinja2 import DebugUndefined
		from jinja2.sandbox import SandboxedEnvironment

		import builder

		path = os.path.join(os.path.dirname(builder.__file__), "templates", "includes", "google_map.html")
		with open(path) as template:
			source = template.read()
		env = SandboxedEnvironment(undefined=DebugUndefined)
		env.globals["_"] = lambda words: words
		return env.from_string(source).render(**context)

	def test_without_the_method_no_map_and_no_error(self):
		self.assertNotIn("<iframe", self.render())

	def test_the_method_gives_the_address(self):
		self.assertIn("q=Main%20Street%201", self.render(site_map_address=lambda: "Main Street 1"))

	def test_an_address_passed_wins(self):
		self.assertIn(
			"q=Elm%20Road", self.render(address="Elm Road", site_map_address=lambda: "Main Street 1")
		)
