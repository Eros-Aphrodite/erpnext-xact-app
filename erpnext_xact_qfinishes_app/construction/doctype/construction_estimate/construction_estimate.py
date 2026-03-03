# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import ast
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, now_datetime


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


def _get_customer_email(customer: str) -> str | None:
	"""First contact email for the customer."""
	if not customer:
		return None
	email = frappe.db.get_value(
		"Contact",
		{"link_doctype": "Customer", "link_name": customer, "email_id": ["!=", ""]},
		"email_id",
		order_by="creation desc",
	)
	return email


@frappe.whitelist()
def send_quote_to_client(estimate_name: str, recipient_email: str = None) -> dict:
	"""
	Generate a share link for the estimate, set quote_sent_at, and optionally email the link.
	Returns the view link and whether email was sent.
	"""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	key = estimate.get_document_share_key(no_expiry=True)
	frappe.db.set_value(
		"Construction Estimate", estimate_name, "quote_sent_at", now_datetime(), update_modified=False
	)
	frappe.db.commit()
	site_url = frappe.utils.get_url()
	view_link = f"{site_url}/view_quote?doctype=Construction Estimate&name={estimate_name}&key={key}"
	email_sent = False
	to_email = recipient_email or _get_customer_email(estimate.customer)
	if to_email:
		try:
			frappe.sendmail(
				recipients=[to_email],
				subject=_("Quote from {0}").format(estimate.title or estimate_name),
				message=_("Please view your quote at: {0}").format(view_link),
				reference_doctype="Construction Estimate",
				reference_name=estimate_name,
			)
			email_sent = True
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Send quote to client")
	return {"view_link": view_link, "email_sent": email_sent}


def validate_quote_key(doctype: str, name: str, key: str) -> bool:
	"""Validate Document Share Key for the estimate. Returns True if valid."""
	if not key or not doctype or not name:
		return False
	from frappe.core.doctype.document_share_key.document_share_key import is_expired
	expires_on = frappe.db.get_value(
		"Document Share Key",
		{"reference_doctype": doctype, "reference_docname": name, "key": key},
		"expires_on",
	)
	if expires_on is None:
		return False
	if is_expired(expires_on):
		return False
	return True


@frappe.whitelist(allow_guest=True)
def accept_quote(doctype: str, name: str, key: str) -> dict:
	"""Client accepts the quote (from view_quote page). Creates Quotation and links it."""
	if not validate_quote_key(doctype, name, key):
		frappe.throw(_("Invalid or expired link."), frappe.PermissionError)
	estimate = frappe.get_doc("Construction Estimate", name)
	if estimate.get("quote_accepted_at"):
		return {"ok": True, "message": _("Already accepted"), "quotation_ref": estimate.quotation_ref}
	frappe.db.set_value(
		"Construction Estimate", name, "quote_accepted_at", now_datetime(), update_modified=False
	)
	quotation_name = make_quotation(name)
	frappe.db.commit()
	_notify_builder_on_quote_accepted(name, quotation_name)
	return {"ok": True, "quotation_ref": quotation_name}


def _notify_builder_on_quote_accepted(estimate_name: str, quotation_name: str) -> None:
	"""In-app notification when client accepts quote."""
	try:
		doc = frappe.get_doc("Construction Estimate", estimate_name)
		recipients = [doc.owner]
		if doc.owner == "Administrator":
			recipients = frappe.get_all(
				"Has Role",
				filters={"role": ["in", ["System Manager", "Projects Manager", "Projects User"]]},
				pluck="parent",
				limit=5,
			) or []
		if not recipients:
			return
		subject = _("Quote {0} accepted by client → Quotation {1}").format(estimate_name, quotation_name)
		notification_doc = {
			"type": "Alert",
			"document_type": "Construction Estimate",
			"document_name": estimate_name,
			"subject": subject,
			"from_user": frappe.session.user,
		}
		from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
		enqueue_create_notification(recipients, notification_doc)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Quote accepted notification")


