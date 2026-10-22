# //// Neoffice — added file (no upstream equivalent): a person nobody named is not published.
"""A practice that gave no team got a team page of cards "Partenaire 1", "Partenaire 2", each under a role (2026-10-22). The writer is
told never to invent a person (facts.FACTS_RULE), and the pass after it (facts.drop_unnamed_people) takes the stand-ins out: the
card that shows one goes, a section left with only its heading goes with it, a real name is never touched. No model is called."""

import unittest

from builder.site_ai.nora import facts


def t(tag, value):
	return {"element": tag, "innerHTML": value}


def card(name, role):
	return {"element": "div", "blockName": "card", "children": [{"element": "img", "attributes": {"src": "/files/p.jpg"}}, t("h3", name), t("p", role)]}


def section(*children):
	return {"element": "section", "children": list(children)}


def page(*sections):
	return [{"element": "div", "blockName": "body", "children": list(sections)}]


def names(blocks):
	out = []
	stack = list(blocks)
	while stack:
		b = stack.pop(0)
		if b.get("element") == "h3":
			out.append(b["innerHTML"])
		stack = list(b.get("children") or []) + stack
	return out


class TestWhatIsAStandIn(unittest.TestCase):
	def test_numbered_stand_ins_in_four_languages(self):
		for text in ("Partenaire 1", "Partenaire n°2", "Membre 3", "Associé 2", "Team member 2", "Partner 1", "Mitarbeiter 4", "Mitarbeiterin 1", "Collaboratore 2", "Prénom Nom", "Full name", "Vorname Nachname"):
			self.assertTrue(facts.STAND_IN_PERSON.match(text), text)

	def test_a_real_name_a_role_or_a_year_is_not(self):
		for text in ("Marie Dupont", "Partenaire privilégié", "Notre équipe", "Associé fondateur", "Partner Program", "Étage 2", "Juriste"):
			self.assertFalse(facts.STAND_IN_PERSON.match(text), text)


class TestTheCardsOfPeopleNobodyNamed(unittest.TestCase):
	def test_a_grid_of_stand_ins_goes_and_its_section_with_it(self):
		blocks = page(
			section(t("h1", "Accueil"), t("p", "Un cabinet")),
			section(t("h2", "Notre équipe"), {"element": "div", "children": [card("Partenaire 1", "Juriste"), card("Partenaire 2", "Avocat")]}),
		)
		edits = facts.drop_unnamed_people(blocks)
		self.assertTrue(edits)
		self.assertEqual(1, len(blocks[0]["children"]))
		self.assertEqual([], names(blocks))

	def test_a_real_member_stays_and_only_the_stand_ins_go(self):
		blocks = page(section(t("h2", "Notre équipe"), {"element": "div", "children": [card("Marie Dupont", "Avocate"), card("Partenaire 2", "Juriste"), card("Partenaire 3", "Juriste")]}))
		facts.drop_unnamed_people(blocks)
		self.assertEqual(["Marie Dupont"], names(blocks))
		self.assertEqual(1, len(blocks[0]["children"]))

	def test_a_page_of_real_people_is_left_alone(self):
		blocks = page(section(t("h2", "Équipe"), {"element": "div", "children": [card("Marie Dupont", "Avocate"), card("Paul Martin", "Juriste")]}))
		self.assertEqual([], facts.drop_unnamed_people(blocks))
		self.assertEqual(["Marie Dupont", "Paul Martin"], names(blocks))

	def test_a_lone_stand_in_line_goes_alone(self):
		blocks = page(section(t("h2", "Notre approche"), t("p", "Nous travaillons avec soin sur chaque dossier, du premier rendez-vous à la décision."), t("h3", "Partenaire 1")))
		edits = facts.drop_unnamed_people(blocks)
		self.assertEqual(1, len(edits))
		self.assertEqual(1, len(blocks[0]["children"]))
		self.assertEqual(2, len(blocks[0]["children"][0]["children"]))

	def test_a_page_without_people_is_untouched(self):
		blocks = page(section(t("h2", "Nos services"), t("p", "Conseil et accompagnement.")))
		self.assertEqual([], facts.drop_unnamed_people(blocks))
		self.assertEqual([], facts.drop_unnamed_people([]))


class TestTheWriterIsToldNotToInventAPerson(unittest.TestCase):
	def test_the_rule_names_the_stand_ins(self):
		self.assertIn("Never invent a person", facts.FACTS_RULE)
		self.assertIn("Partner 1", facts.FACTS_RULE)


if __name__ == "__main__":
	unittest.main()
