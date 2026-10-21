# //// Neoffice — added file (no upstream equivalent): the judge of a build gets the pictures it was written to read,
# //// and the host's own model can judge (builder/site_ai/nora/visual_check.py, managed.py, inspiration/screenshotter.py;
# //// issue 1749, 2026-10-20). Measured on osiris: Obsidian Neoffice/Builder/Projet-Builder-v15/14, section 8.
import base64
import io
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from PIL import Image

from builder.site_ai import managed
from builder.site_ai.inspiration import screenshotter
from builder.site_ai.nora import visual_check

CRITIQUE = "builder.site_ai.ingestion.visual_critique.critique_screenshot"
LOCAL = "nora-think/nora"


def png(width, height):
	out = io.BytesIO()
	Image.new("RGB", (width, height), (240, 240, 240)).save(out, format="PNG")
	return out.getvalue()


def jpeg_size(data_url):
	return Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).size


def issue(area, problem, severity="high"):
	return SimpleNamespace(area=area, problem=problem, severity=severity, fix="")


class TestTheCaptureComesBack(unittest.TestCase):
	"""capture_and_save stored the capture in a File and dropped its bytes: the function that sizes the picture for
	the judge read them from the result, found nothing, and the judge got the stored File (a 1440 x 3706 page kept as
	622 x 1600) and no phone picture at all."""

	def saved(self, **kwargs):
		file_doc = MagicMock(file_url="/files/shot.png")
		file_doc.name = "f1"
		taken = {"success": True, "screenshot": b"the-bytes", "title": "About", "width": 1440, "height": 3706}
		with (
			patch.object(screenshotter.WebsiteScreenshotter, "capture", return_value=taken),
			patch.object(screenshotter.frappe, "get_doc", return_value=file_doc),
		):
			return screenshotter.WebsiteScreenshotter().capture_and_save("http://127.0.0.1:8000/about", **kwargs)

	def test_the_bytes_are_handed_back_only_when_asked(self):
		self.assertNotIn("screenshot", self.saved())
		self.assertEqual(self.saved(keep_bytes=True)["screenshot"], b"the-bytes")
		self.assertEqual(self.saved(keep_bytes=True)["file_url"], "/files/shot.png")

	def test_the_helper_passes_the_request_down(self):
		with patch.object(screenshotter.WebsiteScreenshotter, "capture_and_save", return_value={"success": True}) as save:
			screenshotter.capture_website_screenshot("http://x/", keep_bytes=True)
			screenshotter.capture_website_screenshot("http://x/")
		self.assertTrue(save.call_args_list[0].kwargs["keep_bytes"])
		self.assertFalse(save.call_args_list[1].kwargs["keep_bytes"])

	def test_the_visual_check_asks_for_them_on_every_capture(self):
		with patch(screenshotter.__name__ + ".capture_website_screenshot", return_value={"success": True}) as capture:
			visual_check._screenshot("http://127.0.0.1:8000/about", "About")
			visual_check.capture_phone("http://127.0.0.1:8000/about")
		self.assertTrue(all(call.kwargs.get("keep_bytes") for call in capture.call_args_list), capture.call_args_list)

	def test_with_the_bytes_the_judge_gets_a_picture_it_can_read(self):
		desk = visual_check._readable_data_url({"screenshot": png(1440, 3706)})
		phone = visual_check._readable_data_url({"screenshot": png(375, 4390)})
		self.assertEqual(jpeg_size(desk), (visual_check.READ_WIDTH, round(3706 * visual_check.READ_WIDTH / 1440)))
		# a phone page is cropped to the top, never squashed
		self.assertEqual(jpeg_size(phone), (375, visual_check.READ_MAX_HEIGHT))

	def test_without_them_there_is_no_picture_and_that_was_the_bug(self):
		self.assertIsNone(visual_check._readable_data_url({"success": True, "file_url": "/files/shot.png"}))


