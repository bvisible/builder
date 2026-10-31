# //// Neoffice — added file (no upstream equivalent): a Tailwind component becomes a draft block of the hub (site_ai/nora/importer.py).
"""What is pinned: a component written in Tailwind becomes a block that carries nothing of its source (no word, no picture, no palette colour, no
address) and still lints; its colours are the tokens of the role they play on their ground, its breakpoints are the block's tablet and phone
styles, its buttons and its cards are the design system's (`u-btn`, `u-card`), siblings drawn the same way ask for the same words; a component
that cannot be a block is refused with the reason (a form, a `<details>`, a row of brands without its logos); the same component is always the
same block, and the source, its licence and its holder travel in the block's notes. The components are written here, in Tailwind, not copied.
No Frappe, no network, no model."""

import re
import unittest

from builder.site_ai.nora import block_format, importer


def page(body: str) -> str:
	return f"<!doctype html><html><head><title>x</title><script src='/a.js'></script></head><body>{body}</body></html>"


FEATURES = page("""
<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
  <div class="mx-auto max-w-lg text-center">
    <h2 class="text-3xl/tight font-bold text-gray-900 sm:text-4xl">Features for growth</h2>
    <p class="mt-4 text-lg text-pretty text-gray-700">A short text of a few words to be replaced by the writer of the site.</p>
  </div>
  <div class="mt-8 grid grid-cols-1 gap-8 md:grid-cols-3">
    <div class="rounded-lg border border-gray-200 p-6">
      <div class="inline-flex rounded-lg bg-gray-100 p-3 text-gray-700"><svg class="size-6"><path d="M0 0"/></svg></div>
      <h3 class="mt-4 text-lg font-semibold text-gray-900">High performance</h3>
      <p class="mt-2 text-pretty text-gray-700">Lightning quick load times for every device</p>
    </div>
    <div class="rounded-lg border border-gray-200 p-6">
      <div class="inline-flex rounded-lg bg-gray-100 p-3 text-gray-700"><svg class="size-6"><path d="M0 0"/></svg></div>
      <h3 class="mt-4 text-lg font-semibold text-gray-900">Secure by design</h3>
      <p class="mt-2 text-pretty text-gray-700">Every request is checked twice before it is served to anyone</p>
    </div>
  </div>
</div>
""")

DARK_CTA = page("""
<section class="bg-gray-900">
  <div class="mx-auto max-w-screen-xl px-4 py-16 text-center">
    <h2 class="text-3xl font-bold text-white">Ready to start the project today</h2>
    <p class="mt-4 text-gray-300">Come and see us, we answer within the day.</p>
    <a href="#" class="mt-8 inline-block rounded-sm bg-indigo-600 px-12 py-3 text-sm font-medium text-white hover:bg-indigo-700">Get started</a>
    <a href="#" class="ml-2 inline-block rounded-sm border border-white px-12 py-3 text-sm font-medium text-white">Learn more</a>
  </div>
</section>
""")


def make(markup: str, kind: str = "feature-grid", name: str = "features.hu-test-1") -> dict:
	return importer.import_markup(
		markup, kind=kind, block_id=name, title="A test", source_note="Imported from a test."
	)


def walk(node):
	yield node
	for child in node.get("c") or []:
		yield from walk(child)


def find(node, **want):
	return [n for n in walk(node) if all(n.get(k) == v for k, v in want.items())]


