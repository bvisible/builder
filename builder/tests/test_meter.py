# //// Neoffice — added file (no upstream equivalent): the counter that says what a build spent.
"""A site build made dozens of model calls and counted none of them until 2026-09-15."""

import unittest
from types import SimpleNamespace

from builder.ai import meter


def usage(prompt, completion):
	return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)


class TestMeter(unittest.TestCase):
	def tearDown(self):
		meter.stop()

	def test_nothing_is_counted_outside_a_span(self):
		meter.stop()
		meter.add("kimi", usage(100, 50))
		self.assertEqual(0, meter.read()["calls"])

	def test_a_span_counts_calls_and_tokens_by_kind(self):
		meter.start()
		with meter.kind(meter.WRITING):
			meter.add("kimi", usage(9000, 4000))
			meter.add("kimi", usage(9000, 4000))
		with meter.kind(meter.READING):
			meter.add("kimi", usage(90000, 300))
		span = meter.stop()
		self.assertEqual(3, span["calls"])
		self.assertEqual(108000, span["prompt"])
		self.assertEqual(8300, span["completion"])
		self.assertEqual(2, span["by_kind"][meter.WRITING]["calls"])
		self.assertEqual(90000, span["by_kind"][meter.READING]["prompt"])

	def test_the_summary_names_what_each_kind_cost(self):
		meter.start()
		with meter.kind(meter.WRITING):
			meter.add("kimi", usage(9000, 4000))
		with meter.kind(meter.READING):
			meter.add("kimi", usage(90000, 300))
		line = meter.summary_line(meter.stop())
		self.assertIn("2 model call(s)", line)
		self.assertIn("99k tokens in", line)
		self.assertIn("reading 1 call(s), 90k in", line)

	def test_a_call_with_no_usage_is_not_counted(self):
		meter.start()
		meter.add("kimi", None)
		meter.add("kimi", usage(0, 0))
		self.assertEqual(0, meter.read()["calls"])

	def test_a_broken_usage_object_never_raises(self):
		meter.start()
		meter.add("kimi", SimpleNamespace(prompt_tokens="not a number"))
		self.assertEqual(0, meter.read()["calls"])

	def test_an_empty_span_gives_no_summary_line(self):
		self.assertEqual("", meter.summary_line(meter.read()))

	def test_the_ceiling_answers_only_when_a_budget_is_set(self):
		from unittest.mock import patch

		import frappe

		meter.start()
		with meter.kind(meter.WRITING):
			meter.add("kimi", usage(600000, 100000))
		with patch.dict(frappe.conf, {"nora_build_token_budget": 0}):
			self.assertEqual(0, meter.over_budget())
		with patch.dict(frappe.conf, {"nora_build_token_budget": 1000}):
			self.assertEqual(0, meter.over_budget())
		with patch.dict(frappe.conf, {"nora_build_token_budget": 500}):
			self.assertEqual(200, meter.over_budget())

