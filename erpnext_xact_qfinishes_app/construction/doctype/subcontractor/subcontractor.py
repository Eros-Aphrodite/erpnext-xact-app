# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Subcontractor(Document):
	def validate(self):
		# Avoid duplicate project + supplier
		if self.project and self.supplier:
			existing = frappe.db.exists(
				"Subcontractor",
				{"project": self.project, "supplier": self.supplier, "name": ["!=", self.name]},
			)
			if existing:
				frappe.throw(
					frappe._("A Subcontractor record for this Project and Supplier already exists.")
				)


@frappe.whitelist()
def create_purchase_order(subcontractor_name: str) -> str:
	"""Create a new Purchase Order for this subcontractor (supplier + project pre-filled)."""
	sub = frappe.get_doc("Subcontractor", subcontractor_name)
	company = frappe.defaults.get_defaults().get("company")
	if not company:
		frappe.throw(_("Set default Company in defaults."))
	po = frappe.new_doc("Purchase Order")
	po.supplier = sub.supplier
	po.project = sub.project
	po.company = company
	po.transaction_date = frappe.utils.getdate()
	po.schedule_date = frappe.utils.add_days(po.transaction_date, 7)
	if frappe.db.exists("DocType", "Purchase Order") and hasattr(po, "construction_estimate"):
		# Optional link - leave blank for sub PO
		po.construction_estimate = None
	po.insert(ignore_permissions=True)
	po.run_method("set_missing_values")
	frappe.db.commit()
	return po.name
