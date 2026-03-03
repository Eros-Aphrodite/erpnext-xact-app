# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": _("Estimated"), "fieldname": "estimated", "fieldtype": "Currency", "width": 120},
		{"label": _("Variations"), "fieldname": "variations", "fieldtype": "Currency", "width": 110},
		{"label": _("Budget"), "fieldname": "budget", "fieldtype": "Currency", "width": 120},
		{"label": _("Committed (PO)"), "fieldname": "committed", "fieldtype": "Currency", "width": 120},
		{"label": _("Actual (Purchase)"), "fieldname": "actual_purchase", "fieldtype": "Currency", "width": 140},
		{"label": _("Actual (Labour)"), "fieldname": "actual_labour", "fieldtype": "Currency", "width": 130},
		{"label": _("Actual (Job Expense)"), "fieldname": "actual_job_expense", "fieldtype": "Currency", "width": 150},
		{"label": _("Actual Total"), "fieldname": "actual_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 120},
	]
	project = filters.get("project")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	# By-project aggregates (reuse job costing logic but group by project)
	est = _estimated_by_project(project, from_date, to_date)
	var = _variations_by_project(project, from_date, to_date)
	comm = _committed_by_project(project, from_date, to_date)
	act_p = _actual_purchase_by_project(project, from_date, to_date)
	act_l = _actual_labour_by_project(project, from_date, to_date)
	act_je = _actual_job_expense_by_project(project, from_date, to_date)

	projects = set(est) | set(var) | set(comm) | set(act_p) | set(act_l) | set(act_je)
	data = []
	for proj in sorted(projects, key=lambda x: (x is None, x or "")):
		e = flt(est.get(proj))
		v = flt(var.get(proj))
		budget = e + v
		c = flt(comm.get(proj))
		ap = flt(act_p.get(proj))
		al = flt(act_l.get(proj))
		aje = flt(act_je.get(proj))
		actual_total = ap + al + aje
		variance = budget - actual_total
		data.append({
			"project": proj,
			"estimated": e,
			"variations": v,
			"budget": budget,
			"committed": c,
			"actual_purchase": ap,
			"actual_labour": al,
			"actual_job_expense": aje,
			"actual_total": actual_total,
			"variance": variance,
		})
	return columns, data


def _date_conds(field, from_date, to_date, params):
	conds = []
	if from_date:
		params["from_date"] = getdate(from_date)
		conds.append(f"{field} >= %(from_date)s")
	if to_date:
		params["to_date"] = getdate(to_date)
		conds.append(f"{field} <= %(to_date)s")
	return conds


def _estimated_by_project(project, from_date, to_date):
	params = {}
	conds = ["coalesce(ce.total_amount, 0) > 0"]
	if project:
		params["project"] = project
		conds.append("ce.project = %(project)s")
	conds.extend(_date_conds("ce.transaction_date", from_date, to_date, params))
	rows = frappe.db.sql(
		"select ce.project, sum(ce.total_amount) as amt from `tabConstruction Estimate` ce where " + " and ".join(conds) + " group by ce.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}


def _variations_by_project(project, from_date, to_date):
	params = {}
	conds = ["v.status = 'Approved'"]
	if project:
		params["project"] = project
		conds.append("v.project = %(project)s")
	conds.extend(_date_conds("v.transaction_date", from_date, to_date, params))
	rows = frappe.db.sql(
		"select v.project, sum(v.total_amount) as amt from `tabVariation` v where " + " and ".join(conds) + " group by v.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}


def _committed_by_project(project, from_date, to_date):
	params = {}
	conds = ["po.docstatus = 1"]
	if project:
		params["project"] = project
		conds.append("poi.project = %(project)s")
	conds.extend(_date_conds("po.transaction_date", from_date, to_date, params))
	rows = frappe.db.sql(
		"""
		select poi.project, sum(coalesce(poi.base_net_amount, poi.base_amount, poi.amount, 0)) as amt
		from `tabPurchase Order Item` poi
		inner join `tabPurchase Order` po on po.name = poi.parent
		where """ + " and ".join(conds) + " group by poi.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}


def _actual_purchase_by_project(project, from_date, to_date):
	params = {}
	conds = ["pi.docstatus = 1"]
	if project:
		params["project"] = project
		conds.append("pii.project = %(project)s")
	conds.extend(_date_conds("pi.posting_date", from_date, to_date, params))
	rows = frappe.db.sql(
		"""
		select pii.project, sum(coalesce(pii.base_net_amount, pii.base_amount, pii.amount, 0)) as amt
		from `tabPurchase Invoice Item` pii
		inner join `tabPurchase Invoice` pi on pi.name = pii.parent
		where """ + " and ".join(conds) + " group by pii.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}


def _actual_labour_by_project(project, from_date, to_date):
	params = {}
	conds = ["ts.docstatus = 1"]
	if project:
		params["project"] = project
		conds.append("tdd.project = %(project)s")
	conds.extend(_date_conds("date(tdd.from_time)", from_date, to_date, params))
	rows = frappe.db.sql(
		"""
		select tdd.project, sum(coalesce(tdd.base_costing_amount, tdd.costing_amount, 0)) as amt
		from `tabTimesheet Detail` tdd
		inner join `tabTimesheet` ts on ts.name = tdd.parent
		where """ + " and ".join(conds) + " group by tdd.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}


def _actual_job_expense_by_project(project, from_date, to_date):
	params = {}
	conds = ["1=1"]
	if project:
		params["project"] = project
		conds.append("je.project = %(project)s")
	conds.extend(_date_conds("je.posting_date", from_date, to_date, params))
	rows = frappe.db.sql(
		"""
		select je.project, sum(coalesce(je.amount, 0)) as amt
		from `tabJob Expense` je
		where """ + " and ".join(conds) + " group by je.project",
		params,
		as_dict=True,
	)
	return {r.project: r.amt for r in rows}
