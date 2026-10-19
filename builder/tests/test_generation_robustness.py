# //// Neoffice — added file (no upstream equivalent): tests of what a weaker or a shared model does to a build.
"""A site build used to stop, or ship half a page, on four things a small model does and a shared
gate allows (2026-10-19, the local 27B model behind a capped, gated endpoint):

- a repeater named in kebab-case, whose key became `data.event-services = ...` (a SyntaxError when the
  page was saved, on page three of five);
- a boolean or a null in a repeater item, written as JSON (`true`) and read as Python (NameError, a 500
  on the published route);
- a provider answering 503 "llm busy, retry after 5s", which failed the call after one retry;
- a stream cut at the provider's output ceiling, built from its prefix as if it were whole;
- a brief naming a font the chrome's Select does not offer ("Lora"), a validation error that stopped the
  build before its first page.

No model is called: the streams and the provider are simulated."""

import datetime
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe
import litellm
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai import page_writer as pw
from builder.site_ai.nora import site_builder
from builder.utils import execute_script

KEBAB_PAGE = """
el: div
name: body
c:
  - el: section
    repeat:
      data: event-services
      items:
        - event-title: Bouquets de mariée
          detail: Portés ou posés
        - event-title: Décoration de salle
          detail: Sur mesure
      item:
        el: div
        c:
          - el: h3
            bind: {innerHTML: event-title}
          - el: p
            text: "{{ item.event-title }}"
"""


class TestRepeaterNames(unittest.TestCase):
	def test_an_identifier_is_made_of_anything(self):
		for raw, expected in (
			("event-services", "event_services"),
			("Événements été", "Evenements_ete"),
			("3 offres", "_3_offres"),
			("class", "class_"),
			("", "items"),
			("a.b", "a_b"),
		):
			self.assertEqual(pw.python_identifier(raw), expected, raw)

	def test_an_identifier_never_collides(self):
		self.assertEqual(pw.python_identifier("a-b", taken={"a_b"}), "a_b_2")

	def test_a_kebab_repeater_gives_a_script_python_can_read(self):
		blocks, script = pw.expand_page_yaml(KEBAB_PAGE)
		self.assertTrue(blocks)
		compile(script, "<data script>", "exec")  # was a SyntaxError
		self.assertTrue(script.startswith("data.event_services = "))
		repeater = blocks[0]["children"][0]
		self.assertEqual(repeater["dataKey"]["key"], "event_services")
		title = repeater["children"][0]["children"][0]
		self.assertEqual(
			title["dynamicValues"], [{"key": "event_title", "property": "innerHTML", "type": "key"}]
		)
		self.assertIn("event_title", json.loads(script.split(" = ", 1)[1])[0])

	def test_the_moustache_follows_the_renamed_field(self):
		blocks, _ = pw.expand_page_yaml(KEBAB_PAGE)
		text = blocks[0]["children"][0]["children"][0]["children"][1]
		bound = [dv["key"] for dv in text.get("dynamicValues") or []]
		self.assertEqual(bound, ["event_title"])

	def test_a_page_that_was_fine_is_left_alone(self):
		parsed = {
			"el": "div",
			"c": [
				{"el": "div", "repeat": {"data": "features", "items": [{"title": "A"}], "item": {"el": "p"}}}
			],
		}
		self.assertEqual(pw.normalise_repeaters(parsed), 0)

	def test_a_date_in_an_item_does_not_stop_the_page(self):
		script = pw.build_repeater_data_script(
			{
				"el": "div",
				"repeat": {
					"data": "news",
					"items": [{"day": datetime.date(2026, 10, 19)}],
					"item": {"el": "p"},
				},
			}
		)
		self.assertIn("2026-10-19", script)


class TestDataScriptLiterals(FrappeTestCase):
	def run_script(self, script):
		data = frappe._dict()
		execute_script(script, {"data": data}, "test")
		return data

	def test_json_booleans_and_null_are_readable(self):
		data = self.run_script('data.x = [{"featured": true, "sold": false, "note": null}]')
		self.assertEqual(data.x, [{"featured": True, "sold": False, "note": None}])

	def test_python_literals_still_work(self):
		data = self.run_script('data.x = [{"featured": True}]')
		self.assertEqual(data.x, [{"featured": True}])


