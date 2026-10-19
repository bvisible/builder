# //// Neoffice — added file (no upstream equivalent): the Builder Shortcode registry is written FROM the component
# //// catalogue (builder/site_ai/components.py), not typed and not shipped as a file (neoffice-maintenance#1593).
# ////
# //// What this guards. On 2026-10-17 there were THREE registries that said the same thing — the catalogue (code), a
# //// fixture file of Builder Shortcode rows that nothing read, and Builder AI Shortcode rows typed on one instance and
# //// read by the old generator's prompt — and the editor's list and the generator's prompt each knew a different part.
# //// The catalogue is the only definition now; the registry is its mirror on each site and keeps the one thing a
# //// person owns there, `enabled`. The tests that matter are the last ones: a switch a site turned off stays off
# //// through a migrate, takes the component out of what is offered, and does not break a page that carries it.
import json
import pathlib
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import api
from builder.site_ai import components
from builder.utils import sync_shortcodes

APP = pathlib.Path(__file__).parent.parent
DOCTYPE_JSON = APP / "builder/doctype/builder_shortcode/builder_shortcode.json"
FIXTURES = APP / "builder/doctype/builder_shortcode/builder_shortcode_fixtures.json"
INSTALL = APP / "install.py"
CONTACT_FORM = "Contact form"
INCLUDE = "builder/templates/includes/contact_form.html"
MAP = "builder/templates/includes/google_map.html"


def doctype():
	return json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))


def categories():
	fields = doctype()["fields"]
	return set(next(f for f in fields if f["fieldname"] == "category")["options"].split("\n"))


def registry():
	return {
		r.template_path: r
		for r in frappe.get_all(components.REGISTRY, fields=["name", "template_path", "enabled"])
	}


class TestTheRowsAreWrittenFromTheCatalogue(unittest.TestCase):
	def test_every_component_has_a_complete_row(self):
		seen = set()
		for component in components.catalogue():
			with self.subTest(component.label):
				row = components.registry_row(component)
				for field in (
					"shortcode_name",
					"category",
					"source_app",
					"template_path",
					"description",
					"usage_syntax",
					"example_code",
				):
					self.assertTrue(row[field], f"{field} is missing")
				self.assertIn(row["category"], categories())
				self.assertNotIn(row["shortcode_name"], seen)
				seen.add(row["shortcode_name"])
				self.assertEqual(row["template_path"], component.path)
				self.assertIn(component.path, row["usage_syntax"])

	def test_the_example_is_a_tag_the_editor_would_write(self):
		"""An example nobody could place is worse than none: it must come back unchanged from lawful_tag."""
		for component in components.catalogue():
			with self.subTest(component.label):
				example = components.registry_row(component)["example_code"]
				self.assertEqual(components.lawful_tag(example), example)

	def test_the_parameters_are_readable_by_the_editor_and_the_generator(self):
		for component in components.catalogue():
			with self.subTest(component.label):
				parameters = json.loads(components.registry_row(component)["parameters"])
				self.assertIsInstance(parameters, list)
				self.assertEqual([p["name"] for p in parameters], [p["name"] for p in component.params])
				for parameter in parameters:
					for field in ("name", "label", "type", "description"):
						self.assertTrue(parameter.get(field), f"{field} is missing from {parameter}")

	def test_the_contact_form_offers_its_three_forms(self):
		component = components.by_file("contact_form.html")
		row = components.registry_row(component)
		self.assertEqual(row["category"], "Form")
		parameters = {p["name"]: p for p in json.loads(row["parameters"])}
		self.assertEqual(parameters["contact_model"]["default"], "steps")
		self.assertEqual(parameters["contact_model"]["choices"], ["simple", "steps", "questions"])
		self.assertIn("contact_model", row["example_code"])

	def test_it_documents_only_what_the_template_reads(self):
		"""The editor and the generator only know what the catalogue tells them; a parameter its template never reads
		would be an option that does nothing (the map's `map_address`, 2026-09-16)."""
		for component in components.catalogue():
			template = pathlib.Path(frappe.get_app_path(component.app)).parent / component.path
			if not template.is_file():
				continue
			text = template.read_text(encoding="utf-8")
			for param in component.params:
				with self.subTest(f"{component.label}: {param['name']}"):
					self.assertIn(param["name"], text)
		contact = (APP / "templates/includes/contact_form.html").read_text(encoding="utf-8")
		for name in (
			"contact_model",
			"contact_dialog",
			"contact_button_text",
			"consent_text",
			"phone_required",
		):
			with self.subTest(name):
				self.assertIn(f"{name} is defined", contact)


