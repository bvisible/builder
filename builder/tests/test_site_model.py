# //// Neoffice — added file (no upstream equivalent): the host chooses the model that writes its sites.
"""A host that writes its sites with its own model (the local one) names it in site_config, `nora_site_model`.
`openai_model` and `openai_page_model` cannot say it: they also feed the managed provider, which drops an id
its gateway does not serve, and the pages were then written by whatever model the chat was on (2026-10-20).
No model is called."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.site_ai.nora.site_builder import _page_model

CHAT = SimpleNamespace(model="managed/kimi-k2.7-code")


def registered(*routes):
	return patch(
		"builder.ai.models.ModelRegistry.find",
		side_effect=lambda name: {"name": name} if name in routes else None,
	)


class TestThePageModel(unittest.TestCase):
	def conf(self, **values):
		return patch.object(frappe, "conf", frappe._dict(values))

	def test_the_host_s_site_model_wins_over_the_chat_and_the_managed_model(self):
		with (
			self.conf(nora_site_model="nora/nora"),
			registered("nora/nora", "managed/kimi-k3"),
			patch("builder.site_ai.capabilities.is_managed", return_value=True),
		):
			self.assertEqual(_page_model(CHAT), "nora/nora")

	def test_it_is_trimmed(self):
		with self.conf(nora_site_model="  nora/nora "), registered("nora/nora"):
			self.assertEqual(_page_model(CHAT), "nora/nora")

	def test_a_route_nobody_registered_changes_nothing(self):
		with (
			self.conf(nora_site_model="nora/nowhere"),
			registered("managed/kimi-k3"),
			patch("builder.site_ai.capabilities.is_managed", return_value=True),
			patch(
				"builder.site_ai.config.get_ai_settings", return_value=SimpleNamespace(page_model="kimi-k3")
			),
		):
			self.assertEqual(_page_model(CHAT), "managed/kimi-k3")

	def test_unset_the_managed_model_and_then_the_chat_decide_as_before(self):
		settings = patch(
			"builder.site_ai.config.get_ai_settings", return_value=SimpleNamespace(page_model="kimi-k3")
		)
		with (
			self.conf(),
			registered("managed/kimi-k3"),
			patch("builder.site_ai.capabilities.is_managed", return_value=True),
			settings,
		):
			self.assertEqual(_page_model(CHAT), "managed/kimi-k3")
		with self.conf(), registered(), patch("builder.site_ai.capabilities.is_managed", return_value=False):
			self.assertEqual(_page_model(CHAT), "managed/kimi-k2.7-code")

	def test_an_empty_value_is_unset(self):
		with (
			self.conf(nora_site_model=""),
			registered("nora/nora"),
			patch("builder.site_ai.capabilities.is_managed", return_value=False),
		):
			self.assertEqual(_page_model(CHAT), "managed/kimi-k2.7-code")


if __name__ == "__main__":
	unittest.main()
