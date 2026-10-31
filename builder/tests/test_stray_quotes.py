# //// Neoffice — added file (no upstream equivalent): the closing apostrophe a text was left with.
"""The six descriptions of a garage's services list each ended in `.'`, the cards of an electrician's in `."`: the model closed a quote it never
opened. Pinned here: such a closing apostrophe or double quote goes, in a text with tags after it too; an elision (a letter before the apostrophe)
stays, so does a quoted span the text really opened, a text with Jinja or SVG is not touched, and the blocks of a whole page are walked."""

import unittest

from builder.site_ai.nora.punctuation import stray_quotes


def block(html, **over):
    return {"element": "p", "innerHTML": html, **over}


def fixed(html):
    blocks = [block(html)]
    stray_quotes(blocks)
    return blocks[0]["innerHTML"]


class TestAClosingQuoteWithNoOpeningOne(unittest.TestCase):
    def test_the_apostrophe_after_the_full_stop_goes(self):
        self.assertEqual("Redressage et remise en peinture des éléments touchés.", fixed("Redressage et remise en peinture des éléments touchés.'"))

    def test_an_elision_inside_the_text_does_not_stop_it_going(self):
        self.assertEqual("Vérification avant le passage de l'expertise, pour un dossier solide.", fixed("Vérification avant le passage de l'expertise, pour un dossier solide.'"))

    def test_after_a_question_mark_an_exclamation_mark_or_an_ellipsis(self):
        for mark in "?!…":
            self.assertEqual(f"Une question{mark}", fixed(f"Une question{mark}'"))

    def test_with_closing_tags_after_it_it_still_goes(self):
        self.assertEqual("Un <em>texte</em>.</p>", fixed("Un <em>texte</em>.'</p>"))
        self.assertEqual("Un texte.</em> ", fixed("Un texte.'</em> "))

    def test_a_trailing_space_is_kept(self):
        self.assertEqual("Un texte. ", fixed("Un texte.' "))


class TestADoubleQuote(unittest.TestCase):
    def test_the_double_quote_after_the_full_stop_goes(self):
        self.assertEqual("Travaux complets pour bâtiments neufs.", fixed('Travaux complets pour bâtiments neufs."'))

    def test_with_closing_tags_after_it(self):
        self.assertEqual("Un <em>texte</em>.</p>", fixed('Un <em>texte</em>."</p>'))

    def test_a_double_quoted_span_the_text_opened_stays(self):
        for text in ('Notre plat "signature".', 'Il a dit "bonjour."', '"Un titre entre guillemets."', '("un mot.")'):
            self.assertEqual(text, fixed(text))

    def test_an_apostrophe_the_text_opened_does_not_keep_a_stray_double_quote(self):
        self.assertEqual("Il a dit 'bonjour'.", fixed("Il a dit 'bonjour'.\""))

    def test_a_double_quote_the_text_opened_does_not_keep_a_stray_apostrophe(self):
        self.assertEqual('Il a dit "bonjour".', fixed('Il a dit "bonjour".\''))

    def test_a_quote_inside_an_attribute_is_not_text(self):
        text = '<a href="x.">Un lien</a>'
        self.assertEqual(text, fixed(text))


class TestWhatStays(unittest.TestCase):
    def test_a_quote_the_text_opened(self):
        text = "Notre plat 'signature'."
        self.assertEqual(text, fixed(text))
        text = "Il a dit 'bonjour.'"
        self.assertEqual(text, fixed(text))

    def test_a_quote_opened_after_a_bracket_or_at_the_start(self):
        text = "('un mot.')"
        self.assertEqual(text, fixed(text))
        text = "'Un titre entre guillemets.'"
        self.assertEqual(text, fixed(text))

    def test_a_text_that_does_not_end_in_one(self):
        for text in ("Un texte.", "L'équipe", "Un texte sans point", ""):
            self.assertEqual(text, fixed(text))

    def test_an_apostrophe_after_a_letter_at_the_end_is_not_a_closing_quote(self):
        self.assertEqual("Aujourd'hui", fixed("Aujourd'hui"))

    def test_jinja_and_svg_are_left_alone(self):
        for text in ("{% include 'x.html' %}.'", "{{ title }}.'", "<svg><path d='M0 0'/></svg>.'"):
            self.assertEqual(text, fixed(text))

    def test_a_text_in_a_tag_attribute_is_not_read_as_text(self):
        text = "<a href='x.'>Un lien</a>"
        self.assertEqual(text, fixed(text))


class TestAWholePage(unittest.TestCase):
    def test_nested_blocks_are_walked_and_the_changes_counted(self):
        blocks = [
            {
                "element": "section",
                "children": [
                    block("Premier.'"),
                    {"element": "div", "children": [block("Deuxième.'"), block("Troisième.")]},
                ],
            }
        ]
        self.assertEqual(2, stray_quotes(blocks))
        self.assertEqual("Premier.", blocks[0]["children"][0]["innerHTML"])
        self.assertEqual("Deuxième.", blocks[0]["children"][1]["children"][0]["innerHTML"])
        self.assertEqual("Troisième.", blocks[0]["children"][1]["children"][1]["innerHTML"])

    def test_a_block_with_no_text_is_fine(self):
        self.assertEqual(0, stray_quotes([{"element": "div"}, {"element": "img", "innerHTML": None}]))


if __name__ == "__main__":
    unittest.main()
