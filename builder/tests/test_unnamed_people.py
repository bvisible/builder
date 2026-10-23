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


class TestAPersonWithABelievableName(unittest.TestCase):
	"""The writer of a German "Über uns" gave a family of three, "Hans Lindenhof, Inhaber" and the others, a bio each, when the brief said a
	family business in its third generation and named nobody (2026-10-23)."""

	KNOWN = "Schreinerei Lindenhof Schreinerei in Luzern Familienbetrieb in dritter Generation"

	def team(self, *cards, label="03 — DAS TEAM", heading="Die Familie hinter dem Handwerk"):
		return section(
			t("p", label),
			t("h2", heading),
			t("p", "Drei Generationen, ein gemeinsames Anliegen."),
			{"element": "div", "blockName": "grid", "children": list(cards)},
		)

	def person(self, name, role):
		return {"element": "div", "blockName": "card", "children": [{"element": "img", "attributes": {"src": "/files/p.jpg"}}, t("h3", name), t("p", role), t("p", name.split()[0] + " plant und fertigt mit Sorgfalt.")]}

	def test_a_family_of_invented_names_goes_with_its_section(self):
		blocks = page(section(t("h1", "Über uns"), t("p", "Ein Familienbetrieb in Luzern")), self.team(self.person("Hans Lindenhof", "Inhaber, Schreiner"), self.person("Anna Lindenhof", "Planerin"), self.person("Max Lindenhof", "Monteur")))
		edits = facts.drop_invented_people(blocks, self.KNOWN)
		self.assertEqual([], names(blocks))
		self.assertEqual(1, len(blocks[0]["children"]))
		self.assertEqual(4, len(edits))
		self.assertIn("section left with no person dropped", edits)

	def test_the_shells_around_a_dropped_section_go_too(self):
		"""The section of the real page was a shell around a container: dropping the container alone left an empty band."""
		team = self.team(self.person("Hans Lindenhof", "Inhaber"), self.person("Anna Lindenhof", "Planerin"))
		shell = {"element": "section", "blockName": "band", "children": [{"element": "div", "blockName": "container", "children": [team]}]}
		blocks = page(section(t("h1", "Über uns"), t("p", "Ein Familienbetrieb")), shell)
		facts.drop_invented_people(blocks, self.KNOWN)
		self.assertEqual(1, len(blocks[0]["children"]))
		self.assertEqual([], names(blocks))

	def test_a_name_the_brief_gives_stays(self):
		known = self.KNOWN + " Hans Lindenhof, Inhaber, fertigt seit 1990"
		blocks = page(self.team(self.person("Hans Lindenhof", "Inhaber"), self.person("Anna Lindenhof", "Planerin")))
		facts.drop_invented_people(blocks, known)
		self.assertEqual(["Hans Lindenhof"], names(blocks))

	def test_a_name_like_title_outside_a_team_section_is_left_alone(self):
		menu = section(t("p", "02 — SPEZIALITÄTEN"), t("h2", "Unsere Spezialitäten"), {"element": "div", "children": [card("Fondue Maison", "Käse"), card("Raclette Valaisanne", "Käse")]})
		blocks = page(menu)
		self.assertEqual([], facts.drop_invented_people(blocks, self.KNOWN))
		self.assertEqual(["Fondue Maison", "Raclette Valaisanne"], names(blocks))

	def test_a_heading_that_is_not_a_name_in_a_team_section_stays(self):
		blocks = page(self.team(card("Meister", "Schreiner"), card("Planung und Montage", "Aus einer Hand")))
		self.assertEqual([], facts.drop_invented_people(blocks, self.KNOWN))
		self.assertEqual(["Meister", "Planung und Montage"], names(blocks))

	def test_a_lone_founder_card_goes_and_the_section_heading_stays_when_it_has_other_words(self):
		many = section(
			t("p", "03 — UNSER GRÜNDER"),
			t("h2", "Der Mann hinter dem Betrieb"),
			t("p", "Er hat die Werkstatt aufgebaut."),
			t("p", "Sie ist heute in dritter Generation geführt."),
			t("p", "Familienbetrieb seit Jahrzehnten."),
			self.person("Heinrich Weber", "Gründer"),
		)
		blocks = page(many)
		facts.drop_invented_people(blocks, self.KNOWN)
		self.assertEqual([], names(blocks))
		self.assertEqual(1, len(blocks[0]["children"]))

	def test_french_and_italian_team_sections_are_read_too(self):
		for label, heading in (("03 — L'ÉQUIPE", "Les personnes derrière l'atelier"), ("03 — IL TEAM", "Le persone dietro il lavoro")):
			blocks = page(self.team(self.person("Marie Dupont", "Gérante"), self.person("Paul Martin", "Menuisier"), label=label, heading=heading))
			facts.drop_invented_people(blocks, self.KNOWN)
			self.assertEqual([], names(blocks), label)

	def test_a_page_without_names_and_an_empty_page_are_untouched(self):
		self.assertEqual([], facts.drop_invented_people(page(section(t("h2", "Leistungen"), t("p", "Küchen"))), self.KNOWN))
		self.assertEqual([], facts.drop_invented_people([], self.KNOWN))


