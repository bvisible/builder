# //// Neoffice — added file (no upstream equivalent): the hub's blocks offered in the Builder editor's insertion panel.
"""The hub keeps blocks for the people who build a page by hand (site_ai/nora/hub_templates.py turns them into the cards of the editor's insertion
panel). What is pinned here: a block is drawn on the site's own design tokens with sample words in the language of the site, and becomes a block the
editor reads; a card is redrawn when the block, its thumbnail, its section or the site's design changed, and only then; a block the hub sends that
fails the lint, carries the live form, or has no thumbnail is left out and said; a hub that does not answer, a site that did not ask and a site with
no design tokens change nothing; a person's own template is never touched; and a card is written without the export a Block Template makes to the
app's folder. No network, no model."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from builder.site_ai.nora import hub_templates as T
from builder.tests.test_hub_blocks import block as hub_block
from builder.tests.test_hub_blocks import folding_tree
from builder.tests.test_recipes import HANDLES, LIGHT


def editor_block(**over):
	"""A block as the editor catalogue serves it: the hub's block, its section, its thumbnail."""
	data = hub_block(**{"photos": 1, "id": "steps.rail", "title": "Steps on a rail"})
	data.update(
		{
			"category": "Steps",
			"preview": "https://hub.test/files/hub-block-steps.rail-1.png",
			"generator": False,
		}
	)
	data.update(over)
	return data


def catalogue(*blocks, sections=("Hero", "Steps", "FAQ", "Content")):
	return {"format": 2, "sections": list(sections), "blocks": list(blocks)}


class TestWhetherASiteAsked(unittest.TestCase):
	def test_it_is_off_unless_the_site_config_says_so(self):
		self.assertFalse(T.enabled({}))
		self.assertFalse(T.enabled({"builder_hub_templates": 0}))
		self.assertTrue(T.enabled({"builder_hub_templates": 1}))
		self.assertTrue(T.enabled({"builder_hub_templates": "true"}))

	def test_the_generators_switch_is_not_this_one(self):
		self.assertFalse(T.enabled({"nora_hub_blocks": 1}))

	def test_the_sample_words_are_french_for_a_french_site_and_english_for_any_other(self):
		self.assertEqual("fr", T.sample_language("fr"))
		self.assertEqual("fr", T.sample_language("fr-CH"))
		self.assertEqual("en", T.sample_language("de"))
		self.assertEqual("en", T.sample_language(None))


class TestABlockDrawn(unittest.TestCase):
	def draw(self, **over):
		return T.draw(editor_block(**over), HANDLES, LIGHT, "fr")

	def test_it_is_a_block_of_the_editor_with_children_and_ids(self):
		drawn = self.draw()
		self.assertEqual("section", drawn["element"])
		self.assertTrue(drawn["children"])

		def walk(b):
			yield b
			for c in b.get("children") or []:
				yield from walk(c)

		everything = list(walk(drawn))
		self.assertTrue(all(b.get("blockId") for b in everything))
		self.assertEqual(len(everything), len({b["blockId"] for b in everything}))
		self.assertNotEqual("root", drawn["blockId"])
		self.assertNotIn("originalElement", drawn)

	def test_it_wears_the_design_tokens_of_the_site_not_a_colour(self):
		text = json.dumps(self.draw())
		self.assertIn("var(--t-", text)
		self.assertNotIn("{{", text)

	def test_it_holds_sample_words_in_the_language_of_the_site_and_no_slot(self):
		text = json.dumps(self.draw(), ensure_ascii=False)
		self.assertNotIn("WRITE", text)
		self.assertIn("Nous écrire", text)
		english = json.dumps(T.draw(editor_block(), HANDLES, LIGHT, "en"))
		self.assertIn("Write to us", english)

	def test_its_photographs_are_the_placeholder_of_the_editor(self):
		self.assertIn(T.PLACEHOLDER_PHOTO, json.dumps(self.draw()))

	def test_questions_that_fold_stay_a_details_and_a_summary(self):
		faq = editor_block(id="faq.fold", photos=0, kinds=["faq"], tree=folding_tree(), category="FAQ")
		text = json.dumps(T.draw(faq, HANDLES, LIGHT, "fr"))
		self.assertIn('"element": "details"', text)
		self.assertIn('"element": "summary"', text)

	def test_a_block_that_fails_the_lint_is_left_out_with_the_reason(self):
		bad = editor_block()
		bad["tree"] = {"el": "section", "c": [{"el": "h2", "text": "Fixed words"}]}
		with self.assertRaises(T.Left) as why:
			T.draw(bad, HANDLES, LIGHT, "fr")
		self.assertIn("fixed words", str(why.exception).lower())

	def test_a_block_that_carries_the_live_form_is_left_out(self):
		with_form = editor_block(id="contact.card", kinds=["contact-form"], photos=0, form=True)
		with_form["tree"] = {
			"el": "section",
			"name": "card",
			"c": [
				{"el": "h2", "text": "WRITE heading: 3 to 7 words"},
				{"el": "div", "name": "form", "text": "{{include_component}}"},
			],
		}
		with self.assertRaises(T.Left) as why:
			T.draw(with_form, HANDLES, LIGHT, "fr")
		self.assertIn("form", str(why.exception))


