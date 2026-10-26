# //// Neoffice — added file (no upstream equivalent): a generated photograph never shows a person.
"""A regenerated site of a one-person business showed "a technician at his desk" and "a man and a woman at a laptop" in its hero and its
second section, made by the image generator and presented as the owner and a client (26.10.2026, "ce n'est pas lui"). The writer is told
never to describe a person (recipes.ALT_GUIDANCE) and the plan never to ask for one (site_plan); behind them the guard of the image job
(placeholders.must_not_be_drawn) withholds a slot whose alt names one. No model is called."""

import inspect
import unittest

from builder.site_ai.nora import recipes, site_plan
from builder.site_ai.nora.placeholders import must_not_be_drawn, neutral_named_slots

PALETTE = {"qc-background": "#f4f1ea", "qc-secondary": "#2c6e49"}
SLOT = "https://placehold.co/1200x800/e5e7eb/9ca3af/png?text=Photo"

PEOPLE = (
	"Un technicien assis à son bureau, un ordinateur ouvert devant lui",
	"Un homme et une femme penchés sur un ordinateur portable",
	"Une équipe souriante autour d'une table de réunion",
	"A smiling team around a table",
	"A craftsman at work in his workshop",
	"Ein Mann an einem Schreibtisch",
	"Una squadra di tecnici davanti a un computer",
	"Un technicien au travail chez un client",
)
PLACES = (
	"Une vallée alpine du Valais, prairies et chalets de bois, sommets enneigés au fond",
	"Un ordinateur portable et une tasse de café sur une table en bois, les montagnes du Val Ferret en arrière-plan",
	"Un établi d'atelier avec des outils rangés, lumière claire du matin",
	"Alpine chalets under the glaciers, warm late light",
	"Il villaggio della Val Ferret con i suoi chalet di legno",
)


class TestWhatIsNotDrawn(unittest.TestCase):
	def test_a_scene_whose_subject_is_a_person_is_withheld(self):
		for alt in PEOPLE:
			self.assertTrue(must_not_be_drawn(alt), alt)

	def test_a_place_a_tool_or_a_landscape_is_drawn(self):
		for alt in PLACES:
			self.assertFalse(must_not_be_drawn(alt), alt)

	def test_through_the_image_job_guard(self):
		"""The slots go through neutral_named_slots, not beside it."""
		page = [
			{"element": "img", "attributes": {"src": SLOT, "alt": alt}}
			for alt in (PEOPLE[0], PLACES[0], PEOPLE[1], PLACES[1])
		]
		withheld = neutral_named_slots(page, PALETTE, "qc")
		self.assertEqual(len(withheld), 2)
		self.assertTrue(page[0]["attributes"]["src"].startswith("data:image/svg+xml"))
		self.assertTrue(page[2]["attributes"]["src"].startswith("data:image/svg+xml"))
		self.assertIn("placehold.co", page[1]["attributes"]["src"])
		self.assertIn("placehold.co", page[3]["attributes"]["src"])


class TestAShotIsNotAFloorPlan(unittest.TestCase):
	"""\"arrière-plan\" is in every photographic description: a landscape with mountains in it was withheld as a map."""

	def test_the_shots_are_drawn(self):
		for alt in (
			"Une table en bois, des montagnes en arrière-plan",
			"Un établi au premier plan, la vallée au fond",
			"Un gros plan sur des outils rangés",
			"Des chalets au second plan sous un ciel clair",
		):
			self.assertFalse(must_not_be_drawn(alt), alt)

	def test_a_floor_plan_still_is_not(self):
		for alt in ("Plan d'accès au cabinet", "Le plan du local avec ses salles", "A floor plan of the shop"):
			self.assertTrue(must_not_be_drawn(alt), alt)


class TestWhatTheWriterAndThePlanAreTold(unittest.TestCase):
	def test_the_writer_is_told_never_a_person_and_to_show_the_region(self):
		text = recipes.ALT_GUIDANCE
		self.assertIn("never a person", text)
		self.assertIn("the region around it", text)
		self.assertNotIn("people at work", text)

	def test_the_plan_is_told_never_a_person(self):
		self.assertIn("NEVER a person in a generated photograph", inspect.getsource(site_plan))
