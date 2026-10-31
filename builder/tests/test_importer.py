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
		self.assertIn("a centred heading and a short text", self.block["look"])
		self.assertIn("for what the business offers, at a glance", self.block["look"])

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
		block = make(markup, kind="text", name="text.hu-test-1")
		second = find(block["tree"], name="card")[0]["c"][1]
		self.assertEqual((second["style"]["borderWidth"], second["style"]["borderTopWidth"]), ("0", "1px"))

	def test_a_rounded_box_with_a_side_border_only_is_not_a_card(self):
		markup = page(
			'<div class="mx-auto max-w-7xl px-4 py-8"><div class="rounded-lg border-b p-6"><p class="text-gray-700">Some words in a box</p></div></div>'
		)
		self.assertEqual(find(make(markup, kind="text", name="text.hu-test-1")["tree"], name="card"), [])

	def test_words_for_screen_readers_are_not_the_blocks_words(self):
		markup = page("""<div class="mx-auto max-w-7xl px-4 py-8"><h3 class="text-lg font-bold text-gray-900">Anna</h3>
		<a href="#" class="block"><span class="sr-only">Instagram</span><svg class="size-5"></svg></a></div>""")
		block = make(markup, kind="team", name="team.hu-test-1")
		self.assertEqual([n["el"] for n in walk(block["tree"]["c"][0])][1:], ["h3"])
		self.assertNotIn("Instagram", repr(block["tree"]))


FAQ = page("""
<div class="space-y-4 mx-auto max-w-3xl p-6">
  <details class="group rounded-md border border-gray-100 bg-gray-50 p-4" open>
    <summary class="flex items-center justify-between gap-1.5 text-gray-900">
      <h2 class="text-lg font-medium">How long does a loaf keep before it goes stale on the shelf?</h2>
      <svg class="size-5 shrink-0 group-open:-rotate-180"><path d="M0 0"/></svg>
    </summary>
    <p class="px-4 pt-4 text-gray-700">A loaf keeps two days on the shelf and a week in the freezer, sliced, and it toasts straight from there without any change.</p>
  </details>
  <details class="group rounded-md border border-gray-100 bg-gray-50 p-4">
    <summary class="flex items-center justify-between gap-1.5 text-gray-900">
      <h2 class="text-lg font-medium">Do you deliver?</h2>
      <svg class="size-5 shrink-0"><path d="M0 0"/></svg>
    </summary>
    <p class="px-4 pt-4 text-gray-700">Yes, to the whole valley, every morning before eight, for orders sent the evening before.</p>
  </details>
</div>
""")


