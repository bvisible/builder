# //// Neoffice — added file (no upstream equivalent): the forms of the website kept as data, in the Builder
# //// (2026-10-20, plan of neoffice-maintenance#1593).
"""A form is a record of the theme (`Site Form`); the Builder draws it, lists it, creates and changes it.

What is held here:
  * without the theme (Unpress, a theme that predates the forms) nothing breaks: the include draws the plain
    contact form, the editor is told {"available": false}, the catalogue does not offer the include;
  * with it, the include draws the record at every display: the questions in their types, the steps, the window,
    the hints, the required marks, everything escaped, and never a recipient or a delivery setting;
  * a name that was renamed or switched off falls back on the contact form of the site, never on nothing;
  * the option of the include that names the form offers the forms that exist, and the editor's tag is refused for
    one that does not;
  * the four endpoints of the editor are behind the Builder role, and the theme checks the right on the doctype.

The tests that need the theme skip where it is not installed (the Builder's own CI site)."""

import pathlib
import re
import unittest
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import api, site_forms
from builder.site_ai import components
from builder.tests.test_security_guards import _make_website_user

INCLUDE = "builder/templates/includes/site_form.html"
APP = pathlib.Path(__file__).resolve().parent.parent
PLAIN_FORM = APP / "templates/includes/contact_form.html"
STYLE = APP / "templates/includes/contact_form_style.html"


def render(**params):
	"""The page's own way of giving a component its parameters: {%- set -%} before the include."""
	sets = "".join(f'{{%- set {name} = "{value}" -%}}' for name, value in params.items())
	return frappe.render_template(sets + f'{{% include "{INCLUDE}" %}}', {})


def named(html, name):
	return re.findall(rf'<(?:input|textarea)\b[^>]*\bname="{name}"[^>]*>', html)


def steps(html):
	return re.findall(r'data-step="(\d)"', html)


def forget_capability():
	frappe.local.builder_site_forms_available = None


class TestWithoutTheTheme(FrappeTestCase):
	def setUp(self):
		super().setUp()
		patcher = patch.object(site_forms, "theme_module", return_value=None)
		patcher.start()
		self.addCleanup(patcher.stop)
		forget_capability()
		self.addCleanup(forget_capability)

	def test_there_is_no_definition(self):
		self.assertFalse(site_forms.available())
		self.assertIsNone(site_forms.site_form_definition("anything"))
		self.assertEqual(site_forms.form_choices(), [])

	def test_the_include_draws_the_plain_contact_form(self):
		html = render(site_form="anything")
		self.assertNotIn("data-neo-form", html)
		self.assertEqual(len(named(html, "sender")), 1)
		self.assertIn("data-neo-contact", html)

	def test_the_editor_is_told_the_site_keeps_no_forms(self):
		frappe.set_user("Administrator")
		self.assertEqual(api.get_site_forms(), {"available": False})

	def test_a_write_is_refused_with_a_sentence_not_a_crash(self):
		with self.assertRaises(frappe.ValidationError):
			site_forms.create_form("steps")
		with self.assertRaises(frappe.ValidationError):
			site_forms.save_form("x", {})


class TestTheCatalogue(unittest.TestCase):
	def test_the_include_is_offered_only_where_the_theme_is_installed(self):
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder"]):
			self.assertNotIn(INCLUDE, [c.path for c in components.catalogue()])
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder", "neoffice_theme"]):
			self.assertIn(INCLUDE, [c.path for c in components.catalogue()])

	def test_the_option_that_names_the_form_lists_rows_not_constants(self):
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder", "neoffice_theme"]):
			component = next(c for c in components.catalogue() if c.path == INCLUDE)
		param = component.params[0]
		self.assertEqual(param["name"], "site_form")
		self.assertEqual(param["choices_from"], "builder.site_forms.form_choices")
		listed = [{"value": "contact", "label": "Contact"}]
		with patch("builder.site_forms.form_choices", return_value=listed):
			self.assertEqual(components.choices_of(param), listed)
			# an example in the registry never names a form of one site
			self.assertEqual(components.example_tag(component), component.tag())
			row = components.registry_row(component)
			self.assertNotIn('"choices"', row["parameters"])

	def test_a_form_that_does_not_exist_is_refused(self):
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder", "neoffice_theme"]):
			component = next(c for c in components.catalogue() if c.path == INCLUDE)
		with patch(
			"builder.site_forms.form_choices", return_value=[{"value": "contact", "label": "Contact"}]
		):
			self.assertEqual(component.checked_values({"site_form": "contact"}), {"site_form": "contact"})
			with self.assertRaises(ValueError):
				component.checked_values({"site_form": "no-such-form"})
			# left empty: the contact form of the site
			self.assertEqual(component.checked_values({"site_form": ""}), {})