class TestWhichJudgeAndWhichInstructions(unittest.TestCase):
	def known(self, rows):
		return patch.multiple(
			"builder.ai.models.ModelRegistry",
			find=lambda name: rows.get(name),
			supports_vision=lambda name: bool((rows.get(name) or {}).get("vision")),
		)

	def test_the_host_s_own_lane_is_the_judge_when_no_hosted_reader_exists(self):
		rows = {LOCAL: {"vision": True}, "nora/nora": {"vision": True}}
		with self.known(rows), patch.object(frappe, "conf", {}), patch.object(visual_check, "local_judge_models", return_value=[LOCAL]):
			self.assertEqual(visual_check.judge_model("nora/nora"), LOCAL)

	def test_a_hosted_reader_still_comes_first(self):
		rows = {LOCAL: {"vision": True}, "managed/kimi-k3": {"vision": True}}
		with self.known(rows), patch.object(frappe, "conf", {}), patch.object(visual_check, "local_judge_models", return_value=[LOCAL]):
			self.assertEqual(visual_check.judge_model("nora/nora"), "managed/kimi-k3")

	def test_the_local_judge_can_be_asked_for_by_name(self):
		rows = {LOCAL: {"vision": True}, "managed/kimi-k3": {"vision": True}}
		with self.known(rows), patch.object(frappe, "conf", {"nora_review_model": LOCAL}):
			self.assertEqual(visual_check.judge_model("nora/nora"), LOCAL)

	def test_a_lane_that_cannot_see_is_not_a_judge_and_the_writer_reads_when_nobody_else_can(self):
		rows = {LOCAL: {"vision": False}}
		with self.known(rows), patch.object(frappe, "conf", {}), patch.object(visual_check, "local_judge_models", return_value=[LOCAL]):
			self.assertEqual(visual_check.judge_model("nora/nora"), "nora/nora")

	def test_the_instructions_follow_the_judge(self):
		rows = [
			{"name": LOCAL, "provider": "Nora Think"},
			{"name": "nora-judge/nora", "provider": "Nora Judge"},
			{"name": "managed/kimi-k3", "provider": "Managed"},
		]
		with patch("builder.ai.models.load_models", return_value=rows), patch.object(frappe, "conf", {}):
			self.assertEqual(visual_check.judge_style(LOCAL), "evidence")
			self.assertEqual(visual_check.judge_style("nora-judge/nora"), "evidence")
			self.assertEqual(visual_check.judge_style("managed/kimi-k3"), "default")
			self.assertEqual(visual_check.judge_style("not/registered"), "default")
		with patch("builder.ai.models.load_models", return_value=rows), patch.object(frappe, "conf", {"nora_review_style": "evidence"}):
			self.assertEqual(visual_check.judge_style("managed/kimi-k3"), "evidence")
		with patch("builder.ai.models.load_models", side_effect=RuntimeError("no table")), patch.object(frappe, "conf", {}):
			self.assertEqual(visual_check.judge_style(LOCAL), "default")

	def test_a_judge_that_fails_has_a_replacement_of_the_other_kind(self):
		rows = {LOCAL: {"vision": True}, "nora-judge/nora": {"vision": True}, "managed/kimi-k3": {"vision": True}}
		lanes = [LOCAL, "nora-judge/nora"]
		with self.known(rows), patch.object(visual_check, "local_judge_models", return_value=lanes):
			self.assertEqual(visual_check.fallback_judge("managed/kimi-k3"), LOCAL)
			# the point is the local model: the host's other lane reads before the hosted K3 does (2026-10-21)
			self.assertEqual(visual_check.fallback_judge(LOCAL), "nora-judge/nora")
			self.assertEqual(visual_check.fallback_judge("nora-judge/nora"), LOCAL)
		only_one = {LOCAL: {"vision": True}, "managed/kimi-k3": {"vision": True}}
		with self.known(only_one), patch.object(visual_check, "local_judge_models", return_value=[LOCAL]):
			self.assertEqual(visual_check.fallback_judge(LOCAL), "managed/kimi-k3")
		del rows["managed/kimi-k3"]
		with self.known(rows), patch.object(visual_check, "local_judge_models", return_value=lanes):
			self.assertEqual(visual_check.fallback_judge(LOCAL), "nora-judge/nora")
		with self.known({}), patch.object(visual_check, "local_judge_models", return_value=[]):
			self.assertIsNone(visual_check.fallback_judge("managed/kimi-k3"))


