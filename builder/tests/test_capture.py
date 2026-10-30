# //// Neoffice — added file (no upstream equivalent): a section of a written page kept as a block of the hub (site_ai/nora/capture.py).
"""What is pinned: a section written for a site becomes a block that carries nothing of that site (no word, no photograph, no colour, no
token of its own, no name of the business), still lints, takes the ground the plan gives it, and is refused with the reason when it
cannot be a block; the same section is always the same block (so that the hub keeps one draft of it); a page gives its sections after
the first. Sections come from the real recipes, as the writer receives them. No Frappe, no network, no model."""

import json
import re
import unittest
from unittest.mock import MagicMock, patch

from builder.site_ai.nora import block_format, capture
from builder.site_ai.nora import recipes as R
from builder.tests.test_recipes import HANDLES, LIGHT, PHOTOS

NAMES = {
	"el": "element",
	"name": "blockName",
	"style": "baseStyles",
	"t_style": "tabletStyles",
	"m_style": "mobileStyles",
	"classes": "classes",
}


def to_block(node):
	"""A recipe's node as the page parser would make a Builder block of it."""
	block = {
		"element": node["el"],
		"blockName": node.get("name", ""),
		"children": [to_block(c) for c in node.get("c") or []],
	}
	for src, dst in (
		("style", "baseStyles"),
		("t_style", "tabletStyles"),
		("m_style", "mobileStyles"),
		("classes", "classes"),
	):
		if node.get(src):
			block[dst] = json.loads(json.dumps(node[src]))
	attrs = node.get("attrs") or {}
	block["attributes"] = {k: v for k, v in attrs.items() if k in {"src", "alt", "href"}}
	block["customAttributes"] = {k: v for k, v in attrs.items() if k not in {"src", "alt", "href"}}
	if node.get("text") is not None:
		block["innerHTML"] = node["text"]
	return block


def section(recipe_id, ground="plain", palette=LIGHT, photos=PHOTOS):
	"""The written section of a recipe: its structure, its handles, sample copy in place of the slots."""
	recipe = R.REGISTRY[recipe_id]
	look = R.Look(HANDLES, palette)
	ctx = R.Ctx(look, R.ground_of(look, ground), photos[: recipe.photos], "/contact", "")
	node = recipe.build(ctx)
	R.fill_node(node, "fr")
	return to_block(node)


def captured(recipe_id, **kw):
	forbidden = kw.pop("forbidden", ())
	kind = kw.pop("kind", None)
	return capture.capture_section(
		section(recipe_id, **kw),
		handles=capture.handles_of("t"),
		palette=LIGHT,
		kind=kind,
		forbidden=forbidden,
	)


def nodes(tree):
	yield tree
	for child in tree.get("c") or []:
		yield from nodes(child)


