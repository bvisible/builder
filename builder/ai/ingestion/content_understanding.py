"""
Client content ingestion — understand uploaded assets via vision/LLM.

A client drops a batch of real material in the Builder chat (photos, documents).
Each file becomes a `Builder Content Asset` (status=pending); this module's
understanding pass classifies it so the generator can use real content:

- Images   → vision categorization (what it shows, section, slots, orientation,
             quality, dominant colors, keywords).
- Documents→ text extraction (graceful optional libs, no hard dependency) +
             LLM classification into a page section + summary.

Understanding runs on the brief/general model (K2.6), NOT the *-code page
model: it is vision + non-coding classification. Reuses the provider vision
plumbing (base64 data URLs) already used for logo analysis.
"""

import json
import os

import frappe
from frappe import _

from builder.ai.config import get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.schemas.content_asset import ImageUnderstanding, DocumentUnderstanding
from builder.ai.logging import ai_log


IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "heic", "heif", "tiff", "svg"}


def detect_asset_type(filename: str) -> str:
    """Image vs Document from the file extension."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return "Image" if ext in IMAGE_EXTS else "Document"


def _provider(cfg):
    # Understanding is vision + classification (non-code) → general model (K2.6).
    return get_provider(
        cfg.provider,
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=0.3,
        timeout=cfg.request_timeout,
    )


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

_IMAGE_SYSTEM = (
    "You are a meticulous photo editor preparing a client's real photos for "
    "their website. Classify each photo factually for placement. Describe only "
    "what is actually visible — never invent content."
)


def _understand_image(asset, cfg) -> None:
    llm = _provider(cfg)
    prompt = (
        "Classify this client photo for use on their website: describe exactly "
        "what is visible, the best page section and image slots it serves, its "
        "orientation and quality, up to three dominant colors, and keywords."
    )
    result = llm.generate_structured(
        prompt=prompt,
        schema=ImageUnderstanding,
        system_prompt=_IMAGE_SYSTEM,
        images=[asset.file],
    )
    asset.vision_description = (result.description or "")[:500]
    asset.summary = (result.description or "")[:240]
    asset.suggested_section = result.suggested_section or "generic"
    asset.suggested_slots = ", ".join(result.suggested_slots or [])
    asset.orientation = result.orientation or "landscape"
    asset.quality = result.quality or "medium"
    asset.tags = ", ".join(result.tags or [])
    asset.dominant_colors = json.dumps(result.dominant_colors or [])
    # A logo is brand chrome, not page content — flag it so the matcher skips it.
    if result.is_logo:
        asset.suggested_slots = "logo"
        asset.suggested_section = "generic"
    asset.understanding = json.dumps(result.model_dump())


# ---------------------------------------------------------------------------
# Documents — text extraction with graceful, optional libraries
# ---------------------------------------------------------------------------

def _extract_text(path: str, filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext in ("txt", "md", "csv", "rtf", "json"):
        return _read_plain(path)
    if ext == "pdf":
        return _extract_pdf(path)
    if ext == "docx":
        return _extract_docx(path)
    # Unknown type: best-effort plain read (binary returns garbage → caller trims).
    return _read_plain(path)


def _read_plain(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _extract_pdf(path: str) -> str:
    try:
        import pdfplumber  # optional dependency
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except ImportError:
        pass
    except Exception:
        return ""
    try:
        from pypdf import PdfReader  # optional dependency
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _extract_docx(path: str) -> str:
    try:
        import docx  # python-docx, optional dependency
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:
        return ""


_DOC_SYSTEM = (
    "You organize a client's documents into website content. Classify the text "
    "into the right page section and summarize it, using only what's in the text."
)


def _understand_document(asset, cfg) -> None:
    path = asset.get_full_path()
    text = _extract_text(path, asset.original_filename or "") if path else ""
    text = (text or "").strip()
    asset.extracted_text = text[:140000]  # Long Text safety bound
    if not text:
        asset.summary = _("No extractable text")
        asset.suggested_section = "generic"
        asset.understanding = json.dumps({"empty": True})
        return
    llm = _provider(cfg)
    result = llm.generate_structured(
        prompt=f"Classify and summarize this client document text:\n\n{text[:8000]}",
        schema=DocumentUnderstanding,
        system_prompt=_DOC_SYSTEM,
    )
    asset.summary = (result.summary or "")[:240]
    asset.suggested_section = result.suggested_section or "generic"
    asset.tags = ", ".join(result.tags or [])
    asset.understanding = json.dumps(result.model_dump())


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def understand_asset(asset_name: str) -> dict:
    """Run the understanding pass on a single asset and persist the result."""
    asset = frappe.get_doc("Builder Content Asset", asset_name)
    cfg = get_ai_settings()
    ai_log("info", "Understanding content asset",
           asset=asset_name, type=asset.asset_type, file=asset.original_filename)
    try:
        if asset.asset_type == "Image":
            _understand_image(asset, cfg)
        else:
            _understand_document(asset, cfg)
        asset.status = "understood"
        asset.error_message = None
    except Exception as e:
        asset.status = "failed"
        asset.error_message = str(e)[:480]
        frappe.log_error("Content asset understanding failed",
                         f"{asset_name}\n{frappe.get_traceback()}")
        ai_log("error", "Content asset understanding failed",
               asset=asset_name, error=str(e)[:200])
    asset.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        "name": asset.name,
        "status": asset.status,
        "section": asset.suggested_section,
        "summary": asset.summary,
    }


def understand_assets_batch(asset_names, user: str = None) -> list:
    """Understand a batch sequentially (vision calls are heavy) and notify."""
    results = [understand_asset(name) for name in asset_names]
    if user:
        frappe.publish_realtime("content_assets_understood",
                                {"results": results}, user=user)
    return results


@frappe.whitelist()
def ingest_content_assets(session_id: str, files, company: str = None) -> dict:
    """Create Builder Content Asset rows for a batch of uploaded files and queue
    the understanding pass.

    `files` is a JSON list of either bare file URLs or {file_url, filename}.
    This is the entry point the chat's batch upload calls.
    """
    if isinstance(files, str):
        files = frappe.parse_json(files)
    if not files:
        frappe.throw(_("No files provided"))

    names = []
    for entry in files:
        if isinstance(entry, dict):
            url = entry.get("file_url") or entry.get("url")
            fname = entry.get("filename") or entry.get("name")
        else:
            url, fname = entry, None
        if not url:
            continue
        fname = fname or os.path.basename(url.split("?")[0])

        asset = frappe.new_doc("Builder Content Asset")
        asset.session_id = session_id
        asset.company = company
        asset.asset_type = detect_asset_type(fname)
        asset.file = url
        asset.original_filename = fname
        asset.status = "pending"
        asset.insert(ignore_permissions=True)
        names.append(asset.name)

    frappe.db.commit()

    frappe.enqueue(
        "builder.ai.ingestion.content_understanding.understand_assets_batch",
        queue="long",
        timeout=1800,
        asset_names=names,
        user=frappe.session.user,
    )
    return {"created": len(names), "asset_names": names}
