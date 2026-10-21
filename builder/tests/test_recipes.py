# //// Neoffice — added file (no upstream equivalent): section recipes are structures the plan proposes and the writer adapts.
"""A library of section compositions with slots for the copy and the photographs (site_ai/nora/recipes.py). They are proposals:
the plan picks one by id or leaves the section free, each family offers variants that differ in structure, and the code only
fills in when a plan ignored the field. No model is called."""

import re
import unittest
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

import yaml

from builder.site_ai.nora import recipes as R
from builder.site_ai.nora.site_plan import PlannedPage, PlannedSection, SitePlan

HANDLES = {
	"primary": "var(--t-primary)",
	"secondary": "var(--t-secondary)",
	"background": "var(--t-background)",
	"text": "var(--t-text)",
	"font-heading": "var(--t-font-heading)",
	"font-body": "var(--t-font-body)",
	"container": "var(--t-container)",
	"gutter": "var(--t-gutter)",
	"gutter-phone": "var(--t-gutter-phone)",
}
LIGHT = {"t-primary": "#7a2e1d", "t-secondary": "#d9b26f", "t-background": "#faf5ee", "t-text": "#2b1810"}
DARK_SITE = {"t-primary": "#101820", "t-secondary": "#c9a24b", "t-background": "#12161c", "t-text": "#f2efe8"}
PHOTOS = [f"/files/photo-{i}.png" for i in range(1, 7)]
FORM = "builder/templates/includes/site_form.html"


def build(recipe, palette=LIGHT, photos=PHOTOS, component=FORM, ground="plain", flip=False, sample=True):
	look = R.Look(HANDLES, palette)
	return R.render(
		recipe,
		look,
		ground,
		photos[: recipe.photos],
		"/contact",
		component,
		flip,
		sample="fr" if sample else None,
	)


def tree(recipe, **kw):
	"""The recipe as the page parser expands it, inside a root like the writer's."""
	from builder.ai.page_writer import expand_page_yaml

	text = build(recipe, **kw)
	body = "\n".join("    " + line for line in text.splitlines())
	blocks, _script = expand_page_yaml(
		"el: div\nname: body\nstyle: {display: flex, flexDirection: column}\nc:\n" + body
	)
	return blocks


def shape(node):
	"""The structure of a recipe node, without a word of copy, a colour or a url."""
	if isinstance(node, list):
		return [shape(n) for n in node]
	if not isinstance(node, dict):
		return None
	style = node.get("style") or {}
	return (
		node.get("el"),
		tuple(node.get("classes") or ()),
		style.get("display"),
		style.get("gridTemplateColumns"),
		tuple(shape(node.get("c") or [])),
	)


def walk(node):
	if isinstance(node, dict):
		yield node
		for child in node.get("children") or node.get("c") or []:
			yield from walk(child)
	elif isinstance(node, list):
		for item in node:
			yield from walk(item)


