# //// Neoffice — added file (no upstream equivalent): the site pipeline's own page prompt, after upstream 1.38.0.
"""Upstream 1.38.0 dropped Prompts.GENERATION_YAML (its own generation moved to page markup) and BlockCodec.fields_doc, and
page_writer no longer re-exported compact_json: after the merge of 13.11 every site build failed at its first page. The
pipeline's YAML prompt is ours now (yaml_prompt.py); these tests fail before a build does when a merge takes a piece again."""

import ast
import os
import unittest

import builder.site_ai.nora.site_builder as site_builder
from builder.site_ai.nora.yaml_prompt import BLOCK_FIELDS, GENERATION_YAML


class TestThePipelinePagePrompt(unittest.TestCase):
	def test_the_yaml_prompt_is_whole(self):
		self.assertIn("Output only the YAML document", GENERATION_YAML)
		self.assertIn(BLOCK_FIELDS, GENERATION_YAML)
		self.assertNotIn("{BLOCK_FIELDS}", GENERATION_YAML)
		self.assertNotIn("{AI_TELLS}", GENERATION_YAML)

	def test_the_pipeline_asks_upstream_for_nothing_it_dropped(self):
		source = open(site_builder.__file__, encoding="utf-8").read()
		code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
		self.assertNotIn("Prompts.GENERATION_YAML", code)
		self.assertNotIn("page_writer import compact_json", code)

	def test_every_name_the_pipeline_imports_from_the_builder_exists(self):
		"""Each `from builder.ai… import X` of the site pipeline resolves: a merge that drops one fails here, not in a build."""
		import importlib

		folder = os.path.dirname(site_builder.__file__)
		for name in sorted(os.listdir(folder)):
			if not name.endswith(".py"):
				continue
			tree = ast.parse(open(os.path.join(folder, name), encoding="utf-8").read())
			for node in ast.walk(tree):
				if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("builder.ai"):
					module = importlib.import_module(node.module)
					for alias in node.names:
						found = hasattr(module, alias.name)
						if not found:
							# `from builder.ai import llm`: a submodule, seen once imported
							try:
								importlib.import_module(f"{node.module}.{alias.name}")
								found = True
							except ImportError:
								found = False
						self.assertTrue(found, f"{name}: {node.module}.{alias.name}")
