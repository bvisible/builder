# //// Neoffice — added file (no upstream equivalent): the blocks of the Builder Hub offered to the site plan as section recipes.
"""The hub keeps a library of sections (site_ai/nora/hub_blocks.py draws on it). What is pinned here: a block becomes a recipe of the kind written in
code, drawn with the site's own handles and the ground it asks for, and the page parser reads what it draws; the catalogue is kept so that a hub that
does not answer never stops a build; what the hub sends is linted again and a block that fails is left out; and nothing changes for a site that
did not switch `nora_hub_blocks` on. No network, no model."""

import unittest
from unittest.mock import MagicMock, patch

from builder.site_ai.nora import block_format
from builder.site_ai.nora import hub_blocks as H
from builder.site_ai.nora import recipes as R
from builder.tests.test_recipes import HANDLES, LIGHT, PHOTOS

FORM = "builder/templates/includes/site_form.html"


def block(**over):
	"""A block as the hub serves it: a heading and a line on a plain ground, then a deep band holding the button."""
	data = {
		"id": "steps.rail",
		"title": "Steps on a rail",
		"family": "steps",
		"kinds": ["steps"],
		"look": "the heading on the left, the steps on a rail on the right",
		"photos": 1,
		"form": False,
		"ground": "plain",
		"motion": "None",
		"version": 1,
		"tree": {
			"el": "section",
			"name": "rail",
			"style": {"backgroundColor": "{{ground.background}}", "width": "100%", "padding": "6rem 0"},
			"m_style": {"padding": "4rem 0"},
			"c": [
				{
					"el": "h2",
					"name": "heading",
					"style": {
						"fontFamily": "{{font_heading}}",
						"color": "{{ground.ink}}",
						"maxWidth": "{{container}}",
					},
					"text": "WRITE heading: 3 to 7 words, one accent word",
				},
				{
					"el": "img",
					"name": "photo",
					"classes": ["u-media"],
					"attrs": {"src": "{{photo.0}}", "alt": "WRITE alt: a scene"},
				},
				{
					"el": "div",
					"name": "band",
					"ground": "deep",
					"style": {"backgroundColor": "{{ground.background}}", "padding": "2rem"},
					"c": [
						{
							"el": "p",
							"name": "line",
							"style": {"color": "{{ground.muted}}"},
							"text": "WRITE text: one sentence",
						},
						{
							"el": "a",
							"name": "button",
							"classes": ["u-btn", "u-btn--secondary"],
							"attrs": {"href": "{{cta_href}}"},
							"text": "WRITE button: 2 to 4 words",
						},
					],
				},
			],
		},
	}
	data.update(over)
	return data


def folding_tree():
	"""A FAQ block: the questions fold (`details` with a `summary`), in the site's own accordion (`u-faq`)."""

	def item():
		return {
			"el": "details",
			"name": "question",
			"c": [
				{
					"el": "summary",
					"name": "question-text",
					"text": "WRITE question: a real question, 5 to 12 words",
				},
				{"el": "p", "name": "answer", "text": "WRITE answer: an answer of 25 to 45 words"},
			],
		}

	return {
		"el": "section",
		"name": "faq",
		"style": {"backgroundColor": "{{ground.background}}", "width": "100%", "padding": "6rem 0"},
		"c": [{"el": "div", "name": "faq", "classes": ["u-faq"], "c": [item(), item(), item()]}],
	}


def catalogue_of(*blocks, fmt=1):
	return {"format": fmt, "blocks": list(blocks)}


def draw(recipe, ground="plain", photos=None, component=FORM, sample=None):
	look = R.Look(HANDLES, LIGHT)
	return R.render(
		recipe,
		look,
		ground,
		photos if photos is not None else PHOTOS[: recipe.photos],
		"/contact",
		component,
		False,
		sample=sample,
	)


class Cache:
	"""frappe.cache with a dictionary behind it."""

	def __init__(self, **kept):
		self.kept = dict(kept)
		self.set_calls = []

	def get_value(self, key):
		return self.kept.get(key)

	def set_value(self, key, value, expires_in_sec=None):
		self.kept[key] = value
		self.set_calls.append((key, expires_in_sec))


