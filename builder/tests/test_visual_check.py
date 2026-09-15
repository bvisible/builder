# //// Neoffice — added file (no upstream equivalent): the visual check waits out a web server
# //// that is restarting (builder/site_ai/nora/visual_check.py).
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.site_ai.nora import visual_check

CAPTURE = "builder.site_ai.inspiration.screenshotter.capture_website_screenshot"
REFUSED = RuntimeError("Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8000/about")


class TestScreenshotWaitsForTheServer(unittest.TestCase):
	def setUp(self):
		# the log is the production log: a test writes nothing there (its lines misled a diagnosis)
		logging = patch.object(visual_check, "ai_log")
		logging.start()
		self.addCleanup(logging.stop)

	def test_a_refused_connection_is_waited_out(self):
		good = {"success": True, "file_url": "/files/shot.png"}
		with (
			patch(CAPTURE, side_effect=[REFUSED, REFUSED, good]) as capture,
			patch.object(visual_check.time, "sleep") as sleep,
		):
			self.assertEqual(visual_check._screenshot("http://127.0.0.1:8000/about", "About"), good)
		self.assertEqual(capture.call_count, 3)
		self.assertEqual(sleep.call_count, 2)
		self.assertTrue(all(call.kwargs.get("full_page") for call in capture.call_args_list))

	def test_another_failure_goes_straight_to_the_viewport(self):
		viewport = {"success": True, "file_url": "/files/top.png"}
		with (
			patch(CAPTURE, side_effect=[RuntimeError("Timeout 30000ms exceeded"), viewport]) as capture,
			patch.object(visual_check.time, "sleep") as sleep,
		):
			self.assertEqual(visual_check._screenshot("http://127.0.0.1:8000/services", "Services"), viewport)
		self.assertFalse(capture.call_args_list[1].kwargs.get("full_page"))
		sleep.assert_not_called()

	def test_the_wait_has_an_end(self):
		viewport = {"success": False, "error": "net::ERR_CONNECTION_REFUSED"}
		refusals = [REFUSED] * (visual_check.SERVER_RETRIES + 1)
		with (
			patch(CAPTURE, side_effect=[*refusals, viewport]) as capture,
			patch.object(visual_check.time, "sleep") as sleep,
		):
			self.assertEqual(visual_check._screenshot("http://127.0.0.1:8000/about", "About"), viewport)
		self.assertEqual(capture.call_count, visual_check.SERVER_RETRIES + 2)
		self.assertEqual(sleep.call_count, visual_check.SERVER_RETRIES)


class TestTheCaptureIsDropped(unittest.TestCase):
	"""Every build left one public PNG per page reviewed among the site's files (78 on a test
	instance in three days)."""

	def setUp(self):
		logging = patch.object(visual_check, "ai_log")
		logging.start()
		self.addCleanup(logging.stop)

	def review(self, **critique):
		page = {"name": "p1", "title": "About", "route": "/about"}
		shot = {"success": True, "file_url": "/files/shot.png"}
		with (
			patch.object(visual_check, "_screenshot", return_value=shot),
			patch.object(visual_check.frappe.db, "commit"),
			patch("builder.site_ai.ingestion.visual_critique.critique_screenshot", **critique),
			patch.object(visual_check, "_drop_capture") as drop,
		):
			report = visual_check.review_page(page, None, "model")
		drop.assert_called_once_with(shot)
		return report

	def test_after_the_critique_and_after_a_failure(self):
		read = SimpleNamespace(looks_professional=True, overall="", issues=[])
		self.assertTrue(self.review(return_value=(read, "model"))["professional"])
		self.assertEqual(self.review(side_effect=RuntimeError("model down"))["error"], "model down")

	def test_the_file_record_goes(self):
		with (
			patch.object(visual_check.frappe, "get_all", return_value=["f1"]) as get_all,
			patch.object(visual_check.frappe, "delete_doc") as delete,
			patch.object(visual_check.frappe.db, "commit"),
		):
			visual_check._drop_capture({"success": True, "file_url": "/files/shot.png"})
			visual_check._drop_capture(None)
		get_all.assert_called_once_with("File", filters={"file_url": "/files/shot.png"}, pluck="name")
		delete.assert_called_once_with("File", "f1", ignore_permissions=True, delete_permanently=True)


# //// Neoffice — added tests (2026-09-15): a short answer asks for a short ceiling. Every
# //// structured call used to ask for 40 000 tokens of room, and this model bills its reasoning.
class TestCritiqueCeiling(unittest.TestCase):
	def test_the_critique_asks_for_its_own_ceiling(self):
		from unittest.mock import MagicMock, patch

		from builder.site_ai.ingestion import visual_critique

		provider = MagicMock()
		with patch.object(visual_critique, "get_provider", return_value=provider):
			visual_critique.critique_screenshot("data:image/jpeg;base64,x", model="kimi")
		self.assertEqual(
			visual_critique.CRITIQUE_MAX_TOKENS,
			provider.generate_structured.call_args.kwargs["max_tokens"],
		)
		self.assertLess(visual_critique.CRITIQUE_MAX_TOKENS, 40000)

	def test_a_caller_that_names_no_ceiling_keeps_the_full_one(self):
		from builder.site_ai.providers.litellm_provider import STRUCTURED_MAX_TOKENS

		# the design brief's answer really is long: it keeps the room it needs
		self.assertEqual(40000, STRUCTURED_MAX_TOKENS)