class TestTwoReadsAndAFallback(unittest.TestCase):
	def setUp(self):
		logging = patch.object(visual_check, "ai_log")
		logging.start()
		self.addCleanup(logging.stop)

	def review(self, reads, style="evidence", fallback=None):
		"""reads: what each call of the critique gives (a critique, or an exception)."""
		page = {"name": "p1", "title": "About", "route": "/about", "type": "about"}
		measured = {"status": 200, "widths": {}}
		with (
			patch.object(visual_check, "measure_page", return_value=measured),
			patch.object(visual_check, "_screenshot", return_value={"success": True, "file_url": "/files/x.png"}),
			patch.object(visual_check, "capture_phone", return_value={"success": True, "file_url": "/files/phone.png"}),
			patch.object(visual_check, "_readable_data_url", return_value="data:image/jpeg;base64,x"),
			patch.object(visual_check, "_drop_capture"),
			patch.object(visual_check, "judge_style", side_effect=lambda model: style if model == "judge" else "evidence"),
			patch.object(visual_check, "fallback_judge", return_value=fallback),
			patch.object(visual_check.frappe.db, "commit"),
			patch(CRITIQUE, side_effect=[r if isinstance(r, Exception) else (r, "judge") for r in reads]) as critique,
		):
			report = visual_check.review_page(page, "A Site", "judge")
		return report, critique

	def read(self, professional, *issues, overall="the page"):
		return SimpleNamespace(looks_professional=professional, overall=overall, issues=list(issues))

	def test_a_page_the_judge_likes_is_read_once(self):
		report, critique = self.review([self.read(True)])
		self.assertTrue(report["professional"])
		self.assertEqual((report["reads"], critique.call_count), (1, 1))

	def test_a_refusal_is_read_again_and_two_reads_that_disagree_let_the_page_stand(self):
		report, critique = self.review([self.read(False, issue("Hero", "text overlaps")), self.read(True, issue("Footer", "dense", "low"))])
		self.assertTrue(report["professional"])
		self.assertEqual((report["reads"], critique.call_count), (2, 2))
		self.assertFalse(visual_check.refused(report))
		# what stands is what the second, favourable, read said
		self.assertEqual([i["area"] for i in report["issues"]], [])

	def test_two_refusals_are_a_refusal_with_every_point_once(self):
		report, _ = self.review(
			[
				self.read(False, issue("Hero", "The number overlaps the heading"), issue("Cards", "text cut off")),
				self.read(False, issue("hero ", "the number overlaps the heading"), issue("Form", "labels unreadable")),
			]
		)
		self.assertFalse(report["professional"])
		self.assertTrue(visual_check.refused(report))
		self.assertEqual(report["reads"], 2)
		self.assertEqual(sorted(i["area"] for i in report["issues"]), ["Cards", "Form", "Hero"])

	def test_a_second_read_that_fails_leaves_the_first_one_standing(self):
		report, _ = self.review([self.read(False, issue("Hero", "text overlaps")), RuntimeError("lane busy")])
		self.assertFalse(report["professional"])
		self.assertEqual(report["reads"], 1)
		self.assertIsNone(report["error"])

	def test_a_hosted_judge_is_read_once_whatever_it_says(self):
		report, critique = self.review([self.read(False, issue("Hero", "text overlaps"))], style="default")
		self.assertFalse(report["professional"])
		self.assertEqual((report["reads"], critique.call_count), (1, 1))

	def test_a_judge_that_fails_is_replaced_once(self):
		report, critique = self.review([RuntimeError("account suspended"), self.read(True)], style="default", fallback=LOCAL)
		self.assertTrue(report["professional"])
		self.assertEqual(report["judge"], LOCAL)
		self.assertEqual(critique.call_args_list[1].kwargs["model"], LOCAL)
		self.assertEqual(critique.call_args_list[1].kwargs["style"], "evidence")

	def test_without_a_replacement_the_failure_is_reported_as_before(self):
		report, _ = self.review([RuntimeError("account suspended")], style="default", fallback=None)
		self.assertEqual(report["error"], "account suspended")

	def test_a_lane_with_another_lane_behind_it_waits_ninety_seconds_not_five_minutes_for_its_slot(self):
		from contextlib import nullcontext

		with (
			patch.object(visual_check, "local_judge_models", return_value=["judge"]),
			patch("builder.ai.llm.busy_wait_limit", return_value=nullcontext()) as limit,
		):
			self.review([self.read(True)], fallback="other-lane")
		limit.assert_called_once_with(visual_check.JUDGE_BUSY_WAIT_SECONDS)
		self.assertEqual(visual_check.JUDGE_BUSY_WAIT_SECONDS, 90)

	def test_a_judge_with_nothing_behind_it_keeps_the_default_wait(self):
		from contextlib import nullcontext

		with (
			patch.object(visual_check, "local_judge_models", return_value=["judge"]),
			patch("builder.ai.llm.busy_wait_limit", return_value=nullcontext()) as limit,
		):
			self.review([self.read(True)], fallback=None)
		limit.assert_called_once_with(None)
		# and a hosted judge, which is not one of the host's lanes, keeps it too
		with (
			patch.object(visual_check, "local_judge_models", return_value=["some-lane"]),
			patch("builder.ai.llm.busy_wait_limit", return_value=nullcontext()) as limit,
		):
			self.review([self.read(True)], fallback="other")
		limit.assert_called_once_with(None)

	def test_the_judge_is_given_the_phone_picture(self):
		_, critique = self.review([self.read(True)])
		self.assertEqual(critique.call_args.kwargs["extra_images"], ["data:image/jpeg;base64,x"])