class TestTheLookTheHubPreviewsWith(unittest.TestCase):
	"""The hub draws a preview of a block with its own copy of the formulas of `Look` (builder_hub/block_preview.py). The same numbers are pinned
	there (test_block_preview): if `Look` changes, this test fails and the hub's formulas are to follow."""

	def test_the_colours_a_site_derives_from_its_four_colours(self):
		look = R.Look(
			{"primary": "#7a2e1d", "secondary": "#d9b26f", "background": "#faf5ee", "text": "#2b1810"}, {}
		)
		self.assertEqual("rgba(43, 24, 16, 0.72)", look.muted)
		self.assertEqual("rgba(43, 24, 16, 0.16)", look.hair)
		self.assertEqual("rgba(122, 46, 29, 0.08)", look.tint)
		self.assertEqual("rgba(217, 178, 111, 0.35)", look.frame)
		self.assertEqual("#7a2e1d", look.deep)
		self.assertEqual("#faf5ee", look.ink_on_deep)
		self.assertEqual("rgba(250, 245, 238, 0.8)", look.deep_muted)
		self.assertEqual("rgba(250, 245, 238, 0.25)", look.deep_hair)


class TestDrawn(unittest.TestCase):
	def setUp(self):
		self.recipe, why = H.accept(block())
		self.assertEqual("", why)

	def test_a_block_is_a_recipe_named_after_its_family_with_a_hub_variant(self):
		self.assertEqual("steps.hub-rail", self.recipe.id)
		self.assertEqual("steps", self.recipe.family)
		self.assertEqual(("steps",), self.recipe.kinds)
		self.assertEqual(1, self.recipe.photos)
		self.assertIn("steps on a rail", self.recipe.look)

	def test_the_handles_of_the_site_fill_the_tokens(self):
		text = draw(self.recipe)
		self.assertNotIn("{{", text)
		self.assertIn("var(--t-font-heading)", text)
		self.assertIn("var(--t-container)", text)
		self.assertIn("href: /contact", text.replace("'", ""))
		self.assertIn(PHOTOS[0], text)

	def test_a_slot_is_left_for_the_writer(self):
		text = draw(self.recipe)
		self.assertEqual(4, text.count("WRITE "))

	def test_the_alt_of_a_photograph_is_always_the_generators_own_guidance(self):
		asked = block()
		asked["tree"]["c"][1]["attrs"]["alt"] = "WRITE alt: a portrait of the owner smiling at the till"
		recipe, why = H.accept(asked)
		self.assertEqual("", why)
		text = draw(recipe)
		self.assertIn("never a person (no face, nobody at work", text)
		self.assertNotIn("the owner smiling", text)

	def test_a_node_with_a_ground_draws_itself_and_what_is_under_it_on_that_ground(self):
		look = R.Look(HANDLES, LIGHT)
		node = H.instantiate(block()["tree"], R.Ctx(look, R.ground_of(look, "plain"), PHOTOS[:1], "/contact"))
		plain, band = node["style"]["backgroundColor"], node["c"][2]["style"]["backgroundColor"]
		self.assertEqual(look.background, plain)
		self.assertEqual(look.deep, band)
		self.assertNotEqual(plain, band)
		self.assertEqual(look.deep_muted, node["c"][2]["c"][0]["style"]["color"])

	def test_the_page_parser_reads_what_a_block_draws(self):
		from builder.ai.page_writer import expand_page_yaml

		text = draw(self.recipe)
		body = "\n".join("    " + line for line in text.splitlines())
		blocks, _script = expand_page_yaml(
			"el: div\nname: body\nstyle: {display: flex, flexDirection: column}\nc:\n" + body
		)
		self.assertTrue(blocks)
		self.assertEqual("rail", blocks[0]["children"][0]["blockName"])

	def test_a_form_block_carries_the_include_of_the_component(self):
		with_form = block(id="contact.card", kinds=["contact-form"], photos=0, form=True)
		with_form["tree"] = {
			"el": "section",
			"name": "card",
			"c": [
				{"el": "h2", "text": "WRITE heading: 3 to 7 words"},
				{"el": "div", "name": "form", "text": "{{include_component}}"},
			],
		}
		recipe, why = H.accept(with_form)
		self.assertEqual("", why)
		self.assertTrue(recipe.form)
		self.assertIn('{% include "' + FORM + '" %}', draw(recipe, component=FORM).replace("'", ""))


