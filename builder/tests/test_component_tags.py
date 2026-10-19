# //// Neoffice — added file (no upstream equivalent): the assistant places a catalogued component and changes its options.
"""The editor's assistant is told to place a component (the contact form, a carousel, the map) as a div whose
text is its include tag, and to change its options by rewriting that text. Its block tools refused every `{%`,
so asked to turn the contact form into a quote form it answered that its tools refuse Jinja (2026-10-19, the
contact form the colleague's work made three forms of).

A text that is NOTHING BUT a catalogued component's tag, with literal values for parameters the component
declares, now passes and is rewritten to its canonical form; any other Jinja is still refused, because Jinja
that is not a component's tag crashes the published route."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.ai.agent.tools.forms import (
	CONTACT_FORM_DECLINED,
	NO_FORM_ON_PAGE,
	looks_like_contact_form,
	request_connect_form,
)
from builder.ai.agent.tree import WorkingTree, moustache_fields
from builder.site_ai import components

FORM = "builder/templates/includes/contact_form.html"


def tag(*sets):
	return "".join(f"{{%- set {name} = {value} -%}}" for name, value in sets) + f'{{% include "{FORM}" %}}'


class TestLawfulTag(unittest.TestCase):
	def test_the_contact_form_is_catalogued_with_its_three_forms(self):
		form = components.by_file("contact_form.html")
		self.assertIsNotNone(form)
		names = {p["name"] for p in form.params}
		self.assertTrue(
			{"contact_model", "contact_dialog", "contact_button_text", "consent_text", "phone_required"}
			<= names
		)

	def test_a_tag_with_literal_options_is_rebuilt_canonically(self):
		written = f"{{%- set contact_model = 'questions' -%}}\n  {{%- set phone_required = true -%}} {{% include '{FORM}' %}}"
		self.assertEqual(
			components.lawful_tag(written),
			tag(("contact_model", '"questions"'), ("phone_required", "true")),
		)

	def test_a_capitalised_boolean_is_the_same_literal(self):
		# the generator wrote `True` in a page's tag; the tag the assistant reads back must stay lawful
		written = f'{{%- set phone_required = True -%}}{{% include "{FORM}" %}}'
		self.assertEqual(components.lawful_tag(written), tag(("phone_required", "true")))

	def test_the_bare_include_is_lawful(self):
		self.assertEqual(components.lawful_tag(f"{{% include '{FORM}' %}}"), tag())

	def test_numbers_and_booleans_are_literals(self):
		carousel = components.by_file("product_carousel.html")
		if carousel is None:
			self.skipTest("webshop is not installed here")
		written = f'{{%- set carousel_limit = 12 -%}}{{%- set show_discounted_only = false -%}}{{% include "{carousel.path}" %}}'
		self.assertEqual(
			components.lawful_tag(written),
			carousel.tag({"carousel_limit": 12, "show_discounted_only": False}),
		)

	def test_anything_but_a_component_tag_is_not_lawful(self):
		for text in (
			"{{ frappe.db.get_value('User', 'Administrator', 'email') }}",
			f'{{%- set contact_model = frappe.db.sql("x") -%}}{{% include "{FORM}" %}}',  # an expression, not a literal
			f'{{%- set contact_model = "a{{{{b}}}}" -%}}{{% include "{FORM}" %}}',  # Jinja inside the literal
			f'{{%- set not_a_parameter = "x" -%}}{{% include "{FORM}" %}}',  # a parameter it does not declare
			'{% include "builder/templates/includes/not_catalogued.html" %}',
			f'{{% include "{FORM}" %}}{{% include "{FORM}" %}}',  # a second statement
			f'hello {{% include "{FORM}" %}}',  # words around it
			f'{{% if x %}}{{% include "{FORM}" %}}{{% endif %}}',
			"plain text",
			"",
		):
			self.assertIsNone(components.lawful_tag(text), text)


class TestAssistantGuard(unittest.TestCase):
	def test_a_component_tag_passes_the_guard_and_is_rewritten(self):
		op = {
			"block_id": "form",
			"inner_text": f"{{%- set contact_model = 'questions' -%}}{{% include '{FORM}' %}}",
		}
		self.assertEqual(moustache_fields(op), [])
		self.assertEqual(op["inner_text"], tag(("contact_model", '"questions"')))

	def test_a_tag_with_its_quotes_and_line_breaks_escaped_twice_passes(self):
		# what kimi-k2.7-code wrote: the backslashes are in the text itself
		written = (
			r"{%- set contact_model = \"questions\" -%}\n{%- set phone_required = true -%}\n"
			r"{%- set consent_text = \"J accepte.\" -%}\n{% include \"" + FORM + r"\" %}"
		)
		self.assertIn("\\", written)
		op = {"block_id": "form", "inner_text": written}
		self.assertEqual(moustache_fields(op), [])
		self.assertEqual(
			op["inner_text"],
			tag(
				("contact_model", '"questions"'), ("phone_required", "true"), ("consent_text", '"J accepte."')
			),
		)

	def test_a_backslash_does_not_make_other_jinja_lawful(self):
		op = {"inner_text": r"{{ frappe.db.sql(\"x\") }}\n{% include \"" + FORM + r"\" %}"}
		self.assertTrue(moustache_fields(op))

	def test_other_jinja_is_still_refused(self):
		for op in (
			{"inner_text": "{{ item.title }}"},
			{"inner_html": "{% if x %}y{% endif %}"},
			{"inner_text": f'{{%- set contact_model = frappe.local.conf -%}}{{% include "{FORM}" %}}'},
			{"attributes": {"data-x": "{{ y }}"}},
			{"attributes": {"data-x": tag()}},  # a tag is text, never an attribute
		):
			self.assertTrue(moustache_fields(op), op)

	def test_a_block_payload_may_carry_the_tag_as_its_text(self):
		op = {"block": {"el": "div", "text": tag(("contact_dialog", "true"))}}
		self.assertEqual(moustache_fields(op), [])
		bad = {"block": {"el": "div", "c": [{"el": "p", "text": "{{ x }}"}]}}
		self.assertEqual(moustache_fields(bad), ["block"])
		in_style = {"block": {"el": "div", "style": {"backgroundImage": tag()}}}
		self.assertEqual(moustache_fields(in_style), ["block"])

	def test_the_assistant_places_the_form_then_changes_its_model(self):
		root = {
			"blockId": "root",
			"element": "div",
			"children": [{"blockId": "intro", "element": "p", "innerHTML": "Hello"}],
		}
		tree = WorkingTree(root)
		added = tree.apply("add_block", {"parent_block_id": "root", "block": {"el": "div", "text": tag()}})
		self.assertIn("Added block", added)
		placed = root["children"][-1]
		self.assertEqual(placed["innerHTML"], tag())
		changed = tree.apply(
			"update_block",
			{
				"block_id": placed["blockId"],
				"inner_text": f"{{%- set contact_model = 'questions' -%}}{{% include '{FORM}' %}}",
			},
		)
		self.assertIn("Applied to block", changed)
		self.assertEqual(placed["innerHTML"], tag(("contact_model", '"questions"')))

	def test_the_assistant_cannot_slip_other_jinja_in_beside_a_tag(self):
		root = {"blockId": "root", "element": "div", "children": []}
		tree = WorkingTree(root)
		refused = tree.apply(
			"add_block", {"parent_block_id": "root", "block": {"el": "div", "text": tag() + "{{ secret }}"}}
		)
		self.assertTrue(refused.startswith("FAILED"))
		self.assertEqual(root["children"], [])


class TestContactFormWithoutAModel(unittest.TestCase):
	def add(self, text):
		tree = WorkingTree({"blockId": "root", "element": "div", "children": []})
		return tree.apply("add_block", {"parent_block_id": "root", "block": {"el": "div", "text": text}})

	def test_the_bare_include_is_told_what_it_is(self):
		result = self.add(tag())
		self.assertTrue(result.startswith("Added block"))
		self.assertIn("'questions'", result)
		self.assertNotIn("FAILED", result)

	def test_a_form_in_a_wrapper_is_told_too(self):
		tree = WorkingTree({"blockId": "root", "element": "div", "children": []})
		wrapped = {"el": "section", "c": [{"el": "div", "c": [{"el": "div", "text": tag()}]}]}
		self.assertIn("'questions'", tree.apply("add_block", {"parent_block_id": "root", "block": wrapped}))

	def test_a_chosen_model_is_not(self):
		self.assertNotIn("NOTE", self.add(tag(("contact_model", '"questions"'))))
		self.assertNotIn("NOTE", self.add(tag(("contact_model", '"simple"'))))

	def test_another_block_is_not(self):
		self.assertNotIn("NOTE", self.add("Hello"))


class TestContactFormIsNotConnected(unittest.TestCase):
	def test_an_email_and_a_message_make_a_contact_form(self):
		fields = [
			{"fieldname": "name"},
			{"fieldname": "email", "label": "Your e-mail"},
			{"fieldname": "message"},
		]
		self.assertTrue(looks_like_contact_form(fields))
		self.assertTrue(
			looks_like_contact_form([{"fieldname": "courriel", "label": "E-mail"}, {"fieldname": "demande"}])
		)

	def test_a_booking_form_with_a_message_is_not_a_contact_form(self):
		# the local model's visit booking: it carries an e-mail AND a message, and was declined thirty-seven times
		booking = [
			{"fieldname": "nom", "label": "Nom"},
			{"fieldname": "email", "label": "E-mail"},
			{"fieldname": "date", "label": "Date souhait\u00e9e"},
			{"fieldname": "personnes", "label": "Nombre de personnes"},
			{"fieldname": "message", "label": "Message"},
		]
		self.assertFalse(looks_like_contact_form(booking))
		self.assertFalse(
			looks_like_contact_form(
				[{"fieldname": "email"}, {"fieldname": "guests"}, {"fieldname": "message"}]
			)
		)

	def test_a_quote_form_is_still_a_contact_form(self):
		# a "timeline" and a consent "checkbox" are not bookings
		quote = [
			{"fieldname": "email"},
			{"fieldname": "timeline", "label": "D\u00e9lai"},
			{"fieldname": "budget"},
			{"fieldname": "message"},
			{"fieldname": "consent_checkbox"},
		]
		self.assertTrue(looks_like_contact_form(quote))

	def test_other_forms_are_still_connected(self):
		self.assertFalse(
			looks_like_contact_form(
				[{"fieldname": "name"}, {"fieldname": "email"}, {"fieldname": "party_size"}]
			)
		)
		self.assertFalse(looks_like_contact_form([{"fieldname": "date"}, {"fieldname": "guests"}]))
		self.assertFalse(looks_like_contact_form([]))
		self.assertFalse(looks_like_contact_form(None))

	def test_the_tool_declines_a_contact_form_and_names_the_way(self):
		ctx = SimpleNamespace(page_id="page-x")
		args = {
			"doctype_name": "Contact Valrhone",
			"fields": [{"fieldname": "email"}, {"fieldname": "message"}],
			"form_selector": ".form",
		}
		self.assertEqual(request_connect_form(ctx, args), CONTACT_FORM_DECLINED)
		self.assertIn("get_site_chrome", CONTACT_FORM_DECLINED)


BOOKING_ARGS = {
	"doctype_name": "Visit Booking",
	"fields": [{"fieldname": "nom"}, {"fieldname": "date_souhaitee"}],
	"form_selector": ".booking",
}


class TestConnectFormNeedsAForm(unittest.TestCase):
	def ctx(self, root):
		return SimpleNamespace(page_id="page-x", page_root=lambda: root)

	def goes_on(self, ctx):
		# past the guard the tool reads the database; a connected form on the page ends it there, before any write
		with patch("builder.ai.agent.tools.forms.connected_submission_doctype", return_value="Some Doctype"):
			return request_connect_form(ctx, dict(BOOKING_ARGS)).startswith("ALREADY CONNECTED")

	def test_a_page_without_a_form_is_sent_back_to_draw_one(self):
		root = {"blockId": "root", "element": "div", "children": [{"blockId": "p", "element": "p"}]}
		self.assertEqual(request_connect_form(self.ctx(root), dict(BOOKING_ARGS)), NO_FORM_ON_PAGE)

	def test_a_page_with_an_input_goes_on(self):
		root = {
			"blockId": "root",
			"element": "div",
			"children": [
				{"blockId": "f", "element": "div", "children": [{"blockId": "i", "element": "input"}]}
			],
		}
		self.assertTrue(self.goes_on(self.ctx(root)))

	def test_a_component_instance_may_hold_the_form(self):
		root = {
			"blockId": "root",
			"element": "div",
			"children": [{"blockId": "c", "element": "div", "extendedFromComponent": "booking"}],
		}
		self.assertTrue(self.goes_on(self.ctx(root)))

	def test_a_tree_that_is_not_known_does_not_decline(self):
		self.assertTrue(self.goes_on(SimpleNamespace(page_id="page-x")))
		self.assertTrue(self.goes_on(self.ctx(None)))


if __name__ == "__main__":
	unittest.main()