class TestTheHostSLanesAreProviders(unittest.TestCase):
	def sync(self, conf, existing_providers=()):
		fake = MagicMock()
		fake.conf = conf
		fake.db.exists.side_effect = lambda doctype, name=None: doctype == "DocType" or name in existing_providers
		fake.get_all.return_value = []
		with patch.object(managed, "frappe", fake):
			return managed.sync_nora_judge_providers(), fake

	def test_each_lane_the_host_has_becomes_a_provider(self):
		on, fake = self.sync({"nora_api_key": "k", "nora_base_url": "https://plain/v1", "nora_thinking_url": "https://think/v1"})
		self.assertEqual(on, ["Nora Think", "Nora Judge"])
		made = [call.args[0] for call in fake.new_doc.call_args_list]
		self.assertEqual(made, ["Builder AI Provider", "Builder AI Provider"])
		prefixes = [call.args[0]["model_id"] for call in fake.get_doc.call_args_list if isinstance(call.args[0], dict)]
		self.assertEqual(prefixes, ["nora", "nora"])

	def test_a_lane_the_host_lost_is_switched_off(self):
		on, fake = self.sync({"nora_api_key": "k", "nora_base_url": "https://plain/v1"}, existing_providers=("Nora Think",))
		self.assertEqual(on, ["Nora Judge"])
		fake.db.set_value.assert_any_call("Builder AI Provider", "Nora Think", "enabled", 0)

	def test_without_a_key_nothing_is_created(self):
		on, fake = self.sync({"nora_base_url": "https://plain/v1", "nora_thinking_url": "https://think/v1"})
		self.assertEqual(on, [])
		fake.new_doc.assert_not_called()

	def test_the_lanes_are_not_offered_as_conversation_models(self):
		from builder.ai.models import ModelRegistry

		for provider in ("Nora Vision", "Nora Think", "Nora Judge"):
			self.assertTrue(ModelRegistry.is_host_vision({"provider": provider}))
		self.assertFalse(ModelRegistry.is_host_vision({"provider": "Managed"}))

	def test_the_managed_sync_leaves_them_on(self):
		self.assertTrue({"Nora Vision", "Nora Think", "Nora Judge"} <= set(managed.HOST_ONLY_PROVIDERS))


class TestTheInstructions(unittest.TestCase):
	def test_the_judge_instructions_are_chosen_by_style(self):
		from builder.site_ai.ingestion import visual_critique

		provider = MagicMock()
		with patch.object(visual_critique, "get_provider", return_value=provider):
			visual_critique.critique_screenshot("data:image/jpeg;base64,x", model="m", style="evidence")
			visual_critique.critique_screenshot("data:image/jpeg;base64,x", model="m")
			visual_critique.critique_screenshot("data:image/jpeg;base64,x", model="m", style="unknown")
		systems = [call.kwargs["system_prompt"] for call in provider.generate_structured.call_args_list]
		self.assertEqual(systems[0], visual_critique.EVIDENCE_SYSTEM)
		self.assertEqual(systems[1], visual_critique._CRITIQUE_SYSTEM)
		self.assertEqual(systems[2], visual_critique._CRITIQUE_SYSTEM)
		# the verdict starts from "professional", and the judge does not proof-read
		self.assertIn("default verdict is PROFESSIONAL", visual_critique.EVIDENCE_SYSTEM)
		self.assertIn("Do NOT proof-read", visual_critique.EVIDENCE_SYSTEM)
