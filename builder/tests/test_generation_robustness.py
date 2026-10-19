# //// Neoffice — added file (no upstream equivalent): tests of what a weaker or a shared model does to a build.
"""A site build used to stop, or ship half a page, on four things a small model does and a shared
gate allows (2026-10-19, the local 27B model behind a capped, gated endpoint):

- a repeater named in kebab-case, whose key became `data.event-services = ...` (a SyntaxError when the
  page was saved, on page three of five);
- a boolean or a null in a repeater item, written as JSON (`true`) and read as Python (NameError, a 500
  on the published route);
- a provider answering 503 "llm busy, retry after 5s", which failed the call after one retry;
- a stream cut at the provider's output ceiling (4 096 tokens on the local lane), built from its prefix
  as if it were whole: it is now resumed from its last whole line;
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
from builder.site_ai.nora import layout, site_builder, typography, visual_check
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


def iter_stream(chunks):
	class Stream:
		def __iter__(self):
			yield from chunks

		def close(self):
			pass

	return Stream()


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
		with (
			patch.object(llm, "complete", return_value=self.stream("length")),
			patch.object(site_builder, "CONTINUATION_ROUNDS", 0),
		):
			with self.assertRaises(site_builder.OutputCut) as raised:
				site_builder._stream_text(FakeCtx(), "m", [], {})
		self.assertEqual(raised.exception.text, "el: div\nc: []")

	def test_the_last_attempt_keeps_what_was_written(self):
		with (
			patch.object(llm, "complete", return_value=self.stream("length")),
			patch.object(site_builder, "CONTINUATION_ROUNDS", 0),
		):
			text = site_builder._stream_text(FakeCtx(), "m", [], {}, keep_cut=True)
		self.assertEqual(text, "el: div\nc: []")

	def test_a_cut_stream_is_resumed_from_its_last_whole_line(self):
		cut = [chunk("el: div\nc:\n  - el: p\n    te", "length")]
		rest = [chunk("    text: Hello\n", "stop")]
		calls = []

		def complete(model, messages, params, stream):
			calls.append((messages, params))
			return iter_stream(cut if len(calls) == 1 else rest)

		with patch.object(llm, "complete", complete):
			text = site_builder._stream_text(
				FakeCtx(), "m", [{"role": "user", "content": "page"}], {"max_tokens": 10}
			)
		self.assertEqual(text, "el: div\nc:\n  - el: p\n    text: Hello\n")
		messages, params = calls[1]
		self.assertEqual(messages[-1], {"role": "assistant", "content": "el: div\nc:\n  - el: p\n"})
		self.assertTrue(params["extra_body"]["continue_final_message"])
		self.assertFalse(params["extra_body"]["add_generation_prompt"])

	def test_a_stream_always_cut_is_resumed_a_few_times_then_reported(self):
		calls = []

		def complete(model, messages, params, stream):
			calls.append(1)
			return iter_stream([chunk("line\n", "length")])

		with patch.object(llm, "complete", complete):
			with self.assertRaises(site_builder.OutputCut):
				site_builder._stream_text(FakeCtx(), "m", [], {})
		self.assertEqual(len(calls), 1 + site_builder.CONTINUATION_ROUNDS)

	def test_a_provider_that_refuses_the_resume_leaves_the_page_cut(self):
		calls = []

		def complete(model, messages, params, stream):
			calls.append(1)
			if len(calls) == 1:
				return iter_stream([chunk("el: div\nc: []\nx", "length")])
			raise RuntimeError("400 unknown field continue_final_message")

		with patch.object(llm, "complete", complete):
			with self.assertRaises(site_builder.OutputCut) as raised:
				site_builder._stream_text(FakeCtx(), "m", [], {})
			self.assertEqual(raised.exception.text, "el: div\nc: []\nx")
			calls.clear()
			self.assertEqual(
				site_builder._stream_text(FakeCtx(), "m", [], {}, keep_cut=True), "el: div\nc: []\nx"
			)

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


def grid(template, kids, **screens):
	block = {
		"element": "div",
		"baseStyles": {"display": "grid", "gridTemplateColumns": template},
		"children": [{"element": "div", "baseStyles": {"gridColumn": span}} for span in kids],
	}
	for screen, styles in screens.items():
		block[screen] = styles
	return block


class TestGridPlacementsFit(unittest.TestCase):
	def test_halves_on_a_two_column_template_get_the_twelve_columns_they_were_written_for(self):
		block = grid("repeat(2, minmax(0, 1fr))", ["1 / span 6", "7 / span 6"])
		layout.fit_grid_placements([block])
		self.assertEqual(block["baseStyles"]["gridTemplateColumns"], "repeat(12, minmax(0, 1fr))")

	def test_the_phone_gets_spans_that_fit_its_single_column(self):
		block = grid(
			"repeat(2, minmax(0, 1fr))",
			["1 / span 6", "7 / span 6"],
			mobileStyles={"gridTemplateColumns": "1fr"},
		)
		layout.fit_grid_placements([block])
		self.assertEqual([k["mobileStyles"]["gridColumn"] for k in block["children"]], ["span 1", "span 1"])
		self.assertNotIn("tabletStyles", block["children"][0])

	def test_a_full_width_child_keeps_the_whole_phone_row(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))",
			["1 / -1", "1 / span 12", "span 4"],
			mobileStyles={"gridTemplateColumns": "1fr"},
		)
		layout.fit_grid_placements([block])
		kids = block["children"]
		self.assertNotIn("mobileStyles", kids[0])
		self.assertEqual(kids[1]["mobileStyles"]["gridColumn"], "1 / -1")
		self.assertEqual(kids[2]["mobileStyles"]["gridColumn"], "span 1")

	def test_a_share_of_the_row_is_kept_proportionally(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))",
			["span 6", "span 6", "span 4", "span 10"],
			tabletStyles={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		)
		layout.fit_grid_placements([block])
		self.assertEqual(
			[k["tabletStyles"]["gridColumn"] for k in block["children"]],
			["span 1", "span 1", "span 1", "span 2"],
		)

	def test_the_phone_inherits_what_the_tablet_was_given(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))",
			["span 6", "span 6"],
			tabletStyles={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
			mobileStyles={"gridTemplateColumns": "1fr"},
		)
		layout.fit_grid_placements([block])
		self.assertEqual(block["children"][0]["tabletStyles"]["gridColumn"], "span 1")
		self.assertNotIn("mobileStyles", block["children"][0])  # span 1 already fits one column

	def test_a_child_the_page_already_reset_on_the_phone_is_left_alone(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))", ["span 6", "span 6"], mobileStyles={"gridTemplateColumns": "1fr"}
		)
		block["children"][0]["mobileStyles"] = {"gridColumn": "1 / -1"}
		layout.fit_grid_placements([block])
		self.assertEqual(block["children"][0]["mobileStyles"]["gridColumn"], "1 / -1")
		self.assertEqual(block["children"][1]["mobileStyles"]["gridColumn"], "span 1")

	def test_the_desktop_layout_of_a_grid_that_fits_is_not_touched(self):
		block = grid("repeat(12, minmax(0, 1fr))", ["span 4", "span 4", "span 4"])
		layout.fit_grid_placements([block])
		self.assertEqual(block["baseStyles"]["gridTemplateColumns"], "repeat(12, minmax(0, 1fr))")
		self.assertEqual(block["children"][0]["baseStyles"], {"gridColumn": "span 4"})
		self.assertNotIn("tabletStyles", block)

	def test_a_fluid_grid_and_a_repeater_are_left_alone(self):
		fluid = grid(
			"repeat(auto-fit, minmax(16rem, 1fr))",
			["span 6", "span 6"],
			mobileStyles={"gridTemplateColumns": "1fr"},
		)
		repeater = grid("repeat(2, minmax(0, 1fr))", ["1 / span 6"])
		repeater["isRepeaterBlock"] = True
		self.assertEqual(layout.fit_grid_placements([fluid, repeater]), 0)

	def test_a_template_that_is_not_a_repeat_is_not_rewritten(self):
		block = grid("2fr 1fr", ["1 / span 6", "7 / span 6"])
		layout.fit_grid_placements([block])
		self.assertEqual(block["baseStyles"]["gridTemplateColumns"], "2fr 1fr")

	def test_placements_nobody_can_read_are_ignored(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))",
			["auto", "foo", "", "3 / 3"],
			mobileStyles={"gridTemplateColumns": "1fr"},
		)
		self.assertEqual(layout.fit_grid_placements([block]), 0)

	def test_the_extent_of_a_placement(self):
		extent = layout._extent
		self.assertEqual(extent("span 4"), (None, 4, 4))
		self.assertEqual(extent("1 / span 6"), (1, 6, 6))
		self.assertEqual(extent("7 / span 6"), (7, 12, 6))
		self.assertEqual(extent("2 / 6"), (2, 5, 4))
		self.assertEqual(extent("3"), (3, 3, 1))
		self.assertEqual(extent("1 / -1"), (1, 1, None))
		self.assertIsNone(extent("auto"))
		self.assertIsNone(extent("0 / span 2"))


class TestPhoneWidths(unittest.TestCase):
	def box(self, base, mobile=None):
		block = {"element": "div", "baseStyles": base}
		if mobile is not None:
			block["mobileStyles"] = mobile
		return block

	def test_a_wide_minimum_is_released_on_the_phone(self):
		block = self.box({"minWidth": "30rem"})
		self.assertEqual(layout.fit_phone_widths([block]), 1)
		self.assertEqual(block["mobileStyles"], {"minWidth": "0"})
		self.assertEqual(block["baseStyles"], {"minWidth": "30rem"})

	def test_a_minimum_the_page_already_released_is_left_alone(self):
		block = self.box({"minWidth": "18rem"}, {"minWidth": "12rem"})
		self.assertEqual(layout.fit_phone_widths([block]), 0)
		self.assertEqual(block["mobileStyles"], {"minWidth": "12rem"})

	def test_a_small_minimum_is_kept(self):
		for value in ("10rem", "160px", "var(--w)", "50%", "auto"):
			block = self.box({"minWidth": value})
			self.assertEqual(layout.fit_phone_widths([block]), 0, value)
			self.assertNotIn("mobileStyles", block)

	def test_a_minimum_in_viewport_units_counts_as_a_phone_width(self):
		block = self.box({"minWidth": "100vw"})
		self.assertEqual(layout.fit_phone_widths([block]), 1)

	def test_a_wide_fixed_width_is_capped_on_the_phone(self):
		block = self.box({"width": "600px"})
		self.assertEqual(layout.fit_phone_widths([block]), 1)
		self.assertEqual(block["mobileStyles"], {"maxWidth": "100%"})

	def test_a_width_that_is_already_capped_or_relative_is_left_alone(self):
		for base in (
			{"width": "600px", "maxWidth": "100%"},
			{"width": "100%"},
			{"width": "calc(100% - 2rem)"},
			{"width": "40px"},
		):
			block = self.box(base)
			self.assertEqual(layout.fit_phone_widths([block]), 0, base)

	def test_the_whole_tree_is_walked(self):
		inner = self.box({"minWidth": "30rem"})
		root = {"element": "div", "children": [{"element": "section", "children": [inner]}]}
		self.assertEqual(layout.fit_phone_widths([root]), 1)
		self.assertEqual(inner["mobileStyles"], {"minWidth": "0"})


class TestFluidTracks(unittest.TestCase):
	def test_a_bare_fr_track_stops_growing_with_its_content(self):
		for before, after in (
			("1fr", "minmax(0, 1fr)"),
			("repeat(2, 1fr)", "repeat(2, minmax(0, 1fr))"),
			("2fr 1fr", "minmax(0, 2fr) minmax(0, 1fr)"),
			("1fr 320px", "minmax(0, 1fr) 320px"),
			("minmax(0, 1fr) 1fr", "minmax(0, 1fr) minmax(0, 1fr)"),
		):
			self.assertEqual(layout._fluid(before), after, before)

	def test_a_track_list_that_is_already_fluid_is_left_alone(self):
		for value in (
			"repeat(3, minmax(0, 1fr))",
			"repeat(auto-fit, minmax(16rem, 1fr))",
			"320px minmax(0, 1fr)",
			"",
			"none",
			None,
		):
			self.assertIsNone(layout._fluid(value), value)

	def test_every_screen_of_every_grid_is_made_fluid(self):
		block = {
			"element": "div",
			"baseStyles": {"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)"},
			"tabletStyles": {"gridTemplateColumns": "1fr 1fr"},
			"mobileStyles": {"gridTemplateColumns": "1fr"},
			"children": [{"element": "div", "baseStyles": {"display": "grid", "gridTemplateColumns": "1fr"}}],
		}
		self.assertEqual(layout.fluid_tracks([block]), 4)
		self.assertEqual(block["baseStyles"]["gridTemplateColumns"], "repeat(3, minmax(0, 1fr))")
		self.assertEqual(block["tabletStyles"]["gridTemplateColumns"], "minmax(0, 1fr) minmax(0, 1fr)")
		self.assertEqual(block["mobileStyles"]["gridTemplateColumns"], "minmax(0, 1fr)")
		self.assertEqual(layout.fluid_tracks([block]), 0)  # idempotent

	def test_the_column_count_does_not_change(self):
		for before in ("repeat(2, 1fr)", "2fr 1fr", "1fr"):
			self.assertEqual(layout._tracks(layout._fluid(before)), layout._tracks(before), before)


class TestPhoneHeadings(unittest.TestCase):
	def heading(self, tag, base, tablet=None, mobile=None):
		block = {"element": tag, "baseStyles": {"fontSize": base}}
		if tablet:
			block["tabletStyles"] = tablet
		if mobile:
			block["mobileStyles"] = mobile
		return block

	def test_a_big_heading_gets_the_phone_cap_and_may_break_a_long_word(self):
		block = self.heading("h2", "3.25rem")
		self.assertEqual(typography.shrink_phone_headings([block]), 2)
		self.assertEqual(block["mobileStyles"], {"fontSize": "2.25rem", "overflowWrap": "break-word"})
		self.assertEqual(block["baseStyles"], {"fontSize": "3.25rem"})

	def test_a_pixel_size_counts_in_rem(self):
		block = self.heading("h1", "72px")
		typography.shrink_phone_headings([block])
		self.assertEqual(block["mobileStyles"]["fontSize"], "2.75rem")

	def test_a_heading_that_fits_only_gets_the_word_break(self):
		block = self.heading("h2", "2rem")
		self.assertEqual(typography.shrink_phone_headings([block]), 1)
		self.assertEqual(block["mobileStyles"], {"overflowWrap": "break-word"})

	def test_the_phone_inherits_the_tablet_size(self):
		small = self.heading("h3", "48px", tablet={"fontSize": "1.5rem"})
		typography.shrink_phone_headings([small])
		self.assertNotIn("fontSize", small["mobileStyles"])
		big = self.heading("h3", "1rem", tablet={"fontSize": "3rem"})
		typography.shrink_phone_headings([big])
		self.assertEqual(big["mobileStyles"]["fontSize"], "1.75rem")

	def test_what_the_page_wrote_for_the_phone_is_kept(self):
		block = self.heading("h2", "4rem", mobile={"fontSize": "3rem", "overflowWrap": "normal"})
		self.assertEqual(typography.shrink_phone_headings([block]), 0)
		self.assertEqual(block["mobileStyles"], {"fontSize": "3rem", "overflowWrap": "normal"})

	def test_fluid_sizes_and_other_elements_are_left_to_the_other_pass(self):
		fluid = self.heading("h1", "clamp(2rem, 6vw, 4.5rem)")
		typography.shrink_phone_headings([fluid])
		self.assertNotIn("fontSize", fluid["mobileStyles"])
		paragraph = {"element": "p", "baseStyles": {"fontSize": "4rem"}}
		self.assertEqual(typography.shrink_phone_headings([paragraph]), 0)
		self.assertNotIn("mobileStyles", paragraph)


FLAT_PAGE = """
el: div
name: body
c:
  - el: repeat
    classes: [u-grid, u-grid--3]
    data: steps
    items:
      - {num: '01', title: Demande}
      - {num: '02', title: Dispatch}
    item:
      el: div
      c:
        - el: h3
          bind: {innerHTML: title}
