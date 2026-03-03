# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class Variation(Document):
	def validate(self):
		total = 0.0
		for row in self.items or []:
			row.amount = (row.quantity or 0) * (row.rate or 0)
			total += row.amount or 0
		self.total_amount = total


def _get_customers_for_portal_user():
	"""Return list of customer names the current user is linked to (portal)."""
	from erpnext.controllers.website_list_for_contact import get_customers_suppliers
	customers, _ = get_customers_suppliers("Project", frappe.session.user)
	return customers or []


def _variation_project_customer(variation_name: str) -> str | None:
	"""Return customer name for the variation's project, or None."""
	project = frappe.db.get_value("Variation", variation_name, "project")
	if not project:
		return None
	return frappe.db.get_value("Project", project, "customer")


@frappe.whitelist()
def set_client_approval(variation_name: str, action: str, comment: str = None) -> dict:
	"""
	Set client approval status from portal. action: "Approved" or "Rejected".
	Only callable by a portal user linked to the variation's project customer.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	action = (action or "").strip().capitalize()
	if action not in ("Approved", "Rejected"):
		frappe.throw(_("Action must be Approved or Rejected"))
	variation = frappe.get_doc("Variation", variation_name)
	if not variation.project:
		frappe.throw(_("Variation has no project"))
	customer = frappe.db.get_value("Project", variation.project, "customer")
	if not customer:
		frappe.throw(_("Project has no customer"))
	allowed = _get_customers_for_portal_user()
	if customer not in allowed:
		frappe.throw(_("You do not have permission to approve this variation"), frappe.PermissionError)
	if variation.client_approval_status in ("Approved", "Rejected"):
		frappe.throw(_("This variation has already been {0}.").format(variation.client_approval_status))
	variation.client_approval_status = action
	variation.client_approved_date = now_datetime()
	variation.client_comment = (comment or "").strip() or None
	variation.flags.ignore_permissions = True
	variation.save(ignore_permissions=True)
	frappe.db.commit()
	if action == "Approved":
		_notify_builder_on_client_approval(variation_name, variation)
	return {"ok": True, "client_approval_status": action}


def _notify_builder_on_client_approval(variation_name: str, variation) -> None:
	"""Create an in-app notification for the variation owner / builder."""
	try:
		doc = frappe.get_doc("Variation", variation_name)
		recipients = [doc.owner]
		if doc.owner == "Administrator":
			recipients = frappe.get_all(
				"Has Role",
				filters={"role": ["in", ["System Manager", "Projects Manager", "Projects User"]]},
				pluck="parent",
				limit=5,
			) or []
		if not recipients:
			return
		subject = _("Variation {0} approved by client").format(variation_name)
		notification_doc = {
			"type": "Alert",
			"document_type": "Variation",
			"document_name": variation_name,
			"subject": subject,
			"from_user": frappe.session.user,
		}
		from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
		enqueue_create_notification(recipients, notification_doc)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Variation client approval notification")


@frappe.whitelist()
def create_change_order(variation_name: str) -> str:
	"""Create a Sales Order (change order) from an approved Variation."""
	variation = frappe.get_doc("Variation", variation_name)
	if variation.status != "Approved":
		frappe.throw("Variation must be Approved before creating Change Order.")
	customer = None
	company = None
	if variation.sales_order:
		so = frappe.get_doc("Sales Order", variation.sales_order)
		customer = so.customer
		company = so.company
	if not customer and variation.quotation:
		q = frappe.get_doc("Quotation", variation.quotation)
		customer = q.party_name if q.quotation_to == "Customer" else None
		company = q.company
	if not customer:
		frappe.throw("Could not determine Customer from Sales Order or Quotation.")
	so = frappe.new_doc("Sales Order")
	so.customer = customer
	so.company = company or frappe.defaults.get_defaults().get("company")
	so.project = variation.project
	so.po_no = f"Variation: {variation.name}"
	for row in variation.items or []:
		so.append(
			"items",
			{
				"item_code": row.item,
				"description": row.description or "",
				"qty": row.quantity or 0,
				"uom": row.uom,
				"rate": row.rate or 0,
			},
		)
	so.insert(ignore_permissions=True)
	so.run_method("set_missing_values")
	frappe.db.set_value("Variation", variation_name, "sales_order_ref", so.name, update_modified=False)
	frappe.db.commit()
	return so.name
