# //// Neoffice — added file (no upstream equivalent): the example sites of the hub, shown when a site starts, and what the build makes of them.
"""Jérémy, 14.11: « quand on commence un site, on montre les sites démos que Nora modifie après ? il faudrait pouvoir voir », then, asked
whether Nora takes an example's look or the example itself: « il faut poser la question ». The playbook shows the hub's complete sites with
their picture and a link, asks how to start from the one chosen, and the build takes its look or lays its pages and writes them again.
"""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from builder.site_ai.nora import examples

GARAGE = {
	"name": "garage",
	"title": "Garage : atelier indépendant",
	"description": "Un garage indépendant.",
	"showcase": True,
	"sector": "automotive",
	"thumbnail": "https://hub.example/builder_assets/garage/home/thumb.webp",
	"translations": {"en": {"title": "Garage: independent workshop"}},
	"header_footer": {"primary_color": "#1f2a36", "heading_font": "Bebas Neue"},
	"pages": [
		{
			"name": "page-home",
			"page_title": "Accueil",
			"route": "templates/garage/accueil",
			"live_url": "https://hub.example/templates/garage/accueil",
			"preview": "https://hub.example/home.webp",
		},
		{
			"name": "page-book",
			"page_title": "Prendre rendez-vous",
			"route": "templates/garage/prendre_rendez_vous",
			"live_url": "https://hub.example/templates/garage/prendre_rendez_vous",
			"preview": "https://hub.example/book.webp",
		},
	],
}
UPSTREAM = {
	"name": "mono",
	"title": "Mono",
	"showcase": False,
	"pages": [{"name": "mono_home", "page_title": "Work"}],
}
ROWS = [
	{"name": "qtg-primary", "type": "Color", "value": "#1f2a36"},
	{"name": "qtg-background", "type": "Color", "value": "#1f2a36"},
	{"name": "qtg-text", "type": "Color", "value": "#f5f5f5"},
	{"name": "qtg-font-heading", "type": "Font", "value": "Bebas Neue"},
	{"name": "qtg-font-body", "type": "Font", "value": "DM Sans"},
	{"name": "qtg-gutter", "type": "Dimension", "value": "64px"},
]
HOME_BLOCKS = [
	{
		"element": "div",
		"blockName": "body",
		"children": [
			{"element": "nav", "blockName": "navbar", "children": []},
			{
				"element": "section",
				"blockName": "hero",
				"baseStyles": {"background": "var(--qtg-background)"},
				"children": [
					{"element": "p", "blockId": "k", "innerHTML": "Atelier toutes marques"},
					{
						"element": "h1",
						"blockId": "h",
						"innerHTML": "La précision <em>avant tout</em>",
						"baseStyles": {"color": "var(--qtg-text)"},
					},
					{
						"element": "img",
						"blockId": "i",
						"attributes": {
							"src": "https://hub.example/builder_assets/garage/hero.jpg",
							"alt": "Un mécanicien",
						},
					},
					{
						"element": "a",
						"blockId": "b",
						"innerHTML": "Prendre rendez-vous",
						"attributes": {"href": "prendre_rendez_vous"},
					},
				],
			},
			{"element": "div", "blockName": "section-divider", "children": []},
			{
				"element": "section",
				"blockName": "figures",
				"children": [{"element": "p", "blockId": "f", "innerHTML": "48h"}],
			},
			{
				"element": "section",
				"blockName": "form",
				"children": [
					{
						"element": "div",
						"blockId": "x",
						"innerHTML": '{% include "builder/templates/includes/site_form.html" %}',
					}
				],
			},
		],
	}
]
BUNDLE = {
	"page": {"blocks": json.dumps(HOME_BLOCKS), "route": "templates/garage/accueil"},
	"components": [],
	"variables": ROWS,
}


def hub(method, **params):
	if method == "get_catalog":
		return [GARAGE, UPSTREAM]
	if method == "get_template_bundle":
		return json.loads(json.dumps(BUNDLE))
	raise AssertionError(method)