"""


class TestFlatRepeaters(unittest.TestCase):
	def test_a_repeater_written_flat_becomes_a_repeater(self):
		blocks, script = pw.expand_page_yaml(FLAT_PAGE)
		repeater = blocks[0]["children"][0]
		self.assertEqual(repeater["element"], "div")  # was an empty block named "repeat"
		self.assertTrue(repeater["isRepeaterBlock"])
		self.assertEqual(repeater["dataKey"]["key"], "steps")
		self.assertEqual(repeater["classes"], ["u-grid", "u-grid--3"])
		self.assertEqual(len(repeater["children"]), 1)
		compile(script, "<data script>", "exec")
		self.assertTrue(script.startswith("data.steps = "))
		self.assertEqual(
			[row["title"] for row in json.loads(script.split(" = ", 1)[1])], ["Demande", "Dispatch"]
		)

	def test_the_flat_keys_leave_the_element(self):
		parsed = {
			"el": "section",
			"items": [{"who": "X"}],
			"item": {"el": "p", "text": "{{ item.who }}"},
			"name": "team members",
		}
		self.assertTrue(pw.adopt_flat_repeater(parsed))
		self.assertEqual(parsed["el"], "section")  # a real tag stays
		self.assertNotIn("items", parsed)
		self.assertNotIn("item", parsed)
		self.assertEqual(parsed["repeat"]["data"], "team_members")  # named after the block

	def test_two_unnamed_flat_repeaters_do_not_share_their_data(self):
		page = {
			"el": "div",
			"c": [
				{"el": "repeat", "items": [{"a": 1}], "item": {"el": "p"}},
				{"el": "repeat", "items": [{"b": 2}], "item": {"el": "p"}},
			],
		}
		pw.normalise_repeaters(page)
		self.assertEqual([c["repeat"]["data"] for c in page["c"]], ["items", "items_2"])

	def test_a_flat_repeater_obeys_the_naming_rule_too(self):
		page = {
			"el": "div",
			"c": [
				{
					"el": "repeat",
					"data": "event-services",
					"items": [{"event-title": "Z"}],
					"item": {"el": "p"},
				}
			],
		}
		pw.normalise_repeaters(page)
		self.assertEqual(page["c"][0]["repeat"]["data"], "event_services")
		self.assertIn("event_title", page["c"][0]["repeat"]["items"][0])

	def test_what_is_not_a_flat_repeater_is_left_alone(self):
		ordinary = {"el": "div", "c": [{"el": "p", "text": "x"}]}
		self.assertFalse(pw.adopt_flat_repeater(ordinary))
		already = {
			"el": "div",
			"repeat": {"data": "a", "items": [], "item": {"el": "p"}},
			"item": {"el": "p"},
		}
		self.assertFalse(pw.adopt_flat_repeater(already))
		no_template = {"el": "repeat", "items": [{"a": 1}]}
		self.assertFalse(pw.adopt_flat_repeater(no_template))


GUTTER, PHONE_GUTTER = "var(--qvb-gutter)", "var(--qvb-gutter-phone)"


class TestPhoneGutters(unittest.TestCase):
	def test_a_container_that_forgot_its_phone_gutter_gets_it(self):
		block = {
			"element": "div",
			"baseStyles": {"paddingLeft": GUTTER, "paddingRight": GUTTER, "width": "100%"},
		}
		self.assertEqual(layout.fit_phone_gutters([block], GUTTER, PHONE_GUTTER), 2)
		self.assertEqual(block["mobileStyles"], {"paddingLeft": PHONE_GUTTER, "paddingRight": PHONE_GUTTER})
		self.assertEqual(block["baseStyles"]["paddingLeft"], GUTTER)

	def test_a_padding_shorthand_with_the_token_is_covered(self):
		block = {"element": "section", "baseStyles": {"padding": f"80px {GUTTER}"}}
		self.assertEqual(layout.fit_phone_gutters([block], GUTTER, PHONE_GUTTER), 1)
		self.assertEqual(block["mobileStyles"], {"padding": f"80px {PHONE_GUTTER}"})

	def test_what_the_page_wrote_for_the_phone_is_kept(self):
		block = {
			"element": "div",
			"baseStyles": {"paddingLeft": GUTTER, "paddingRight": GUTTER, "padding": f"4rem {GUTTER}"},
			"mobileStyles": {"paddingLeft": "16px", "paddingRight": "16px"},
		}
		self.assertEqual(layout.fit_phone_gutters([block], GUTTER, PHONE_GUTTER), 0)
		self.assertEqual(block["mobileStyles"], {"paddingLeft": "16px", "paddingRight": "16px"})

	def test_other_paddings_are_not_touched(self):
		block = {"element": "div", "baseStyles": {"paddingLeft": "64px", "padding": "2rem"}}
		self.assertEqual(layout.fit_phone_gutters([block], GUTTER, PHONE_GUTTER), 0)
		self.assertNotIn("mobileStyles", block)

	def test_a_site_without_a_grid_changes_nothing(self):
		block = {"element": "div", "baseStyles": {"paddingLeft": GUTTER}}
		self.assertEqual(layout.fit_phone_gutters([block], None, PHONE_GUTTER), 0)
		self.assertEqual(layout.fit_phone_gutters([block], GUTTER, GUTTER), 0)


def critique(professional, *issues):
	return SimpleNamespace(
		looks_professional=professional,
		issues=[SimpleNamespace(severity=sev, area=area, problem="p", fix="f") for sev, area in issues],
	)


class TestVerdictAboutTheChrome(unittest.TestCase):
	def test_a_verdict_resting_only_on_the_footer_is_set_aside(self):
		self.assertTrue(visual_check.verdict_is_about_the_chrome(critique(False, ("high", "Footer"))))
		self.assertTrue(
			visual_check.verdict_is_about_the_chrome(
				critique(False, ("high", "Footer"), ("medium", "Navigation menu"))
			)
		)

	def test_low_points_do_not_change_that(self):
		self.assertTrue(
			visual_check.verdict_is_about_the_chrome(
				critique(False, ("high", "Footer"), ("low", "Hero section"))
			)
		)

	def test_a_page_faulted_in_its_body_stays_refused(self):
		self.assertFalse(
			visual_check.verdict_is_about_the_chrome(
				critique(False, ("high", "Footer"), ("high", "Hero section"))
			)
		)
		self.assertFalse(
			visual_check.verdict_is_about_the_chrome(critique(False, ("medium", "Pricing cards")))
		)

	def test_a_page_called_professional_is_left_alone(self):
		self.assertFalse(visual_check.verdict_is_about_the_chrome(critique(True, ("high", "Footer"))))

	def test_an_unprofessional_verdict_with_no_serious_point_stays(self):
		self.assertFalse(visual_check.verdict_is_about_the_chrome(critique(False)))
		self.assertFalse(visual_check.verdict_is_about_the_chrome(critique(False, ("low", "Footer"))))


TEXT_IN_STYLE = """
el: div
name: body
c:
  - el: h2
    style:
      color: red
      fontSize: 2rem
      text: "1. Responsable du traitement"
  - el: p
    style:
      color: blue
    text: "Written where it belongs"
  - el: p
    style:
      color: blue
      text: "ignored, the block has its own"
    text: "The block's own text wins"
