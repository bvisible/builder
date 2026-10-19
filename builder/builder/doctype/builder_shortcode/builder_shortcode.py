# //// Neoffice — added file (no upstream equivalent): what a page of this site can carry, as desk shows it.
# //// Neoffice DocType, no upstream counterpart. First commit 057ddaaa 2026-02-02; rewritten 2026-10-20.
#
# This is NOT a second definition of the components. They are defined once, in code (`website_components` in the hooks
# of each app, site_ai/components.py), and `components.sync_registry` writes one row here for each of them on every
# install and migrate: the documentation a person reads (description, usage, example) follows the code, and the one
# field a person owns is `enabled`, the switch that stops the editor, the assistant and the generator from offering
# a component on this site. A page that already carries its tag is untouched. Nobody types a row: nothing would read it.
# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuilderShortcode(Document):
	pass
