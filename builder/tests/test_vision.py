# //// Neoffice — added file (no upstream equivalent): tests of the photo description (D-11).
"""describe_image: which model reads the photo, and the three ways of coming back without a
description, each its own. No model and no network: the provider and the image loader are stood
in for."""

import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from builder.site_ai import vision

DATA_URL = "data:image/jpeg;base64,AAAA"
ANSWER = "Sac à dos rouge en toile, vu de face"


class FakeProvider:
	def __init__(self, model, sees, answer, error):
		self.model, self.sees, self.answer, self.error = model, sees, answer, error
		self.calls = []

	def supports_vision(self):
		return self.sees

	def generate(self, prompt, system_prompt=None, images=None, **kwargs):
		self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "images": images})
		if self.error:
			raise self.error
		return self.answer


class Settings:
	def __init__(self, model):
		self.model = model


@contextmanager
def staged(nora=None, general="managed/kimi-k3", seeing=("nora/nora", "managed/kimi-k3"), answer=ANSWER, error=None, data_url=DATA_URL):
	"""The registry, the provider factory and the image loader stood in for; yields the providers made, by model."""
	made = {}

	def factory(name=None, model=None, **kwargs):
		made[model] = FakeProvider(model, model in seeing, answer, error)
		return made[model]

	with ExitStack() as stack:
		stack.enter_context(patch("builder.site_ai.managed.nora_vision_model", return_value=nora))
		stack.enter_context(patch("builder.site_ai.config.get_ai_settings", return_value=Settings(general)))
		stack.enter_context(patch("builder.site_ai.providers.get_provider", side_effect=factory))
		stack.enter_context(patch("builder.site_ai.providers.base.BaseProvider._image_to_data_url", return_value=data_url))
		stack.enter_context(patch.object(vision, "site_language", return_value="fr"))
		stack.enter_context(patch.object(vision, "ai_log"))
		yield made


class TestWhoReads(unittest.TestCase):
	"""Nora Vision first, then the general model, and only a model that sees."""

	def test_nora_vision_reads_first(self):
		with staged(nora="nora/nora") as made:
			self.assertEqual(vision.describe_image("/files/a.jpg"), ANSWER)
		self.assertEqual(len(made["nora/nora"].calls), 1)
		self.assertNotIn("managed/kimi-k3", made)

	def test_the_general_model_reads_when_nora_is_not_seeded(self):
		with staged(nora=None) as made:
			vision.describe_image("/files/a.jpg")
		self.assertEqual(len(made["managed/kimi-k3"].calls), 1)

	def test_a_nora_that_cannot_see_gives_way(self):
		with staged(nora="nora/nora", seeing=("managed/kimi-k3",)) as made:
			vision.describe_image("/files/a.jpg")
		self.assertEqual(made["nora/nora"].calls, [])
		self.assertEqual(len(made["managed/kimi-k3"].calls), 1)


class TestThreeFailures(unittest.TestCase):
	"""No description comes back three ways, and the merchant must read the right one."""

	def test_no_model_that_sees(self):
		with staged(nora=None, seeing=()) as made, self.assertRaises(vision.NoVisionModel) as caught:
			vision.describe_image("/files/a.jpg")
		self.assertEqual(caught.exception.reason, "no_vision_model")
		self.assertTrue(all(p.calls == [] for p in made.values()))

	def test_an_unreadable_photo_is_refused_before_the_model_is_asked(self):
		with staged(nora="nora/nora", data_url=None) as made, self.assertRaises(vision.ImageUnreadable) as caught:
			vision.describe_image("/files/missing.jpg")
		self.assertEqual(caught.exception.reason, "image_unreadable")
		self.assertEqual(made["nora/nora"].calls, [])

	def test_an_empty_path_is_unreadable(self):
		with staged(nora="nora/nora"), self.assertRaises(vision.ImageUnreadable):
			vision.describe_image("")

	def test_a_model_error(self):
		with staged(nora="nora/nora", error=RuntimeError("timed out")), self.assertRaises(vision.DescriptionFailed) as caught:
			vision.describe_image("/files/a.jpg")
		self.assertEqual(caught.exception.reason, "model_failed")

	def test_an_empty_answer(self):
		with staged(nora="nora/nora", answer="  \n "), self.assertRaises(vision.DescriptionFailed):
			vision.describe_image("/files/a.jpg")

	def test_the_three_are_distinct_and_share_a_base(self):
		kinds = (vision.NoVisionModel, vision.ImageUnreadable, vision.DescriptionFailed)
		self.assertEqual(len({kind.reason for kind in kinds}), 3)
		self.assertTrue(all(issubclass(kind, vision.DescribeImageError) for kind in kinds))


class TestTheRequest(unittest.TestCase):
	"""What the model receives: the photo read beforehand, the language, the shop's words."""

	def test_the_photo_travels_as_the_data_url_read_before_the_call(self):
		with staged(nora="nora/nora") as made:
			vision.describe_image("/files/a.jpg")
		self.assertEqual(made["nora/nora"].calls[0]["images"], [DATA_URL])
		self.assertEqual(made["nora/nora"].calls[0]["system_prompt"], vision.SYSTEM_PROMPT)

	def test_the_site_language_is_the_default(self):
		with staged(nora="nora/nora") as made:
			vision.describe_image("/files/a.jpg")
		self.assertIn("(language code: fr)", made["nora/nora"].calls[0]["prompt"])

	def test_an_explicit_language_wins(self):
		with staged(nora="nora/nora") as made:
			vision.describe_image("/files/a.jpg", language="de")
		self.assertIn("(language code: de)", made["nora/nora"].calls[0]["prompt"])

	def test_the_context_names_the_product(self):
		with staged(nora="nora/nora") as made:
			vision.describe_image("/files/a.jpg", context="Sac à dos Alpine 30 L, rouge")
		self.assertIn("Sac à dos Alpine 30 L, rouge", made["nora/nora"].calls[0]["prompt"])

	def test_the_rules_forbid_inventing(self):
		self.assertIn("Never add a brand", vision.SYSTEM_PROMPT)
		self.assertIn(f"at most {vision.ALT_TARGET_LENGTH} characters", vision.SYSTEM_PROMPT)


class TestTheCleanAnswer(unittest.TestCase):
	"""An alt text is one clean sentence, whatever the model wraps around it."""

	def test_a_label_and_quotes_are_dropped(self):
		self.assertEqual(vision.clean_alt_text('Alt text: "Sac à dos rouge en toile"'), "Sac à dos rouge en toile")
		self.assertEqual(vision.clean_alt_text("Texte alternatif : « Veste noire »"), "Veste noire")

	def test_the_first_line_that_says_something(self):
		self.assertEqual(vision.clean_alt_text("Alt text:\nVeste noire, vue de dos\nSecond line"), "Veste noire, vue de dos")

	def test_quotes_inside_stay(self):
		self.assertEqual(vision.clean_alt_text("Planche 'Alpine' vue de dessus"), "Planche 'Alpine' vue de dessus")

	def test_a_long_answer_is_cut_at_a_word(self):
		text = vision.clean_alt_text("mot " * 80)
		self.assertLessEqual(len(text), vision.ALT_MAX_LENGTH)
		self.assertTrue(text.endswith("mot"))

	def test_nothing_is_nothing(self):
		self.assertEqual(vision.clean_alt_text(None), "")
		self.assertEqual(vision.clean_alt_text("   "), "")
