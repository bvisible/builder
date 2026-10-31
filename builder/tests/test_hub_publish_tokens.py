# //// Neoffice — added file (no upstream equivalent): the design tokens a page sends to the Builder Hub.
"""A page published to the hub carries the design tokens its blocks name. Builder Variable was renamed Builder Token (name field variable_name
became token_name): the collection still read the old doctype and a publish from a current builder lost every token. Pinned here: the doctype
is the one the site has, rows leave under the old wire name, a name the site does not know is skipped. The database is replaced."""

import unittest
from unittest.mock import MagicMock, patch

import frappe

from builder import hub_publish


def rows(has_token_doctype, stored, names):
    db = MagicMock()
    db.exists.side_effect = lambda doctype, name=None: has_token_doctype if (doctype, name) == ("DocType", "Builder Token") else False
    asked = []

    def get_value(doctype, name, fields, as_dict=True):
        asked.append((doctype, name, tuple(fields)))
        return stored.get(name)

    db.get_value.side_effect = get_value
    with patch.object(hub_publish.frappe, "db", db):
        return hub_publish._token_rows(names), asked


class TestTheTokensOfAPublishedPage(unittest.TestCase):
    def test_a_current_site_reads_builder_token_and_sends_the_old_wire_name(self):
        stored = {"u-1": frappe._dict(name="u-1", token_name="Primary", type="Color", value="#112233", dark_value=None, group="g")}
        out, asked = rows(True, stored, ["u-1"])
        self.assertEqual(("Builder Token", "u-1", ("name", "token_name", "type", "value", "dark_value", "group")), asked[0])
        self.assertEqual([{"doctype": "Builder Variable", "name": "u-1", "variable_name": "Primary", "type": "Color", "value": "#112233", "dark_value": None, "group": "g"}], out)

    def test_an_older_site_reads_builder_variable(self):
        stored = {"u-1": frappe._dict(name="u-1", variable_name="Primary", type="Color", value="#112233", dark_value=None, group="g")}
        out, asked = rows(False, stored, ["u-1"])
        self.assertEqual("Builder Variable", asked[0][0])
        self.assertEqual("Primary", out[0]["variable_name"])

    def test_a_name_the_site_does_not_know_is_skipped(self):
        out, _ = rows(True, {}, ["u-missing"])
        self.assertEqual([], out)


class TestWhichTokensAPageNames(unittest.TestCase):
    def test_a_uuid_token_of_the_editor_and_a_prefixed_token_of_a_generated_site_are_both_named(self):
        blob = '{"c": "var(--0824f62b-f051-48a6-b08b-283242b35aa7)", "b": "var(--gf-primary)", "t": "var(--gf-font-heading)"}'
        self.assertEqual(
            ["0824f62b-f051-48a6-b08b-283242b35aa7", "gf-font-heading", "gf-primary"],
            hub_publish.referenced_token_names(blob),
        )

    def test_a_token_named_twice_is_named_once(self):
        self.assertEqual(["gf-primary"], hub_publish.referenced_token_names("var(--gf-primary) var(--gf-primary)"))

    def test_a_page_without_tokens_names_none(self):
        self.assertEqual([], hub_publish.referenced_token_names('{"c": "#fff", "d": "var(  --x )"}'))

    def test_a_css_variable_that_is_no_token_of_the_site_is_named_and_then_skipped(self):
        blob = "var(--gf-primary) var(--some-library-variable)"
        names = hub_publish.referenced_token_names(blob)
        self.assertIn("some-library-variable", names)
        stored = {"gf-primary": frappe._dict(name="gf-primary", token_name="Primary", type="Color", value="#112233", dark_value=None, group="Business")}
        out, _ = rows(True, stored, names)
        self.assertEqual(["gf-primary"], [r["name"] for r in out])


GENERATED = {"gf-primary": frappe._dict(name="gf-primary", token_name="Primary", type="Color", value="#112233", dark_value=None, group="Business")}


class TestTheGroupTheTokensLeaveIn(unittest.TestCase):
    """The hub serves a template group's tokens by the group's name, and exports them at promotion the same way: a token that stays in the group
    its source site gave it (a business name) never reaches a client who installs the template."""

    def rows_in(self, group):
        db = MagicMock()
        db.exists.return_value = True
        db.get_value.side_effect = lambda doctype, name, fields, as_dict=True: GENERATED.get(name)
        with patch.object(hub_publish.frappe, "db", db):
            return hub_publish._token_rows(["gf-primary"], group)

    def test_the_rows_leave_in_the_template_group(self):
        self.assertEqual("restaurant", self.rows_in("restaurant")[0]["group"])

    def test_with_no_group_a_token_keeps_its_own(self):
        self.assertEqual("Business", self.rows_in(None)[0]["group"])

    def test_the_bundle_of_each_page_is_built_for_the_group_it_is_published_in(self):
        built = []
        response = MagicMock(status_code=200)
        response.json.return_value = {"message": {"group": "restaurant"}}
        with (
            patch.object(hub_publish, "_hub_config", return_value=("https://hub.test", {})),
            patch.object(hub_publish, "_build_page_bundle", side_effect=lambda name, group=None: built.append((name, group)) or {"page": {}}),
            patch.object(hub_publish, "_upload_and_rewrite_assets", side_effect=lambda payload, *a: payload),
            patch.object(hub_publish.requests, "post", return_value=response),
        ):
            hub_publish._publish_group_sync(["page-a", "page-b"], "restaurant", "Restaurant")
        self.assertEqual([("page-a", "restaurant"), ("page-b", "restaurant")], built)


if __name__ == "__main__":
    unittest.main()
