# //// Neoffice — added file (no upstream equivalent): the site's colours and fonts stay equal
# //// between the Builder Tokens (upstream design system) and the chrome's theme fields.
import frappe
from frappe.tests.utils import FrappeTestCase

PREFIX = "tst"
KEYS = {"primary": "#112233", "secondary": "#445566", "background": "#fafafa", "text": "#101010", "font-heading": "Raleway", "font-body": "Inter"}


class TestDesignSystemSync(FrappeTestCase):
	"""Theme pane -> tokens on save, Design Tokens -> theme fields through the hook,
	and a save that touched something else leaves an edited token alone."""

	def setUp(self):
		frappe.set_user("Administrator")
		for key, value in KEYS.items():
			name = f"{PREFIX}-{key}"
			if frappe.db.exists("Builder Token", name):
				frappe.db.set_value("Builder Token", name, "value", value)
			else:
				frappe.get_doc(
					{"doctype": "Builder Token", "token_name": f"Test {key}", "type": "Font" if key.startswith("font") else "Color", "value": value, "group": "Test"}
				).insert(ignore_permissions=True, set_name=name)
		config = frappe.get_single("Website Header Footer Config")
		self._saved = {f: config.get(f) for f in ("token_prefix", "primary_color", "secondary_color", "background_color", "text_color", "heading_font", "body_font")}
		config.token_prefix = PREFIX
		config.primary_color, config.secondary_color = KEYS["primary"], KEYS["secondary"]
		config.background_color, config.text_color = KEYS["background"], KEYS["text"]
		config.heading_font, config.body_font = KEYS["font-heading"], KEYS["font-body"]
		config.save(ignore_permissions=True)

	def tearDown(self):
		config = frappe.get_single("Website Header Footer Config")
		config.flags.skip_token_sync = True
		for f, v in self._saved.items():
			config.set(f, v)
		config.save(ignore_permissions=True)
		for key in KEYS:
			frappe.delete_doc("Builder Token", f"{PREFIX}-{key}", ignore_permissions=True, force=True)

	def test_the_theme_pane_writes_the_tokens(self):
		config = frappe.get_single("Website Header Footer Config")
		config.primary_color = "#abcdef"
		config.heading_font = "Playfair Display"
		config.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Builder Token", f"{PREFIX}-primary", "value"), "#abcdef")
		self.assertEqual(frappe.db.get_value("Builder Token", f"{PREFIX}-font-heading", "value"), "Playfair Display")

	def test_a_token_edit_writes_the_theme_field(self):
		token = frappe.get_doc("Builder Token", f"{PREFIX}-secondary")
		token.value = "#fedcba"
		token.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_single_value("Website Header Footer Config", "secondary_color"), "#fedcba")
		token = frappe.get_doc("Builder Token", f"{PREFIX}-font-body")
		token.value = "Source Sans 3"
		token.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_single_value("Website Header Footer Config", "body_font"), "Source Sans 3")

	def test_an_unrelated_save_leaves_an_edited_token_alone(self):
		# the pane loaded the config, then someone edited the token behind it
		config = frappe.get_single("Website Header Footer Config")
		frappe.db.set_value("Builder Token", f"{PREFIX}-text", "value", "#222222")
		config.footer_text_color = "#333333"
		config.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Builder Token", f"{PREFIX}-text", "value"), "#222222")
