# //// Neoffice — added file (no upstream equivalent): the assistant's tools on the forms of the website
# //// (2026-10-20, plan of neoffice-maintenance#1593).
"""The assistant lists, creates and changes the forms of the site; the user applies each write on a card.

What is held here:
  * the tools exist only where the site keeps forms (the theme installed and migrated), and so do the rules that
    tell the model about them;
  * `list_site_forms` is a read: it shows the questions, never who is told;
  * `create_site_form` and `update_site_form` raise a confirm card and write NOTHING before it is applied; a
    proposal that cannot work (unknown form, nothing to change, too many questions) is declined with a sentence;
  * applying a card runs as the user: the theme checks their right, and the form is held to every rule at save;
  * `get_site_chrome` shows the names of the forms the include may be given."""

import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import site_forms
from builder.ai.agent import pending, registry
from builder.ai.agent.tools import site_forms as tools
from builder.site_ai import components
from builder.site_ai.nora import prompts
from builder.site_ai.nora.tools import _with_listed_choices

CTX = SimpleNamespace(page_id=None)


def forget_capability():
	frappe.local.builder_site_forms_available = None


class TestOnlyWhereTheSiteKeepsForms(FrappeTestCase):
	def tearDown(self):
		forget_capability()
		super().tearDown()

	def test_without_the_theme_the_model_is_offered_no_tool_and_no_rule(self):
		with patch.object(site_forms, "theme_module", return_value=None):
			forget_capability()
			self.assertFalse(site_forms.available())
			self.assertFalse(tools.NAMES & set(registry.build_default_registry().names()))
			self.assertEqual(prompts.site_forms_rules(), "")

	def test_with_the_theme_it_is_offered_all_three_and_the_rule(self):
		forget_capability()
		if not site_forms.available():
			self.skipTest("the theme that keeps forms is not installed here")
		self.assertTrue(tools.NAMES <= set(registry.build_default_registry().names()))
		rules = prompts.site_forms_rules()
		for name in tools.NAMES:
			self.assertIn(name, rules)

	def test_the_writers_end_the_turn_and_the_reader_does_not(self):
		sides = {tool.name: tool.side for tool in tools.TOOLS}
		self.assertEqual(
			sides,
			{"list_site_forms": "server", "create_site_form": "terminal", "update_site_form": "terminal"},
		)

	def test_the_reader_is_known_to_write_nothing(self):
		from builder.ai.agent import loop

		self.assertIn("list_site_forms", loop.READ_ONLY_SERVER_TOOLS)
		self.assertNotIn("create_site_form", loop.READ_ONLY_SERVER_TOOLS)
		self.assertNotIn("update_site_form", loop.READ_ONLY_SERVER_TOOLS)

	def test_every_card_kind_is_known_to_the_confirm_endpoint(self):
		self.assertIn("create_site_form", pending.KINDS)
		self.assertIn("update_site_form", pending.KINDS)


