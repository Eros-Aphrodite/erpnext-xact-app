# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class ConstructionLead(Document):
	def validate(self):
		if not self.company:
			self.company = frappe.defaults.get_defaults().get("company")

	@frappe.whitelist()
	def create_quote(self):
		"""Create a Construction Estimate from this lead and link it."""
		if self.construction_estimate:
			frappe.msgprint(
				frappe._("Quote already created: {0}").format(self.construction_estimate),
				indicator="blue",
			)
			return self.construction_estimate
		if not self.customer:
			self.convert_to_customer()
			self.customer = frappe.db.get_value("Construction Lead", self.name, "customer")
		estimate = frappe.new_doc("Construction Estimate")
		estimate.customer = self.customer or ""
		estimate.title = self.lead_name or "Quote from Lead"
		if self.budget_amount:
			estimate.total_amount = self.budget_amount
		estimate.currency = self.currency or frappe.defaults.get_defaults().get("currency")
		if hasattr(estimate, "construction_lead"):
			estimate.construction_lead = self.name
		estimate.insert()
		frappe.db.set_value(
			"Construction Lead",
			self.name,
			{"construction_estimate": estimate.name, "stage": "Quote Sent"},
			update_modified=False,
		)
		frappe.db.commit()
		frappe.msgprint(
			frappe._("Quote {0} created.").format(estimate.name),
			indicator="green",
		)
		return estimate.name

	@frappe.whitelist()
	def convert_to_customer(self):
		"""Create Customer from lead and link."""
		if self.customer:
			frappe.msgprint(
				frappe._("Already converted to Customer: {0}").format(self.customer),
				indicator="blue",
			)
			return self.customer
		customer = frappe.new_doc("Customer")
		customer.customer_name = self.lead_name or self.contact_person or "Unknown"
		customer.customer_type = "Company"
		if self.email:
			customer.email_id = self.email
		if self.phone:
			customer.mobile_no = self.phone
		customer.insert()
		frappe.db.set_value(
			"Construction Lead",
			self.name,
			{"customer": customer.name, "stage": "Contacted"},
			update_modified=False,
		)
		frappe.db.commit()
		frappe.msgprint(
			frappe._("Customer {0} created.").format(customer.name),
			indicator="green",
		)
		return customer.name
