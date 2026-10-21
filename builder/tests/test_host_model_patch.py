# //// Neoffice — added file (no upstream equivalent): an update puts the local model on every instance that holds the host's endpoint.
"""Nine of the eleven client instances had no `nora/…` route (the providers were only created by the managed sync), so naming the
local model in site_config would have named a route nobody registered, and the page writer silently stayed on the hosted
model. The three providers are created on every migrate whether or not the instance is managed, and a patch names the local
model once, unless the site already says something about it (2026-10-21). No model is called."""

import os
import unittest
from unittest.mock import MagicMock, patch

import frappe

from builder.builder.patches import use_the_host_model_for_site_generation as host_patch
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