class TestTheSampleWords(unittest.TestCase):
	def test_a_role_the_generator_knows_gets_its_own_sample(self):
		self.assertEqual("Nous écrire", T.sample_for("WRITE button: 2 to 4 words", "fr"))
		self.assertEqual("Write to us", T.sample_for("WRITE button: 2 to 4 words", "en"))

	def test_a_role_it_does_not_know_gets_a_label_that_fits_the_words_the_slot_allows(self):
		self.assertEqual("Détail", T.sample_for("WRITE caption: 1 word", "fr"))
		self.assertEqual("Un court libellé", T.sample_for("WRITE caption: 1 to 3 words", "fr"))
		self.assertEqual("Un libellé court et précis", T.sample_for("WRITE caption: 2 to 6 words", "fr"))
		self.assertEqual("A detail", T.sample_for("WRITE caption: 1 to 2 words", "en"))
		self.assertEqual(
			"A short and precise label", T.sample_for("WRITE phrase: a speciality of the business", "en")
		)

	def test_what_the_guidance_allows(self):
		self.assertEqual(4, T.max_words("2 to 4 words"))
		self.assertEqual(1, T.max_words("1 word"))
		self.assertEqual(3, T.max_words("1 to 3 words of the business's own, a speciality"))
		self.assertIsNone(T.max_words("a name"))
		self.assertIsNone(T.max_words(""))

	def test_every_slot_of_a_node_is_filled_wherever_it_is(self):
		node = {
			"el": "div",
			"text": "WRITE heading: 3 to 7 words",
			"attrs": {"alt": "WRITE alt: a scene", "href": "/contact"},
			"c": [{"el": "p", "text": "WRITE caption: 1 word"}, {"el": "p", "text": "plain"}],
		}
		T.fill_slots(node, "fr")
		self.assertEqual("Détail", node["c"][0]["text"])
		self.assertEqual("plain", node["c"][1]["text"])
		self.assertEqual("/contact", node["attrs"]["href"])
		self.assertNotIn("WRITE", json.dumps(node))

	def test_a_caption_never_becomes_a_paragraph(self):
		tree = {
			"el": "section",
			"name": "plans",
			"c": [{"el": "p", "name": "plan", "text": "WRITE caption: 1 to 3 words"}],
		}
		drawn = T.draw(editor_block(photos=0, tree=tree, kinds=["cards"]), HANDLES, LIGHT, "fr")
		self.assertLessEqual(len(drawn["children"][0]["innerHTML"].split()), 3)


