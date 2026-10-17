# //// Neoffice — added file (no upstream equivalent): the Builder Shortcode registry and the way it
# //// reaches a site (builder/utils.py sync_shortcodes, neoffice-maintenance#1593).
# ////
# //// What this guards. The rows sat in builder_shortcode_fixtures.json and nothing read it: the
# //// `fixtures` hook exports `source_app = "webshop"` only, and there is no builder/fixtures/
# //// folder. Measured on 2026-10-17: eight rows on our own instance, zero on a client's, updated
# //// that same morning. So the editor's shortcode list and the generator's own documentation were
# //// empty on every client site, and a ninth entry would have reached nobody. The test that matters
# //// here is the last one: a site with no shortcode at all gets them.
import json
import pathlib
import unittest

import frappe

APP = pathlib.Path(__file__).parent.parent
FIXTURES = APP / "builder/doctype/builder_shortcode/builder_shortcode_fixtures.json"
DOCTYPE_JSON = APP / "builder/doctype/builder_shortcode/builder_shortcode.json"
INSTALL = APP / "install.py"
CONTACT_FORM = "Contact Form"
INCLUDE = "builder/templates/includes/contact_form.html"


def rows():
	return json.loads(FIXTURES.read_text(encoding="utf-8"))


def row(name):
	return next(r for r in rows() if r["shortcode_name"] == name)


def categories():
	fields = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))["fields"]
	return set(next(f for f in fields if f["fieldname"] == "category")["options"].split("\n"))


class TestTheShortcodeFile(unittest.TestCase):
	def test_every_entry_is_complete(self):
		seen = set()
		for entry in rows():
			with self.subTest(entry.get("shortcode_name")):
				for field in ("doctype", "shortcode_name", "category", "source_app", "template_path"):
					self.assertTrue(entry.get(field), f"{field} is missing")
				self.assertEqual(entry["doctype"], "Builder Shortcode")
				self.assertIn(entry["category"], categories())
				self.assertNotIn(entry["shortcode_name"], seen)
				seen.add(entry["shortcode_name"])

	def test_each_template_is_where_the_entry_says(self):
		"""A path that points nowhere renders an empty page section and says nothing."""
		for entry in rows():
			app = entry["source_app"]
			if app not in frappe.get_installed_apps():
				continue
			with self.subTest(entry["shortcode_name"]):
				path = pathlib.Path(frappe.get_app_path(app)).parent / entry["template_path"]
				self.assertTrue(path.is_file(), f"{entry['template_path']} is not on disk")

	def test_the_parameters_are_readable_by_the_editor_and_the_generator(self):
		for entry in rows():
			with self.subTest(entry["shortcode_name"]):
				parameters = json.loads(entry.get("parameters") or "[]")
				self.assertIsInstance(parameters, list)
				for parameter in parameters:
					for field in ("name", "type", "description"):
						self.assertTrue(parameter.get(field), f"{field} is missing from {parameter}")


class TestTheContactFormEntry(unittest.TestCase):
	def test_it_points_at_the_include_that_is_the_form(self):
		entry = row(CONTACT_FORM)
		self.assertEqual(entry["template_path"], INCLUDE)
		self.assertEqual(entry["category"], "Form")
		self.assertIn(INCLUDE, entry["usage_syntax"])
		self.assertIn(INCLUDE, entry["example_code"])

	def test_it_offers_the_three_forms(self):
		parameters = {p["name"]: p for p in json.loads(row(CONTACT_FORM)["parameters"])}
		self.assertIn("contact_model", parameters)
		self.assertEqual(parameters["contact_model"]["default"], "steps")
		for model in ("simple", "steps", "questions"):
			self.assertIn(model, parameters["contact_model"]["description"])

	def test_it_documents_every_parameter_the_template_reads(self):
		"""The editor and the generator only know what this entry tells them."""
		template = (APP / "templates/includes/contact_form.html").read_text(encoding="utf-8")
		documented = {p["name"] for p in json.loads(row(CONTACT_FORM)["parameters"])}
		for name in ("contact_model", "contact_dialog", "contact_button_text", "consent_text", "phone_required"):
			with self.subTest(name):
				self.assertIn(f"{name} is defined", template)
				self.assertIn(name, documented)


