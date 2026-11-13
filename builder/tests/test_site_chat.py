# //// Neoffice — added file (no upstream equivalent): Nora's conversation about a whole site, the Website space's
# //// « Nora » tab (2026-11-13).
"""Nora's conversation about a whole site (builder.site_ai.nora.site_chat and site_changes).

What the person sees under each answer is computed from the pages themselves: a section whose text changed, a photo
replaced, a section added or removed. The tests feed block trees as the editor stores them, so they need no page and
no site; the few frappe calls the endpoints make are patched.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.site_ai.nora import site_changes, site_chat


def block(block_id, element="div", children=None, **fields):
	return {"blockId": block_id, "element": element, "children": children or [], **fields}


def page(*sections):
	return block("root", "div", list(sections), originalElement="body")


def hours(text="Lundi à vendredi 8 h – 18 h", heading="Nos horaires"):
	return block(
		"hours",
		"section",
		[block("hours-title", "h2", innerHTML=heading), block("hours-text", "p", innerHTML=text)],
	)


def hero(src="/files/atelier.jpg", color="#141414"):
	return block(
		"hero",
		"section",
		[
			block("hero-title", "h1", innerHTML="L'atelier"),
			block("hero-photo", "img", attributes={"src": src}),
		],
		baseStyles={"color": color},
	)


class TestSectionChanges(unittest.TestCase):
	def test_nothing_changed_gives_no_section(self):
		self.assertEqual(site_changes.section_changes(page(hero(), hours()), page(hero(), hours())), [])

	def test_new_text_is_a_text_change_of_its_section(self):
		changes = site_changes.section_changes(
			page(hero(), hours()), page(hero(), hours(text="Samedi 9 h – 12 h"))
		)
		self.assertEqual(changes, [{"block_id": "hours", "label": "Nos horaires", "kinds": ["text"]}])

	def test_a_replaced_picture_is_a_photo_not_a_look(self):
		changes = site_changes.section_changes(page(hero()), page(hero(src="/files/soir.jpg")))
		self.assertEqual(changes[0]["kinds"], ["photo"])
		self.assertEqual(changes[0]["label"], "L'atelier")

	def test_a_colour_is_a_look(self):
		changes = site_changes.section_changes(page(hero()), page(hero(color="#AA3700")))
		self.assertEqual(changes[0]["kinds"], ["look"])

	def test_added_and_removed_sections(self):
		changes = site_changes.section_changes(
			page(hero(), hours()),
			page(hours(), block("faq", "section", [block("q", "h2", innerHTML="Questions")])),
		)
		self.assertEqual([c["kinds"] for c in changes], [["added"], ["removed"]])
		self.assertEqual(changes[0]["label"], "Questions")
		self.assertEqual(changes[1]["label"], "L'atelier")
		self.assertIsNone(
			changes[1]["block_id"], "a section that left the page has nothing to open in the editor"
		)

	def test_label_falls_back_on_the_name_then_the_words(self):
		named = block("s", "section", [block("t", "p", innerHTML="Bienvenue chez nous")], blockName="Bandeau")
		self.assertEqual(site_changes.section_label(named), "Bandeau")
		nameless = block("s", "section", [block("t", "p", innerHTML="Bienvenue chez nous")])
		self.assertEqual(site_changes.section_label(nameless), "Bienvenue chez nous")
		technical = block("s", "section", [block("t", "p", innerHTML="Bienvenue")], blockName="<section>")
		self.assertEqual(site_changes.section_label(technical), "Bienvenue")

	def test_blocks_parse_from_the_stored_text(self):
		self.assertEqual(site_changes.parse_blocks(json.dumps([page(hero())]))["blockId"], "root")
		self.assertIsNone(site_changes.parse_blocks("not json"))
		self.assertIsNone(site_changes.parse_blocks(""))


class TestPageState(unittest.TestCase):
	def test_a_draft_differing_from_the_page_is_not_online_yet(self):
		self.assertEqual(
			site_changes.page_state({"draft_blocks": "[2]", "blocks": "[1]", "published": 1}), "draft"
		)

	def test_published_and_offline(self):
		self.assertEqual(
			site_changes.page_state({"draft_blocks": None, "blocks": "[1]", "published": 1}), "published"
		)
		self.assertEqual(
			site_changes.page_state({"draft_blocks": None, "blocks": "[1]", "published": 0}), "offline"
		)

	def test_the_home_route_is_the_root_of_the_site(self):
		self.assertEqual(site_changes.visitor_route("home"), "/")
		self.assertEqual(site_changes.visitor_route("/index"), "/")
		self.assertEqual(site_changes.visitor_route("contact"), "/contact")


class TestSites(unittest.TestCase):
	SITES = ({"name": "Main"}, {"name": "Shop"})

	def test_the_first_readable_site_by_default(self):
		self.assertEqual(site_chat.chosen_site(None, self.SITES), "Main")
		self.assertEqual(site_chat.chosen_site("Shop", self.SITES), "Shop")

	def test_a_site_the_reader_cannot_read_is_refused_not_swapped(self):
		with self.assertRaises(frappe.PermissionError):
			site_chat.chosen_site("Someone else's", self.SITES)

	def test_an_instance_without_profiles_is_one_site(self):
		self.assertIsNone(site_chat.chosen_site(None, []))


class TestOpenPage(unittest.TestCase):
	def ctx(self, **fields):
		return SimpleNamespace(
			user="nora@example.com", site_profile="Main", switch_page=lambda page_id: "", tree=None, **fields
		)

	def test_another_sites_page_is_refused(self):
		with (
			patch("builder.ai.agent.tools.query.resolve_page_reference", return_value=("p-other", "")),
			patch("builder.ai.agent.tools.site_scope.other_site_of", return_value="Shop"),
		):
			result = site_chat.run_open_page(self.ctx(), {"page": "/"})
		self.assertTrue(result.startswith("FAILED"))
		self.assertIn("another site", result)

	def test_an_unknown_page_lists_the_sites_pages(self):
		with (
			patch(
				"builder.ai.agent.tools.query.resolve_page_reference",
				return_value=(None, "no page named 'Equipe'"),
			),
			patch.object(site_chat, "pages_line", return_value='"Contact" /contact'),
		):
			result = site_chat.run_open_page(self.ctx(), {"page": "Equipe"})
		self.assertIn('"Contact" /contact', result)

	def test_a_page_the_person_may_not_write_is_refused(self):
		with (
			patch("builder.ai.agent.tools.query.resolve_page_reference", return_value=("p1", "")),
			patch("builder.ai.agent.tools.site_scope.other_site_of", return_value=None),
			patch.object(site_chat.frappe.db, "get_value", return_value=("Contact", "contact", 0)),
			patch.object(site_chat.frappe, "has_permission", return_value=False),
		):
			result = site_chat.run_open_page(self.ctx(), {"page": "Contact"})
		self.assertIn("may not change", result)

	def test_open_page_is_offered_to_the_sites_conversation_only(self):
		from builder.ai.agent.registry import build_default_registry

		self.assertNotIn(
			"open_page", build_default_registry().names(), "the editor's agent works on its open page"
		)


class TestSwitchPage(unittest.TestCase):
	def runner(self):
		runner = site_chat.SiteChatRunner.__new__(site_chat.SiteChatRunner)
		runner.page_id, runner.tree, runner.pending_state, runner.revert_snapshot = (
			"home",
			"home-tree",
			None,
			"snap-home",
		)
		runner.site_snapshots = {}
		return runner

	def test_a_failed_switch_leaves_the_open_page_as_it_was(self):
		runner = self.runner()
		runner.load_page = (
			lambda page_id: "FAILED: page contact is being edited by another AI task right now."
		)
		self.assertTrue(runner.switch_page("contact").startswith("FAILED"))
		self.assertEqual(
			(runner.page_id, runner.tree, runner.revert_snapshot), ("home", "home-tree", "snap-home")
		)

	def test_the_first_snapshot_of_a_page_is_kept(self):
		runner = self.runner()
		runner.load_page = lambda page_id: ""
		runner.switch_page("contact")
		self.assertEqual(runner.page_id, "contact")
		self.assertEqual(runner.site_snapshots, {"home": "snap-home"})


class TestResume(unittest.TestCase):
	def test_a_conversation_of_the_tab_resumes_in_its_own_runner(self):
		with patch.object(site_chat, "is_site_session", return_value=True):
			job = site_chat.resume_job("s1")
		self.assertIs(job, site_chat.run_resumed_site_job)
		self.assertNotIn("<locals>", job.__qualname__, "the queue finds a job by its import path")

	def test_the_editors_conversation_keeps_the_editors_runner(self):
		with patch.object(site_chat, "is_site_session", return_value=False):
			self.assertIsNone(site_chat.resume_job("s1"))


class TestDeskAnswers(unittest.TestCase):
	def test_send_answers_with_a_plain_200(self):
		"""The desk's frappe.call runs its callback for a 200 only: a 202 (the editor's endpoint gives one) left the tab
		without its conversation, deaf to every event of the turn (seen on osiris, 13.11)."""
		import inspect

		self.assertNotIn("http_status_code", inspect.getsource(site_chat.send))


class TestSiteScopes(unittest.TestCase):
	def test_a_site_counts_its_own_pages_and_the_shared_ones(self):
		with patch.object(site_chat.frappe.db, "has_column", return_value=True):
			self.assertEqual(
				site_chat.site_scopes("Main"),
				[{"neo_website_profile": "Main"}, {"neo_website_profile": ("is", "not set")}],
			)
			self.assertEqual(site_chat.site_scopes(None), [{"neo_website_profile": ("is", "not set")}])
		with patch.object(site_chat.frappe.db, "has_column", return_value=False):
			self.assertEqual(site_chat.site_scopes("Main"), [{}])


class TestWholeSiteChanges(unittest.TestCase):
	def test_a_single_doctype_is_read_from_its_singles_row(self):
		"""get_single_value refuses `modified` (no field of the meta): the cards of the pages were lost with it (13.11)."""
		since = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-36500)
		self.assertTrue(site_chat.changed_since("System Settings", since))
		self.assertFalse(site_chat.changed_since("System Settings", frappe.utils.add_to_date(None, days=1)))

	def test_the_pages_cards_survive_a_failure_of_the_whole_sites(self):
		runner = site_chat.SiteChatRunner.__new__(site_chat.SiteChatRunner)
		runner.site_before, runner.site_profile, runner.site_started = {}, None, frappe.utils.now_datetime()
		with (
			patch.object(runner, "pages_written_meanwhile", return_value=[]),
			patch.object(runner, "site_wide_kinds", side_effect=frappe.ValidationError("boom")),
			patch.object(site_chat.frappe, "log_error") as logged,
		):
			self.assertEqual(runner.site_changes(), [])
		logged.assert_called_once()


class TestLiveStates(unittest.TestCase):
	def test_a_card_tells_the_page_as_it_is_now(self):
		"""Published after the turn, a page's card says « online » and leads to the page online."""
		page_now = frappe._dict(name="p1", route="contact", published=1, draft_blocks=None, blocks="[1]")
		messages = [
			{"role": "user", "metadata": {"siteChat": "Main"}},
			{
				"role": "assistant",
				"metadata": {
					"changes": [
						{"kind": "page", "page": "p1", "state": "draft", "sections": [{"block_id": "b1"}]},
						{"kind": "page", "page": "gone", "state": "draft"},
						{"kind": "chrome", "state": "site"},
					]
				},
			},
		]
		with (
			patch.object(site_chat.frappe.db, "has_column", return_value=False),
			patch.object(
				site_chat.frappe.db,
				"get_value",
				side_effect=lambda dt, name, *a, **k: page_now if name == "p1" else None,
			),
			patch.object(site_changes, "site_origin", return_value="https://example.test"),
		):
			cards = site_chat.with_live_states(messages)[1]["metadata"]["changes"]
		self.assertEqual(cards[0]["state"], "published")
		self.assertEqual(cards[0]["links"]["online"], "https://example.test/contact")
		self.assertTrue(cards[0]["links"]["editor"].endswith("/page/p1?block=b1"))
		self.assertEqual((cards[1]["state"], cards[1]["links"]), ("deleted", {}))
		self.assertEqual(cards[2]["state"], "site", "a whole-site card is left as it was")


class TestATurnWaitingInTheQueueIsRunning(unittest.TestCase):
	"""A turn of the tab queued behind a busy worker holds no lock yet: the tab took it for one that had ended and fell
	silent (13.11, osiris's default queue thousands of jobs long). Running = its lock, or its named job still queued."""

	def test_a_queued_turn_without_lock_is_running(self):
		with (
			patch.object(site_chat.AISession, "is_session_running", return_value=False),
			patch("builder.site_ai.nora.api.turn_state", return_value={"running": True}),
		):
			self.assertTrue(site_chat.turn_running("s1"))

	def test_a_turn_at_work_is_running_and_none_is_not(self):
		with (
			patch.object(site_chat.AISession, "is_session_running", return_value=True),
			patch("builder.site_ai.nora.api.turn_state", return_value={"running": False}),
		):
			self.assertTrue(site_chat.turn_running("s1"))
		with (
			patch.object(site_chat.AISession, "is_session_running", return_value=False),
			patch("builder.site_ai.nora.api.turn_state", return_value={"running": False}),
		):
			self.assertFalse(site_chat.turn_running("s1"))
		self.assertFalse(site_chat.turn_running(None))