class TestWhenACardIsDrawnAgain(unittest.TestCase):
	def test_the_hash_follows_the_block_its_thumbnail_its_section_and_the_design(self):
		signature = T.design_signature(HANDLES, LIGHT, "fr")
		base = T.card_hash(editor_block(), signature)
		self.assertEqual(base, T.card_hash(editor_block(), signature))
		self.assertNotEqual(base, T.card_hash(editor_block(version=2), signature))
		self.assertNotEqual(
			base, T.card_hash(editor_block(preview="https://hub.test/files/other.png"), signature)
		)
		self.assertNotEqual(base, T.card_hash(editor_block(category="Hero"), signature))
		self.assertNotEqual(
			base,
			T.card_hash(editor_block(), T.design_signature(HANDLES, {**LIGHT, "t-primary": "#000000"}, "fr")),
		)

	def test_the_design_signature_follows_the_tokens_the_colours_and_the_language(self):
		base = T.design_signature(HANDLES, LIGHT, "fr")
		self.assertEqual(base, T.design_signature(HANDLES, LIGHT, "fr"))
		self.assertNotEqual(base, T.design_signature(HANDLES, LIGHT, "en"))
		self.assertNotEqual(base, T.design_signature({**HANDLES, "container": "var(--other)"}, LIGHT, "fr"))
		with patch.object(T, "RENDERER", T.RENDERER + 1):
			self.assertNotEqual(base, T.design_signature(HANDLES, LIGHT, "fr"))

	def test_a_card_is_added_updated_or_removed_and_one_that_did_not_change_is_left_alone(self):
		add, update, remove = T.plan({"a": "1", "b": "2", "c": "3"}, {"a": "1", "b": "9", "d": "4"})
		self.assertEqual(["d"], add)
		self.assertEqual(["b"], update)
		self.assertEqual(["c"], remove)

	def test_the_sections_are_ranked_as_the_hub_lists_them(self):
		self.assertEqual({"Hero": 0, "Steps": 1}, T.section_order({"sections": ["Hero", "Steps"]}))
		self.assertEqual({}, T.section_order({}))
		self.assertEqual({}, T.section_order({"sections": "Hero"}))


