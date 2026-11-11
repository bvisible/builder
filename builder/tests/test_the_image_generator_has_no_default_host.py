# //// Neoffice — added file (no upstream equivalent): the legacy image generator has no default host (11.11.2026).
"""The legacy image generator used to fall back to `http://localhost:11434` (a local Ollama) and to the key "ollama".
Ollama is retired: a site with no image endpoint must say so, not connect to a port nobody serves. Nothing is sent."""

import unittest
from unittest.mock import patch

from builder.site_ai.generators.image_generator import ImageGenerator


class TestTheImageGeneratorHasNoDefaultHost(unittest.TestCase):
	def test_without_an_image_endpoint_it_names_none_and_refuses_to_generate(self):
		with patch.object(ImageGenerator, "_get_settings", return_value={}), patch("requests.post") as post:
			generator = ImageGenerator()
			self.assertIsNone(generator.base_url)
			self.assertIsNone(generator.api_key)
			with self.assertRaisesRegex(RuntimeError, "No image endpoint is configured"):
				generator.generate("a tree")
		post.assert_not_called()

	def test_a_configured_endpoint_is_called_with_its_key(self):
		settings = {"base_url": "https://images.example.test", "api_key": "k-test"}
		answer = unittest.mock.MagicMock(status_code=200)
		answer.json.return_value = {"data": []}
		with patch.object(ImageGenerator, "_get_settings", return_value=settings), patch("requests.post", return_value=answer) as post:
			try:
				ImageGenerator().generate("a tree")
			except Exception:
				pass  # what is done with an empty answer is not this test's business
		self.assertEqual(post.call_args.args[0], "https://images.example.test/v1/images/generations")
		self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer k-test")
