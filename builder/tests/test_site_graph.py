# //// Neoffice — added file (no upstream equivalent): the site's identity for search engines
# //// (builder/site_graph.py). neoffice-maintenance#691 (lot 1), 2026-09-24.
#
# The home page declares the WebSite (the name Google prints above each result) and the
# Organization behind it, which other apps complete through the `site_organization` hook.
import json
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder import site_graph

BASE = "https://shop.test"


class _Chrome(dict):
	"""Enough of a Website Header Footer Config: its fields and its logo."""

	def get_logo_data(self):
		return {"image": self.get("logo_image") or "/assets/neoffice_theme/images/neoffice_logo.svg"}


def contribute(organization):
	"""A `site_organization` hook, as another app declares one."""
	organization["@type"] = "OnlineStore"
	organization["vatID"] = "CHE-123.456.789 TVA"
	return [{"@type": "Store", "parentOrganization": {"@id": organization["@id"]}}, "not a node"]


def fail(organization):
	raise ValueError("an app's contribution failed")


def _graph(chrome, hooks=(), app_name="Frappe"):
	real_get_hooks = frappe.get_hooks

	def get_hooks(name=None, *args, **kwargs):
		if name == "site_organization":
			return list(hooks)
		return real_get_hooks(name, *args, **kwargs)

	with (
		patch("builder.site_graph.site_base", return_value=BASE),
		patch(
			"builder.site_icon._website_setting", side_effect=lambda field: {"app_name": app_name}.get(field)
		),
		patch("builder.site_graph.frappe.get_hooks", side_effect=get_hooks),
	):
		return site_graph.site_graph(chrome)


class TestSiteGraph(unittest.TestCase):
	def test_the_website_and_its_organization(self):
		chrome = _Chrome(
			logo_type="Image",
			logo_image="/files/atelier logo.png",
			logo_text="Atelier Nord",
			business_name="Atelier Nord Sàrl",
			business_phone="+41 27 000 00 00",
			business_email="hello@shop.test",
			instagram_url="https://www.instagram.com/ateliernord",
			facebook_url="",
		)
		graph = _graph(chrome)
		website, organization = graph["@graph"]
		self.assertEqual(
			(website["@type"], website["name"], website["url"]), ("WebSite", "Atelier Nord", BASE + "/")
		)
		self.assertEqual(website["publisher"], {"@id": BASE + "/#organization"})
		self.assertEqual(organization["@id"], BASE + "/#organization")
		self.assertEqual(organization["legalName"], "Atelier Nord Sàrl")
		self.assertEqual(organization["logo"], BASE + "/files/atelier%20logo.png")
		self.assertEqual(organization["telephone"], "+41 27 000 00 00")
		self.assertEqual(organization["sameAs"], ["https://www.instagram.com/ateliernord"])

	def test_the_name_is_the_brand_then_the_site_then_the_business(self):
		self.assertEqual(_graph(_Chrome(logo_text="Maison Test"))["@graph"][0]["name"], "Maison Test")
		self.assertEqual(_graph(_Chrome(logo_text="My Site"), app_name="Rives")["@graph"][0]["name"], "Rives")
		self.assertEqual(_graph(_Chrome(business_name="Rives SA"))["@graph"][0]["name"], "Rives SA")
		self.assertIsNone(_graph(_Chrome(logo_text="My Site")))

	def test_a_site_without_chrome_declares_nothing(self):
		# an offline site: get_header_footer_config answers None to a visitor
		with patch("builder.hf_utils.header_footer.get_header_footer_config", return_value=None):
			self.assertIsNone(site_graph.site_graph())

	def test_no_logo_rather_than_neoffice_s(self):
		organization = _graph(_Chrome(logo_type="Image", logo_text="Maison Test"))["@graph"][1]
		self.assertNotIn("logo", organization)

	def test_other_apps_complete_the_organization_and_a_failure_costs_only_their_share(self):
		hooks = ["builder.tests.test_site_graph.fail", "builder.tests.test_site_graph.contribute"]
		with patch("builder.site_graph.frappe.log_error") as logged:
			graph = _graph(_Chrome(logo_text="Maison Test"), hooks=hooks)["@graph"]
		organization = graph[1]
		self.assertEqual(organization["@type"], "OnlineStore")
		self.assertEqual(organization["vatID"], "CHE-123.456.789 TVA")
		logged.assert_called_once()
		# the node a contribution returns joins the graph; what is not a node does not
		self.assertEqual(len(graph), 3)
		self.assertEqual(graph[2]["parentOrganization"], {"@id": organization["@id"]})


class TestSiteHome(unittest.TestCase):
	def setUp(self):
		self.request = getattr(frappe.local, "request", None)
		self.addCleanup(setattr, frappe.local, "request", self.request)
		self.profile = getattr(frappe.local, "website_profile_doc", None)
		self.addCleanup(setattr, frappe.local, "website_profile_doc", self.profile)
		frappe.local.website_profile_doc = None

	def page(self, route, home=False):
		return SimpleNamespace(route=route, is_home_page=lambda: home)

	def test_the_root_of_the_site_is_its_home(self):
		frappe.local.request = SimpleNamespace(path="/")
		self.assertTrue(site_graph.is_site_home(self.page("accueil")))

	def test_another_page_is_not_unless_it_is_the_home_page(self):
		frappe.local.request = SimpleNamespace(path="/a-propos")
		self.assertFalse(site_graph.is_site_home(self.page("a-propos")))
		frappe.local.request = SimpleNamespace(path="/accueil")
		self.assertTrue(site_graph.is_site_home(self.page("accueil", home=True)))

	def test_a_profile_names_its_own_home(self):
		frappe.local.request = SimpleNamespace(path="/b2b-accueil")
		frappe.local.website_profile_doc = frappe._dict(
			home_route="b2b-accueil", primary_domain="pro.shop.test"
		)
		self.assertTrue(site_graph.is_site_home(self.page("b2b-accueil")))
		self.assertFalse(site_graph.is_site_home(self.page("accueil", home=True)))
		self.assertEqual(site_graph.site_base(), "https://pro.shop.test")


class TestWebpageTemplate(unittest.TestCase):
	def test_the_home_page_prints_the_graph_once(self):
		from jinja2.sandbox import SandboxedEnvironment

		import builder

		path = os.path.join(os.path.dirname(builder.__file__), "templates", "generators", "webpage.html")
		with open(path) as template:
			source = template.read()
		block = re.search(r"\{%- if site_jsonld %\}.*?\{%- endif %\}", source, re.S)
		self.assertIsNotNone(block, "webpage.html no longer prints the site graph")
		environment = SandboxedEnvironment()
		graph = {"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": "A </script> B"}]}
		html = environment.from_string(block.group(0)).render(site_jsonld=graph)
		self.assertEqual(html.count('<script type="application/ld+json">'), 1)
		self.assertNotIn("</script> B", html)
		body = html.split('<script type="application/ld+json">', 1)[1].rsplit("</script>", 1)[0]
		self.assertEqual(json.loads(body), graph)
		self.assertEqual(environment.from_string(block.group(0)).render(site_jsonld=None).strip(), "")