class TestTheLibrary(unittest.TestCase):
	def test_every_family_offers_variants_that_differ_in_structure(self):
		families = {}
		for r in R.REGISTRY.values():
			families.setdefault(r.family, []).append(r)
		self.assertGreaterEqual(len(families), 12)
		for family, recipes in families.items():
			self.assertGreaterEqual(len(recipes), 3, family)
			shapes = []
			for r in recipes:
				ctx = R.Ctx(
					R.Look(HANDLES, LIGHT),
					R.ground_of(R.Look(HANDLES, LIGHT), "plain"),
					PHOTOS,
					"/contact",
					FORM,
				)
				shapes.append(repr(shape(r.build(ctx))))
			self.assertEqual(len(set(shapes)), len(shapes), f"two variants of {family} share a skeleton")

	def test_the_catalogue_names_every_recipe_once(self):
		text = "\n".join(R.catalogue_lines())
		for r in R.REGISTRY.values():
			self.assertEqual(text.count(f"{r.id}:"), 1, r.id)
		self.assertIn("leave `recipe` empty", text)
		self.assertIn("starting structure the writer adapts", text)

	def test_the_variants_come_in_an_order_of_the_sites_own(self):
		def first_of_the_cta(seed):
			lines = R.catalogue_lines(seed)
			start = next(i for i, line in enumerate(lines) if line.startswith("- for kind cta"))
			return lines[start + 1].split(":")[0].strip()

		firsts = {first_of_the_cta(f"site {n}") for n in range(12)}
		self.assertGreater(len(firsts), 1, "every site read the same variant first")
		self.assertEqual(first_of_the_cta("one"), first_of_the_cta("one"))
		text = "\n".join(R.catalogue_lines("any"))
		for r in R.REGISTRY.values():
			self.assertEqual(text.count(f"{r.id}:"), 1, r.id)

	def test_a_recipe_is_the_writers_own_format_and_expands(self):
		for r in R.REGISTRY.values():
			for palette in (LIGHT, DARK_SITE):
				with self.subTest(recipe=r.id, palette=palette["t-background"]):
					blocks = tree(r, palette=palette)
					self.assertEqual(len(blocks), 1)
					body = blocks[0]
					self.assertEqual(len(body["children"]), 1, "one section per recipe")
					top = body["children"][0]
					self.assertEqual(top["element"], "section")
					self.assertEqual((top.get("baseStyles") or {}).get("width") or "100%", "100%")

	def test_no_sample_slot_is_left_once_the_copy_is_in(self):
		for r in R.REGISTRY.values():
			with self.subTest(recipe=r.id):
				self.assertEqual(R.unfilled_slots(tree(r)), [])
				self.assertNotIn("WRITE", build(r))

	def test_every_slot_names_its_role_and_a_length(self):
		for r in R.REGISTRY.values():
			text = build(r, sample=False)
			slots = re.findall(r"WRITE ([\w-]+): ([^'\"\n]*)", text)
			self.assertTrue(slots, r.id)
			for role, guidance in slots:
				self.assertTrue(guidance.strip(), f"{r.id}: slot {role} has no guidance")

	def test_the_site_s_handles_carry_the_colours_and_the_type(self):
		for r in R.REGISTRY.values():
			with self.subTest(recipe=r.id):
				text = build(r)
				self.assertNotRegex(text, r"#[0-9a-fA-F]{3,8}\b", "a literal hex colour")
				self.assertNotIn("var(--t-primary, ", text)
				self.assertIn("var(--t-font-heading)", text)

	def test_every_grid_and_flex_row_says_what_the_phone_does(self):
		for r in R.REGISTRY.values():
			with self.subTest(recipe=r.id):
				ctx = R.Ctx(
					R.Look(HANDLES, LIGHT),
					R.ground_of(R.Look(HANDLES, LIGHT), "plain"),
					PHOTOS,
					"/contact",
					FORM,
				)
				for node in walk(r.build(ctx)):
					style = node.get("style") or {}
					if style.get("display") == "grid" and "u-grid" not in (node.get("classes") or []):
						self.assertIn(
							"gridTemplateColumns",
							node.get("m_style") or {},
							f"{node.get('name')} has no phone columns",
						)
					if any(
						(child.get("style") or {}).get("position") == "absolute"
						for child in node.get("c") or []
					):
						self.assertTrue(
							node.get("m_style"),
							f"{node.get('name')}: a parent of absolute children needs a phone fallback",
						)

	def test_the_photographs_are_the_ones_given_and_as_many_as_declared(self):
		for r in R.REGISTRY.values():
			with self.subTest(recipe=r.id):
				srcs = [b["attributes"]["src"] for b in walk(tree(r)) if b.get("element") == "img"]
				self.assertEqual(len(srcs), r.photos)
				self.assertEqual(srcs, PHOTOS[: r.photos])

	def test_the_form_recipes_carry_the_component_they_were_given(self):
		for r in R.REGISTRY.values():
			text = build(r)
			if r.form:
				self.assertIn('{% include "' + FORM + '" %}', text.replace('\\"', '"'), r.id)
			else:
				self.assertNotIn("{% include", text)

	def test_the_deep_band_is_a_dark_ground_on_both_kinds_of_site(self):
		for palette in (LIGHT, DARK_SITE):
			look = R.Look(HANDLES, palette)
			deep = R.ground_of(look, "deep")
			self.assertTrue(deep.bg["backgroundColor"].startswith(("var(", "#")))
			self.assertNotEqual(deep.bg["backgroundColor"], deep.ink)

	def test_flipping_swaps_the_columns_of_a_pair(self):
		r = R.REGISTRY["two-column.framed"]
		plain, flipped = tree(r, flip=False), tree(r, flip=True)
		first = lambda b: [c.get("blockName") for c in walk(b)][4:6]  # noqa: E731
		self.assertNotEqual(first(plain), first(flipped))
		self.assertIn("7fr 5fr", build(r, flip=True))
		self.assertIn("5fr 7fr", build(r, flip=False))


