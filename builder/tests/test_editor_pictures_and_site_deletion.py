# //// Neoffice — added file (no upstream equivalent): the assistant draws a picture once the site exists, and a site is deleted by
# //// the person who runs it, or by Nora on their word (2026-11-18).
"""Two things a person who had just built a site could not do:

* ask the editor's assistant for a new picture: only the site build drew pictures, the assistant answered that it could not;
* delete the site to start again: its record refused to go while its pages linked to it, and the conversation that built the
  site went with its home page.

What is held here: the picture tool is offered only where the site can draw, draws without placing anything, and says so; a
site deleted from the desk takes its pages and its header with it, its conversations kept; Nora deletes a site only on an answer
given after her question, and empties the only site of an instance instead of deleting it."""

import inspect
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from builder.ai.agent import registry
from builder.ai.agent.tools import images
from builder.site_ai.nora import site_builder, site_delete


class TestTheAssistantDrawsAPicture(unittest.TestCase):
	def names(self, available):
		with patch.object(images, "image_generation_available", return_value=available):
			return registry.build_default_registry().names()

	def test_the_tool_is_offered_only_where_the_site_can_draw(self):
		self.assertIn("generate_image", self.names(True))
		self.assertNotIn("generate_image", self.names(False))

	def test_it_draws_without_placing_and_says_so(self):
		ctx = SimpleNamespace(found_images=[])
		with (
			patch.object(images, "image_generation_available", return_value=True),
			patch("builder.api.generate_one_image", side_effect=["/files/a.png", "/files/b.png"]) as draw,
		):
			answer = images.run_generate_image(
				ctx,
				{
					"description": "an electrician repairing a switchboard",
					"count": 2,
					"orientation": "square",
				},
			)
		self.assertEqual(draw.call_count, 2)
		self.assertEqual(draw.call_args.kwargs, {"width": 1024, "height": 1024})
		self.assertIn("NOT on the page yet", answer)
		self.assertIn("/files/a.png", answer)
		self.assertEqual([i["url"] for i in ctx.found_images], ["/files/a.png", "/files/b.png"])

	def test_a_site_that_cannot_draw_offers_photographs(self):
		with patch.object(images, "image_generation_available", return_value=False):
			self.assertIn(
				"search_images", images.run_generate_image(SimpleNamespace(), {"description": "a roof"})
			)

	def test_a_service_that_fails_is_said(self):
		with (
			patch.object(images, "image_generation_available", return_value=True),
			patch("builder.api.generate_one_image", side_effect=RuntimeError("timeout")),
		):
			self.assertIn(
				"did not draw",
				images.run_generate_image(SimpleNamespace(found_images=[]), {"description": "a roof"}),
			)


class TestASiteDeletedFromTheDesk(unittest.TestCase):
	def test_its_pages_go_and_its_conversations_stay(self):
		pages = [
			frappe._dict(name="page-1", page_title="Accueil", route="home"),
			frappe._dict(name="page-2", page_title="Contact", route="contact"),
		]
		with (
			patch.object(site_delete.frappe, "get_all", side_effect=[pages, ["chat-1"]]),
			patch.object(site_delete.frappe.db, "set_value") as set_value,
			patch.object(site_delete.frappe, "delete_doc") as delete,
			patch.object(site_delete.frappe.db, "exists", return_value=True),
			patch.object(site_delete, "let_go_of_the_pages") as let_go,
			patch.object(site_delete, "forms_of", return_value=["second-site-contact"]),
		):
			site_delete.on_profile_trash(SimpleNamespace(name="Second site"))
		let_go.assert_called_once_with("Second site", ["page-1", "page-2"])
		set_value.assert_called_once_with(
			"Builder AI Session", "chat-1", {"page": None, "status": "Archived"}, update_modified=False
		)
		deleted = [call.args[:2] for call in delete.call_args_list]
		self.assertEqual(
			deleted,
			[
				("Builder Page", "page-1"),
				("Builder Page", "page-2"),
				(site_delete.FORM, "second-site-contact"),
				(site_delete.VARIANT, "Second site"),
			],
		)


