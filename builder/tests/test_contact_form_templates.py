# //// Neoffice — added file (no upstream equivalent): the contact forms an owner drops in the editor
# //// (builder_block_template/contact_form_*) and the one runtime they share
# //// (public/js/neo_contact_form.js), neoffice-maintenance#1593.
# ////
# //// What this guards. The stock endpoint was a spam relay and filed nothing; the form that replaced
# //// it carries a signed token, a minimum delay and a field only a script fills. Those live in the
# //// runtime now, so a template is only markup — and a template whose field is misnamed, whose
# //// honeypot is missing or whose category the panel does not draw fails silently: the visitor sees a
# //// form, presses Send, and nobody ever receives anything. That is the shape of the bug this whole
# //// work came from, so each of those ways to lose a message is a test here.
import json
import pathlib
import re
import unittest

APP = pathlib.Path(__file__).parent.parent
TEMPLATES = APP / "builder/builder_block_template"
PREVIEWS = APP / "www"
RUNTIME = APP / "public/js/neo_contact_form.js"
INCLUDE = APP / "templates/includes/contact_form.html"
STORE = APP.parent / "frontend/src/stores/blockTemplateStore.ts"

CONTACT_FORMS = ("contact_form_simple", "contact_form_steps", "contact_form_questions")
SUBMIT_URL = "/api/method/neoffice_theme.website_messages.submit"

# upstream's own form templates, left in categories our panel does not draw on purpose: they are
# markup with no endpoint behind them, and the category list is also what the site generator picks
# from (blockTemplateStore.ts). Making them visible would put a form that posts nowhere one click
# away, and in the generator's reach.
DELIBERATELY_NOT_DRAWN = {"form_1", "form_2", "form_3", "label"}


def load(folder):
	return json.loads((TEMPLATES / folder / f"{folder}.json").read_text(encoding="utf-8"))


def tree(folder):
	return json.loads(load(folder)["block"])


def walk(block):
	yield block
	for child in block.get("children") or []:
		yield from walk(child)


def controls(block):
	"""Every named field of the form, as (name, element, type, customAttributes)."""
	found = []
	for node in walk(block):
		custom = node.get("customAttributes") or {}
		if custom.get("name"):
			found.append(
				(custom["name"], node["element"], (node.get("attributes") or {}).get("type", ""), custom)
			)
	return found


def drawn_categories():
	"""The categories the editor's panel actually draws, read from its own list."""
	source = STORE.read_text(encoding="utf-8")
	block = re.search(r"blockTemplateCategoryOptions:\s*\[(.*?)\]\s*as", source, re.S).group(1)
	return set(re.findall(r'"([^"]+)"', block))


def runtime_known_fields():
	"""The eight names the runtime posts as fields; anything else it folds into the message."""
	line = re.search(r"var KNOWN_FIELDS = \[(.*?)\];", RUNTIME.read_text(encoding="utf-8"), re.S).group(1)
	return set(re.findall(r'"([^"]+)"', line))


