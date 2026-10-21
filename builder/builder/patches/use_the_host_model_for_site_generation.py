# //// Neoffice — added file (no upstream equivalent): an instance that holds the host's endpoint writes its sites with the host's model.
# Neoffice migration, listed in patches.txt; frappe/builder has no equivalent (2026-10-21).
#
# The local model (Nora, on the host's own hardware) writes a whole site for the price of the electricity, and measured on the test
# instance it writes the same pages as the hosted models the clients were using, 2.4 times faster. Switching a client to it by hand,
# instance by instance, was refused: an update must do it. This patch, which runs on the next migrate of every instance:
#
#   1. creates the three Nora providers (vision, reasoning lane, plain lane) when site_config holds the host's endpoint and key,
#      managed or not (managed.sync_nora_providers), so that the route exists before anything names it;
#   2. names the local model as the one that writes the sites (`nora_site_model`), unless the site already says something about it.
#
# "Already says something" includes an empty value: a host that set `nora_site_model` to "" asked for the hosted model, and an
# update does not undo a decision. The judge needs no key: with `nora_review_model` unset it reads with the host's own lanes
# (visual_check.judge_model). Setting `nora_site_model` back to "" (or to another route) in site_config is the way out.
import frappe
from frappe.installer import update_site_config

from builder.site_ai.managed import NORA_PROVIDER_NAME, NORA_ROUTE_PREFIX, nora_model_id, sync_nora_providers


def execute():
	on = sync_nora_providers()
	if NORA_PROVIDER_NAME not in on:
		return
	if frappe.conf.get("nora_site_model") is not None:
		return
	update_site_config("nora_site_model", f"{NORA_ROUTE_PREFIX}/{nora_model_id()}")