class TestASectionBecomesABlockThatCarriesNothingOfItsSite(unittest.TestCase):
	def setUp(self):
		self.block = captured("features.ruled")
		self.dump = json.dumps(self.block["tree"])

	def test_it_lints_and_is_the_block_the_hub_takes(self):
		tree = self.block["tree"]
		errors, _warnings = block_format.lint(
			tree,
			block_id=self.block["id"],
			kinds=self.block["kinds"],
			photos=self.block["photos"],
			form=False,
			motion=self.block["motion"],
		)
		self.assertEqual([], errors)
		self.assertEqual("section", tree["el"])
		self.assertTrue(re.fullmatch(r"features\.cap-[0-9a-f]{8}", self.block["id"]), self.block["id"])
		self.assertEqual(["feature-grid"], self.block["kinds"])

	def test_not_one_word_of_the_original_is_kept(self):
		for text in (n.get("text") for n in nodes(self.block["tree"]) if n.get("text")):
			self.assertTrue(block_format.SLOT.match(text), text)
		sample = R.SAMPLES["fr"]["text"]
		self.assertNotIn(sample.split()[0] + " " + sample.split()[1], self.dump)

	def test_nothing_of_the_site_is_left_a_token_stands_for_every_handle(self):
		self.assertNotIn("var(--t-", self.dump)
		self.assertNotIn("#", self.dump.replace("{{", "").replace("}}", ""))
		self.assertIn("{{font_heading}}", self.dump)
		self.assertIn("{{container}}", self.dump)

	def test_what_depends_on_the_ground_is_written_for_whatever_ground_the_plan_gives(self):
		self.assertIn("{{ground.background}}", self.dump)
		self.assertIn("{{ground.ink}}", self.dump)
		self.assertIn("{{ground.accent}}", self.dump)
		self.assertEqual("plain", self.block["ground"])

	def test_the_line_for_the_plan_says_the_structure_and_nothing_else(self):
		look = self.block["look"]
		self.assertIn("a heading", look)
		self.assertIn("items side by side", look)
		self.assertLess(len(look), 401)
		for word in re.findall(r"[a-zà-ÿ]{5,}", R.SAMPLES["fr"]["text"].lower()):
			self.assertNotIn(word, look.lower())

	def test_the_same_section_is_always_the_same_block_and_another_one_is_another(self):
		self.assertEqual(self.block["id"], captured("features.ruled")["id"])
		self.assertNotEqual(self.block["id"], captured("features.list")["id"])

	def test_a_section_on_a_deep_band_is_a_deep_block(self):
		block = captured("figures.band", ground="deep")
		dump = json.dumps(block["tree"])
		self.assertEqual("deep", block["ground"])
		self.assertIn("{{ground.background}}", dump)
		self.assertIn("{{ground.ink}}", dump)
		self.assertNotIn("{{deep}}", dump)
		self.assertNotIn("{{ink_on_deep}}", dump)

	def test_a_tinted_section_is_a_tinted_block(self):
		self.assertEqual("tint", captured("figures.statements", ground="tint")["ground"])


class TestWhatTheWordsBecome(unittest.TestCase):
	def test_each_text_asks_for_what_it_was_in_the_length_it_had(self):
		slots = [n["text"] for n in nodes(captured("features.ruled")["tree"]) if n.get("text")]
		roles = {block_format.SLOT.match(t).group(1) for t in slots}
		self.assertIn("heading", roles)
		self.assertTrue(
			roles
			<= {
				"heading",
				"item-title",
				"item-text",
				"lead",
				"label",
				"text",
				"caption",
				"numeral",
				"figure",
				"button",
			},
			roles,
		)
		for text in slots:
			if block_format.SLOT.match(text).group(1) == "heading":
				self.assertRegex(text, r"WRITE heading: \d+ to \d+ words")

	def test_a_heading_with_an_accent_word_says_so(self):
		words = capture.Words()
		node = {"el": "h2"}
		self.assertTrue(
			words.slot(node, "Une maison <em>de pain</em> depuis longtemps").endswith(", one accent word")
		)
		self.assertNotIn("accent", capture.Words().slot(node, "Une maison de pain depuis longtemps"))

	def test_the_first_heading_is_the_heading_and_the_next_are_item_titles(self):
		words = capture.Words()
		self.assertTrue(words.slot({"el": "h2"}, "Un titre de section").startswith("WRITE heading:"))
		self.assertTrue(words.slot({"el": "h3"}, "Un titre").startswith("WRITE item-title:"))

	def test_a_button_a_numeral_a_label_a_figure_and_a_lead(self):
		words = capture.Words()
		self.assertTrue(
			words.slot({"el": "a", "classes": ["u-btn", "u-btn--primary"]}, "Nous écrire").startswith(
				"WRITE button: 1 to 3 words"
			)
		)
		self.assertTrue(words.slot({"el": "p"}, "02").startswith("WRITE numeral:"))
		self.assertTrue(
			words.slot({"el": "p", "style": {"textTransform": "uppercase"}}, "Notre maison").startswith(
				"WRITE label:"
			)
		)
		self.assertTrue(
			words.slot({"el": "p", "style": {"fontSize": "4rem"}}, "1 200+").startswith("WRITE figure:")
		)
		self.assertTrue(
			words.slot({"el": "p"}, " ".join(["mot"] * 30)).startswith("WRITE lead: 21 to 39 words")
		)
		self.assertTrue(words.slot({"el": "p"}, " ".join(["mot"] * 30)).startswith("WRITE item-text:"))


