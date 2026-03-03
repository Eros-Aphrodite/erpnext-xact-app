# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Sales Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 130},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
	]
	project = filters.get("project")
	customer = filters.get("customer")

	conditions = [
		"si.docstatus = 1",
		"si.outstanding_amount > 0",
		"si.due_date < %(today)s",
	]
	params = {"today": getdate(today())}
	if project:
		params["project"] = project
		conditions.append("si.project = %(project)s")
	if customer:
		params["customer"] = customer
		conditions.append("si.customer = %(customer)s")

	rows = frappe.db.sql(
		f"""
		select
			si.name,
			si.customer,
			si.project,
			si.posting_date,
			si.due_date,
			si.grand_total,
			si.outstanding_amount,
			DATEDIFF(%(today)s, si.due_date) as days_overdue
		from `tabSales Invoice` si
		where { " and ".join(conditions) }
		order by si.due_date asc
		""",
		params,
		as_dict=True,
	)
	data = [
		{
			"name": r.name,
			"customer": r.customer,
			"project": r.project,
			"posting_date": r.posting_date,
			"due_date": r.due_date,
			"grand_total": flt(r.grand_total),
			"outstanding_amount": flt(r.outstanding_amount),
			"days_overdue": r.days_overdue or 0,
		}
		for r in rows
	]
	if data:
		data.append({
			"name": "",
			"customer": "",
			"project": _("Total"),
			"posting_date": None,
			"due_date": None,
			"grand_total": sum(flt(d["grand_total"]) for d in data if d.get("name")),
			"outstanding_amount": sum(flt(d["outstanding_amount"]) for d in data if d.get("name")),
			"days_overdue": None,
		})
	return columns, data
