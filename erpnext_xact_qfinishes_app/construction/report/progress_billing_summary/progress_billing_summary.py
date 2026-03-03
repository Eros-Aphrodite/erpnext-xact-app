# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
 columns = [
  {"label": _("Estimate"), "fieldname": "estimate", "fieldtype": "Link", "options": "Construction Estimate", "width": 140},
  {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
  {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
  {"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 120},
  {"label": _("Stage"), "fieldname": "stage_name", "fieldtype": "Data", "width": 120},
  {"label": _("Percent"), "fieldname": "percent", "fieldtype": "Percent", "width": 80},
  {"label": _("Stage Amount"), "fieldname": "stage_amount", "fieldtype": "Currency", "width": 120},
  {"label": _("Invoiced"), "fieldname": "invoiced", "fieldtype": "Check", "width": 80},
  {"label": _("Sales Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
 ]
 data = []
 estimate_filters = {}
 if filters and filters.get("project"):
  estimate_filters["project"] = filters["project"]
 estimates = frappe.get_all(
  "Construction Estimate",
  filters=estimate_filters,
  fields=["name", "customer", "project", "total_amount", "sales_order_ref"],
  order_by="modified desc",
 )
 for est in estimates:
  contract_value = flt(est.total_amount)
  if est.sales_order_ref:
   so_total = frappe.db.get_value("Sales Order", est.sales_order_ref, "grand_total")
   if so_total is not None:
    contract_value = flt(so_total)
  stages = frappe.get_all(
   "Billing Stage",
   filters={"parent": est.name, "parenttype": "Construction Estimate"},
   fields=["stage_name", "percent", "invoiced", "sales_invoice"],
   order_by="idx asc",
  )
  if not stages:
   data.append({
    "estimate": est.name,
    "customer": est.customer,
    "project": est.project,
    "contract_value": contract_value,
    "stage_name": None,
    "percent": None,
    "stage_amount": None,
    "invoiced": None,
    "sales_invoice": None,
   })
   continue
  for s in stages:
   stage_amount = round(contract_value * flt(s.percent or 0) / 100, 2) if contract_value else 0
   data.append({
    "estimate": est.name,
    "customer": est.customer,
    "project": est.project,
    "contract_value": contract_value,
    "stage_name": s.stage_name,
    "percent": s.percent,
    "stage_amount": stage_amount,
    "invoiced": s.invoiced,
    "sales_invoice": s.sales_invoice,
   })
 return columns, data