class TestFoldingQuestions(unittest.TestCase):
	def setUp(self):
		self.block = make(FAQ, kind="faq", name="faq.hu-test-1")
		self.tree = self.block["tree"]

	def test_it_lints_with_details_and_summary_in_the_format(self):
		errors, warnings = block_format.lint(
			self.tree, block_id=self.block["id"], kinds=["faq"], photos=0, motion="None"
		)
		self.assertEqual(([], []), (errors, warnings))
		self.assertIn("details", block_format.TAGS)
		self.assertIn("summary", block_format.TAGS)

	def test_the_questions_are_the_sites_accordion(self):
		faq = find(self.tree, classes=["u-faq"])[0]
		self.assertEqual("faq", faq["name"])
		self.assertEqual(["details", "details"], [c["el"] for c in faq["c"]])
		for item in faq["c"]:
			self.assertEqual(["summary", "p"], [c["el"] for c in item["c"]])

	def test_a_question_keeps_the_type_of_the_source_and_nothing_of_its_box(self):
		for item in find(self.tree, name="question", el="details"):
			self.assertNotIn("style", item)
			self.assertNotIn("attrs", item)  # `open` is the visitor's
		summary = find(self.tree, el="summary")[0]
		self.assertEqual(
			{
				"fontSize": "1.125rem",
				"fontWeight": "500",
				"lineHeight": "1.556",
				"color": "{{ground.ink}}",
				"fontFamily": "{{font_body}}",
			},
			summary["style"],
		)

	def test_a_question_and_an_answer_ask_for_what_they_are(self):
		summary = find(self.tree, el="summary")[0]
		answer = find(self.tree, name="answer")[0]
		self.assertRegex(
			summary["text"], r"^WRITE question: a real question a customer asks, \d+ to \d+ words$"
		)
		self.assertRegex(
			answer["text"], r"^WRITE answer: an answer of \d+ to \d+ words from the business's own facts$"
		)
		self.assertNotIn("How long", repr(self.tree))

	def test_the_answer_has_no_air_of_its_own_the_accordion_gives_it(self):
		answer = find(self.tree, name="answer")[0]
		for key in ("margin", "paddingLeft", "paddingTop", "paddingRight"):
			self.assertNotIn(key, answer["style"])
		self.assertEqual("{{ground.muted}}", answer["style"]["color"])

	def test_the_spacing_of_the_source_is_not_kept_and_the_width_of_the_page_is(self):
		faq = find(self.tree, classes=["u-faq"])[0]
		self.assertNotIn("style", faq)
		narrow = find(self.tree, name="narrow")[0]
		self.assertEqual("48rem", narrow["style"]["maxWidth"])  # `max-w-3xl` was on the page's body

	def test_the_questions_of_a_list_ask_for_the_same_words(self):
		questions = [n["text"] for n in find(self.tree, el="summary")]
		self.assertEqual(1, len(set(questions)))
		answers = [n["text"] for n in find(self.tree, name="answer")]
		self.assertEqual(1, len(set(answers)))

	def test_the_icon_is_left_out_and_said(self):
		self.assertIn("2 icons", self.block["notes"])

	def test_a_single_details_is_not_an_accordion(self):
		one = make(
			page(
				'<div class="px-4"><details><summary class="text-gray-900">A question here</summary><p class="text-gray-700">An answer here</p></details></div>'
			),
			kind="text",
			name="text.hu-test-2",
		)
		self.assertEqual([], find(one["tree"], classes=["u-faq"]))


def role_page(body):
	return page(f'<div class="mx-auto max-w-screen-xl px-4 py-8">{body}</div>')


class TestColoursNamedByTheirRole(unittest.TestCase):
	"""Flowbite names a colour by the role it plays (`text-heading`, `bg-neutral-secondary`, `border-default`), shadcn/ui too (`text-muted-foreground`,
	`bg-primary`, `border-border`): each lands on the token the same role has in the table of Tailwind colours."""

	def token(self, kind, text, ground="plain"):
		return importer.resolve_colour(importer.colour(kind, text), ground)

	def test_flowbite_roles(self):
		self.assertEqual("{{ground.ink}}", self.token("text", "heading"))
		self.assertEqual("{{ground.muted}}", self.token("text", "body"))
		self.assertEqual("{{ground.accent}}", self.token("text", "fg-brand"))
		self.assertEqual("{{ground.background}}", self.token("bg", "neutral-primary"))
		self.assertEqual("{{tint}}", self.token("bg", "neutral-secondary-medium"))
		self.assertEqual("{{ground.hair}}", self.token("border", "default"))
		self.assertEqual("{{ground.hair}}", self.token("border", "default-medium"))

	def test_shadcn_roles(self):
		self.assertEqual("{{ground.ink}}", self.token("text", "foreground"))
		self.assertEqual("{{ground.muted}}", self.token("text", "muted-foreground"))
		self.assertEqual("{{ground.accent}}", self.token("text", "primary"))
		self.assertEqual("{{ground.ink}}", self.token("text", "primary-foreground", "deep"))
		self.assertEqual("{{ground.background}}", self.token("bg", "background"))
		self.assertEqual("{{tint}}", self.token("bg", "muted"))
		self.assertEqual("{{ground.hair}}", self.token("border", "border"))

	def test_a_brand_surface_is_a_deep_one_and_a_pale_one_is_not(self):
		self.assertEqual("deep", importer.ground_of(importer.colour("bg", "brand")))
		self.assertEqual("deep", importer.ground_of(importer.colour("bg", "primary")))
		self.assertEqual("plain", importer.ground_of(importer.colour("bg", "brand-soft")))
		self.assertEqual("tint", importer.ground_of(importer.colour("bg", "muted")))

	def test_an_opacity_is_kept_and_a_name_that_is_not_a_role_is_unknown(self):
		self.assertEqual(0.9, importer.colour("bg", "primary/90").alpha)
		self.assertIsNone(importer.colour("text", "sparkle"))

	def test_a_side_border_colour_and_the_start_and_end_sides(self):
		self.assertEqual(
			{"borderColor": importer.colour("border", "default")}, importer.utility("border-b-default")
		)
		self.assertEqual(
			{"borderWidth": "0", "borderLeftWidth": "0", "borderStyle": "solid"},
			importer.utility("border-s-0"),
		)
		self.assertEqual({"borderRadius": "var(--radius)"}, importer.utility("rounded-base"))

	def test_a_component_written_with_roles_takes_the_design_system(self):
		block = make(
			role_page(
				'<h1 class="text-4xl font-bold text-heading">A headline of a few words</h1>'
				'<p class="text-body">Some words that say what we do and for whom we do it.</p>'
				'<button type="button" class="text-white bg-brand rounded-base px-5 py-3">Start</button>'
				'<button type="button" class="text-body bg-neutral-secondary-medium border border-default-medium rounded-base px-5 py-3">More</button>'
			),
			kind="hero",
			name="hero.fb-test-1",
		)
		blob = repr(block["tree"])
		for word in ("brand", "neutral", "default", "text-", "bg-"):
			self.assertNotIn(word, blob)
		self.assertEqual(
			["u-btn--primary", "u-btn--outline"], [b["classes"][1] for b in find(block["tree"], el="a")]
		)
		self.assertEqual("{{ground.ink}}", find(block["tree"], name="heading")[0]["style"]["color"])


