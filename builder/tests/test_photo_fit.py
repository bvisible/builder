# //// Neoffice — added file (no upstream equivalent): the photographs a user brings are kept when they belong on the site, and placed where they are said to be.
"""Ten photographs brought for a mountain restaurant, one of them a modern home office: the vision read them all, the pages used all
ten, the office on the booking page, and the summary gave the assistant no placement to tell (2026-10-21). No model is called."""

import unittest

from builder.site_ai.nora import photo_fit
from builder.site_ai.nora.layout import one_photo_once

PHOTOS = [
	{
		"url": "/files/terrasse.png",
		"shows": "A dining terrace with a view of the mountains.",
		"text": "a dining terrace with a view of the mountains",
	},
	{
		"url": "/files/raclette.png",
		"shows": "A cook scraping melted raclette.",
		"text": "a cook scraping melted raclette",
	},
	{
		"url": "/files/bureau.png",
		"shows": "A modern home office with two armchairs.",
		"text": "a modern home office with two armchairs",
	},
]


class FakeProvider:
	def __init__(self, unusable=None, boom=False):
		self.unusable, self.boom, self.prompts = unusable or [], boom, []

	def generate_structured(self, prompt, schema, **kwargs):
		self.prompts.append(prompt)
		if self.boom:
			raise RuntimeError("the lane is down")
		return schema.model_validate({"unusable": self.unusable})


class TestWhichPhotographsBelong(unittest.TestCase):
	def judge(self, provider, library=PHOTOS):
		return photo_fit.unusable_photos(
			"nora/nora", "Auberge Test", "Mountain restaurant.", library, provider=provider
		)

	def test_the_photograph_of_another_trade_is_left_out_with_its_reason(self):
		provider = FakeProvider([{"n": 3, "reason": "an office, not a restaurant"}])
		self.assertEqual(self.judge(provider), {"/files/bureau.png": "an office, not a restaurant"})
		# the judgement is made on the descriptions the vision wrote, numbered
		self.assertIn("3. a modern home office", provider.prompts[0])
		self.assertIn("Mountain restaurant", provider.prompts[0])

	def test_a_number_that_is_not_in_the_list_is_ignored(self):
		self.assertEqual(self.judge(FakeProvider([{"n": 9, "reason": "?"}, {"n": 0}])), {})

	def test_a_verdict_that_discards_everything_leaves_everything_in(self):
		self.assertEqual(self.judge(FakeProvider([{"n": 1}, {"n": 2}, {"n": 3}])), {})

	def test_a_failure_leaves_everything_in(self):
		self.assertEqual(self.judge(FakeProvider(boom=True)), {})

	def test_a_single_photograph_is_the_users_choice(self):
		provider = FakeProvider([{"n": 1, "reason": "no"}])
		self.assertEqual(self.judge(provider, PHOTOS[:1]), {})
		self.assertEqual(provider.prompts, [])

	def test_the_matcher_does_not_place_what_was_left_out(self):
		assets = [{"file": "/files/a.png"}, {"file": "/files/b.png"}]
		self.assertEqual(photo_fit.usable_assets(assets, {"/files/b.png"}), [{"file": "/files/a.png"}])
		self.assertEqual(photo_fit.usable_assets(assets, None), assets)


def section(name, *children):
	return {"blockName": name, "element": "section", "children": list(children)}


def img(src):
	return {"element": "img", "attributes": {"src": src}}


class TestThePlanOfThePhotographs(unittest.TestCase):
	def pages(self):
		home = [
			{
				"blockName": "body",
				"element": "div",
				"children": [
					section("hero", {"element": "div", "children": [img("/files/terrasse.png")]}),
					section("two-column", img("/files/raclette.png")),
				],
			}
		]
		carte = [
			{
				"blockName": "body",
				"element": "div",
				"children": [section("intro", img("/files/terrasse.png"))],
			}
		]
		return [("Accueil", home), ("La carte", carte)]

	def test_where_each_photograph_is_used_is_the_page_and_its_section(self):
		uses = photo_fit.where_used(self.pages())
		self.assertEqual(uses["/files/terrasse.png"], ["Accueil (hero)", "La carte (intro)"])
		self.assertEqual(uses["/files/raclette.png"], ["Accueil (two-column)"])

	def test_the_plan_says_used_left_out_and_not_placed(self):
		plan = photo_fit.photo_plan(
			PHOTOS, {"/files/bureau.png": "an office, not a restaurant"}, self.pages()
		)
		text = "\n".join(plan)
		self.assertIn("PHOTO PLAN", plan[0])
		self.assertIn(
			"- terrasse.png (A dining terrace with a view of the mountains): used on Accueil (hero); La carte (intro)",
			text,
		)
		self.assertIn("- raclette.png (A cook scraping melted raclette): used on Accueil (two-column)", text)
		self.assertIn(
			"- bureau.png (A modern home office with two armchairs): NOT USED, an office, not a restaurant",
			text,
		)

	def test_a_photograph_nobody_needed_is_said_to_be_not_placed(self):
		plan = photo_fit.photo_plan(PHOTOS, {}, self.pages())
		self.assertIn(
			"- bureau.png (A modern home office with two armchairs): not placed, no section needed it",
			"\n".join(plan),
		)

	def test_without_photographs_there_is_no_plan(self):
		self.assertEqual(photo_fit.photo_plan([], {}, self.pages()), [])


class TestARepeatTakesAPhotographOfTheLibrary(unittest.TestCase):
	"""A banquet page showed the same hall twice: its own list had no third photograph (2026-10-21)."""

	def page(self):
		return [section("story", img("/files/a.png")), section("two-column", img("/files/a.png"))]

	def test_with_no_spare_in_the_page_list_the_repeat_stays(self):
		blocks = self.page()
		self.assertEqual(one_photo_once(blocks, ["/files/a.png"]), [])
		self.assertEqual(blocks[1]["children"][0]["attributes"]["src"], "/files/a.png")

	def test_a_spare_from_the_whole_library_replaces_it(self):
		blocks = self.page()
		swaps = one_photo_once(blocks, ["/files/a.png", "/files/b.png"])
		self.assertEqual(len(swaps), 1)
		self.assertEqual(blocks[0]["children"][0]["attributes"]["src"], "/files/a.png")
		self.assertEqual(blocks[1]["children"][0]["attributes"]["src"], "/files/b.png")


class TestTheAssistantAnswersFromThePlan(unittest.TestCase):
	def test_the_playbook_tells_it_to(self):
		from builder.site_ai.nora.prompts import site_playbook

		text = site_playbook()
		self.assertIn("PHOTO PLAN", text)
		self.assertIn("Never claim a placement the plan does not list", text)


if __name__ == "__main__":
	unittest.main()
