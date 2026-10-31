# //// Neoffice — added file (no upstream equivalent): the photos a group publishes to the Builder Hub are shrunk.
"""The photos of a generated site are PNGs of two megabytes; five groups put 41 MB into the public repository of the hub. A photo is shrunk on
its way to the hub: an opaque image becomes a JPEG under a width cap, a transparent one stays a PNG, a small, animated or unreadable file and
every other kind goes untouched, and a file is never made bigger. The upload sends the new bytes under the new name."""

import io
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from builder import hub_image, hub_publish


def photo(width=1400, height=800, mode="RGB"):
    """A smooth picture with noise on top: big as a PNG, small as a JPEG, like a photograph."""
    base = Image.radial_gradient("L").resize((width, height))
    tinted = Image.merge("RGB", (base, base.point(lambda v: 255 - v), base.point(lambda v: v // 2 + 40)))
    noisy = Image.blend(tinted, Image.effect_noise((width, height), 30).convert("RGB"), 0.2)
    return noisy.convert(mode)


def encoded(image, kind="PNG", **options):
    out = io.BytesIO()
    image.save(out, kind, **options)
    return out.getvalue()


def opened(content):
    return Image.open(io.BytesIO(content))


class TestAPhotoIsShrunk(unittest.TestCase):
    def test_an_opaque_png_becomes_a_smaller_jpeg_under_a_new_name(self):
        original = encoded(photo())
        self.assertGreater(len(original), hub_image.MIN_BYTES)
        content, name = hub_image.shrink_for_hub(original, "gen_ab12.png")
        self.assertEqual("gen_ab12.jpg", name)
        self.assertLess(len(content), len(original) / 2)
        self.assertEqual("JPEG", opened(content).format)

    def test_the_picture_keeps_its_size_under_the_cap(self):
        content, _ = hub_image.shrink_for_hub(encoded(photo(1400, 800)), "a.png")
        self.assertEqual((1400, 800), opened(content).size)

    def test_a_wider_picture_is_scaled_down_to_the_cap(self):
        content, _ = hub_image.shrink_for_hub(encoded(photo(2400, 1000)), "a.png")
        self.assertEqual((hub_image.MAX_WIDTH, 800), opened(content).size)

    def test_a_capital_extension_is_replaced(self):
        _, name = hub_image.shrink_for_hub(encoded(photo()), "PHOTO.PNG")
        self.assertEqual("PHOTO.jpg", name)

    def test_an_alpha_channel_that_is_opaque_everywhere_does_not_keep_the_picture_a_png(self):
        content, name = hub_image.shrink_for_hub(encoded(photo(mode="RGBA")), "a.png")
        self.assertEqual("a.jpg", name)
        self.assertEqual("JPEG", opened(content).format)

    def test_the_orientation_of_a_phone_photo_is_applied_before_the_metadata_is_dropped(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        sideways = encoded(photo(1400, 700), "JPEG", quality=98, exif=exif)
        with patch.object(hub_image, "MIN_BYTES", 1024):
            content, _ = hub_image.shrink_for_hub(sideways, "a.jpg")
        self.assertEqual((700, 1400), opened(content).size)


class TestWhatStaysAsItIs(unittest.TestCase):
    def test_a_transparent_png_stays_a_png_with_its_transparency(self):
        image = photo(1400, 800, "RGBA")
        image.paste((0, 0, 0, 0), (0, 0, 400, 400))
        original = encoded(image)
        content, name = hub_image.shrink_for_hub(original, "logo.png")
        self.assertTrue(name.endswith(".png"))
        shrunk = opened(content)
        self.assertEqual("PNG", shrunk.format)
        self.assertEqual(0, shrunk.convert("RGBA").getpixel((10, 10))[3])

    def test_a_small_file_goes_as_it_is(self):
        small = encoded(Image.new("RGB", (200, 200), "red"))
        self.assertLess(len(small), hub_image.MIN_BYTES)
        content, name = hub_image.shrink_for_hub(small, "a.png")
        self.assertTrue(content is small, "the file was changed")
        self.assertEqual("a.png", name)

    def test_a_file_that_is_no_image_goes_as_it_is(self):
        junk = b"not a picture" * 40000
        content, name = hub_image.shrink_for_hub(junk, "a.png")
        self.assertTrue(content is junk, "the file was changed")
        self.assertEqual("a.png", name)

    def test_the_other_kinds_go_as_they_are(self):
        big = encoded(photo())
        for name in ("a.svg", "a.gif", "a.pdf", "a.mp4", "a"):
            content, kept = hub_image.shrink_for_hub(big, name)
            self.assertTrue(content is big, "the file was changed")
            self.assertEqual(name, kept)

    def test_an_animated_image_goes_as_it_is(self):
        frames = [photo(600, 400), photo(600, 400)]
        original = encoded(frames[0], "PNG", save_all=True, append_images=frames[1:])
        with patch.object(hub_image, "MIN_BYTES", 1024):
            content, name = hub_image.shrink_for_hub(original, "a.png")
        self.assertTrue(content is original, "the file was changed")
        self.assertEqual("a.png", name)

    def test_a_file_is_never_made_bigger(self):
        # one pixel stripes: a PNG packs them into a few kilobytes, a JPEG cannot
        stripes = Image.new("RGB", (1400, 800))
        stripes.paste((255, 255, 255), (0, 0, 1400, 800))
        for x in range(0, 1400, 2):
            stripes.paste((0, 0, 0), (x, 0, x + 1, 800))
        lean = encoded(stripes)
        with patch.object(hub_image, "MIN_BYTES", 1024):
            content, name = hub_image.shrink_for_hub(lean, "a.png")
        self.assertTrue(content is lean, "the file was changed")
        self.assertEqual("a.png", name)


class TestTheUpload(unittest.TestCase):
    def upload(self, file_url, content):
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file_url)[1], delete=False) as handle:
            handle.write(content)
        try:
            file_doc = MagicMock(is_private=0)
            file_doc.get_full_path.return_value = handle.name
            frappe = MagicMock()
            frappe.get_doc.return_value = file_doc
            requests = MagicMock()
            requests.post.return_value.status_code = 200
            requests.post.return_value.json.return_value = {"message": {"file_url": "/files/hubpub-x-gen.jpg"}}
            with patch.object(hub_publish, "frappe", frappe), patch.object(hub_publish, "requests", requests):
                result = hub_publish._upload_one_asset(file_url, "x", "https://hub", {})
            return result, requests.post.call_args.kwargs["files"]["file"]
        finally:
            os.unlink(handle.name)

    def test_a_photo_leaves_shrunk_under_its_new_name(self):
        original = encoded(photo())
        result, (name, content, mimetype) = self.upload("/files/gen_cd34.png", original)
        self.assertEqual("/files/hubpub-x-gen.jpg", result)
        self.assertEqual(("gen_cd34.jpg", "image/jpeg"), (name, mimetype))
        self.assertLess(len(content), len(original) / 2)

    def test_a_file_that_is_not_shrunk_leaves_as_it_was(self):
        svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>"
        _, (name, content, mimetype) = self.upload("/files/mark.svg", svg)
        self.assertEqual(("mark.svg", svg, "image/svg+xml"), (name, content, mimetype))


if __name__ == "__main__":
    unittest.main()
