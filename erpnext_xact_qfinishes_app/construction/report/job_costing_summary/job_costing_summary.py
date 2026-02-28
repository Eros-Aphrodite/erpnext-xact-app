# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Cost Code"),
			"fieldname": "cost_code",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Trade"),
			"fieldname": "trade",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Estimated"),
			"fieldname": "estimated",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Variations (Approved)"),
			"fieldname": "variations",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Budget (Est + Var)"),
			"fieldname": "budget",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Committed (PO)"),
			"fieldname": "committed",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Actual (Purchase)"),
			"fieldname": "actual_purchase",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Actual (Labour)"),
			"fieldname": "actual_labour",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Actual (Total)"),
			"fieldname": "actual_total",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Variance (Budget - Actual)"),
			"fieldname": "variance",
			"fieldtype": "Currency",
			"width": 190,
		},
	]


def get_data(filters):
	project = filters.get("project")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	estimated_by_cc = get_estimated_by_cost_code(project, from_date, to_date)
	variations_by_cc = get_variations_by_cost_code(project, from_date, to_date)

	# These are project-level totals (ERPNext PO/PI/Timesheet lines do not carry Cost Code)
	committed = get_committed_po_total(project, from_date, to_date)
	actual_purchase = get_actual_purchase_total(project, from_date, to_date)
	actual_labour = get_actual_labour_total(project, from_date, to_date)
	actual_total = flt(actual_purchase) + flt(actual_labour)

	cost_codes = set(estimated_by_cc) | set(variations_by_cc)
	rows = []

	for cc in sorted(cost_codes, key=lambda x: (x is None, x or "")):
		trade = None
		if cc:
			trade = frappe.db.get_value("Cost Code", cc, "trade")

		estimated = flt(estimated_by_cc.get(cc))
		variations = flt(variations_by_cc.get(cc))
		budget = estimated + variations

		rows.append(
			{
				"cost_code": cc,
				"trade": trade,
				"estimated": estimated,
				"variations": variations,
				"budget": budget,
				"committed": None,
				"actual_purchase": None,
				"actual_labour": None,
				"actual_total": None,
				"variance": None,
			}
		)

	# Totals row (shows committed/actual at project level)
	total_estimated = sum(flt(v) for v in estimated_by_cc.values())
	total_variations = sum(flt(v) for v in variations_by_cc.values())
	total_budget = total_estimated + total_variations

	rows.append({})
	rows.append(
		{
			"cost_code": _("TOTAL"),
			"trade": "",
			"estimated": total_estimated,
			"variations": total_variations,
			"budget": total_budget,
			"committed": committed,
			"actual_purchase": actual_purchase,
			"actual_labour": actual_labour,
			"actual_total": actual_total,
			"variance": flt(total_budget) - flt(actual_total),
		}
	)

	rows.append(
		{
			"cost_code": "",
			"trade": _("Committed/Actual are project totals (no cost-code split yet)."),
			"estimated": None,
			"variations": None,
			"budget": None,
			"committed": None,
			"actual_purchase": None,
			"actual_labour": None,
			"actual_total": None,
			"variance": None,
		}
	)

	return rows


def get_estimated_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["ce.project = %(project)s"]
	params = {"project": project}
	if from_date:
		conditions.append("ce.transaction_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("ce.transaction_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			cei.cost_code as cost_code,
			sum(coalesce(cei.amount, 0)) as amount
		from `tabConstruction Estimate Item` cei
		inner join `tabConstruction Estimate` ce on ce.name = cei.parent
		where {where}
		group by cei.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.amount) for r in rows}


def get_variations_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["v.project = %(project)s", "v.status = 'Approved'"]
	params = {"project": project}
	if from_date:
		conditions.append("v.transaction_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("v.transaction_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			vi.cost_code as cost_code,
			sum(coalesce(vi.amount, 0)) as amount
		from `tabVariation Item` vi
		inner join `tabVariation` v on v.name = vi.parent
		where {where}
		group by vi.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.amount) for r in rows}


def get_committed_po_total(project, from_date=None, to_date=None):
	conditions = ["poi.project = %(project)s", "po.docstatus = 1"]
	params = {"project": project}
	if from_date:
		conditions.append("po.transaction_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("po.transaction_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where = " and ".join(conditions)
	res = frappe.db.sql(
		f"""
		select
			sum(
				coalesce(poi.base_net_amount, poi.base_amount, poi.net_amount, poi.amount, 0)
			) as total
		from `tabPurchase Order Item` poi
		inner join `tabPurchase Order` po on po.name = poi.parent
		where {where}
		""",
		params,
		as_dict=True,
	)
	return flt(res[0].total) if res else 0


def get_actual_purchase_total(project, from_date=None, to_date=None):
	conditions = ["pii.project = %(project)s", "pi.docstatus = 1"]
	params = {"project": project}
	if from_date:
		conditions.append("pi.posting_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("pi.posting_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where = " and ".join(conditions)
	res = frappe.db.sql(
		f"""
		select
			sum(
				coalesce(pii.base_net_amount, pii.base_amount, pii.net_amount, pii.amount, 0)
			) as total
		from `tabPurchase Invoice Item` pii
		inner join `tabPurchase Invoice` pi on pi.name = pii.parent
		where {where}
		""",
		params,
		as_dict=True,
	)
	return flt(res[0].total) if res else 0


def get_actual_labour_total(project, from_date=None, to_date=None):
	conditions = ["tdd.project = %(project)s", "ts.docstatus = 1"]
	params = {"project": project}
	if from_date:
		conditions.append("date(tdd.from_time) >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("date(tdd.from_time) <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where = " and ".join(conditions)
	res = frappe.db.sql(
		f"""
		select
			sum(coalesce(tdd.base_costing_amount, tdd.costing_amount, 0)) as total
		from `tabTimesheet Detail` tdd
		inner join `tabTimesheet` ts on ts.name = tdd.parent
		where {where}
		""",
		params,
		as_dict=True,
	)
	return flt(res[0].total) if res else 0
