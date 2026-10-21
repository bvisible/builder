# //// Neoffice — added file (no upstream equivalent): the sites an instance builds carry their photographs.
# Neoffice migration, listed in patches.txt; frappe/builder has no equivalent (2026-10-21).
#
# An instance that holds the host's image endpoint (`comfyui_url`, with its key, or the shared `nora_api_key`) is already routed to it
# (comfyui_client.is_configured), so a site it builds gets photographs; the legacy `image_generation_enabled` flag only says so in the
# configuration, and two instances carried an explicit 0 from the time image generation was switched off (the local flux, then
# the Codex backend, were unusable). The host asked for photographs everywhere: this writes the flag down where it is missing or 0.
# Nothing else changes with it: an instance without the endpoint is left alone.
import frappe
from frappe.installer import update_site_config


def execute():
	conf = frappe.conf
	if not (conf.get("comfyui_url") and (conf.get("comfyui_api_key") or conf.get("nora_api_key"))):
		return
	if conf.get("image_generation_enabled"):
		return
	update_site_config("image_generation_enabled", 1)
