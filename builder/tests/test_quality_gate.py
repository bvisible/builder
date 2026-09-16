# //// Neoffice — added file (no upstream equivalent): tests of the look's authority.
"""The pure parts of the quality gate (2026-09-16): the verdict a report earns, the measured
findings at three widths, the interior-page contract, the judge that is not the writer, the
logo a rebuild keeps, the reasoning effort K3 is asked for, and the site plan the page brief
executes. No browser, no model: what each helper decides from what it is given."""

import unittest
from unittest.mock import patch

import frappe

from builder.ai.llm import patch_params_for_provider
from builder.site_ai.nora import site_plan, visual_check
from builder.site_ai.nora.layout import interior_top
from builder.site_ai.nora.site_builder import keeps_own_logo, page_brief_text


def report(**kw):
	base = {"name": "p1", "title": "Contact", "route": "/contact", "professional": True, "issues": [], "error": None, "overall": "", "gate": [], "chrome": [], "http_error": None}
	base.update(kw)
	return base


class TestTheVerdict(unittest.TestCase):
	"""A page is accepted when nothing measured or seen stands against it; refused when the
	judge calls it unprofessional, the browser measured it broken, or it did not render."""

	def test_a_clean_professional_page_is_accepted(self):
		self.assertTrue(visual_check.accepted(report()))
		self.assertFalse(visual_check.refused(report()))

	def test_a_page_the_judge_calls_unprofessional_is_refused(self):
		r = report(professional=False, overall="the title wraps letter by letter")
		self.assertFalse(visual_check.accepted(r))
		self.assertTrue(visual_check.refused(r))
		self.assertIn("the designer", visual_check.why_refused(r))

	def test_a_measured_break_refuses_a_page_the_judge_liked(self):
		r = report(gate=[{"kind": "starved-text", "severity": "high", "width": 375, "where": 'h1 "Contactez-nous"', "detail": "88px wide, wrapped on 9 lines"}])
		self.assertFalse(visual_check.accepted(r))
		self.assertTrue(visual_check.refused(r))
		self.assertIn("measured at 375px", visual_check.why_refused(r))

	def test_a_medium_point_blocks_acceptance_but_does_not_refuse(self):
		r = report(issues=[{"area": "hero", "severity": "medium", "problem": "the kicker is faint", "fix": "darken it"}])
		self.assertFalse(visual_check.accepted(r))
		self.assertFalse(visual_check.refused(r))

	def test_a_page_that_answered_an_error_is_refused(self):
		r = report(http_error=417, error="the page answered HTTP 417")
		self.assertTrue(visual_check.refused(r))
		self.assertFalse(visual_check.accepted(r))
		self.assertIn("417", visual_check.why_refused(r))

	def test_a_page_that_could_not_be_read_is_neither_accepted_nor_refused(self):
		r = report(professional=None, error="screenshot failed")
		self.assertFalse(visual_check.accepted(r))
		self.assertFalse(visual_check.refused(r))


class TestTheMeasuredFindings(unittest.TestCase):
	def measured(self):
		sticks = {"kind": "sticks-out", "severity": "high", "where": 'div "mark"', "detail": "spans -120px to 200px"}
		return {
			"status": 200,
			"widths": {
				1440: {"findings": [sticks], "facts": {"band": True, "body_h1": 0, "header_logo": True, "header_text": "", "width": 1440}},
				768: {"findings": [sticks], "facts": {"band": True, "body_h1": 0, "width": 768}},
				375: {"findings": [sticks, {"kind": "starved-text", "severity": "high", "where": 'h1 "Nos marques"', "detail": "88px wide"}], "facts": {"band": True, "body_h1": 0, "width": 375}},
			},
		}

	def test_a_finding_seen_at_every_width_is_reported_once_with_the_widest_screen(self):
		found = visual_check.dedupe_findings(self.measured())
		self.assertEqual([(f["kind"], f["width"]) for f in found], [("sticks-out", 1440), ("starved-text", 375)])

	def test_the_measured_points_lead_the_revision(self):
		gate = visual_check.dedupe_findings(self.measured())
		issues = [{"area": "hero", "severity": "high", "problem": "faint", "fix": "darken"}]
		text = visual_check.revision_instructions(issues, gate)
		lines = text.splitlines()
		self.assertTrue(lines[1].startswith("- [measured, high] at 1440px"))
		self.assertTrue(lines[-1].startswith("- [high] hero"))

	def test_an_interior_page_without_its_band_breaks_the_contract(self):
		m = {"widths": {1440: {"findings": [], "facts": {"band": False, "body_h1": 1, "header_logo": True, "width": 1440}}}}
		page, chrome = visual_check.contract_findings(m, is_home=False)
		self.assertEqual([p["kind"] for p in page], ["band-missing"])
		self.assertEqual(chrome, [])

	def test_a_band_and_an_h1_is_a_double_title(self):
		m = {"widths": {1440: {"findings": [], "facts": {"band": True, "body_h1": 1, "header_logo": True, "width": 1440}}}}
		page, _chrome = visual_check.contract_findings(m, is_home=False)
		self.assertEqual([p["kind"] for p in page], ["double-title"])

	def test_the_home_owes_no_band_and_a_bare_header_is_the_chrome_s_finding(self):
		m = {"widths": {1440: {"findings": [], "facts": {"band": False, "body_h1": 1, "header_logo": False, "header_text": "", "width": 1440}}}}
		page, chrome = visual_check.contract_findings(m, is_home=True)
		self.assertEqual(page, [])
		self.assertEqual([c["kind"] for c in chrome], ["logo-missing"])