FLOWBITE_PAGE = """---
title: Tailwind CSS Jumbotron - Flowbite
---

Some text of the page that is not an example.

## Default jumbotron

{{< example bodyClass="p-0" github="components/jumbotron.md" show_dark=true >}}

<section class="bg-neutral-primary">
    <div class="py-8 px-4 mx-auto max-w-screen-2xl text-center lg:py-16">
        <h1 class="mb-6 text-4xl font-bold text-heading md:text-5xl">A headline for a start</h1>
        <a href="{{< param homepage >}}/docs/" class="text-fg-brand">A link whose address is a shortcode</a>
    </div>
</section>
{{< /example >}}

## Another one

{{< example github="components/jumbotron.md" >}}
<section class="bg-neutral-primary"><div class="px-4"><p class="text-body">Second example of the page</p></div></section>
{{< /example >}}
"""

ACCORDION = """<div id="accordion-collapse" data-accordion="collapse" class="rounded-base border border-default overflow-hidden shadow-xs">
  <h2 id="h1"><button type="button" class="flex w-full p-5 text-body" data-accordion-target="#b1" aria-expanded="true"><span>What is it?</span><svg data-accordion-icon class="w-5 h-5"></svg></button></h2>
  <div id="b1" class="hidden" aria-labelledby="h1"><div class="p-4"><p class="mb-2 text-body">It is a library of components for pages.</p><p class="text-body">A second paragraph that is left out.</p></div></div>
  <h2 id="h2"><button type="button" class="flex w-full p-5 text-body" data-accordion-target="#b2" aria-expanded="false"><span>Is it free?</span><svg class="w-5 h-5"></svg></button></h2>
  <div id="b2" class="hidden" aria-labelledby="h2"><div class="p-4"><p class="text-body">Yes, it is free to use for all.</p></div></div>
</div>"""


class TestAPictureThatFillsItsCell(unittest.TestCase):
	def test_height_auto_and_max_width_is_a_picture_that_fills_its_cell(self):
		block = make(
			role_page(
				'<div class="grid grid-cols-2 gap-4"><div><img class="h-auto max-w-full rounded-lg" src="https://example.com/a.jpg" alt=""></div><div><img class="h-auto max-w-full rounded-lg" src="https://example.com/b.jpg" alt=""></div></div>'
			),
			kind="gallery",
			name="gallery.fb-test-1",
		)
		for image in find(block["tree"], el="img"):
			self.assertEqual("100%", image["style"]["width"])
			self.assertEqual("cover", image["style"]["objectFit"])

	def test_a_picture_with_a_height_and_no_width_keeps_its_proportions(self):
		block = make(
			role_page(
				'<div class="flex"><img class="h-8" src="https://example.com/a.jpg" alt=""><img class="h-8" src="https://example.com/b.jpg" alt=""></div>'
			),
			kind="gallery",
			name="gallery.fb-test-2",
		)
		for image in find(block["tree"], el="img"):
			self.assertEqual("auto", image["style"]["width"])
			self.assertEqual("contain", image["style"]["objectFit"])


