# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = [
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 80},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 140},
	]
	rows = frappe.db.sql(
		"""
		select status, count(*) as count, sum(coalesce(total_amount, 0)) as total_amount
		from `tabConstruction Estimate`
		where coalesce(total_amount, 0) > 0
		group by status
		order by field(status, 'Won', 'Quoted', 'Draft', 'Lost')
		""",
		as_dict=True,
	)
	data = [{"status": r.status or "Draft", "count": r.count, "total_amount": flt(r.total_amount)} for r in rows]
	if data:
		total_count = sum(d["count"] for d in data)
		total_amt = sum(flt(d["total_amount"]) for d in data)
		data.append({"status": _("Total Pipeline"), "count": total_count, "total_amount": total_amt})
	return columns, data