class TestTheTools(FrappeTestCase):
	def setUp(self):
		super().setUp()
		forget_capability()
		if not site_forms.available():
			self.skipTest("the theme that keeps forms is not installed here")
		frappe.set_user("Administrator")
		self.module = site_forms.theme_module()
		self.created = []
		self.cards = []
		patcher = patch.object(
			pending,
			"request_confirmation",
			side_effect=lambda ctx, kind, summary, payload: self.cards.append((kind, summary, payload)),
		)
		patcher.start()
		self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.created:
			if frappe.db.exists("Site Form", name):
				frappe.delete_doc("Site Form", name, force=True, ignore_permissions=True)
		forget_capability()
		super().tearDown()

	def make(self, preset="questions"):
		made = self.module.create_form(title="Test form " + uuid.uuid4().hex[:8], preset=preset, lang="en")
		self.created.append(made["name"])
		return made

	# -- reading ---------------------------------------------------------------------------------
	def test_the_forms_are_listed_with_their_questions_and_without_who_is_told(self):
		made = self.make("questions")
		self.module.save_form(made["name"], {"recipients": "boss@private.example"})
		answer = tools.run_list_site_forms(CTX, {})
		self.assertNotIn("boss@private.example", answer)
		listed = {form["name"]: form for form in json.loads(answer)["forms"]}
		form = listed[made["name"]]
		labels = [q["label"] for q in form["questions"]]
		self.assertIn("Budget you have in mind", labels)
		budget = next(q for q in form["questions"] if q["identifier"] == "budget")
		self.assertEqual((budget["type"], budget["required"]), ("Single choice", True))
		self.assertIn("Over 5,000 CHF", budget["choices"])

	def test_a_user_who_may_not_read_the_forms_is_told_so(self):
		frappe.set_user("Guest")
		self.assertTrue(tools.run_list_site_forms(CTX, {}).startswith("FAILED"))

	# -- creating --------------------------------------------------------------------------------
	def test_a_creation_raises_a_card_and_creates_nothing(self):
		before = frappe.db.count("Site Form")
		self.assertIsNone(
			tools.request_create_site_form(
				CTX,
				{
					"preset": "questions",
					"title": "Call back",
					"questions": [{"label": "Best time", "type": "text"}],
				},
			)
		)
		self.assertEqual(frappe.db.count("Site Form"), before)
		kind, summary, payload = self.cards[0]
		self.assertEqual(kind, "create_site_form")
		self.assertIn("Call back", summary)
		self.assertIn("Best time", summary)
		self.assertEqual(payload["preset"], "questions")

	def test_an_unknown_preset_or_too_many_questions_are_declined(self):
		self.assertTrue(tools.request_create_site_form(CTX, {"preset": "fancy"}).startswith("DECLINED"))
		many = [{"label": f"Q{i}"} for i in range(tools.MAX_QUESTIONS_PER_CALL + 1)]
		self.assertTrue(
			tools.request_create_site_form(CTX, {"preset": "simple", "questions": many}).startswith(
				"DECLINED"
			)
		)
		self.assertTrue(
			tools.request_create_site_form(CTX, {"preset": "simple", "questions": "text"}).startswith(
				"DECLINED"
			)
		)
		self.assertEqual(self.cards, [])

	def test_applying_a_creation_makes_the_form_and_says_how_to_put_it_on_a_page(self):
		message = pending.apply_pending_action(
			"create_site_form",
			{
				"preset": "simple",
				"title": "Call back " + uuid.uuid4().hex[:6],
				"questions": [{"label": "Best time", "type": "text"}],
			},
		)
		name = next(
			n for n in frappe.get_all("Site Form", pluck="name", order_by="creation desc") if n in message
		)
		self.created.append(name)
		self.assertIn('site_form = "' + name + '"', message)
		self.assertIn("builder/templates/includes/site_form.html", message)
		self.assertIn("Best time", [f["label"] for f in self.module.get_form(name)["fields"]])
		# the tag the message gives is one the assistant's block tools accept
		tag = (
			'{%- set site_form = "' + name + '" -%}{% include "builder/templates/includes/site_form.html" %}'
		)
		with patch("frappe.get_installed_apps", return_value=["frappe", "builder", "neoffice_theme"]):
			self.assertEqual(components.lawful_tag(tag), tag)

	# -- changing --------------------------------------------------------------------------------
	def test_a_change_raises_a_card_and_changes_nothing(self):
		made = self.make("questions")
		self.assertIsNone(
			tools.request_update_site_form(
				CTX,
				{"form": made["name"], "add_questions": [{"label": "Surface du local (m²)", "type": "text"}]},
			)
		)
		self.assertEqual(len(self.module.get_form(made["name"])["fields"]), len(made["fields"]))
		kind, summary, payload = self.cards[0]
		self.assertEqual(kind, "update_site_form")
		self.assertIn("Surface du local", summary)
		self.assertEqual(payload["form"], made["name"])

	def test_a_change_to_a_form_that_does_not_exist_is_declined(self):
		self.assertTrue(
			tools.request_update_site_form(CTX, {"form": "no-such-form", "title": "x"}).startswith("DECLINED")
		)
		self.assertTrue(tools.request_update_site_form(CTX, {"title": "x"}).startswith("DECLINED"))

	def test_a_change_that_changes_nothing_is_declined(self):
		made = self.make("simple")
		self.assertTrue(tools.request_update_site_form(CTX, {"form": made["name"]}).startswith("DECLINED"))
		self.assertEqual(self.cards, [])

	def test_applying_a_change_adds_the_question_before_the_message(self):
		made = self.make("questions")
		message = pending.apply_pending_action(
			"update_site_form",
			{
				"form": made["name"],
				"add_questions": [{"label": "Surface du local (m²)", "type": "text", "required": True}],
				"remove_questions": ["Budget you have in mind"],
				"settings": {"success_message": "We will come back to you within a day."},
			},
		)
		saved = self.module.get_form(made["name"])
		labels = [f["label"] for f in saved["fields"]]
		self.assertEqual(labels[-2:], ["Surface du local (m²)", "Message"])
		self.assertNotIn("Budget you have in mind", labels)
		self.assertEqual(saved["success_message"], "We will come back to you within a day.")
		self.assertIn(saved["title"], message)

	def test_a_change_the_theme_refuses_comes_back_as_a_sentence(self):
		made = self.make("simple")
		with self.assertRaises(frappe.ValidationError):
			pending.apply_pending_action(
				"update_site_form", {"form": made["name"], "remove_questions": ["sender"]}
			)
		self.assertEqual(len(self.module.get_form(made["name"])["fields"]), len(made["fields"]))

	def test_a_user_who_may_not_write_cannot_apply_a_change(self):
		made = self.make("simple")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			pending.apply_pending_action(
				"update_site_form", {"form": made["name"], "settings": {"title": "x"}}
			)
		with self.assertRaises(frappe.PermissionError):
			pending.apply_pending_action("create_site_form", {"preset": "simple"})


class TestWhatTheAssistantSeesOfTheInclude(unittest.TestCase):
	def test_the_names_of_the_forms_it_may_write_are_listed(self):
		param = {"name": "site_form", "choices_from": "builder.site_forms.form_choices", "about": "the form"}
		with patch(
			"builder.site_forms.form_choices",
			return_value=[{"value": "contact", "label": "Contact"}, {"value": "quote", "label": "Quote"}],
		):
			seen = _with_listed_choices(param, components)
		self.assertEqual(seen["choices"], ["contact", "quote"])
		self.assertNotIn("choices_from", seen)

	def test_a_parameter_with_constant_choices_is_left_alone(self):
		param = {"name": "display", "choices": [{"value": "full", "label": "Full"}]}
		self.assertIs(_with_listed_choices(param, components), param)