class TestTailwindBecomesCss(unittest.TestCase):
	def test_spacing_sizes_and_the_other_utilities(self):
		u = importer.utility
		self.assertEqual(
			u("p-4"),
			{"paddingTop": "1rem", "paddingRight": "1rem", "paddingBottom": "1rem", "paddingLeft": "1rem"},
		)
		self.assertEqual(u("px-0.5"), {"paddingLeft": "0.125rem", "paddingRight": "0.125rem"})
		self.assertEqual(u("-mt-2"), {"marginTop": "-0.5rem"})
		self.assertEqual(u("mx-auto"), {"marginLeft": "auto", "marginRight": "auto"})
		self.assertEqual(u("gap-px"), {"gap": "1px"})
		self.assertEqual(u("w-1/2"), {"width": "50%"})
		self.assertEqual(u("size-5"), {"width": "1.25rem", "height": "1.25rem"})
		self.assertEqual(u("max-w-3xl"), {"maxWidth": "48rem"})
		self.assertEqual(u("grid-cols-3"), {"gridTemplateColumns": "repeat(3, minmax(0, 1fr))"})
		self.assertEqual(u("col-span-2"), {"gridColumn": "span 2 / span 2"})
		self.assertEqual(u("items-center"), {"alignItems": "center"})
		self.assertEqual(u("justify-between"), {"justifyContent": "space-between"})
		self.assertEqual(u("font-semibold"), {"fontWeight": "600"})
		self.assertEqual(u("text-lg/tight"), {"fontSize": "1.125rem", "lineHeight": "1.25"})
		self.assertEqual(u("h-[calc(100%-2rem)]"), {"height": "calc(100% - 2rem)"})

	def test_what_only_decorates_says_nothing_and_what_is_unknown_is_none(self):
		for decoration in (
			"transition",
			"duration-200",
			"cursor-pointer",
			"antialiased",
			"font-sans",
			"outline-hidden",
		):
			self.assertEqual(importer.utility(decoration), {}, decoration)
		self.assertIsNone(importer.utility("bg-[url(/x.png)]"))
		self.assertIsNone(importer.utility("mg-6"))
		self.assertIsNone(importer.utility("rounded-ss-[30px]"))

	def test_rounded_and_shadow_are_the_sites_own(self):
		self.assertEqual(importer.utility("rounded-lg"), {"borderRadius": "var(--radius-lg)"})
		self.assertEqual(importer.utility("rounded-full"), {"borderRadius": "var(--radius-pill)"})
		self.assertEqual(
			importer.utility("rounded-t-lg"),
			{"borderTopLeftRadius": "var(--radius-lg)", "borderTopRightRadius": "var(--radius-lg)"},
		)
		self.assertEqual(importer.utility("shadow-sm"), {"boxShadow": "var(--shadow-sm)"})
		self.assertEqual(importer.utility("shadow-none"), {"boxShadow": "none"})

	def test_variants(self):
		self.assertEqual(importer.split_variants("md:hover:bg-red-500"), (["md", "hover"], "bg-red-500"))
		self.assertEqual(importer.split_variants("h-[calc(100%-2rem)]"), ([], "h-[calc(100%-2rem)]"))
		levels, dropped, ignored = importer.parse_classes(
			[
				"grid-cols-1",
				"md:grid-cols-3",
				"hover:bg-gray-100",
				"rtl:text-right",
				"ltr:sm:text-left",
				"foo-bar",
			]
		)
		self.assertEqual(levels[0]["gridTemplateColumns"], "repeat(1, minmax(0, 1fr))")
		self.assertEqual(levels[2]["gridTemplateColumns"], "repeat(3, minmax(0, 1fr))")
		self.assertEqual(levels[1]["textAlign"], "left")  # `ltr:` is the direction we draw
		self.assertEqual(dropped, ["foo-bar"])
		self.assertEqual(sorted(ignored), ["hover:bg-gray-100", "rtl:text-right"])

	def test_a_shorthand_never_wins_over_an_axis(self):
		levels, _d, _i = importer.parse_classes(["px-2", "p-6"])
		self.assertEqual(levels[0]["paddingLeft"], "0.5rem")
		self.assertEqual(levels[0]["paddingTop"], "1.5rem")