class TestWhatIsLeftOut(unittest.TestCase):
	def test_a_block_that_does_not_lint_is_left_out_with_the_first_reason(self):
		bad = block()
		bad["tree"]["c"][0]["style"]["color"] = "{{brand_pink}}"
		recipe, why = H.accept(bad)
		self.assertIsNone(recipe)
		self.assertIn("brand_pink", why)

	def test_a_block_for_no_kind_of_the_plan_is_left_out(self):
		recipe, why = H.accept(block(kinds=["parallax-wonder"]))
		self.assertIsNone(recipe)
		self.assertIn("kinds is empty", why)

	def test_the_kinds_the_plan_does_not_know_are_dropped_and_the_rest_kept(self):
		recipe, _ = H.accept(block(kinds=["steps", "parallax-wonder"]))
		self.assertEqual(("steps",), recipe.kinds)

	def test_a_block_with_no_look_for_the_plan_is_left_out(self):
		recipe, why = H.accept(block(look="  "))
		self.assertIsNone(recipe)
		self.assertIn("no look", why)

	def test_something_that_is_not_a_block_is_left_out(self):
		for junk in (None, "steps.rail", 3, ["x"]):
			with self.subTest(junk):
				self.assertIsNone(H.accept(junk)[0])

	def test_a_script_in_a_tree_never_gets_through(self):
		bad = block()
		bad["tree"]["c"].append({"el": "script", "text": "WRITE text: x"})
		self.assertIsNone(H.accept(bad)[0])
		bad = block()
		bad["tree"]["c"][2]["c"][1]["attrs"]["href"] = "javascript:alert(1)"
		self.assertIsNone(H.accept(bad)[0])


class TestTheCatalogueIsKept(unittest.TestCase):
	def run_catalogue(self, cache, fetched):
		with patch.object(H.frappe, "cache", cache), patch.object(H, "fetch", return_value=fetched) as fetch:
			return H.catalogue(), fetch

	def test_a_fresh_catalogue_is_used_without_asking_the_hub(self):
		fresh = catalogue_of(block())
		(body, source), fetch = self.run_catalogue(Cache(**{H.FRESH_KEY: fresh}), None)
		self.assertEqual((fresh, "fresh"), (body, source))
		fetch.assert_not_called()

	def test_an_answer_of_the_hub_is_kept_fresh_for_an_hour_and_as_the_last_good_for_a_month(self):
		cache = Cache()
		(_body, source), _ = self.run_catalogue(cache, catalogue_of(block()))
		self.assertEqual("hub", source)
		self.assertEqual({(H.FRESH_KEY, H.FRESH_FOR), (H.KEPT_KEY, H.KEPT_FOR)}, set(cache.set_calls))

	def test_a_hub_that_does_not_answer_gives_the_last_good_catalogue(self):
		kept = catalogue_of(block())
		(body, source), _ = self.run_catalogue(Cache(**{H.KEPT_KEY: kept}), None)
		self.assertEqual((kept, "kept"), (body, source))

	def test_a_hub_that_never_answered_gives_nothing(self):
		(body, source), _ = self.run_catalogue(Cache(), None)
		self.assertEqual((None, "none"), (body, source))

	def test_a_cache_that_fails_does_not_fail_the_build(self):
		broken = MagicMock()
		broken.get_value.side_effect = RuntimeError("redis is down")
		broken.set_value.side_effect = RuntimeError("redis is down")
		(_body, source), _ = self.run_catalogue(broken, catalogue_of(block()))
		self.assertEqual("hub", source)

	def test_fetch_asks_the_get_block_catalog_of_the_hub_with_a_short_timeout(self):
		response = MagicMock()
		response.json.return_value = {"message": catalogue_of(block())}
		with (
			patch("requests.get", return_value=response) as get,
			patch("builder.api.hub_url", return_value="https://hub.example"),
		):
			body = H.fetch()
		self.assertEqual(1, len(body["blocks"]))
		self.assertEqual(
			"https://hub.example/api/method/builder_hub.api.get_block_catalog", get.call_args.args[0]
		)
		self.assertEqual(H.TIMEOUT, get.call_args.kwargs["timeout"])

	def test_fetch_is_none_for_an_error_a_timeout_or_an_answer_that_is_not_a_catalogue(self):
		with patch("builder.api.hub_url", return_value="https://hub.example"):
			with patch("requests.get", side_effect=OSError("timeout")):
				self.assertIsNone(H.fetch())
			bad_status = MagicMock()
			bad_status.raise_for_status.side_effect = RuntimeError("HTTP 500")
			with patch("requests.get", return_value=bad_status):
				self.assertIsNone(H.fetch())
			for message in (None, [], {"blocks": "no"}, "text"):
				response = MagicMock()
				response.json.return_value = {"message": message}
				with patch("requests.get", return_value=response):
					self.assertIsNone(H.fetch(), message)


