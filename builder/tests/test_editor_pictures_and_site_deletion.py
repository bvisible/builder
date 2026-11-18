# //// Neoffice — added file (no upstream equivalent): the assistant draws a picture once the site exists, and a site is deleted by
# //// the person who runs it, or by Nora on their word (2026-11-18).
"""Two things a person who had just built a site could not do:

* ask the editor's assistant for a new picture: only the site build drew pictures, the assistant answered that it could not;
* delete the site to start again: its record refused to go while its pages linked to it, and the conversation that built the
  site went with its home page.

What is held here: the picture tool is offered only where the site can draw, draws without placing anything, and says so; a
site deleted from the desk takes its pages and its header with it, its conversations kept; Nora deletes a site only on an answer
given after her question, and empties the only site of an instance instead of deleting it."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from builder.ai.agent import registry
from builder.ai.agent.tools import images
from builder.site_ai.nora import site_delete


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
		):
			site_delete.on_profile_trash(SimpleNamespace(name="Second site"))
		set_value.assert_called_once_with(
			"Builder AI Session", "chat-1", {"page": None, "status": "Archived"}, update_modified=False
		)
		deleted = [call.args[:2] for call in delete.call_args_list]
		self.assertEqual(
			deleted,
			[("Builder Page", "page-1"), ("Builder Page", "page-2"), (site_delete.VARIANT, "Second site")],
		)


class TestNoraDeletesASite(unittest.TestCase):
	def setUp(self):
		# Only the question's own key is kept here: every other key (the installed apps, the time zone…) goes to the real cache.
		self.cache = {}
		cache = site_delete.frappe.cache
		real = {name: getattr(cache, name) for name in ("get_value", "set_value", "delete_value")}

		def ours(key):
			return isinstance(key, str) and key.startswith("builder_delete_site_asked")

		def get_value(key, *args, **kwargs):
			return self.cache.get(key) if ours(key) else real["get_value"](key, *args, **kwargs)

		def set_value(key, value, *args, **kwargs):
			if not ours(key):
				return real["set_value"](key, value, *args, **kwargs)
			self.cache[key] = value

		def delete_value(key, *args, **kwargs):
			if not ours(key):
				return real["delete_value"](key, *args, **kwargs)
			self.cache.pop(key, None)

		patches = [
			patch.object(cache, "get_value", side_effect=get_value),
			patch.object(cache, "set_value", side_effect=set_value),
			patch.object(cache, "delete_value", side_effect=delete_value),
			patch.object(
				site_delete,
				"pages_of",
				return_value=[frappe._dict(name="page-1", page_title="Accueil", route="home")],
			),
			patch.object(site_delete.frappe, "has_permission", return_value=True),
			patch.object(site_delete.frappe.db, "commit"),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		self.ctx = SimpleNamespace(session_id=None, page_id=None)

	def exists(self, only):
		def answer(doctype, filters=None):
			if doctype == "DocType" or isinstance(filters, str):
				return True
			return not only  # another site than this one

		return patch.object(site_delete.frappe.db, "exists", side_effect=answer)

	def test_nora_asks_first(self):
		with self.exists(only=False), patch.object(site_delete.frappe, "delete_doc") as delete:
			answer = site_delete.run_delete_site(
				self.ctx, {"website_profile": "Second site", "confirmed": True}
			)
		self.assertTrue(answer.startswith("CONFIRM_NEEDED"))
		delete.assert_not_called()

	def test_after_the_yes_the_site_goes(self):
		with self.exists(only=False), patch.object(site_delete.frappe, "delete_doc") as delete:
			site_delete.run_delete_site(self.ctx, {"website_profile": "Second site"})
			answer = site_delete.run_delete_site(
				self.ctx, {"website_profile": "Second site", "confirmed": True}
			)
		self.assertTrue(answer.startswith("DONE"))
		delete.assert_called_once_with("Website Profile", "Second site")

	def test_the_only_site_is_emptied_not_deleted(self):
		with (
			self.exists(only=True),
			patch.object(
				site_delete, "remove_pages", return_value={"pages": 1, "conversations_kept": 1}
			) as remove,
			patch.object(site_delete.frappe, "delete_doc") as delete,
		):
			site_delete.run_delete_site(self.ctx, {"website_profile": "Main site"})
			answer = site_delete.run_delete_site(
				self.ctx, {"website_profile": "Main site", "confirmed": True}
			)
		remove.assert_called_once_with("Main site")
		delete.assert_not_called()
		self.assertIn("the site stays", answer)

	def test_a_yes_written_before_the_question_counts_for_nothing(self):
		ctx = SimpleNamespace(session_id="a-chat", page_id=None)
		with (
			self.exists(only=False),
			patch.object(site_delete, "_answered_since", return_value=False),
			patch.object(site_delete.frappe, "delete_doc") as delete,
		):
			site_delete.run_delete_site(ctx, {"website_profile": "Second site"})
			answer = site_delete.run_delete_site(ctx, {"website_profile": "Second site", "confirmed": True})
		self.assertTrue(answer.startswith("CONFIRM_NEEDED"))
		delete.assert_not_called()

	def test_the_editor_open_on_the_site_is_told_its_page_is_gone(self):
		ctx = SimpleNamespace(session_id=None, page_id="page-1", emit=MagicMock())
		with self.exists(only=False), patch.object(site_delete.frappe, "delete_doc"):
			site_delete.run_delete_site(ctx, {"website_profile": "Second site"})
			ctx.emit.assert_not_called()  # the question changes nothing
			answer = site_delete.run_delete_site(ctx, {"website_profile": "Second site", "confirmed": True})
		# the site is gone: no site to start the new one on
		ctx.emit.assert_called_once_with("refetch", resources=["page_gone"], site=None, after_commit=True)
		self.assertIn("the editor now offers the person", answer)

	def test_the_emptied_site_is_where_the_new_one_starts(self):
		ctx = SimpleNamespace(session_id=None, page_id="page-1", emit=MagicMock())
		with (
			self.exists(only=True),
			patch.object(site_delete, "remove_pages", return_value={"pages": 1, "conversations_kept": 1}),
			patch.object(site_delete.frappe, "delete_doc"),
		):
			site_delete.run_delete_site(ctx, {"website_profile": "Main site"})
			site_delete.run_delete_site(ctx, {"website_profile": "Main site", "confirmed": True})
		ctx.emit.assert_called_once_with(
			"refetch", resources=["page_gone"], site="Main site", after_commit=True
		)

	def test_an_editor_open_elsewhere_is_left_alone(self):
		ctx = SimpleNamespace(session_id=None, page_id="another-site-page", emit=MagicMock())
		with self.exists(only=False), patch.object(site_delete.frappe, "delete_doc"):
			site_delete.run_delete_site(ctx, {"website_profile": "Second site"})
			answer = site_delete.run_delete_site(ctx, {"website_profile": "Second site", "confirmed": True})
		ctx.emit.assert_not_called()
		self.assertNotIn("the editor now offers", answer)

	def test_a_person_who_may_not_delete_is_refused(self):
		with self.exists(only=False), patch.object(site_delete.frappe, "has_permission", return_value=False):
			self.assertTrue(
				site_delete.run_delete_site(self.ctx, {"website_profile": "Second site"}).startswith("FAILED")
			)