class TestColoursAreTheRoleTheyPlay(unittest.TestCase):
	def token(self, kind, text, ground="plain"):
		return importer.resolve_colour(importer.colour(kind, text), ground)

	def test_ink_on_the_plain_ground(self):
		self.assertEqual(self.token("text", "gray-900"), "{{ground.ink}}")
		self.assertEqual(self.token("text", "black"), "{{ground.ink}}")
		self.assertEqual(self.token("text", "gray-700"), "{{ground.muted}}")
		self.assertEqual(self.token("text", "gray-500"), "{{ground.muted}}")
		self.assertEqual(self.token("text", "indigo-700"), "{{ground.accent}}")

	def test_ink_on_a_deep_ground(self):
		self.assertEqual(self.token("text", "white", "deep"), "{{ground.ink}}")
		self.assertEqual(self.token("text", "gray-300", "deep"), "{{ground.muted}}")
		self.assertEqual(self.token("text", "gray-100", "deep"), "{{ground.ink}}")

	def test_surfaces(self):
		self.assertEqual(self.token("bg", "white"), "{{ground.background}}")
		self.assertEqual(self.token("bg", "gray-100"), "{{tint}}")
		self.assertEqual(self.token("bg", "gray-100", "tint"), "{{background}}")
		self.assertEqual(self.token("bg", "white/10", "deep"), "{{ground.hair}}")

	def test_borders(self):
		self.assertEqual(self.token("border", "gray-200"), "{{ground.hair}}")
		self.assertEqual(self.token("border", "white", "deep"), "{{ground.hair}}")
		self.assertEqual(self.token("border", "indigo-600"), "{{ground.accent}}")

	def test_the_ground_a_surface_makes(self):
		g = lambda text: importer.ground_of(importer.colour("bg", text))  # noqa: E731
		self.assertEqual(g("gray-900"), "deep")
		self.assertEqual(g("indigo-600"), "deep")
		self.assertEqual(g("gray-50"), "tint")
		self.assertEqual(g("white"), "plain")
		self.assertEqual(g("indigo-100"), "plain")
		self.assertEqual(importer.ground_of(None), "plain")

	def test_a_colour_that_is_not_a_palette_colour_is_unknown(self):
		self.assertIsNone(importer.colour("text", "[#0072b1]"))
		self.assertIsNone(importer.colour("bg", "gray-123"))


class TestAComponentBecomesABlock(unittest.TestCase):
	def setUp(self):
		self.block = make(FEATURES)
		self.tree = self.block["tree"]

	def test_it_is_a_section_in_the_sites_container(self):
		self.assertEqual(self.tree["el"], "section")
		self.assertEqual(self.tree["style"]["backgroundColor"], "{{ground.background}}")
		container = self.tree["c"][0]
		self.assertEqual(container["style"]["maxWidth"], "{{container}}")
		self.assertEqual(container["style"]["paddingLeft"], "{{gutter}}")
		self.assertEqual(container["m_style"]["paddingLeft"], "{{gutter_phone}}")

	def test_it_lints(self):
		errors, warnings = block_format.lint(
			self.tree,
			block_id=self.block["id"],
			kinds=self.block["kinds"],
			photos=self.block["photos"],
			motion="None",
		)
		self.assertEqual((errors, warnings), ([], []))

	def test_every_word_is_a_slot_of_the_length_of_the_source(self):
		texts = [n["text"] for n in walk(self.tree) if "text" in n]
		self.assertTrue(texts)
		for text in texts:
			self.assertRegex(text, r"^WRITE [\w-]+: ")
		blob = repr(self.tree)
		for word in ("Features", "growth", "performance", "Lightning", "Secure"):
			self.assertNotIn(word, blob)
		heading = find(self.tree, name="heading")[0]
		self.assertRegex(heading["text"], r"^WRITE heading: 2 to 4 words$")

	def test_the_first_heading_is_the_heading_and_the_others_are_titles(self):
		self.assertEqual(len(find(self.tree, name="heading")), 1)
		self.assertEqual(len(find(self.tree, name="item-title")), 2)

	def test_no_palette_colour_survives(self):
		blob = repr(self.tree)
		self.assertNotRegex(blob, r"#[0-9a-fA-F]{3,8}\b|rgb|gray-|indigo-")

	def test_the_fonts_are_the_sites_and_the_ink_follows_the_ground(self):
		heading = find(self.tree, name="heading")[0]
		self.assertEqual(heading["style"]["fontFamily"], "{{font_heading}}")
		self.assertEqual(heading["style"]["color"], "{{ground.ink}}")
		lead = find(self.tree, name="lead")[0]
		self.assertEqual(lead["style"]["fontFamily"], "{{font_body}}")
		self.assertEqual(lead["style"]["color"], "{{ground.muted}}")

	def test_a_bordered_rounded_box_is_a_card_of_the_design_system(self):
		cards = find(self.tree, name="card")
		self.assertEqual(len(cards), 2)
		for card in cards:
			self.assertEqual(card["classes"], ["u-card"])
			self.assertNotIn("borderColor", card.get("style", {}))
			self.assertNotIn("borderRadius", card.get("style", {}))
			self.assertNotIn("paddingTop", card.get("style", {}))  # p-6 is the card's own padding

	def test_the_icons_are_left_out_and_said(self):
		self.assertEqual(find(self.tree, el="svg"), [])
		self.assertIn("2 icons of the source left out", self.block["notes"])
		for card in find(self.tree, name="card"):
			self.assertEqual([c["el"] for c in card["c"]], ["h3", "p"])

	def test_the_first_child_of_a_box_has_no_top_margin(self):
		for card in find(self.tree, name="card"):
			self.assertNotIn("marginTop", card["c"][0].get("style", {}))
			self.assertIn("marginTop", card["c"][1]["style"])

	def test_breakpoints_are_the_blocks_tablet_and_phone_styles(self):
		grid = find(self.tree, name="grid")[0]
		self.assertEqual(grid["style"]["gridTemplateColumns"], "repeat(3, minmax(0, 1fr))")
		self.assertEqual(grid["m_style"]["gridTemplateColumns"], "repeat(1, minmax(0, 1fr))")
		self.assertNotIn("t_style", grid)  # `md:` is the tablet and the desktop
		heading = find(self.tree, name="heading")[0]
		self.assertEqual(heading["style"]["fontSize"], "2.25rem")  # sm:text-4xl
		self.assertEqual(heading["m_style"]["fontSize"], "1.875rem")  # text-3xl

	def test_the_narrow_wrapper_is_kept_and_named(self):
		head = find(self.tree, name="head")[0]
		self.assertEqual(head["style"]["maxWidth"], "32rem")
		self.assertEqual(head["style"]["textAlign"], "center")

	def test_it_says_what_it_is(self):
		self.assertEqual(self.block["kinds"], ["feature-grid"])
		self.assertEqual(self.block["ground"], "plain")
		self.assertEqual(self.block["motion"], "None")
		self.assertTrue(self.block["look"].endswith("."))
		self.assertNotIn("Kept from", self.block["look"])
		self.assertIn("a heading", self.block["look"])

	def test_the_same_component_is_always_the_same_block(self):
		self.assertEqual(make(FEATURES), self.block)