class TestASiteThatHoldsItsHome(unittest.TestCase):
	"""On the database itself (the clone): a site's record links its home page, and frappe refuses to delete a page a record still
	links. Mocked, the deletion passed; for real, 74 of 87 test sites of osiris refused to go (2026-11-18)."""

	SITE = "ZZ Test site that holds its home"

	def setUp(self):
		if not frappe.db.exists("DocType", "Website Profile") or not frappe.db.has_column(
			"Builder Page", "neo_website_profile"
		):
			self.skipTest("the sites of the theme are not installed")
		frappe.set_user("Administrator")
		self.addCleanup(self.clean)
		frappe.get_doc(
			{"doctype": "Website Profile", "title": self.SITE, "primary_domain": "zz-holds-its-home.test"}
		).insert(ignore_permissions=True)
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Accueil",
				"route": "zz-holds-its-home",
				"neo_website_profile": self.SITE,
				"blocks": "[]",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Website Profile", self.SITE, "home_page", page.name)
		self.page = page.name

	def clean(self):
		frappe.db.rollback()
		for doctype, name in (("Builder Page", getattr(self, "page", None)), ("Website Profile", self.SITE)):
			if name and frappe.db.exists(doctype, name):
				frappe.db.delete(doctype, {"name": name})
		frappe.db.commit()

	def test_the_site_goes_with_its_home(self):
		frappe.delete_doc("Website Profile", self.SITE, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Website Profile", self.SITE))
		self.assertFalse(frappe.db.exists("Builder Page", self.page))

	def test_the_only_site_emptied_lets_go_of_its_home(self):
		self.assertEqual(site_delete.remove_pages(self.SITE)["pages"], 1)
		self.assertFalse(frappe.db.exists("Builder Page", self.page))
		self.assertFalse(frappe.db.get_value("Website Profile", self.SITE, "home_page"))


class TestASiteThatHoldsItsForm(unittest.TestCase):
	"""On the database itself (the clone): the build gives a site with a contact page its own form (the theme's Site Form), and the
	form links the site's record: the site refused to go, and the card said nothing (18.11, osiris)."""

	SITE = "ZZ Test site that holds its form"
	FORM = "zz-test-site-that-holds-its-form-contact"

	def setUp(self):
		if not frappe.db.exists("DocType", "Website Profile") or not frappe.db.exists("DocType", site_delete.FORM):
			self.skipTest("the sites of the theme are not installed")
		frappe.set_user("Administrator")
		self.addCleanup(self.clean)
		frappe.get_doc(
			{"doctype": "Website Profile", "title": self.SITE, "primary_domain": "zz-holds-its-form.test"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": site_delete.FORM,
				"title": "Contact",
				"slug": self.FORM,
				"profile": self.SITE,
				"kind": "Contact",
				"form_fields": [
					{"label": "Email", "type": "Email", "required": 1, "step": 1, "fieldname": "sender", "role": "Email"},
					{"label": "Message", "type": "Long text", "required": 1, "step": 1, "fieldname": "message", "role": "Message"},
				],
			}
		).insert(ignore_permissions=True)

	def clean(self):
		frappe.db.rollback()
		for doctype, name in ((site_delete.FORM, self.FORM), ("Website Profile", self.SITE)):
			if frappe.db.exists(doctype, name):
				frappe.db.delete(doctype, {"name": name})
		frappe.db.commit()

	def test_the_site_goes_with_its_form(self):
		self.assertEqual(site_delete.forms_of(self.SITE), [self.FORM])
		frappe.delete_doc("Website Profile", self.SITE, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Website Profile", self.SITE))
		self.assertFalse(frappe.db.exists(site_delete.FORM, self.FORM))

	def test_the_card_names_the_form(self):
		with_form = site_delete.question(self.SITE, [], only=False)
		with patch.object(site_delete, "forms_of", return_value=[]):
			without = site_delete.question(self.SITE, [], only=False)
		self.assertTrue(with_form.startswith(without) and len(with_form) > len(without))


class TestARefusedDeletionIsSaid(unittest.TestCase):
	"""A record that still uses the site (an order, an article) refuses its deletion: the person reads why, nothing is removed."""

	def test_the_refusal_is_said_and_nothing_is_removed(self):
		with (
			patch.object(site_delete.frappe.db, "exists", return_value=True),
			patch.object(site_delete, "_only_site", return_value=False),
			patch.object(site_delete, "may_delete", return_value=True),
			patch.object(site_delete, "pages_of", return_value=[]),
			patch.object(site_delete.frappe.db, "savepoint") as savepoint,
			patch.object(site_delete.frappe.db, "rollback") as rollback,
			patch.object(
				site_delete.frappe,
				"delete_doc",
				side_effect=frappe.LinkExistsError("Cannot delete: <a href='/app/sales-order/SO-1'>SO-1</a> uses it"),
			),
		):
			said = site_delete.apply_delete_site({"site": "Second site"})
		savepoint.assert_called_once_with("delete_site")
		rollback.assert_called_once_with(save_point="delete_site")
		self.assertIn("Second site", said)
		self.assertIn("SO-1", said)
		self.assertNotIn("<a", said)


class TestNoraDeletesASite(unittest.TestCase):
	"""Nora proposes, the person's click deletes: delete_site raises a confirm card and nothing else; the deletion runs
	when the card is applied (apply_delete_site), held to the right of the person who applies it."""

	def setUp(self):
		patches = [
			patch.object(
				site_delete,
				"pages_of",
				return_value=[frappe._dict(name="page-1", page_title="Accueil", route="home")],
			),
			# a site without a form: `exists` answers True for every doctype here, the theme's Site Form included, which the
			# CI does not install (its meta cannot be read there)
			patch.object(site_delete, "forms_of", return_value=[]),
			patch.object(site_delete.frappe, "has_permission", return_value=True),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		self.ctx = SimpleNamespace(session_id="a-chat", page_id="page-1")

	def exists(self, only):
		def answer(doctype, filters=None):
			if doctype == "DocType" or isinstance(filters, str):
				return True
			return not only  # another site than this one

		return patch.object(site_delete.frappe.db, "exists", side_effect=answer)

	def test_nora_only_raises_the_card(self):
		with (
			self.exists(only=False),
			patch("builder.ai.agent.pending.request_confirmation") as card,
			patch.object(site_delete.frappe, "delete_doc") as delete,
		):
			answer = site_delete.request_delete_site(self.ctx, {"website_profile": "Second site"})
		self.assertIsNone(answer)  # the turn ends on the card
		delete.assert_not_called()
		_ctx, kind, question, payload = card.call_args.args
		self.assertEqual(kind, "delete_site")
		self.assertIn("Second site", question)
		self.assertIn("Accueil", question)
		self.assertEqual(
			payload,
			{"site": "Second site", "only": False, "page": "page-1", "channel": "", "question": question},
		)

	def test_the_tool_ends_the_turn_and_takes_no_confirmation_from_the_model(self):
		self.assertEqual(site_delete.delete_site.side, "terminal")
		self.assertEqual(list(site_delete.delete_site.parameters["properties"]), ["website_profile"])

	def test_a_person_who_may_not_delete_is_refused_before_any_card(self):
		with (
			self.exists(only=False),
			patch.object(site_delete.frappe, "has_permission", return_value=False),
			patch("builder.ai.agent.pending.request_confirmation") as card,
		):
			answer = site_delete.request_delete_site(self.ctx, {"website_profile": "Second site"})
		self.assertTrue(answer.startswith("DECLINED"))
		card.assert_not_called()

	def test_the_click_deletes_the_site(self):
		with self.exists(only=False), patch.object(site_delete.frappe, "delete_doc") as delete:
			outcome = site_delete.apply_delete_site({"site": "Second site", "page": "page-1"})
		delete.assert_called_once_with("Website Profile", "Second site")
		self.assertIn("Second site", outcome)

	def test_the_click_empties_the_only_site(self):
		with (
			self.exists(only=True),
			patch.object(
				site_delete, "remove_pages", return_value={"pages": 1, "conversations_kept": 1}
			) as remove,
			patch.object(site_delete.frappe, "delete_doc") as delete,
		):
			site_delete.apply_delete_site({"site": "Main site", "page": "page-1"})
		remove.assert_called_once_with("Main site")
		delete.assert_not_called()

	def test_the_click_asks_the_right_again(self):
		with (
			self.exists(only=False),
			patch.object(site_delete.frappe, "has_permission", return_value=False),
			patch.object(site_delete.frappe, "delete_doc") as delete,
		):
			with self.assertRaises(frappe.PermissionError):
				site_delete.apply_delete_site({"site": "Second site", "page": "page-1"})
		delete.assert_not_called()

	def test_the_screen_hears_its_page_went_with_the_site(self):
		def gone(doctype, name=None):
			return (
				doctype == "Website Profile" and name == "Main site"
			)  # the emptied site stays, the page went

		with patch.object(site_delete.frappe.db, "exists", side_effect=gone):
			self.assertEqual(
				site_delete.page_gone({"site": "Main site", "page": "page-1"}), {"site": "Main site"}
			)
		with patch.object(site_delete.frappe.db, "exists", return_value=False):
			self.assertEqual(site_delete.page_gone({"site": "Second site", "page": "page-1"}), {"site": None})
		with patch.object(site_delete.frappe.db, "exists", return_value=True):
			self.assertIsNone(site_delete.page_gone({"site": "Second site", "page": "page-1"}))

	def test_another_screen_on_the_conversation_hears_it_too(self):
		payload = {"site": "Second site", "page": "page-1", "channel": "page-1"}
		with (
			patch.object(site_delete, "page_gone", return_value={"site": None}),
			patch.object(site_delete.frappe, "publish_realtime") as said,
		):
			self.assertEqual(site_delete.tell_the_screens(payload, "a-chat"), {"site": None})
		said.assert_called_once_with(
			"ai_chat_refetch_page-1",
			{"resources": ["page_gone"], "site": None, "session_id": "a-chat"},
			user=site_delete.frappe.session.user,
			after_commit=True,
		)
		with (
			patch.object(site_delete, "page_gone", return_value=None),
			patch.object(site_delete.frappe, "publish_realtime") as said,
		):
			self.assertIsNone(
				site_delete.tell_the_screens(payload, "a-chat")
			)  # the page stayed: nothing to say
		said.assert_not_called()


class TestTheCardOfADeletion(unittest.TestCase):
	"""confirm_pending_settings for a deletion: held to the site's right, not to the Builder's settings; no turn resumed;
	the screen told that its page is gone."""

	def confirm(self, settings_right, decision="apply", kind="delete_site"):
		from builder.ai import api

		message = SimpleNamespace(
			session="a-chat",
			status="pending_action",
			content="Delete the site?",
			metadata_json=json.dumps(
				{
					"status": "pending_action",
					"kind": kind,
					"payload": {"site": "Second site", "page": "page-1"},
				}
			),
		)
		with (
			patch.object(api.frappe.db, "exists", return_value=True),
			patch.object(api.frappe, "get_doc", return_value=message),
			patch.object(api.frappe, "has_permission", return_value=settings_right),
			patch.object(api.frappe.db, "get_value", return_value=api.frappe.session.user),
			patch.object(api.frappe.db, "set_value"),
			patch.object(api.AISession, "try_append_message"),
			patch(
				"builder.ai.agent.pending.apply_pending_action", return_value="The site is deleted."
			) as apply,
			patch.object(api, "resume_after_action", return_value=True) as resume,
			patch("builder.site_ai.nora.site_delete.tell_the_screens", return_value={"site": None}),
		):
			return api.confirm_pending_settings("msg-1", decision), apply, resume

	def test_the_site_manager_applies_it_without_the_builder_settings(self):
		result, apply, resume = self.confirm(settings_right=False)
		apply.assert_called_once_with("delete_site", {"site": "Second site", "page": "page-1"})
		resume.assert_not_called()
		self.assertEqual(result["page_gone"], {"site": None})
		self.assertFalse(result["resumed"])

	def test_every_other_card_keeps_the_builder_settings_gate(self):
		with self.assertRaises(frappe.PermissionError):
			self.confirm(settings_right=False, kind="home_page")


class TestTheNewSiteAfterADeletion(unittest.TestCase):
	"""« Build a new site » of the editor's window, once Nora deleted the site of the open page."""

	def page_for(self, form=None, **kwargs):
		from builder.site_ai.nora import api

		page = MagicMock(name="page")
		page.name = "page-new"
		with (
			patch.object(api, "site_home_page", return_value="shared-home") as home,
			patch.object(api, "new_site_form", return_value=form),
			patch.object(api.frappe, "new_doc", return_value=page) as new_doc,
			patch.object(api.frappe.db, "commit"),
		):
			result = api.site_creation_page(**kwargs)
		self.new_doc = new_doc
		return result, home

	def test_no_site_left_means_a_blank_page_never_a_shared_one(self):
		result, home = self.page_for(website_profile=None, fresh=1)
		home.assert_not_called()
		self.assertEqual(result, {"page_id": "page-new", "created": True})

	def test_an_instance_that_keeps_other_sites_starts_the_new_one_in_its_form(self):
		# a blank page there belonged to no site, and its build would have worked on the main site's header and footer (18.11)
		result, home = self.page_for(form="/app/site-nora?new=1", website_profile=None, fresh=1)
		self.assertEqual(result, {"page_id": None, "created": False, "open": "/app/site-nora?new=1"})
		self.new_doc.assert_not_called()
		home.assert_not_called()

	def test_the_form_is_the_answer_only_after_a_deletion(self):
		result, _home = self.page_for(form="/app/site-nora?new=1", website_profile=None)
		self.assertEqual(result["page_id"], "shared-home")

	def test_the_form_is_known_only_where_the_website_space_keeps_sites(self):
		from builder.site_ai.nora import api

		def run(page_exists=True, sites=3):
			with (
				patch.object(api.frappe.db, "exists", side_effect=lambda doctype, name=None: page_exists or doctype != "Page"),
				patch.object(api.frappe.db, "count", return_value=sites),
			):
				return api.new_site_form()

		self.assertEqual(run(), "/app/site-nora?new=1")
		self.assertIsNone(run(page_exists=False))
		self.assertIsNone(run(sites=0))

	def test_create_with_ai_still_reopens_the_page_it_finds(self):
		result, home = self.page_for(website_profile=None)
		home.assert_called_once_with(None)
		self.assertEqual(result, {"page_id": "shared-home", "created": False})

	def test_the_emptied_site_is_looked_up_even_after_a_deletion(self):
		result, home = self.page_for(website_profile="Main site", fresh=1)
		home.assert_called_once_with("Main site")
		self.assertEqual(result["page_id"], "shared-home")


class TestARebuildKeepsTheConversations(unittest.TestCase):
	def test_the_chats_of_the_replaced_pages_are_archived_before_they_go(self):
		source = inspect.getsource(site_builder.build_site)
		kept = source.index("keep_the_conversations(list(to_delete))")
		self.assertLess(
			kept, source.index('frappe.delete_doc("Builder Page", name, ignore_permissions=True, force=True)')
		)


class TestABaseSiteIsOfferedToBeGenerated(unittest.TestCase):
	"""A new instance holds the four pages generated when it was set up, shared by every site and never touched: the Nora tab
	offers to generate the site, not to change it (Jérémy, 18.11)."""

	def base(self, own, shared, may_read=True):
		from builder.site_ai.nora import site_chat

		classes = {"A Site": own, None: shared}
		with (
			patch.object(site_chat.frappe, "has_permission", return_value=may_read),
			patch.object(site_chat.frappe.db, "has_column", return_value=True),
			patch("builder.api.classify_existing_pages", side_effect=lambda profile=None: classes[profile]),
		):
			return site_chat.site_is_base("A Site")

	def test_the_pages_of_the_setup_untouched_make_a_base_site(self):
		empty = {"untouched": [], "protected": []}
		self.assertTrue(self.base(empty, {"untouched": [{"name": "p1"}], "protected": []}))

	def test_a_page_edited_or_a_site_built_is_no_base_site(self):
		empty = {"untouched": [], "protected": []}
		edited = {"untouched": [{"name": "p1"}], "protected": [{"name": "p2"}]}
		self.assertFalse(self.base(empty, edited))
		self.assertFalse(
			self.base(
				{"untouched": [{"name": "own"}], "protected": []},
				{"untouched": [{"name": "p1"}], "protected": []},
			)
		)
		self.assertFalse(self.base(empty, empty))
		self.assertFalse(self.base(empty, {"untouched": [{"name": "p1"}], "protected": []}, may_read=False))

	def test_the_tab_is_told(self):
		from builder.site_ai.nora import site_chat

		self.assertIn('"base": site_is_base(profile)', inspect.getsource(site_chat.open_chat))