# what launch-ui renders (written here, in its idioms): a gradient button, a gradient text, a glow, a picture and its dark twin, `max-w-container`
LAUNCH_HERO = page(
	"""
<section data-slot="section" class="line-b px-4 py-12 sm:py-24 md:py-32 group relative overflow-hidden fade-bottom">
  <div class="max-w-container relative z-10 mx-auto flex flex-col items-center gap-6 text-center sm:gap-8">
    <h1 class="animate-appear from-foreground to-foreground relative z-10 inline-block bg-linear-to-r bg-clip-text text-4xl font-semibold text-transparent drop-shadow-2xl sm:text-6xl">A headline for the product of the day</h1>
    <p class="text-md animate-appear text-muted-foreground max-w-[740px] font-medium opacity-0 delay-100 sm:text-xl">A line that says what it does and for whom it does it, in a few words.</p>
    <div class="animate-appear relative z-10 flex justify-center gap-4 opacity-0 delay-300">
      <a href="/start" class="inline-flex items-center justify-center gap-2 text-sm font-medium text-primary-foreground shadow-sm hover:from-primary/70 bg-linear-to-b from-primary/60 to-primary/100 dark:from-primary/100 border-t-primary h-10 rounded-md px-5">Get started</a>
      <a href="/code" class="inline-flex items-center justify-center gap-2 text-sm font-medium glass-4 text-foreground h-10 rounded-md border px-5">Source</a>
    </div>
    <div class="relative w-full pt-12">
      <img src="/shot-light.png" alt="A screen" width="1248" height="765" class="w-full block dark:hidden">
      <img src="/shot-dark.png" alt="A screen" width="1248" height="765" class="w-full hidden dark:block">
    </div>
  </div>
  <div class="absolute top-0 left-0 h-full w-full translate-y-[1rem] opacity-80 transition-all duration-500">
    <div data-slot="glow" class="absolute w-full bottom-0"><div class="from-brand/30 to-brand-foreground/0 absolute left-1/2 h-[256px] w-[60%] -translate-x-1/2 scale-[2.5] rounded-[50%] bg-radial from-10% to-60% opacity-20"></div></div>
  </div>
</section>
"""
)


