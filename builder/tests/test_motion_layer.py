# //// Neoffice — added file (no upstream equivalent): the motion layer of the site (theme_variables.html "The motion layer", the footer's script).
"""A site's `motion_style` used to be the length of a hover. It now also decides whether the page moves, and a section moves no more than its site.
What is pinned: the stylesheet emits the movements for Calm and Brisk and none for None, only inside `prefers-reduced-motion: no-preference`, and
keeps the resting layout of a strip of words whatever the style; the recipes that move are offered, picked and described to the writer only for a
site that moves as much; the checks that read a page (the capture and the layout probe) ask the browser for reduced motion; the footer's script
is there when the site moves. No network, no model."""

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.site_ai.nora import block_format
from builder.site_ai.nora import hub_blocks as H
from builder.site_ai.nora import recipes as R
from builder.tests.test_hub_blocks import block, draw
from builder.tests.test_recipes import HANDLES


def theme_css(motion):
	from builder.hf_utils.header_footer import get_theme_css

	config = frappe.new_doc("Website Header Footer Config")
	config.token_prefix = ""
	config.motion_style = motion
	return get_theme_css(config)


def source(*parts):
	with open(frappe.get_app_path("builder", *parts), encoding="utf-8") as f:
		return f.read()


class TestTheStylesheet(unittest.TestCase):
	def test_a_site_that_does_not_move_gets_no_movement(self):
		css = theme_css("None")
		for movement in (
			"@keyframes u-reveal-in",
			"u-marquee-run",
			"animation-timeline",
			"--motion-distance",
			"is-moving",
		):
			self.assertNotIn(movement, css)

	def test_a_strip_of_words_and_a_figure_keep_their_resting_layout_whatever_the_style(self):
		for motion in ("None", "Calm", "Brisk"):
			css = theme_css(motion)
			with self.subTest(motion):
				self.assertIn(":where(.u-marquee__track) {\n\tdisplay: flex;\n\tflex-wrap: wrap;", css)
				self.assertIn(":where(.u-marquee__group)", css)
				self.assertIn(":where(.u-count) {\n\tfont-variant-numeric: tabular-nums;", css)

	def test_calm_reveals_over_forty_percent_of_the_entry_and_drifts_slowly(self):
		css = theme_css("Calm")
		self.assertIn("animation-range: entry 0% entry 40%;", css)
		self.assertIn("--marquee-speed: 45;", css)
		self.assertIn("--count-duration: 1600ms;", css)
		self.assertIn("--motion-distance: 1.5rem;", css)

	def test_brisk_is_shorter_nearer_and_faster(self):
		css = theme_css("Brisk")
		self.assertIn("animation-range: entry 0% entry 28%;", css)
		self.assertIn("--marquee-speed: 90;", css)
		self.assertIn("--count-duration: 900ms;", css)
		self.assertIn("--motion-distance: 0.875rem;", css)

	def test_the_children_of_a_group_rise_in_turn(self):
		css = theme_css("Calm")
		self.assertIn(
			":where(.u-reveal-group > :nth-child(2)) {\n\t\t\tanimation-range: entry 6% entry 46%;", css
		)
		self.assertIn(
			":where(.u-reveal-group > :nth-child(6)) {\n\t\t\tanimation-range: entry 30% entry 70%;", css
		)
		self.assertNotIn(":nth-child(7)", css)

	def test_every_movement_sits_inside_no_preference(self):
		css = theme_css("Calm")
		media = css.index("@media screen and (prefers-reduced-motion: no-preference)")
		for movement in (
			"@keyframes u-reveal-in",
			"animation: u-reveal-in",
			"animation: u-marquee-run",
			"@keyframes u-marquee-run",
		):
			self.assertGreater(css.index(movement), media, movement)

	def test_a_reveal_moves_by_translate_and_gives_the_element_back_to_its_own_styles(self):
		"""`transform` would replace a block's own (a tilted card); `both` would hold the keyframe's end instead of the block's."""
		css = theme_css("Calm")
		keyframes = css[css.index("@keyframes u-reveal-in") :]
		keyframes = keyframes[: keyframes.index("}\n\n")]
		self.assertIn("translate:", keyframes)
		self.assertNotIn("transform", keyframes)
		self.assertIn("animation: u-reveal-in linear backwards;", css)
		self.assertNotIn("u-reveal-in linear both", css)

	def test_a_strip_can_be_stopped_by_pointing_at_it_or_tabbing_into_it(self):
		css = theme_css("Calm")
		self.assertIn(".u-marquee.is-moving:hover .u-marquee__track", css)
		self.assertIn(".u-marquee.is-moving:focus-within .u-marquee__track", css)
		self.assertIn("animation-play-state: paused;", css)

	def test_the_reveal_waits_for_a_browser_that_can_drive_it_by_the_scroll(self):
		css = theme_css("Calm")
		self.assertLess(
			css.index("@supports (animation-timeline: view())"), css.index("@keyframes u-reveal-in")
		)


