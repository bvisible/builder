# //// Neoffice — added file (no upstream equivalent): on a phone, a section number does not sit on its heading and a
# //// caption is not cut by its box (neoffice-maintenance#1750). The trees are those the local model stored on
# //// 2026-10-20, reduced to the blocks that matter.
import copy
import unittest

from builder.site_ai.nora import layout

NUMBER = {
	"element": "span",
	"innerHTML": "02",
	"baseStyles": {
		"position": "absolute",
		"top": "12px",
		"left": "12px",
		"fontSize": "3rem",
		"lineHeight": "1",
	},
}
# "Groupes et banquets": the heading cleared the number by a 56 px margin, taken back on the phone
SECTION = {
	"element": "div",
	"baseStyles": {"position": "relative", "margin": "0 auto"},
	"children": [
		NUMBER,
		{
			"element": "h2",
			"innerHTML": "Ce que la maison met à votre table",
			"baseStyles": {"margin": "0 0 16px 56px"},
			"mobileStyles": {"margin": "0 0 16px 0px"},
		},
	],
}
# "La carte": the heading sits in a column 60 % wide on a wide screen, the whole line on the phone
WRAPPED_SECTION = {
	"element": "div",
	"baseStyles": {"display": "flex", "justifyContent": "center", "position": "relative"},
	"children": [
		{**NUMBER, "innerHTML": "01"},
		{
			"element": "div",
			"baseStyles": {"width": "60%"},
			"mobileStyles": {"width": "100%"},
			"children": [{"element": "h2", "innerHTML": "Cuisine de saison aux produits du terroir"}],
		},
	],
}
# the accounting firm's home: a caption in the blue square, centred on its left edge and held on one line
SQUARE = {
	"element": "div",
	"baseStyles": {"position": "absolute", "inset": "0", "backgroundColor": "var(--primary)"},
	"children": [
		{
			"element": "div",
			"innerHTML": "6",
			"baseStyles": {
				"position": "absolute",
				"left": "50%",
				"top": "50%",
				"transform": "translate(-50%, -50%)",
			},
		},
		{
			"element": "p",
			"innerHTML": "semaines pour le bouclement de vos comptes",
			"baseStyles": {
				"position": "absolute",
				"left": "50%",
				"top": "calc(50% + 44px)",
				"transform": "translateX(-50%)",
				"whiteSpace": "nowrap",
			},
		},
	],
}


class TestSectionNumbersOnThePhone(unittest.TestCase):
	def test_a_number_laid_over_its_heading_goes_into_the_flow_on_the_phone(self):
		for section in (SECTION, WRAPPED_SECTION):
			tree = [copy.deepcopy(section)]
			self.assertEqual(layout.numbers_in_flow_on_the_phone(tree), 1)
			number = tree[0]["children"][0]
			self.assertEqual(number["mobileStyles"]["position"], "static")
			self.assertEqual(number["mobileStyles"]["width"], "100%")
			# a wide screen keeps the number where the page put it
			self.assertEqual(number["baseStyles"]["position"], "absolute")

	def test_a_faint_number_a_number_alone_and_a_written_phone_position_are_left_alone(self):
		faint = copy.deepcopy(SECTION)
		faint["children"][0]["baseStyles"]["opacity"] = "0.08"
		alone = copy.deepcopy(SECTION)
		alone["children"] = alone["children"][:1]
		written = copy.deepcopy(SECTION)
		written["children"][0]["mobileStyles"] = {"position": "absolute", "top": "-40px"}
		for section in (faint, alone, written):
			self.assertEqual(layout.numbers_in_flow_on_the_phone([section]), 0)
		self.assertEqual(written["children"][0]["mobileStyles"], {"position": "absolute", "top": "-40px"})

	def test_a_word_laid_over_a_heading_is_not_a_number(self):
		badge = copy.deepcopy(SECTION)
		badge["children"][0]["innerHTML"] = "Nouveau"
		self.assertEqual(layout.numbers_in_flow_on_the_phone([badge]), 0)


class TestCaptionsOnThePhone(unittest.TestCase):
	def test_a_caption_held_on_one_line_may_wrap_on_the_phone_centred_on_its_box(self):
		tree = [copy.deepcopy(SQUARE)]
		self.assertEqual(layout.captions_wrap_on_the_phone(tree), 1)
		caption = tree[0]["children"][1]
		self.assertEqual(
			caption["mobileStyles"], {"whiteSpace": "normal", "width": "90%", "textAlign": "center"}
		)
		self.assertEqual(caption["baseStyles"]["whiteSpace"], "nowrap")

	def test_a_caption_not_centred_only_wraps(self):
		tree = [copy.deepcopy(SQUARE)]
		caption = tree[0]["children"][1]
		caption["baseStyles"].update({"left": "24px", "transform": "none"})
		self.assertEqual(layout.captions_wrap_on_the_phone(tree), 1)
		self.assertEqual(caption["mobileStyles"], {"whiteSpace": "normal"})

	def test_an_ellipsis_a_written_phone_rule_and_a_text_in_the_flow_are_left_alone(self):
		ellipsis = copy.deepcopy(SQUARE)
		ellipsis["children"][1]["baseStyles"]["textOverflow"] = "ellipsis"
		written = copy.deepcopy(SQUARE)
		written["children"][1]["mobileStyles"] = {"whiteSpace": "nowrap", "fontSize": "0.7rem"}
		in_flow = copy.deepcopy(SQUARE)
		in_flow["children"][1]["baseStyles"]["position"] = "relative"
		for tree in (ellipsis, written, in_flow):
			self.assertEqual(layout.captions_wrap_on_the_phone([tree]), 0)