class TestTheRegistryReachesASite(unittest.TestCase):
	"""The point of the whole file: a client had none of these rows."""

	def tearDown(self):
		frappe.db.rollback()

	def test_a_site_with_no_shortcode_at_all_gets_them(self):
		from builder.utils import sync_shortcodes

		frappe.db.delete("Builder Shortcode")
		self.assertEqual(frappe.db.count("Builder Shortcode"), 0)

		sync_shortcodes()

		expected = {r["shortcode_name"] for r in rows() if r["source_app"] in frappe.get_installed_apps()}
		self.assertTrue(expected, "no row of the file belongs to an installed app")
		self.assertEqual(expected, set(frappe.get_all("Builder Shortcode", pluck="name")))
		self.assertIn(CONTACT_FORM, expected)

	def test_a_shortcode_the_site_turned_off_stays_off(self):
		"""`enabled` belongs to the site: a migrate must not switch it back on."""
		from builder.utils import sync_shortcodes

		sync_shortcodes()
		frappe.db.set_value("Builder Shortcode", CONTACT_FORM, "enabled", 0)

		sync_shortcodes()

		self.assertEqual(frappe.db.get_value("Builder Shortcode", CONTACT_FORM, "enabled"), 0)
		# what the editor reads, however, follows the file
		self.assertEqual(
			frappe.db.get_value("Builder Shortcode", CONTACT_FORM, "template_path"),
			INCLUDE,
		)

	def test_a_row_that_will_not_save_does_not_stop_the_others(self):
		"""This runs inside `bench migrate` on every instance of the fleet. A row that refuses to
		save — one a site edited into something invalid, a field a later version renamed — must cost
		a line in the Error Log, not the instance's whole update."""
		import json as json_module
		import tempfile
		from unittest.mock import patch

		from builder.utils import sync_shortcodes

		broken = {
			"doctype": "Builder Shortcode",
			"shortcode_name": "Broken Test Shortcode",
			# a value the Select does not allow: the row refuses to save
			"category": "Not a category this doctype knows",
			"enabled": 1,
			"source_app": "builder",
			"template_path": "builder/templates/includes/contact_form.html",
		}
		with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
			json_module.dump([broken] + rows(), handle)
			path = handle.name

		real = frappe.get_module_path

		def only_the_fixtures(*args, **kwargs):
			# everything else still needs the real one: get_doc imports a controller through it
			if args and args[-1].endswith("builder_shortcode_fixtures.json"):
				return path
			return real(*args, **kwargs)

		frappe.db.delete("Builder Shortcode")
		with patch("frappe.get_module_path", side_effect=only_the_fixtures):
			sync_shortcodes()

		self.assertFalse(frappe.db.exists("Builder Shortcode", "Broken Test Shortcode"))
		expected = {r["shortcode_name"] for r in rows() if r["source_app"] in frappe.get_installed_apps()}
		self.assertEqual(expected, set(frappe.get_all("Builder Shortcode", pluck="name")))

	def test_a_row_of_an_app_that_is_not_installed_is_skipped(self):
		from builder.utils import sync_shortcodes

		frappe.db.delete("Builder Shortcode")
		sync_shortcodes()
		for entry in rows():
			if entry["source_app"] not in frappe.get_installed_apps():
				with self.subTest(entry["shortcode_name"]):
					self.assertFalse(frappe.db.exists("Builder Shortcode", entry["shortcode_name"]))


class TestItRunsOnEveryMigrate(unittest.TestCase):
	def test_a_fresh_site_and_an_updated_one_both_call_it(self):
		"""A sync nothing calls is a file nobody reads — which is how this started."""
		source = INSTALL.read_text(encoding="utf-8")
		self.assertIn("sync_shortcodes", source)
		after_install = source.split("def after_install")[1].split("def ")[0]
		after_migrate = source.split("def after_migrate")[1].split("def ")[0]
		self.assertIn("sync_shortcodes()", after_install)
		self.assertIn("sync_shortcodes()", after_migrate)
