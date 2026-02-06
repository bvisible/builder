# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""
Chat API endpoints for the Builder AI Chat.

All endpoints follow the standard response format:
{
    "success": bool,
    "message": str (on error),
    ...data fields
}
"""

import frappe
from frappe import _


@frappe.whitelist()
def start_session():
	"""
	Start a new builder chat session or resume an existing active session.

	Returns:
		Dict with session info and welcome message
	"""
	from builder.builder_chat_service import BuilderChatService

	service = BuilderChatService()
	return service.start_session(user=frappe.session.user)


@frappe.whitelist()
def send_message(session_id: str, message: str):
	"""
	Send a message to the builder chat and get a response.

	Args:
		session_id: The session UUID
		message: The user's message text

	Returns:
		Dict with AI response, extracted data, and progress info
	"""
	from builder.builder_chat_service import BuilderChatService

	if not session_id:
		return {"success": False, "message": _("Session ID is required")}

	if not message:
		return {"success": False, "message": _("Message is required")}

	service = BuilderChatService()
	return service.process_message(session_id, message)


@frappe.whitelist()
def upload_logo(session_id: str, file_url: str):
	"""
	Handle logo upload for a session.

	Args:
		session_id: The session UUID
		file_url: URL of the already uploaded file

	Returns:
		Dict with success status and response
	"""
	from builder.builder_chat_service import BuilderChatService

	if not session_id:
		return {"success": False, "message": _("Session ID is required")}

	if not file_url:
		return {"success": False, "message": _("File URL is required")}

	service = BuilderChatService()
	return service.upload_logo(session_id, file_url)


@frappe.whitelist()
def trigger_generation(session_id: str):
	"""
	Trigger site generation with collected parameters.

	Args:
		session_id: The session UUID

	Returns:
		Dict with job_id and status
	"""
	from builder.builder_chat_service import BuilderChatService

	if not session_id:
		return {"success": False, "message": _("Session ID is required")}

	service = BuilderChatService()
	return service.trigger_generation(session_id)


@frappe.whitelist()
def get_generation_status(session_id: str):
	"""
	Get the current generation status for polling.

	Args:
		session_id: The session UUID

	Returns:
		Dict with generation progress info
	"""
	if not session_id:
		return {"success": False, "message": _("Session ID is required")}

	try:
		session = frappe.get_doc("Builder Chat Session", {"session_id": session_id})

		if not session.job_id:
			return {"success": False, "message": _("No generation job found")}

		# Get status from the existing API
		from builder.api import get_site_generation_status
		status = get_site_generation_status(session.job_id)

		if status:
			return status
		else:
			return {
				"status": session.generation_status or "unknown",
				"progress": session.generation_progress or 0,
			}

	except frappe.DoesNotExistError:
		return {"success": False, "message": _("Session not found")}
	except Exception as e:
		frappe.log_error("Builder Chat: Get generation status error", str(e))
		return {"success": False, "message": _("Failed to get generation status")}


@frappe.whitelist()
def get_session(session_id: str):
	"""
	Get full session data including conversation history.

	Args:
		session_id: The session UUID

	Returns:
		Dict with full session info
	"""
	from builder.builder_chat_service import BuilderChatService

	if not session_id:
		return {"success": False, "message": _("Session ID is required")}

	service = BuilderChatService()
	return service.get_session(session_id)