def section(kind, recipe="", component="", photos=None, purpose="", layout=""):
	return PlannedSection(
		kind=kind, recipe=recipe, component=component, photos=photos or [], purpose=purpose, layout=layout
	)


def page(*sections, route="about", title="About"):
	return PlannedPage(route=route, title=title, sections=list(sections))


def uses(planned, photos=PHOTOS[:3], taken=None, seed="site"):
	made = []

	def mint(text, n):
		made.append((text, n))
		return f"https://placehold.co/1200x800/e5e7eb/9ca3af/png?text={n}"

	out = R.uses_for_page(
		planned,
		handles=HANDLES,
		palette=LIGHT,
		page_photos=list(photos),
		mint=mint,
		cta_href="/contact",
		seed=seed,
		taken=taken,
	)
	return out, made


class TestThePlanChooses(unittest.TestCase):
	def test_the_plan_s_pick_is_the_recipe_of_the_section(self):
		got, _ = uses(
			page(section("two-column", "two-column.portrait"), section("faq", "faq.centred"), section("text"))
		)
		self.assertEqual(
			{i: u.recipe.id for i, u in got.items()}, {0: "two-column.portrait", 1: "faq.centred"}
		)
		self.assertFalse(any(u.fallback for u in got.values()))

	def test_a_section_left_free_stays_free(self):
		got, _ = uses(page(section("two-column", "two-column.portrait"), section("faq"), section("figures")))
		self.assertEqual(sorted(got), [0])

	def test_a_pick_that_is_not_a_recipe_of_the_kind_is_ignored(self):
		got, _ = uses(
			page(
				section("faq", "figures.band"),
				section("two-column", "no.such.recipe"),
				section("gallery", "gallery.mosaic"),
			)
		)
		self.assertEqual({i: u.recipe.id for i, u in got.items()}, {2: "gallery.mosaic"})

	def test_a_form_recipe_needs_the_component(self):
		without, _ = uses(page(section("contact-form", "contact.split")))
		self.assertEqual(without, {})
		with_form, _ = uses(page(section("contact-form", "contact.split", component=FORM)))
		self.assertEqual(next(iter(with_form)), 0)
		self.assertIn(FORM, with_form[0].yaml)

	def test_the_same_recipe_is_not_drawn_twice_on_a_page(self):
		got, _ = uses(page(section("two-column", "two-column.framed"), section("story", "two-column.framed")))
		self.assertEqual(sorted(got), [0])

	def test_the_hero_is_left_to_the_hero_recipe(self):
		got, _ = uses(
			page(section("hero", "two-column.framed"), section("faq", "faq.side"), route="home", title="Home")
		)
		self.assertEqual(sorted(got), [1])

	def test_a_plan_that_ignored_the_field_is_filled_in_by_a_seed_of_the_site(self):
		planned = page(section("two-column"), section("faq"), section("figures"))
		a, _ = uses(planned, seed="Auberge A")
		self.assertEqual(sorted(a), [0, 1, 2])
		self.assertTrue(all(u.fallback for u in a.values()))
		picks = {tuple(uses(planned, seed=f"site {n}")[0][i].recipe.id for i in (0, 1, 2)) for n in range(12)}
		self.assertGreater(len(picks), 3, "two sites must not draw the same skeletons")

	def test_a_plan_that_named_one_recipe_is_not_filled_in(self):
		got, _ = uses(page(section("two-column", "two-column.halves"), section("faq"), section("figures")))
		self.assertEqual(sorted(got), [0])

	def test_the_fallback_spreads_the_variants_over_the_site(self):
		taken = {}
		seen = []
		for n in range(3):
			got, _ = uses(page(section("two-column"), route=f"p{n}", title=f"P{n}"), taken=taken)
			seen.append(got[0].recipe.id)
		self.assertEqual(len(set(seen)), 3)


