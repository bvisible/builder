# //// Neoffice — added file (no upstream equivalent): tests of the site playbook helpers.
"""The pure parts of builder/site_ai/nora: page normalisation, token prefixes, the
layout choice, the page brief, the text-card parser and the capability rules. No
model is called; frappe is only needed for the capability and managed-model
helpers (site_config)."""

import unittest
from unittest.mock import patch

import frappe

from builder.site_ai.capabilities import MANAGED_DISABLED_TOOLS, disabled_tools
from builder.site_ai.nora.adopt import rewrite_blocks
from builder.site_ai.nora.cards import parse_card
from builder.site_ai.nora.contrast import NAMED, accent_shade, contrast, palette_roles, parse_color, repair_contrast
from builder.site_ai.nora.site_builder import (
	_color,
	available_includes,
	choose_layout_system,
	normalise_pages,
	page_brief_text,
	placeholder_photos,
	token_prefix,
)


class FakeBrief:
	design_concept = "Editorial workshop"
	signature_element = "Oversized numerals"
	site_tone = "professional"
	hero_style = "split"
	heading_font = "Raleway"
	body_font = "Source Sans 3"
	border_radius_style = "subtle"
	cta_shape = "Rounded"
	button_hover = "Darken"
	motion_style = "Calm"


class TestPages(unittest.TestCase):
	def test_known_titles_get_their_route_and_type(self):
		pages = normalise_pages(["Accueil", "À propos", "Prestations", "Contact", "FAQ", "Boutique"], "vitrine")
		self.assertEqual([p["route"] for p in pages], ["home", "about", "services", "contact", "faq", "shop"])
		self.assertEqual(pages[0]["type"], "accueil")
		self.assertEqual(pages[2]["type"], "services")

	def test_a_known_page_keeps_its_canonical_route_over_the_models(self):
		pages = normalise_pages([{"title": "Accueil", "route": "accueil"}, {"title": "Contact", "route": "nous-contacter"}, {"title": "Nos ateliers", "route": "ateliers"}], "vitrine")
		self.assertEqual([p["route"] for p in pages], ["home", "contact", "ateliers"])

	def test_home_comes_first_whatever_the_order(self):
		pages = normalise_pages(["Contact", "Accueil"], "vitrine")
		self.assertEqual(pages[0]["route"], "home")

	def test_unknown_title_is_slugged_and_generic(self):
		(page,) = normalise_pages([{"title": "Nos ateliers créatifs"}], "vitrine")
		self.assertEqual(page["route"], "nos-ateliers-creatifs")
		self.assertEqual(page["type"], "generic")

	def test_duplicate_routes_collapse(self):
		pages = normalise_pages(["Accueil", "Home", "Contact"], "vitrine")
		self.assertEqual(len(pages), 2)

	def test_empty_list_falls_back_to_the_site_type_defaults(self):
		pages = normalise_pages([], "vitrine")
		self.assertTrue(pages and pages[0]["route"] == "home")


class TestTokens(unittest.TestCase):
	def test_prefix_is_the_initials_or_the_first_word(self):
		self.assertEqual(token_prefix("The League Agency"), "tla")
		self.assertEqual(token_prefix("The 5 Burrows"), "t5b")
		self.assertEqual(token_prefix("Fromagerie"), "fromager")

	def test_colour_values_are_literal_or_the_fallback(self):
		self.assertEqual(_color("var(--muted-color)", "#123456", fallback="#000"), "#123456")
		self.assertEqual(_color("", None, fallback="#1a1a1a"), "#1a1a1a")
		self.assertEqual(_color("rgba(0,0,0,0.5)", fallback="#000"), "rgba(0,0,0,0.5)")


class TestLayout(unittest.TestCase):
	def test_direction_words_pick_the_system(self):
		self.assertEqual(choose_layout_system("Poster affirmé", FakeBrief()), "poster-brutalist")
		self.assertEqual(choose_layout_system("grille éditoriale", FakeBrief()), "editorial-grid")

	def test_tone_decides_without_a_direction(self):
		self.assertEqual(choose_layout_system("", FakeBrief()), "editorial-grid")