class TestButtonsAndGrounds(unittest.TestCase):
	def setUp(self):
		self.block = make(DARK_CTA, kind="cta", name="cta.hu-test-1")
		self.tree = self.block["tree"]

	def test_a_dark_shell_is_a_deep_block(self):
		self.assertEqual(self.block["ground"], "deep")
		self.assertEqual(self.tree["style"]["backgroundColor"], "{{ground.background}}")

	def test_the_ink_is_the_deep_grounds(self):
		heading = find(self.tree, name="heading")[0]
		self.assertEqual(heading["style"]["color"], "{{ground.ink}}")
		self.assertEqual(find(self.tree, name="text")[0]["style"]["color"], "{{ground.muted}}")

	def test_a_filled_button_and_an_outlined_one(self):
		buttons = find(self.tree, el="a")
		# on a deep ground the filled button is the ground's own (`ground.button`), the outlined one is outlined
		self.assertEqual(
			[b["classes"] for b in buttons], [["u-btn", "u-btn--secondary"], ["u-btn", "u-btn--outline"]]
		)
		for button in buttons:
			self.assertEqual(button["attrs"], {"href": "{{cta_href}}"})
			self.assertRegex(button["text"], r"^WRITE button: ")
			self.assertNotIn("backgroundColor", button.get("style", {}))
			self.assertNotIn("color", button.get("style", {}))  # the class draws it

	def test_a_filled_button_on_the_plain_ground_is_the_primary_one(self):
		plain = make(
			page(
				'<div class="mx-auto max-w-7xl px-4 py-8"><a href="#" class="inline-block rounded bg-emerald-600 px-5 py-3 text-white">Go</a></div>'
			),
			kind="cta",
			name="cta.hu-test-2",
		)
		self.assertEqual(find(plain["tree"], el="a")[0]["classes"], ["u-btn", "u-btn--primary"])

	def test_a_link_without_padding_is_a_link_not_a_button(self):
		link = make(
			page(
				'<div class="mx-auto max-w-7xl px-4 py-8"><p class="text-gray-700">Hello there my friend</p><a href="#" class="text-sm text-indigo-700 underline">More</a></div>'
			),
			kind="cta",
			name="cta.hu-test-3",
		)
		anchor = find(link["tree"], el="a")[0]
		self.assertNotIn("classes", anchor)
		self.assertEqual(anchor["style"]["color"], "{{ground.accent}}")
		self.assertEqual(anchor["attrs"], {"href": "{{cta_href}}"})

	def test_a_wide_shell_is_the_sites_container_not_a_narrow_box(self):
		self.assertEqual(find(self.tree, name="narrow"), [])