class TestEveryContactFormReachesTheInbox(unittest.TestCase):
	def test_the_form_posts_to_the_endpoint_that_stores_the_message_first(self):
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				forms = [node for node in walk(tree(folder)) if node["element"] == "form"]
				self.assertEqual(len(forms), 1)
				custom = forms[0]["customAttributes"]
				self.assertEqual(custom["action"], SUBMIT_URL)
				self.assertEqual(custom["method"], "POST")
				self.assertEqual(custom["data-neo-contact"], "1")
				# the runtime takes the token here, and falls back on the stock URL on a 404
				self.assertIn("issue_token", custom["data-token-url"])
				self.assertIn("frappe.www.contact.send_message", custom["data-legacy-action"])

	def test_one_field_is_the_address_and_it_is_an_email(self):
		"""The name field was named `sender` too once, and no message ever arrived (#398)."""
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				senders = [c for c in controls(tree(folder)) if c[0] == "sender"]
				self.assertEqual(len(senders), 1)
				self.assertEqual(senders[0][2], "email")

	def test_a_message_and_a_way_to_send_it(self):
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				block = tree(folder)
				names = [c[0] for c in controls(block)]
				self.assertIn("message", names)
				self.assertIn("full_name", names)
				submits = [
					node
					for node in walk(block)
					if node["element"] == "button" and (node.get("attributes") or {}).get("type") == "submit"
				]
				self.assertEqual(len(submits), 1)

	def test_the_visitor_is_told_what_happened(self):
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				status = [n for n in walk(tree(folder)) if (n.get("customAttributes") or {}).get("data-neo-status")]
				self.assertEqual(len(status), 1)
				# the texts are the template's own, in the site's language, not the runtime's fallbacks
				custom = [n for n in walk(tree(folder)) if n["element"] == "form"][0]["customAttributes"]
				for key in ("data-sent", "data-failed", "data-throttled"):
					self.assertTrue(custom.get(key), f"{folder} says nothing for {key}")


class TestTheDefenceTravelsWithEveryTemplate(unittest.TestCase):
	"""A template is markup, so these are the parts of the defence that are markup."""

	def test_each_form_carries_the_field_only_a_bot_fills(self):
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				traps = [n for n in walk(tree(folder)) if (n.get("customAttributes") or {}).get("data-neo-honeypot")]
				self.assertEqual(len(traps), 1)
				trap = traps[0]
				# off screen, not display:none: a bot that reads the markup has to believe it is real
				self.assertEqual(trap["baseStyles"].get("left"), "-9999px")
				self.assertEqual(trap["baseStyles"].get("position"), "absolute")
				inside = [c[0] for c in controls(trap)]
				self.assertEqual(inside, ["website"])

	def test_every_question_of_its_own_says_which_question_it_is(self):
		"""A name the runtime does not know travels inside the message, under its question.

		The runtime takes data-label first, then the label tied to the field. A radio or a box
		MUST carry data-label: the label beside one belongs to the option, so the owner would
		read "Un devis: Un devis" instead of the question that was asked.
		"""
		known = runtime_known_fields()
		for folder in CONTACT_FORMS:
			block = tree(folder)
			tied = {(n.get("customAttributes") or {}).get("for") for n in walk(block) if n["element"] == "label"}
			for name, element, kind, custom in controls(block):
				if name in known:
					continue
				with self.subTest(folder=folder, field=name):
					if kind in ("radio", "checkbox"):
						self.assertTrue(
							custom.get("data-label"),
							f"{name} is one option among several: it must name the question",
						)
					else:
						self.assertTrue(
							custom.get("data-label") or custom.get("id") in tied,
							f"{name} has nothing to call itself in the message",
						)

	def test_the_runtime_is_loaded_on_the_pages_that_carry_a_form(self):
		"""Not by web_include_js: frappe renders those in base.html, and a Builder page never goes
		through it — our templates/generators/webpage.html owns the document. The page says whether
		it has a form and loads the runtime itself, so a page without one loads nothing."""
		page = (APP / "builder/doctype/builder_page/builder_page.py").read_text(encoding="utf-8")
		self.assertIn("context.has_contact_form", page)
		self.assertIn("_asset_version('js/neo_contact_form.js')", page)
		# both doors: a block template renders the attribute, the include is still an {% include %} here
		self.assertIn('"data-neo-contact" in content', page)
		self.assertIn('"contact_form.html" in content', page)
		scripts = (APP / "templates/generators/webpage_scripts.html").read_text(encoding="utf-8")
		self.assertIn("{% if has_contact_form %}", scripts)
		self.assertIn("{{ contact_form_script }}", scripts)
		self.assertTrue(RUNTIME.is_file())

	def test_there_is_only_one_implementation(self):
		"""The include carried its own copy of the script: the next form beside it shipped without."""
		self.assertNotIn("<script>", INCLUDE.read_text(encoding="utf-8"))
		source = RUNTIME.read_text(encoding="utf-8")
		for part in ("issue_token", "TOKEN_MIN_AGE_MS", "data-neo-honeypot", "legacyBody"):
			self.assertIn(part, source)