class TestLaunchUi(unittest.TestCase):
	def setUp(self):
		self.block = importer.import_launch_ui_markup("hero", LAUNCH_HERO)
		self.tree = self.block["tree"]

	def test_it_is_a_block_that_lints_with_the_words_and_the_picture_as_slots(self):
		errors, warnings = block_format.lint(
			self.tree, block_id=self.block["id"], kinds=["hero"], photos=self.block["photos"], motion="None"
		)
		self.assertEqual(([], []), (errors, warnings))
		self.assertEqual("hero.lu-hero", self.block["id"])
		self.assertEqual("Hero (Launch UI)", self.block["title"])
		self.assertNotIn("headline", repr(self.tree))

	def test_a_glow_and_an_animation_are_not_a_block_s(self):
		blob = repr(self.tree)
		for word in ("glow", "radial", "animate", "opacity", "translate", "scale", "gradient", "transparent"):
			self.assertNotIn(word, blob)
		self.assertEqual(
			[],
			[
				n
				for n in walk(self.tree)
				if "absolute" in repr(n.get("style", {})) and "bottom" in n.get("style", {})
			],
		)

	def test_the_small_dot_of_a_timeline_is_not_a_veil(self):
		dot = make(
			role_page(
				'<ol class="relative border-s border-default"><li class="mb-10 ms-4"><div class="absolute w-3 h-3 bg-neutral-secondary-medium rounded-full -start-1.5 border border-buffer"></div><h3 class="text-lg text-heading">A step of the story</h3></li></ol>'
			),
			kind="steps",
			name="steps.lu-test-1",
		)
		self.assertEqual(
			1, len(find(dot["tree"], el="div", name="box")) + len(find(dot["tree"], el="div", name="card"))
		)

	def test_the_picture_with_a_dark_twin_is_one_picture(self):
		images = find(self.tree, el="img")
		self.assertEqual(1, len(images))
		self.assertEqual(1, self.block["photos"])
		self.assertEqual("{{photo.0}}", images[0]["attrs"]["src"])

	def test_the_first_frame_of_an_entrance_animation_is_not_kept(self):
		# `opacity-0` + `animate-appear`: invisible until the animation plays; without the animation it would be invisible for good
		for node in walk(self.tree):
			self.assertNotIn("opacity", node.get("style", {}))
		self.assertEqual("{{ground.muted}}", find(self.tree, name="lead")[0]["style"]["color"])

	def test_the_text_of_a_gradient_heading_is_ink_not_transparent(self):
		heading = find(self.tree, name="heading")[0]
		self.assertEqual("{{ground.ink}}", heading["style"]["color"])
		self.assertNotIn("backgroundColor", heading["style"])

	def test_a_button_with_a_gradient_is_the_primary_one_and_a_glass_one_the_outlined_one(self):
		buttons = find(self.tree, el="a")
		self.assertEqual(
			[["u-btn", "u-btn--primary"], ["u-btn", "u-btn--outline"]], [b["classes"] for b in buttons]
		)

	def test_the_width_of_the_library_is_the_sites_container_and_nothing_clips(self):
		self.assertEqual("{{container}}", find(self.tree, name="head")[0]["style"]["maxWidth"])
		self.assertNotIn("overflow", repr(self.tree))

	def test_the_source_and_its_licence_travel_with_the_block(self):
		for part in (
			"launch-ui",
			"components/sections/hero/default.tsx",
			"b0d4d5bce9",
			"MIT licence",
			"Copyright (c) 2024 Mikolaj Dobrucki",
		):
			self.assertIn(part, self.block["notes"])

	def test_every_section_is_a_kind_the_plan_knows(self):
		from builder.site_ai.nora.site_plan import SECTION_KINDS

		for section, kind in importer.LAUNCH_UI_KINDS.items():
			self.assertIn(kind, SECTION_KINDS, section)

	def test_the_folder_of_rendered_sections_is_read_and_what_is_missing_is_said(self):
		import tempfile

		with tempfile.TemporaryDirectory() as folder:
			with open(f"{folder}/hero.html", "w", encoding="utf-8") as f:
				f.write(LAUNCH_HERO)
			done = importer.import_launch_ui(folder, ["hero", "faq"], push=False)
		self.assertEqual({"hero": "hero.lu-hero"}, done["blocks"])
		self.assertEqual(["faq"], list(done["refused"]))
		self.assertIn("not rendered", done["refused"]["faq"])
		self.assertEqual({}, done["sent"])