class TestPhotographsLinksAndNames(unittest.TestCase):
	def base(self, **over):
		def img(src):
			return {
				"element": "img",
				"attributes": {"src": src, "alt": "Le pain du four"},
				"customAttributes": {},
				"baseStyles": {"width": "100%"},
			}

		kids = over.pop("kids", [img("/files/a.jpg"), img("/files/b.jpg"), img("/files/a.jpg")])
		block = {
			"element": "section",
			"blockName": "gallery",
			"baseStyles": {"backgroundColor": "var(--t-background)", "padding": "4rem 0"},
			"children": [
				{
					"element": "h2",
					"blockName": "heading",
					"innerHTML": "Notre galerie du four",
					"baseStyles": {},
				},
				*kids,
			],
		}
		block.update(over)
		return block

	def cap(self, block, **kw):
		return capture.capture_section(block, handles=capture.handles_of("t"), palette=LIGHT, **kw)

	def test_each_distinct_photograph_is_a_numbered_slot_and_its_alt_is_the_generators_guidance(self):
		block = self.cap(self.base())
		imgs = [n for n in nodes(block["tree"]) if n["el"] == "img"]
		self.assertEqual(["{{photo.0}}", "{{photo.1}}", "{{photo.0}}"], [n["attrs"]["src"] for n in imgs])
		self.assertEqual(2, block["photos"])
		self.assertEqual({R.slot("alt", R.ALT_GUIDANCE)}, {n["attrs"]["alt"] for n in imgs})

	def test_a_link_goes_where_the_site_sends_its_visitors_unless_it_is_an_anchor(self):
		links = [
			{
				"element": "a",
				"innerHTML": "Voir",
				"attributes": {"href": "/notre-maison"},
				"customAttributes": {},
				"classes": ["u-btn"],
			},
			{"element": "a", "innerHTML": "Ici", "attributes": {"href": "#carte"}, "customAttributes": {}},
			{
				"element": "a",
				"innerHTML": "Appeler",
				"attributes": {"href": "tel:+41000000"},
				"customAttributes": {},
			},
		]
		block = self.cap(self.base(kids=links))
		self.assertEqual(
			["{{cta_href}}", "#carte", "{{cta_href}}"],
			[n["attrs"]["href"] for n in nodes(block["tree"]) if n["el"] == "a"],
		)

	def test_a_name_that_says_the_business_is_dropped_and_a_plain_one_stays(self):
		block = self.cap(self.base(blockName="gallery-du-four"), forbidden=["Four", "Maison"])
		self.assertNotIn("name", block["tree"])
		self.assertEqual("heading", block["tree"]["c"][0]["name"])

	def test_a_title_or_a_label_of_an_attribute_is_words_and_is_not_kept(self):
		link = {
			"element": "a",
			"innerHTML": "Voir",
			"attributes": {"href": "#x", "title": "Voir la boulangerie"},
			"customAttributes": {"aria-label": "Voir", "role": "link"},
		}
		attrs = next(n for n in nodes(self.cap(self.base(kids=[link]))["tree"]) if n["el"] == "a")["attrs"]
		self.assertEqual({"href": "#x", "role": "link"}, attrs)

	def test_the_classes_of_the_design_system_stay_the_others_go_and_the_reveals_are_the_sites(self):
		kid = {
			"element": "div",
			"classes": ["u-card", "nora-divider", "u-reveal", "u-reveal-group", "u-grid--3"],
			"children": [],
			"innerHTML": "Un mot",
		}
		classes = next(n for n in nodes(self.cap(self.base(kids=[kid]))["tree"]) if "classes" in n)["classes"]
		self.assertEqual(["u-card", "u-grid--3"], classes)

	def test_a_figure_that_counts_or_a_strip_that_drifts_makes_a_block_that_moves(self):
		counts = {
			"element": "p",
			"classes": ["u-count"],
			"innerHTML": "400",
			"baseStyles": {"fontSize": "4rem"},
		}
		strip = {
			"element": "div",
			"classes": ["u-marquee"],
			"children": [
				{
					"element": "div",
					"classes": ["u-marquee__track"],
					"children": [{"element": "p", "innerHTML": "Pain"}],
				}
			],
		}
		self.assertEqual("Calm", self.cap(self.base(kids=[counts]))["motion"])
		self.assertEqual("Brisk", self.cap(self.base(kids=[counts, strip]))["motion"])
		self.assertEqual("None", self.cap(self.base())["motion"])


