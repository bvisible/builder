# //// Neoffice — added file (no upstream equivalent): the arguments of a tool call, read against the tool's schema.
"""A medium or small model sends an object or an array argument as a JSON string; the local 27B model did it
for `add_block`'s `block` eight rounds in a row (2026-10-19) and never placed the form. No model is called."""

import json
import unittest

from builder.ai.agent.coerce import coerce_arguments
from builder.ai.agent.tools.blocks import add_block
from builder.ai.agent.tree import WorkingTree

SCHEMA = {
	"type": "object",
	"properties": {
		"parent_block_id": {"type": "string"},
		"block": {
			"type": "object",
			"properties": {"el": {"type": "string"}, "style": {"type": "object"}, "c": {"type": "array"}},
		},
		"fields": {
			"type": "array",
			"items": {"type": "object", "properties": {"options": {"type": "array"}}},
		},
		"note": {"type": ["string", "object"]},
		"free": {},
	},
}


class TestCoerceArguments(unittest.TestCase):
	def test_an_object_sent_as_text_is_parsed(self):
		args = {"parent_block_id": "root", "block": json.dumps({"el": "section", "c": [{"el": "p"}]})}
		self.assertEqual(coerce_arguments(SCHEMA, args), 1)
		self.assertEqual(args["block"], {"el": "section", "c": [{"el": "p"}]})
		self.assertEqual(args["parent_block_id"], "root")

	def test_an_array_sent_as_text_and_its_items_sent_as_text_are_parsed(self):
		args = {"fields": json.dumps([{"fieldname": "email"}, json.dumps({"fieldname": "date"})])}
		self.assertEqual(coerce_arguments(SCHEMA, args), 2)
		self.assertEqual(args["fields"], [{"fieldname": "email"}, {"fieldname": "date"}])

	def test_the_items_of_a_real_array_are_parsed_too(self):
		args = {"fields": [json.dumps({"fieldname": "email"}), {"fieldname": "date"}]}
		self.assertEqual(coerce_arguments(SCHEMA, args), 1)
		self.assertEqual(args["fields"], [{"fieldname": "email"}, {"fieldname": "date"}])

	def test_a_declared_property_inside_an_object_is_parsed(self):
		args = {"block": {"el": "div", "style": json.dumps({"padding": "8px"})}}
		self.assertEqual(coerce_arguments(SCHEMA, args), 1)
		self.assertEqual(args["block"]["style"], {"padding": "8px"})

	def test_text_that_is_not_such_a_value_is_left_alone(self):
		for value in ("hello", "", '"a string"', "42", "null", "a {brace} inside"):
			args = {"block": value, "fields": value}
			self.assertEqual(coerce_arguments(SCHEMA, args), 0, value)
			self.assertEqual(args, {"block": value, "fields": value})

	def test_the_loose_json_a_model_writes_is_read_as_well(self):
		# unquoted keys, as the local model wrote them in a block it sent as text
		args = {"block": '{"el": "div", "style": {marginTop: "24px"}}'}
		self.assertEqual(coerce_arguments(SCHEMA, args), 1)
		self.assertEqual(args["block"]["style"], {"marginTop": "24px"})

	def test_an_array_is_not_taken_for_an_object(self):
		args = {"block": "[1, 2]"}
		self.assertEqual(coerce_arguments(SCHEMA, args), 0)
		self.assertEqual(args["block"], "[1, 2]")

	def test_a_string_the_schema_allows_is_left_alone(self):
		args = {"parent_block_id": '{"a": 1}', "note": '{"a": 1}', "free": '{"a": 1}', "unknown": '{"a": 1}'}
		before = dict(args)
		self.assertEqual(coerce_arguments(SCHEMA, args), 0)
		self.assertEqual(args, before)

	def test_nothing_to_read_is_no_error(self):
		self.assertEqual(coerce_arguments(SCHEMA, {}), 0)
		self.assertEqual(coerce_arguments({}, {"block": "{}"}), 0)
		self.assertEqual(coerce_arguments(SCHEMA, None), 0)

	def test_the_real_add_block_places_a_block_sent_as_text(self):
		tree = WorkingTree({"blockId": "root", "element": "div", "children": []})
		args = {"parent_block_id": "root", "block": json.dumps({"el": "section", "name": "booking", "c": []})}
		self.assertEqual(coerce_arguments(add_block.parameters, args), 1)
		self.assertIn("Added block", tree.apply("add_block", args))
		self.assertEqual(len(tree.root["children"]), 1)

	def test_a_block_that_stays_text_is_told_to_send_an_object(self):
		tree = WorkingTree({"blockId": "root", "element": "div", "children": []})
		for text in (json.dumps({"el": "section"}), "{not json {% include 'x' %}"):
			result = tree.apply("add_block", {"parent_block_id": "root", "block": text})
			self.assertTrue(result.startswith("FAILED: `block` arrived as TEXT"), result)
		self.assertEqual(tree.root["children"], [])


class TestRepeatedCall(unittest.TestCase):
	def runner(self):
		from builder.ai.agent.loop import AgentRunner

		runner = AgentRunner.__new__(AgentRunner)  # the method reads nothing but its own counter
		runner.repeated_calls = {}
		return runner

	def test_the_third_identical_call_with_the_same_result_is_told_to_stop(self):
		runner = self.runner()
		op = {"tool_name": "connect_form", "args": {"doctype_name": "X", "fields": [{"fieldname": "a"}]}}
		results = [runner.warn_on_repeated_call(op, "DECLINED: nope") for _ in range(4)]
		self.assertEqual(results[0], "DECLINED: nope")
		self.assertEqual(results[1], "DECLINED: nope")
		self.assertIn("STOP", results[2])
		self.assertIn("3 times", results[2])
		self.assertIn("4 times", results[3])

	def test_a_changing_result_is_not_a_repeat(self):
		runner = self.runner()
		op = {"tool_name": "read_block", "args": {"block_id": "a"}}
		for n in range(6):
			self.assertNotIn("STOP", runner.warn_on_repeated_call(op, f"result {n}"))

	def test_different_arguments_are_not_a_repeat(self):
		runner = self.runner()
		for n in range(6):
			op = {"tool_name": "read_block", "args": {"block_id": f"b{n}"}}
			self.assertNotIn("STOP", runner.warn_on_repeated_call(op, "same result"))


if __name__ == "__main__":
	unittest.main()
