# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Job(Document):
	def validate(self):
		if self.project:
			# Sync title from project name
			project_title = frappe.db.get_value("Project", self.project, "project_name")
			if project_title:
				self.title = project_title

	@frappe.whitelist()
	def refresh_summary(self) -> None:
		"""Update contract value, progress invoiced, variations, and related links from project data."""
		if not self.project:
			return

		# Title from project
		project_name = frappe.db.get_value("Project", self.project, "project_name")
		self.title = project_name or self.project

		# Primary Construction Estimate (latest with this project)
		est = frappe.db.get_value(
			"Construction Estimate",
			{"project": self.project},
			["name", "total_amount", "material_request_ref"],
			order_by="modified desc",
			as_dict=True,
		)
		self.construction_estimate = est.name if est else None
		self.material_request_ref = (est.material_request_ref or None) if est else None

		# Contract value: from Sales Orders (submitted) for this project
		so_totals = frappe.db.sql(
			"""
			select sum(grand_total) from `tabSales Order`
			where project = %s and docstatus = 1
			""",
			(self.project,),
		)
		contract_value = flt(so_totals[0][0] if so_totals and so_totals[0][0] else 0)
		if contract_value == 0 and est:
			contract_value = flt(est.total_amount)
		self.contract_value = contract_value

		# Primary Sales Order (latest submitted)
		so_name = frappe.db.get_value(
			"Sales Order",
			{"project": self.project, "docstatus": 1},
			"name",
			order_by="modified desc",
		)
		self.sales_order = so_name

		# Progress invoiced: sum of submitted Sales Invoices for this project
		si_totals = frappe.db.sql(
			"""
			select sum(grand_total) from `tabSales Invoice`
			where project = %s and docstatus = 1
			""",
			(self.project,),
		)
		self.progress_invoiced = flt(si_totals[0][0] if si_totals and si_totals[0][0] else 0)

		# Variations total: sum of Variation total_amount for this project (approved or all)
		var_totals = frappe.db.sql(
			"""
			select sum(total_amount) from `tabVariation`
			where project = %s and status = 'Approved'
			""",
			(self.project,),
		)
		self.variations_total = flt(var_totals[0][0] if var_totals and var_totals[0][0] else 0)

		# Remaining to bill (contract + variations - invoiced)
		self.remaining_to_bill = self.contract_value + self.variations_total - self.progress_invoiced
		if self.remaining_to_bill < 0:
			self.remaining_to_bill = 0

		self.save(ignore_permissions=True)
		frappe.db.commit()
