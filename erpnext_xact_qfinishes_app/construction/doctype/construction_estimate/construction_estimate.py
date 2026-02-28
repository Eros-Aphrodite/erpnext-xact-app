# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import ast
import frappe
from frappe.model.document import Document


def _safe_eval_qty(expr: str, length: float = 0, width: float = 0, height: float = 0) -> float:
	"""Safely evaluate a quantity expression. Only allows length, width, height and basic math."""
	if not expr or not expr.strip():
		return 0.0
	expr = expr.strip()
	ns = {"length": float(length or 0), "width": float(width or 0), "height": float(height or 0)}
	try:
		tree = ast.parse(expr, mode="eval")
		for node in ast.walk(tree):
			if isinstance(node, ast.Name) and node.id not in ("length", "width", "height"):
				frappe.throw(f"Invalid variable '{node.id}' in expression. Use only length, width, height.")
			if isinstance(node, ast.Call):
				frappe.throw("Function calls are not allowed in quantity expressions.")
		return float(eval(compile(tree, "<qty>", "eval"), {"__builtins__": {}}, ns))
	except SyntaxError as e:
		frappe.throw(f"Invalid expression: {e}")
	except Exception as e:
		frappe.throw(f"Error evaluating expression: {e}")


class ConstructionEstimate(Document):
	def validate(self):
		self._recompute_totals()

	def _recompute_totals(self):
		total_qty = 0.0
		total_amount = 0.0
		for row in self.items or []:
			row.amount = (row.quantity or 0) * (row.rate or 0)
			total_qty += row.quantity or 0
			total_amount += row.amount or 0
		self.total_qty = total_qty
		self.total_amount = total_amount


@frappe.whitelist()
def make_quotation(estimate_name: str) -> str:
	"""Create an ERPNext Quotation from a Construction Estimate. Returns the name of the created Quotation."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	quotation = frappe.new_doc("Quotation")
	quotation.quotation_to = "Customer"
	quotation.party_name = estimate.customer
	if estimate.company:
		quotation.company = estimate.company
	quotation.transaction_date = estimate.transaction_date or frappe.utils.getdate()

	for row in estimate.items or []:
		if not row.get("include_in_quotation"):
			continue
		if not row.get("item") and not row.get("description"):
			continue
		quotation.append(
			"items",
			{
				"item_code": row.item,
				"description": row.description or row.section or "",
				"qty": row.quantity or 0,
				"uom": row.uom,
				"rate": row.rate or 0,
			},
		)

	quotation.insert(ignore_permissions=True)
	quotation.run_method("set_missing_values")
	remarks = (quotation.remarks or "") + f"\n\nSource Estimate: {estimate.name}"
	frappe.db.set_value("Quotation", quotation.name, "remarks", remarks.strip(), update_modified=False)
	frappe.db.set_value("Construction Estimate", estimate_name, "quotation_ref", quotation.name, update_modified=False)
	frappe.db.set_value("Construction Estimate", estimate_name, "status", "Quoted", update_modified=False)
	frappe.db.commit()
	return quotation.name


@frappe.whitelist()
def expand_assembly(estimate_name: str, assembly_template: str, section: str = "", quantity: float = 1.0):
	"""Append estimate lines from an Assembly Template. quantity = multiplier for qty_per_unit."""
	template = frappe.get_doc("Assembly Template", assembly_template)
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	for row in template.items or []:
		estimate.append(
			"items",
			{
				"section": section or template.template_name,
				"cost_code": row.cost_code or template.cost_code,
				"assembly_template": assembly_template,
				"item": row.item,
				"description": row.description,
				"quantity": (row.qty_per_unit or 0) * (quantity or 1),
				"uom": row.uom,
				"include_in_quotation": 1,
			},
		)
	estimate.run_method("validate")
	estimate.save(ignore_permissions=True)
	return estimate.name


@frappe.whitelist()
def calculate_quantities(estimate_name: str) -> str:
	"""Evaluate qty_expression for each line and set quantity. Returns estimate name."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	for row in estimate.items or []:
		if not row.get("qty_expression"):
			continue
		qty = _safe_eval_qty(
			row.qty_expression,
			row.get("length"),
			row.get("width"),
			row.get("height"),
		)
		row.quantity = max(0, qty)
	estimate.run_method("validate")
	estimate.save(ignore_permissions=True)
	return estimate.name


@frappe.whitelist()
def recalculate_rates(estimate_name: str) -> str:
	"""Apply Construction Pricing Rule margins to each line. Returns estimate name."""
	from erpnext_xact_qfinishes_app.construction.doctype.construction_pricing_rule.construction_pricing_rule import (
		get_margin_for_line,
	)

	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	as_of = estimate.transaction_date or frappe.utils.getdate()

	for row in estimate.items or []:
		cost = get_line_cost(row)
		if cost is None:
			continue
		trade = None
		if row.get("cost_code"):
			trade = frappe.db.get_value("Cost Code", row.cost_code, "trade")
		m = get_margin_for_line(cost_code=row.cost_code, trade=trade, as_of_date=as_of)
		margin = (m.get("margin_percent") or 0) / 100
		allowance = (m.get("allowance_percent") or 0) / 100
		row.rate = cost * (1 + margin + allowance)

	estimate.run_method("validate")
	estimate.save(ignore_permissions=True)
	return estimate.name


def get_line_cost(row):
	"""Get base cost for a line: row.cost or Item's standard_rate/valuation_rate."""
	if row.get("cost") is not None and row.cost != 0:
		return float(row.cost)
	if not row.get("item"):
		return None
	item = frappe.db.get_value(
		"Item",
		row.item,
		["standard_rate", "valuation_rate"],
		as_dict=True,
	)
	if not item:
		return None
	return float(item.standard_rate or item.valuation_rate or 0) or None