class TestWhatTheBusinessGave(unittest.TestCase):
	NO_FIGURES = "Cabinet comptable pour PME. Un seul interlocuteur, des clôtures dans les six semaines, des tarifs annoncés d'avance."
	FIGURES = "Cabinet comptable fondé en 1998, 120 clients, clôture dans les six semaines."

	def test_a_business_that_gave_one_number_is_not_offered_a_band_of_figures(self):
		self.assertEqual(R.material_figures(self.NO_FIGURES), 1)
		self.assertGreaterEqual(R.material_figures(self.FIGURES), 3)
		self.assertIn("figures", R.withheld_families(self.NO_FIGURES))
		self.assertNotIn("figures", R.withheld_families(self.FIGURES))
		without = "\n".join(R.catalogue_lines("s", self.NO_FIGURES))
		with_ = "\n".join(R.catalogue_lines("s", self.FIGURES))
		self.assertNotIn("figures.band", without)
		self.assertIn("figures.band", with_)

	def test_quotations_are_offered_only_when_the_business_gave_some(self):
		self.assertIn("testimonials", R.withheld_families(self.FIGURES))
		self.assertNotIn(
			"testimonials", R.withheld_families("Nos clients nous écrivent : lire leurs témoignages.")
		)
		self.assertNotIn("testimonials.cards", "\n".join(R.catalogue_lines("s", self.FIGURES)))

	def test_without_material_nothing_is_withheld(self):
		self.assertEqual(R.withheld_families(None), set())
		text = "\n".join(R.catalogue_lines("s"))
		for r in R.REGISTRY.values():
			self.assertIn(f"{r.id}:", text)

	def test_a_figures_recipe_the_plan_names_anyway_is_left_a_free_section(self):
		planned = page(section("figures", "figures.band"), section("faq", "faq.side"))
		made = []
		got = R.uses_for_page(
			planned,
			handles=HANDLES,
			palette=LIGHT,
			page_photos=[],
			mint=lambda t, n: made.append(n) or "x",
			cta_href="/c",
			seed="s",
			material=self.NO_FIGURES,
		)
		self.assertEqual({i: u.recipe.id for i, u in got.items()}, {1: "faq.side"})
		given = R.uses_for_page(
			planned,
			handles=HANDLES,
			palette=LIGHT,
			page_photos=[],
			mint=lambda t, n: "x",
			cta_href="/c",
			seed="s",
			material=self.FIGURES,
		)
		self.assertEqual({i: u.recipe.id for i, u in given.items()}, {0: "figures.band", 1: "faq.side"})

	def test_the_site_material_is_what_the_business_gave(self):
		text = R.site_material(
			{
				"activity": "A",
				"differentiators": "B",
				"categories": ["C", "D"],
				"brands": ["E"],
				"site_name": "never",
			}
		)
		self.assertEqual(text, "A B C D E")

	def test_the_plan_prompt_carries_only_the_families_the_material_supports(self):
		from builder.site_ai.nora.site_plan import plan_prompt

		site = {
			"site_name": "Atelier",
			"activity": self.NO_FIGURES,
			"differentiators": "",
			"site_type": "vitrine",
			"images_on": True,
		}
		text = plan_prompt(
			site, SimpleNamespace(), [{"route": "about", "title": "About", "type": "about"}], {}, [], "French"
		)
		self.assertIn("two-column.framed", text)
		self.assertNotIn("figures.band", text)
		self.assertNotIn("testimonials.cards", text)


class TestARecipeIsNotDrawnEverywhere(unittest.TestCase):
	def drawn(self, kind, recipe, pages=4, taken=None):
		taken = taken if taken is not None else {}
		out = []
		for n in range(pages):
			got, _ = uses(page(section(kind, recipe), route=f"p{n}", title=f"P{n}"), taken=taken, seed="site")
			out.append(got[0])
		return out

	def test_a_structure_the_plan_names_on_every_page_is_varied_after_the_second(self):
		got = self.drawn("two-column", "two-column.framed")
		self.assertEqual([u.recipe.id for u in got[:2]], ["two-column.framed"] * 2)
		self.assertEqual([u.fallback for u in got], [False, False, True, True])
		for u in got[2:]:
			self.assertNotEqual(u.recipe.id, "two-column.framed")
			self.assertEqual(u.recipe.family, "two-column")

	def test_the_opening_and_the_closing_are_repeated_on_purpose(self):
		for kind, recipe in (
			("statement", "statement.centred"),
			("intro", "statement.columns"),
			("cta", "cta.band"),
		):
			got = self.drawn(kind, recipe, pages=5)
			self.assertEqual({u.recipe.id for u in got}, {recipe}, kind)
			self.assertFalse(any(u.fallback for u in got), kind)

	def test_when_every_variant_of_the_family_is_used_the_plan_s_pick_stays(self):
		taken = {r.id: 2 for r in R.REGISTRY.values() if r.family == "faq"}
		got, _ = uses(page(section("faq", "faq.side")), taken=taken)
		self.assertEqual(got[0].recipe.id, "faq.side")
		self.assertFalse(got[0].fallback)

	def test_the_variants_drawn_depend_on_the_site(self):
		def drawn_for(seed):
			taken = {}
			out = []
			for n in range(4):
				got, _ = uses(
					page(section("two-column", "two-column.framed"), route=f"p{n}", title=f"P{n}"),
					taken=taken,
					seed=seed,
				)
				out.append(got[0].recipe.id)
			return tuple(out)

		self.assertGreater(len({drawn_for(f"site {n}") for n in range(10)}), 1)