class TestTheFooterScript(unittest.TestCase):
	def setUp(self):
		self.footer = source("templates", "includes", "header_footer", "footer.html")

	def test_the_script_is_there_unless_the_site_does_not_move(self):
		self.assertIn('{%- if (config.motion_style or "Calm") != "None" -%}', self.footer)

	def test_it_does_nothing_for_a_visitor_who_asked_for_less_motion(self):
		self.assertIn('window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;', self.footer)

	def test_a_year_is_not_counted_and_a_printed_page_has_its_numbers(self):
		self.assertIn("figure.value >= 1900 && figure.value <= 2100", self.footer)
		self.assertIn('window.addEventListener("beforeprint"', self.footer)


class TestThePagesAreReadWithoutMotion(unittest.TestCase):
	def test_the_capture_and_the_layout_probe_ask_for_reduced_motion(self):
		"""A section caught at opacity 0 below the fold is a hole in the picture the judge reads and a text the probe takes for invisible."""
		text = source("site_ai", "inspiration", "screenshotter.py")
		self.assertEqual(2, text.count('reduced_motion="reduce"'))


def moving(motion, family="steps", name=None):
	built, why = H.accept(block(id=f"{family}.{name or motion.lower()}", motion=motion))
	assert built is not None, why
	return built


class TestASectionMovesNoMoreThanItsSite(unittest.TestCase):
	def test_the_hub_says_how_much_a_block_moves_and_the_recipe_keeps_it(self):
		self.assertEqual("Brisk", moving("Brisk").motion)
		self.assertEqual("None", moving("None").motion)

	def test_the_recipes_written_in_code_do_not_move(self):
		hub = {i for i in R.REGISTRY if H.is_hub_recipe(i)}
		self.assertEqual({"None"}, {r.motion for i, r in R.REGISTRY.items() if i not in hub})

	def test_the_ladder(self):
		still, calm, brisk = (
			R.Recipe("a.b", ("steps",), "x", None, motion=m) for m in ("None", "Calm", "Brisk")
		)
		self.assertEqual([True, True, True], [R.moves_within(still, s) for s in ("None", "Calm", "Brisk")])
		self.assertEqual([False, True, True], [R.moves_within(calm, s) for s in ("None", "Calm", "Brisk")])
		self.assertEqual([False, False, True], [R.moves_within(brisk, s) for s in ("None", "Calm", "Brisk")])
		# whoever does not say gets everything; a style nobody knows is read as the liveliest
		self.assertTrue(R.moves_within(brisk, "Wild"))

	def test_the_catalogue_offers_a_site_what_it_may_draw_and_says_which_recipes_move(self):
		calm, brisk = moving("Calm"), moving("Brisk")
		with patch.dict(R.REGISTRY, {calm.id: calm, brisk.id: brisk}):

			def offered(**kw):
				return "\n".join(R.catalogue_lines(**kw))

			self.assertNotIn(calm.id, offered(motion="None"))
			self.assertNotIn(brisk.id, offered(motion="None"))
			self.assertIn(calm.id, offered(motion="Calm"))
			self.assertNotIn(brisk.id, offered(motion="Calm"))
			everything = offered(motion="Brisk")
			self.assertIn(calm.id, everything)
			self.assertIn(brisk.id, everything)
			self.assertIn(brisk.id, offered())
			self.assertIn("moves, and rests where motion is off", everything)

	def test_the_other_recipes_are_offered_to_every_site(self):
		with patch.dict(R.REGISTRY, {}, clear=False):
			still = [i for i in R.REGISTRY if not H.is_hub_recipe(i)]
			text = "\n".join(R.catalogue_lines(motion="None"))
			for recipe_id in still:
				self.assertIn(f"    {recipe_id}:", text)

	def test_a_recipe_the_plan_named_is_left_out_for_a_site_that_moves_less(self):
		brisk = moving("Brisk", name="drift")
		section = SimpleNamespace(kind="steps", recipe=brisk.id, component="")
		with patch.dict(R.REGISTRY, {brisk.id: brisk}):
			self.assertEqual((None, False), R.pick(section, "seed", {}, "Calm"))
			self.assertEqual((brisk, False), R.pick(section, "seed", {}, "Brisk"))
			self.assertEqual((brisk, False), R.pick(section, "seed", {}))

	def test_the_other_variant_a_repeat_falls_back_on_never_moves_more_than_the_site(self):
		calm, brisk = moving("Calm", name="rise"), moving("Brisk", name="drift")
		section = SimpleNamespace(kind="steps", recipe=calm.id, component="")
		taken = {calm.id: R.MAX_REPEATS}
		with patch.dict(R.REGISTRY, {calm.id: calm, brisk.id: brisk}, clear=True):
			# on a Calm site the only variant left is the one the plan named: it stays, a Brisk one is not a way out
			self.assertEqual((calm, False), R.pick(section, "seed", taken, "Calm"))
			picked, changed = R.pick(section, "seed", taken, "Brisk")
			self.assertEqual((brisk.id, True), (picked.id, changed))

	def test_the_writer_is_told_to_keep_a_movement_only_when_a_section_has_one(self):
		calm, still = moving("Calm"), moving("None", name="rest")
		said = "u-reveal"
		with_motion = "\n".join(R.brief_lines({0: R.Use(calm, "- el: section", [])}, HANDLES, "French"))
		without = "\n".join(R.brief_lines({0: R.Use(still, "- el: section", [])}, HANDLES, "French"))
		self.assertIn(said, with_motion)
		self.assertIn("write ONE group of words", with_motion)
		self.assertNotIn(said, without)