@frappe.whitelist()
def make_material_request(estimate_name: str) -> str:
	"""Create a Material Request (Purchase) from a Construction Estimate. Items get Cost Code and Project for job costing."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	if estimate.get("material_request_ref"):
		frappe.throw(
			frappe._("This estimate already has a Material Request: {0}. Create a new estimate or clear the link to create another.").format(
				frappe.get_desk_link("Material Request", estimate.material_request_ref)
			)
		)
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Purchase"
	mr.transaction_date = estimate.transaction_date or frappe.utils.getdate()
	if estimate.company:
		mr.company = estimate.company
	if estimate.project:
		mr.project = estimate.project
	# Required By: default to 7 days from today so procurement can plan
	schedule_date = frappe.utils.add_days(mr.transaction_date, 7)

	item_count = 0
	for row in estimate.items or []:
		if not row.get("item"):
			continue
		qty = flt(row.get("quantity") or 0)
		if qty <= 0:
			continue
		item_count += 1
		mr.append(
			"items",
			{
				"item_code": row.item,
				"description": row.description or row.section or "",
				"qty": qty,
				"uom": row.uom or frappe.db.get_value("Item", row.item, "stock_uom") or "Nos",
				"schedule_date": schedule_date,
				"project": estimate.project,
				"cost_code": row.get("cost_code"),
				"rate": row.get("cost") or row.get("rate"),
			},
		)

	if item_count == 0:
		frappe.throw(frappe._("No lines with an Item and quantity > 0. Add items to the estimate first."))

	mr.insert(ignore_permissions=True)
	mr.run_method("set_missing_values")
	frappe.db.set_value(
		"Construction Estimate", estimate_name, "material_request_ref", mr.name, update_modified=False
	)
	frappe.db.commit()
	return mr.name


def _get_supplier_for_estimate_row(row, company: str) -> str | None:
	"""Preferred supplier from row, or Item default supplier."""
	if row.get("preferred_supplier"):
		return row.preferred_supplier
	try:
		from erpnext.stock.doctype.item.item import get_item_defaults
		defaults = get_item_defaults(row.get("item"), company)
		return (defaults or {}).get("default_supplier")
	except Exception:
		return None


@frappe.whitelist()
def make_purchase_orders_by_supplier(estimate_name: str) -> list[str]:
	"""Create one Purchase Order per supplier from estimate lines. Groups by preferred_supplier (or Item default). Returns list of PO names."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	company = estimate.company or frappe.defaults.get_default("company")
	if not company:
		frappe.throw(frappe._("Set Company on the estimate or default company."))

	# Group lines by supplier: supplier -> list of (row,)
	by_supplier = {}
	no_supplier_rows = []

	for row in estimate.items or []:
		if not row.get("item"):
			continue
		qty = flt(row.get("quantity") or 0)
		if qty <= 0:
			continue
		supplier = _get_supplier_for_estimate_row(row, company)
		if not supplier:
			no_supplier_rows.append(row)
			continue
		by_supplier.setdefault(supplier, []).append(row)

	if no_supplier_rows and not by_supplier:
		frappe.throw(
			frappe._("No lines have a Preferred Supplier or Item default supplier. Set Preferred Supplier on estimate lines or set default supplier on Items.")
		)

	schedule_date = frappe.utils.add_days(estimate.transaction_date or frappe.utils.getdate(), 7)
	created = []

	for supplier, rows in by_supplier.items():
		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = company
		po.transaction_date = estimate.transaction_date or frappe.utils.getdate()
		po.schedule_date = schedule_date
		po.project = estimate.project
		if frappe.db.exists("DocType", "Purchase Order") and hasattr(po, "construction_estimate"):
			po.construction_estimate = estimate_name
		for row in rows:
			po.append(
				"items",
				{
					"item_code": row.item,
					"description": row.description or row.section or "",
					"qty": flt(row.quantity),
					"uom": row.uom or frappe.db.get_value("Item", row.item, "stock_uom") or "Nos",
					"rate": flt(row.get("cost") or row.get("rate") or 0),
					"schedule_date": schedule_date,
					"project": estimate.project,
					"cost_code": row.get("cost_code"),
				},
			)
		po.insert(ignore_permissions=True)
		po.run_method("set_missing_values")
		created.append(po.name)

	if no_supplier_rows:
		frappe.msgprint(
			frappe._("{0} line(s) have no supplier and were skipped. Add Preferred Supplier or Item default.").format(len(no_supplier_rows)),
			indicator="orange",
		)
	frappe.db.commit()
	return created