class TestTheJudge(unittest.TestCase):
	"""The judge is never the writer when a stronger reader is registered."""

	def registry(self, known: dict):
		from builder.ai.models import ModelRegistry

		return patch.multiple(ModelRegistry, find=lambda name: known.get(name), supports_vision=lambda name: bool((known.get(name) or {}).get("vision")))

	def test_the_configured_reader_wins(self):
		with self.registry({"openrouter/anthropic/claude-sonnet-5": {"vision": True}, "managed/kimi-k3": {"vision": True}}), patch.object(frappe, "conf", {"nora_review_model": "openrouter/anthropic/claude-sonnet-5"}):
			self.assertEqual(visual_check.judge_model("managed/kimi-k3"), "openrouter/anthropic/claude-sonnet-5")

	def test_without_a_configured_reader_the_strongest_managed_kimi_reads(self):
		with self.registry({"managed/kimi-k3": {"vision": True}}), patch.object(frappe, "conf", {}):
			self.assertEqual(visual_check.judge_model("managed/kimi-k2.7-code-highspeed"), "managed/kimi-k3")

	def test_the_writer_reads_its_own_pages_only_when_nobody_else_can(self):
		with self.registry({"managed/kimi-k2.7-code": {"vision": True}}), patch.object(frappe, "conf", {}):
			self.assertEqual(visual_check.judge_model("managed/kimi-k2.7-code"), "managed/kimi-k2.7-code")

	def test_a_reader_that_cannot_see_is_not_a_judge(self):
		with self.registry({"managed/kimi-k3": {"vision": False}}), patch.object(frappe, "conf", {"nora_review_model": "managed/kimi-k3"}):
			self.assertEqual(visual_check.judge_model("managed/kimi-k2.7-code"), "managed/kimi-k2.7-code")


class TestTheInteriorTop(unittest.TestCase):
	def test_every_h1_of_an_interior_page_becomes_an_h2_with_its_styles(self):
		blocks = [{"element": "div", "children": [
			{"element": "section", "children": [{"element": "h1", "innerHTML": "Une équipe à votre écoute", "baseStyles": {"fontSize": "3rem"}}]},
			{"element": "section", "children": [{"element": "h1", "innerHTML": "Nos valeurs"}]},
		]}]
		self.assertEqual(interior_top(blocks, "À propos"), 2)
		heads = [b for s in blocks[0]["children"] for b in s["children"]]
		self.assertEqual([h["element"] for h in heads], ["h2", "h2"])
		self.assertEqual(heads[0]["baseStyles"]["fontSize"], "3rem")

	def test_a_page_without_h1_is_left_alone(self):
		blocks = [{"element": "div", "children": [{"element": "section", "children": [{"element": "h2", "innerHTML": "Nos valeurs"}]}]}]
		self.assertEqual(interior_top(blocks, "À propos"), 0)