class TestWhatCannotBeABlock(unittest.TestCase):
	def refused(self, kid, **over):
		block = {
			"element": "section",
			"blockName": "x",
			"baseStyles": {},
			"children": [{"element": "h2", "innerHTML": "Titre du bloc"}, kid],
		}
		block.update(over)
		with self.assertRaises(capture.Refused) as raised:
			capture.capture_section(block, handles=capture.handles_of("t"), palette=LIGHT)
		return str(raised.exception)

	def test_an_icon_a_component_a_script_a_binding_and_a_repeater(self):
		self.assertIn("icon", self.refused({"element": "div", "customAttributes": {"data-lucide": "star"}}))
		self.assertIn("component", self.refused({"element": "div", "extendedFromComponent": "card"}))
		self.assertIn("script", self.refused({"element": "div", "clientScript": {"js": "x()"}}))
		self.assertIn("binding", self.refused({"element": "div", "dynamicValues": [{"key": "a"}]}))
		self.assertIn("repeater", self.refused({"element": "div", "isRepeaterBlock": True}))

	def test_a_live_include_and_a_tag_the_format_does_not_know(self):
		self.assertIn(
			"live component",
			self.refused(
				{"element": "div", "innerHTML": '{% include "builder/templates/includes/site_form.html" %}'}
			),
		)
		self.assertIn("`button`", self.refused({"element": "button", "innerHTML": "Envoyer"}))

	def test_a_photograph_set_as_a_background_and_too_many_colours_of_its_own(self):
		self.assertIn(
			"background",
			self.refused({"element": "div", "baseStyles": {"backgroundImage": "url(/files/a.jpg)"}}),
		)
		loud = {
			"element": "div",
			"baseStyles": {
				"color": "#111",
				"backgroundColor": "#222",
				"borderColor": "#333",
				"outlineColor": "#444",
			},
			"innerHTML": "Un mot",
		}
		self.assertIn("colours", self.refused(loud))

	def test_a_block_that_is_not_a_section(self):
		block = {"element": "div", "children": [{"element": "h2", "innerHTML": "Titre"}]}
		with self.assertRaises(capture.Refused):
			capture.capture_section(block, handles=capture.handles_of("t"), palette=LIGHT)


class TestAPage(unittest.TestCase):
	def page(self):
		return [
			{
				"element": "div",
				"blockName": "body",
				"children": [section("statement.centred"), section("features.ruled"), section("cta.band")],
			}
		]

	def test_the_first_section_stays_with_its_site_and_the_others_are_captured(self):
		made, why = capture.capture_page(self.page(), palette=LIGHT)
		self.assertEqual(2, len(made) + len(why))
		self.assertTrue(made)
		for block in made:
			self.assertNotIn("var(--t-", json.dumps(block["tree"]))

	def test_a_page_that_does_not_use_the_tokens_of_a_site_gives_nothing(self):
		made, why = capture.capture_page([{"element": "section", "children": []}])
		self.assertEqual([], made)
		self.assertTrue(why)

	def test_the_kind_is_the_one_the_name_of_the_section_says(self):
		self.assertEqual("feature-grid", capture.kind_of({"blockName": "features-ruled"}))
		self.assertEqual("figures", capture.kind_of({"blockName": "figures-band"}))
		self.assertEqual("cta", capture.kind_of({"blockName": "cta-band"}))
		self.assertEqual("text", capture.kind_of({"blockName": "something-else"}))
		self.assertEqual("steps", capture.kind_of({"blockName": "something-else"}, "steps"))

	def test_the_family_is_the_one_the_recipes_of_the_kind_go_by(self):
		self.assertEqual("features", capture.family_of("feature-grid"))
		self.assertEqual("cta", capture.family_of("cta"))
		self.assertEqual("no-recipe-yet", capture.family_of("no-recipe-yet"))