class TestSyncing(unittest.TestCase):
	"""`sync` with the database and the hub replaced."""

	def run_sync(
		self,
		body,
		rows=(),
		design=(HANDLES, LIGHT),
		conf=None,
		taken=None,
		exists=lambda *a: False,
		language="fr",
	):
		frappe = MagicMock()
		frappe.flags = SimpleNamespace(in_import=False)
		frappe.as_json = lambda value, indent=0: json.dumps(value)
		frappe.get_all.return_value = [SimpleNamespace(**r) for r in rows]
		frappe.db.get_single_value.return_value = language
		frappe.db.get_value.return_value = taken
		frappe.db.exists.side_effect = exists
		inserted, seen = [], []

		def get_doc(values):
			seen.append(frappe.flags.in_import)
			doc = MagicMock()
			doc.insert.side_effect = lambda **kw: inserted.append(values)
			return doc

		frappe.get_doc.side_effect = get_doc
		with (
			patch.object(T, "frappe", frappe),
			patch.object(T, "fetch", return_value=body) as fetch,
			patch.object(T, "site_design", return_value=design),
		):
			result = T.sync(conf if conf is not None else {"builder_hub_templates": 1})
		return result, frappe, inserted, seen, fetch

	def test_a_site_that_did_not_ask_is_not_even_asked_of_the_hub(self):
		result, frappe, _inserted, _seen, fetch = self.run_sync(catalogue(editor_block()), conf={})
		self.assertEqual({"state": "off"}, result)
		fetch.assert_not_called()
		frappe.db.commit.assert_not_called()

	def test_a_hub_that_does_not_answer_changes_nothing(self):
		result, frappe, inserted, _seen, _fetch = self.run_sync(None)
		self.assertIn("does not answer", result["state"])
		self.assertEqual([], inserted)
		frappe.db.delete.assert_not_called()
		frappe.db.commit.assert_not_called()

	def test_a_site_with_no_design_tokens_is_offered_nothing_and_loses_nothing(self):
		result, frappe, inserted, _seen, _fetch = self.run_sync(catalogue(editor_block()), design=None)
		self.assertIn("no design tokens", result["state"])
		self.assertEqual([], inserted)
		frappe.db.delete.assert_not_called()

	def test_a_new_block_becomes_a_card_in_its_section_two_columns_wide_with_its_thumbnail(self):
		result, frappe, inserted, _seen, _fetch = self.run_sync(catalogue(editor_block()))
		self.assertEqual(["steps.rail"], result["added"])
		values = inserted[0]
		self.assertEqual("Block Template", values["doctype"])
		self.assertEqual("Steps on a rail", values["template_name"])
		self.assertEqual("Steps", values["category"])
		self.assertEqual("https://hub.test/files/hub-block-steps.rail-1.png", values["preview"])
		self.assertEqual((2, 2), (values["preview_width"], values["preview_height"]))
		self.assertEqual("steps.rail", values["hub_block"])
		self.assertEqual(1 * 1000 + 1, values["sort_order"])
		self.assertTrue(values["hub_hash"])
		self.assertEqual("section", json.loads(values["block"])["element"])
		frappe.db.commit.assert_called_once()

	def test_the_cards_of_a_section_are_numbered_in_the_order_the_hub_lists_them(self):
		blocks = [
			editor_block(id="steps.a", title="A"),
			editor_block(id="steps.b", title="B"),
			editor_block(id="steps.c", title="C", category="Hero"),
		]
		_result, _frappe, inserted, _seen, _fetch = self.run_sync(catalogue(*blocks))
		self.assertEqual([1001, 1002, 1], [v["sort_order"] for v in inserted])

	def test_a_card_is_written_without_the_export_to_the_apps_folder_and_the_flag_comes_back(self):
		_result, frappe, _inserted, seen, _fetch = self.run_sync(catalogue(editor_block()))
		self.assertEqual([True], seen)
		self.assertFalse(frappe.flags.in_import)

	def test_a_card_whose_block_did_not_change_is_left_alone(self):
		body = catalogue(editor_block())
		signature = T.design_signature(HANDLES, LIGHT, "fr")
		rows = [
			{
				"name": "Steps on a rail",
				"hub_block": "steps.rail",
				"hub_hash": T.card_hash(editor_block(), signature),
			}
		]
		result, frappe, inserted, _seen, _fetch = self.run_sync(body, rows=rows)
		self.assertEqual([], result["added"] + result["updated"] + result["removed"])
		self.assertEqual([], inserted)
		frappe.db.set_value.assert_not_called()

	def test_a_card_whose_block_changed_is_updated_in_place(self):
		rows = [{"name": "Steps on a rail", "hub_block": "steps.rail", "hub_hash": "stale"}]
		result, frappe, inserted, _seen, _fetch = self.run_sync(catalogue(editor_block()), rows=rows)
		self.assertEqual(["steps.rail"], result["updated"])
		self.assertEqual([], inserted)
		call = frappe.db.set_value.call_args
		self.assertEqual(("Block Template", "Steps on a rail"), call.args[:2])
		self.assertEqual("steps.rail", call.args[2]["hub_block"])

	def test_a_card_whose_block_the_hub_no_longer_offers_goes_and_only_by_the_database(self):
		rows = [{"name": "Gone block", "hub_block": "gone.one", "hub_hash": "x"}]
		result, frappe, _inserted, _seen, _fetch = self.run_sync(catalogue(), rows=rows)
		self.assertEqual(["gone.one"], result["removed"])
		frappe.db.delete.assert_called_once_with("Block Template", {"name": "Gone block"})
		frappe.delete_doc.assert_not_called()

	def test_only_the_rows_that_carry_a_hub_block_are_looked_at(self):
		_result, frappe, _inserted, _seen, _fetch = self.run_sync(catalogue(editor_block()))
		self.assertEqual(("!=", ""), frappe.get_all.call_args.kwargs["filters"]["hub_block"])

	def test_a_template_a_person_made_under_the_same_name_is_not_taken(self):
		_result, _frappe, inserted, _seen, _fetch = self.run_sync(
			catalogue(editor_block()), taken="", exists=lambda doctype, name: name == "Steps on a rail"
		)
		self.assertEqual("Steps on a rail (steps.rail)", inserted[0]["template_name"])

	def test_a_block_that_cannot_be_drawn_is_said_and_the_others_go_on(self):
		bad = editor_block(id="steps.bad", title="Bad")
		bad["tree"] = {"el": "section", "c": [{"el": "h2", "text": "Fixed words"}]}
		result, _frappe, inserted, _seen, _fetch = self.run_sync(catalogue(bad, editor_block()))
		self.assertEqual(["steps.rail"], result["added"])
		self.assertTrue(result["left_out"][0].startswith("steps.bad:"))
		self.assertEqual(1, len(inserted))

	def test_a_block_with_no_thumbnail_is_not_offered(self):
		result, _frappe, inserted, _seen, _fetch = self.run_sync(catalogue(editor_block(preview="")))
		self.assertEqual([], inserted)
		self.assertIn("thumbnail", result["left_out"][0])

	def test_an_unexpected_failure_on_one_block_is_logged_with_its_title_first_and_the_others_go_on(self):
		frappe = MagicMock()
		frappe.flags = SimpleNamespace(in_import=False)
		frappe.as_json = lambda value, indent=0: json.dumps(value)
		frappe.get_all.return_value = []
		frappe.db.get_single_value.return_value = "fr"
		frappe.db.exists.return_value = False
		calls = []

		def get_doc(values):
			doc = MagicMock()

			def insert(**kw):
				calls.append(values["hub_block"])
				if values["hub_block"] == "steps.a":
					raise RuntimeError("boom")

			doc.insert.side_effect = insert
			return doc

		frappe.get_doc.side_effect = get_doc
		body = catalogue(editor_block(id="steps.a", title="A"), editor_block(id="steps.b", title="B"))
		with (
			patch.object(T, "frappe", frappe),
			patch.object(T, "fetch", return_value=body),
			patch.object(T, "site_design", return_value=(HANDLES, LIGHT)),
		):
			result = T.sync({"builder_hub_templates": 1})
		self.assertEqual(["steps.b"], result["added"])
		self.assertEqual(["steps.a", "steps.b"], calls)
		self.assertEqual("Hub block steps.a not offered", frappe.log_error.call_args.args[0])

	def test_the_hooks_never_raise(self):
		with patch.object(T, "sync", side_effect=RuntimeError("boom")), patch.object(T, "frappe") as frappe:
			T.sync_quietly()
		self.assertEqual("Hub blocks not synced to the editor", frappe.log_error.call_args.args[0])


class TestWhatTheHubSends(unittest.TestCase):
	def fetch_with(self, message=None, error=None):
		response = MagicMock()
		response.json.return_value = {"message": message}
		if error:
			response.raise_for_status.side_effect = error
		with (
			patch("requests.get", return_value=response),
			patch("builder.api.hub_url", return_value="https://hub.test"),
		):
			return T.fetch()

	def test_a_catalogue_in_a_format_this_site_reads_is_taken(self):
		body = catalogue(editor_block())
		self.assertEqual(body, self.fetch_with(body))

	def test_a_catalogue_in_a_format_it_does_not_know_is_not(self):
		self.assertIsNone(self.fetch_with({**catalogue(), "format": 99}))

	def test_an_answer_that_is_not_a_catalogue_or_an_error_is_not(self):
		self.assertIsNone(self.fetch_with("hello"))
		self.assertIsNone(self.fetch_with({"format": 2}))
		self.assertIsNone(self.fetch_with(catalogue(), error=RuntimeError("503")))
