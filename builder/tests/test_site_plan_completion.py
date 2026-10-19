# //// Neoffice — added file (no upstream equivalent): the pages a site plan left out are planned in small batches.
"""The local model's answer is cut at 4 096 tokens: asked to plan a site of seven pages it planned two (eight
sections, against thirty-two for the strong model), or ended in a half-written section that failed the whole
plan; the pages without a plan were written thin (2026-10-20). A cut answer now keeps what is whole, and the pages
a plan lacks are asked for on their own. No model is called."""

import json
import unittest
from types import SimpleNamespace

from builder.site_ai.nora import site_plan as sp

PAGES = [
	{"route": "home", "title": "Accueil", "type": "accueil"},
	{"route": "menu", "title": "La carte", "type": "content"},
	{"route": "groups", "title": "Groupes", "type": "content"},
	{"route": "about", "title": "L'auberge", "type": "content"},
	{"route": "book", "title": "Réserver", "type": "content"},
]
SITE = {"site_name": "Auberge", "activity": "Restaurant", "site_type": "vitrine", "sells": False}
BRIEF = SimpleNamespace()
WHOLE = ("hero", "cards", "cta")


def planned(route, *kinds, photos=()):
	sections = [
		sp.PlannedSection(kind=k, photos=list(photos) if i == 0 else []) for i, k in enumerate(kinds or WHOLE)
	]
	return sp.PlannedPage(route=route, title=route.title(), sections=sections)


def first_plan(*routes):
	return sp.SitePlan(
		direction="warm and rustic",
		signature_move="a 2px accent rule above every h2",
		interior_top="a two-column intro",
		rhythm="5rem padding",
		pages=[planned(r) for r in routes],
	)


class FakeLLM:
	def __init__(self, *answers):
		self.answers = list(answers)
		self.prompts = []

	def generate_structured(self, prompt, schema, system_prompt, images, max_tokens):
		self.prompts.append(prompt)
		answer = self.answers.pop(0) if self.answers else sp.PlannedPages()
		if isinstance(answer, Exception):
			raise answer
		return answer


def complete(llm, plan, photos=()):
	return sp.complete_plan(llm, plan, SITE, BRIEF, PAGES, {}, list(photos), "fr")


class TestACutAnswerKeepsWhatIsWhole(unittest.TestCase):
	def test_a_half_written_last_section_is_dropped(self):
		# what json repair made of the local model's plan, cut in the middle of a section: a list where a section goes
		cut = {
			"direction": "d",
			"pages": [
				{
					"route": "home",
					"title": "Accueil",
					"sections": [{"kind": "hero"}, {"kind": "cards"}, ["kind"]],
				},
				{
					"route": "menu",
					"title": "Carte",
					"sections": [{"kind": "intro"}, {"kind": "no-such-kind"}],
				},
				["route"],
				"menu",
			],
		}
		plan = sp.SitePlan.model_validate(cut)
		self.assertEqual([p.route for p in plan.pages], ["home", "menu"])
		self.assertEqual([s.kind for s in plan.pages[0].sections], ["hero", "cards"])
		self.assertEqual([s.kind for s in plan.pages[1].sections], ["intro"])

	def test_a_plan_that_is_not_cut_is_unchanged(self):
		whole = first_plan("home", "menu")
		again = sp.SitePlan.model_validate_json(whole.model_dump_json())
		self.assertEqual(again, whole)

	def test_the_pages_asked_on_their_own_are_read_the_same_way(self):
		got = sp.PlannedPages.model_validate(
			{"pages": [{"route": "book", "title": "B", "sections": [{"kind": "cta"}, 7]}, None]}
		)
		self.assertEqual([len(p.sections) for p in got.pages], [1])

	def test_a_json_text_cut_in_a_section_is_read(self):
		text = json.dumps(first_plan("home").model_dump())
		cut = text[: text.rindex('"kind"')] + '"kind'
		try:
			import json_repair
		except ImportError:
			self.skipTest("json_repair is not installed here")
		plan = sp.SitePlan.model_validate(json_repair.loads(cut))
		self.assertEqual(plan.pages[0].route, "home")
		self.assertLess(len(plan.pages[0].sections), 3)


class TestWhichPagesAreMissing(unittest.TestCase):
	def test_a_page_with_no_section_is_missing(self):
		plan = first_plan("home", "menu")
		plan.pages.append(sp.PlannedPage(route="groups", title="Groupes", sections=[]))
		self.assertEqual([p["route"] for p in sp.missing_routes(plan, PAGES)], ["groups", "about", "book"])

	def test_a_page_the_plan_stopped_in_the_middle_of_is_missing(self):
		plan = first_plan("home", "menu", "groups", "about")
		plan.pages.append(planned("book", "intro", "cards"))
		self.assertEqual([p["route"] for p in sp.missing_routes(plan, PAGES)], ["book"])

	def test_a_legal_page_is_whole_with_its_text(self):
		plan = first_plan("home")
		plan.pages.append(planned("terms", "intro", "legal-text"))
		legal = [{"route": "terms", "title": "T", "type": "legal"}]
		self.assertEqual(sp.missing_routes(plan, legal), [])

	def test_a_complete_plan_misses_nothing(self):
		plan = first_plan("home", "menu", "groups", "about", "book")
		self.assertEqual(sp.missing_routes(plan, PAGES), [])


