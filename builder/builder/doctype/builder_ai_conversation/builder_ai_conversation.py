import frappe
from frappe.model.document import Document


class BuilderAIConversation(Document):
	def before_save(self):
		if not self.messages:
			self.messages = "[]"
		if not self.site_context:
			self.site_context = "{}"
		if not self.generated_blocks:
			self.generated_blocks = "[]"
