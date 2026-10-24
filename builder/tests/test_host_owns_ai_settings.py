# //// Neoffice — added file (no upstream equivalent): a client of a managed instance cannot set up AI providers.
"""A Website Manager holds write on `Builder AI Provider`, and the endpoints behind the `/providers` command only
asked for page write. The command was hidden from a client of a managed instance, but the endpoints answered 200:
`save_ai_provider(name="Managed", provider={"api_base": …})` would have sent the host's key to any server at the next
chat. Found on 2026-10-24 by calling the endpoints from a client session after the v1.36.1 merge (the exposure is older).
No model is called, nothing is written."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.ai import api
from builder.site_ai import capabilities

CLIENT = "someone@example.com"

# every endpoint that connects, changes, lists the balance of or tests a provider
ENDPOINTS = {
	"save_ai_provider": ({"provider_name": "X"},),
	"import_provider_models": ("Managed",),
	"delete_ai_provider": ("Managed",),
	"get_provider_credits": ("Managed",),
	"verify_ai_key": ("custom", "k", "https://example.invalid/v1", "m"),
	"start_codex_login": (),
	"poll_codex_login": ("state",),
	"finish_codex_login": ("http://localhost/cb",),
	"setup_ai_provider": ("custom", "k", "https://example.invalid/v1", ["m"]),
	"test_api_key": ("Managed", "k"),
}


def as_user(user: str, managed: bool):
	"""The user and the instance mode, for the length of one `with`."""
	return _Both(patch.object(capabilities, "is_managed", return_value=managed), patch.object(frappe, "session", SimpleNamespace(user=user)))


class _Both:
	def __init__(self, *patches):
		self.patches = patches

	def __enter__(self):
		for p in self.patches:
			p.start()

	def __exit__(self, *exc):
		for p in reversed(self.patches):
			p.stop()


class TestWhoOwnsTheAISettings(unittest.TestCase):
	def test_a_self_hosted_instance_keeps_its_behaviour(self):
		with as_user(CLIENT, managed=False):
			self.assertTrue(capabilities.host_owns_ai_settings())
			capabilities.require_host_ai_settings()

	def test_the_host_administrator_of_a_managed_instance_may(self):
		with as_user("Administrator", managed=True):
			self.assertTrue(capabilities.host_owns_ai_settings())

	def test_a_client_of_a_managed_instance_may_not(self):
		with as_user(CLIENT, managed=True):
			self.assertFalse(capabilities.host_owns_ai_settings())
			with self.assertRaises(frappe.PermissionError):
				capabilities.require_host_ai_settings()

	def test_it_follows_the_rule_of_the_model_picker(self):
		"""One answer to "who is the host", in the picker and on the server."""
		with as_user(CLIENT, managed=True):
			self.assertFalse(capabilities.ai_capabilities()["model_picker"])
		with as_user("Administrator", managed=True):
			self.assertTrue(capabilities.ai_capabilities()["model_picker"])


class TestTheDecorator(unittest.TestCase):
	def test_it_refuses_before_the_function_runs(self):
		calls = []

		@capabilities.host_ai_settings_only
		def endpoint(x, y=2):
			calls.append((x, y))
			return x + y

		with as_user(CLIENT, managed=True):
			with self.assertRaises(frappe.PermissionError):
				endpoint(1)
		self.assertEqual(calls, [])
		with as_user("Administrator", managed=True):
			self.assertEqual(endpoint(1, y=3), 4)
		with as_user(CLIENT, managed=False):
			self.assertEqual(endpoint(5), 7)

	def test_it_keeps_the_signature_frappe_reads(self):
		import inspect

		self.assertEqual(list(inspect.signature(api.setup_ai_provider).parameters)[:3], ["preset", "api_key", "api_base"])
		self.assertEqual(api.save_ai_provider.__name__, "save_ai_provider")


class TestEveryProviderEndpointRefusesAClient(unittest.TestCase):
	def test_each_endpoint(self):
		"""The refusal must come from the host's guard: a user without roles is already refused by Frappe, which would
		pass this test on the code of before. The guard is replaced by one with a signature of its own."""
		for name, args in ENDPOINTS.items():
			with self.subTest(endpoint=name):
				with patch.object(capabilities, "require_host_ai_settings", side_effect=frappe.PermissionError("host-only")):
					with self.assertRaises(frappe.PermissionError) as refused:
						getattr(api, name)(*args)
				self.assertIn("host-only", str(refused.exception))

	def test_the_list_is_the_list_of_the_endpoints_that_set_up_providers(self):
		"""A new endpoint of this family must be added above, or this fails: it reads the module."""
		import inspect

		families = ("provider", "codex_login", "ai_key", "api_key")
		found = {
			name
			for name, fn in inspect.getmembers(api, inspect.isfunction)
			if fn.__module__ == api.__name__
			and any(word in name for word in families)
			and name not in {"resolve_api_key", "settings_api_key"}
		}
		self.assertTrue(found <= set(ENDPOINTS), found - set(ENDPOINTS))


class TestTheDoctypeKeepsAClientFromWritingAProvider(unittest.TestCase):
	def test_the_hook_refuses_writes_only_for_a_client_of_a_managed_instance(self):
		hook = capabilities.ai_provider_permission
		with as_user(CLIENT, managed=True):
			for ptype in ("write", "create", "delete"):
				self.assertIs(hook(doc=None, ptype=ptype, user=CLIENT), False, ptype)
			self.assertIsNone(hook(doc=None, ptype="read", user=CLIENT))
			self.assertIsNone(hook(doc=None, ptype="write", user="Administrator"))
		with as_user(CLIENT, managed=False):
			self.assertIsNone(hook(doc=None, ptype="write", user=CLIENT))

	def test_it_is_registered_for_the_provider_doctype(self):
		from builder import hooks

		self.assertEqual(hooks.has_permission["Builder AI Provider"], "builder.site_ai.capabilities.ai_provider_permission")
		self.assertTrue(callable(frappe.get_attr(hooks.has_permission["Builder AI Provider"])))
