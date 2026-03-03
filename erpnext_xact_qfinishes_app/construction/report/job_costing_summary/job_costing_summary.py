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
			"label": _("Actual (Job Expense)"),
			"fieldname": "actual_job_expense",
			"fieldtype": "Currency",
			"width": 150,
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
	committed_by_cc = get_committed_po_by_cost_code(project, from_date, to_date)
	actual_purchase_by_cc = get_actual_purchase_by_cost_code(project, from_date, to_date)
	actual_labour_by_cc = get_actual_labour_by_cost_code(project, from_date, to_date)
	actual_job_expense_by_cc = get_job_expense_by_cost_code(project, from_date, to_date)

	rows = []
	all_cost_codes = (
		set(estimated_by_cc)
		| set(variations_by_cc)
		| set(committed_by_cc)
		| set(actual_purchase_by_cc)
		| set(actual_labour_by_cc)
		| set(actual_job_expense_by_cc)
	)

	for cc in sorted(all_cost_codes, key=lambda x: (x is None, x or "")):
		trade = None
		if cc:
			trade = frappe.db.get_value("Cost Code", cc, "trade")

		estimated = flt(estimated_by_cc.get(cc))
		variations = flt(variations_by_cc.get(cc))
		budget = estimated + variations
		committed = flt(committed_by_cc.get(cc))
		actual_purchase = flt(actual_purchase_by_cc.get(cc))
		actual_labour = flt(actual_labour_by_cc.get(cc))
		actual_job_expense = flt(actual_job_expense_by_cc.get(cc))
		actual_total = actual_purchase + actual_labour + actual_job_expense
		variance = budget - actual_total if budget or actual_total else 0

		rows.append(
			{
				"cost_code": cc,
				"trade": trade,
				"estimated": estimated,
				"variations": variations,
				"budget": budget,
				"committed": committed,
				"actual_purchase": actual_purchase,
				"actual_labour": actual_labour,
				"actual_job_expense": actual_job_expense,
				"actual_total": actual_total,
				"variance": variance,
			}
		)

	# Totals row across all cost codes
	total_estimated = sum(flt(v) for v in estimated_by_cc.values())
	total_variations = sum(flt(v) for v in variations_by_cc.values())
	total_budget = total_estimated + total_variations
	total_committed = sum(flt(v) for v in committed_by_cc.values())
	total_actual_purchase = sum(flt(v) for v in actual_purchase_by_cc.values())
	total_actual_labour = sum(flt(v) for v in actual_labour_by_cc.values())
	total_actual_job_expense = sum(flt(v) for v in actual_job_expense_by_cc.values())
	total_actual = total_actual_purchase + total_actual_labour + total_actual_job_expense

	rows.append({})
	rows.append(
		{
			"cost_code": _("TOTAL"),
			"trade": "",
			"estimated": total_estimated,
			"variations": total_variations,
			"budget": total_budget,
			"committed": total_committed,
			"actual_purchase": total_actual_purchase,
			"actual_labour": total_actual_labour,
			"actual_job_expense": total_actual_job_expense,
			"actual_total": total_actual,
			"variance": total_budget - total_actual,
		}
	)

	return rows


def base_date_conditions(field, from_date, to_date, params):
	conditions = []
	if from_date:
		conditions.append(f"{field} >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append(f"{field} <= %(to_date)s")
		params["to_date"] = getdate(to_date)
	return conditions


def get_estimated_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["ce.project = %(project)s"]
	params = {"project": project}
	conditions.extend(base_date_conditions("ce.transaction_date", from_date, to_date, params))

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
	conditions.extend(base_date_conditions("v.transaction_date", from_date, to_date, params))

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


def get_committed_po_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["poi.project = %(project)s", "po.docstatus = 1"]
	params = {"project": project}
	conditions.extend(base_date_conditions("po.transaction_date", from_date, to_date, params))

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			poi.cost_code as cost_code,
			sum(
				coalesce(poi.base_net_amount, poi.base_amount, poi.net_amount, poi.amount, 0)
			) as total
		from `tabPurchase Order Item` poi
		inner join `tabPurchase Order` po on po.name = poi.parent
		where {where}
		group by poi.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.total) for r in rows}


def get_actual_purchase_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["pii.project = %(project)s", "pi.docstatus = 1"]
	params = {"project": project}
	conditions.extend(base_date_conditions("pi.posting_date", from_date, to_date, params))

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			pii.cost_code as cost_code,
			sum(
				coalesce(pii.base_net_amount, pii.base_amount, pii.net_amount, pii.amount, 0)
			) as total
		from `tabPurchase Invoice Item` pii
		inner join `tabPurchase Invoice` pi on pi.name = pii.parent
		where {where}
		group by pii.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.total) for r in rows}


def get_actual_labour_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["tdd.project = %(project)s", "ts.docstatus = 1"]
	params = {"project": project}
	# Timesheet Detail doesn't have a separate posting date; use from_time
	conditions.extend(base_date_conditions("date(tdd.from_time)", from_date, to_date, params))

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			tdd.cost_code as cost_code,
			sum(coalesce(tdd.base_costing_amount, tdd.costing_amount, 0)) as total
		from `tabTimesheet Detail` tdd
		inner join `tabTimesheet` ts on ts.name = tdd.parent
		where {where}
		group by tdd.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.total) for r in rows}


def get_job_expense_by_cost_code(project, from_date=None, to_date=None):
	conditions = ["je.project = %(project)s"]
	params = {"project": project}
	conditions.extend(base_date_conditions("je.posting_date", from_date, to_date, params))

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			je.cost_code as cost_code,
			sum(coalesce(je.amount, 0)) as total
		from `tabJob Expense` je
		where {where}
		group by je.cost_code
		""",
		params,
		as_dict=True,
	)
	return {r.cost_code: flt(r.total) for r in rows}
