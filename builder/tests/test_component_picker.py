# //// Neoffice — added file (no upstream equivalent): the editor's component picker, the human half of what
# //// the assistant learned on 2026-10-19 (test_component_tags.py).
"""A person picks a component of the catalogue in the editor, sets its options in a small form, and the editor
places (or updates) the div whose text is the canonical include tag.

What is held here:
  * the options a person types are checked against what the component DECLARES (a choice that is not on offer,
    a number out of range, a character that would end the Jinja statement are refused with a sentence), and the
    tag built from them comes back unchanged from `lawful_tag`, the one gate the assistant's block tools use;
  * a block's text is read back into its options through the same reading `lawful_tag` is built on, so the
    picker can change a block the generator or the assistant placed;
  * the catalogue is offered by page: the components suited to the open page first, nothing recommended on a
    route the generator does not know;
  * the three entry points are behind the Builder role: anonymous, portal user and administrator."""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import api
from builder.site_ai import components
from builder.tests.test_security_guards import _make_website_user

FORM = "builder/templates/includes/contact_form.html"
MAP = "builder/templates/includes/google_map.html"
BLOG = "builder/templates/includes/blog_listing.html"


def form():
	return components.by_file("contact_form.html")


class TestDeclarations(unittest.TestCase):
	"""What the catalogue declares for the form must be coherent, or the picker offers a default it refuses."""

	def test_a_default_is_one_of_the_choices(self):
		for component in components.catalogue():
			for param in component.params:
				offered = [c["value"] for c in components.choices_of(param)]
				if offered and param.get("default") not in (None, ""):
					self.assertIn(str(param["default"]), offered, f"{component.path} {param['name']}")

	def test_a_default_is_within_its_bounds(self):
		for component in components.catalogue():
			for param in component.params:
				if param.get("type") != "int":
					continue
				low, high = param.get("min"), param.get("max")
				if low is not None:
					self.assertGreaterEqual(param["default"], low, f"{component.path} {param['name']}")
				if high is not None:
					self.assertLessEqual(param["default"], high, f"{component.path} {param['name']}")

	def test_the_contact_form_offers_its_three_forms_and_its_window(self):
		by_name = {p["name"]: p for p in form().params}
		self.assertEqual(
			[c["value"] for c in components.choices_of(by_name["contact_model"])],
			["simple", "steps", "questions"],
		)
		self.assertEqual(by_name["contact_dialog"]["type"], "bool")
		# an empty button text is a choice (no button, the page has its own link), not silence
		self.assertTrue(by_name["contact_button_text"].get("blank"))

	def test_every_parameter_has_a_readable_label(self):
		for component in components.catalogue():
			for param in component.params:
				label = components.param_label(param)
				self.assertTrue(label and "_" not in label, f"{component.path} {param['name']}: {label}")

	def test_the_help_a_person_reads_is_not_the_generators_note(self):
		self.assertTrue(form().help)
		self.assertNotEqual(form().help, form().note)
		self.assertNotIn("<form>", form().help)