@frappe.whitelist()
def make_progress_invoice(estimate_name: str, stage_name: str, item_code: str = None) -> str:
	"""Create a Sales Invoice for one progress billing stage. Uses contract value from linked Sales Order or estimate total."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	stages = [s for s in (estimate.billing_stages or []) if s.stage_name == stage_name and not s.invoiced]
	if not stages:
		frappe.throw(
			frappe._("No uninvoiced stage named '{0}' found. Check stage name or that it is not already invoiced.").format(
				stage_name
			)
		)
	stage = stages[0]

	# Contract value: from Sales Order or estimate total
	contract_value = flt(estimate.total_amount or 0)
	if estimate.get("sales_order_ref"):
		so = frappe.db.get_value(
			"Sales Order", estimate.sales_order_ref, ["grand_total", "customer", "company", "project"], as_dict=True
		)
		if so:
			contract_value = flt(so.grand_total)
	else:
		so = None

	if contract_value <= 0:
		frappe.throw(frappe._("Contract value is zero. Link a Sales Order or ensure estimate has a total amount."))

	stage_amount = round(contract_value * flt(stage.percent or 0) / 100, 2)
	if stage_amount <= 0:
		frappe.throw(frappe._("Stage amount is zero. Check stage percent."))

	# Retention: bill only (100 - retention_percent)% of the stage amount
	retention_percent = flt(estimate.get("retention_percent") or 0)
	amount_to_bill = round(stage_amount * (1 - retention_percent / 100), 2)
	if amount_to_bill <= 0:
		frappe.throw(frappe._("Amount to bill after retention is zero. Reduce retention % or check stage percent."))

	# Item for the line: use provided item or first item from SO, or a default
	if item_code and frappe.db.exists("Item", item_code):
		line_item_code = item_code
	else:
		if so and estimate.sales_order_ref:
			first_so_item = frappe.db.get_value(
				"Sales Order Item",
				{"parent": estimate.sales_order_ref},
				"item_code",
				order_by="idx asc",
			)
			if first_so_item:
				line_item_code = first_so_item
			else:
				line_item_code = None
		else:
			line_item_code = None
	if not line_item_code:
		frappe.throw(
			frappe._("Could not determine item for progress line. Link a Sales Order with items or pass item_code.")
		)

	si = frappe.new_doc("Sales Invoice")
	si.customer = (so.get("customer") if so else None) or estimate.customer
	si.company = (so.get("company") if so else None) or estimate.company
	si.project = estimate.project
	si.posting_date = frappe.utils.getdate()
	if estimate.sales_order_ref:
		si.taxes_and_charges = frappe.db.get_value("Sales Order", estimate.sales_order_ref, "taxes_and_charges")
	si.append(
		"items",
		{
			"item_code": line_item_code,
			"qty": 1,
			"rate": amount_to_bill,
			"description": f"{stage_name} ({stage.percent}%)" + (f" (retention {retention_percent}% held)" if retention_percent else ""),
			"sales_order": estimate.sales_order_ref,
		},
	)
	si.set_missing_values()
	si.insert(ignore_permissions=True)
	si.run_method("calculate_taxes_and_totals")

	# Mark this stage row as invoiced and link SI (stage is a reference to the row)
	stage.invoiced = 1
	stage.sales_invoice = si.name
	estimate.save(ignore_permissions=True)
	frappe.db.commit()
	return si.name


def _get_contract_value_for_estimate(estimate) -> float:
	"""Contract value from Sales Order or estimate total."""
	contract_value = flt(estimate.total_amount or 0)
	if estimate.get("sales_order_ref"):
		so_total = frappe.db.get_value("Sales Order", estimate.sales_order_ref, "grand_total")
		if so_total is not None:
			contract_value = flt(so_total)
	return contract_value


@frappe.whitelist()
def get_retention_summary(estimate_name: str) -> dict:
	"""Return total retention held, released amount, and remaining to release for the estimate."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	contract_value = _get_contract_value_for_estimate(estimate)
	retention_percent = flt(estimate.get("retention_percent") or 0)
	total_held = 0.0
	for stage in estimate.billing_stages or []:
		if not stage.invoiced:
			continue
		stage_amount = contract_value * flt(stage.percent or 0) / 100
		total_held += stage_amount * retention_percent / 100
	released = 0.0
	if estimate.get("retention_release_invoice") and frappe.db.exists("Sales Invoice", estimate.retention_release_invoice):
		released = flt(frappe.db.get_value("Sales Invoice", estimate.retention_release_invoice, "grand_total"))
	return {
		"total_retention_held": round(total_held, 2),
		"retention_released_amount": round(released, 2),
		"remaining_to_release": round(total_held - released, 2),
	}