class TestThePhotographs(unittest.TestCase):
	def test_the_plan_s_photographs_come_first_then_the_page_s_then_a_placeholder(self):
		planned = page(section("gallery", "gallery.mosaic", photos=["/files/chosen.png"]))
		got, made = uses(planned, photos=["/files/a.png", "/files/b.png"])
		self.assertEqual(got[0].photos[:3], ["/files/chosen.png", "/files/a.png", "/files/b.png"])
		self.assertTrue(got[0].photos[3].startswith("https://placehold.co/"))
		self.assertEqual(len(made), 1)

	def test_a_photograph_claimed_by_a_section_is_not_handed_to_another(self):
		planned = page(
			section("two-column", "two-column.framed"),
			section("gallery", "gallery.captions", photos=["/files/a.png"]),
		)
		got, _ = uses(planned, photos=["/files/a.png", "/files/b.png", "/files/c.png", "/files/d.png"])
		self.assertEqual(got[1].photos[0], "/files/a.png")
		self.assertNotIn("/files/a.png", got[0].photos)

	def test_a_recipe_that_would_overspend_the_image_budget_is_left_out(self):
		left = []
		got = R.uses_for_page(
			page(section("gallery", "gallery.mosaic")),
			handles=HANDLES,
			palette=LIGHT,
			page_photos=[],
			mint=lambda t, n: "x",
			cta_href="/c",
			seed="s",
			budget={"left": 2},
			left_out=left,
		)
		self.assertEqual(got, {})
		self.assertEqual(left, ["gallery.mosaic"])

	def test_the_budget_is_spent_only_by_the_photographs_the_site_has_not_got(self):
		budget = {"left": 8}
		R.uses_for_page(
			page(section("two-column", "two-column.framed")),
			handles=HANDLES,
			palette=LIGHT,
			page_photos=["/files/a.png"],
			mint=lambda t, n: "x",
			cta_href="/c",
			seed="s",
			budget=budget,
		)
		self.assertEqual(budget["left"], 8)
		R.uses_for_page(
			page(section("two-column", "two-column.framed")),
			handles=HANDLES,
			palette=LIGHT,
			page_photos=[],
			mint=lambda t, n: "x",
			cta_href="/c",
			seed="s",
			budget=budget,
		)
		self.assertEqual(budget["left"], 7)

	def test_a_recipe_without_photographs_asks_for_none(self):
		got, made = uses(page(section("faq", "faq.side")), photos=[])
		self.assertEqual(got[0].photos, [])
		self.assertEqual(made, [])