"""


class TestMisplacedKeys(unittest.TestCase):
	def test_a_text_written_inside_the_style_goes_back_to_the_block(self):
		blocks, _ = pw.expand_page_yaml(TEXT_IN_STYLE)
		heading, kept, own = blocks[0]["children"]
		self.assertEqual(heading["innerHTML"], "1. Responsable du traitement")  # was an empty block
		self.assertNotIn("text", heading["baseStyles"])
		self.assertEqual(heading["baseStyles"]["color"], "red")
		self.assertEqual(kept["innerHTML"], "Written where it belongs")
		self.assertEqual(own["innerHTML"], "The block's own text wins")

	def test_the_other_block_keys_are_hoisted_too(self):
		node = {"el": "div", "style": {"color": "red", "classes": ["u-card"], "name": "intro"}}
		self.assertEqual(pw.hoist_misplaced_keys(node), 2)
		self.assertEqual(node["classes"], ["u-card"])
		self.assertEqual(node["name"], "intro")
		self.assertEqual(node["style"], {"color": "red"})

	def test_a_clean_block_is_left_alone(self):
		node = {"el": "p", "style": {"color": "red"}, "text": "x"}
		self.assertEqual(pw.hoist_misplaced_keys(node), 0)
		self.assertEqual(node, {"el": "p", "style": {"color": "red"}, "text": "x"})
		self.assertEqual(pw.hoist_misplaced_keys({"el": "p"}), 0)
		self.assertEqual(pw.hoist_misplaced_keys({"el": "p", "style": "bold"}), 0)


class TestPhoneCollapse(unittest.TestCase):
	def test_a_twelve_column_grid_with_no_phone_layout_collapses_to_one_column(self):
		block = grid("repeat(12, minmax(0, 1fr))", ["1 / span 5", "7 / span 6"])
		layout.fit_grid_placements([block])
		self.assertEqual(block["mobileStyles"]["gridTemplateColumns"], "minmax(0, 1fr)")
		self.assertEqual([k["mobileStyles"]["gridColumn"] for k in block["children"]], ["span 1", "span 1"])
		self.assertNotIn("tabletStyles", block)  # the tablet keeps its twelve columns

	def test_four_narrow_items_keep_two_columns_on_the_phone(self):
		block = grid("repeat(12, minmax(0, 1fr))", ["span 3", "span 3", "span 3", "span 3"])
		layout.fit_grid_placements([block])
		self.assertEqual(block["mobileStyles"]["gridTemplateColumns"], "repeat(2, minmax(0, 1fr))")
		self.assertEqual({k["mobileStyles"]["gridColumn"] for k in block["children"]}, {"span 1"})

	def test_a_phone_layout_the_page_wrote_is_respected(self):
		block = grid(
			"repeat(12, minmax(0, 1fr))",
			["span 6", "span 6"],
			mobileStyles={"gridTemplateColumns": "repeat(2, 1fr)"},
		)
		layout.fit_grid_placements([block])
		self.assertEqual(block["mobileStyles"]["gridTemplateColumns"], "repeat(2, 1fr)")
		tablet = grid(
			"repeat(12, minmax(0, 1fr))", ["span 6", "span 6"], tabletStyles={"gridTemplateColumns": "1fr"}
		)
		layout.fit_grid_placements([tablet])
		self.assertNotIn("gridTemplateColumns", tablet.get("mobileStyles", {}))  # it inherits the tablet's

	def test_full_width_children_and_small_grids_are_not_collapsed(self):
		full = grid("repeat(12, minmax(0, 1fr))", ["1 / -1", "span 12"])
		self.assertEqual(layout.fit_grid_placements([full]), 0)
		small = grid("repeat(4, minmax(0, 1fr))", ["span 2", "span 2"])
		self.assertEqual(layout.fit_grid_placements([small]), 0)
		self.assertNotIn("mobileStyles", small)


class TestPhoneRows(unittest.TestCase):
	def row(self, base=None, mobile=None, kids=2, **extra):
		block = {
			"element": "div",
			"baseStyles": {"display": "flex", "gap": "24px", **(base or {})},
			"children": [{"element": "span"} for _ in range(kids)],
			**extra,
		}
		if mobile is not None:
			block["mobileStyles"] = mobile
		return block

	def test_a_row_of_two_items_may_wrap_on_the_phone(self):
		block = self.row()
		self.assertEqual(layout.wrap_phone_rows([block]), 1)
		self.assertEqual(block["mobileStyles"], {"flexWrap": "wrap"})
		self.assertNotIn("flexWrap", block["baseStyles"])

	def test_a_column_and_a_lone_item_are_left_alone(self):
		for block in (
			self.row({"flexDirection": "column"}),
			self.row({"flexDirection": "column-reverse"}),
			self.row(kids=1),
		):
			self.assertEqual(layout.wrap_phone_rows([block]), 0)
			self.assertNotIn("mobileStyles", block)

	def test_what_the_page_said_about_wrapping_or_the_phone_layout_is_kept(self):
		for block in (
			self.row({"flexWrap": "nowrap"}),
			self.row(mobile={"flexWrap": "nowrap"}),
			self.row(mobile={"flexDirection": "column"}),
			self.row(mobile={"display": "block"}),
		):
			self.assertEqual(layout.wrap_phone_rows([block]), 0)

	def test_a_scrolling_strip_is_not_wrapped(self):
		for block in (
			self.row({"overflowX": "auto"}),
			self.row({"overflow": "scroll"}),
			self.row(classes=["logo-carousel"]),
			self.row(classes=["u-marquee"]),
		):
			self.assertEqual(layout.wrap_phone_rows([block]), 0)

	def test_a_grid_is_not_a_row(self):
		block = {"element": "div", "baseStyles": {"display": "grid"}, "children": [{}, {}]}
		self.assertEqual(layout.wrap_phone_rows([block]), 0)


class TestTokenSyncKeepsFontsTheChromeLacks(unittest.TestCase):
	def chrome(self, options, current="Inter"):
		saved = []
		field = SimpleNamespace(fieldtype="Select", options=options)
		doc = SimpleNamespace(
			meta=SimpleNamespace(get_field=lambda name: field),
			flags=SimpleNamespace(),
			get=lambda name: current,
			set=lambda name, value: saved.append((name, value)),
			save=lambda: saved.append("saved"),
		)
		return doc, saved

	def sync(self, token_value, chrome):
		from builder.hf_utils import tokens

		token = SimpleNamespace(name="qxb-font-body", value=token_value)
		with (
			patch.object(
				tokens, "_chrome_for_prefix", return_value=("Website Header Footer Variant", "QW x")
			),
			patch.object(tokens.frappe, "get_doc", return_value=chrome),
		):
			return tokens.sync_token_to_chrome(token)

	def test_a_font_the_chrome_offers_is_written_back(self):
		chrome, saved = self.chrome("Inter\nLato\nMerriweather")
		self.assertTrue(self.sync("Lato", chrome))
		self.assertEqual(saved, [("body_font", "Lato"), "saved"])

	def test_a_font_the_chrome_lacks_stays_a_token_and_nothing_fails(self):
		chrome, saved = self.chrome("Inter\nLato\nMerriweather")
		self.assertFalse(self.sync("Lora", chrome))
		self.assertEqual(saved, [])  # was a validation error that stopped the build

	def test_a_select_with_no_options_is_not_second_guessed(self):
		chrome, _saved = self.chrome("")
		self.assertTrue(self.sync("Lora", chrome))


SHALLOW_ITEM_PAGE = """
el: div
name: body
c:
  - el: div
    name: feature-cards
    classes: ['u-grid', 'u-grid--3']
    repeat:
      data: features
      items:
        - title: 'Bouquets de saison'
          body: 'Compositions fraîches'
        - title: 'Abonnement mensuel'
          body: 'Des fleurs chaque mois'
    item:
      el: div
      c:
        - el: h3
          bind: {innerHTML: title}
