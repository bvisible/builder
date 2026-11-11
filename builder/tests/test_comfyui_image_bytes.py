# //// Neoffice — added file (no upstream equivalent): ComfyUI hands back a picture's bytes, saved nowhere, to a
# //// caller that works on them before it saves anything (builder/site_ai/generators/comfyui_client.py,
# //// neoffice-maintenance#2573).
import unittest
from unittest.mock import patch

from builder.site_ai.generators import comfyui_client


class TestComfyUIImageBytes(unittest.TestCase):
	def run_generation(self, call):
		queued = []

		def run_workflow(workflow):
			queued.append(workflow)
			return b"the picture"

		with (
			patch.object(comfyui_client, "_run_workflow", side_effect=run_workflow),
			patch.object(comfyui_client, "_save_png", return_value="/files/gen_saved.png") as save,
			patch.object(comfyui_client, "ai_log"),
		):
			result = call()
		return result, queued, save

	def test_the_bytes_come_back_and_nothing_is_saved(self):
		result, queued, save = self.run_generation(
			lambda: comfyui_client.generate_image_bytes("a logo", width=1024, height=512)
		)
		self.assertEqual(result, b"the picture")
		save.assert_not_called()
		latent = queued[0]["7"]["inputs"]
		self.assertEqual((latent["width"], latent["height"]), (1024, 512))
		self.assertEqual(queued[0]["4"]["inputs"]["text"], "a logo")

	def test_generate_image_still_saves_the_same_picture(self):
		result, queued, save = self.run_generation(
			lambda: comfyui_client.generate_image("a loaf of bread", width=512, height=512, seed=7)
		)
		self.assertEqual(result, "/files/gen_saved.png")
		save.assert_called_once_with(b"the picture", prefix="gen")
		self.assertEqual(queued[0]["8"]["inputs"]["seed"], 7)

	def test_the_template_workflow_is_never_mutated(self):
		self.run_generation(lambda: comfyui_client.generate_image_bytes("a logo", width=1024, height=512))
		self.assertEqual(comfyui_client._WF_GENERATE["4"]["inputs"]["text"], "")
		self.assertEqual(comfyui_client._WF_GENERATE["7"]["inputs"]["width"], 1024)
		self.assertEqual(comfyui_client._WF_GENERATE["7"]["inputs"]["height"], 1024)