class HubCase(unittest.TestCase):
	def setUp(self):
		patches = [
			mock.patch.object(examples, "_hub_get", side_effect=hub),
			mock.patch.object(
				examples,
				"_cache",
				return_value=SimpleNamespace(get_value=lambda key: None, set_value=lambda *a, **k: None),
			),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)


class TestTheExamplesAreShown(HubCase):
	def test_only_the_complete_sites_are_examples(self):
		self.assertEqual([e["name"] for e in examples.examples("fr")], ["garage"])

	def test_each_example_comes_with_its_picture_and_a_link_that_opens_it(self):
		line = examples.playbook_line("fr")
		self.assertIn("image https://hub.example/builder_assets/garage/home/thumb.webp", line)
		self.assertIn("link https://hub.example/templates/garage/accueil", line)
		self.assertIn("in markdown", line)
		self.assertIn("« Sans exemple »", line)

	def test_the_person_is_asked_how_to_start_from_it(self):
		line = examples.playbook_line("fr")
		self.assertIn("« Reprendre son allure »", line)
		self.assertIn("« Le reprendre tel quel »", line)
		self.assertIn("example_use='look' or 'as_is'", line)
		self.assertIn("step 3 is NOT asked", line)

	def test_the_title_is_in_the_persons_language(self):
		self.assertEqual(examples.examples("en")[0]["title"], "Garage: independent workshop")

	def test_a_hub_that_does_not_answer_shows_no_example(self):
		with mock.patch.object(examples, "_hub_get", side_effect=OSError("down")):
			self.assertEqual(examples.playbook_line("fr"), "")

	def test_the_chosen_example_is_found_by_its_name_its_title_or_its_picture(self):
		for value in (
			"garage",
			"Garage : atelier indépendant",
			"https://hub.example/builder_assets/garage/home/thumb.webp",
		):
			self.assertEqual(examples.find(value)["name"], "garage", value)
		self.assertIsNone(examples.find("mono"))
		self.assertIsNone(examples.find(""))


class TestTheExamplesLook(HubCase):
	def test_its_tokens_are_read_with_their_prefix(self):
		prefix, rows = examples.tokens(examples.find("garage"))
		self.assertEqual(prefix, "qtg")
		self.assertIn({"suffix": "font-heading", "type": "Font", "value": "Bebas Neue"}, rows)

	def test_its_colours_type_and_ground_are_the_sites(self):
		look = examples.look(examples.find("garage"))
		self.assertEqual(
			(look["primary"], look["heading_font"], look["body_font"]), ("#1f2a36", "Bebas Neue", "DM Sans")
		)
		self.assertEqual(look["background_mode"], "dark")
		light = examples.look(examples.find("garage"), [{"suffix": "background", "value": "#faf8f4"}])
		self.assertEqual(light["background_mode"], "light")

	def test_its_tokens_become_the_sites_own(self):
		written = []
		names = examples.adopt_tokens(
			examples.tokens(examples.find("garage"))[1], "abc", "Atelier", lambda *a: written.append(a)
		)
		self.assertIn("abc-font-heading", names)
		self.assertIn(("abc-gutter", "Atelier Gutter", "Dimension", "64px", "Atelier"), written)

	def test_the_plan_is_told_its_sections_in_order(self):
		lines = examples.plan_lines(examples.find("garage"))
		self.assertIn("« Accueil »: hero (1 photograph), figures, form", lines)
		self.assertIn("never the example's", lines)