class TestTheRegistry(unittest.TestCase):
	def tearDown(self):
		H.forget()

	def sync(self, body, source="hub", on=True):
		conf = {"nora_hub_blocks": 1} if on else {}
		with patch.object(H, "catalogue", return_value=(body, source)):
			return H.sync_registry(conf)

	def test_it_is_off_unless_the_site_asks(self):
		for conf, expected in (
			({}, False),
			({"nora_hub_blocks": 0}, False),
			({"nora_hub_blocks": "off"}, False),
			({"nora_hub_blocks": 1}, True),
			({"nora_hub_blocks": "true"}, True),
		):
			with self.subTest(conf):
				self.assertEqual(expected, H.enabled(conf))

	def test_a_site_that_did_not_ask_gets_no_hub_recipe_and_does_not_reach_the_hub(self):
		with patch.object(H, "catalogue") as catalogue:
			result = H.sync_registry({})
		catalogue.assert_not_called()
		self.assertEqual("off", result["source"])
		self.assertFalse([i for i in R.REGISTRY if H.is_hub_recipe(i)])

	def test_the_blocks_of_the_catalogue_join_the_registry_and_nothing_else_changes(self):
		before = set(R.REGISTRY)
		result = self.sync(catalogue_of(block()))
		self.assertEqual(["steps.hub-rail"], result["ids"])
		self.assertEqual(before | {"steps.hub-rail"}, set(R.REGISTRY))

	def test_a_second_sync_does_not_duplicate_and_a_site_that_switched_off_loses_them(self):
		self.sync(catalogue_of(block()))
		self.sync(catalogue_of(block()))
		self.assertEqual(1, len([i for i in R.REGISTRY if H.is_hub_recipe(i)]))
		self.sync(catalogue_of(block()), on=False)
		self.assertFalse([i for i in R.REGISTRY if H.is_hub_recipe(i)])

	def test_a_block_withdrawn_from_the_hub_leaves_the_registry_at_the_next_build(self):
		self.sync(catalogue_of(block(), block(id="steps.zigzag")))
		self.assertEqual(2, len([i for i in R.REGISTRY if H.is_hub_recipe(i)]))
		self.sync(catalogue_of(block()))
		self.assertEqual({"steps.hub-rail"}, {i for i in R.REGISTRY if H.is_hub_recipe(i)})

	def test_a_hub_that_gave_nothing_leaves_no_hub_recipe_and_the_code_recipes_stay(self):
		code = {i for i in R.REGISTRY if not H.is_hub_recipe(i)}
		result = self.sync(None, source="none")
		self.assertEqual([], result["ids"])
		self.assertEqual(code, set(R.REGISTRY))

	def test_a_catalogue_at_format_one_is_still_read_by_a_generator_that_knows_two(self):
		for fmt in block_format.READABLE:
			with self.subTest(fmt):
				self.assertEqual(["steps.hub-rail"], self.sync(catalogue_of(block(), fmt=fmt))["ids"])

	def test_a_block_with_folding_questions_is_read_and_drawn_as_details_the_page_parser_knows(self):
		from builder.ai.page_writer import expand_page_yaml

		faq = block(id="faq.fold", kinds=["faq"], photos=0, tree=folding_tree())
		self.assertEqual(["faq.hub-fold"], self.sync(catalogue_of(faq))["ids"])
		text = draw(R.REGISTRY["faq.hub-fold"])
		body = "\n".join("    " + line for line in text.splitlines())
		blocks, _script = expand_page_yaml("el: div\nname: body\nc:\n" + body)
		found = [b["element"] for b in R._in_order(blocks)]
		self.assertEqual(3, found.count("details"))
		self.assertEqual(3, found.count("summary"))

	def test_a_format_the_site_does_not_know_is_not_guessed(self):
		result = self.sync(catalogue_of(block(), fmt=99))
		self.assertEqual([], result["ids"])
		self.assertIn("format 99", result["source"])

	def test_a_bad_block_is_left_out_and_said_while_the_good_ones_stay(self):
		bad = block(id="steps.broken")
		bad["tree"]["el"] = "div"
		result = self.sync(catalogue_of(bad, block()))
		self.assertEqual(["steps.hub-rail"], result["ids"])
		self.assertEqual(1, len(result["left_out"]))
		self.assertTrue(result["left_out"][0].startswith("steps.broken:"))

	def test_two_blocks_of_one_id_make_one_recipe(self):
		result = self.sync(catalogue_of(block(), block(title="Another")))
		self.assertEqual(["steps.hub-rail"], result["ids"])
		self.assertIn("already a recipe", result["left_out"][0])

	def test_a_block_never_takes_the_id_of_a_recipe_written_in_code(self):
		self.assertFalse([i for i in R.REGISTRY if H.is_hub_recipe(i)])
		self.assertTrue(
			all(H.HUB_MARK in H.recipe_id(f"{family}.variant") for family in ("steps", "cta", "two-column"))
		)