class TestTheLinterKnowsTheWholeLayer(unittest.TestCase):
	def test_each_part_of_the_layer_is_a_motion_class(self):
		for name in (
			"u-reveal",
			"u-reveal-group",
			"u-marquee",
			"u-marquee__track",
			"u-marquee__group",
			"u-count",
		):
			tree = block()["tree"]
			tree["classes"] = [name]
			with self.subTest(name):
				errors, _ = block_format.lint(
					tree, block_id="steps.rail", kinds=["steps"], photos=1, motion="None"
				)
				self.assertTrue(any("motion is None" in e for e in errors), errors)
				errors, _ = block_format.lint(
					tree, block_id="steps.rail", kinds=["steps"], photos=1, motion="Calm"
				)
				self.assertEqual([], errors)

	def test_a_reveal_under_a_box_that_clips_is_warned_it_never_plays(self):
		"""`overflow: hidden|auto|scroll` makes a scroll container; the scroll-driven reveal follows the nearest one and that one never scrolls."""
		tree = block()["tree"]
		tree["style"] = {**tree["style"], "overflow": "hidden"}
		tree["c"][0]["classes"] = ["u-reveal"]
		_errors, warnings = block_format.lint(
			tree, block_id="steps.rail", kinds=["steps"], photos=1, motion="Calm"
		)
		self.assertTrue(any("never play" in w for w in warnings), warnings)
		tree["style"]["overflow"] = "clip"
		_errors, warnings = block_format.lint(
			tree, block_id="steps.rail", kinds=["steps"], photos=1, motion="Calm"
		)
		self.assertEqual([], warnings)