class TestAnExamplePageLaid(HubCase):
	def laid(self):
		example = examples.find("garage")
		pages = [
			{"title": "Accueil", "route": "home"},
			{"title": "Prendre rendez-vous", "route": "prendre-rendez-vous"},
		]
		return examples.lay_example(BUNDLE, "qtg", "abc", examples.route_map(example, pages))

	def test_it_wears_the_sites_tokens_its_form_and_its_addresses(self):
		text = json.dumps(self.laid())
		self.assertNotIn("--qtg-", text)
		self.assertIn("var(--abc-background)", text)
		self.assertIn("contact_form.html", text)
		self.assertNotIn("site_form.html", text)
		self.assertIn('"href": "/prendre-rendez-vous"', text)
		self.assertNotIn('"navbar"', text)

	def test_the_page_of_the_site_finds_its_example_page(self):
		example = examples.find("garage")
		self.assertEqual(
			examples.matching_page(example, {"title": "Prendre rendez-vous", "route": "rdv"})["name"],
			"page-book",
		)
		self.assertEqual(
			examples.matching_page(example, {"title": "Home", "route": "home"})["name"], "page-home"
		)
		self.assertIsNone(examples.matching_page(example, {"title": "Blog", "route": "blog"}))


def answer(texts=(), pictures=()):
	return examples.Rewrite(
		texts=[examples.NewText(id=i, text=t) for i, t in texts],
		pictures=[examples.NewPicture(**p) for p in pictures],
	)


PHOTOS = [{"url": "/files/atelier.jpg", "shows": "the workshop"}]


class TestItsWordsWrittenAgain(HubCase):
	def rewrite(self, *answers):
		blocks = examples.lay_example(BUNDLE, "qtg", "abc", {})
		calls = iter(answers)
		done = examples.rewrite(
			blocks,
			{"title": "Accueil"},
			"- name: Atelier Sève",
			"French",
			"m",
			PHOTOS,
			call=lambda prompt, system: next(calls),
		)
		return blocks, done

	def test_every_word_of_the_example_is_replaced(self):
		blocks, done = self.rewrite(
			answer(
				[
					("t0", "Ébénisterie sur mesure"),
					("t1", "Le bois <em>suisse</em>"),
					("t2", "Nous écrire"),
					("t3", "Sur mesure"),
				],
				[{"id": "p0", "photo": "/files/atelier.jpg"}],
			)
		)
		text = json.dumps(blocks, ensure_ascii=False)
		for words in (
			"Atelier toutes marques",
			"La précision",
			"48h",
			"Un mécanicien",
			"hub.example/builder_assets",
		):
			self.assertNotIn(words, text)
		self.assertIn("Le bois <em>suisse</em>", text)
		self.assertIn('"src": "/files/atelier.jpg"', text)
		self.assertIn('"alt": "the workshop"', text)
		self.assertIn(
			'{% include \\"builder/templates/includes/contact_form.html\\" %}',
			text,
			"a live component is never rewritten",
		)
		self.assertEqual((done["texts"], done["photos"], done["made"]), (4, 1, 0))

	def test_markup_the_example_did_not_have_is_written_as_text(self):
		blocks, _done = self.rewrite(
			answer([("t0", "<script>x</script>Atelier"), ("t1", "a"), ("t2", "b"), ("t3", "c")], [])
		)
		self.assertEqual(
			blocks[0]["children"][0]["children"][0]["innerHTML"], "&lt;script&gt;x&lt;/script&gt;Atelier"
		)

	def test_a_text_left_out_is_asked_again_then_emptied_never_kept(self):
		blocks, done = self.rewrite(
			answer([("t1", "Le bois"), ("t2", "Nous écrire"), ("t3", "Sur mesure")], []), answer([], [])
		)
		self.assertEqual(blocks[0]["children"][0]["children"][0]["innerHTML"], "")
		self.assertEqual(done["emptied"], ["Atelier toutes marques"])

	def test_the_examples_own_words_and_a_number_nobody_gave_are_asked_again(self):
		"""The model kept « La précision avant tout » and wrote « 100% » (14.11, the garage's home written for a cabinetmaker)."""
		blocks, done = self.rewrite(
			answer(
				[
					("t0", "Atelier Sève"),
					("t1", "La précision <em>avant tout</em>"),
					("t2", "Nous écrire"),
					("t3", "100%"),
				]
			),
			answer([("t1", "Le bois <em>suisse</em>"), ("t3", "Sur mesure")]),
		)
		text = json.dumps(blocks, ensure_ascii=False)
		self.assertNotIn("La précision", text)
		self.assertNotIn("100", text)
		self.assertIn("Le bois <em>suisse</em>", text)
		self.assertEqual(done["emptied"], [])

	def test_a_number_given_twice_is_dropped_and_a_numbering_kept(self):
		from builder.site_ai.nora.examples import suspect

		self.assertEqual(suspect("/01", "/01", ""), "")
		self.assertEqual(suspect("Fondé en 1987", "Depuis 2003", "- founded in 1987"), "")
		self.assertTrue(suspect("Depuis 2003", "Depuis 2003", ""))
		blocks, done = self.rewrite(
			answer([("t0", "Atelier"), ("t1", "Le bois"), ("t2", "Nous écrire"), ("t3", "100% bois")]),
			answer([("t3", "100% bois")]),
		)
		self.assertEqual(blocks[0]["children"][2]["children"][0]["innerHTML"], "bois")  # hero, divider, figures
		self.assertTrue(done["emptied"][0].startswith("number dropped"))

	def test_a_brace_the_answer_left_at_the_end_is_dropped(self):
		from builder.site_ai.nora.examples import safe_text

		self.assertEqual(safe_text("une proposition adaptée    }", "x"), "une proposition adaptée")

	def test_a_picture_no_photograph_fits_is_made_again(self):
		blocks, done = self.rewrite(
			answer(
				[("t0", "a"), ("t1", "b"), ("t2", "c"), ("t3", "d")],
				[{"id": "p0", "shows": "an oak workbench"}],
			)
		)
		image = blocks[0]["children"][0]["children"][2]["attributes"]
		self.assertTrue(image["src"].startswith("https://placehold.co/"))
		self.assertEqual(image["alt"], "an oak workbench")
		self.assertEqual(done["made"], 1)

	def test_no_answer_lays_nothing(self):
		blocks, done = examples.page_from_example(
			BUNDLE, "qtg", "abc", {}, {"title": "Accueil"}, "", "French", "m", [], call=lambda p, s: None
		)
		self.assertEqual((blocks, done), ([], None))


