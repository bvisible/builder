# //// Neoffice — added file (no upstream equivalent): the dividers between the sections of a generated page.
"""What is pinned here: a style is chosen by the brief, else by the words of the art direction, else a sober curve; a shape is drawn from a
seed (the same twice, never the same on two boundaries) and stays inside its box; the boundary of two flat grounds gets a band that wears
both of them, the boundary of two equal grounds a fine line, a photograph's foot a shape laid over it with the room it needs; two photographs,
a section that overlaps its neighbour on purpose, and a style of "none" are left alone; a second run draws the same dividers and not twice as
many; the divider an older writer drew itself is removed and an icon is not. No model, no database."""

import copy
import re
import unittest

from builder.site_ai.nora import dividers as D

PALETTE = {"t-primary": "#253357", "t-background": "#f8f9fa", "t-tint": "#eef4ef", "t-accent": "#3f8f5b"}
ACCENT = "var(--t-accent)"


def section(background=None, **styles):
	base = {"padding": "5rem 0"}
	if background:
		base["backgroundColor"] = background
	base.update(styles)
	return {"element": "section", "blockId": "s", "baseStyles": base, "children": [{"element": "div", "baseStyles": {}, "children": [], "innerHTML": "text"}]}


def photo_section(**styles):
	one = section("#101820", position="relative", **styles)
	one["children"].insert(0, {"element": "img", "baseStyles": {"position": "absolute", "objectFit": "cover"}, "attributes": {"src": "/files/x.jpg"}, "children": []})
	return one


def page(*sections):
	return [{"element": "div", "blockId": "root", "baseStyles": {"backgroundColor": "#f8f9fa"}, "children": list(sections)}]


def dividers_of(blocks):
	return [c for c in blocks[0]["children"] if D.MARK in (c.get("classes") or [])]


class TestTheStyleOfASite(unittest.TestCase):
	def test_the_brief_names_it(self):
		self.assertEqual("wave", D.style_for("wave"))
		self.assertEqual("peaks", D.style_for("Mountain ridge", "a calm sea"))
		self.assertEqual("none", D.style_for("none", "mountains"))

	def test_a_synonym_is_a_style(self):
		self.assertEqual("peaks", D.style_for("alpine"))
		self.assertEqual("tilt", D.style_for("diagonal"))
		self.assertEqual("hills", D.style_for("collines"))
		self.assertEqual("none", D.style_for("straight"))

	def test_the_art_direction_decides_when_the_brief_is_silent(self):
		self.assertEqual("peaks", D.style_for("", "thin alpine mountain-line dividers", "a trade of the high valleys"))
		self.assertEqual("wave", D.style_for(None, "the flow of water, a lake, waves"))
		self.assertEqual("torn", D.style_for("", "a hand-made paper print workshop"))

	def test_nothing_to_go_on_is_a_sober_curve(self):
		self.assertEqual("curve", D.style_for("", "a clean professional direction"))
		self.assertEqual("curve", D.style_for("zigzag"))

	def test_a_word_is_not_matched_inside_another(self):
		self.assertEqual("curve", D.style_for("", "a beautiful warm direction"), "'eau' of 'beautiful' is not water")