class TestTheRestOfTheGeneratorSeesThemAsRecipes(unittest.TestCase):
	def setUp(self):
		H.forget()
		with patch.object(H, "catalogue", return_value=(catalogue_of(block()), "hub")):
			H.sync_registry({"nora_hub_blocks": 1})

	def tearDown(self):
		H.forget()

	def test_the_plan_reads_them_in_its_catalogue_in_the_family_they_belong_to(self):
		lines = "\n".join(R.catalogue_lines(seed="a site"))
		self.assertIn("steps.hub-rail: the heading on the left", lines)
		self.assertIn("1 photograph", lines.split("steps.hub-rail:")[1].splitlines()[0])

	def test_the_plan_can_name_one_and_the_page_gets_its_structure(self):
		section = type(
			"S",
			(),
			{
				"kind": "steps",
				"recipe": "steps.hub-rail",
				"component": "",
				"photos": [],
				"purpose": "how it goes",
			},
		)()
		picked, changed = R.pick(section, "seed", {})
		self.assertEqual("steps.hub-rail", picked.id)
		self.assertFalse(changed)

	def test_a_block_for_another_kind_is_not_taken_for_a_section_of_this_one(self):
		section = type("S", (), {"kind": "cta", "recipe": "steps.hub-rail", "component": "", "photos": []})()
		self.assertEqual((None, False), R.pick(section, "seed", {}))

	def test_a_slot_a_block_leaves_in_a_page_is_removed_like_any_other(self):
		blocks = [{"element": "div", "children": [{"element": "p", "innerHTML": "WRITE heading: x"}]}]
		self.assertEqual(1, R.scrub_unfilled(blocks))


if __name__ == "__main__":
	unittest.main()