class TestTheBrief(unittest.TestCase):
	def test_the_brief_gives_the_structures_and_the_freedom_to_adapt_them(self):
		got, _ = uses(page(section("two-column", "two-column.portrait"), section("faq", "faq.side")))
		lines = R.brief_lines(got, HANDLES, "French")
		text = "\n".join(lines)
		self.assertIn("section 1, 2", text)
		self.assertIn("a starting point you ADAPT", text)
		self.assertIn("never leave a `WRITE` text in the page", text)
		self.assertIn("the adaptations the plan states win", text)
		self.assertIn("Section 1 (two-column.portrait):", text)
		self.assertIn("- el: section", text)
		self.assertEqual(R.brief_lines({}, HANDLES, "French"), [])

	def test_an_opening_statement_is_told_not_to_repeat_the_page_title(self):
		for recipe_id in ("statement.centred", "statement.columns", "statement.manifesto"):
			self.assertIn(
				"never the title of the page", build(R.REGISTRY[recipe_id], sample=False), recipe_id
			)
		text = "\n".join(
			R.brief_lines({0: R.Use(R.REGISTRY["faq.side"], "- el: section", [])}, HANDLES, "French")
		)
		self.assertIn("a heading that only repeats it is removed", text)

	def test_the_structure_parses_as_the_writer_s_yaml(self):
		got, _ = uses(page(section("gallery", "gallery.mosaic"), section("pricing", "pricing.ledger")))
		for use in got.values():
			parsed = yaml.safe_load(use.yaml)
			self.assertEqual(parsed[0]["el"], "section")

	def test_the_photograph_budget_is_the_sites_to_set(self):
		self.assertEqual(R.image_budget({}), R.IMAGE_BUDGET)
		self.assertEqual(R.image_budget({"nora_recipe_images": 3}), 3)
		self.assertEqual(R.image_budget({"nora_recipe_images": "0"}), 0)
		self.assertEqual(R.image_budget({"nora_recipe_images": "many"}), R.IMAGE_BUDGET)

	def test_recipes_can_be_switched_off(self):
		self.assertTrue(R.enabled({}))
		self.assertTrue(R.enabled({"nora_section_recipes": 1}))
		self.assertFalse(R.enabled({"nora_section_recipes": 0}))
		self.assertFalse(R.enabled({"nora_section_recipes": "off"}))


class TestThePageBrief(unittest.TestCase):
	PAGE: ClassVar[dict] = {"title": "About", "route": "about", "type": "about"}

	def brief(
		self,
		planned_sections,
		photos=("/files/a.png", "/files/b.png", "/files/c.png"),
		revision=None,
		site=None,
		page=None,
	):
		site = site if site is not None else {}
		site.update(
			{
				"site_name": "Atelier Test",
				"activity": "a workshop",
				"site_type": "vitrine",
				"profile": None,
				"page_types": ["accueil", "about"],
				"plan": SitePlan(
					pages=[
						PlannedPage(
							route=(page or self.PAGE)["route"],
							title=(page or self.PAGE)["title"],
							sections=planned_sections,
						)
					]
				),
			}
		)
		from builder.site_ai.nora.site_builder import page_brief_text

		with patch("builder.site_ai.nora.site_builder.available_includes", return_value=[]):
			return page_brief_text(
				site,
				SimpleNamespace(hero_style="image", site_tone=""),
				dict(page or self.PAGE),
				HANDLES,
				"",
				"classic-centered",
				"French",
				list(photos),
				("Contact", "/contact"),
				palette=LIGHT,
				revision=revision,
			)

	def test_the_sections_with_a_recipe_start_from_its_structure_and_keep_the_plan_s_adaptations(self):
		text = self.brief(
			[
				section("two-column", "two-column.portrait", layout="reverse the columns, a deep ground"),
				section("text"),
				section("faq", "faq.side"),
			]
		)
		self.assertIn("STARTING STRUCTURES for section 1, 3", text)
		self.assertIn("starts from the recipe two-column.portrait", text)
		self.assertIn(
			"adaptations the plan decided (they win over the structure where they differ): reverse the columns, a deep ground",
			text,
		)
		self.assertIn("Section 3 (faq.side):", text)
		self.assertIn("[text]", text)  # a section left free is still described the old way

	def test_a_photograph_a_recipe_holds_is_not_offered_a_second_time(self):
		text = self.brief([section("two-column", "two-column.framed")])
		self.assertEqual(text.count("/files/a.png"), 1)
		self.assertIn("/files/b.png", text)

	def test_a_revision_rewrites_the_previous_version_and_is_not_given_the_structures_again(self):
		text = self.brief(
			[section("two-column", "two-column.framed")], revision="REVISE: the heading is too small"
		)
		self.assertNotIn("STARTING STRUCTURES", text)
		self.assertNotIn("starts from the recipe", text)

	def test_the_structures_are_drawn_once_per_page_and_kept_for_its_revisions(self):
		site = {}
		first = self.brief([section("two-column"), section("faq")], site=site)
		again = self.brief([section("two-column"), section("faq")], site=site)
		self.assertEqual(first, again)
		self.assertIn("STARTING STRUCTURES", first)

	def test_recipes_can_be_switched_off_for_the_whole_build(self):
		with patch.object(R, "enabled", return_value=False):
			text = self.brief([section("two-column", "two-column.framed")])
		self.assertNotIn("STARTING STRUCTURES", text)

	def test_a_legal_page_is_written_not_designed(self):
		text = self.brief(
			[section("two-column", "two-column.framed")],
			page={"title": "Terms", "route": "terms", "type": "legal"},
		)
		self.assertNotIn("STARTING STRUCTURES", text)