class TestTheLogoARebuildKeeps(unittest.TestCase):
	def test_the_client_s_own_logo_is_kept(self):
		self.assertTrue(keeps_own_logo("Image", "/files/client-wordmark.svg", "/files/logo-default.png"))

	def test_the_host_s_inherited_logo_is_not(self):
		self.assertFalse(keeps_own_logo("Image", "/files/logo-default.png", "/files/logo-default.png"))

	def test_a_text_logo_or_no_image_is_not_a_logo_of_its_own(self):
		self.assertFalse(keeps_own_logo("Text", "/files/client-wordmark.svg", None))
		self.assertFalse(keeps_own_logo("Image", "", None))


class TestK3ReasoningEffort(unittest.TestCase):
	def test_k3_is_asked_to_think_at_the_configured_effort(self):
		with patch.object(frappe, "conf", {"nora_reasoning_effort": "low"}):
			params = patch_params_for_provider("openai/kimi-k3", {"max_tokens": 40000, "temperature": 0.7})
		self.assertEqual(params["extra_body"], {"reasoning_effort": "low"})
		self.assertEqual(params["temperature"], 1)

	def test_high_is_the_default_and_a_wrong_value_falls_back_to_it(self):
		with patch.object(frappe, "conf", {"nora_reasoning_effort": "turbo"}):
			self.assertEqual(patch_params_for_provider("openai/kimi-k3", {})["extra_body"]["reasoning_effort"], "high")
		with patch.object(frappe, "conf", {}):
			self.assertEqual(patch_params_for_provider("openai/kimi-k3", {})["extra_body"]["reasoning_effort"], "high")

	def test_k2_gets_no_reasoning_effort(self):
		with patch.object(frappe, "conf", {"nora_reasoning_effort": "low"}):
			self.assertNotIn("extra_body", patch_params_for_provider("openai/kimi-k2.7-code", {"temperature": 0.7}))

	def test_a_caller_s_own_effort_is_not_overridden(self):
		with patch.object(frappe, "conf", {"nora_reasoning_effort": "low"}):
			params = patch_params_for_provider("openai/kimi-k3", {"extra_body": {"reasoning_effort": "max"}})
		self.assertEqual(params["extra_body"]["reasoning_effort"], "max")


class FakeBrief:
	design_concept = "Calm editorial"
	signature_element = "A sage rule above each h2"
	site_tone = "professional"
	hero_style = "split"
	heading_font = "Fraunces"
	body_font = "Source Sans 3"
	border_radius_style = "subtle"
	cta_shape = "Rounded"
	button_hover = "Darken"
	motion_style = "Calm"


class TestTheSitePlan(unittest.TestCase):
	def plan(self):
		return site_plan.SitePlan(
			direction="Light ground, ink navy, one sage accent.",
			signature_move="a 2px sage rule 48px wide above every h2",
			interior_top="a two-column intro: a short statement left, one photograph right, 96px of padding",
			rhythm="sections at 96px, content 1200px wide",
			logo_notes="the wordmark is wide: header on white",
			pages=[site_plan.PlannedPage(route="about", title="À propos", sections=[
				site_plan.PlannedSection(kind="intro", purpose="who they are", copy="two lines, warm", layout="two columns 7fr 5fr", photos=["/files/team.jpg"]),
				site_plan.PlannedSection(kind="hours", purpose="when the shop is open", component="webshop/templates/includes/opening_hours.html"),
			], notes="no team section: nobody is named")],
		)

	def test_the_page_brief_executes_the_plan_s_sections_and_carries_the_contract(self):
		site = {"site_name": "Atelier Test", "activity": "a workshop", "site_type": "vitrine", "profile": None, "page_types": ["accueil", "about"], "plan": self.plan()}
		page = {"title": "À propos", "route": "about", "type": "about"}
		handles = {"primary": "var(--t-primary)", "secondary": "var(--t-secondary)", "background": "var(--t-background)", "text": "var(--t-text)", "font-heading": "var(--t-font-heading)", "font-body": "var(--t-font-body)"}
		with patch("builder.site_ai.nora.site_builder.available_includes", return_value=[]):
			text = page_brief_text(site, FakeBrief(), page, handles, "", "classic-centered", "French", [], ("Contact", "/contact"))
		self.assertIn("1. [intro] who they are — copy: two lines, warm — layout: two columns 7fr 5fr — photos: /files/team.jpg", text)
		self.assertIn('2. [hours] when the shop is open — component: {% include "webshop/templates/includes/opening_hours.html" %}', text)
		self.assertIn("THIS PAGE OPENS WITH (the site's title band is drawn above it): a two-column intro", text)
		self.assertIn("SIGNATURE MOVE, exactly this on every page: a 2px sage rule", text)
		self.assertIn("PAGE NOTES from the plan: no team section", text)
		self.assertNotIn("the story and the mission", text)

	def test_a_page_the_plan_does_not_cover_keeps_the_static_plan(self):
		site = {"site_name": "Atelier Test", "activity": "a workshop", "site_type": "vitrine", "profile": None, "page_types": ["accueil", "about"], "plan": self.plan()}
		page = {"title": "Contact", "route": "contact", "type": "contact"}
		handles = {"primary": "var(--t-primary)", "secondary": "var(--t-secondary)", "background": "var(--t-background)", "text": "var(--t-text)", "font-heading": "var(--t-font-heading)", "font-body": "var(--t-font-body)"}
		with patch("builder.site_ai.nora.site_builder.available_includes", return_value=[]):
			text = page_brief_text(site, FakeBrief(), page, handles, "", "classic-centered", "French", [], ("Contact", "/contact"))
		self.assertIn("a contact form: name, email, message, one submit button", text)
		# the site-wide contract still applies
		self.assertIn("RHYTHM: sections at 96px", text)

	def test_the_home_is_not_told_what_an_interior_page_opens_with(self):
		lines = site_plan.contract_lines(self.plan(), is_home=True)
		self.assertFalse(any(line.startswith("THIS PAGE OPENS WITH") for line in lines))
		self.assertTrue(any(line.startswith("LOGO: the wordmark is wide") for line in lines))

	def test_a_plan_survives_its_json(self):
		again = site_plan.from_json(site_plan.as_json(self.plan()))
		self.assertEqual(again.pages[0].sections[1].component, "webshop/templates/includes/opening_hours.html")
		self.assertIsNone(site_plan.from_json("not json"))


