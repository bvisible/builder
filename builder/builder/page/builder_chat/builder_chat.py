# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
	"""Page context for Builder AI Chat."""
	context.no_cache = 1