class TestPageBrief(unittest.TestCase):
	def test_brief_carries_handles_photos_and_rules(self):
		site = {"site_name": "Atelier Lumen", "activity": "Menuiserie", "differentiators": "Bois suisse"}
		handles = {k: f"var(--al-{k})" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		page = {"title": "Contact", "route": "contact", "type": "contact"}
		photos = placeholder_photos(page, "Menuiserie sur mesure")
		palette = {"al-primary": "#3B2B20", "al-secondary": "#B08548", "al-background": "#FBF7F2", "al-text": "#1a1a1a"}
		text = page_brief_text(site, FakeBrief(), page, handles, "", "editorial-grid", "French", photos, ("Contactez-nous", "/contact"), palette=palette)
		self.assertIn("var(--al-primary)", text)
		self.assertIn("CONTRAST:", text)
		self.assertIn("var(--al-background) = #FBF7F2 (LIGHT", text)
		self.assertIn("var(--al-primary) = #3B2B20 (DARK", text)
		self.assertIn("INTERIOR page", text)
		self.assertIn("placehold.co", text)
		self.assertIn("no header, navigation or footer", text)
		self.assertIn("u-btn", text)
		self.assertIn("'Atelier Lumen'", text)

	def test_the_contact_page_learns_its_includes(self):
		site = {"site_name": "X", "activity": "Y"}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		text = page_brief_text(site, FakeBrief(), {"title": "Contact", "route": "contact", "type": "contact"}, handles, "", "bento", "French", [], ("CTA", "/"))
		self.assertIn("INCLUDES", text)
		self.assertIn("builder/templates/includes/contact_form.html", text)
		self.assertIn("`text` of its own plain div block", text)
		self.assertTrue(all(tag.startswith("{%") for tag, _ in available_includes("contact")))
		self.assertEqual(available_includes("generic"), [])
		# the contact form is an order, not an option: the model wrote its own inert <form>
		self.assertIn("INCLUDES REQUIRED", text)
		self.assertIn("do NOT write a <form> of your own", text)
		about = page_brief_text(site, FakeBrief(), {"title": "À propos", "route": "about", "type": "about"}, handles, "", "bento", "French", [], ("CTA", "/"))
		self.assertNotIn("INCLUDES REQUIRED", about)

	def test_known_pages_keep_their_canonical_type(self):
		pages = normalise_pages([{"title": "Contact", "type": "form"}, {"title": "Accueil", "route": "accueil", "type": "landing"}], "vitrine")
		self.assertEqual([(p["route"], p["type"]) for p in pages], [("home", "accueil"), ("contact", "contact")])

	def test_home_page_opens_with_the_hero(self):
		site = {"site_name": "X", "activity": "Y"}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		text = page_brief_text(site, FakeBrief(), {"title": "Accueil", "route": "home", "type": "accueil"}, handles, "", "bento", "French", [], ("CTA", "/"))
		self.assertIn("HOME page", text)


class TestTextCards(unittest.TestCase):
	def test_a_one_line_multi_choices_card(self):
		spec = parse_card("Quelles pages ? [choices multi: Accueil, Contact, FAQ] [buttons: Continue]")
		self.assertEqual(spec["text"], "Quelles pages ?")
		choices = spec["ui"][0]
		self.assertEqual(choices["kind"], "choices")
		self.assertTrue(choices["multi"])
		self.assertEqual([o["label"] for o in choices["options"]], ["Accueil", "Contact", "FAQ"])
		self.assertEqual(spec["ui"][-1]["kind"], "actions")

	def test_palettes_keep_their_colours_and_buttons_split(self):
		text = (
			"Couleurs.\n[choices: \n- Noyer: chaleureux\n  [colors: #3B2B20, #B08548]\n- Ardoise: sobre\n  [colors: #31413A, #A98A5B]]\n"
			"[color_input: Ou vos couleurs\n- Primaire: dominante, #3B2B20\n- Secondaire: accents, #B08548]\n[buttons: Créer le site / Modifier]"
		)
		spec = parse_card(text)
		self.assertEqual(spec["ui"][0]["options"][0]["colors"], ["#3B2B20", "#B08548"])
		self.assertEqual(spec["ui"][1]["kind"], "color_input")
		self.assertEqual([b["label"] for b in spec["ui"][-1]["buttons"]], ["Créer le site", "Modifier"])

	def test_a_recap_with_heading_and_list(self):
		spec = parse_card("Récap :\n[heading: Atelier]\n[list:\n- Pages : Accueil\n- Couleurs : #000]\n[buttons: Créer le site, Modifier]")
		self.assertEqual([el["kind"] for el in spec["ui"]], ["heading", "list", "actions"])

	def test_an_options_line_is_a_list_not_one_option(self):
		spec = parse_card("Which site?\n[choices: Site\n- options: Site principal, Nora Test, Nora Test 3]\n[buttons: Build the site]")
		self.assertEqual([o["label"] for o in spec["ui"][0]["options"]], ["Site principal", "Nora Test", "Nora Test 3"])
		self.assertEqual(spec["ui"][0].get("label"), "Site")
		spec = parse_card("Pages?\n[choices multi: Pages\nAccueil, Contact, FAQ]")
		self.assertEqual([o["label"] for o in spec["ui"][0]["options"]], ["Accueil", "Contact", "FAQ"])

	def test_a_head_written_as_tool_arguments_sets_label_and_multi(self):
		spec = parse_card("Pages ?\n[choices: label: Pages; multi: true\n- Accueil — la vitrine\n- Contact — le formulaire]\n[buttons: Continuer]")
		group = spec["ui"][0]
		self.assertEqual(group.get("label"), "Pages")
		self.assertTrue(group.get("multi"))
		self.assertEqual([o["label"] for o in group["options"]], ["Accueil", "Contact"])
		spec = parse_card("Couleurs\n[choices: Palette, single-select\n- Lilas doux: violet #9B7CB6\n- Jardin: rose #E8B4B8]")
		self.assertEqual(spec["ui"][0].get("label"), "Palette")
		self.assertFalse(spec["ui"][0].get("multi"))

	def test_plain_prose_is_not_a_card(self):
		self.assertIsNone(parse_card("Le site est créé. Il comprend cinq pages."))
		self.assertIsNone(parse_card(""))

	def test_a_card_without_any_control_is_not_materialised(self):
		self.assertIsNone(parse_card("Voici :\n[heading: Titre]\n[list:\n- a]"))


class TestCapabilities(unittest.TestCase):
	def test_managed_instance_drops_the_schema_tools(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": None}):
			self.assertEqual(disabled_tools(), list(MANAGED_DISABLED_TOOLS))

	def test_self_hosted_keeps_everything(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 0, "nora_disabled_tools": None}):
			self.assertEqual(disabled_tools(), [])

	def test_site_config_overrides_the_list(self):
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": "run_python, seed_sample_data"}):
			self.assertEqual(disabled_tools(), ["run_python", "seed_sample_data"])
		with patch.dict(frappe.local.conf, {"ai_managed": 1, "nora_disabled_tools": []}):
			self.assertEqual(disabled_tools(), [])


PALETTE = {"nt2-primary": "#C68E3F", "nt2-secondary": "#F7F0E3", "nt2-background": "#F7F0E3", "nt2-text": "#1a1a1a"}


class TestContrast(unittest.TestCase):
	def test_colours_parse_including_handles_and_alpha(self):
		self.assertEqual(parse_color("var(--nt2-text)", PALETTE), (26.0, 26.0, 26.0, 1.0))
		self.assertEqual(parse_color("#fff", PALETTE), (255.0, 255.0, 255.0, 1.0))
		self.assertEqual(parse_color("rgba(255,255,255,0.82)", PALETTE)[3], 0.82)
		self.assertEqual(parse_color("var(--unknown, #000)", PALETTE), (0.0, 0.0, 0.0, 1.0))
		self.assertIsNone(parse_color("linear-gradient(#000, #fff)", PALETTE))
		self.assertIsNone(parse_color("url(/files/x.png)", PALETTE))

	def test_the_cream_band_with_white_copy_gets_the_text_handle(self):
		"""The CTA band of neoffice-maintenance #281, as the model wrote it on osiris."""
		band = {"blockName": "cta-section", "baseStyles": {"backgroundColor": "var(--nt2-secondary)"}, "children": [
			{"element": "div", "baseStyles": {"color": "var(--nt2-primary)"}, "innerHTML": "<svg viewBox='0 0 1 1'></svg>"},
			{"element": "h2", "baseStyles": {"color": "#ffffff"}, "innerHTML": "Prêt à goûter le levain ?"},
			{"element": "p", "baseStyles": {"color": "rgba(255,255,255,0.82)"}, "innerHTML": "Passez commande"},
			{"element": "a", "classes": ["u-btn", "u-btn--primary"], "innerHTML": "Contactez-nous"},
		]}
		fixes = repair_contrast([band], PALETTE)
		self.assertEqual(len(fixes), 2)
		self.assertEqual(band["children"][1]["baseStyles"]["color"], "var(--nt2-text)")
		self.assertEqual(band["children"][2]["baseStyles"]["color"], "var(--nt2-text)")
		# the icon keeps its accent colour: no text under it
		self.assertEqual(band["children"][0]["baseStyles"]["color"], "var(--nt2-primary)")
		# the button's colours come from its class, nothing was written on it
		self.assertNotIn("baseStyles", band["children"][3])

	def test_a_dark_band_with_inherited_dark_text_gets_the_light_handle(self):
		dark = {"blockName": "dark-band", "baseStyles": {"backgroundColor": "#1a1a1a"}, "children": [{"element": "h2", "innerHTML": "Titre"}]}
		fixes = repair_contrast([dark], PALETTE)
		self.assertEqual(len(fixes), 1)
		self.assertEqual(dark["baseStyles"]["color"], "var(--nt2-background)")

	def test_photos_and_gradients_are_left_alone(self):
		over = {"classes": ["u-over-image"], "children": [{"element": "h2", "baseStyles": {"color": "#fff"}, "innerHTML": "Sur photo"}]}
		grad = {"baseStyles": {"background": "linear-gradient(#000, #fff)"}, "children": [{"element": "p", "baseStyles": {"color": "#fff"}, "innerHTML": "x"}]}
		img = {"baseStyles": {"background": "url(/files/hero.png) center/cover"}, "children": [{"element": "p", "baseStyles": {"color": "#fff"}, "innerHTML": "x"}]}
		self.assertEqual(repair_contrast([over, grad, img], PALETTE), [])
		self.assertEqual(over["children"][0]["baseStyles"]["color"], "#fff")

	def test_readable_text_is_untouched(self):
		ok = {"baseStyles": {"backgroundColor": "var(--nt2-primary)"}, "children": [{"element": "h2", "baseStyles": {"color": "var(--nt2-text)"}, "innerHTML": "Titre"}]}
		self.assertEqual(repair_contrast([ok], PALETTE), [])

	def test_palette_roles_read_the_luminance(self):
		roles = palette_roles(PALETTE)
		self.assertIn("var(--nt2-secondary) = #F7F0E3 (LIGHT", roles)
		self.assertIn("var(--nt2-text) = #1a1a1a (DARK", roles)
		self.assertIn("var(--nt2-primary) = #C68E3F (MID", roles)
		self.assertLess(contrast(parse_color("#C68E3F", PALETTE), NAMED["white"]), 3.0)

	def test_an_accent_kicker_is_deepened_not_flattened(self):
		kicker = {"element": "span", "blockName": "kicker", "baseStyles": {"color": "var(--nt2-primary)"}, "innerHTML": "BOULANGERIE ARTISANALE"}
		band = {"baseStyles": {"backgroundColor": "var(--nt2-background)"}, "children": [kicker]}
		fixes = repair_contrast([band], PALETTE)
		self.assertEqual(len(fixes), 1)
		self.assertTrue(kicker["baseStyles"]["color"].startswith("color-mix(in srgb, var(--nt2-primary) "), kicker["baseStyles"]["color"])
		self.assertIn("black)", kicker["baseStyles"]["color"])
		shade = accent_shade("var(--nt2-primary)", parse_color("#C68E3F", PALETTE), parse_color("#F7F0E3", PALETTE))
		self.assertIsNotNone(shade)
		self.assertGreaterEqual(contrast(shade[1], parse_color("#F7F0E3", PALETTE)), 3.0)

	def test_white_on_cream_is_not_an_accent_case(self):
		h2 = {"element": "h2", "baseStyles": {"color": "#ffffff"}, "innerHTML": "Titre"}
		band = {"baseStyles": {"backgroundColor": "var(--nt2-secondary)"}, "children": [h2]}
		repair_contrast([band], PALETTE)
		self.assertEqual(h2["baseStyles"]["color"], "var(--nt2-text)")

	def test_copy_over_a_positioned_photo_is_left_alone(self):
		"""The proof section of Boulangerie Solstice: an absolute cover image, a gradient
		overlay, then white numbers. The section itself inherits the cream page."""
		numbers = {"element": "h3", "baseStyles": {"color": "#ffffff"}, "innerHTML": "12h"}
		section = {"blockName": "proof-section", "baseStyles": {"position": "relative"}, "children": [
			{"element": "img", "classes": ["u-media"], "baseStyles": {"position": "absolute", "inset": "0", "objectFit": "cover"}},
			{"element": "div", "baseStyles": {"position": "absolute", "inset": "0", "backgroundImage": "linear-gradient(180deg, rgba(15,15,15,0.45), rgba(15,15,15,0.65))"}},
			{"element": "div", "baseStyles": {"position": "relative"}, "children": [numbers]},
		]}
		self.assertEqual(repair_contrast([section], PALETTE), [])
		self.assertEqual(numbers["baseStyles"]["color"], "#ffffff")


class TestBriefHeroColours(unittest.TestCase):
	def test_missing_hero_colours_follow_the_palette(self):
		from builder.site_ai.schemas.design_brief import DesignBrief

		dark = DesignBrief(primary_color="#1a1a1a", secondary_color="#B08548")
		self.assertEqual(dark.hero_background, "#1a1a1a")
		self.assertEqual(dark.hero_text_color, "#ffffff")
		light = DesignBrief(primary_color="#F7F0E3", secondary_color="#C68E3F", body_color="#222222")
		self.assertEqual(light.hero_background, "#F7F0E3")
		self.assertEqual(light.hero_text_color, "#222222")
		kept = DesignBrief(primary_color="#1a1a1a", hero_background="#ffffff", hero_text_color="#333333")
		self.assertEqual((kept.hero_background, kept.hero_text_color), ("#ffffff", "#333333"))

	def test_fonts_named_in_the_concept_replace_a_default(self):
		from builder.site_ai.schemas.design_brief import DesignBrief

		b = DesignBrief(design_concept="Cormorant Garamond supplies the headline voice, while Manrope keeps the body crisp.")
		self.assertEqual((b.heading_font, b.body_font), ("Cormorant Garamond", "Manrope"))
		chosen = DesignBrief(design_concept="Cormorant Garamond for headlines", heading_font="Playfair Display", body_font="Lora")
		self.assertEqual((chosen.heading_font, chosen.body_font), ("Playfair Display", "Lora"))
		plain = DesignBrief(design_concept="A warm, quiet workshop.")
		self.assertEqual((plain.heading_font, plain.body_font), ("Inter", "Inter"))


class TestAdoption(unittest.TestCase):
	PALETTE = {"primary": "#1c3d52", "secondary": "#b0843f", "background": "#ffffff", "text": "#1a1a1a"}
	FONTS = {"font-heading": "Cormorant Garamond", "font-body": "DM Sans"}

	def test_palette_literals_become_handles_with_their_semantics(self):
		blocks = [{"baseStyles": {"backgroundColor": "#1C3D52", "color": "#ffffff", "border": "1px solid #b0843f", "--primary-color": "#1c3d52"},
			"mobileStyles": {"color": "#1a1a1a", "backgroundColor": "#fff"},
			"children": [{"baseStyles": {"color": "#b0843f80", "backgroundImage": "linear-gradient(#1c3d52, #b0843f)"}}]}]
		changed = rewrite_blocks(blocks, "gf", self.PALETTE, self.FONTS)
		self.assertEqual(changed, 7)
		base = blocks[0]["baseStyles"]
		self.assertEqual(base["backgroundColor"], "var(--gf-primary)")
		self.assertEqual(base["color"], "#ffffff")  # white copy on a dark band is not "the background"
		self.assertEqual(base["border"], "1px solid var(--gf-secondary)")
		self.assertEqual(base["--primary-color"], "var(--gf-primary)")
		self.assertEqual(blocks[0]["mobileStyles"], {"color": "var(--gf-text)", "backgroundColor": "var(--gf-background)"})
		child = blocks[0]["children"][0]["baseStyles"]
		self.assertEqual(child["color"], "#b0843f80")  # an alpha shade is not the token
		self.assertEqual(child["backgroundImage"], "linear-gradient(var(--gf-primary), var(--gf-secondary))")

	def test_fonts_become_handles_and_keep_their_fallbacks(self):
		blocks = [{"baseStyles": {"fontFamily": "'DM Sans', sans-serif"}, "children": [{"baseStyles": {"fontFamily": "Cormorant Garamond"}}, {"baseStyles": {"fontFamily": "Cormorant, serif"}}]}]
		self.assertEqual(rewrite_blocks(blocks, "gf", self.PALETTE, self.FONTS), 2)
		self.assertEqual(blocks[0]["baseStyles"]["fontFamily"], "var(--gf-font-body), sans-serif")
		self.assertEqual(blocks[0]["children"][0]["baseStyles"]["fontFamily"], "var(--gf-font-heading)")
		self.assertEqual(blocks[0]["children"][1]["baseStyles"]["fontFamily"], "Cormorant, serif")

	def test_a_rewritten_page_is_stable(self):
		blocks = [{"baseStyles": {"backgroundColor": "#1c3d52", "fontFamily": "DM Sans"}}]
		rewrite_blocks(blocks, "gf", self.PALETTE, self.FONTS)
		self.assertEqual(rewrite_blocks(blocks, "gf", self.PALETTE, self.FONTS), 0)


class TestPageStream(unittest.TestCase):
	"""Liveness of a streamed page: a thinking model's reasoning counts as output."""

	def test_delta_parts_reads_reasoning_before_content(self):
		from types import SimpleNamespace as NS

		from builder.site_ai.nora.site_builder import _delta_parts

		thinking = NS(choices=[NS(delta=NS(content=None, reasoning_content="let me think"))])
		content = NS(choices=[NS(delta=NS(content="el: div", reasoning_content=None))])
		provider = NS(choices=[NS(delta=NS(content=None, provider_specific_fields={"reasoning_content": "hmm"}))])
		empty = NS(choices=[])
		self.assertEqual(_delta_parts(thinking), ("", "let me think"))
		self.assertEqual(_delta_parts(content), ("el: div", ""))
		self.assertEqual(_delta_parts(provider), ("", "hmm"))
		self.assertEqual(_delta_parts(empty), ("", ""))


class TestAccent(unittest.TestCase):
	"""The page's own accent colour joins the design system (accent.py)."""

	palette = {"nt2-primary": "#1E3A5F", "nt2-secondary": "#C9D2DC", "nt2-background": "#ffffff", "nt2-text": "#1a1a1a"}

	def blocks(self):
		return [{"element": "section", "baseStyles": {"backgroundColor": "#1E3A5F", "borderTop": "3px solid #F59E0B"}, "children": [
			{"element": "span", "baseStyles": {"color": "#f59e0b"}, "mobileStyles": {"color": "#F59E0B"}},
			{"element": "p", "baseStyles": {"color": "#777777", "background": "linear-gradient(#f59e0b, #ffffff)", "boxShadow": "0 0 0 #f59e0b33"}},
		]}]

	def test_dominant_accent_ignores_the_palette_and_the_neutrals(self):
		from builder.site_ai.nora.accent import dominant_accent, foreign_colours

		counts = foreign_colours(self.blocks(), self.palette)
		self.assertEqual(dict(counts), {"#f59e0b": 4})
		self.assertEqual(dominant_accent(self.blocks(), self.palette), "#f59e0b")
		self.assertIsNone(dominant_accent([{"baseStyles": {"color": "#f59e0b"}}], self.palette))

	def test_rewrite_hex_folds_every_use_into_the_token_but_the_alpha_form(self):
		from builder.site_ai.nora.accent import rewrite_hex

		blocks = self.blocks()
		edits = rewrite_hex(blocks, {"#f59e0b": "var(--nt2-accent)"})
		self.assertEqual(edits, 4)
		self.assertEqual(blocks[0]["baseStyles"]["borderTop"], "3px solid var(--nt2-accent)")
		span, p = blocks[0]["children"]
		self.assertEqual(span["baseStyles"]["color"], "var(--nt2-accent)")
		self.assertEqual(span["mobileStyles"]["color"], "var(--nt2-accent)")
		self.assertEqual(p["baseStyles"]["background"], "linear-gradient(var(--nt2-accent), #ffffff)")
		self.assertEqual(p["baseStyles"]["boxShadow"], "0 0 0 #f59e0b33")
		self.assertEqual(blocks[0]["baseStyles"]["backgroundColor"], "#1E3A5F")

	def test_the_brief_hands_the_accent_handle_over_once_minted(self):
		site = {"site_name": "X", "activity": "Y"}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		page = {"title": "Services", "route": "services", "type": "services"}
		self.assertNotIn("ACCENT:", page_brief_text(site, FakeBrief(), page, handles, "", "bento", "French", [], ("CTA", "/")))
		handles["accent"] = "var(--nt2-accent)"
		self.assertIn("ACCENT: var(--nt2-accent)", page_brief_text(site, FakeBrief(), page, handles, "", "bento", "French", [], ("CTA", "/")))


class TestShopIncludes(unittest.TestCase):
	"""The shop's includes show instance-wide data: never on another business's profile
	(a second storefront of the same company keeps them), and the carousels only on an
	e-commerce site."""

	def test_other_business_compares_the_site_name_with_the_instance_company(self):
		from builder.site_ai.nora.site_builder import _business_key, _other_business

		self.assertEqual(_business_key("Guigoz & Filliez SA"), "guigoz filliez")
		self.assertEqual(_business_key("Boulangerie Solstice Sàrl"), "boulangerie solstice")
		defaults = {("Website Profile", "Main", "is_default"): 1, ("Website Profile", "Espace B2B", "is_default"): 0, ("Website Profile", "Nora Test", "is_default"): 0}
		defaults[("Website Profile", "Espace B2B", "title")] = "Espace B2B"
		defaults[("Website Profile", "Nora Test", "title")] = "Nora Test"
		defaults[("Website Profile", "Burrows", "is_default")] = 0
		defaults[("Website Profile", "Burrows", "title")] = "The 5 Burrows"
		with patch("builder.site_ai.nora.site_builder.frappe.db.get_value", side_effect=lambda d, n, f: defaults.get((d, n, f))), patch(
			"builder.site_ai.nora.site_builder.frappe.db.get_single_value", return_value="Guigoz & Filliez SA"
		):
			self.assertFalse(_other_business(None, "Valrhône Industrie SA"))
			self.assertFalse(_other_business("Main", "Valrhône Industrie SA"))
			self.assertFalse(_other_business("Espace B2B", "Guigoz & Filliez SA"))
			self.assertFalse(_other_business("Espace B2B", "guigoz filliez"))
			# a second brand of the company gets a profile named after it
			self.assertFalse(_other_business("Burrows", "The 5 Burrows"))
			self.assertTrue(_other_business("Nora Test", "Valrhône Industrie SA"))
			self.assertTrue(_other_business("Nora Test", ""))

	def test_the_tool_names_the_site_types_that_set_the_chrome(self):
		from builder.site_ai.nora.site_builder import CLASS_CONTRACT
		from builder.site_ai.nora.tools import SITE_TYPES

		for kind in ("vitrine", "vitrine_user", "ecommerce", "ecommerce_search", "one_page"):
			self.assertIn(kind, SITE_TYPES)
		self.assertIn("u-grid", CLASS_CONTRACT)

	def test_another_business_gets_no_shop_include(self):
		with patch("builder.site_ai.nora.site_builder._other_business", return_value=True):
			tags = [t for t, _ in available_includes("contact", "ecommerce", "Nora Test 2", "Valrhône Industrie SA")]
		self.assertTrue(any("contact_form" in t for t in tags))
		self.assertFalse(any("webshop/" in t for t in tags))

	def test_the_shop_menu_entry_stays_on_the_shop(self):
		from unittest.mock import MagicMock

		from builder.site_ai.nora.site_builder import apply_navigation

		created = [{"name": "p1", "title": "Accueil", "route": "/"}, {"name": "p2", "title": "Bouquets", "route": "/bouquets"}]

		def build(secondary):
			config = MagicMock()
			config.get.return_value = None
			with patch("builder.site_ai.nora.site_builder._other_business", return_value=secondary), patch(
				"builder.site_ai.nora.site_builder.frappe"
			):
				apply_navigation(config, created, "ecommerce", "florist", "Nora Test" if secondary else None, "fr")
			return [c.args[1]["url"] for c in config.append.call_args_list if c.args[0] == "menu_items"]

		self.assertNotIn("/all-products", build(secondary=True))
		self.assertIn("/all-products", build(secondary=False))

	def test_carousels_need_an_ecommerce_site(self):
		with patch("builder.site_ai.nora.site_builder._other_business", return_value=False), patch(
			"frappe.get_installed_apps", return_value=["frappe", "builder", "webshop"]
		):
			vitrine = [t for t, _ in available_includes("accueil", "vitrine", None)]
			shop = [t for t, _ in available_includes("accueil", "ecommerce", None)]
			hours = [t for t, _ in available_includes("contact", "vitrine", None)]
		self.assertEqual(vitrine, [])
		self.assertTrue(all("carousel" in t for t in shop) and shop)
		self.assertTrue(any("opening_hours" in t for t in hours))


class TestBriefCall(unittest.TestCase):
	"""What reaches the model for the design brief (neoffice-maintenance #296)."""

	def test_a_logo_answered_in_words_is_no_logo(self):
		from builder.site_ai.nora.site_builder import clean_logo

		for value in (None, "", "none", "None", "null", "aucun", "pas de logo", "skip"):
			self.assertIsNone(clean_logo(value), value)
		self.assertEqual(clean_logo("/files/logo.png"), "/files/logo.png")
		self.assertEqual(clean_logo("https://x.test/logo.svg"), "https://x.test/logo.svg")
		self.assertIsNone(clean_logo("logo.png"))

	def test_structured_calls_leave_room_for_the_reasoning(self):
		from pydantic import BaseModel

		from builder.site_ai.providers.litellm_provider import STRUCTURED_MAX_TOKENS, LiteLLMProvider

		class Answer(BaseModel):
			x: int

		seen = {}

		def fake_complete(model, messages, params, *, stream, api_key=None):
			seen.update(params)
			return '{"x": 1}'

		provider = LiteLLMProvider(model="managed/kimi-k2.7-code-highspeed", max_tokens=16384)
		with patch("builder.ai.llm.complete", side_effect=fake_complete), patch.object(
			LiteLLMProvider, "_resolve_model", return_value="managed/kimi-k2.7-code-highspeed"
		), patch("builder.ai.models.ModelRegistry.supports_vision", return_value=False):
			answer = provider.generate_structured("give x", Answer, system_prompt="sys")
		self.assertEqual(answer.x, 1)
		self.assertGreaterEqual(seen["max_tokens"], STRUCTURED_MAX_TOKENS)
		self.assertEqual(seen["response_format"], {"type": "json_object"})


class TestTypography(unittest.TestCase):
	"""Viewport font sizes get a clamp, oversized fixed ones are lowered (typography.py)."""

	def test_vw_sizes_become_clamps_and_fixed_sizes_are_capped(self):
		from builder.site_ai.nora.typography import cap_font_sizes, capped_font_size

		# display type in a p (the hero's brand name) keeps its size class, running text does not
		self.assertEqual(capped_font_size("11vw", "p"), "clamp(2rem, 11vw, 4.5rem)")
		self.assertEqual(capped_font_size("3vw", "p"), "clamp(1rem, 3vw, 1.5rem)")
		self.assertEqual(capped_font_size("7vw", "h1"), "clamp(2rem, 7vw, 4.5rem)")
		self.assertEqual(capped_font_size("15vw", "h2", mobile=True), "clamp(1.5rem, 15vw, 2.25rem)")
		self.assertEqual(capped_font_size("96px", "h1"), "4.5rem")
		self.assertIsNone(capped_font_size("72px", "span"))
		self.assertEqual(capped_font_size("120px", "span"), "6rem")
		self.assertIsNone(capped_font_size("1.125rem", "p"))
		# a clamp of our shape, the model's included, is normalised from its vw part
		self.assertEqual(capped_font_size("clamp(1rem, 3vw, 2rem)", "h2"), "clamp(1.5rem, 3vw, 3.25rem)")
		self.assertIsNone(capped_font_size("clamp(1rem, 2vw + 0.5rem, 2rem)", "h2"))
		# a clamp written by an earlier rule is re-derived from its vw part
		self.assertEqual(capped_font_size("clamp(1rem, 11vw, 1.35rem)", "p"), "clamp(2rem, 11vw, 4.5rem)")
		self.assertIsNone(capped_font_size("clamp(2rem, 11vw, 4.5rem)", "p"))
		blocks = [{"element": "section", "children": [{"element": "p", "baseStyles": {"fontSize": "10vw"}, "mobileStyles": {"fontSize": "1rem"}}, {"element": "h2", "baseStyles": {"fontSize": "64px"}}]}]
		self.assertEqual(cap_font_sizes(blocks), 2)
		self.assertEqual(blocks[0]["children"][0]["baseStyles"]["fontSize"], "clamp(2rem, 10vw, 4.5rem)")
		self.assertEqual(blocks[0]["children"][1]["baseStyles"]["fontSize"], "3.25rem")


class TestChromeTools(unittest.TestCase):
	"""The assistant reads and changes the site chrome by dialogue (tools.py)."""

	def test_the_registry_carries_the_three_site_tools(self):
		from builder.site_ai.nora.tools import TOOLS

		self.assertEqual([t.name for t in TOOLS], ["generate_site", "get_site_chrome", "update_site_chrome"])
		self.assertTrue(all(t.side == "server" and callable(t.handler) for t in TOOLS))

	def test_update_payload_keeps_the_chrome_fields_only(self):
		from builder.site_ai.nora.tools import chrome_payload

		payload = chrome_payload({
			"cta_text": "Devis gratuit", "cta_url": "/contact", "show_opening_hours": 1, "primary_color": "#123456",
			"menu_items": [{"label": "Accueil", "url": "/"}, {"label": "", "url": "/x"}, "junk"],
			"footer_links": [{"label": "CGV", "url": "/cgv", "column_name": "Infos"}],
			"secret": "x", "_profile": "Nora Test",
		})
		self.assertEqual(payload["cta_text"], "Devis gratuit")
		self.assertEqual(payload["show_opening_hours"], 1)
		self.assertEqual(payload["menu_items"], [{"label": "Accueil", "url": "/"}])
		self.assertEqual(payload["footer_links"], [{"label": "CGV", "url": "/cgv", "column_name": "Infos"}])
		self.assertNotIn("secret", payload)
		self.assertNotIn("_profile", payload)
		# the design-system colours are chrome fields too (the tokens follow through the hooks)
		self.assertEqual(payload["primary_color"], "#123456")
		self.assertEqual(chrome_payload({"nope": 1}), {})


class TestVisualCheck(unittest.TestCase):
	"""The final look at the built pages (visual_check.py)."""

	def test_loopback_url_names_the_profile(self):
		from builder.site_ai.nora import visual_check

		with patch.object(visual_check.frappe, "local") as local, patch.object(visual_check.frappe, "conf", {"webserver_port": 8000}):
			local.site = "prod.local"
			self.assertEqual(visual_check.loopback_page_url("/projects", "Nora Test 2"), "http://prod.local:8000/projects?_website_profile=Nora%20Test%202")
			self.assertEqual(visual_check.loopback_page_url("/", None), "http://prod.local:8000/")
			# /home redirects to / and loses the query string: ask for / directly
			self.assertEqual(visual_check.loopback_page_url("/home", "Nora Test 2"), "http://prod.local:8000/?_website_profile=Nora%20Test%202")

	def test_only_body_defects_are_actionable_and_become_instructions(self):
		from types import SimpleNamespace as NS

		from builder.site_ai.nora.visual_check import actionable, revision_instructions

		critique = NS(issues=[
			NS(area="hero", severity="high", problem="stretched photo", fix="use object-fit cover"),
			NS(area="footer", severity="high", problem="wrong logo", fix="chrome"),
			NS(area="services", severity="low", problem="tight spacing", fix="more padding"),
			NS(area="gallery", severity="medium", problem="empty band", fix="remove the band"),
		])
		issues = actionable(critique)
		self.assertEqual([i["area"] for i in issues], ["hero", "gallery"])
		text = revision_instructions(issues)
		self.assertTrue(text.startswith("REVISION"))
		self.assertIn("[high] hero: stretched photo -> use object-fit cover", text)
		self.assertIn("keep everything else", text)

	def test_summary_lines_relay_the_verdicts(self):
		from builder.site_ai.nora.visual_check import summary_lines

		reviews = [
			{"name": "p1", "title": "Accueil", "route": "/", "professional": True, "issues": [], "error": None},
			{"name": "p2", "title": "Services", "route": "/services", "professional": False, "issues": [{"area": "grid", "severity": "high", "problem": "empty column", "fix": "fill"}], "error": None},
			{"name": "p3", "title": "Contact", "route": "/contact", "professional": None, "issues": [], "error": "screenshot failed"},
		]
		lines = summary_lines(reviews, {"p2": 1})
		self.assertEqual(len(lines), 4)
		self.assertIn("Accueil: looks professional", lines[1])
		self.assertIn("Services: needs work; 1 point(s) fixed in a revision pass", lines[2])
		self.assertIn("Contact: not reviewed", lines[3])
		self.assertEqual(summary_lines([], {}), [])

	def test_created_pages_map_back_to_their_specs(self):
		from builder.site_ai.nora.site_builder import pages_by_name

		pages = [{"title": "Accueil", "route": "home", "type": "accueil"}, {"title": "Contact", "route": "contact", "type": "contact"}]
		created = [{"name": "p1", "title": "Accueil", "route": "/home"}, {"name": "p2", "title": "Contact", "route": "/contact"}]
		self.assertEqual([(p["name"], p["type"]) for p in pages_by_name(pages, created)], [("p1", "accueil"), ("p2", "contact")])

	def test_the_brief_carries_the_revision(self):
		site = {"site_name": "X", "activity": "Y"}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		page = {"title": "Services", "route": "services", "type": "services"}
		text = page_brief_text(site, FakeBrief(), page, handles, "", "bento", "French", [], ("CTA", "/"), revision="REVISION: fix the hero")
		self.assertTrue(text.rstrip().endswith("REVISION: fix the hero"))


class TestLayout(unittest.TestCase):
	"""An unplaced child of a wide grid spans the row (layout.py)."""

	def test_orphans_of_a_twelve_column_grid_span_the_row(self):
		from builder.site_ai.nora.layout import place_orphans

		grid = {"element": "div", "baseStyles": {"display": "grid", "gridTemplateColumns": "repeat(12, 1fr)"}, "children": [
			{"element": "span", "baseStyles": {"gridColumn": "1 / -1"}},
			{"element": "h2", "baseStyles": {"gridColumn": "1 / -1"}},
			{"element": "div", "baseStyles": {}, "children": [{"element": "div"}]},
		]}
		logos = {"element": "div", "baseStyles": {"display": "grid", "gridTemplateColumns": "repeat(12, 1fr)"}, "children": [{"element": "img", "baseStyles": {}} for _ in range(12)]}
		narrow = {"element": "div", "baseStyles": {"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)"}, "children": [{"element": "div", "baseStyles": {}} for _ in range(3)]}
		blocks = [{"element": "section", "children": [grid, logos, narrow]}]
		self.assertEqual(place_orphans(blocks), 1)
		self.assertEqual(grid["children"][2]["baseStyles"]["gridColumn"], "1 / -1")
		self.assertNotIn("gridColumn", logos["children"][0]["baseStyles"])
		self.assertNotIn("gridColumn", narrow["children"][0]["baseStyles"])


class TestBraceCards(unittest.TestCase):
	"""A card printed as the tool's arguments in pseudo-JSON is still a card (cards.py)."""

	def test_the_recap_written_in_braces_becomes_a_card(self):
		from builder.site_ai.nora.cards import looks_like_card, parse_card

		text = (
			"Voici le récapitulatif.\n{kind: heading, text: Récapitulatif — Lilas & Co}\n"
			"{kind: list, items: ['Nom : Lilas & Co', 'Type : Boutique en ligne', 'Logo : aucun']}\n"
			"{kind: actions, buttons: [{label: Construire le site}, {label: Modifier quelque chose, variant: secondary}]}"
		)
		self.assertTrue(looks_like_card(text))
		card = parse_card(text)
		self.assertEqual([u["kind"] for u in card["ui"]], ["heading", "list", "actions"])
		self.assertEqual(len(next(u for u in card["ui"] if u["kind"] == "list")["items"]), 3)
		self.assertEqual([b["label"] for b in next(u for u in card["ui"] if u["kind"] == "actions")["buttons"]], ["Construire le site", "Modifier quelque chose"])

	def test_choices_written_in_braces_keep_their_options(self):
		from builder.site_ai.nora.cards import parse_card

		text = "Quel type ?\n{kind: choices, label: Type de site, multi: false, options: [{label: Vitrine, description: sans comptes}, {label: Boutique en ligne}]}\n{kind: actions, buttons: [{label: Continuer}]}"
		card = parse_card(text)
		choices = next(u for u in card["ui"] if u["kind"] == "choices")
		self.assertEqual([o["label"] for o in choices["options"]], ["Vitrine", "Boutique en ligne"])
		self.assertEqual(choices["options"][0]["description"], "sans comptes")