class TestTheChoiceReachesTheBuild(HubCase):
	def test_the_example_picked_on_the_card_is_read_from_the_answer(self):
		from builder.site_ai.nora import tools

		reply = "Garage : atelier indépendant: Accueil, Prendre rendez-vous\n(chosen image: https://hub.example/builder_assets/garage/home/thumb.webp)"
		with mock.patch.object(tools.frappe, "get_all", return_value=[SimpleNamespace(content=reply)]):
			self.assertEqual(tools.answers_of_the_conversation("s1").get("example_site"), "garage")

	def test_the_tool_takes_the_example_and_how(self):
		from builder.site_ai.nora import tools

		properties = tools.generate_site.parameters["properties"]
		self.assertEqual(properties["example_use"]["enum"], ["look", "as_is"])
		self.assertIn("example_site", properties)

	def test_the_plan_is_told_the_example(self):
		from builder.site_ai.nora.site_plan import plan_prompt

		prompt = plan_prompt(
			{"site_name": "X", "example_plan": "EXAMPLE SITE the client chose"},
			SimpleNamespace(),
			[],
			{},
			[],
			"French",
		)
		self.assertIn("EXAMPLE SITE the client chose", prompt)


class TestThePlaybookOrder(unittest.TestCase):
	def test_the_examples_come_after_the_business_and_before_the_pages(self):
		from builder.site_ai.nora import prompts

		with mock.patch.object(prompts, "example_line", return_value="1c. EXAMPLES"):
			text = prompts.site_playbook("page-1")
		self.assertLess(text.index("1. The business."), text.index("1c. EXAMPLES"))
		self.assertLess(text.index("1c. EXAMPLES"), text.index("2. The pages."))
