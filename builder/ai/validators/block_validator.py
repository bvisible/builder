#//// Neoffice — added file (no upstream equivalent): validates and REPAIRS LLM block output instead of
#//// rejecting the generation. builder/ai/** = the Neoffice AI site generator; frappe/builder ships no
#//// such module. First commit 563d9875 2026-02-01.
"""
Block Validator - Validation + auto-repair for FrappeBlock structures.
Fixes common LLM output issues instead of rejecting the entire generation.
"""

#//// Neoffice — re for the sanitiser below (URL schemes, dangerous CSS).
import re
import uuid
from typing import Optional
import frappe
from builder.ai.logging import ai_log


class BlockValidator:
    """
    Validator and auto-repairer for FrappeBlock structures.
    Fixes common issues (missing blockId, invalid elements) instead of failing.
    """

    VALID_ELEMENTS = {
        # Layout
        "div", "section", "article", "aside", "main", "header", "footer", "nav",
        # Headings & text
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "label", "blockquote",
        "small", "strong", "em", "b", "i", "u", "sub", "sup", "mark", "code", "pre",
        "cite", "abbr", "time", "address", "q", "del", "ins", "kbd", "samp", "var",
        "dl", "dt", "dd", "data", "wbr",
        # Interactive
        "a", "button", "img", "video", "iframe", "audio", "source",
        # Lists
        "ul", "ol", "li",
        # Forms
        "form", "input", "textarea", "select", "option",
        # Table
        "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup", "col",
        # Misc
        "hr", "br", "figure", "figcaption", "details", "summary",
        # SVG (LLM sometimes generates inline SVG icons)
        "svg", "path", "circle", "rect", "line", "polyline", "polygon", "g", "defs",
        "clipPath", "use", "symbol", "text", "tspan",
    }

    #//// Neoffice — the sanitiser below (constants + three methods) is entirely ours.
    #//// VALID_ELEMENTS above filters the block's `element` and NOTHING else, so three
    #//// model-controlled fields reached the rendered page untouched:
    #////   • innerHTML — parsed by BeautifulSoup in builder_page.add_inner_html_content and
    #////     appended to the tag verbatim, so a <script> in it is a <script> on the site;
    #////   • attributes / customAttributes — copied wholesale (`tag.attrs = attributes`),
    #////     so onclick=… or href="javascript:…" shipped as written;
    #////   • clientScript — emitted as a real <script> block by attach_client_script.
    #//// That mattered the day the prompt stopped being ours alone: scraped brochures and
    #//// chat messages now reach the model, and its output is published HTML. Fencing the
    #//// input (builder/ai/utils.as_untrusted_source) asks the model to behave; this is the
    #//// half that does not depend on it behaving.
    #//// Deliberately NOT applied in add_inner_html_content: that path also renders pages a
    #//// human authored in the editor, where an embed or a widget script is the feature.
    #//// This class only ever sees LLM output.

    # Dropped outright — an AI page has no business shipping any of these, and each is a
    # script vector (<link>/<meta> for CSP-bypassing redirects, <base> for hijacking every
    # relative URL on the page).
    FORBIDDEN_INNER_TAGS = {
        "script", "base", "link", "meta", "object", "embed", "applet", "frame", "frameset",
    }

    # Attributes carrying a URL, checked against the scheme rules below.
    URL_ATTRIBUTES = {
        "href", "src", "srcset", "action", "formaction", "poster", "data",
        "background", "xlink:href", "ping", "cite",
    }

    # `data:` is allowed only for raster images: data:image/svg+xml carries script.
    _SAFE_DATA_URL = re.compile(r"^data:image/(png|jpe?g|gif|webp|avif|bmp);base64,", re.I)
    _DANGEROUS_SCHEME = re.compile(r"^\s*(javascript|vbscript|data|blob|file)\s*:", re.I)
    # url(javascript:…), expression(…), -moz-binding, behavior: — the CSS script vectors.
    _DANGEROUS_CSS = re.compile(
        r"(expression\s*\(|-moz-binding|behaviou?r\s*:|url\s*\(\s*['\"]?\s*(javascript|vbscript|data)\s*:)",
        re.I,
    )

    def __init__(self):
        self._repairs = 0

    @classmethod
    def _clean_attribute(cls, name: str, value) -> Optional[str]:
        """The value to keep for `name`, or None when the attribute must go."""
        lname = (name or "").strip().lower()

        # Every event handler, whatever the tag: onclick, onerror, onmouseover…
        if lname.startswith("on"):
            return None
        # srcdoc is a whole document inline — the iframe equivalent of innerHTML.
        if lname == "srcdoc":
            return None

        if isinstance(value, (list, tuple)):
            value = " ".join(str(v) for v in value)
        if value is None:
            return None
        value = str(value)

        if lname == "style":
            return None if cls._DANGEROUS_CSS.search(value) else value

        if lname in cls.URL_ATTRIBUTES:
            if cls._SAFE_DATA_URL.match(value.strip()):
                return value
            # `&#106;avascript:` and friends: strip what a browser ignores before
            # deciding, or the check reads a scheme the browser will not.
            probe = re.sub(r"[\s\x00-\x20]+", "", value)
            if cls._DANGEROUS_SCHEME.match(probe):
                return None
        return value

    def _sanitise_attributes(self, holder: dict, key: str) -> None:
        attrs = holder.get(key)
        if not isinstance(attrs, dict) or not attrs:
            return
        cleaned = {}
        for name, value in attrs.items():
            kept = self._clean_attribute(name, value)
            if kept is None:
                ai_log("warning", "Dropped unsafe attribute from generated block",
                       attribute=name, blockId=holder.get("blockId"))
                self._repairs += 1
                continue
            cleaned[name] = kept
        if cleaned != attrs:
            holder[key] = cleaned

    def _sanitise_inner_html(self, block: dict) -> None:
        inner = block.get("innerHTML")
        if not inner or not isinstance(inner, str):
            return
        # Cheap pre-check: most generated innerHTML is a sentence with a <strong> in it,
        # and parsing every one of them would cost far more than it protects.
        if "<" not in inner:
            return

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(inner, "html.parser")
        changed = False
        for tag in soup.find_all(True):
            if tag.name and tag.name.lower() in self.FORBIDDEN_INNER_TAGS:
                ai_log("warning", "Dropped forbidden tag from generated innerHTML",
                       tag=tag.name, blockId=block.get("blockId"))
                tag.decompose()
                changed = True
                continue
            for name in list(tag.attrs):
                kept = self._clean_attribute(name, tag.attrs[name])
                if kept is None:
                    del tag.attrs[name]
                    changed = True
                elif kept != tag.attrs[name]:
                    tag.attrs[name] = kept
                    changed = True
        if changed:
            block["innerHTML"] = str(soup)
            self._repairs += 1

    def _sanitise_block(self, block: dict) -> None:
        """Strip from ONE block everything an LLM should never be able to publish."""
        self._sanitise_attributes(block, "attributes")
        self._sanitise_attributes(block, "customAttributes")
        self._sanitise_inner_html(block)

        # A generated page never needs its own JS: nothing in the prompts asks for it, and
        # attach_client_script turns whatever is here into a <script> tag on the live site.
        if block.get("clientScript"):
            script = block.get("clientScript")
            if isinstance(script, dict) and script.get("js"):
                ai_log("warning", "Dropped clientScript from generated block",
                       blockId=block.get("blockId"))
                script.pop("js", None)
                self._repairs += 1
        if block.get("blockClientScript"):
            ai_log("warning", "Dropped blockClientScript from generated block",
                   blockId=block.get("blockId"))
            block.pop("blockClientScript", None)
            self._repairs += 1

    def repair_block(self, block: dict, _depth: int = 0) -> Optional[dict]:
        """
        Validate and auto-repair a single block.
        Returns the repaired block, or None if unfixable.
        """
        if not isinstance(block, dict):
            return None

        # Auto-generate missing blockId
        if "blockId" not in block or not block["blockId"]:
            element = block.get("element", "div")
            block["blockId"] = f"{element}-auto-{uuid.uuid4().hex[:8]}"
            self._repairs += 1

        # Default to div if element missing
        if "element" not in block or not block["element"]:
            block["element"] = "div"
            self._repairs += 1

        # Fix invalid element type — map to closest valid or use div
        element = block.get("element")
        if element not in self.VALID_ELEMENTS:
            ai_log("debug", "Replacing invalid element with div",
                   invalid_element=element, blockId=block.get("blockId"))
            block["element"] = "div"
            self._repairs += 1

        #//// Neoffice — sanitise what the model wrote before it becomes a published page.
        #//// See _sanitise_block for why the element allowlist above was not enough.
        self._sanitise_block(block)

        # Recursively repair children
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                block["children"] = []
                self._repairs += 1
            else:
                repaired_children = []
                for child in children:
                    repaired = self.repair_block(child, _depth=_depth + 1)
                    if repaired:
                        repaired_children.append(repaired)
                block["children"] = repaired_children

        return block

    def validate_and_repair(self, blocks: list[dict]) -> list[dict]:
        """
        Validate and auto-repair a list of blocks.
        Returns the repaired blocks list. Only returns empty if input was completely invalid.
        """
        self._repairs = 0

        if not isinstance(blocks, list):
            ai_log("warning", "Blocks is not a list", type=str(type(blocks)))
            return []

        if not blocks:
            ai_log("warning", "Blocks list is empty")
            return []

        # Deduplicate blockIds
        seen_ids = set()

        def dedup_ids(block):
            if not isinstance(block, dict):
                return
            block_id = block.get("blockId", "")
            if block_id in seen_ids:
                new_id = f"{block_id}-{uuid.uuid4().hex[:6]}"
                block["blockId"] = new_id
                self._repairs += 1
            seen_ids.add(block.get("blockId", ""))
            for child in block.get("children", []):
                dedup_ids(child)

        # Repair each block
        repaired = []
        for block in blocks:
            fixed = self.repair_block(block)
            if fixed:
                repaired.append(fixed)

        # Dedup after repair
        for block in repaired:
            dedup_ids(block)

        # Mechanical safety-net rules (behind the prompts — prompts steer,
        # these guarantee):
        #  R1: a root section laid out as flex WITHOUT an explicit
        #      flexDirection and holding >=2 wide children renders side-by-side
        #      columns of full sections (diagnosed on a k2.7 run) -> force column.
        #  R2: ghost/watermark display words (absolute + huge font) must sit
        #      behind the content with a capped opacity, or they cross the copy.
        for block in repaired:
            self._apply_root_flex_rule(block)
        for block in repaired:
            self._apply_ghost_text_rule(block)
        for block in repaired:
            self._apply_placeholder_text_rule(block)

        if self._repairs > 0:
            ai_log("info", "Blocks auto-repaired",
                   repairs=self._repairs, blocks_count=len(repaired))

        return repaired

    @staticmethod
    def _is_wide_child(child: dict) -> bool:
        if not isinstance(child, dict):
            return False
        width = str((child.get("baseStyles") or {}).get("width", "")).strip()
        if not width or width in ("100%", "auto"):
            return True
        if width.endswith("%"):
            try:
                return float(width[:-1]) > 50
            except ValueError:
                return True
        return False

    def _apply_root_flex_rule(self, block: dict) -> None:
        """R1 — root-level flex sections without explicit direction stack."""
        if not isinstance(block, dict):
            return
        styles = block.get("baseStyles") or {}
        if str(styles.get("display", "")).strip() == "flex" and not styles.get("flexDirection"):
            children = [c for c in (block.get("children") or []) if isinstance(c, dict)]
            wide = [c for c in children if self._is_wide_child(c)]
            if len(wide) >= 2:
                styles["flexDirection"] = "column"
                block["baseStyles"] = styles
                self._repairs += 1
                ai_log("info", "mechanical rule applied", rule="root-flex-column",
                       block=block.get("blockId"))

    _FONT_HUGE_PX = 64.0

    @classmethod
    def _font_size_px(cls, value) -> float:
        import re as _re

        raw = str(value or "")
        nums = [float(n) for n in _re.findall(r"(\d+(?:\.\d+)?)", raw)]
        if not nums:
            return 0.0
        biggest = max(nums)
        if "rem" in raw or ("em" in raw and "rem" not in raw):
            return biggest * 16.0
        return biggest

    def _apply_ghost_text_rule(self, block: dict, _depth: int = 0) -> None:
        """R2 — oversized absolute display text goes behind content, faded."""
        if not isinstance(block, dict) or _depth > 30:
            return
        styles = block.get("baseStyles") or {}
        text = str(block.get("innerHTML") or "").strip()
        if (
            text
            and str(styles.get("position", "")).strip() == "absolute"
            and self._font_size_px(styles.get("fontSize")) >= self._FONT_HUGE_PX
        ):
            try:
                opacity = float(str(styles.get("opacity", "1")))
            except ValueError:
                opacity = 1.0
            changed = False
            if opacity > 0.08:
                styles["opacity"] = "0.08"
                changed = True
            if str(styles.get("zIndex", "")).strip() not in ("-1",):
                styles["zIndex"] = "-1"
                changed = True
            if changed:
                styles.setdefault("pointerEvents", "none")
                block["baseStyles"] = styles
                self._repairs += 1
                ai_log("info", "mechanical rule applied", rule="ghost-text-behind",
                       block=block.get("blockId"))
        for child in block.get("children") or []:
            self._apply_ghost_text_rule(child, _depth + 1)

    _PLACEHOLDER_TEXT_RE = None

    def _strip_placeholder_text(self, value: str):
        """Drop ?text=… from large placehold.co URLs (the service prints the
        text as a giant word across the image). Avatar-sized (<300px wide)
        placeholders keep their initials."""
        import re as _re

        if "placehold.co" not in value:
            return value, False
        changed = False

        def _sub(match):
            nonlocal changed
            url = match.group(0)
            size = _re.search(r"placehold\.co/(\d+)x(\d+)", url)
            width = int(size.group(1)) if size else 1000
            if width < 300:
                return url
            before = url
            url = _re.sub(r"\?text=[^\s\"'\)]*", "", url)
            # placehold.co prints its dimensions when no text is given — make
            # the label invisible by using the background color for the text
            url = _re.sub(
                r"(placehold\.co/\d+x\d+/)([0-9a-fA-F]{3,8})/([0-9a-fA-F]{3,8})",
                lambda m: m.group(1) + m.group(2) + "/" + m.group(2),
                url,
            )
            if url != before:
                changed = True
            return url

        value = _re.sub(r"https?://[^\s\"'\)]*placehold\.co[^\s\"'\)]*", _sub, value)
        return value, changed

    def _apply_placeholder_text_rule(self, block: dict, _depth: int = 0) -> None:
        """R3 — text-bearing large placeholders become plain color blocks."""
        if not isinstance(block, dict) or _depth > 30:
            return
        for container_key in ("baseStyles", "mobileStyles", "tabletStyles", "attributes", "rawStyles"):
            container = block.get(container_key)
            if not isinstance(container, dict):
                continue
            for key, value in list(container.items()):
                if isinstance(value, str) and "placehold.co" in value:
                    new_value, changed = self._strip_placeholder_text(value)
                    if changed:
                        container[key] = new_value
                        self._repairs += 1
                        ai_log("info", "mechanical rule applied",
                               rule="placeholder-text-stripped", block=block.get("blockId"))
        inner = block.get("innerHTML")
        if isinstance(inner, str) and "placehold.co" in inner:
            new_inner, changed = self._strip_placeholder_text(inner)
            if changed:
                block["innerHTML"] = new_inner
                self._repairs += 1
                ai_log("info", "mechanical rule applied",
                       rule="placeholder-text-stripped", block=block.get("blockId"))
        for child in block.get("children") or []:
            self._apply_placeholder_text_rule(child, _depth + 1)

    def validate(self, block: dict, _depth: int = 0) -> bool:
        """Legacy validation — still returns bool for backward compat."""
        if not isinstance(block, dict):
            return False
        if "blockId" not in block:
            return False
        if "element" not in block:
            return False
        if block.get("element") not in self.VALID_ELEMENTS:
            return False
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                return False
            for child in children:
                if not self.validate(child, _depth=_depth + 1):
                    return False
        return True

    def validate_blocks(self, blocks: list[dict]) -> bool:
        """Legacy validation — returns True if all blocks valid."""
        if not isinstance(blocks, list) or not blocks:
            return False
        for i, block in enumerate(blocks):
            if not self.validate(block):
                ai_log("warning", "Block validation failed at index",
                       index=i, element=block.get("element"), blockId=block.get("blockId"))
                return False
        return True


__all__ = [
    "BlockValidator",
]
