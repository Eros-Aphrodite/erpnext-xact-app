# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"label": _("Project Name"), "fieldname": "project_name", "fieldtype": "Data", "width": 180},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 130},
		{"label": _("Progress Invoiced"), "fieldname": "progress_invoiced", "fieldtype": "Currency", "width": 140},
		{"label": _("Remaining to Bill"), "fieldname": "remaining_to_bill", "fieldtype": "Currency", "width": 140},
		{"label": _("% Invoiced"), "fieldname": "percent_invoiced", "fieldtype": "Percent", "width": 100},
	]
	# Contract value from submitted SOs; fallback to estimate total
	project_filter = " and p.name = %(project)s" if filters.get("project") else ""
	params = {"project": filters.get("project")} if filters.get("project") else {}
	rows = frappe.db.sql(
		f"""
		select
			p.name as project,
			p.project_name as project_name,
			coalesce(so_totals.contract_value, est_totals.est_total, 0) as contract_value,
			coalesce(si_totals.invoiced, 0) as progress_invoiced
		from `tabProject` p
		left join (
			select project, sum(grand_total) as contract_value
			from `tabSales Order` where docstatus = 1 group by project
		) so_totals on so_totals.project = p.name
		left join (
			select project, sum(total_amount) as est_total
			from `tabConstruction Estimate` group by project
		) est_totals on est_totals.project = p.name
		left join (
			select project, sum(grand_total) as invoiced
			from `tabSales Invoice` where docstatus = 1 group by project
		) si_totals on si_totals.project = p.name
		where coalesce(so_totals.contract_value, est_totals.est_total, 0) > 0
		{project_filter}
		order by p.name
		""",
		params,
		as_dict=True,
	)
	data = []
	for r in rows:
		contract = flt(r.contract_value)
		invoiced = flt(r.progress_invoiced)
		remaining = max(0, contract - invoiced)
		pct = (invoiced / contract * 100) if contract else 0
		data.append({
			"project": r.project,
			"project_name": r.project_name,
			"contract_value": contract,
			"progress_invoiced": invoiced,
			"remaining_to_bill": remaining,
			"percent_invoiced": round(pct, 1),
		})
	return columns, data
