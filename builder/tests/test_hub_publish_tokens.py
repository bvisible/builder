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


if __name__ == "__main__":
    unittest.main()