class TestFlowbite(unittest.TestCase):
	def test_the_examples_of_a_page_are_read_with_their_titles_and_no_shortcode(self):
		examples = importer.flowbite_examples(FLOWBITE_PAGE)
		self.assertEqual(["Default jumbotron", "Another one"], [t for t, _m in examples])
		self.assertNotIn("{{", examples[0][1])
		self.assertIn("A headline for a start", examples[0][1])
		self.assertEqual([], importer.flowbite_examples("No example here."))

	def test_an_example_becomes_a_block_with_its_source_in_the_notes(self):
		title, markup = importer.flowbite_examples(FLOWBITE_PAGE)[0]
		block = importer.import_flowbite_markup("jumbotron", 1, title, markup)
		self.assertEqual("hero.fb-jumbotron-1", block["id"])
		self.assertEqual("Hero 1 (Flowbite)", block["title"])
		self.assertEqual(["hero"], block["kinds"])
		for part in (
			"Flowbite",
			"content/components/jumbotron.md",
			"Default jumbotron",
			"MIT licence",
			"Copyright (c) Bergside Inc.",
		):
			self.assertIn(part, block["notes"])
		self.assertEqual("{{ground.accent}}", find(block["tree"], el="a")[0]["style"]["color"])

	def test_every_component_is_a_kind_the_plan_knows(self):
		from builder.site_ai.nora.site_plan import SECTION_KINDS

		for component, kind in importer.FLOWBITE_KINDS.items():
			self.assertIn(kind, SECTION_KINDS, component)

	def test_an_accordion_drawn_with_a_script_becomes_the_questions_that_fold(self):
		block = make(page(ACCORDION), kind="faq", name="faq.fb-test-1")
		faq = find(block["tree"], classes=["u-faq"])
		self.assertEqual(1, len(faq))
		items = faq[0]["c"]
		self.assertEqual(["details", "details"], [i["el"] for i in items])
		for item in items:
			self.assertEqual(["summary", "p"], [c["el"] for c in item["c"]])  # one answer paragraph
		self.assertNotIn("data-accordion", repr(block["tree"]))
		self.assertNotIn("A second paragraph", repr(block["tree"]))

	def test_a_background_photograph_is_refused_on_the_shell_too(self):
		markup = page(
			'<section class="bg-center bg-[url(\'https://example.com/a.jpg\')] bg-dark"><div class="px-4"><h1 class="text-white">Words</h1></div></section>'
		)
		with self.assertRaises(importer.Refused) as caught:
			make(markup, kind="hero", name="hero.fb-test-2")
		self.assertIn("background", str(caught.exception))

	def test_the_import_reports_what_it_made_and_what_it_refused(self):
		pages = {
			"jumbotron": FLOWBITE_PAGE
			+ """
## A form

{{< example >}}
<section><form><input type="text"></form></section>
{{< /example >}}
"""
		}
		original = importer.fetch_flowbite
		try:
			importer.fetch_flowbite = lambda component: pages[component]
			done = importer.import_flowbite(["jumbotron"], push=False)
		finally:
			importer.fetch_flowbite = original
		self.assertEqual(
			{"jumbotron/1": "hero.fb-jumbotron-1", "jumbotron/2": "hero.fb-jumbotron-2"}, done["blocks"]
		)
		self.assertEqual(["jumbotron/3"], list(done["refused"]))
		self.assertIn("A form: a form is a live component", done["refused"]["jumbotron/3"])
		self.assertEqual({}, done["sent"])


class TestTheChromeAndTheLoneCard(unittest.TestCase):
	def test_the_navigation_a_component_page_draws_above_its_section_is_left_out(self):
		block = make(
			page(
				'<section class="bg-white"><nav class="container p-6 mx-auto flex"><a href="#" class="text-gray-700">Home</a><a href="#" class="text-gray-700">Pricing</a></nav>'
				'<header class="px-4"><nav><a href="#">Docs</a></nav></header>'
				'<div class="container mx-auto px-6 py-16 text-center"><h1 class="text-4xl font-bold text-gray-800">A headline for the page</h1><p class="mt-4 text-gray-500">A line that says what it is for.</p></div></section>'
			),
			kind="hero",
			name="hero.mk-test-1",
		)
		blob = repr(block["tree"])
		self.assertNotIn("Home", blob)
		self.assertEqual(
			["h1", "p"], [n["el"] for n in walk(block["tree"]) if n["el"] in {"h1", "p", "nav", "a"}]
		)

	def test_one_card_is_not_a_row_of_cards(self):
		one = page(
			'<div class="mx-auto max-w-sm"><article class="rounded-lg border border-gray-200 p-6"><h3 class="text-lg font-bold text-gray-900">A title</h3><p class="text-gray-700">Some words of a card.</p></article></div>'
		)
		with self.assertRaises(importer.Refused) as caught:
			make(one, kind="cards", name="cards.hu-test-1")
		self.assertIn("one card", str(caught.exception))
		self.assertEqual(
			1, len(find(make(one, kind="text", name="text.hu-test-1")["tree"], name="card"))
		)  # as a text section it is allowed

	def test_a_row_of_cards_is_one(self):
		three = page(
			'<div class="grid grid-cols-3 gap-4">'
			+ '<article class="rounded-lg border border-gray-200 p-6"><h3 class="text-lg font-bold text-gray-900">A title</h3><p class="text-gray-700">Some words of a card.</p></article>'
			* 3
			+ "</div>"
		)
		self.assertEqual(3, len(find(make(three, kind="cards", name="cards.hu-test-2")["tree"], name="card")))


