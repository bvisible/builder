# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuilderSiteConfig(Document):
    """
    Stores configuration and metadata for AI-generated sites.
    Created after a complete site generation to track:
    - Colors, theme, site type
    - Generated pages
    - Design brief used
    - Generation timing
    """

    def before_insert(self):
        if not self.generated_at:
            self.generated_at = frappe.utils.now()