"""


class TestShallowItem(unittest.TestCase):
	def test_an_item_written_beside_repeat_goes_inside_it(self):
		blocks, script = pw.expand_page_yaml(SHALLOW_ITEM_PAGE)
		repeater = blocks[0]["children"][0]
		self.assertTrue(repeater["isRepeaterBlock"])  # was a heading over nothing
		self.assertEqual(repeater["dataKey"]["key"], "features")
		self.assertEqual(repeater["classes"], ["u-grid", "u-grid--3"])
		self.assertEqual(len(repeater["children"]), 1)
		self.assertTrue(script.startswith("data.features = "))

	def test_a_repeat_that_has_its_item_is_left_alone(self):
		node = {"el": "div", "repeat": {"data": "a", "items": [], "item": {"el": "p"}}}
		self.assertFalse(pw.adopt_flat_repeater(node))
		self.assertEqual(node["repeat"]["item"], {"el": "p"})

	def test_a_repeat_with_no_item_anywhere_stays_as_it_is(self):
		node = {"el": "div", "repeat": {"data": "a", "items": [{"x": 1}]}}
		self.assertFalse(pw.adopt_flat_repeater(node))


class TestTextlessBlocks(unittest.TestCase):
	def el(self, tag, name="", **extra):
		return {"element": tag, "blockName": name, **extra}

	def test_a_heading_without_words_is_reported_with_its_name(self):
		page = [
			self.el("div", children=[self.el("h1", "hero-title"), self.el("p", "hero-sub", innerHTML="x")])
		]
		self.assertEqual(layout.textless_blocks(page), ["hero-title (h1)"])

	def test_three_empty_paragraphs_or_buttons_are_enough_without_a_heading(self):
		page = [self.el("div", children=[self.el("p"), self.el("a"), self.el("button")])]
		self.assertEqual(len(layout.textless_blocks(page)), 3)
		two = [self.el("div", children=[self.el("p"), self.el("a")])]
		self.assertEqual(layout.textless_blocks(two), [])

	def test_what_has_words_a_binding_or_children_is_not_empty(self):
		page = [
			self.el(
				"div",
				children=[
					self.el("h2", innerHTML="Titre"),
					self.el("h3", dynamicValues=[{"key": "title", "property": "innerHTML", "type": "key"}]),
					self.el("a", children=[self.el("img")]),
					self.el("p", innerHTML="   "),
				],
			)
		]
		self.assertEqual(layout.textless_blocks(page), [])  # one blank paragraph alone is not worth a retry

	def test_a_repeater_template_and_other_elements_are_not_judged(self):
		page = [
			self.el("div", children=[self.el("div"), self.el("span"), self.el("img"), self.el("section")])
		]
		self.assertEqual(layout.textless_blocks(page), [])
