# //// Neoffice — added file (no upstream equivalent): pushes local pages to the central Neoservice
# //// Builder Hub as a template candidate. Neoffice-only; the hub is ours. First commit d20acdac
# //// 2026-06-11.
"""Publish local Builder pages to the central Neoservice Builder Hub.

bvisible extension — counterpart of builder_hub.publish on the hub side.

From any client instance, the Administrator can push a set of pages as a
template-group candidate to the central hub (template_hub_url). Assets are
uploaded first, their URLs rewritten hub-local, then the page bundles are
POSTed. On the hub they land in an editable staging folder ("Hub Inbox —
<group>") where the team depersonalizes content before promoting the group to
the public catalog.

Config (pushed by neoffice-devops SiteConfigPhase):
- template_hub_url           target hub (also used by the template picker)
- hub_publish_api_key/secret token of the hub's publisher service user
"""

import json
import mimetypes
import os
import re

import frappe
import requests
from frappe import _

PUBLISH_TIMEOUT = 120
# //// Neoffice — a page names its design tokens by `var(--<id>)`, and the id of a token the editor makes is a uuid while the id of a
# //// token of a generated site is `<prefix>-primary` (site_ai/nora/site_builder.py, mint_tokens). The collection only knew the uuid,
# //// so a generated site reached the hub with none of its colours and fonts (2026-10-31). Every `var(--name)` is looked up now;
# //// the ones that are no token of this site (a plain CSS variable) are skipped by `_token_rows`.
VARIABLE_RE = re.compile(r"var\(--([A-Za-z0-9][\w-]*)\)")
FILES_URL_RE = re.compile(r"/files/[^\"'\\)\s<>]+")


def _check_administrator():
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only the Administrator can publish to the hub"), frappe.PermissionError)


def _hub_config() -> tuple[str, dict]:
    hub_url = (frappe.conf.get("template_hub_url") or "").rstrip("/")
    key = frappe.conf.get("hub_publish_api_key")
    secret = frappe.conf.get("hub_publish_api_secret")
    if not hub_url:
        frappe.throw(_("template_hub_url is not configured on this site"))
    if not (key and secret):
        frappe.throw(_("hub_publish_api_key / hub_publish_api_secret are not configured on this site"))
    return hub_url, {"Authorization": f"token {key}:{secret}"}


@frappe.whitelist()
def publish_group_to_hub(pages, group: str, title: str | None = None, description: str = ""):
    """Queue the publication of `pages` (list of Builder Page names) to the
    central hub as template-group candidate `group`."""
    _check_administrator()
    if isinstance(pages, str):
        pages = frappe.parse_json(pages)
    if not pages:
        frappe.throw(_("No pages selected"))
    _hub_config()  # fail fast on missing config before queueing

    job = frappe.enqueue(
        "builder.hub_publish._publish_group_job",
        queue="long",
        timeout=1800,
        pages=pages,
        group=group,
        title=title or group,
        description=description,
        user=frappe.session.user,
    )
    return {"job_id": job.id, "group": group}


def _publish_group_job(pages, group, title, description, user):
    try:
        result = _publish_group_sync(pages, group, title, description)
        frappe.publish_realtime(
            "hub_publish_complete", {"group": group, "result": result}, user=user
        )
    except Exception as e:
        frappe.log_error("Hub publish failed", frappe.get_traceback())
        frappe.publish_realtime(
            "hub_publish_error", {"group": group, "error": str(e)[:500]}, user=user
        )
        raise


def _publish_group_sync(pages, group, title="", description=""):
    """Build the bundles, upload assets, POST to the hub. Synchronous —
    callable directly via `bench execute` for testing."""
    hub_url, headers = _hub_config()

    bundles = [_build_page_bundle(name, group) for name in pages]
    payload = {
        "group": group,
        "title": title or group,
        "description": description,
        "replace": True,
        "pages": bundles,
    }

    payload = _upload_and_rewrite_assets(payload, group, hub_url, headers)

    resp = requests.post(
        f"{hub_url}/api/method/builder_hub.publish.publish_template_group",
        json=payload,
        headers={**headers, "Content-Type": "application/json"},
        timeout=PUBLISH_TIMEOUT,
    )
    if resp.status_code != 200:
        frappe.throw(
            _("Hub rejected the publish ({0}): {1}").format(resp.status_code, resp.text[:500])
        )
    return resp.json().get("message")


# the roles a generated site's token ends in (`<prefix>-primary`), longest first so that `-font-heading` is not read as `-heading`
TOKEN_ROLES = ("font-heading", "font-body", "gutter-phone", "container", "secondary", "background", "primary", "gutter", "accent", "text")


def token_label(name: str, group: str) -> str | None:
    """The label of a generated site's token as the hub shows it (`Garage primary`), or None for a token that is not one: the label a site gives
    its own tokens names its business, and a template of the catalog must not."""
    for role in TOKEN_ROLES:
        if name.endswith("-" + role):
            return f"{group.replace('_', ' ').replace('-', ' ').strip().capitalize()} {role.replace('-', ' ')}"
    return None


def referenced_token_names(blob: str) -> list[str]:
    """The names a page's blocks give in `var(--name)`, once each, in order."""
    return sorted(set(VARIABLE_RE.findall(blob)))