class TestBusyProvider(unittest.TestCase):
	def busy(self, message="llm busy with long-context jobs, retry after 5s"):
		return litellm.ServiceUnavailableError(message=message, llm_provider="openai", model="nora")

	def test_a_busy_answer_gives_a_pause(self):
		self.assertEqual(llm.busy_pause(self.busy()), 5.0)

	def test_the_pause_is_bounded(self):
		self.assertEqual(llm.busy_pause(self.busy("llm busy, retry after 900s")), 30.0)

	def test_other_failures_are_not_waited_for(self):
		self.assertIsNone(llm.busy_pause(self.busy("service unavailable")))
		self.assertIsNone(llm.busy_pause(ValueError("llm busy")))
		self.assertIsNone(
			llm.busy_pause(litellm.RateLimitError(message="quota", llm_provider="openai", model="m"))
		)

	def test_a_busy_provider_is_asked_again(self):
		answers = [self.busy(), self.busy(), "answer"]

		def completion(**kwargs):
			value = answers.pop(0)
			if isinstance(value, Exception):
				raise value
			return value

		with patch.object(llm.litellm, "completion", completion), patch.object(llm.time, "sleep") as sleep:
			self.assertEqual(llm.completion_waiting_for_a_busy_provider(model="m"), "answer")
		self.assertEqual(sleep.call_count, 2)

	def test_a_quota_refusal_goes_straight_up(self):
		def completion(**kwargs):
			raise litellm.RateLimitError(
				message="account suspended due to insufficient balance", llm_provider="openai", model="m"
			)

		with patch.object(llm.litellm, "completion", completion), patch.object(llm.time, "sleep") as sleep:
			with self.assertRaises(litellm.RateLimitError):
				llm.completion_waiting_for_a_busy_provider(model="m")
		sleep.assert_not_called()

	def test_the_wait_has_an_end(self):
		def completion(**kwargs):
			raise self.busy()

		with (
			patch.object(llm.litellm, "completion", completion),
			patch.object(llm.time, "sleep"),
			patch.object(llm, "BUSY_WAIT_SECONDS", -1),
		):
			with self.assertRaises(litellm.ServiceUnavailableError):
				llm.completion_waiting_for_a_busy_provider(model="m")


def chunk(text="", finish=None):
	return SimpleNamespace(
		choices=[
			SimpleNamespace(delta=SimpleNamespace(content=text, reasoning_content=None), finish_reason=finish)
		],
		usage=None,
	)


class FakeCtx:
	def is_cancelled(self):
		return False

	def record_usage(self, chunk, model=None):
		pass


class TestCutStream(FrappeTestCase):
	def stream(self, finish):
		class Stream:
			def __iter__(self):
				yield chunk("el: div\n")
				yield chunk("c: []", finish)

			def close(self):
				pass

		return Stream()

	def test_a_stream_cut_at_the_ceiling_is_an_error_carrying_its_text(self):
		with patch.object(llm, "complete", return_value=self.stream("length")):
			with self.assertRaises(site_builder.OutputCut) as raised:
				site_builder._stream_text(FakeCtx(), "m", [], {})
		self.assertEqual(raised.exception.text, "el: div\nc: []")

	def test_the_last_attempt_keeps_what_was_written(self):
		with patch.object(llm, "complete", return_value=self.stream("length")):
			text = site_builder._stream_text(FakeCtx(), "m", [], {}, keep_cut=True)
		self.assertEqual(text, "el: div\nc: []")

	def test_a_stream_that_ended_normally_is_returned(self):
		with patch.object(llm, "complete", return_value=self.stream("stop")):
			self.assertEqual(site_builder._stream_text(FakeCtx(), "m", [], {}), "el: div\nc: []")


CHROME_FONTS = "Inter\nMontserrat\nPoppins\nRoboto\nOpen Sans\nLato\nRaleway\nSource Sans 3\nNunito\nMerriweather\nDM Sans\nManrope\nSpace Grotesk"


def config_offering(options):
	return SimpleNamespace(meta=SimpleNamespace(get_field=lambda field: SimpleNamespace(options=options)))


class TestChromeFont(unittest.TestCase):
	def test_an_offered_font_is_kept(self):
		self.assertEqual(site_builder.chrome_font(config_offering(CHROME_FONTS), "body_font", "Lato"), "Lato")

	def test_a_serif_the_chrome_lacks_becomes_the_offered_serif(self):
		self.assertEqual(
			site_builder.chrome_font(config_offering(CHROME_FONTS), "heading_font", "Lora"), "Merriweather"
		)
		self.assertEqual(
			site_builder.chrome_font(config_offering(CHROME_FONTS), "heading_font", "Playfair Display"),
			"Merriweather",
		)

	def test_a_geometric_face_becomes_space_grotesk(self):
		self.assertEqual(
			site_builder.chrome_font(config_offering(CHROME_FONTS), "heading_font", "Syne"), "Space Grotesk"
		)

	def test_anything_else_becomes_inter(self):
		self.assertEqual(
			site_builder.chrome_font(config_offering(CHROME_FONTS), "body_font", "Some Unknown Face"), "Inter"
		)

	def test_a_chrome_without_inter_falls_back_to_its_first_option(self):
		self.assertEqual(
			site_builder.chrome_font(config_offering("Lato\nRoboto"), "body_font", "Lora"), "Lato"
		)

	def test_a_field_without_options_is_not_second_guessed(self):
		self.assertEqual(site_builder.chrome_font(config_offering(""), "body_font", "Lora"), "Lora")
