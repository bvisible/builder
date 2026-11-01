# //// Neoffice — added file (no upstream equivalent): an update puts the hub's blocks in the editor and in the sites Nora builds.
# Neoffice migration, listed in patches.txt; frappe/builder has no equivalent (2026-11-01).
#
# Two switches decide whether an instance uses the library of the Neoservice hub, and both were off unless set by hand, on osiris only:
# `builder_hub_templates` offers the hub's blocks in the editor's insertion panel (site_ai/nora/hub_templates.py) and `nora_hub_blocks`
# offers the hub's published blocks to the plan of every site Nora builds (site_ai/nora/hub_blocks.py). The host asked for both everywhere
# (2026-11-01: « que mon travail soit dispo partout après l'update et que Nora puisse l'utiliser »), by the update and not by hand, as
# the local model was (use_the_host_model_for_site_generation). The instance must name a hub (`template_hub_url`, which the update
# puts on every instance): without one the two readers would ask the default hub of upstream, which holds none of this.
# A value already in site_config, a 0 or an empty one included, is a decision of the host and stays: it is the way to switch a
# site back off. `nora_capture_blocks` is not touched: it sends sections of the sites to the hub, which is not using the library.
import frappe
from frappe.installer import update_site_config

SWITCHES = ("builder_hub_templates", "nora_hub_blocks")


def execute():
	if not frappe.conf.get("template_hub_url"):
		return
	for key in SWITCHES:
		if frappe.conf.get(key) is None:
			update_site_config(key, 1)
