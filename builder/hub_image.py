# //// Neoffice — added file (no upstream equivalent): shrinks a photo before it is published to the Builder Hub.
"""A generated site's photos come out as PNGs of about two megabytes each (1600 x 900), where the groups that came with the hub weigh fifty
kilobytes on average. The hub keeps what it is sent in a public repository and every instance that installs a group downloads it, so a photo
is shrunk on its way out: an opaque image becomes a JPEG, a wider image than the pages ever show is scaled down, and an image that really uses
transparency stays a PNG. Nothing here changes a file it cannot make smaller: it goes as it is."""

import io
import os

from PIL import Image, ImageOps

MIN_BYTES = 300 * 1024
MAX_WIDTH = 1920
JPEG_QUALITY = 82
SHRINKABLE = {".png", ".jpg", ".jpeg", ".webp"}


def _uses_transparency(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return image.getchannel("A").getextrema()[0] < 255
    return image.mode == "P" and "transparency" in image.info


def _encoded(image: Image.Image) -> tuple[bytes, str]:
    out = io.BytesIO()
    if _uses_transparency(image):
        image.convert("RGBA").save(out, "PNG", optimize=True)
        return out.getvalue(), ".png"
    image.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue(), ".jpg"


def shrink_for_hub(content: bytes, basename: str) -> tuple[bytes, str]:
    """The bytes and the file name to upload for an image: the smaller re-encoding when there is one, else `content` and `basename` as they came.
    A file that is no image Pillow reads, an animated one and every other kind (svg, gif, pdf...) are returned untouched."""
    stem, extension = os.path.splitext(basename)
    if extension.lower() not in SHRINKABLE or len(content) < MIN_BYTES:
        return content, basename
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
        if getattr(image, "is_animated", False):
            return content, basename
        image = ImageOps.exif_transpose(image)
        if image.width > MAX_WIDTH:
            image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)), Image.LANCZOS)
        shrunk, new_extension = _encoded(image)
    except Exception:
        # the hub serves the file as it always did; a broken image is not this step's to refuse
        return content, basename
    if len(shrunk) >= len(content):
        return content, basename
    return shrunk, stem + new_extension