class TestPicturesAndRepeatedGroups(unittest.TestCase):
	TEAM = page("""
	<div class="mx-auto max-w-7xl px-4 py-8">
	  <h2 class="text-3xl font-bold text-gray-900">Our team</h2>
	  <ul class="mt-8 grid grid-cols-2 gap-8 lg:grid-cols-3">
	    <li><img alt="" src="https://example.com/a.jpg" class="aspect-square w-full rounded-full object-cover"><h3 class="mt-2 font-medium text-gray-900">Ann</h3><p class="text-sm text-gray-500">Chef</p></li>
	    <li><img alt="" src="https://example.com/b.jpg" class="aspect-square w-full rounded-full object-cover"><h3 class="mt-2 font-medium text-gray-900">Bob the baker of the house</h3><p class="text-sm text-gray-500">Baker and pastry chef</p></li>
	  </ul>
	</div>""")

	def test_a_picture_is_a_numbered_photo_with_an_alt_slot_and_never_an_address(self):
		block = make(self.TEAM, kind="team", name="team.hu-test-1")
		images = find(block["tree"], el="img")
		self.assertEqual([i["attrs"]["src"] for i in images], ["{{photo.0}}", "{{photo.1}}"])
		for image in images:
			self.assertRegex(image["attrs"]["alt"], r"^WRITE alt: ")
		self.assertEqual(block["photos"], 2)
		self.assertNotIn("example.com", repr(block["tree"]))

	def test_siblings_drawn_the_same_way_ask_for_the_same_words(self):
		block = make(self.TEAM, kind="team", name="team.hu-test-1")
		titles = [n["text"] for n in find(block["tree"], name="item-title")]
		self.assertEqual(len(titles), 2)
		self.assertEqual(titles[0], titles[1])
		captions = [n["text"] for n in find(block["tree"], name="caption")]
		self.assertEqual(captions[0], captions[1])

	def test_the_heading_that_repeats_is_not_the_sections_heading(self):
		cards = page("""<div class="mx-auto max-w-7xl px-4 py-8"><div class="grid grid-cols-2 gap-4">
		<div class="rounded-lg border border-gray-200 p-6"><h2 class="text-lg font-bold text-gray-900">Starter</h2><p class="text-gray-700">For one person</p></div>
		<div class="rounded-lg border border-gray-200 p-6"><h2 class="text-lg font-bold text-gray-900">Team</h2><p class="text-gray-700">For a small team</p></div>
		</div></div>""")
		block = make(cards, kind="cards", name="cards.hu-test-1")
		self.assertEqual(find(block["tree"], name="heading"), [])
		self.assertEqual(len(find(block["tree"], name="item-title")), 2)

	def test_a_figure_is_a_figure_whatever_its_currency(self):
		figures = page("""<dl class="mx-auto max-w-7xl grid grid-cols-2 gap-4 px-4 py-8">
		<div class="flex flex-col"><dt class="order-last text-lg text-gray-500">Sales</dt><dd class="text-4xl font-extrabold text-blue-600">$4.8m</dd></div>
		<div class="flex flex-col"><dt class="order-last text-lg text-gray-500">Addons</dt><dd class="text-4xl font-extrabold text-blue-600">24</dd></div></dl>""")
		block = make(figures, kind="figures", name="figures.hu-test-1")
		slots = [n["text"].split(":")[0] for n in walk(block["tree"]) if "text" in n]
		self.assertEqual(slots, ["WRITE caption", "WRITE figure", "WRITE caption", "WRITE figure"])
		numbers = find(block["tree"], name="figure")
		self.assertEqual(numbers[0]["style"]["color"], "{{ground.accent}}")