class TestThePlanPrompt(unittest.TestCase):
	def prompt(self, images_on):
		from builder.site_ai.nora.site_plan import plan_prompt

		site = {
			"site_name": "Atelier Test",
			"activity": "a workshop",
			"site_type": "vitrine",
			"images_on": images_on,
		}
		pages = [{"route": "about", "title": "About", "type": "about"}]
		return plan_prompt(site, SimpleNamespace(), pages, {}, [], "French")

	def test_the_plan_is_offered_the_recipes_and_may_leave_a_section_free(self):
		text = self.prompt(True)
		self.assertIn("SECTION RECIPES (optional)", text)
		self.assertIn("two-column.framed", text)
		self.assertIn("leave `recipe` empty", text)

	def test_a_site_that_generates_its_photographs_says_so_to_the_plan(self):
		text = self.prompt(True)
		self.assertIn("The site GENERATES a photograph for every photo slot", text)
		self.assertIn("never a plain coloured block", text)

	def test_a_site_that_does_not_keeps_the_old_line(self):
		text = self.prompt(False)
		self.assertIn("a photo slot is a plain block in the palette", text)
		self.assertNotIn("GENERATES", text)

	def test_the_plan_is_not_offered_recipes_when_they_are_switched_off(self):
		with patch.object(R, "enabled", return_value=False):
			self.assertNotIn("SECTION RECIPES", self.prompt(True))


class TestPicturesTheWriterMadeUp(unittest.TestCase):
	def blocks(self, *srcs):
		images = [
			{
				"blockId": f"i{n}",
				"element": "img",
				"blockName": "photo",
				"attributes": {"src": src, "alt": f"Alt {n}"},
			}
			for n, src in enumerate(srcs)
		]
		return [
			{
				"blockId": "root",
				"element": "div",
				"children": [{"blockId": "s", "element": "section", "children": images}],
			}
		]

	def run_(self, blocks, offered=()):
		return R.replace_invented_pictures(
			blocks, offered, lambda alt: f"https://placehold.co/1200x800/png?text={alt}"
		)

	def srcs(self, blocks):
		return [c["attributes"]["src"] for c in blocks[0]["children"][0]["children"]]

	def test_a_stock_photo_address_the_writer_remembered_goes_back_to_a_placeholder_with_its_alt(self):
		blocks = self.blocks("https://images.unsplash.com/photo-1554224155-6726b348b6f5?w=800")
		edits = self.run_(blocks)
		self.assertEqual(self.srcs(blocks), ["https://placehold.co/1200x800/png?text=Alt 0"])
		self.assertEqual(len(edits), 1)

	def test_the_files_of_the_site_the_placeholders_and_the_offered_photographs_are_kept(self):
		blocks = self.blocks(
			"/files/gen_a.png",
			"https://placehold.co/1200x800/png?text=x",
			"https://cdn.example.com/offered.jpg",
			"data:image/png;base64,AAAA",
			"/assets/builder/logo.svg",
		)
		self.assertEqual(self.run_(blocks, offered={"https://cdn.example.com/offered.jpg"}), [])
		self.assertEqual(len(self.srcs(blocks)), 5)

	def test_on_a_page_that_carries_no_photograph_the_picture_is_taken_out(self):
		blocks = self.blocks("https://picsum.photos/seed/legal-document/400/500", "/files/gen_a.png")
		edits = R.replace_invented_pictures(blocks, set(), None)
		self.assertEqual(self.srcs(blocks), ["/files/gen_a.png"])
		self.assertEqual(len(edits), 1)

	def test_a_site_that_has_spent_its_photographs_has_the_picture_taken_out(self):
		blocks = self.blocks(
			"https://picsum.photos/seed/a/400/500", "https://picsum.photos/seed/b/400/500", "/files/gen_a.png"
		)
		left = {"n": 1}

		def make(alt):
			if left["n"] <= 0:
				return None
			left["n"] -= 1
			return "https://placehold.co/1200x800/png?text=x"

		edits = R.replace_invented_pictures(blocks, set(), make)
		self.assertEqual(self.srcs(blocks), ["https://placehold.co/1200x800/png?text=x", "/files/gen_a.png"])
		self.assertEqual(len(edits), 2)

	def test_an_image_without_a_source_is_left_alone(self):
		blocks = self.blocks("")
		self.assertEqual(self.run_(blocks), [])


