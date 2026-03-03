# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = [
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 140},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 80},
		{"label": _("Budget Total"), "fieldname": "budget_total", "fieldtype": "Currency", "width": 140},
	]
	rows = frappe.db.sql(
		"""
		select stage, count(*) as count, sum(coalesce(budget_amount, 0)) as budget_total
		from `tabConstruction Lead`
		group by stage
		order by field(stage, 'New', 'Contacted', 'Quote Sent', 'Under Review', 'Won', 'Lost')
		""",
		as_dict=True,
	)
	data = [{"stage": r.stage or "New", "count": r.count, "budget_total": flt(r.budget_total)} for r in rows]
	if data:
		data.append({
			"stage": _("Total"),
			"count": sum(d["count"] for d in data),
			"budget_total": sum(flt(d["budget_total"]) for d in data),
		})
	return columns, data