class TestSpacingBetweenChildren(unittest.TestCase):
	def test_space_y_and_divide_become_the_childrens_own(self):
		markup = page("""<div class="mx-auto max-w-7xl px-4 py-8"><div class="space-y-4">
		<p class="text-gray-700">One</p><p class="text-gray-700">Two</p><p class="text-gray-700">Three</p></div>
		<div class="mt-8 divide-y divide-gray-200"><p class="py-2 text-gray-700">A</p><p class="py-2 text-gray-700">B</p></div></div>""")
		block = make(markup, kind="text", name="text.hu-test-1")
		first, second = block["tree"]["c"][0]["c"]
		spaced = first["c"]
		self.assertNotIn("marginTop", spaced[0].get("style", {}))
		self.assertEqual(spaced[1]["style"]["marginTop"], "1rem")
		self.assertEqual(spaced[2]["style"]["marginTop"], "1rem")
		rows = second["c"]
		self.assertNotIn("borderTopWidth", rows[0].get("style", {}))
		self.assertEqual(rows[1]["style"]["borderTopWidth"], "1px")
		self.assertEqual(rows[1]["style"]["borderColor"], "{{ground.hair}}")


class TestBordersAndHiddenWords(unittest.TestCase):
	def test_a_border_on_one_side_leaves_the_others_at_zero(self):
		# a page without a reset draws a `solid` border at `medium` on the sides nobody set
		self.assertEqual(
			importer.utility("border-t"),
			{"borderWidth": "0", "borderTopWidth": "1px", "borderStyle": "solid"},
		)
		self.assertEqual(
			importer.utility("border"),
			{
				"borderTopWidth": "1px",
				"borderRightWidth": "1px",
				"borderBottomWidth": "1px",
				"borderLeftWidth": "1px",
				"borderStyle": "solid",
			},
		)

	def test_a_divider_leaves_the_other_sides_at_zero_too(self):
		markup = page("""<div class="mx-auto max-w-7xl px-4 py-8"><div class="divide-y divide-gray-200 rounded-lg border border-gray-200">
		<p class="p-4 text-gray-700">One</p><p class="p-4 text-gray-700">Two</p></div></div>""")
		block = make(markup, kind="cards", name="cards.hu-test-1")
		second = find(block["tree"], name="card")[0]["c"][1]
		self.assertEqual((second["style"]["borderWidth"], second["style"]["borderTopWidth"]), ("0", "1px"))

	def test_a_rounded_box_with_a_side_border_only_is_not_a_card(self):
		markup = page(
			'<div class="mx-auto max-w-7xl px-4 py-8"><div class="rounded-lg border-b p-6"><p class="text-gray-700">Some words in a box</p></div></div>'
		)
		self.assertEqual(find(make(markup, kind="cards", name="cards.hu-test-1")["tree"], name="card"), [])

	def test_words_for_screen_readers_are_not_the_blocks_words(self):
		markup = page("""<div class="mx-auto max-w-7xl px-4 py-8"><h3 class="text-lg font-bold text-gray-900">Anna</h3>
		<a href="#" class="block"><span class="sr-only">Instagram</span><svg class="size-5"></svg></a></div>""")
		block = make(markup, kind="team", name="team.hu-test-1")
		self.assertEqual([n["el"] for n in walk(block["tree"]["c"][0])][1:], ["h3"])
		self.assertNotIn("Instagram", repr(block["tree"]))