class TestThereIsNoSecondDefinition(unittest.TestCase):
	def test_the_fixture_file_is_gone(self):
		"""It was the second copy: rows typed beside the catalogue, which a person could not tell from it."""
		self.assertFalse(FIXTURES.exists())

	def test_the_export_hook_is_gone(self):
		import builder.hooks as hooks

		self.assertFalse(
			hasattr(hooks, "fixtures"), "an export of the registry would write a second definition"
		)

	def test_a_person_switches_a_block_and_nothing_else(self):
		"""The definition fields are read-only, nobody creates or deletes a row: it is written from the code."""
		meta = doctype()
		fields = {f["fieldname"]: f for f in meta["fields"]}
		for name in (
			"shortcode_name",
			"category",
			"source_app",
			"template_path",
			"description",
			"usage_syntax",
			"parameters",
			"example_code",
		):
			self.assertTrue(fields[name].get("read_only"), name)
		self.assertFalse(fields["enabled"].get("read_only"))
		for permission in meta["permissions"]:
			self.assertFalse(permission.get("create"), permission["role"])
			self.assertFalse(permission.get("delete"), permission["role"])
			self.assertTrue(permission.get("write"), permission["role"])

	def test_the_doctype_is_newer_than_the_one_a_migrate_already_loaded(self):
		"""A migrate reloads a doctype only if its `modified` moved: the file carried 2025-02-02 until this change."""
		self.assertGreater(doctype()["modified"], "2026-10-19")