class TestTheStylesheet(unittest.TestCase):
	def test_the_forms_wear_the_same_rules_as_the_plain_contact_form(self):
		"""site_form.html draws a copy of the <style> of contact_form.html. Two copies drift: this holds them equal
		while both exist."""
		plain = re.search(r"<style>\n.*?\n</style>\n", PLAIN_FORM.read_text(), re.S).group(0)
		self.assertIn(plain, STYLE.read_text())

	def test_a_page_with_a_form_kept_as_data_loads_the_runtime(self):
		source = (APP / "builder/doctype/builder_page/builder_page.py").read_text()
		self.assertIn('"site_form.html" in content', source)


class TestWithTheTheme(FrappeTestCase):
	def setUp(self):
		super().setUp()
		forget_capability()
		if not site_forms.available():
			self.skipTest("the theme that keeps forms is not installed here")
		frappe.set_user("Administrator")
		self.module = site_forms.theme_module()
		self.created = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in getattr(self, "created", []):
			if frappe.db.exists("Site Form", name):
				frappe.delete_doc("Site Form", name, force=True, ignore_permissions=True)
		forget_capability()
		super().tearDown()

	def make(self, preset="questions", **changes):
		made = self.module.create_form(title="Test form " + uuid.uuid4().hex[:8], preset=preset, lang="en")
		self.created.append(made["name"])
		if changes:
			made = self.module.save_form(made["name"], changes)
		return made

	# -- what the page draws ---------------------------------------------------------------------
	def test_a_form_is_drawn_from_its_record(self):
		made = self.make("questions")
		html = render(site_form=made["name"])
		self.assertIn(f'data-neo-form="{made["name"]}"', html)
		self.assertEqual(steps(html), ["1", "2"])
		for name in ("full_name", "sender", "phone", "request_type", "budget", "start_when", "message"):
			self.assertTrue(named(html, name), name)
		self.assertLess(html.index('name="request_type"'), html.index('name="message"'))
		# every option names the question it answers, or the owner reads "A quote: A quote"
		self.assertEqual(
			len(re.findall(r'name="request_type"[^>]*data-label="What is your request about\?"', html)), 4
		)
		self.assertRegex(named(html, "message")[0], r"\brequired\b")
		self.assertNotRegex(named(html, "phone")[0], r"\brequired\b")
		self.assertIn('autocomplete="email"', named(html, "sender")[0])
		# the name and the e-mail stand side by side
		self.assertIn('class="form-row"', html)

	def test_a_simple_form_has_no_steps(self):
		html = render(site_form=self.make("simple")["name"])
		self.assertEqual(steps(html), [])
		self.assertNotIn("data-progress", html)
		self.assertNotIn("data-step-next", html)
		self.assertEqual(len(named(html, "sender")), 1)

	def test_a_question_that_was_added_is_drawn_in_its_type(self):
		made = self.make("simple")
		extra = [
			{
				"label": "Colour",
				"type": "Single choice",
				"options": "red\nblue",
				"required": 1,
				"help": "Pick one",
			},
			{"label": "Days", "type": "Checkboxes", "options": "Mon\nTue"},
			{"label": "Preferred date", "type": "Date"},
			{"label": "I agree to be contacted.", "type": "Consent", "required": 1},
		]
		self.module.save_form(made["name"], {"fields": made["fields"] + extra})
		html = render(site_form=made["name"])
		self.assertEqual(len(re.findall(r'type="radio" name="colour"', html)), 2)
		self.assertEqual(len(re.findall(r'type="checkbox" name="days"', html)), 2)
		self.assertIn('type="date"', html)
		self.assertRegex(
			html, r'type="checkbox" id="[^"]+" name="i_agree_to_be_contacted" value="1" required'
		)
		self.assertIn("Pick one", html)

	def test_what_the_owner_types_is_escaped(self):
		made = self.make("simple")
		self.module.save_form(
			made["name"],
			{"fields": made["fields"] + [{"label": "Tom & Jerry", "type": "Text", "help": 'Say "hi"'}]},
		)
		# the framework strips tags from a field it saves; a record written around it (an import, a script) is
		# not stripped, and the page must not trust it
		row = frappe.get_all(
			"Site Form Field", filters={"parent": made["name"], "label": "Tom & Jerry"}, pluck="name"
		)[0]
		frappe.db.set_value("Site Form Field", row, "label", '<img src=x onerror="alert(1)">')
		frappe.db.set_value("Site Form Field", row, "help", '"><script>alert(2)</script>')
		html = render(site_form=made["name"])
		self.assertNotIn("<img src=x", html)
		self.assertNotIn("<script>alert(2)", html)
		self.assertIn("&lt;img", html)
		self.assertNotIn('"><script', html)

	def test_a_form_in_a_window_draws_its_button_and_its_dialog(self):
		html = render(site_form=self.make("simple", dialog=1, button_text="Write to us")["name"])
		self.assertIn("builder-contact-form--dialog", html)
		self.assertIn("<dialog", html)
		self.assertRegex(html, r"data-contact-open>Write to us</button>")

	def test_a_window_with_no_button_text_draws_no_button(self):
		html = render(site_form=self.make("simple", dialog=1, button_text="")["name"])
		self.assertIn("<dialog", html)
		self.assertNotIn("data-contact-open", html)

	def test_the_message_once_sent_and_the_send_button_are_the_forms(self):
		made = self.make("simple", success_message="We call you back.", submit_text="Send it")
		html = render(site_form=made["name"])
		self.assertIn('data-sent="We call you back."', html)
		self.assertIn(">Send it</button>", html)

	def test_the_page_never_carries_the_delivery(self):
		made = self.make("simple", recipients="boss@private.example", visitor_copy="None")
		html = render(site_form=made["name"])
		self.assertNotIn("boss@private.example", html)
		self.assertNotIn("Acknowledgement", html)

	# -- when the name is not a form -------------------------------------------------------------
	def test_a_name_that_is_not_a_form_falls_back_on_the_contact_form_of_the_site(self):
		contact = self.make("steps")
		html = render(site_form="no-such-form")
		self.assertTrue(named(html, "sender"), "the page lost its form")
		self.assertTrue(contact["name"])

	def test_a_switched_off_form_is_not_drawn_but_the_page_keeps_a_form(self):
		made = self.make("simple", enabled=0)
		html = render(site_form=made["name"])
		self.assertNotIn(f'data-neo-form="{made["name"]}"', html)
		self.assertTrue(named(html, "sender"))

	def test_a_page_that_names_no_form_draws_the_contact_form(self):
		self.make("steps")
		html = frappe.render_template(f'{{% include "{INCLUDE}" %}}', {})
		self.assertTrue(named(html, "sender"))

	# -- the option of the include ---------------------------------------------------------------
	def test_the_option_offers_the_forms_that_exist(self):
		made = self.make("simple")
		self.assertIn(made["name"], [c["value"] for c in site_forms.form_choices()])
		made_off = self.make("simple", enabled=0)
		self.assertNotIn(made_off["name"], [c["value"] for c in site_forms.form_choices()])

	def test_the_editor_writes_a_tag_for_a_form_that_exists_only(self):
		made = self.make("simple")
		tag = api.render_component_tag(INCLUDE, {"site_form": made["name"]})
		self.assertEqual(tag, f'{{%- set site_form = "{made["name"]}" -%}}{{% include "{INCLUDE}" %}}')
		self.assertEqual(api.read_component_tag(tag)["values"], {"site_form": made["name"]})
		with self.assertRaises(frappe.ValidationError):
			api.render_component_tag(INCLUDE, {"site_form": "no-such-form"})

	# -- the endpoints of the editor -------------------------------------------------------------
	def test_the_editor_lists_forms_presets_and_limits(self):
		made = self.make("simple")
		state = api.get_site_forms()
		self.assertTrue(state["available"])
		self.assertIn(made["name"], [form["name"] for form in state["forms"]])
		self.assertEqual([p["key"] for p in state["presets"]], ["simple", "steps", "questions"])
		self.assertEqual(state["limits"]["fields"], self.module.MAX_FIELDS)

	def test_a_form_is_created_read_and_changed_through_the_editor(self):
		made = api.create_site_form("questions", "Quote " + uuid.uuid4().hex[:6])
		self.created.append(made["name"])
		again = api.get_site_form(made["name"])
		self.assertEqual(again["name"], made["name"])
		fields = [dict(f, label="Budget?") if f["fieldname"] == "budget" else f for f in again["fields"]]
		saved = api.save_site_form(made["name"], {"fields": fields, "success_message": "Thanks!"})
		self.assertEqual(saved["success_message"], "Thanks!")
		self.assertEqual([f["label"] for f in saved["fields"] if f["fieldname"] == "budget"], ["Budget?"])

	def test_a_form_the_theme_refuses_comes_back_as_a_sentence(self):
		made = self.make("simple")
		no_email = [f for f in made["fields"] if f["role"] != "Email"]
		with self.assertRaises(frappe.ValidationError):
			api.save_site_form(made["name"], {"fields": no_email})
		with self.assertRaises(frappe.ValidationError):
			api.save_site_form(made["name"], "not json")

	def test_anonymous_is_refused_everywhere(self):
		made = self.make("simple")
		frappe.set_user("Guest")
		for call in (
			lambda: api.get_site_forms(),
			lambda: api.get_site_form(made["name"]),
			lambda: api.create_site_form("simple"),
			lambda: api.save_site_form(made["name"], {"title": "x"}),
		):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_a_portal_user_is_refused_everywhere(self):
		made = self.make("simple")
		frappe.set_user(_make_website_user())
		for call in (
			lambda: api.get_site_forms(),
			lambda: api.get_site_form(made["name"]),
			lambda: api.create_site_form("simple"),
			lambda: api.save_site_form(made["name"], {"title": "x"}),
		):
			with self.assertRaises(frappe.PermissionError):
				call()