class TestTheShapes(unittest.TestCase):
	def test_the_same_seed_draws_the_same_shape(self):
		for style in D.STYLES:
			self.assertEqual(D.layers(style, "a:1"), D.layers(style, "a:1"), style)

	def test_another_boundary_draws_another_one(self):
		for style in ("wave", "hills", "peaks", "torn"):
			self.assertNotEqual(D.layers(style, "a:1"), D.layers(style, "a:2"), style)

	def test_every_shape_stays_inside_its_box(self):
		for style in D.STYLES:
			for seed in ("x:0", "x:1", "x:2", "page:7"):
				for edge, opacity, _ in D.layers(style, seed):
					self.assertTrue(0 < opacity <= 1)
					numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", edge)]
					xs, ys = numbers[0::2], numbers[1::2]
					# the control points of a smooth curve may overshoot a little; the points it passes through do not
					self.assertTrue(all(-100 <= x <= D.WIDTH + 100 for x in xs), (style, seed))
					self.assertTrue(all(-20 <= y <= D.HEIGHT + 20 for y in ys), (style, seed))
					self.assertTrue(edge.startswith("M"), edge[:20])

	def test_the_front_layer_is_the_solid_one_and_the_ones_behind_are_translucent(self):
		for style in ("wave", "hills", "peaks"):
			opacities = [o for _, o, _ in D.layers(style, "s")]
			self.assertEqual(1.0, opacities[-1], style)
			self.assertTrue(all(o < 1 for o in opacities[:-1]), style)

	def test_a_mountain_has_a_ridge_line_on_its_far_layers_only(self):
		ridges = [ridge for _, _, ridge in D.layers("peaks", "s")]
		self.assertEqual([True, True, False], ridges)

	def test_a_line_is_the_edge_alone(self):
		for style in D.STYLES:
			text = D.svg(style, "s", ACCENT, lines=True)
			self.assertNotIn(" Z", text, style)
			self.assertIn('fill="none"', text)
			self.assertIn("vector-effect", text)

	def test_the_drawing_is_decoration_for_a_screen_reader_and_scales_with_the_band(self):
		text = D.svg("wave", "s", "var(--t-primary)")
		self.assertIn('aria-hidden="true"', text)
		self.assertIn('preserveAspectRatio="none"', text)
		self.assertIn("var(--t-primary)", text)
		self.assertNotIn("<text", text)
		self.assertNotIn('transform="matrix', text)
		self.assertIn('transform="matrix(1 0 0 -1 0 100)"', D.svg("wave", "s", "#fff", flip_y=True))

	def test_the_fill_runs_past_the_band_so_no_hairline_shows_where_it_meets_the_next_section(self):
		text = D.svg("peaks", "s", "#fff")
		self.assertIn(f"L{D.WIDTH},{D.HEIGHT + D.SEAM}", text)
		self.assertIn("overflow:visible", text)


