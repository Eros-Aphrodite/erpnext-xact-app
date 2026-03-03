# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 220},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Data", "width": 160},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "width": 80},
	]
	project = filters.get("project")
	currency = frappe.defaults.get_defaults().get("currency") or "AUD"

	# Open estimates count (Draft + Quoted)
	est_conds = ["coalesce(ce.total_amount, 0) > 0", "ce.status in ('Draft', 'Quoted')"]
	est_params = {}
	if project:
		est_conds.append("ce.project = %(project)s")
		est_params["project"] = project
	open_est = frappe.db.sql(
		"select count(*) as c from `tabConstruction Estimate` ce where " + " and ".join(est_conds),
		est_params,
		as_dict=True,
	)[0].c or 0

	# Pipeline value (Quoted + Won total amount)
	pipe_conds = ["coalesce(ce.total_amount, 0) > 0", "ce.status in ('Quoted', 'Won')"]
	pipe_params = {}
	if project:
		pipe_conds.append("ce.project = %(project)s")
		pipe_params["project"] = project
	pipe_row = frappe.db.sql(
		"select sum(ce.total_amount) as total from `tabConstruction Estimate` ce where " + " and ".join(pipe_conds),
		pipe_params,
		as_dict=True,
	)[0]
	pipeline_value = flt(pipe_row and pipe_row.total)

	# WIP: remaining to bill (contract value - progress invoiced) from projects with SO/estimate
	wip_conds = ["(so_totals.contract_value > 0 OR est_totals.est_total > 0)"]
	wip_params = {}
	if project:
		wip_conds.append("p.name = %(project)s")
		wip_params["project"] = project
	wip_sql = """
		select
			coalesce(sum(coalesce(so_totals.contract_value, est_totals.est_total, 0) - coalesce(si_totals.invoiced, 0)), 0) as wip
		from `tabProject` p
		left join (
			select project, sum(grand_total) as contract_value from `tabSales Order` where docstatus = 1 group by project
		) so_totals on so_totals.project = p.name
		left join (
			select project, sum(total_amount) as est_total from `tabConstruction Estimate` where status = 'Won' group by project
		) est_totals on est_totals.project = p.name
		left join (
			select project, sum(grand_total) as invoiced from `tabSales Invoice` where docstatus = 1 group by project
		) si_totals on si_totals.project = p.name
		where """ + " and ".join(wip_conds)
	wip_row = frappe.db.sql(wip_sql, wip_params, as_dict=True)[0]
	wip_value = flt(wip_row and wip_row.wip)
	# Only positive remaining
	wip_value = max(0, wip_value)

	# Active jobs count (projects with Job or with CE/SO)
	job_conds = ["1=1"]
	job_params = {}
	if project:
		job_conds.append("j.project = %(project)s")
		job_params["project"] = project
	job_count = frappe.db.sql(
		"select count(distinct j.project) as c from `tabJob` j where " + " and ".join(job_conds),
		job_params,
		as_dict=True,
	)[0].c or 0
	if not project:
		# When no filter, count all jobs
		job_count = frappe.db.sql("select count(*) as c from `tabJob` j", as_dict=True)[0].c or 0

	# Overdue invoices
	overdue_conds = ["si.docstatus = 1", "si.outstanding_amount > 0", "si.due_date < %(today)s"]
	overdue_params = {"today": getdate(today())}
	if project:
		overdue_conds.append("si.project = %(project)s")
		overdue_params["project"] = project
	overdue_rows = frappe.db.sql(
		"select count(*) as cnt, sum(si.outstanding_amount) as amt from `tabSales Invoice` si where " + " and ".join(overdue_conds),
		overdue_params,
		as_dict=True,
	)[0]
	overdue_count = overdue_rows.cnt or 0
	overdue_amount = flt(overdue_rows and overdue_rows.amt)

	# Format for display (Buildxact-style "Know your numbers")
	def fmt_curr(amount):
		return frappe.format_value(amount, "Currency", currency) if amount is not None else "0.00"

	data = [
		{"metric": _("Open quotes (Draft + Quoted)"), "value": str(open_est), "currency": ""},
		{"metric": _("Pipeline value (Quoted + Won)"), "value": fmt_curr(pipeline_value), "currency": currency},
		{"metric": _("WIP – remaining to bill"), "value": fmt_curr(wip_value), "currency": currency},
		{"metric": _("Active jobs"), "value": str(job_count), "currency": ""},
		{"metric": _("Overdue invoices (count)"), "value": str(overdue_count), "currency": ""},
		{"metric": _("Overdue amount"), "value": fmt_curr(overdue_amount), "currency": currency},
	]
	return columns, data
