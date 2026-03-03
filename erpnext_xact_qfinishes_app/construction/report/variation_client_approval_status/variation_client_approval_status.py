# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Variation"), "fieldname": "name", "fieldtype": "Link", "options": "Variation", "width": 120},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 200},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Client Approval"), "fieldname": "client_approval_status", "fieldtype": "Data", "width": 120},
		{"label": _("Client Approved On"), "fieldname": "client_approved_date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Client Comment"), "fieldname": "client_comment", "fieldtype": "Data", "width": 200},
	]
	conditions = ["1=1"]
	values = {}
	if filters.get("project"):
		conditions.append("v.project = %(project)s")
		values["project"] = filters["project"]
	if filters.get("client_approval_status"):
		conditions.append("v.client_approval_status = %(client_approval_status)s")
		values["client_approval_status"] = filters["client_approval_status"]
	q = """
		select v.name, v.project, v.title, v.total_amount, v.status,
			v.client_approval_status, v.client_approved_date, v.client_comment
		from `tabVariation` v
		where """ + " and ".join(conditions) + """
		order by v.modified desc
	"""
	data = frappe.db.sql(q, values, as_dict=True)
	# Ensure client_approval_status shows Pending when null
	for row in data:
		if not row.get("client_approval_status"):
			row["client_approval_status"] = "Pending"
	return columns, data
