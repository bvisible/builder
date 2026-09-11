# //// Neoffice — added file (no upstream equivalent): which models a conversation is offered.
import unittest
from unittest.mock import MagicMock, patch

from builder.ai.models import ModelRegistry
from builder.site_ai.managed import NORA_PROVIDER_NAME

# as load_models() returns them: creation order, the host's vision endpoint seeded first
ROWS = [
	{"name": "nora/nora", "label": "Nora vision", "provider": NORA_PROVIDER_NAME, "vision": True},
	{"name": "managed/chat-model", "label": "chat-model", "provider": "Managed", "vision": True},
	{"name": "managed/page-model", "label": "page-model", "provider": "Managed", "vision": True},
]


def seeded_catalog():
	return patch.object(ModelRegistry, "catalog", return_value=[dict(r) for r in ROWS])


class TestModelPicker(unittest.TestCase):
	def test_the_conversation_starts_on_the_chat_model(self):
		"""The picker starts on its first entry, and a client has no picker at all: with the
		vision endpoint seeded first, every conversation ran on the OCR model."""
		settings = MagicMock()
		settings.get_password.return_value = None
		with seeded_catalog(), patch("builder.ai.llm.provider_api_key", return_value="key"), patch(
			"frappe.get_single", return_value=settings
		):
			names = [m["name"] for group in ModelRegistry.available() for m in group["models"]]
		self.assertEqual(names, ["managed/chat-model", "managed/page-model"])

	def test_an_unknown_selection_falls_back_to_a_chat_model(self):
		with seeded_catalog():
			self.assertEqual(ModelRegistry.get_default("openrouter"), "managed/chat-model")
			# a model named explicitly still passes through
			self.assertEqual(ModelRegistry.get_default("managed/page-model"), "managed/page-model")

	def test_the_vision_endpoint_still_resolves_for_its_callers(self):
		with seeded_catalog():
			self.assertEqual(ModelRegistry.find("nora/nora")["label"], "Nora vision")
			self.assertTrue(ModelRegistry.supports_vision("nora/nora"))
