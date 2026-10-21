# //// Neoffice — added file (no upstream equivalent): an update puts the local model on every instance that holds the host's endpoint.
"""Nine of the eleven client instances had no `nora/…` route (the providers were only created by the managed sync), so naming the
local model in site_config would have named a route nobody registered, and the page writer silently stayed on the hosted
model. The three providers are created on every migrate whether or not the instance is managed, and a patch names the local
model once, unless the site already says something about it (2026-10-21). No model is called."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from builder.ai.models import ModelRegistry
from builder.builder.patches import enable_image_generation_where_the_host_has_it as images_patch
from builder.builder.patches import use_the_host_model_for_site_generation as host_patch
from builder.builder.patches import use_the_host_model_for_the_assistant as assistant_patch
from builder.site_ai import managed

HOST = {"nora_base_url": "https://plain/v1", "nora_thinking_url": "https://think/v1", "nora_api_key": "k"}


class TestTheProvidersExistOnAnUnmanagedInstance(unittest.TestCase):
	def sync(self, conf, doctype_exists=True):
		fake = MagicMock()
		fake.conf = conf
		fake.db.exists.side_effect = lambda doctype, name=None: doctype == "DocType" and doctype_exists
		fake.get_all.return_value = []
		with patch.object(managed, "frappe", fake):
			return managed.sync_nora_providers(), fake

	def test_the_three_providers_are_created_without_ai_managed(self):
		on, fake = self.sync(dict(HOST))
		self.assertNotIn("ai_managed", HOST)
		self.assertEqual(on, ["Nora Vision", "Nora Think", "Nora Judge"])
		self.assertEqual(fake.new_doc.call_count, 3)

	def test_without_the_reasoning_lane_it_is_the_two_that_exist(self):
		on, _fake = self.sync({k: v for k, v in HOST.items() if k != "nora_thinking_url"})
		self.assertEqual(on, ["Nora Vision", "Nora Judge"])

	def test_nothing_is_created_without_the_endpoint_or_the_key(self):
		for conf in ({}, {"nora_base_url": "https://plain/v1"}, {"nora_api_key": "k"}):
			on, fake = self.sync(conf)
			self.assertEqual(on, [], conf)
			fake.new_doc.assert_not_called()

	def test_a_bench_that_has_not_migrated_yet_has_no_provider_table(self):
		on, fake = self.sync(dict(HOST), doctype_exists=False)
		self.assertEqual(on, [])
		fake.new_doc.assert_not_called()

	def test_the_model_id_follows_the_host(self):
		with patch.object(managed.frappe, "conf", frappe._dict()):
			self.assertEqual(managed.nora_model_id(), "nora")
		with patch.object(managed.frappe, "conf", frappe._dict(nora_model="nora-27b")):
			self.assertEqual(managed.nora_model_id(), "nora-27b")
		with patch.object(managed.frappe, "conf", frappe._dict(nora_ocr_model="ocr", nora_model="nora-27b")):
			self.assertEqual(managed.nora_model_id(), "ocr")

	def test_every_migrate_runs_it(self):
		from builder import install

		self.assertIs(install.sync_nora_providers, managed.sync_nora_providers)


class TestThePatchNamesTheLocalModelOnce(unittest.TestCase):
	def run_patch(self, conf, providers_on):
		with (
			patch.object(frappe, "conf", frappe._dict(conf)),
			patch.object(host_patch, "sync_nora_providers", return_value=providers_on),
			patch.object(host_patch, "update_site_config") as update,
		):
			host_patch.execute()
		return update

	def test_an_instance_that_holds_the_host_endpoint_writes_with_the_local_model(self):
		update = self.run_patch(dict(HOST), ["Nora Vision", "Nora Think", "Nora Judge"])
		update.assert_called_once_with("nora_site_model", "nora/nora")

	def test_the_model_id_is_the_host_s(self):
		update = self.run_patch({**HOST, "nora_model": "nora-27b"}, ["Nora Vision"])
		update.assert_called_once_with("nora_site_model", "nora/nora-27b")

	def test_a_value_already_there_is_not_touched(self):
		update = self.run_patch({**HOST, "nora_site_model": "managed/kimi-k3"}, ["Nora Vision"])
		update.assert_not_called()

	def test_an_empty_value_is_a_decision_for_the_hosted_model_and_stays(self):
		update = self.run_patch({**HOST, "nora_site_model": ""}, ["Nora Vision"])
		update.assert_not_called()

	def test_the_instance_the_host_has_not_wired_is_left_alone(self):
		# no endpoint or key: the providers are not created, so the route does not exist
		update = self.run_patch({}, [])
		update.assert_not_called()

	def test_a_route_that_would_not_exist_is_not_named(self):
		# the judge lanes alone are not the writer's route
		update = self.run_patch(dict(HOST), ["Nora Think", "Nora Judge"])
		update.assert_not_called()

	def test_the_providers_are_created_before_the_route_is_named(self):
		order = []
		with (
			patch.object(frappe, "conf", frappe._dict(HOST)),
			patch.object(
				host_patch,
				"sync_nora_providers",
				side_effect=lambda: order.append("providers") or ["Nora Vision"],
			),
			patch.object(host_patch, "update_site_config", side_effect=lambda *a: order.append("config")),
		):
			host_patch.execute()
		self.assertEqual(order, ["providers", "config"])


class TestThePatchIsListed(unittest.TestCase):
	"""An entry without its file kills `bench migrate` on the whole fleet (see the note in patches.txt)."""

	def test_it_is_in_the_post_model_sync_section_and_its_module_exists(self):
		root = os.path.dirname(os.path.dirname(__file__))
		with open(os.path.join(root, "patches.txt")) as f:
			text = f.read()
		name = "builder.builder.patches.use_the_host_model_for_site_generation"
		self.assertIn(name, text.split("[post_model_sync]")[1])
		self.assertTrue(
			os.path.exists(
				os.path.join(root, "builder", "patches", "use_the_host_model_for_site_generation.py")
			)
		)


if __name__ == "__main__":
	unittest.main()


class TestThePatchesOfTheAssistantAndTheImages(unittest.TestCase):
	def run_assistant_patch(self, conf, providers_on):
		with (
			patch.object(frappe, "conf", frappe._dict(conf)),
			patch.object(assistant_patch, "sync_nora_providers", return_value=providers_on),
			patch.object(assistant_patch, "update_site_config") as update,
		):
			assistant_patch.execute()
		return update

	def test_the_assistant_is_put_on_the_host_model(self):
		self.run_assistant_patch(dict(HOST), ["Nora Vision"]).assert_called_once_with(
			"nora_assistant_model", "nora/nora"
		)

	def test_an_assistant_model_already_named_stays(self):
		self.run_assistant_patch(
			{**HOST, "nora_assistant_model": "managed/kimi-k3"}, ["Nora Vision"]
		).assert_not_called()
		self.run_assistant_patch({**HOST, "nora_assistant_model": ""}, ["Nora Vision"]).assert_not_called()

	def test_no_route_no_assistant_change(self):
		self.run_assistant_patch({}, []).assert_not_called()

	def run_images_patch(self, conf):
		with (
			patch.object(frappe, "conf", frappe._dict(conf)),
			patch.object(images_patch, "update_site_config") as update,
		):
			images_patch.execute()
		return update

	def test_the_flag_is_written_where_the_endpoint_is_and_the_flag_is_missing_or_zero(self):
		endpoint = {"comfyui_url": "https://images/", "nora_api_key": "k"}
		self.run_images_patch(endpoint).assert_called_once_with("image_generation_enabled", 1)
		self.run_images_patch({**endpoint, "image_generation_enabled": 0}).assert_called_once_with(
			"image_generation_enabled", 1
		)
		self.run_images_patch(
			{"comfyui_url": "https://images/", "comfyui_api_key": "c"}
		).assert_called_once_with("image_generation_enabled", 1)

	def test_the_flag_is_left_alone_when_it_is_on_or_there_is_no_endpoint(self):
		endpoint = {"comfyui_url": "https://images/", "nora_api_key": "k"}
		self.run_images_patch({**endpoint, "image_generation_enabled": 1}).assert_not_called()
		self.run_images_patch({"nora_api_key": "k"}).assert_not_called()
		self.run_images_patch({"comfyui_url": "https://images/"}).assert_not_called()

	def test_both_are_listed_in_the_post_model_sync_section(self):
		root = os.path.dirname(os.path.dirname(__file__))
		with open(os.path.join(root, "patches.txt")) as f:
			section = f.read().split("[post_model_sync]")[1]
		for name in ("use_the_host_model_for_the_assistant", "enable_image_generation_where_the_host_has_it"):
			self.assertIn(f"builder.builder.patches.{name}", section)
			self.assertTrue(os.path.exists(os.path.join(root, "builder", "patches", f"{name}.py")))


class TestTheAssistantRunsOnTheHostModel(unittest.TestCase):
	"""The clients' assistant ran on a hosted Kimi because the picker's first model was the answer (2026-10-21)."""

	def host(self, routes=("nora/nora", "managed/kimi-k3"), conf=None, user="someone"):
		stack = [
			patch.object(frappe, "conf", frappe._dict({"nora_assistant_model": "nora/nora", **(conf or {})})),
			patch.object(frappe, "session", SimpleNamespace(user=user)),
			patch.object(
				ModelRegistry, "find", side_effect=lambda name: {"name": name} if name in routes else None
			),
			patch.object(
				ModelRegistry, "catalog", return_value=[{"name": "managed/kimi-k3", "provider": "Managed"}]
			),
		]
		return stack

	def run_with(self, stack, fn):
		from contextlib import ExitStack

		with ExitStack() as es:
			for cm in stack:
				es.enter_context(cm)
			return fn()

	def test_the_host_model_answers_whatever_the_browser_asks_for(self):
		stack = self.host()
		self.assertEqual(self.run_with(stack, lambda: ModelRegistry.get_default("openrouter")), "nora/nora")
		self.assertEqual(
			self.run_with(self.host(), lambda: ModelRegistry.get_default("managed/kimi-k3")), "nora/nora"
		)

	def test_the_hosts_administrator_keeps_the_choice(self):
		self.assertEqual(
			self.run_with(
				self.host(user="Administrator"), lambda: ModelRegistry.get_default("managed/kimi-k3")
			),
			"managed/kimi-k3",
		)
		self.assertEqual(
			self.run_with(self.host(user="Administrator"), lambda: ModelRegistry.get_default("openrouter")),
			"nora/nora",
		)

	def test_a_route_nobody_registered_changes_nothing(self):
		stack = self.host(routes=("managed/kimi-k3",))
		self.assertEqual(
			self.run_with(stack, lambda: ModelRegistry.get_default("openrouter")), "managed/kimi-k3"
		)
		self.assertIsNone(
			self.run_with(self.host(routes=("managed/kimi-k3",)), ModelRegistry.host_assistant_model)
		)

	def test_unset_the_assistant_decides_as_before(self):
		stack = self.host(conf={"nora_assistant_model": ""})
		self.assertEqual(
			self.run_with(stack, lambda: ModelRegistry.get_default("managed/kimi-k3")), "managed/kimi-k3"
		)
		self.assertIsNone(
			self.run_with(self.host(conf={"nora_assistant_model": ""}), ModelRegistry.host_assistant_model)
		)

	def picker(self, host_model, managed, user):
		from builder.site_ai import capabilities

		with (
			patch.object(capabilities, "is_managed", return_value=managed),
			patch.object(capabilities, "get_assistant_name", return_value="Nora"),
			patch.object(
				ModelRegistry, "host_assistant_model", return_value="nora/nora" if host_model else None
			),
			patch.object(frappe, "session", SimpleNamespace(user=user)),
		):
			return capabilities.ai_capabilities()["model_picker"]

	def test_the_picker_is_for_the_hosts_administrator_once_the_host_names_the_model(self):
		self.assertFalse(self.picker(host_model=True, managed=False, user="someone"))
		self.assertTrue(self.picker(host_model=True, managed=False, user="Administrator"))
		self.assertFalse(self.picker(host_model=True, managed=True, user="someone"))

	def test_without_a_host_model_the_picker_is_as_it_was(self):
		self.assertTrue(self.picker(host_model=False, managed=False, user="someone"))
		self.assertFalse(self.picker(host_model=False, managed=True, user="someone"))
		self.assertTrue(self.picker(host_model=False, managed=True, user="Administrator"))

	def test_a_request_about_a_page_does_not_change_the_site_chrome(self):
		"""The local model answered "translate this page" by changing the site's header and footer (2026-10-20)."""
		from builder.site_ai.nora.prompts import site_playbook
		from builder.site_ai.nora.tools import update_site_chrome

		for text in (update_site_chrome.description, site_playbook()):
			self.assertIn("THIS page", text)
		self.assertIn("never calls update_site_chrome", site_playbook())