class TestTheSummary(unittest.TestCase):
	def test_a_refused_page_is_named_and_the_user_is_asked(self):
		reviews = [report(name="p1", title="Contact", professional=False), report(name="p2", title="À propos")]
		held = [{"name": "p1", "title": "Contact", "route": "/contact", "attempts": 4, "why": "the designer: the title wraps letter by letter", "essential": False}]
		lines = visual_check.summary_lines(reviews, {}, held)
		self.assertTrue(any("Contact: REFUSED after 4 look(s), NOT published and NOT in the menu" in line for line in lines))
		self.assertTrue(any("À propos: looks professional" in line for line in lines))
		self.assertTrue(any(line.startswith("Ask the user, with ONE present_ui choices card") for line in lines))

	def test_an_essential_refused_page_stays_up_and_says_so(self):
		held = [{"name": "p1", "title": "Accueil", "route": "/", "attempts": 4, "why": "measured", "essential": True}]
		lines = visual_check.summary_lines([], {}, held)
		self.assertTrue(any("published but flagged" in line for line in lines))


class TestTheCallersTimeout(unittest.TestCase):
	"""A non-streamed call to a thinking model takes minutes: the provider's timeout must reach
	litellm instead of the 120 s that cut the site plan twice."""

	def test_the_provider_sends_its_timeout(self):
		from builder.site_ai.providers.litellm_provider import LiteLLMProvider

		provider = LiteLLMProvider(model="managed/kimi-k3", timeout=900)
		self.assertEqual(provider._params()["timeout"], 900)

	def test_complete_hands_it_to_litellm_and_keeps_120_by_default(self):
		from unittest.mock import MagicMock

		from builder.ai import llm

		answer = MagicMock()
		answer.choices = [MagicMock(message=MagicMock(content="ok"))]
		answer.usage = None
		with patch.object(llm.litellm, "completion", return_value=answer) as call, patch.object(llm, "route", return_value=("openai/x", {}, "k")):
			llm.complete("openai/x", [{"role": "user", "content": "hi"}], {"timeout": 900, "max_tokens": 10}, stream=False)
			self.assertEqual(call.call_args.kwargs["timeout"], 900)
			self.assertNotIn("timeout", {k: v for k, v in call.call_args.kwargs.items() if k == "params"})
			llm.complete("openai/x", [{"role": "user", "content": "hi"}], {"max_tokens": 10}, stream=False)
			self.assertEqual(call.call_args.kwargs["timeout"], 120)