class TestTheFormsTheGeneratorWrites(FrappeTestCase):
	"""The site generator writes the contact form with its options; where the site keeps forms the build makes a Site
	Form of the website out of them and the page draws that."""

	def setUp(self):
		super().setUp()
		forget_capability()
		if not site_forms.available():
			self.skipTest("the theme that keeps forms is not installed here")
		frappe.set_user("Administrator")
		self.module = site_forms.theme_module()
		self.before = set(frappe.get_all("Site Form", pluck="name"))

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in set(frappe.get_all("Site Form", pluck="name")) - self.before:
			frappe.delete_doc("Site Form", name, force=True, ignore_permissions=True)
		forget_capability()
		super().tearDown()

	@staticmethod
	def page(*tags):
		"""A page as the generator writes it: sections whose children carry the includes."""
		return [{"element": "div", "children": [{"element": "div", "innerHTML": tag} for tag in tags]}]

	CONTACT = '{% include "builder/templates/includes/contact_form.html" %}'

	@staticmethod
	def contact(**options):
		sets = "".join(
			f"{{%- set {key} = {str(value).lower() if isinstance(value, bool) else json_string(value)} -%}}"
			for key, value in options.items()
		)
		return sets + '{% include "builder/templates/includes/contact_form.html" %}'

	def html(self, blocks):
		return blocks[0]["children"][0]["innerHTML"]

	def made(self):
		return set(frappe.get_all("Site Form", pluck="name")) - self.before

	@staticmethod
	def form_of(blocks):
		"""The form a page ended up drawing, from its tag."""
		return components.parse_tag(blocks[0]["children"][0]["innerHTML"])[1]["site_form"]

	def test_the_plain_include_becomes_the_steps_form_of_the_website(self):
		blocks = self.page(self.CONTACT)
		self.assertEqual(site_forms.adopt_contact_forms(blocks), 1)
		name = self.form_of(blocks)
		self.assertEqual(self.html(blocks), site_forms.form_tag(name))
		form = self.module.get_form(name)
		self.assertEqual(len(form["steps"]), 2)
		self.assertEqual(
			[f["role"] for f in form["fields"] if f["role"]], ["Name", "Email", "Phone", "Message"]
		)

	def test_the_model_the_generator_chose_is_the_preset_the_form_starts_from(self):
		blocks = self.page(self.contact(contact_model="questions"))
		site_forms.adopt_contact_forms(blocks)
		identifiers = [f["fieldname"] for f in self.module.get_form(self.form_of(blocks))["fields"]]
		for wanted in ("request_type", "budget", "start_when"):
			self.assertIn(wanted, identifiers)
		blocks = self.page(self.contact(contact_model="simple"))
		site_forms.adopt_contact_forms(blocks)
		self.assertEqual(self.module.get_form(self.form_of(blocks))["steps"], [])

	def test_the_window_the_consent_and_the_phone_come_with_it(self):
		blocks = self.page(
			self.contact(
				contact_model="simple",
				contact_dialog=True,
				contact_button_text="Request a quote",
				consent_text="I agree to be contacted.",
				phone_required=True,
			)
		)
		site_forms.adopt_contact_forms(blocks)
		form = self.module.get_form(self.form_of(blocks))
		self.assertEqual((form["dialog"], form["button_text"]), (1, "Request a quote"))
		consent = [f for f in form["fields"] if f["type"] == "Consent"]
		self.assertEqual([(c["label"], c["required"]) for c in consent], [("I agree to be contacted.", 1)])
		phone = [f for f in form["fields"] if f["role"] == "Phone"]
		self.assertEqual([p["required"] for p in phone], [1])

	def test_the_pages_of_one_build_that_ask_the_same_things_share_one_form(self):
		made = {}
		first, second = self.page(self.CONTACT), self.page(self.CONTACT)
		site_forms.adopt_contact_forms(first, made=made)
		site_forms.adopt_contact_forms(second, made=made)
		self.assertLessEqual(len(self.made()), 1)
		self.assertEqual(self.html(first), self.html(second))

	def test_a_rebuild_adds_no_form(self):
		first, second = self.page(self.CONTACT), self.page(self.CONTACT)
		site_forms.adopt_contact_forms(first)
		after_the_first = self.made()
		site_forms.adopt_contact_forms(second)
		self.assertEqual(self.made(), after_the_first)
		self.assertEqual(self.html(first), self.html(second))

	def test_another_set_of_questions_is_another_form(self):
		steps, quote = self.page(self.CONTACT), self.page(self.contact(contact_model="questions"))
		site_forms.adopt_contact_forms(steps)
		site_forms.adopt_contact_forms(quote)
		self.assertNotEqual(self.form_of(steps), self.form_of(quote))

	def test_the_form_of_a_website_is_that_websites(self):
		profile = frappe.db.get_value("Website Profile", {}, "name")
		if not profile:
			self.skipTest("this site has no Website Profile")
		blocks = self.page(self.contact(contact_model="questions"))
		site_forms.adopt_contact_forms(blocks, profile)
		self.assertEqual(self.module.get_form(self.form_of(blocks))["profile"], profile)

	def test_a_tag_written_by_hand_is_left_alone(self):
		by_hand = '{% include "builder/templates/includes/contact_form.html" %}{{ frappe.session.user }}'
		blocks = self.page(by_hand, "<p>no form here</p>")
		self.assertEqual(site_forms.adopt_contact_forms(blocks), 0)
		self.assertEqual(blocks[0]["children"][0]["innerHTML"], by_hand)
		self.assertEqual(self.made(), set())

	def test_without_the_theme_nothing_changes(self):
		blocks = self.page(self.CONTACT)
		with patch.object(site_forms, "theme_module", return_value=None):
			forget_capability()
			self.assertEqual(site_forms.adopt_contact_forms(blocks), 0)
		self.assertEqual(self.html(blocks), self.CONTACT)

	def test_a_failure_leaves_the_page_with_its_plain_form(self):
		blocks = self.page(self.CONTACT)
		with patch.object(self.module, "create_form", side_effect=RuntimeError("no")):
			self.assertEqual(site_forms.adopt_contact_forms(blocks), 0)
		self.assertEqual(self.html(blocks), self.CONTACT)

	def test_the_tag_written_is_one_the_editor_and_the_assistant_read(self):
		blocks = self.page(self.CONTACT)
		site_forms.adopt_contact_forms(blocks)
		tag = self.html(blocks)
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder", "neoffice_theme"]):
			self.assertEqual(components.lawful_tag(tag), tag)
			self.assertEqual(components.parse_tag(tag)[1], {"site_form": self.form_of(blocks)})

	def test_the_generator_is_not_offered_the_include_that_would_duplicate_its_form(self):
		from builder.site_ai.nora.site_builder import available_includes

		offered = [c.file for c in available_includes("contact", generator=True)]
		self.assertIn("contact_form.html", offered)
		self.assertNotIn("site_form.html", offered)
		# the assistant and the editor still see it
		self.assertIn("site_form.html", [c.file for c in available_includes("contact")])

	def test_the_buttons_of_a_page_find_the_form_of_either_include(self):
		from builder.site_ai.nora.buttons import retarget_self_links

		blocks = self.page(self.CONTACT)
		site_forms.adopt_contact_forms(blocks)
		link = {
			"element": "a",
			"classes": ["u-btn"],
			"attributes": {"href": "/contact"},
			"innerText": "Contact us",
		}
		blocks[0]["children"].append(link)
		edits = retarget_self_links(blocks, "contact", "/contact")
		self.assertTrue(edits, "the call to action should lead to the form of its own page")
		self.assertEqual(link["attributes"]["href"], "#contact-form")


def json_string(value):
	import json

	return json.dumps(str(value))
