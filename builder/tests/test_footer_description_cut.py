# //// Neoffice — added file (no upstream equivalent): the footer of a generated site says its activity in one
# //// line, and a long activity is cut where the cut reads as meant (neoffice-maintenance#2717).
import unittest

from builder.api import _shorten_for_footer

# the words the issue names, and their German and English kin: a line that ends on one reads as a text that broke
FUNCTION_WORDS = {
	"de",
	"du",
	"des",
	"la",
	"le",
	"les",
	"et",
	"ou",
	"à",
	"en",
	"pour",
	"avec",
	"und",
	"oder",
	"the",
	"of",
}

# the shape of the activity a beauty institute's site was built from: one long sentence, a list of what it does
INSTITUTE = (
	"Institut de beauté au cœur de la vieille ville, ouvert du mardi au samedi : soins du visage et du corps, "
	"épilation à la cire tiède, beauté du regard (rehaussement et teinture des cils), maquillage de jour et de "
	"soirée, manucure et soin des pieds pour toutes les occasions."
)
NO_LIST = (
	"Une seule phrase très longue sans aucune virgule qui décrit une activité de menuiserie artisanale dans le "
	"Valais central depuis trois générations avec des meubles sur mesure en bois massif pour les chalets et les "
	"appartements de la région"
)


def last_word(line: str) -> str:
	return line.rstrip("…").split()[-1].strip(",;:()").lower()


class TestFooterDescriptionCut(unittest.TestCase):
	def test_a_list_is_cut_after_one_of_its_items_not_on_a_preposition(self):
		line = _shorten_for_footer(INSTITUTE)

		self.assertFalse(line.endswith("maquillage de…"), line)
		self.assertTrue(line.endswith("(rehaussement et teinture des cils)…"), line)
		self.assertLessEqual(len(line), 201)

	def test_the_page_subtitle_cut_never_ends_inside_a_parenthesis_or_on_a_function_word(self):
		line = _shorten_for_footer(INSTITUTE, limit=180)

		self.assertEqual(line.count("("), line.count(")"), line)
		self.assertNotIn(last_word(line), FUNCTION_WORDS, line)

	def test_a_sentence_without_a_list_ends_on_a_word_that_carries_meaning(self):
		line = _shorten_for_footer(NO_LIST)

		self.assertTrue(line.endswith("…"))
		self.assertNotIn(last_word(line), FUNCTION_WORDS, line)
		self.assertTrue(NO_LIST.startswith(line.rstrip("…")), line)

	def test_whole_sentences_and_short_texts_are_kept_as_they_are(self):
		self.assertEqual(_shorten_for_footer("Un garage à Sion."), "Un garage à Sion.")
		two = "Un garage à Sion. " + "Entretien de toutes les marques et de tous les modèles. " * 3
		self.assertEqual(
			_shorten_for_footer(two, limit=80),
			"Un garage à Sion. Entretien de toutes les marques et de tous les modèles.",
		)

	def test_a_german_activity_does_not_end_on_und(self):
		text = (
			"Wir sind eine Schreinerei im Oberwallis und bauen Möbel nach Mass für Chalets und Wohnungen, Küchen "
			"und Badezimmer, Treppen und Türen, Fenster aus Holz und Holz-Metall, sowie Innenausbau für Hotels und "
			"Restaurants in der ganzen Region und"
		)
		self.assertNotIn(last_word(_shorten_for_footer(text)), FUNCTION_WORDS)
