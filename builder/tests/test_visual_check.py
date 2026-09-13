# //// Neoffice — added file (no upstream equivalent): the visual check waits out a web server
# //// that is restarting (builder/site_ai/nora/visual_check.py).
import unittest
from unittest.mock import patch

from builder.site_ai.nora import visual_check

CAPTURE = "builder.site_ai.inspiration.screenshotter.capture_website_screenshot"
REFUSED = RuntimeError("Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8000/about")


class TestScreenshotWaitsForTheServer(unittest.TestCase):
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
