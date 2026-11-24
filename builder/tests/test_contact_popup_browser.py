# //// Neoffice — added file (no upstream equivalent): the contact window of the site chrome, played in a
# //// real browser (neoffice-maintenance#3336). The runtime is public/js/neo_contact_form.js, loaded on every page of
# //// a site; what a window must do (open from a link of the menu without leaving the page, keep the focus, close on
# //// Escape and give the focus back, step the burger menu aside, send like the form of a page) is behaviour that no
# //// string match proves. Each test builds the page a visitor would get (the real footer, the real script, the real
# //// header script) and serves it from a fake host: nothing leaves the machine. A bench without a headless Chromium
# //// (the CI of an app has none) skips the file.
import json
import os
import re
import unittest
from urllib.parse import parse_qs, urlparse

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = "builder/templates/includes/contact_form.html"
HOST = "http://site.test"
TOKEN = "/api/method/neoffice_theme.website_messages.issue_token"
CAPTCHA = "/api/method/neoffice_theme.website_messages.captcha_config"
SUBMIT = "/api/method/neoffice_theme.website_messages.submit"


def read(*parts):
	with open(os.path.join(HERE, *parts), encoding="utf-8") as f:
		return f.read()


def footer(**config):
	context = {
		"config": frappe._dict({"contact_popup": 1, **config}),
		"template": "Simple",
		"logo": None,
		"description": "",
		"copyright_text": "",
		"social_links": [],
		"show_newsletter": 0,
		"show_opening_hours": 0,
		"opening_hours_display": "Compact",
		"opening_hours": None,
		"newsletter_title": None,
		"newsletter_placeholder": None,
		"powered_by": None,
		"footer_columns": {},
		"legal_links": [],
		"logo_height": "Medium",
		"footer_html": None,
	}
	return frappe.render_template("builder/templates/includes/header_footer/footer.html", context)


def header_script():
	"""The script the real header ships (the burger menu), as it is: header_styles.html holds one."""
	scripts = re.findall(
		r"<script>(.*?)</script>", read("templates", "includes", "header_footer", "header_styles.html"), re.S
	)
	return scripts[-1]


HEADER = """
<header class="site-header">
	<button class="site-header__burger" aria-expanded="false" aria-label="Menu">Menu</button>
	<nav class="site-nav">
		<a id="menu-contact" class="site-nav__link" href="#contact">Contact</a>
		<a id="menu-about" class="site-nav__link" href="/about">About</a>
	</nav>
	<div class="site-header__mobile-menu" aria-hidden="true">
		<div class="mobile-menu__overlay"></div>
		<div class="mobile-menu__content">
			<button class="mobile-menu__close" aria-label="Close menu">x</button>
			<nav class="mobile-menu__nav"><a id="mobile-contact" class="mobile-menu__link" href="#contact">Contact</a></nav>
		</div>
	</div>
</header>
<style>.site-header__mobile-menu{display:none;position:fixed;inset:0;z-index:1001}.site-header__mobile-menu[aria-hidden="false"]{display:block}</style>
"""


def page(body="", window=True, **config):
	return (
		"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Test</title></head><body>"
		+ HEADER
		+ "<main><h1>A page</h1><a id='in-page' href='#contact'>Talk to us</a>"
		+ body
		+ "</main><footer>"
		+ (footer(**config) if window else "")
		+ "</footer><script>"
		+ read("public", "js", "neo_contact_form.js")
		+ "</script><script>"
		+ header_script()
		+ "</script></body></html>"
	)