class TestTheRegistryReachesASite(FrappeTestCase):
	"""The point: a client had no row, and a row that nobody wrote from the code would drift from it."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_a_site_with_no_row_gets_one_per_component(self):
		frappe.db.delete(components.REGISTRY)

		done = sync_shortcodes_counts()

		wanted = {c.path for c in components.catalogue()}
		self.assertTrue(wanted)
		self.assertEqual(set(registry()), wanted)
		self.assertEqual(done["added"], len(wanted))
		self.assertTrue(frappe.db.exists(components.REGISTRY, CONTACT_FORM))

	def test_a_second_run_changes_nothing(self):
		sync_shortcodes()
		done = sync_shortcodes_counts()
		self.assertEqual((done["added"], done["updated"], done["removed"], done["failed"]), (0, 0, 0, 0))

	def test_the_documentation_follows_the_code(self):
		sync_shortcodes()
		frappe.db.set_value(components.REGISTRY, CONTACT_FORM, "description", "stale words from another time")

		sync_shortcodes()

		self.assertEqual(
			frappe.db.get_value(components.REGISTRY, CONTACT_FORM, "description"),
			components.by_file("contact_form.html").shows,
		)

	def test_a_block_the_site_turned_off_stays_off(self):
		"""`enabled` belongs to the site: a migrate must not switch it back on."""
		sync_shortcodes()
		frappe.db.set_value(components.REGISTRY, CONTACT_FORM, "enabled", 0)

		sync_shortcodes()

		self.assertEqual(frappe.db.get_value(components.REGISTRY, CONTACT_FORM, "enabled"), 0)
		self.assertEqual(frappe.db.get_value(components.REGISTRY, CONTACT_FORM, "template_path"), INCLUDE)

	def test_a_row_of_the_old_fixture_keeps_its_switch_under_its_new_name(self):
		"""The fixture called it "Contact Form", the catalogue "Contact form": the row is found by what it points at,
		renamed, and its `enabled` survives (the one thing the rename must not cost)."""
		frappe.db.delete(components.REGISTRY)
		frappe.get_doc(
			{
				"doctype": components.REGISTRY,
				"shortcode_name": "Contact Form",
				"category": "Form",
				"enabled": 0,
				"source_app": "builder",
				"template_path": INCLUDE,
			}
		).insert(ignore_permissions=True)

		sync_shortcodes()

		self.assertEqual(frappe.db.get_value(components.REGISTRY, CONTACT_FORM, "enabled"), 0)
		self.assertEqual(frappe.db.count(components.REGISTRY, {"template_path": INCLUDE}), 1)

	def test_what_the_catalogue_does_not_hold_is_removed(self):
		"""A retired component, an include of the old fixture that was never a block (Order Summary needs a `doc`),
		a row typed by hand: nothing reads them, and they looked like something."""
		sync_shortcodes()
		for name, path in (
			("Order Summary", "webshop/templates/includes/order_summary.html"),
			("Typed by hand", "builder/templates/includes/not_catalogued.html"),
		):
			frappe.get_doc(
				{
					"doctype": components.REGISTRY,
					"shortcode_name": name,
					"category": "Other",
					"source_app": "builder",
					"template_path": path,
				}
			).insert(ignore_permissions=True)

		done = sync_shortcodes_counts()

		self.assertEqual(done["removed"], 2)
		self.assertFalse(frappe.db.exists(components.REGISTRY, "Order Summary"))
		self.assertFalse(frappe.db.exists(components.REGISTRY, "Typed by hand"))
		self.assertEqual(set(registry()), {c.path for c in components.catalogue()})

	def test_a_row_that_will_not_save_does_not_stop_the_others(self):
		"""This runs inside `bench migrate` on every instance of the fleet. A row that refuses to save must cost a
		line in the Error Log, not the instance's whole update."""
		frappe.db.delete(components.REGISTRY)
		real = components.registry_row

		def one_bad_row(component):
			row = real(component)
			if component.path == INCLUDE:
				# a value the Select does not allow: the row refuses to save
				row["category"] = "Not a category this doctype knows"
			return row

		with patch.object(components, "registry_row", side_effect=one_bad_row):
			done = components.sync_registry()

		self.assertEqual(done["failed"], 1)
		self.assertNotIn(INCLUDE, registry())
		self.assertEqual(set(registry()), {c.path for c in components.catalogue()} - {INCLUDE})


def sync_shortcodes_counts():
	return components.sync_registry()


class TestTheSwitchIsHonoured(FrappeTestCase):
	"""Turning a block off stops it being offered. It does not break a page that carries it."""

	def setUp(self):
		frappe.set_user("Administrator")
		sync_shortcodes()
		frappe.db.set_value(components.REGISTRY, CONTACT_FORM, "enabled", 0)

	def test_it_is_no_longer_offered_to_a_page(self):
		self.assertNotIn(INCLUDE, [c.path for c in components.for_page("contact")])
		self.assertNotIn(INCLUDE, [c.path for c in components.enabled_catalogue()])
		self.assertIn(INCLUDE, [c.path for c in components.catalogue()])

	def test_the_editor_lists_it_as_off_and_does_not_recommend_it(self):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Switch contact",
				"route": "contact",
				"published": 0,
				"blocks": "[]",
			}
		).insert(ignore_permissions=True)
		listed = {c["path"]: c for c in api.get_site_components(page=page.name)}
		self.assertIs(listed[INCLUDE]["enabled"], False)
		self.assertFalse(listed[INCLUDE]["suited"])
		self.assertIs(listed[MAP]["enabled"], True)

	def test_a_page_that_carries_it_keeps_it(self):
		tag = components.by_file("contact_form.html").tag({"contact_model": "questions"})
		self.assertEqual(components.lawful_tag(tag), tag)
		self.assertEqual(components.clean_tag(tag), tag)
		self.assertEqual(api.read_component_tag(tag)["values"], {"contact_model": "questions"})
		self.assertEqual(
			api.render_component_tag(INCLUDE, {"contact_model": "simple"}),
			components.by_file("contact_form.html").tag({"contact_model": "simple"}),
		)

	def test_the_two_endpoints_that_read_the_registry_follow_the_catalogue_and_the_switch(self):
		available = {row["template_path"]: row for row in api.get_available_shortcodes()}
		self.assertNotIn(INCLUDE, available)
		self.assertIn(MAP, available)
		for key in (
			"shortcode_name",
			"category",
			"source_app",
			"template_path",
			"description",
			"usage_syntax",
			"parameters",
			"example_code",
		):
			self.assertIn(key, available[MAP])
		self.assertIsInstance(available[MAP]["parameters"], list)

		markdown = api.get_shortcodes_for_ai()
		self.assertIn(MAP, markdown)
		self.assertNotIn(INCLUDE, markdown)

	def test_switched_back_on_it_is_offered_again(self):
		frappe.db.set_value(components.REGISTRY, CONTACT_FORM, "enabled", 1)
		self.assertIn(INCLUDE, [c.path for c in components.for_page("contact")])
		self.assertIn(INCLUDE, {row["template_path"] for row in api.get_available_shortcodes()})
		self.assertIn("contact_model", api.get_shortcodes_for_ai())