class TestMerakiUi(unittest.TestCase):
	def test_the_slug_the_id_and_the_title(self):
		self.assertEqual("center-content-with-trusted-by", importer.meraki_slug("CenterContentWithTrustedBy"))
		self.assertEqual("e-commerce", importer.meraki_slug("E-commerce"))
		self.assertEqual("hero.mk-heros-side-image", importer.meraki_id("heros", "SideImage", "hero"))
		self.assertRegex(importer.meraki_id("faq", "CollapseWithSideLinks", "faq"), block_format.BLOCK_ID)

	def test_every_category_has_files_and_is_a_kind_the_plan_knows(self):
		from builder.site_ai.nora.site_plan import SECTION_KINDS

		self.assertEqual(set(importer.MERAKI_KINDS), set(importer.MERAKI_FILES))
		for category, kind in importer.MERAKI_KINDS.items():
			self.assertIn(kind, SECTION_KINDS, category)
			self.assertTrue(importer.MERAKI_FILES[category])

	def test_a_component_becomes_a_block_with_its_source_in_the_notes(self):
		markup = page(
			'<section class="bg-white dark:bg-gray-900"><div class="container px-6 py-10 mx-auto text-center"><h1 class="text-3xl font-semibold text-gray-800 dark:text-white">A title that says it</h1>'
			'<p class="max-w-lg mx-auto mt-6 text-gray-500 dark:text-gray-400">A short text under it.</p><a href="#" class="px-5 py-2 mt-6 text-sm text-white bg-blue-600 rounded-lg">Start</a></div></section>'
		)
		block = importer.import_meraki_markup("heros", "CenterContent", markup)
		self.assertEqual("hero.mk-heros-center-content", block["id"])
		self.assertEqual("Hero, center content (Meraki UI)", block["title"])
		for part in (
			"Meraki UI",
			"components/heros/CenterContent.html",
			"fe0472efe9",
			"MIT licence",
			"Copyright (c) 2021 Khatab Wedaa",
		):
			self.assertIn(part, block["notes"])
		self.assertEqual(["u-btn", "u-btn--primary"], find(block["tree"], el="a")[0]["classes"])


class TestTheLineThePlanReads(unittest.TestCase):
	"""The plan picks a block by one line: a block that says `a band` is a block it never picks."""

	def look(self, markup, kind, name):
		return make(markup, kind=kind, name=name)["look"]

	def test_a_hero_says_its_alignment_its_text_its_buttons_and_what_it_is_for(self):
		look = make(DARK_CTA, kind="hero", name="hero.mk-test-1")["look"]
		self.assertEqual(
			"a centred heading and a short text, with a button and a quieter one in outline; on a deep band; for the first screen of a page.",
			look,
		)

	def test_folding_questions_say_how_many_and_that_they_fold(self):
		look = make(FAQ, kind="faq", name="faq.hu-test-9")["look"]
		self.assertIn("2 folding questions in one column", look)
		self.assertTrue(look.endswith("for practical questions, a reference page."))

	def test_a_grid_says_its_items_its_columns_and_what_each_holds(self):
		look = self.look(
			page(
				'<div class="mx-auto max-w-7xl px-4"><h2 class="text-3xl font-bold text-gray-900 text-center">Our offers</h2><div class="grid grid-cols-3 gap-4">'
				+ '<div class="rounded-lg border border-gray-200 p-6"><h3 class="text-lg font-bold text-gray-900">A title</h3><p class="text-gray-700">Some words that say what the offer is.</p></div>'
				* 3
				+ "</div></div>"
			),
			"feature-grid",
			"features.hu-test-9",
		)
		self.assertIn("3 cards in 3 columns, each holding a title and a text", look)
		self.assertIn("a left-aligned heading" if "left" in look else "a centred heading", look)

	def test_round_portraits_are_named_and_their_photographs_are_not_counted_twice(self):
		look = make(TestPicturesAndRepeatedGroups.TEAM, kind="team", name="team.hu-test-9")["look"]
		self.assertIn("2 round portraits", look)
		self.assertNotIn("photographs", look)
		self.assertIn("for the people behind the business", look)

	def test_nothing_of_the_source_is_in_the_line(self):
		look = make(FEATURES, kind="feature-grid", name="features.hu-test-9")["look"]
		for word in ("Features", "growth", "performance", "gray", "indigo"):
			self.assertNotIn(word, look)
		self.assertLess(len(look), 400)


