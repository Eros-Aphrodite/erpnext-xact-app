# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Variation(Document):
	def validate(self):
		total = 0.0
		for row in self.items or []:
			row.amount = (row.quantity or 0) * (row.rate or 0)
			total += row.amount or 0
		self.total_amount = total


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