def counters_block():
	def figure():
		return {
			"el": "div",
			"name": "figure-item",
			"c": [
				{
					"el": "p",
					"name": "figure",
					"classes": ["u-count"],
					"text": "WRITE figure: one number in digits",
				},
				{"el": "p", "name": "figure-label", "text": "WRITE figure-label: what it counts"},
			],
		}

	tree = {
		"el": "section",
		"name": "counters",
		"style": {"backgroundColor": "{{ground.background}}", "padding": "7rem 0"},
		"c": [
			{
				"el": "div",
				"name": "container",
				"c": [
					{
						"el": "div",
						"name": "head",
						"classes": ["u-reveal"],
						"c": [{"el": "h2", "name": "heading", "text": "WRITE heading: 4 to 8 words"}],
					},
					{
						"el": "div",
						"name": "figures",
						"classes": ["u-reveal-group"],
						"c": [figure(), figure(), figure()],
					},
				],
			}
		],
	}
	return block(
		id="figures.counters",
		kinds=["figures"],
		photos=0,
		motion="Calm",
		look="three counting figures",
		tree=tree,
	)


def written_block(name, element="div", classes=None, children=None):
	"""A block of the page as the writer's YAML becomes it."""
	node = {"blockName": name, "element": element}
	if classes is not None:
		node["classes"] = classes
	if children:
		node["children"] = children
	return node


def written_counters(root="figures"):
	"""What the writer made of the section it was given: the root renamed, the site's own grid for the group, every movement gone."""
	items = [
		written_block(
			"figure-item", children=[written_block("figure", "p"), written_block("figure-label", "p")]
		)
		for _ in range(3)
	]
	return written_block(
		root,
		"section",
		children=[
			written_block(
				"container",
				children=[
					written_block("head", children=[written_block("heading", "h2")]),
					written_block("figures", classes=["u-grid", "u-grid--3"], children=items),
				],
			)
		],
	)


def names(blocks, name):
	return [b for b in R._walk_blocks(blocks) if b.get("blockName") == name]