class TestCheckedValues(unittest.TestCase):
	def test_what_is_declared_is_kept(self):
		kept = form().checked_values(
			{"contact_model": "questions", "contact_dialog": True, "consent_text": " I agree "}
		)
		self.assertEqual(
			kept, {"contact_model": "questions", "contact_dialog": True, "consent_text": "I agree"}
		)

	def test_what_is_not_declared_is_dropped(self):
		self.assertEqual(
			form().checked_values({"nothing_like_it": "x", "contact_model": "simple"}),
			{"contact_model": "simple"},
		)

	def test_an_empty_text_is_silence_unless_the_parameter_says_otherwise(self):
		self.assertEqual(form().checked_values({"consent_text": "", "contact_model": ""}), {})
		self.assertEqual(form().checked_values({"contact_button_text": ""}), {"contact_button_text": ""})

	def test_a_choice_that_is_not_offered_is_refused(self):
		with self.assertRaises(ValueError):
			form().checked_values({"contact_model": "wizard"})

	def test_a_boolean_must_be_a_boolean(self):
		for bad in ("true", 1, "yes"):
			with self.assertRaises(ValueError, msg=repr(bad)):
				form().checked_values({"phone_required": bad})

	def test_a_number_is_read_and_held_to_its_bounds(self):
		map_ = components.by_file("google_map.html")
		self.assertEqual(map_.checked_values({"zoom": "12"}), {"zoom": 12})
		self.assertEqual(map_.checked_values({"zoom": 12.0}), {"zoom": 12})
		self.assertEqual(map_.checked_values({"zoom": ""}), {})
		for bad in (0, 21, 12.5, "twelve", True):
			with self.assertRaises(ValueError, msg=repr(bad)):
				map_.checked_values({"zoom": bad})

	def test_a_character_that_would_end_the_statement_is_refused(self):
		for bad in ("100% yes", "a {{ b }}", "ends with a backslash\\", "two\nlines", "%}"):
			with self.assertRaises(ValueError, msg=repr(bad)):
				form().checked_values({"consent_text": bad})

	def test_a_text_that_is_too_long_is_refused(self):
		with self.assertRaises(ValueError):
			form().checked_values({"consent_text": "x" * (components.MAX_TEXT + 1)})


