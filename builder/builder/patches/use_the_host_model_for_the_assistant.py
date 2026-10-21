# //// Neoffice — added file (no upstream equivalent): an instance that holds the host's endpoint runs its assistant on the host's model.
# Neoffice migration, listed in patches.txt; frappe/builder has no equivalent (2026-10-21).
#
# The assistant of the site editor ran on a hosted Kimi on every client, whatever the host wanted: the picker's first model
# was the answer, and nothing could name another. `nora_assistant_model` now does (builder.ai.models.ModelRegistry.host_assistant_model),
# and this patch, which runs on the next migrate of every instance, names the host's own model there, after creating the providers
# that make the route exist (managed.sync_nora_providers). A value already in site_config, an empty one included, is a decision of
# the host and stays: setting `nora_assistant_model` to "" is the way back to the hosted model.
import frappe
from frappe.installer import update_site_config

from builder.site_ai.managed import NORA_PROVIDER_NAME, NORA_ROUTE_PREFIX, nora_model_id, sync_nora_providers


def execute():
	on = sync_nora_providers()
	if NORA_PROVIDER_NAME not in on:
		return
	if frappe.conf.get("nora_assistant_model") is not None:
		return
	update_site_config("nora_assistant_model", f"{NORA_ROUTE_PREFIX}/{nora_model_id()}")
