# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
		{"label": _("PO Count"), "fieldname": "po_count", "fieldtype": "Int", "width": 90},
		{"label": _("PO Total"), "fieldname": "po_total", "fieldtype": "Currency", "width": 120},
		{"label": _("PI Count"), "fieldname": "pi_count", "fieldtype": "Int", "width": 90},
		{"label": _("PI Total"), "fieldname": "pi_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Spend"), "fieldname": "total_spend", "fieldtype": "Currency", "width": 120},
	]
	project = filters.get("project")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	# Construction POs: PO with construction_estimate set, or PO with project (for project filter)
	po_conds = ["po.docstatus = 1"]
	po_params = {}
	if project:
		po_conds.append("(po.project = %(project)s OR ce.project = %(project)s)")
		po_params["project"] = project
	if from_date:
		po_params["from_date"] = getdate(from_date)
		po_conds.append("po.transaction_date >= %(from_date)s")
	if to_date:
		po_params["to_date"] = getdate(to_date)
		po_params["to_date2"] = getdate(to_date)
		po_conds.append("po.transaction_date <= %(to_date2)s")

	po_join = "left join `tabConstruction Estimate` ce on ce.name = po.construction_estimate"
	if not project:
		po_conds.append("po.construction_estimate is not null and po.construction_estimate != ''")

	po_sql = f"""
		select
			po.supplier,
			count(distinct po.name) as po_count,
			sum(coalesce(po.base_net_total, po.base_grand_total, po.grand_total, 0)) as po_total
		from `tabPurchase Order` po
		{po_join}
		where { " and ".join(po_conds) }
		group by po.supplier
	"""
	po_rows = frappe.db.sql(po_sql, po_params, as_dict=True)

	# Purchase Invoices by supplier (optionally by project)
	pi_conds = ["pi.docstatus = 1"]
	pi_params = {}
	if project:
		pi_params["project"] = project
		pi_conds.append(
			"(pi.project = %(project)s or exists (select 1 from `tabPurchase Invoice Item` pii "
			"where pii.parent = pi.name and pii.project = %(project)s))"
		)
	if from_date:
		pi_params["from_date"] = getdate(from_date)
		pi_conds.append("pi.posting_date >= %(from_date)s")
	if to_date:
		pi_params["to_date"] = getdate(to_date)
		pi_conds.append("pi.posting_date <= %(to_date)s")

	pi_sql = f"""
		select
			pi.supplier,
			count(distinct pi.name) as pi_count,
			sum(coalesce(pi.base_net_total, pi.base_grand_total, pi.grand_total, 0)) as pi_total
		from `tabPurchase Invoice` pi
		where { " and ".join(pi_conds) }
		group by pi.supplier
	"""
	pi_rows = frappe.db.sql(pi_sql, pi_params, as_dict=True)

	po_by_supplier = {r.supplier: r for r in po_rows}
	pi_by_supplier = {r.supplier: r for r in pi_rows}
	# When no project filter: construction-only suppliers (from POs); when project set: PO + PI suppliers
	suppliers = set(po_by_supplier) | (set(pi_by_supplier) if project else set()) if project else set(po_by_supplier)

	data = []
	for sup in sorted(suppliers, key=lambda x: (x or "")):
		po_rec = po_by_supplier.get(sup) or frappe._dict({"po_count": 0, "po_total": 0})
		pi_rec = pi_by_supplier.get(sup) or frappe._dict({"pi_count": 0, "pi_total": 0})
		po_total = flt(po_rec.po_total)
		pi_total = flt(pi_rec.pi_total)
		supplier_name = frappe.db.get_value("Supplier", sup, "supplier_name") if sup else ""
		data.append({
			"supplier": sup,
			"supplier_name": supplier_name or "",
			"po_count": po_rec.po_count or 0,
			"po_total": po_total,
			"pi_count": pi_rec.pi_count or 0,
			"pi_total": pi_total,
			"total_spend": po_total + pi_total,
		})

	# Sort by total spend descending
	data.sort(key=lambda r: flt(r["total_spend"]), reverse=True)

	if data:
		data.append({
			"supplier": "",
			"supplier_name": _("Total"),
			"po_count": sum(d["po_count"] for d in data if d["supplier"]),
			"po_total": sum(flt(d["po_total"]) for d in data if d["supplier"]),
			"pi_count": sum(d["pi_count"] for d in data if d["supplier"]),
			"pi_total": sum(flt(d["pi_total"]) for d in data if d["supplier"]),
			"total_spend": sum(flt(d["total_spend"]) for d in data if d["supplier"]),
		})
	return columns, data