class TestAFaqHoldsItsAnswers(unittest.TestCase):
	def test_questions_without_answers_are_not_a_faq(self):
		bare = page(
			'<div class="container mx-auto px-6 py-10"><h1 class="text-2xl font-semibold text-gray-800">Questions</h1>'
			+ '<div><button class="flex"><h1 class="text-xl text-gray-700">A question one asks</h1></button></div>'
			* 3
			+ "</div>"
		)
		with self.assertRaises(importer.Refused) as caught:
			make(bare, kind="faq", name="faq.mk-test-1")
		self.assertIn("no answers", str(caught.exception))

	def test_a_grid_of_titles_and_texts_is_one(self):
		grid = page(
			'<div class="container mx-auto px-6"><div class="grid grid-cols-2 gap-8">'
			+ '<div><h2 class="text-xl font-semibold text-gray-800">A question one asks</h2><p class="text-gray-500">The answer, in a few words.</p></div>'
			* 2
			+ "</div></div>"
		)
		self.assertIn("2 items in 2 columns", make(grid, kind="faq", name="faq.mk-test-2")["look"])

	def test_a_testimonial_with_a_round_photograph_is_not_a_team(self):
		look = make(TestPicturesAndRepeatedGroups.TEAM, kind="testimonials", name="testimonials.hu-test-9")[
			"look"
		]
		self.assertIn("each holding a round photograph", look)
		self.assertNotIn("round portraits", look)


class TestPushingToTheHub(unittest.TestCase):
	def test_a_hub_that_says_it_is_asked_too_often_is_asked_again_after_a_wait(self):
		answers = iter(
			[
				"not sent: the hub answered 429",
				"not sent: the hub answered 429",
				"draft cta.hu-test v1",
				"draft cta.hu-two v1",
			]
		)
		waits = []
		import time

		real_push, real_sleep = importer.capture.push_block, time.sleep
		try:
			importer.capture.push_block = lambda block: next(answers)
			time.sleep = lambda seconds: waits.append(seconds)
			sent = importer.push_all({"a": {"id": "cta.hu-test"}, "b": {"id": "cta.hu-two"}})
		finally:
			importer.capture.push_block, time.sleep = real_push, real_sleep
		self.assertEqual({"a": "draft cta.hu-test v1", "b": "draft cta.hu-two v1"}, sent)
		self.assertEqual([importer.PUSH_WAIT, importer.PUSH_WAIT], waits)

	def test_it_gives_up_after_its_tries_and_says_so(self):
		import time

		real_push, real_sleep = importer.capture.push_block, time.sleep
		calls = []
		try:
			importer.capture.push_block = lambda block: calls.append(1) or "not sent: the hub answered 429"
			time.sleep = lambda seconds: None
			sent = importer.push_all({"a": {"id": "cta.hu-test"}})
		finally:
			importer.capture.push_block, time.sleep = real_push, real_sleep
		self.assertEqual(importer.PUSH_TRIES, len(calls))
		self.assertIn("429", sent["a"])


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
			# four components that differ (the length of the invitation of each is not the same)
			importer.fetch_hyperui = lambda category, number: DARK_CTA.replace(
				"Get started", "Get started " + "now " * number
			)
			importer.capture.push_block = lambda block: sent.append(block["id"]) or "sent"
			done = importer.import_hyperui(["ctas"], push=False)
		finally:
			importer.fetch_hyperui, importer.capture.push_block = originals
		self.assertEqual(sent, [])
		self.assertEqual(done["sent"], {})
		self.assertEqual(len(done["blocks"]), 4)
		self.assertTrue(re.fullmatch(r"cta\.hu-ctas-\d", done["blocks"]["ctas/1"]))

	def test_variants_that_come_out_the_same_are_one_block(self):
		originals = importer.fetch_hyperui
		try:
			importer.fetch_hyperui = lambda category, number: DARK_CTA
			done = importer.import_hyperui(["ctas"], push=False)
		finally:
			importer.fetch_hyperui = originals
		self.assertEqual(["ctas/1"], list(done["blocks"]))
		self.assertEqual(["ctas/2", "ctas/3", "ctas/4"], sorted(done["refused"]))
		self.assertTrue(all("the same block as ctas/1" in why for why in done["refused"].values()))


if __name__ == "__main__":
	unittest.main()