class TestThePlanUsesOnlyThePhotographsItWasGiven(unittest.TestCase):
	def test_a_photograph_address_the_plan_made_up_is_taken_out_of_its_sections(self):
		from builder.site_ai.nora.site_plan import keep_offered_photos

		plan = SitePlan(
			pages=[
				PlannedPage(
					route="about",
					title="About",
					sections=[
						section(
							"two-column", photos=["https://picsum.photos/seed/x/800/1000", "/files/mine.png"]
						),
						section("gallery", photos=["https://images.unsplash.com/photo-1"]),
					],
				)
			]
		)
		removed = keep_offered_photos(plan, [{"url": "/files/mine.png"}])
		self.assertEqual(removed, 2)
		self.assertEqual([s.photos for s in plan.pages[0].sections], [["/files/mine.png"], []])

	def test_with_no_photograph_offered_every_section_loses_its_addresses(self):
		from builder.site_ai.nora.site_plan import keep_offered_photos

		plan = SitePlan(
			pages=[
				PlannedPage(
					route="a",
					title="A",
					sections=[section("gallery", photos=["https://picsum.photos/seed/y/1/1"])],
				)
			]
		)
		self.assertEqual(keep_offered_photos(plan, []), 1)


class TestARecipeLeftNull(unittest.TestCase):
	def test_a_null_recipe_is_a_free_section_not_a_failed_plan(self):
		self.assertEqual(PlannedSection(kind="text", recipe=None).recipe, "")
		self.assertEqual(PlannedSection(kind="text").recipe, "")
		self.assertEqual(PlannedSection(kind="faq", recipe=" faq.side ").recipe, "faq.side")


class TestASlotLeftInAPage(unittest.TestCase):
	def blocks(self):
		slotted = {
			"blockId": "a",
			"element": "h2",
			"blockName": "heading",
			"innerHTML": "WRITE heading: 3 to 7 words",
		}
		fine = {"blockId": "b", "element": "p", "blockName": "text", "innerHTML": "A real sentence."}
		image = {
			"blockId": "c",
			"element": "img",
			"blockName": "photo",
			"attributes": {"src": "/files/a.png", "alt": "WRITE alt: what it shows"},
		}
		return [
			{
				"blockId": "root",
				"element": "div",
				"children": [{"blockId": "s", "element": "section", "children": [slotted, fine, image]}],
			}
		]

	def test_a_slot_that_stayed_is_found_with_its_role(self):
		self.assertCountEqual(R.unfilled_slots(self.blocks()), ["heading (heading)", "photo (alt)"])

	def test_a_slot_that_is_still_there_at_the_end_is_removed(self):
		blocks = self.blocks()
		self.assertEqual(R.scrub_unfilled(blocks), 2)
		section_ = blocks[0]["children"][0]
		self.assertEqual([c["blockName"] for c in section_["children"]], ["text", "photo"])
		self.assertEqual(section_["children"][1]["attributes"]["alt"], "")
		self.assertEqual(R.unfilled_slots(blocks), [])

	def test_a_page_without_slots_is_left_alone(self):
		blocks = [
			{
				"blockId": "root",
				"element": "div",
				"children": [{"blockId": "p", "element": "p", "innerHTML": "Hello"}],
			}
		]
		self.assertEqual(R.unfilled_slots(blocks), [])
		self.assertEqual(R.scrub_unfilled(blocks), 0)


class TestTheLayoutPassesAcceptThem(unittest.TestCase):
	def test_the_mechanical_passes_run_on_every_recipe(self):
		from builder.site_ai.nora.layout import (
			fit_grid_placements,
			fit_phone_widths,
			fluid_tracks,
			wrap_phone_rows,
		)

		for r in R.REGISTRY.values():
			with self.subTest(recipe=r.id):
				blocks = tree(r)
				fit_grid_placements(blocks)
				fit_phone_widths(blocks)
				fluid_tracks(blocks)
				wrap_phone_rows(blocks)
				self.assertEqual(R.unfilled_slots(blocks), [])


if __name__ == "__main__":
	unittest.main()