class TestTheOldGeneratorsPromptReadsTheCatalogue(FrappeTestCase):
	"""get_shortcodes_context fed the old generator the Builder AI Shortcode rows of ONE instance."""

	def setUp(self):
		frappe.set_user("Administrator")
		sync_shortcodes()

	def own_shortcode(self, name, include):
		return frappe.get_doc(
			{
				"doctype": "Builder AI Shortcode",
				"name1": name,
				"shortcode": name.lower().replace(" ", "_"),
				"category": "Other",
				"description": f"{name} of this site",
				"jinja_code": f"{{% include '{include}' %}}",
			}
		).insert(ignore_permissions=True)

	def context(self, page_type=None):
		from builder.site_ai.prompts.system_prompts import get_shortcodes_context

		return get_shortcodes_context(page_type)

	def test_the_components_are_the_catalogues_with_their_options(self):
		text = self.context("contact")
		self.assertIn(INCLUDE, text)
		self.assertIn("contact_model", text)  # the three forms, which the typed row never knew

	def test_a_typed_row_that_repeats_a_component_is_not_listed_twice(self):
		self.own_shortcode("Google Map", MAP)
		text = self.context("contact")
		# the catalogue's map may or may not be offered here (it needs an address): the typed row never is
		self.assertLessEqual(text.count(MAP), 1)
		self.assertNotIn("Google Map of this site", text)

	def test_a_typed_row_the_catalogue_does_not_hold_is_still_offered(self):
		self.own_shortcode("Search Box", "webshop/templates/includes/search_box.html")
		text = self.context("contact")
		self.assertIn("webshop/templates/includes/search_box.html", text)
		self.assertIn("Search Box", text)

	def test_a_block_the_site_turned_off_is_not_offered(self):
		frappe.db.set_value(components.REGISTRY, CONTACT_FORM, "enabled", 0)
		self.assertNotIn(INCLUDE, self.context("contact"))

	def test_a_page_type_the_catalogue_does_not_know_gets_what_the_site_offers(self):
		text = self.context("accueil_ecommerce")
		self.assertIn(INCLUDE, text)


class TestItRunsOnEveryMigrate(unittest.TestCase):
	def test_a_fresh_site_and_an_updated_one_both_call_it(self):
		"""A sync nothing calls is a registry nobody writes — which is how this started."""
		source = INSTALL.read_text(encoding="utf-8")
		self.assertIn("sync_shortcodes", source)
		after_install = source.split("def after_install")[1].split("def ")[0]
		after_migrate = source.split("def after_migrate")[1].split("def ")[0]
		self.assertIn("sync_shortcodes()", after_install)
		self.assertIn("sync_shortcodes()", after_migrate)

	def test_sync_shortcodes_is_the_catalogues_sync(self):
		"""The name the hooks call must not become a second implementation."""
		with patch.object(
			components, "sync_registry", return_value={"added": 0, "updated": 0, "removed": 0, "failed": 0}
		) as sync:
			from builder.utils import sync_shortcodes as call

			call()
		sync.assert_called_once()
