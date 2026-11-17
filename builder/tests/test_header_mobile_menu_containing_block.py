# //// Neoffice — added file (no upstream equivalent): the phone menu of the site chrome must cover the screen.
# //// A sticky header carried `will-change: transform` (2026-08-04), which makes it the containing block of its
# //// position:fixed descendants: the menu (inset 0) was one bar high, its links lay over the page (found 2026-11-17).
import os
import re
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(HERE, "templates", "includes", "header_footer", "header_styles.html")

# what turns an element into the containing block of its fixed descendants
CONTAINING_BLOCK = re.compile(
	r"(?<![-\w])(?:transform|filter|backdrop-filter|perspective|container-type)\s*:\s*(?!none)"
	r"|(?<![-\w])contain\s*:\s*[^;]*\b(?:paint|layout|strict|content)\b"
	r"|will-change\s*:\s*[^;]*\b(?:transform|filter|backdrop-filter|perspective|contain)\b"
)
# a rule that styles the bar itself, at rest: .site-header, .site-header--sticky, .site-header--floating.site-header--sticky
RESTING_BAR = re.compile(r"\.site-header(?:--[a-z0-9-]+)*(?:\.site-header--[a-z0-9-]+)*")


def css_rules():
	"""(selector list, body) of every flat rule of the template's CSS, with the Jinja removed."""
	with open(TEMPLATE, encoding="utf-8") as f:
		text = f.read()
	text = re.sub(r"\{#.*?#\}", "", text, flags=re.S)
	text = re.sub(r"\{%.*?%\}", "", text, flags=re.S)
	text = re.sub(r"\{\{.*?\}\}", "x", text, flags=re.S)
	text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
	return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text)]


class TestThePhoneMenuIsNotTrappedInTheBar(unittest.TestCase):
	def test_the_bar_at_rest_creates_no_containing_block_for_its_fixed_children(self):
		"""The menu is `position: fixed; inset: 0` inside the header: with a containing block on the bar it is
		sized to the bar. Only the hidden state (`.is-hidden`, translated out of sight) may carry a transform."""
		offenders = []
		for selectors, body in css_rules():
			for selector in (s.strip() for s in selectors.split(",")):
				if RESTING_BAR.fullmatch(selector) and CONTAINING_BLOCK.search(body):
					offenders.append(f"{selector} {{ {' '.join(body.split())} }}")
		self.assertEqual([], offenders, "the bar traps its fixed descendants, the phone menu among them")

	def test_the_menu_is_still_fixed_over_the_whole_screen(self):
		"""The other half: if the menu stopped being fixed and full screen, the first test would prove nothing."""
		rule = next(body for selectors, body in css_rules() if selectors.strip() == ".site-header__mobile-menu")
		self.assertRegex(rule, r"position\s*:\s*fixed")
		self.assertRegex(rule, r"inset\s*:\s*0")

	def test_the_hidden_bar_still_slides_out(self):
		"""The fix removes a hint, not the behaviour: the bar still travels out of the way when it is hidden."""
		bodies = [body for selectors, body in css_rules() if selectors.strip() == ".site-header--sticky.is-hidden"]
		# one rule per mode: the default slides the bar out, the reduced-motion one keeps it in place on purpose
		self.assertTrue(any("translateY" in body for body in bodies))
