# //// Neoffice — added file (no upstream equivalent): the arguments of a tool call, read against the tool's schema.
"""A medium or small model often sends an argument the schema declares as an object or an array as a JSON
STRING (`"block": "{\\"el\\": \\"section\\", ...}"`). The tool then reads "no block definition supplied", says
so, and the model sends the same string again: on 2026-10-19 the local 27B model went through eight such
rounds and stopped at the step limit without placing a form. The string is parsed here, once, before any tool
sees it, so every tool (add_block, update_block, connect_form, ...) benefits and none has to know."""


def declared_types(schema) -> set[str]:
	kind = schema.get("type") if isinstance(schema, dict) else None
	return set(kind) if isinstance(kind, list) else ({kind} if kind else set())


def parsed_container(text: str, wanted: set[str]):
	"""The object or array a JSON string holds, when the schema asks for one; else None."""
	text = text.strip()
	if not text or text[0] not in "{[":
		return None
	# the same tolerance as for the whole call: unquoted keys, single quotes, a trailing comma (a model that sends
	# a block as text writes `{marginTop: "24px"}` as often as valid JSON)
	from builder.ai.llm import loads_tolerant

	value, _ = loads_tolerant(text)
	if isinstance(value, dict) and "object" in wanted:
		return value
	if isinstance(value, list) and "array" in wanted:
		return value
	return None


def coerce_arguments(parameters: dict, args: dict) -> int:
	"""Replace, in place, each string argument that the schema declares as an object or an array and that holds
	JSON of that kind by the parsed value, down through declared object properties and array items. Returns how
	many were replaced. A string the schema allows as a string (a tool that declares `string` or no type) is
	left alone."""
	if not isinstance(args, dict) or not isinstance(parameters, dict):
		return 0
	replaced = 0
	properties = parameters.get("properties") or {}
	for key, value in list(args.items()):
		schema = properties.get(key)
		if not isinstance(schema, dict):
			continue
		wanted = declared_types(schema)
		if isinstance(value, str) and wanted & {"object", "array"} and "string" not in wanted:
			parsed = parsed_container(value, wanted)
			if parsed is not None:
				args[key] = value = parsed
				replaced += 1
		if isinstance(value, dict) and schema.get("properties"):
			replaced += coerce_arguments(schema, value)
		elif isinstance(value, list) and isinstance(schema.get("items"), dict):
			item_schema = schema["items"]
			for index, item in enumerate(value):
				if isinstance(item, str) and "object" in declared_types(item_schema):
					parsed = parsed_container(item, {"object"})
					if parsed is not None:
						value[index] = item = parsed
						replaced += 1
				if isinstance(item, dict) and item_schema.get("properties"):
					replaced += coerce_arguments(item_schema, item)
	return replaced