class TestTheWritersDroppedMovementIsPutBack(unittest.TestCase):
	def use(self, motion="Calm"):
		built, why = H.accept(counters_block())
		assert built is not None, why
		yaml_text = draw(built, sample=None, component="")
		return R.Use(replace(built, motion=motion), yaml_text, [])

	def test_the_classes_come_back_on_the_nodes_of_the_same_name(self):
		page = [written_counters()]
		restored = R.restore_motion(page, {2: self.use()})
		self.assertEqual(["u-reveal"], names(page, "head")[0]["classes"])
		# the root of the written section is named like the group inside it: the group gets the movement, the root does not
		root = page[0]
		group = (
			names(page, "figures")[0] if names(page, "figures")[0] is not root else names(page, "figures")[1]
		)
		self.assertNotIn("classes", root)
		# the site's own grid stays, the group's movement joins it
		self.assertEqual(["u-grid", "u-grid--3", "u-reveal-group"], group["classes"])
		self.assertEqual([["u-count"]] * 3, [b["classes"] for b in names(page, "figure")])
		self.assertNotIn("classes", names(page, "figure-label")[0])
		self.assertEqual(5, len(restored))
		self.assertIn("figures.hub-counters: head + u-reveal", restored)

	def test_it_only_adds_and_a_second_pass_changes_nothing(self):
		page = [written_counters()]
		R.restore_motion(page, {0: self.use()})
		self.assertEqual([], R.restore_motion(page, {0: self.use()}))

	def test_a_section_of_another_recipe_that_shares_a_few_names_is_left_alone(self):
		other = written_block(
			"features", "section", children=[written_block("head", children=[written_block("figure", "p")])]
		)
		page = [other, written_counters(root="stats")]
		R.restore_motion(page, {0: self.use()})
		self.assertNotIn("classes", names([other], "head")[0])
		self.assertNotIn("classes", names([other], "figure")[0])
		heads = [b for b in names(page, "head") if "classes" in b]
		self.assertEqual([["u-reveal"]], [h["classes"] for h in heads])

	def test_a_section_that_no_longer_looks_like_the_recipe_gets_nothing(self):
		page = [written_block("intro", "section", children=[written_block("heading", "h2")])]
		self.assertEqual([], R.restore_motion(page, {0: self.use()}))
		self.assertNotIn("classes", page[0]["children"][0])

	def test_a_recipe_that_does_not_move_is_never_touched(self):
		still = self.use(motion="None")
		page = [written_counters()]
		self.assertEqual([], R.restore_motion(page, {0: still}))

	def test_two_uses_do_not_claim_the_same_section(self):
		page = [written_counters(root="a"), written_counters(root="b")]
		restored = R.restore_motion(page, {0: self.use(), 1: self.use()})
		self.assertEqual(10, len(restored))

	def test_a_page_with_nothing_to_restore_or_nothing_written_is_fine(self):
		self.assertEqual([], R.restore_motion([], {0: self.use()}))
		self.assertEqual([], R.restore_motion([written_counters()], {}))
		self.assertEqual([], R.restore_motion([written_counters()], None))

	def test_the_writers_page_goes_through_it_after_the_slots_are_scrubbed(self):
		text = source("site_ai", "nora", "site_builder.py")
		self.assertIn("section_recipes.restore_motion(blocks,", text)
		self.assertLess(
			text.index("section_recipes.scrub_unfilled(blocks)"),
			text.index("section_recipes.restore_motion(blocks,"),
		)


def wb(name, element="div", classes=None, children=None, styles=None):
	node = written_block(name, element, classes, children)
	if styles:
		node["baseStyles"] = styles
	return node


def section_of(
	head=None, grid_items=3, name="section", classes=None, styles=None, grid_classes=("u-grid", "u-grid--3")
):
	"""A written section as the pipeline holds it: the section, one container, the heading block, then a grid."""
	kids = []
	if head is not False:
		kids.append(head or wb("head", children=[wb("title", "h2")]))
	if grid_items:
		kids.append(
			wb(
				"cards",
				classes=list(grid_classes),
				children=[wb("card", classes=["u-card"]) for _ in range(grid_items)],
			)
		)
	return wb(name, "section", classes=classes, styles=styles, children=[wb("container", children=kids)])


def classes_of(blocks, name):
	return [b.get("classes") for b in names(blocks, name)]