class TestTheCardsOfARepeatedTemplate(unittest.TestCase):
	"""On the German build the three cards were one template repeated over the page's data: the names were rows of `data.members`, the
	template's heading was bound to the field and empty in the blocks."""

	KNOWN = "Schreinerei Lindenhof Schreinerei in Luzern Familienbetrieb in dritter Generation"

	def bound_heading(self, key):
		return {"element": "h3", "innerHTML": "", "dynamicValues": [{"key": key, "property": "innerHTML", "type": "key"}]}

	def team(self, label="03 — DAS TEAM", heading="Die Familie hinter dem Handwerk", key="members"):
		template = {"element": "div", "blockName": "card", "children": [{"element": "img", "attributes": {"src": ""}}, self.bound_heading("name"), {"element": "p", "innerHTML": "", "dynamicValues": [{"key": "role", "property": "innerHTML", "type": "key"}]}]}
		grid = {"element": "div", "blockName": "grid", "isRepeaterBlock": True, "dataKey": {"key": key, "property": "innerHTML", "type": "key"}, "children": [template]}
		return section(t("p", label), t("h2", heading), t("p", "Drei Generationen, ein gemeinsames Anliegen."), grid)

	def script(self, *rows, key="members"):
		import json

		return f"data.{key} = {json.dumps([{'name': n, 'role': r} for n, r in rows], ensure_ascii=False)}\n"

	def test_the_repeated_cards_of_invented_names_go_with_their_section(self):
		blocks = page(section(t("h1", "Über uns"), t("p", "Ein Familienbetrieb")), self.team())
		edits, script = facts.drop_invented_people_rows(blocks, self.script(("Hans Lindenhof", "Inhaber"), ("Anna Lindenhof", "Planerin"), ("Max Lindenhof", "Monteur")), self.KNOWN)
		self.assertEqual(1, len(blocks[0]["children"]))
		self.assertIn("section left with no person dropped", edits)
		self.assertTrue(any("Hans Lindenhof" in e for e in edits))

	def test_the_shells_around_the_repeated_section_go_too(self):
		shell = {"element": "section", "blockName": "band", "children": [{"element": "div", "blockName": "container", "children": [self.team()]}]}
		blocks = page(section(t("h1", "Über uns"), t("p", "Ein Familienbetrieb")), shell)
		facts.drop_invented_people_rows(blocks, self.script(("Hans Lindenhof", "Inhaber"), ("Anna Lindenhof", "Planerin")), self.KNOWN)
		self.assertEqual(1, len(blocks[0]["children"]))

	def test_the_rows_the_brief_names_stay_in_the_data(self):
		import json

		known = self.KNOWN + " Hans Lindenhof Inhaber"
		blocks = page(self.team())
		edits, script = facts.drop_invented_people_rows(blocks, self.script(("Hans Lindenhof", "Inhaber"), ("Anna Lindenhof", "Planerin")), known)
		kept = json.loads(script.split("=", 1)[1])
		self.assertEqual(["Hans Lindenhof"], [r["name"] for r in kept])
		self.assertEqual(1, len(blocks[0]["children"]))  # the section stays: it still has a person
		self.assertEqual(1, len(edits))

	def test_a_repeater_that_is_not_about_a_team_is_left_alone(self):
		blocks = page(self.team(label="02 — SPEZIALITÄTEN", heading="Unsere Spezialitäten"))
		script = self.script(("Fondue Maison", "Käse"), ("Raclette Valaisanne", "Käse"))
		edits, after = facts.drop_invented_people_rows(blocks, script, self.KNOWN)
		self.assertEqual([], edits)
		self.assertEqual(script, after)

	def test_a_repeater_whose_names_are_not_names_is_left_alone(self):
		blocks = page(self.team())
		script = self.script(("Meister", "Schreiner"), ("Planung und Montage", "Aus einer Hand"))
		self.assertEqual(([], script), facts.drop_invented_people_rows(blocks, script, self.KNOWN))

	def test_no_data_and_no_blocks_are_left_alone(self):
		self.assertEqual(([], ""), facts.drop_invented_people_rows([], "", self.KNOWN))
		blocks = page(self.team())
		self.assertEqual(([], ""), facts.drop_invented_people_rows(blocks, "", self.KNOWN))


if __name__ == "__main__":
	unittest.main()