@frappe.whitelist()
def make_retention_release_invoice(estimate_name: str, item_code: str = None) -> str:
	"""Create a Sales Invoice for the released retention amount (one-off release)."""
	estimate = frappe.get_doc("Construction Estimate", estimate_name)
	if flt(estimate.get("retention_percent") or 0) <= 0:
		frappe.throw(frappe._("Estimate has no retention %. Set Retention % first."))
	summary = get_retention_summary(estimate_name)
	amount = summary["remaining_to_release"]
	if amount <= 0:
		frappe.throw(
			frappe._("No retention left to release. Total held: {0}, already released: {1}.").format(
				summary["total_retention_held"], summary["retention_released_amount"]
			)
		)
	contract_value = _get_contract_value_for_estimate(estimate)
	so = None
	if estimate.sales_order_ref:
		so = frappe.db.get_value(
			"Sales Order", estimate.sales_order_ref, ["customer", "company", "project"], as_dict=True
		)
	if not so:
		frappe.throw(frappe._("Link a Sales Order for progress billing first."))
	# Item for the line
	if item_code and frappe.db.exists("Item", item_code):
		line_item_code = item_code
	else:
		first_so_item = frappe.db.get_value(
			"Sales Order Item", {"parent": estimate.sales_order_ref}, "item_code", order_by="idx asc"
		)
		line_item_code = first_so_item or None
	if not line_item_code:
		frappe.throw(frappe._("Could not determine item. Pass item_code or ensure Sales Order has items."))
	si = frappe.new_doc("Sales Invoice")
	si.customer = so.customer
	si.company = so.company
	si.project = estimate.project
	si.posting_date = frappe.utils.getdate()
	if estimate.sales_order_ref:
		si.taxes_and_charges = frappe.db.get_value("Sales Order", estimate.sales_order_ref, "taxes_and_charges")
	si.append(
		"items",
		{
			"item_code": line_item_code,
			"qty": 1,
			"rate": amount,
			"description": frappe._("Retention release"),
			"sales_order": estimate.sales_order_ref,
		},
	)
	si.set_missing_values()
	si.insert(ignore_permissions=True)
	si.run_method("calculate_taxes_and_totals")
	frappe.db.set_value(
		"Construction Estimate", estimate_name, "retention_release_invoice", si.name, update_modified=False
	)
	frappe.db.commit()
	return si.name


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
	"""Get base cost for a line: row.cost, Construction Supplier Price (if supplier set), or Item's standard_rate/valuation_rate."""
	if row.get("cost") is not None and row.cost != 0:
		return float(row.cost)
	if not row.get("item"):
		return None
	# Dealer/supplier price list: prefer Construction Supplier Price when preferred_supplier is set
	if row.get("preferred_supplier"):
		sp = frappe.db.get_value(
			"Construction Supplier Price",
			{"item": row.item, "supplier": row.preferred_supplier},
			"rate",
		)
		if sp is not None and flt(sp) > 0:
			return float(sp)
	item = frappe.db.get_value(
		"Item",
		row.item,
		["standard_rate", "valuation_rate"],
		as_dict=True,
	)
	if not item:
		return None
	return float(item.standard_rate or item.valuation_rate or 0) or None