class TestSendingADraft(unittest.TestCase):
	def sent(self, status, conf=None, body=None):
		response = MagicMock(status_code=status)
		response.json.return_value = {"message": body or {}}
		conf = (
			{
				"template_hub_url": "https://hub.example",
				"hub_publish_api_key": "k",
				"hub_publish_api_secret": "s",
			}
			if conf is None
			else conf
		)
		with patch("frappe.conf", conf, create=True), patch("requests.post", return_value=response) as post:
			return capture.push_block({"id": "cta.cap-12345678", "tree": {}}), post

	def test_a_block_goes_to_the_hubs_publish_block_with_the_sites_publisher_key(self):
		line, post = self.sent(200, body={"block": "cta.cap-12345678", "version": 1})
		self.assertEqual("draft cta.cap-12345678 v1", line)
		url = post.call_args.args[0]
		self.assertEqual("https://hub.example/api/method/builder_hub.publish.publish_block", url)
		self.assertEqual("token k:s", post.call_args.kwargs["headers"]["Authorization"])

	def test_a_published_block_is_not_overwritten_and_it_is_said(self):
		line, _post = self.sent(403)
		self.assertIn("already published", line)

	def test_a_site_with_no_hub_sends_nothing(self):
		line, post = self.sent(200, conf={})
		self.assertIn("no hub", line)
		post.assert_not_called()

	def test_what_is_said_never_holds_the_key(self):
		line, _post = self.sent(500)
		self.assertNotIn("k:s", line)


class TestKeepingWhatTheJudgeAccepted(unittest.TestCase):
	def pages(self):
		return [
			{"name": "p1", "title": "Accueil"},
			{"name": "p2", "title": "Notre maison"},
			{"name": "p3", "title": "Contact"},
		]

	def reports(self):
		good = {"professional": True, "gate": [], "issues": []}
		return [
			{"name": "p1", **good},
			{"name": "p2", "professional": False, "gate": [], "issues": []},
			{"name": "p3", **good},
		]

	def keep(self, **over):
		args = {"hidden": (), "held": [], "site_name": "Maison du Four", "activity": "Boulangerie à Sion"}
		args.update(over)
		sent = {}

		def stored(name, push=False, forbidden=()):
			sent[name] = sorted(forbidden)
			return {"blocks": [f"cta.cap-{name}"], "refused": [], "sent": {f"cta.cap-{name}": "draft v1"}}

		with patch.object(capture, "capture_stored_page", side_effect=stored):
			lines = capture.keep_accepted(self.pages(), self.reports(), **args)
		return lines, sent

	def test_only_the_pages_the_judge_called_professional_are_kept(self):
		lines, sent = self.keep()
		self.assertEqual(["p1", "p3"], sorted(sent))
		self.assertEqual(["cta.cap-p1: draft v1", "cta.cap-p3: draft v1"], lines)

	def test_a_held_or_hidden_page_is_never_kept(self):
		_lines, sent = self.keep(held=[{"name": "p1"}], hidden={"p3"})
		self.assertEqual({}, sent)

	def test_the_words_of_the_business_are_given_so_that_no_name_carries_them(self):
		_lines, sent = self.keep()
		self.assertEqual(["Boulangerie", "Four", "Maison", "Sion"], sent["p1"])

	def test_a_page_that_cannot_be_read_is_said_and_never_stops_the_others(self):
		def stored(name, push=False, forbidden=()):
			if name == "p1":
				raise ValueError("boom")
			return {"blocks": [], "refused": [], "sent": {}}

		with patch.object(capture, "capture_stored_page", side_effect=stored):
			lines = capture.keep_accepted(self.pages(), self.reports(), site_name="x", activity="y")
		self.assertEqual(["Accueil: not kept (ValueError)"], lines)

	def test_it_is_off_unless_the_site_asks(self):
		self.assertFalse(capture.enabled({}))
		self.assertFalse(capture.enabled({"nora_capture_blocks": 0}))
		self.assertTrue(capture.enabled({"nora_capture_blocks": 1}))
		self.assertTrue(capture.enabled({"nora_capture_blocks": "on"}))

	def test_the_build_asks_after_the_final_look_and_before_its_summary(self):
		from builder.tests.test_motion_layer import source

		text = source("site_ai", "nora", "site_builder.py")
		self.assertLess(
			text.index("capture.keep_accepted("),
			text.index("lines += visual_check.summary_lines(reviews, revised, held)"),
		)


if __name__ == "__main__":
	unittest.main()