class TestRenderComponentTag(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_the_tag_is_the_one_lawful_tag_returns(self):
		tag = api.render_component_tag(
			FORM, {"contact_model": "questions", "contact_dialog": True, "consent_text": "I agree"}
		)
		self.assertEqual(components.lawful_tag(tag), tag)
		parsed = components.parse_tag(tag)
		self.assertEqual(
			parsed[1], {"contact_model": "questions", "contact_dialog": True, "consent_text": "I agree"}
		)

	def test_the_options_may_arrive_as_a_json_string(self):
		self.assertEqual(
			api.render_component_tag(FORM, '{"contact_model": "simple"}'),
			form().tag({"contact_model": "simple"}),
		)

	def test_no_option_is_the_bare_include(self):
		self.assertEqual(api.render_component_tag(FORM, None), form().tag())

	def test_a_refused_option_throws_with_its_sentence(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			api.render_component_tag(FORM, {"consent_text": "100%"})
		# the characters are named whatever the language of the site, so the person knows what to remove
		self.assertIn(components.UNSAFE_TEXT_SHOWN, str(caught.exception))

	def test_an_option_that_would_break_the_page_never_becomes_a_tag(self):
		for payload in (
			{"consent_text": 'x" -%}{{ frappe.conf }}{%- set y = "'},
			{"consent_text": "back\\"},
			{"contact_model": 'x" -%}{% include "other.html" %}'},
		):
			with self.assertRaises(frappe.ValidationError, msg=str(payload)):
				api.render_component_tag(FORM, payload)

	def test_an_unknown_component_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			api.render_component_tag("builder/templates/includes/not_catalogued.html", {})

	def test_options_that_are_not_an_object_are_refused(self):
		for payload in ("not json", "[1, 2]", "3"):
			with self.assertRaises(frappe.ValidationError, msg=payload):
				api.render_component_tag(FORM, payload)


class TestReadComponentTag(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_a_tag_the_generator_wrote_is_read_back(self):
		# the shape a generated page carries: a newline between the statement and the include, Python's True
		written = f'{{%- set contact_model = "simple" -%}}\n{{%- set phone_required = True -%}}\n{{% include "{FORM}" %}}'
		read = api.read_component_tag(written)
		self.assertEqual(read["path"], FORM)
		self.assertEqual(read["values"], {"contact_model": "simple", "phone_required": True})

	def test_a_tag_written_by_hand_is_named_but_not_read(self):
		for written in (
			f'{{%- set contact_model = frappe.db.sql("x") -%}}{{% include "{FORM}" %}}',
			f'{{%- set not_a_parameter = 1 -%}}{{% include "{FORM}" %}}',
			f'{{% if x %}}{{% include "{FORM}" %}}{{% endif %}}',
		):
			read = api.read_component_tag(written)
			self.assertEqual(read["path"], FORM, written)
			self.assertIsNone(read["values"], written)

	def test_any_other_text_is_not_a_component(self):
		for text in (
			None,
			"",
			"plain text",
			"{{ 1 + 1 }}",
			'{% include "builder/templates/includes/not_catalogued.html" %}',
		):
			self.assertIsNone(api.read_component_tag(text), repr(text))

	def test_what_is_read_can_be_written_back_unchanged(self):
		original = form().tag({"contact_model": "questions", "contact_button_text": ""})
		read = api.read_component_tag(original)
		self.assertEqual(api.render_component_tag(read["path"], read["values"]), original)


class TestComponentsOfAPage(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def page(self, route):
		"""An unpublished page on that route (it never answers a visitor, and the test rolls it back)."""
		return (
			frappe.get_doc(
				{
					"doctype": "Builder Page",
					"page_title": f"Picker {route}",
					"route": route,
					"published": 0,
					"blocks": "[]",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_the_contact_page_gets_the_contact_form_first(self):
		listing = api.get_site_components(page=self.page("contact"))
		suited = [c for c in listing if c["suited"]]
		self.assertIn(FORM, [c["path"] for c in suited])
		for component in suited:
			self.assertIn("contact", component["pages"])
		# the suited ones come first, the others after them, none dropped
		flags = [bool(c["suited"]) for c in listing]
		self.assertEqual(flags, sorted(flags, reverse=True))
		self.assertEqual(len(listing), len(components.catalogue()))

	def test_a_route_the_generator_does_not_know_recommends_nothing(self):
		listing = api.get_site_components(page=self.page("a-route-nobody-planned"))
		self.assertTrue(listing)
		self.assertTrue(all(c["suited"] is None for c in listing))

	def test_a_page_that_does_not_exist_recommends_nothing(self):
		self.assertTrue(all(c["suited"] is None for c in api.get_site_components(page="no-such-page")))

	def test_without_a_page_nothing_is_recommended_either(self):
		self.assertTrue(all(c["suited"] is None for c in api.get_site_components()))

	def test_the_home_route_is_the_home_page_type(self):
		self.assertEqual(components.page_type_for_route("home"), "accueil")
		self.assertEqual(components.page_type_for_route("/contact/"), "contact")
		self.assertIsNone(components.page_type_for_route("a-route-nobody-planned"))
		self.assertIsNone(components.page_type_for_route(None))

	def test_a_component_with_nothing_to_show_is_not_suited_but_is_still_listed(self):
		page = self.page("contact")
		with patch.object(components, "has_data", return_value=False):
			listing = api.get_site_components(page=page)
		self.assertTrue(listing)
		self.assertFalse(any(c["suited"] for c in listing))
		self.assertTrue(all(c["has_data"] is False for c in listing))

	def test_a_parameter_reaches_the_panel_with_its_label_and_its_choices(self):
		listed = {c["path"]: c for c in api.get_site_components()}[FORM]
		params = {p["name"]: p for p in listed["params"]}
		self.assertTrue(params["contact_model"]["label"])
		self.assertNotEqual(params["contact_model"]["label"], "contact_model")
		self.assertEqual(
			[c["value"] for c in params["contact_model"]["choices"]], ["simple", "steps", "questions"]
		)
		self.assertTrue(all(c["label"] for c in params["contact_model"]["choices"]))
		self.assertNotIn("choices", params["phone_required"])


class TestWhoMayUseIt(FrappeTestCase):
	"""The editor is behind a role: anonymous and portal user are refused, on all three entry points."""

	CALLS = (
		lambda: api.get_site_components(),
		lambda: api.render_component_tag(FORM, {}),
		lambda: api.read_component_tag(f'{{% include "{FORM}" %}}'),
	)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_anonymous_is_refused(self):
		frappe.set_user("Guest")
		for call in self.CALLS:
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_a_portal_user_is_refused(self):
		frappe.set_user(_make_website_user())
		for call in self.CALLS:
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_the_administrator_is_served(self):
		frappe.set_user("Administrator")
		self.assertTrue(api.get_site_components())
		self.assertEqual(api.render_component_tag(FORM, {}), form().tag())
		self.assertEqual(api.read_component_tag(f'{{% include "{FORM}" %}}')["path"], FORM)