class TestCompletePlan(unittest.TestCase):
	def test_a_complete_plan_asks_nothing(self):
		llm = FakeLLM()
		plan = first_plan("home", "menu", "groups", "about", "book")
		self.assertIs(complete(llm, plan), plan)
		self.assertEqual(llm.prompts, [])

	def test_the_missing_pages_are_asked_for_in_one_batch(self):
		llm = FakeLLM(sp.PlannedPages(pages=[planned("groups"), planned("about"), planned("book")]))
		plan = complete(llm, first_plan("home", "menu"))
		self.assertEqual([p.route for p in plan.pages], ["home", "menu", "groups", "about", "book"])
		self.assertEqual(len(llm.prompts), 1)

	def test_more_pages_than_a_batch_take_two_calls(self):
		llm = FakeLLM(
			sp.PlannedPages(pages=[planned("menu"), planned("groups"), planned("about")]),
			sp.PlannedPages(pages=[planned("book")]),
		)
		plan = complete(llm, first_plan("home"))
		self.assertEqual(sorted(p.route for p in plan.pages), ["about", "book", "groups", "home", "menu"])
		self.assertEqual(len(llm.prompts), 2)
		self.assertIn("'Réserver'", llm.prompts[1])
		self.assertNotIn("'La carte'", llm.prompts[1])

	def test_the_prompt_carries_the_decisions_and_only_the_missing_pages(self):
		llm = FakeLLM(sp.PlannedPages(pages=[planned("groups")]))
		complete(llm, first_plan("home", "menu", "about", "book"))
		prompt = llm.prompts[0]
		self.assertIn("ALREADY DECIDED", prompt)
		self.assertIn("warm and rustic", prompt)
		self.assertIn("a 2px accent rule above every h2", prompt)
		self.assertIn("'Groupes' at /groups", prompt)
		self.assertNotIn("'Accueil' at /home", prompt)

	def test_a_photo_used_on_a_planned_page_is_not_offered_again(self):
		llm = FakeLLM(sp.PlannedPages(pages=[planned("book")]))
		plan = first_plan("menu", "groups", "about", "home")
		plan.pages[0] = planned("menu", "hero", "cards", "cta", photos=["/files/used.jpg"])
		complete(llm, plan, photos=[{"url": "/files/used.jpg"}, {"url": "/files/free.jpg"}])
		self.assertNotIn("/files/used.jpg", llm.prompts[0])
		self.assertIn("/files/free.jpg", llm.prompts[0])

	def test_a_page_that_was_not_asked_or_is_already_planned_is_ignored(self):
		stray = sp.PlannedPages(
			pages=[planned("book"), planned("elsewhere"), planned("home", "cta", "cta", "cta", "cta")]
		)
		plan = complete(FakeLLM(stray), first_plan("home", "menu", "groups", "about"))
		self.assertEqual([p.route for p in plan.pages].count("home"), 1)
		self.assertNotIn("elsewhere", [p.route for p in plan.pages])
		self.assertIn("book", [p.route for p in plan.pages])
		self.assertEqual(next(p for p in plan.pages if p.route == "home").sections[-1].kind, "cta")
		self.assertEqual(len(next(p for p in plan.pages if p.route == "home").sections), 3)

	def test_a_failing_batch_leaves_the_pages_to_the_static_plans(self):
		llm = FakeLLM(
			RuntimeError("provider down"), RuntimeError("provider down"), RuntimeError("provider down")
		)
		plan = complete(llm, first_plan("home"))
		self.assertEqual([p.route for p in plan.pages], ["home"])
		self.assertEqual(len(llm.prompts), sp.PLAN_COMPLETION_ROUNDS)

	def test_a_model_that_answers_nothing_is_asked_a_bounded_number_of_times(self):
		llm = FakeLLM()
		complete(llm, first_plan("home"))
		self.assertEqual(len(llm.prompts), sp.PLAN_COMPLETION_ROUNDS)

	def test_a_half_planned_page_is_replaced_by_the_whole_one(self):
		plan = first_plan("home", "menu", "groups", "about")
		plan.pages.append(planned("book", "intro"))
		plan = complete(
			FakeLLM(sp.PlannedPages(pages=[planned("book", "intro", "cards", "cta", "faq")])), plan
		)
		books = [p for p in plan.pages if p.route == "book"]
		self.assertEqual(len(books), 1)
		self.assertEqual(len(books[0].sections), 4)

	def test_a_page_asked_again_that_comes_back_no_fuller_keeps_the_first(self):
		plan = first_plan("home", "menu", "groups", "about")
		plan.pages.append(planned("book", "intro", "cards"))
		plan = complete(FakeLLM(sp.PlannedPages(pages=[planned("book", "cta")])), plan)
		books = [p for p in plan.pages if p.route == "book"]
		self.assertEqual([len(p.sections) for p in books], [2])

	def test_an_empty_entry_of_the_first_answer_is_replaced(self):
		plan = first_plan("home", "menu", "groups", "about")
		plan.pages.append(sp.PlannedPage(route="book", title="Réserver", sections=[]))
		plan = complete(FakeLLM(sp.PlannedPages(pages=[planned("book", "contact-form", "cta", "faq")])), plan)
		books = [p for p in plan.pages if p.route == "book"]
		self.assertEqual(len(books), 1)
		self.assertEqual(books[0].sections[0].kind, "contact-form")


if __name__ == "__main__":
	unittest.main()