class TestTheEditorDrawsThem(unittest.TestCase):
	def test_the_contact_forms_sit_in_a_category_the_panel_draws(self):
		drawn = drawn_categories()
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				self.assertIn(load(folder)["category"], drawn)

	def test_upstream_s_own_forms_stay_out_of_the_panel(self):
		"""Not an oversight: see DELIBERATELY_NOT_DRAWN above before making them visible."""
		drawn = drawn_categories()
		for folder in sorted(DELIBERATELY_NOT_DRAWN):
			with self.subTest(folder):
				self.assertNotIn(load(folder)["category"], drawn)

	def test_each_one_has_a_preview_the_panel_can_show(self):
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				preview = load(folder)["preview"]
				self.assertTrue(preview.startswith("/builder_assets/"))
				self.assertTrue((PREVIEWS / preview.lstrip("/")).is_file(), f"{preview} is not on disk")

	def test_each_one_says_what_it_is_for(self):
		"""The description is what the site generator chooses a template by (83b20f91)."""
		for folder in CONTACT_FORMS:
			with self.subTest(folder):
				doc = load(folder)
				self.assertTrue(doc.get("description"))
				self.assertEqual(doc["name"], doc["template_name"])


class TestTheFormInSteps(unittest.TestCase):
	def test_the_steps_are_numbered_without_a_gap(self):
		steps = sorted(
			int((n.get("customAttributes") or {}).get("data-step"))
			for n in walk(tree("contact_form_steps"))
			if (n.get("customAttributes") or {}).get("data-step")
		)
		self.assertEqual(steps, [1, 2, 3])

	def test_every_step_but_the_last_goes_forward_and_every_one_but_the_first_goes_back(self):
		block = tree("contact_form_steps")
		for node in walk(block):
			step = (node.get("customAttributes") or {}).get("data-step")
			if not step:
				continue
			buttons = [(n.get("customAttributes") or {}) for n in walk(node) if n["element"] == "button"]
			forward = any("data-step-next" in b for b in buttons)
			back = any("data-step-back" in b for b in buttons)
			submit = any(
				(n.get("attributes") or {}).get("type") == "submit" for n in walk(node) if n["element"] == "button"
			)
			with self.subTest(step=step):
				self.assertEqual(forward or submit, True)
				self.assertEqual(back, step != "1")

	def test_the_steps_are_an_enhancement_the_buttons_wait_for_the_script(self):
		"""Without JavaScript every step shows and the form posts in one go: a Next that cannot
		work must not be drawn."""
		for node in walk(tree("contact_form_steps")):
			custom = node.get("customAttributes") or {}
			if "data-step-next" in custom or "data-step-back" in custom or "data-progress" in custom:
				with self.subTest(custom):
					self.assertEqual((node.get("attributes") or {}).get("hidden"), "true")

	def test_the_progress_line_counts_by_itself(self):
		steps = tree("contact_form_steps")
		progress = [n for n in walk(steps) if (n.get("customAttributes") or {}).get("data-progress")]
		self.assertEqual(len(progress), 1)
		html = progress[0]["innerHTML"]
		self.assertIn("data-step-now", html)
		self.assertIn("data-step-total", html)


class TestTheRuntimeAndTheEndpointAgree(unittest.TestCase):
	def test_the_runtime_posts_the_fields_the_endpoint_takes(self):
		"""Across two apps: the theme owns the endpoint, the builder owns the form."""
		try:
			from neoffice_theme.website_messages import submit
		except ImportError:
			self.skipTest("neoffice_theme is not on this bench")
		import inspect

		self.assertEqual(runtime_known_fields(), set(inspect.signature(submit).parameters))