class TestTheDividersOfAPage(unittest.TestCase):
	def test_two_flat_grounds_get_a_band_that_wears_both(self):
		blocks = page(section("#f8f9fa"), section("#253357"))
		edits = D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertEqual(1, len(edits))
		first, band, second = blocks[0]["children"]
		self.assertEqual("section-divider", band["blockName"])
		self.assertEqual("#f8f9fa", band["baseStyles"]["backgroundColor"], "the band is the ground of the section above")
		self.assertIn("fill:#253357", band["innerHTML"], "the section below rises into it")
		self.assertEqual("true", band["attributes"]["aria-hidden"])
		self.assertEqual("5rem 0", first["baseStyles"]["padding"], "nothing overlaps: the sections keep their own padding")
		self.assertEqual("5rem 0", second["baseStyles"]["padding"])

	def test_a_token_ground_is_followed_by_the_divider(self):
		blocks = page(section("var(--t-background)"), section("var(--t-primary)"))
		D.apply_dividers(blocks, PALETTE, "curve", "p", ACCENT)
		band = dividers_of(blocks)[0]
		self.assertEqual("var(--t-background)", band["baseStyles"]["backgroundColor"])
		self.assertIn("fill:var(--t-primary)", band["innerHTML"])

	def test_a_token_the_build_palette_lacks_is_a_flat_ground_too(self):
		blocks = page(section("var(--t-background)"), section("var(--t-tint)"))
		D.apply_dividers(blocks, PALETTE, "hills", "p", ACCENT)
		self.assertEqual(1, len(dividers_of(blocks)))

	def test_two_equal_grounds_get_a_fine_line_in_the_accent(self):
		blocks = page(section("#f8f9fa"), section("#f8f9fa"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT)
		band = dividers_of(blocks)[0]
		self.assertIn("stroke:var(--t-accent)", band["innerHTML"])
		self.assertNotIn("fill:var(--t-accent)", band["innerHTML"])
		self.assertEqual("#f8f9fa", band["baseStyles"]["backgroundColor"])

	def test_two_nearly_equal_grounds_are_equal(self):
		blocks = page(section("#f8f9fa"), section("#f9f9fb"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertIn("stroke:", dividers_of(blocks)[0]["innerHTML"])

	def test_without_an_accent_equal_grounds_are_left_straight(self):
		blocks = page(section("#f8f9fa"), section("#f8f9fa"))
		self.assertEqual([], D.apply_dividers(blocks, PALETTE, "wave", "p", ""))

	def test_a_page_is_not_a_ruled_notebook(self):
		blocks = page(*[section("#f8f9fa") for _ in range(9)])
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertEqual(D.MAX_LINES, len(dividers_of(blocks)))

	def test_the_foot_of_a_photograph_gets_a_shape_laid_over_it_and_the_room_it_needs(self):
		blocks = page(photo_section(), section("#f8f9fa"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT)
		hero, band, _ = blocks[0]["children"]
		size = D.band_size("peaks")
		self.assertEqual(f"calc(-1 * {size})", band["baseStyles"]["marginTop"])
		self.assertNotIn("backgroundColor", band["baseStyles"], "the photograph shows through above the shape")
		self.assertEqual(f"calc(5rem + {size})", hero["baseStyles"]["paddingBottom"])
		self.assertNotIn("padding", hero["baseStyles"], "the shorthand is expanded so the longhand wins on every screen")
		self.assertEqual("5rem", hero["baseStyles"]["paddingTop"])
		self.assertIn("fill:#f8f9fa", band["innerHTML"])

	def test_the_head_of_a_photograph_gets_the_shape_of_the_section_above(self):
		blocks = page(section("#f8f9fa"), photo_section())
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		_, band, photo = blocks[0]["children"]
		self.assertEqual(f"calc(-1 * {D.band_size('wave')})", band["baseStyles"]["marginBottom"])
		self.assertIn("fill:#f8f9fa", band["innerHTML"])
		self.assertIn('transform="matrix(1 0 0 -1 0 100)"', band["innerHTML"], "it hangs from the top")
		self.assertIn("paddingTop", photo["baseStyles"])

	def test_the_phone_padding_grows_too(self):
		hero = photo_section()
		hero["mobileStyles"] = {"padding": "3rem 0"}
		blocks = page(hero, section("#f8f9fa"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertIn("calc(3rem + ", hero["mobileStyles"]["paddingBottom"])
		self.assertNotIn("padding", hero["mobileStyles"])

	def test_two_photographs_are_left_alone(self):
		blocks = page(photo_section(), photo_section())
		self.assertEqual([], D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT))

	def test_a_gradient_is_a_picture(self):
		gradient = section(None, backgroundImage="linear-gradient(135deg, #123, #456)")
		self.assertEqual(("picture", ""), D.ground(gradient, PALETTE, "#fff"))
		over = section("#f8f9fa")
		over["children"].append({"element": "div", "baseStyles": {"position": "absolute", "background": "linear-gradient(#000, #fff)"}, "children": []})
		self.assertEqual(("picture", ""), D.ground(over, PALETTE, "#fff"))

	def test_a_translucent_tint_is_the_flat_ground_it_makes_over_the_page(self):
		"""The recipes' tint is rgba(brand, 0.08): over the page ground it is a flat colour, not a picture."""
		blocks = page(section("#f8f9fa"), section("rgba(37, 51, 87, 0.08)"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		band = dividers_of(blocks)[0]
		self.assertEqual(1, len(dividers_of(blocks)))
		self.assertNotIn("calc(", str(blocks[0]["children"][0]["baseStyles"]), "no overlap: a flat ground needs no room")
		self.assertRegex(band["innerHTML"], r"fill:#[0-9a-f]{6}")
		kind, value = D.ground(section("rgba(37, 51, 87, 0.08)"), PALETTE, "#ffffff")
		self.assertEqual(("plain", "#eeeff2"), (kind, value))

	def test_a_token_of_the_site_that_nothing_defines_paints_nothing(self):
		"""The writer invents var(--t-tint): the browser drops the declaration and the page shows through."""
		self.assertEqual(("plain", "#f8f9fa"), D.ground(section("var(--t-surface)"), PALETTE, "#f8f9fa"))
		self.assertEqual(("picture", ""), D.ground(section("var(--another-thing)"), PALETTE, "#f8f9fa"), "a variable of someone else is unknown")

	def test_a_section_that_overlaps_its_neighbour_on_purpose_is_left_alone(self):
		blocks = page(section("#f8f9fa"), section("#253357", marginTop="-4rem"))
		self.assertEqual([], D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT))

	def test_a_section_with_no_ground_of_its_own_wears_the_page_ground(self):
		blocks = page(section(None), section("#253357"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertEqual("#f8f9fa", dividers_of(blocks)[0]["baseStyles"]["backgroundColor"])

	def test_a_style_of_none_or_a_name_it_does_not_know_does_nothing(self):
		for style in ("none", "", "zigzag"):
			blocks = page(section("#f8f9fa"), section("#253357"))
			before = copy.deepcopy(blocks)
			self.assertEqual([], D.apply_dividers(blocks, PALETTE, style, "p", ACCENT))
			self.assertEqual(before, blocks)

	def test_a_page_of_one_section_has_none(self):
		self.assertEqual([], D.apply_dividers(page(section("#f8f9fa")), PALETTE, "wave", "p", ACCENT))
		self.assertEqual([], D.apply_dividers([], PALETTE, "wave", "p", ACCENT))

	def test_a_second_run_draws_the_same_dividers_and_not_twice_as_many(self):
		blocks = page(photo_section(), section("#f8f9fa"), section("#253357"), section("#253357"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT)
		first = [(b["innerHTML"], b["baseStyles"]) for b in dividers_of(blocks)]
		padding = copy.deepcopy(blocks[0]["children"][0]["baseStyles"])
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT)
		self.assertEqual(first, [(b["innerHTML"], b["baseStyles"]) for b in dividers_of(blocks)])
		self.assertEqual(padding, blocks[0]["children"][0]["baseStyles"], "the room is not added a second time")

	def test_a_new_style_replaces_the_old_one(self):
		blocks = page(section("#f8f9fa"), section("#253357"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		D.apply_dividers(blocks, PALETTE, "torn", "p", ACCENT)
		self.assertEqual(1, len(dividers_of(blocks)))
		self.assertEqual(D.band_size("torn"), dividers_of(blocks)[0]["baseStyles"]["height"])

	def test_two_dividers_of_a_page_are_not_twins_and_alternate_sides(self):
		blocks = page(section("#f8f9fa"), section("#253357"), section("#f8f9fa"), section("#253357"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT)
		bands = dividers_of(blocks)
		self.assertEqual(3, len(bands))
		self.assertEqual(3, len({b["innerHTML"] for b in bands}))
		mirrored = [b["baseStyles"].get("transform") == "scaleX(-1)" for b in bands]
		self.assertNotEqual(mirrored[0], mirrored[1])

	def test_the_same_page_is_drawn_the_same_on_a_rebuild(self):
		def drawn():
			blocks = page(section("#f8f9fa"), section("#253357"), section("#f8f9fa"))
			D.apply_dividers(blocks, PALETTE, "hills", "site:about", ACCENT)
			return [b["innerHTML"] for b in dividers_of(blocks)]

		self.assertEqual(drawn(), drawn())


class TestThePageAgainstTheChrome(unittest.TestCase):
	def test_the_page_meets_the_band_under_the_header_and_the_footer(self):
		blocks = page(section("#f8f9fa"))
		edits = D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT, top="#ffffff", bottom="#1f4e79")
		self.assertCountEqual(["peaks between above the page", "peaks between below the page"], edits)
		above, middle, below = blocks[0]["children"]
		self.assertEqual("section", middle["element"])
		self.assertEqual(("#ffffff", True), (above["baseStyles"]["backgroundColor"], "fill:#f8f9fa" in above["innerHTML"]))
		self.assertEqual(("#f8f9fa", True), (below["baseStyles"]["backgroundColor"], "fill:#1f4e79" in below["innerHTML"]))

	def test_a_page_that_has_no_chrome_ground_meets_nothing_there(self):
		blocks = page(section("#f8f9fa"), section("#253357"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT, top="", bottom="")
		self.assertEqual(1, len(dividers_of(blocks)))

	def test_a_footer_of_the_ground_of_the_last_section_needs_no_shape(self):
		blocks = page(section("#253357"))
		self.assertEqual([], D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT, bottom="#253357"))

	def test_a_fine_line_is_never_drawn_against_the_chrome(self):
		blocks = page(section("#ffffff"))
		self.assertEqual([], D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT, top="#ffffff", bottom="#ffffff"))

	def test_a_photograph_that_ends_the_page_ends_in_the_footers_shape(self):
		blocks = page(photo_section())
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT, bottom="#1f4e79")
		hero, band = blocks[0]["children"]
		self.assertIn("fill:#1f4e79", band["innerHTML"])
		self.assertEqual(f"calc(-1 * {D.band_size('peaks')})", band["baseStyles"]["marginTop"])
		self.assertIn("calc(", hero["baseStyles"]["paddingBottom"])

	def test_a_second_run_does_not_add_the_chrome_dividers_twice(self):
		blocks = page(section("#f8f9fa"))
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT, top="#ffffff", bottom="#1f4e79")
		D.apply_dividers(blocks, PALETTE, "peaks", "p", ACCENT, top="#ffffff", bottom="#1f4e79")
		self.assertEqual(2, len(dividers_of(blocks)))

	def test_the_grounds_the_chrome_shows(self):
		chrome = {"page_header_template": "Standard", "page_header_background": "None", "footer_bg_color": "#1f4e79"}
		self.assertEqual(("var(--t-background)", "#1f4e79"), D.chrome_grounds(chrome, "t", False))
		self.assertEqual(("", "#1f4e79"), D.chrome_grounds(chrome, "t", True), "a home has no band")
		self.assertEqual(("#123456", "#1f4e79"), D.chrome_grounds({**chrome, "page_header_background": "Solid", "page_header_bg_color": "#123456"}, "t", False))
		self.assertEqual("", D.chrome_grounds({**chrome, "page_header_background": "Tinted"}, "t", False)[0], "a tint is not told")
		self.assertEqual("", D.chrome_grounds({**chrome, "page_header_background": "Image"}, "t", False)[0])
		self.assertEqual("", D.chrome_grounds({**chrome, "page_header_template": "None"}, "t", False)[0])
		self.assertEqual("", D.chrome_grounds({**chrome, "page_header_template": "Builder"}, "t", False)[0], "a band composed in the editor is the page's own")
		self.assertEqual(("var(--t-background)", ""), D.chrome_grounds({}, "t", False), "an empty chrome is the default band")


class TestWhatAnOlderWriterDrew(unittest.TestCase):
	def drawn(self, view_box, **extra):
		return {"element": "div", "baseStyles": {"width": "100%"}, "children": [], "innerHTML": f'<svg viewBox="{view_box}" preserveAspectRatio="none"><path d="M0,24 L600,0 L1200,24 Z"/></svg>', **extra}

	def test_a_wide_flat_drawing_between_sections_is_removed(self):
		first = section("#f8f9fa")
		first["children"].append(self.drawn("0 0 1200 24"))
		blocks = page(first, section("#253357"))
		edits = D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertIn("1 divider drawn by the writer removed", edits)
		self.assertFalse(any("<svg" in str(c.get("innerHTML") or "") for c in first["children"]))

	def test_the_band_the_writer_put_it_in_goes_with_it(self):
		wrapper = {"element": "div", "baseStyles": {"backgroundColor": "#f8f9fa", "overflow": "hidden"}, "children": [self.drawn("0 0 1400 40")]}
		blocks = page(section("#f8f9fa"), wrapper, section("#f8f9fa"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertNotIn(wrapper, blocks[0]["children"])

	def test_an_icon_and_a_small_flourish_stay(self):
		holder = section("#f8f9fa")
		holder["children"] += [self.drawn("0 0 24 24"), self.drawn("0 0 120 6")]
		blocks = page(holder, section("#253357"))
		D.apply_dividers(blocks, PALETTE, "wave", "p", ACCENT)
		self.assertEqual(3, len(holder["children"]))

	def test_a_drawing_that_holds_text_stays(self):
		text = {"element": "div", "children": [], "innerHTML": '<svg viewBox="0 0 1200 40"><text x="0" y="20">Since 1998</text></svg>'}
		self.assertFalse(D.is_drawn_divider(text))


if __name__ == "__main__":
	unittest.main()