class TestContactPopupInABrowser(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		try:
			from playwright.sync_api import sync_playwright

			cls.playwright = sync_playwright().start()
		except Exception as error:
			raise unittest.SkipTest(f"Playwright is not usable here: {error}")
		try:
			cls.browser = cls.playwright.chromium.launch()
		except Exception as error:
			cls.playwright.stop()
			raise unittest.SkipTest(f"no headless Chromium on this bench: {error}")

	@classmethod
	def tearDownClass(cls):
		cls.browser.close()
		cls.playwright.stop()

	def visit(self, pages, path="/about", viewport=None):
		"""Open `path` of a fake site; returns the page, with every request it made in self.calls."""
		self.calls = []
		context = self.browser.new_context(viewport=viewport or {"width": 1280, "height": 800})
		self.addCleanup(context.close)

		def serve(route):
			url = urlparse(route.request.url)
			self.calls.append((route.request.method, url.path, route.request.post_data))
			if url.path == TOKEN:
				return route.fulfill(json={"message": {"token": "signed-token", "decoy": ""}})
			if url.path == CAPTCHA:
				return route.fulfill(json={"message": {}})
			if url.path == SUBMIT:
				return route.fulfill(json={"message": "ok"})
			if url.path in pages:
				return route.fulfill(body=pages[url.path], content_type="text/html")
			return route.fulfill(status=404, body="")

		context.route(f"{HOST}/**", serve)
		tab = context.new_page()
		tab.goto(HOST + path)
		return tab

	def requests_to(self, path):
		return [call for call in self.calls if call[1] == path]

	def open_windows(self, tab):
		return tab.evaluate("document.querySelectorAll('dialog[open]').length")

	def test_a_link_of_the_menu_opens_the_window_without_leaving_the_page(self):
		tab = self.visit({"/about": page()})
		tab.evaluate("window.stayed = 1")
		tab.click("#menu-contact")
		self.assertEqual(1, self.open_windows(tab))
		self.assertEqual(HOST + "/about", tab.url)  # no #contact put on the address
		self.assertEqual(1, tab.evaluate("window.stayed"))  # the page did not reload
		self.assertEqual("Contact us", tab.inner_text("dialog[open] h2"))

	def test_a_link_inside_the_page_opens_it_too(self):
		tab = self.visit({"/about": page()})
		tab.click("#in-page")
		self.assertEqual(1, self.open_windows(tab))

	def test_the_address_of_another_page_opens_the_window(self):
		"""/about#contact is a link a menu may carry from another page: the page opens with the window."""
		tab = self.visit({"/about": page()}, path="/about#contact")
		self.assertEqual(1, self.open_windows(tab))

	def test_the_window_asks_the_server_for_nothing_until_it_opens(self):
		tab = self.visit({"/about": page()})
		tab.wait_for_timeout(300)
		self.assertEqual([], self.requests_to(TOKEN))
		self.assertEqual([], self.requests_to(CAPTCHA))
		tab.click("#menu-contact")
		tab.wait_for_timeout(300)
		self.assertEqual(1, len(self.requests_to(TOKEN)))
		# closing and opening again does not take a second one
		tab.keyboard.press("Escape")
		tab.click("#menu-contact")
		tab.wait_for_timeout(300)
		self.assertEqual(1, len(self.requests_to(TOKEN)))

	def test_the_focus_stays_in_the_window(self):
		tab = self.visit({"/about": page()})
		tab.click("#menu-contact")
		inside = "!!document.activeElement.closest('dialog')"
		self.assertTrue(tab.evaluate(inside))
		for _ in range(14):
			tab.keyboard.press("Tab")
			self.assertTrue(tab.evaluate(inside), "Tab left the window")
		for _ in range(14):
			tab.keyboard.press("Shift+Tab")
			self.assertTrue(tab.evaluate(inside), "Shift+Tab left the window")

	def test_escape_closes_the_window_and_the_focus_goes_back_to_the_link(self):
		tab = self.visit({"/about": page()})
		tab.focus("#menu-contact")
		tab.keyboard.press("Enter")
		self.assertEqual(1, self.open_windows(tab))
		tab.keyboard.press("Escape")
		self.assertEqual(0, self.open_windows(tab))
		self.assertEqual("menu-contact", tab.evaluate("document.activeElement.id"))

	def test_the_close_button_and_the_backdrop_close_it(self):
		tab = self.visit({"/about": page()})
		tab.click("#menu-contact")
		tab.click("dialog[open] [data-contact-close]")
		self.assertEqual(0, self.open_windows(tab))
		self.assertEqual("menu-contact", tab.evaluate("document.activeElement.id"))
		tab.click("#menu-contact")
		tab.mouse.click(4, 4)  # the backdrop
		self.assertEqual(0, self.open_windows(tab))

	def test_the_burger_menu_steps_aside_and_gets_the_focus_back(self):
		tab = self.visit({"/about": page()}, viewport={"width": 390, "height": 800})
		tab.evaluate("document.querySelector('.site-header__burger').style.display = 'block'")
		tab.click(".site-header__burger")
		self.assertEqual("false", tab.get_attribute(".site-header__mobile-menu", "aria-hidden"))
		tab.click("#mobile-contact")
		self.assertEqual(1, self.open_windows(tab))
		self.assertEqual("true", tab.get_attribute(".site-header__mobile-menu", "aria-hidden"))
		tab.keyboard.press("Escape")
		self.assertEqual(0, self.open_windows(tab))
		self.assertEqual("site-header__burger", tab.evaluate("document.activeElement.className"))

	def test_a_message_leaves_by_the_road_of_the_form_of_a_page(self):
		"""The same request, field for field, as the form standing on a page, given the same answers."""
		answers = {
			"full_name": "Ada Visitor",
			"sender": "ada@example.com",
			"message": "Is the green one in stock?",
		}
		inline = frappe.render_template('{% include "' + FORM + '" %}', {})
		sent = {}
		for where, body, window in (("window", "", True), ("page", inline, False)):
			tab = self.visit(
				{
					"/about": page(
						body=body, window=window, contact_popup_success="Thanks, we will reply soon."
					)
				}
			)
			if window:
				tab.click("#menu-contact")
				scope = "dialog[open] "
			else:
				scope = ""
				# the form of a page is in two steps: the first holds the name and the address
				tab.fill(scope + "input[name=full_name]", answers["full_name"])
				tab.fill(scope + "input[name=sender]", answers["sender"])
				tab.click(scope + "[data-step-next]")
			if window:
				tab.fill(scope + "input[name=full_name]", answers["full_name"])
				tab.fill(scope + "input[name=sender]", answers["sender"])
			tab.fill(scope + "textarea[name=message]", answers["message"])
			tab.click(scope + "button[type=submit]")
			tab.wait_for_selector(scope + ".builder-contact-form__status:not([hidden])", timeout=15000)
			posts = self.requests_to(SUBMIT)
			self.assertEqual(1, len(posts), where)
			sent[where] = {k: v[0] for k, v in parse_qs(posts[0][2]).items()}
			if window:
				self.assertEqual(
					"Thanks, we will reply soon.",
					tab.inner_text("dialog[open] .builder-contact-form__status"),
				)
		self.assertEqual(sent["page"], sent["window"])
		self.assertEqual("signed-token", sent["window"]["token"])
		self.assertEqual(answers["sender"], sent["window"]["sender"])
		self.assertNotIn("phone", {k for k, v in sent["window"].items() if v})

	def test_a_page_with_a_window_of_its_own_keeps_it_and_the_two_do_not_open_together(self):
		own = frappe.render_template(
			'{%- set contact_dialog = true -%}{%- set contact_button_text = "Write to us" -%}{% include "'
			+ FORM
			+ '" %}',
			{},
		)
		tab = self.visit({"/about": page(body=own)})
		tab.click("#menu-contact")
		self.assertEqual(1, self.open_windows(tab))  # the first window of the page answers the link
		tab.keyboard.press("Escape")
		tab.click("[data-contact-open]")
		self.assertEqual(1, self.open_windows(tab))  # its button opens it, and it alone
		self.assertEqual("Write to us", tab.inner_text("dialog[open] h2"))

	def test_a_site_that_does_not_ask_is_not_touched(self):
		tab = self.visit({"/about": page(window=False)})
		tab.click("#menu-contact")
		self.assertEqual(0, self.open_windows(tab))
		self.assertEqual(HOST + "/about#contact", tab.url)  # the link does what a link does

	def test_the_header_script_is_the_one_the_test_plays(self):
		"""The burger test above is faithful only while the header keeps these hooks."""
		script = header_script()
		for hook in (".site-header__burger", ".site-header__mobile-menu", ".mobile-menu__close"):
			self.assertIn(hook, script)
		json.dumps(script)  # a string, whatever it holds


if __name__ == "__main__":
	unittest.main()