class TestEverySectionRises(unittest.TestCase):
	def test_the_heading_block_and_the_grid_of_each_section_but_the_first_get_their_reveal(self):
		page = [section_of(name="first"), section_of(name="second"), section_of(name="third")]
		done = R.apply_reveals(page)
		# the first section is on the screen when the page opens: it never moves
		self.assertNotIn("classes", page[0]["children"][0]["children"][0])
		self.assertNotIn(
			"u-reveal-group", [c for b in R._walk_blocks([page[0]]) for c in b.get("classes", [])]
		)
		for section in page[1:]:
			head, cards = section["children"][0]["children"]
			self.assertEqual(["u-reveal"], head["classes"])
			self.assertEqual(["u-grid", "u-grid--3", "u-reveal-group"], cards["classes"])
		self.assertEqual(4, len(done))

	def test_a_second_pass_adds_nothing(self):
		page = [section_of(), section_of()]
		R.apply_reveals(page)
		self.assertEqual([], R.apply_reveals(page))

	def test_a_section_over_a_photograph_or_that_already_moves_is_left_alone(self):
		over = section_of(classes=["u-over-image", "u-over-image--bottom"])
		moving = section_of()
		moving["children"][0]["children"][1]["classes"].append("u-reveal-group")
		page = [section_of(), over, moving]
		self.assertEqual([], R.apply_reveals(page))

	def test_nothing_is_added_under_a_box_that_clips(self):
		for key in ("overflow", "overflowX", "overflowY"):
			boxed = section_of(styles={key: "hidden"})
			page = [section_of(), boxed]
			with self.subTest(key):
				self.assertEqual([], R.apply_reveals(page))
		# a box inside the section: what is under it is skipped, what is not under it is not
		clip = wb(
			"clip",
			styles={"overflow": "auto"},
			children=[wb("cards", classes=["u-grid"], children=[wb("a"), wb("b")])],
		)
		head = wb("head", children=[wb("title", "h2")])
		section = wb("s", "section", children=[wb("container", children=[head, clip])])
		page = [section_of(), section]
		R.apply_reveals(page)
		self.assertEqual(["u-reveal"], head["classes"])
		self.assertEqual(["u-grid"], clip["children"][0]["classes"])

	def test_a_heading_block_with_a_photograph_or_a_grid_does_not_rise_as_a_whole(self):
		with_photo = wb("head", children=[wb("title", "h2"), wb("photo", "img")])
		with_grid = wb("head", styles={"display": "grid"}, children=[wb("title", "h2"), wb("text", "p")])
		page = [
			section_of(),
			section_of(head=with_photo, grid_items=0),
			section_of(head=with_grid, grid_items=0),
		]
		self.assertEqual([], R.apply_reveals(page))

	def test_a_block_that_is_not_a_heading_block_is_not_given_the_head_reveal(self):
		cards_first = section_of(head=wb("lead", children=[wb("text", "p")]))
		page = [section_of(), cards_first]
		R.apply_reveals(page)
		self.assertNotIn("classes", cards_first["children"][0]["children"][0])
		self.assertIn("u-reveal-group", cards_first["children"][0]["children"][1]["classes"])

	def test_a_grid_of_one_and_a_grid_inside_a_grid_are_not_groups(self):
		one = section_of(grid_items=1)
		inner = wb("inner", classes=["u-grid"], children=[wb("a"), wb("b")])
		outer = wb("outer", classes=["u-grid"], children=[wb("x", children=[inner]), wb("y")])
		nested = wb(
			"n", "section", children=[wb("container", children=[wb("head", children=[wb("t", "h2")]), outer])]
		)
		page = [section_of(), one, nested]
		R.apply_reveals(page)
		self.assertNotIn("u-reveal-group", classes_of([one], "cards")[0])
		self.assertEqual(["u-grid", "u-reveal-group"], nested["children"][0]["children"][1]["classes"])
		self.assertEqual(["u-grid"], inner["classes"])

	def test_a_page_of_one_section_or_none_is_left_as_it_is(self):
		self.assertEqual([], R.apply_reveals([section_of()]))
		self.assertEqual([], R.apply_reveals([]))
		self.assertEqual([], R.apply_reveals(None))

	def test_it_runs_after_the_motion_is_restored_and_only_for_a_site_that_moves(self):
		text = source("site_ai", "nora", "site_builder.py")
		self.assertLess(
			text.index("section_recipes.restore_motion(blocks,"),
			text.index("section_recipes.apply_reveals(blocks)"),
		)
		self.assertIn('(getattr(brief, "motion_style", "") or "Calm") != "None" and page["type"] != "legal"', text)


if __name__ == "__main__":
	unittest.main()