def _token_rows(names, group: str | None = None) -> list[dict]:
    """The design tokens `names` as the hub takes them. Builder Variable was renamed Builder Token, its name field variable_name became
    token_name; read the doctype this site has and send the rows under the old wire name, as builder_hub.api does, so the hub and any
    older consumer take them as they are (2026-10-30). With `group`, the rows leave in that group: a consumer asks the hub for the tokens of a
    template group by the group's name, and a token of a generated site sits in a group named after its business (2026-10-31)."""
    token_doctype, name_field = ("Builder Token", "token_name") if frappe.db.exists("DocType", "Builder Token") else ("Builder Variable", "variable_name")
    rows = []
    for name in names:
        var = frappe.db.get_value(token_doctype, name, ["name", name_field, "type", "value", "dark_value", "group"], as_dict=True)
        if var:
            rows.append(
                {
                    "doctype": "Builder Variable",
                    "name": var.name,
                    "variable_name": (token_label(var.name, group) if group else None) or var.get(name_field),
                    "type": var.type,
                    "value": var.value,
                    "dark_value": var.dark_value,
                    "group": group or var.group,
                }
            )
    return rows


def _build_page_bundle(page_name: str, group: str | None = None) -> dict:
    """Mirror of builder_hub.api._get_template_bundle, built from local data
    (without URL absolutization — URLs get rewritten hub-local at upload)."""
    from builder.export_import_standard_page import extract_fonts_from_blocks
    from builder.utils import extract_components_from_blocks

    page_doc = frappe.get_doc("Builder Page", page_name)
    blocks = frappe.parse_json(page_doc.draft_blocks or page_doc.blocks or "[]")

    component_ids = extract_components_from_blocks(blocks)
    components = []
    for cid in component_ids:
        comp = frappe.get_doc("Builder Component", cid)
        components.append(
            {
                "doctype": "Builder Component",
                "name": comp.name,
                "component_id": comp.component_id,
                "component_name": comp.component_name,
                "block": comp.block or "{}",
            }
        )

    # Variables referenced by var(--<id>) in blocks or component blocks.
    # Locally saved pages have no template_group, so reference-scan is the
    # only reliable way to collect them.
    blob = frappe.as_json(blocks, indent=0) + "".join(c["block"] for c in components)
    variables = _token_rows(referenced_token_names(blob), group)

    client_scripts = []
    for cs in page_doc.client_scripts:
        script = frappe.db.get_value(
            "Builder Client Script", cs.builder_script, ["script_type", "script"], as_dict=True
        )
        if script:
            client_scripts.append(
                {
                    "doctype": "Builder Client Script",
                    "name": cs.builder_script,
                    "script_type": script.script_type,
                    "script": script.script,
                }
            )

    fonts = set(extract_fonts_from_blocks(blocks))
    for comp in components:
        fonts.update(extract_fonts_from_blocks(frappe.parse_json(comp["block"])))
    font_docs = []
    for font_name in fonts:
        font = frappe.db.get_value(
            "User Font", {"font_name": font_name}, ["name", "font_name", "font_file"], as_dict=True
        )
        if font:
            font_docs.append({"doctype": "User Font", **font})

    preview = page_doc.preview if (page_doc.preview or "").startswith("/files/") else None

    return {
        "page": {
            "page_title": page_doc.page_title,
            "preview": preview,
            "blocks": blocks,
            "page_data_script": page_doc.page_data_script,
            "head_html": page_doc.head_html,
            "body_html": page_doc.body_html,
            "meta_description": page_doc.meta_description,
        },
        "components": components,
        "variables": variables,
        "client_scripts": client_scripts,
        "fonts": font_docs,
    }


def _upload_and_rewrite_assets(payload: dict, group: str, hub_url: str, headers: dict) -> dict:
    """Upload every referenced /files/* asset to the hub, then rewrite all
    occurrences in the payload to the returned hub-local URLs."""
    blob = frappe.as_json(payload, indent=0)
    # Self-referencing absolute URLs (user pasted the full site URL) become
    # relative so they're collected for upload like every other local asset.
    blob = blob.replace(f"{frappe.utils.get_url()}/files/", "/files/")
    candidates = sorted(set(FILES_URL_RE.findall(blob)), key=len, reverse=True)

    url_map = {}
    for file_url in candidates:
        hub_file_url = _upload_one_asset(file_url, group, hub_url, headers)
        if hub_file_url:
            url_map[file_url] = hub_file_url

    for orig, new in url_map.items():
        blob = blob.replace(orig, new)
    return frappe.parse_json(blob)


def _upload_one_asset(file_url: str, group: str, hub_url: str, headers: dict) -> str | None:
    from urllib.parse import unquote

    file_name = frappe.db.get_value("File", {"file_url": file_url}, "name") or frappe.db.get_value(
        "File", {"file_url": unquote(file_url)}, "name"
    )
    if not file_name:
        return None
    file_doc = frappe.get_doc("File", file_name)
    if file_doc.is_private:
        return None  # private files are never published to the hub

    try:
        path = file_doc.get_full_path()
        with open(path, "rb") as f:
            content = f.read()
    except Exception:
        return None

    basename = os.path.basename(unquote(file_url))
    mimetype = mimetypes.guess_type(basename)[0] or "application/octet-stream"
    resp = requests.post(
        f"{hub_url}/api/method/builder_hub.publish.upload_template_asset",
        files={"file": (basename, content, mimetype)},
        data={"group": group},
        headers=headers,
        timeout=PUBLISH_TIMEOUT,
    )
    if resp.status_code != 200:
        frappe.throw(
            _("Asset upload failed for {0} ({1}): {2}").format(
                file_url, resp.status_code, resp.text[:300]
            )
        )
    return (resp.json().get("message") or {}).get("file_url")
