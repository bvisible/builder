# //// Neoffice — added file (no upstream equivalent): a card whose photograph will not be drawn is written without it.
"""A page of a regenerated site showed `features.photo-cards` with grey rectangles where two of its three photographs should have been:
the guard that keeps a picture from stating something false (placeholders.neutral_named_slots) had withheld the card whose alt read "a
desktop screen showing a screen-sharing session", and the image job had given up on another. A plain block on top of a card is never
the look the site is after: the card is written without a photograph (placeholders.drop_plain_card_photos). No model is called."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from builder.site_ai.nora import recipes as R
from builder.site_ai.nora.placeholders import (
	drop_plain_card_photos,
	must_not_be_drawn,
	neutral_empty_slots,
	neutral_named_slots,
	neutral_paint,
	neutral_placeholders,
)
from builder.tests.test_recipes import build, tree, walk

PALETTE = {"qc-background": "#f4f1ea", "qc-secondary": "#2c6e49"}
SLOT = "https://placehold.co/1200x800/e5e7eb/9ca3af/png?text=Services"
SCREEN = "Un écran de bureau affichant une session de partage d'écran"
BENCH = "Un technicien penché sur un ordinateur ouvert, dans un atelier lumineux"
SERVER = "Une baie de serveurs dans une salle sobre, éclairée par une lumière froide"


def photo_cards(*alts, src=SLOT):
	"""The recipe as the writer's own YAML expands it, its three photograph slots given the writer's alt texts."""
	blocks = tree(R.REGISTRY["features.photo-cards"], photos=[src] * 3, sample=True)
	images = [b for b in walk(blocks) if b.get("element") == "img"]
	assert len(images) == 3, "the recipe has three photograph slots"
	for index, (image, alt) in enumerate(zip(images, alts, strict=True)):
		image["attributes"]["alt"] = alt
		image["blockId"] = f"photo-{index}"
	return blocks


def cards_of(blocks):
	return [b for b in walk(blocks) if "u-card" in (b.get("classes") or [])]


def pictures(card):
	return [b for b in walk(card) if b.get("element") == "img"]


def is_plain(image):
	return neutral_paint(str((image.get("attributes") or {}).get("src") or "")) is not None


class TestCardsWithoutAPhotograph(unittest.TestCase):
	def test_the_card_the_guard_withheld_is_written_without_its_photograph(self):
		blocks = photo_cards(SCREEN, BENCH, SERVER)
		withheld = neutral_named_slots(blocks, PALETTE, "qc")
		self.assertEqual(len(withheld), 1, "the guard keeps the screen from the image job")
		cards = cards_of(blocks)
		self.assertEqual(len(cards), 3)
		self.assertTrue(
			any(is_plain(i) for c in cards for i in pictures(c)),
			"before the pass the card shows a plain block",
		)

		self.assertEqual(drop_plain_card_photos(blocks), 1)

		self.assertEqual([len(pictures(c)) for c in cards], [0, 1, 1])
		self.assertEqual(
			cards[0]["baseStyles"].get("justifyContent"),
			"center",
			"its copy sits in the middle of the stretched card",
		)
		self.assertNotIn("justifyContent", cards[1].get("baseStyles") or {})
		for card in cards:
			for image in pictures(card):
				self.assertIn(
					"placehold.co", image["attributes"]["src"], "the two others are left for the image job"
				)
		self.assertFalse(any(is_plain(i) for i in walk(blocks) if i.get("element") == "img"))
		# the card keeps its words
		self.assertTrue(all("children" in c and c["children"] for c in cards))

	def test_the_card_that_keeps_no_photograph_keeps_its_copy(self):
		blocks = photo_cards(SCREEN, BENCH, SERVER)
		neutral_named_slots(blocks, PALETTE, "qc")
		before = [
			json.dumps([c for c in walk(card) if c.get("innerHTML")], sort_keys=True)
			for card in cards_of(blocks)
		]
		self.assertEqual(drop_plain_card_photos(blocks), 1)
		after = [
			json.dumps([c for c in walk(card) if c.get("innerHTML")], sort_keys=True)
			for card in cards_of(blocks)
		]
		self.assertEqual(before, after)

	def test_when_most_of_a_row_lost_its_photograph_the_row_has_none(self):
		"""Three cards, one of them with a photograph and two of them without, is a row that looks broken: the three are alike."""
		blocks = photo_cards(SCREEN, "Un plan d'accès à l'atelier", SERVER)
		self.assertEqual(len(neutral_named_slots(blocks, PALETTE, "qc")), 2)
		self.assertEqual(drop_plain_card_photos(blocks), 3)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [0, 0, 0])
		self.assertFalse(
			any("justifyContent" in (c.get("baseStyles") or {}) for c in cards_of(blocks)),
			"a row of cards without photographs is not centred",
		)

	def test_a_page_with_every_photograph_is_left_alone(self):
		blocks = photo_cards(BENCH, SERVER, "Un atelier de réparation, lumière du matin sur l'établi")
		neutral_named_slots(blocks, PALETTE, "qc")
		self.assertEqual(drop_plain_card_photos(blocks), 0)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [1, 1, 1])

	def test_a_real_photograph_is_never_taken_out_alone(self):
		blocks = photo_cards(BENCH, SERVER, SCREEN, src="/files/atelier.jpg")
		self.assertEqual(drop_plain_card_photos(blocks), 0)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [1, 1, 1])

	def test_a_plain_block_outside_a_card_is_not_ours_to_remove(self):
		"""A framed picture, a hero: nothing says the page does without it, and the site draws the plain block there on purpose."""
		hero = {
			"element": "section",
			"children": [{"element": "img", "attributes": {"src": SLOT, "alt": SCREEN}}],
		}
		neutral_named_slots([hero], PALETTE, "qc")
		self.assertEqual(drop_plain_card_photos([hero]), 0)
		self.assertEqual(len(hero["children"]), 1)

	def test_the_site_with_its_image_generation_off_has_no_plain_block_in_its_cards_either(self):
		blocks = photo_cards(BENCH, SERVER, SCREEN)
		neutral_placeholders(blocks, PALETTE, "qc")
		neutral_empty_slots(blocks, PALETTE, "qc")
		self.assertEqual(drop_plain_card_photos(blocks), 3)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [0, 0, 0])

	def test_a_photograph_the_image_job_gave_up_on_is_named_by_its_block(self):
		blocks = photo_cards(BENCH, SERVER, SCREEN)
		self.assertEqual(
			drop_plain_card_photos(blocks, failed={"photo-1"}), 1, "one of three: that card only"
		)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [1, 0, 1])
		self.assertEqual(
			drop_plain_card_photos(blocks, failed={"photo-0"}),
			2,
			"then half of what is left: the row has none",
		)
		self.assertEqual([len(pictures(c)) for c in cards_of(blocks)], [0, 0, 0])


class _Page:
	def __init__(self, blocks):
		self.fields = {"blocks": json.dumps(blocks), "draft_blocks": json.dumps(blocks)}
		self.saved = 0

	def get(self, name):
		return self.fields.get(name)

	def set(self, name, value):
		self.fields[name] = value

	def save(self, **_kwargs):
		self.saved += 1


class TestTheImageJobGivingUp(unittest.TestCase):
	"""The worker that draws the pictures after the build: a card it cannot draw for is not left on a placeholder the site shows as a grey block."""

	def run_job(self, page, slots, fail=()):
		from builder import api

		def generate(prompt, width=1024, height=1024):
			if prompt in fail:
				raise RuntimeError("the image backend did not answer")
			return f"/files/{abs(hash(prompt))}.png"

		comfy = SimpleNamespace(is_configured=lambda: True, generate_image=generate)
		with (
			patch("builder.site_ai.generators.comfyui_client.is_configured", comfy.is_configured),
			patch("builder.site_ai.generators.comfyui_client.generate_image", comfy.generate_image),
			patch.object(api, "_update_generation_status"),
			patch.object(api.frappe, "get_doc", return_value=page),
			patch.object(api.frappe, "log_error"),
			patch("frappe.db", MagicMock(), create=True),
		):
			api._generate_images_worker("job", slots)

	def slots_for(self, blocks, page_name="page-services"):
		return [
			{
				"page_name": page_name,
				"block_id": b["blockId"],
				"src": b["attributes"]["src"],
				"alt": b["attributes"]["alt"],
				"size": "1200x800",
				"type": "img",
			}
			for b in walk(blocks)
			if b.get("element") == "img"
		]

	def test_a_card_whose_picture_failed_is_saved_without_it(self):
		blocks = photo_cards(BENCH, SERVER, "Un atelier de réparation, lumière du matin sur l'établi")
		page = _Page(blocks)
		self.run_job(page, self.slots_for(blocks), fail={SERVER})
		for field in ("blocks", "draft_blocks"):
			saved = json.loads(page.fields[field])
			counts = [len(pictures(c)) for c in cards_of(saved)]
			self.assertEqual(counts, [1, 0, 1], field)
			for card in cards_of(saved):
				for image in pictures(card):
					self.assertNotIn("placehold.co", image["attributes"]["src"], "the other two were drawn")
		self.assertGreater(page.saved, 0)

	def test_a_job_that_drew_everything_leaves_the_cards_as_they_are(self):
		blocks = photo_cards(BENCH, SERVER, "Un atelier de réparation, lumière du matin sur l'établi")
		page = _Page(blocks)
		self.run_job(page, self.slots_for(blocks))
		saved = json.loads(page.fields["blocks"])
		self.assertEqual([len(pictures(c)) for c in cards_of(saved)], [1, 1, 1])


class TestTheWriterIsToldWhatIsNotDrawn(unittest.TestCase):
	"""The writer chose the alt that the guard then refused: nobody had told it that a screen, a sign, a map, a document or a portrait is never drawn."""

	def test_a_recipe_photograph_says_what_the_site_does_not_draw(self):
		text = R.ALT_GUIDANCE.lower()
		for word in ("screen", "sign", "map", "document", "portrait"):
			self.assertIn(word, text)
			self.assertTrue(
				must_not_be_drawn(f"a {word} on a table"),
				f"the guard does not refuse {word}: the guidance and the guard disagree",
			)

	def test_the_guidance_reaches_the_writer_in_the_recipe(self):
		brief = " ".join(build(R.REGISTRY["features.photo-cards"], sample=False).split())
		self.assertIn("never a screen", brief)


if __name__ == "__main__":
	unittest.main()