class TestWhatCannotBeABlock(unittest.TestCase):
	def refused(self, markup, **kw):
		with self.assertRaises(importer.Refused) as caught:
			make(markup, **kw)
		return str(caught.exception)

	def test_a_form(self):
		self.assertIn(
			"form",
			self.refused(
				page(
					'<div class="px-4"><form><input type="email"><button class="px-4 py-2 bg-gray-900 text-white">Go</button></form></div>'
				)
			),
		)

	def test_a_details(self):
		self.assertIn(
			"details",
			self.refused(page('<div class="px-4"><details><summary>Q</summary><p>A</p></details></div>')),
		)

	def test_a_table(self):
		self.assertIn("table", self.refused(page("<div><table><tr><td>1</td></tr></table></div>")))

	def test_more_than_one_root(self):
		self.assertIn("2 elements", self.refused(page("<div><p>a</p></div><div><p>b</p></div>")))

	def test_nothing_left_once_the_icons_are_dropped(self):
		self.assertIn("icons", self.refused(page('<div class="px-4"><svg></svg><svg></svg></div>')))

	def test_a_row_of_brands_without_its_logos(self):
		markup = page(
			'<div class="mx-auto max-w-7xl px-4"><h2 class="text-xl font-bold text-gray-900">Trusted by</h2><div class="flex"><svg></svg><svg></svg><svg></svg></div></div>'
		)
		self.assertIn("logos", self.refused(markup, kind="brand-row", name="brand-row.hu-test-1"))

	def test_too_many_classes_that_are_not_understood(self):
		markup = page(
			'<div class="px-4 a-1 b-2 c-3 d-4 e-5 f-6 g-7"><p class="text-gray-700">Hello there</p></div>'
		)
		self.assertIn("not understood", self.refused(markup))

	def test_more_pictures_than_a_block_holds(self):
		images = "".join('<img alt="" src="https://example.com/x.jpg" class="h-8">' for _ in range(7))
		self.assertIn(
			"7 pictures",
			self.refused(
				page(
					f'<div class="mx-auto max-w-7xl px-4 py-8"><h2 class="text-xl font-bold">Hi</h2><div class="flex">{images}</div></div>'
				),
				kind="gallery",
				name="gallery.hu-test-1",
			),
		)


class TestHyperUI(unittest.TestCase):
	def test_the_id_is_stable_and_valid(self):
		self.assertEqual(
			importer.hyperui_id("feature-grids", 2, "feature-grid"), "features.hu-feature-grids-2"
		)
		self.assertRegex(importer.hyperui_id("team-sections", 3, "team"), block_format.BLOCK_ID)

	def test_every_category_is_a_kind_the_plan_knows(self):
		from builder.site_ai.nora.site_plan import SECTION_KINDS

		for category, kind in importer.HYPERUI_KINDS.items():
			self.assertIn(kind, SECTION_KINDS, category)
			self.assertIn(category, importer.HYPERUI_COUNT)

	def test_the_source_and_its_licence_travel_with_the_block(self):
		block = importer.import_hyperui_markup("feature-grids", 1, FEATURES)
		self.assertIn("HyperUI", block["notes"])
		self.assertIn("MIT licence", block["notes"])
		self.assertIn("Copyright (c) Mark Mead", block["notes"])
		self.assertIn("github.com/markmead/hyperui", block["notes"])
		self.assertIn("feature-grids/1.html", block["notes"])
		self.assertRegex(block["notes"], r"[0-9a-f]{10}")
		self.assertEqual(block["id"], "features.hu-feature-grids-1")
		self.assertEqual(block["title"], "Feature grid 1 (HyperUI)")

	def test_the_import_reports_what_it_made_and_what_it_refused(self):
		pages = {("cta", 1): DARK_CTA}
		originals = (importer.fetch_hyperui, capture_push := importer.capture.push_block)
		try:
			importer.fetch_hyperui = lambda category, number: (
				pages.get((category, number)) or page("<form></form>")
			)
			importer.capture.push_block = lambda block: f"draft {block['id']} v1"
			done = importer.import_hyperui(["ctas"], push=True)
		finally:
			importer.fetch_hyperui, importer.capture.push_block = originals[0], capture_push
		self.assertEqual(done["blocks"], {})  # the fake serves a form for every ctas/N: all refused
		self.assertEqual(sorted(done["refused"]), [f"ctas/{n}" for n in range(1, 5)])
		self.assertTrue(all("form" in why for why in done["refused"].values()))

	def test_nothing_is_sent_unless_asked(self):
		sent = []
		originals = (importer.fetch_hyperui, importer.capture.push_block)
		try:
			importer.fetch_hyperui = lambda category, number: DARK_CTA
			importer.capture.push_block = lambda block: sent.append(block["id"]) or "sent"
			done = importer.import_hyperui(["ctas"], push=False)
		finally:
			importer.fetch_hyperui, importer.capture.push_block = originals
		self.assertEqual(sent, [])
		self.assertEqual(done["sent"], {})
		self.assertEqual(len(done["blocks"]), 4)
		self.assertTrue(re.fullmatch(r"cta\.hu-ctas-\d", done["blocks"]["ctas/1"]))


if __name__ == "__main__":
	unittest.main()
