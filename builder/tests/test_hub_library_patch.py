# //// Neoffice — added file (no upstream equivalent): an update switches the hub's library on where the hub is set.
"""`builder_hub_templates` (the editor's panel) and `nora_hub_blocks` (the blocks Nora's plan is offered) were off unless set by hand, and
only osiris had set one of them: a client got neither after an update. A patch writes both down on the next migrate of an instance that
names a hub, unless the site already says something about them. Pinned here: it writes where they are missing, never over a value (0
included), never on an instance without a hub, never `nora_capture_blocks`, and it is listed in the post-model-sync section. No hub is called."""

import os
import unittest
from unittest.mock import patch

import frappe

from builder.builder.patches import enable_the_hub_library_where_the_hub_is_set as library_patch

HUB = {"template_hub_url": "https://hub.example"}


def written(conf):
	with (
		patch.object(frappe, "conf", frappe._dict(conf)),
		patch.object(library_patch, "update_site_config") as update,
	):
		library_patch.execute()
	return [call.args for call in update.call_args_list]


class TestTheLibraryIsSwitchedOn(unittest.TestCase):
	def test_both_switches_are_written_where_they_are_missing(self):
		self.assertEqual(
			[("builder_hub_templates", 1), ("nora_hub_blocks", 1)],
			written(dict(HUB)),
		)

	def test_a_switch_already_there_stays_whatever_its_value(self):
		for value in (1, 0, "", "off", False):
			self.assertEqual([("nora_hub_blocks", 1)], written({**HUB, "builder_hub_templates": value}), value)
			self.assertEqual([("builder_hub_templates", 1)], written({**HUB, "nora_hub_blocks": value}), value)

	def test_nothing_changes_when_both_are_decided(self):
		self.assertEqual([], written({**HUB, "builder_hub_templates": 1, "nora_hub_blocks": 0}))

	def test_an_instance_without_a_hub_is_left_alone(self):
		self.assertEqual([], written({}))
		self.assertEqual([], written({"template_hub_url": ""}))
		self.assertEqual([], written({"template_hub_url": None}))

	def test_the_capture_of_sections_is_not_switched_on(self):
		self.assertNotIn("nora_capture_blocks", [key for key, _ in written(dict(HUB))])

	def test_it_is_in_the_post_model_sync_section_and_its_module_exists(self):
		root = os.path.dirname(os.path.dirname(__file__))
		name = "enable_the_hub_library_where_the_hub_is_set"
		with open(os.path.join(root, "patches.txt")) as f:
			before, after = f.read().split("[post_model_sync]")
		self.assertIn(f"builder.builder.patches.{name}", after)
		self.assertNotIn(f"builder.builder.patches.{name}", before)
		self.assertTrue(os.path.exists(os.path.join(root, "builder", "patches", f"{name}.py")))


if __name__ == "__main__":
	unittest.main()
