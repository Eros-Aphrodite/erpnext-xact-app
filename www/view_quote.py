# Copyright (c) 2026, Q Finishes and contributors
# Public page: view quote via share link (track viewed, optional Accept)

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	doctype = frappe.form_dict.get("doctype")
	name = frappe.form_dict.get("name")
	key = frappe.form_dict.get("key")
	context.valid = False
	context.estimate = None
	context.key = key
	context.doctype = doctype
	context.name = name
	if not doctype or not name or not key:
		context.error = _("Missing link parameters.")
		return context
	if doctype != "Construction Estimate":
		context.error = _("Invalid document type.")
		return context
	from erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate import (
		validate_quote_key,
	)
	if not validate_quote_key(doctype, name, key):
		context.error = _("Invalid or expired link.")
		return context
	estimate = frappe.get_doc("Construction Estimate", name)
	context.estimate = estimate
	context.valid = True
	# Track first view
	if not estimate.get("quote_viewed_at"):
		frappe.db.set_value(
			"Construction Estimate", name, "quote_viewed_at", frappe.utils.now_datetime(), update_modified=False
		)
		frappe.db.commit()
	context.already_accepted = bool(estimate.get("quote_accepted_at"))
	context.currency = estimate.currency or frappe.defaults.get_defaults().get("currency") or "AUD"
	return context
