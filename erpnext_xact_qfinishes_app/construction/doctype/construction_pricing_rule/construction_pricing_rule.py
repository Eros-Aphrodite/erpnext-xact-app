# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ConstructionPricingRule(Document):
	"""Margin and allowance rules by cost code / trade for estimates and quotations."""
	pass


@frappe.whitelist()
def get_margin_for_line(cost_code=None, trade=None, as_of_date=None):
	"""Return applicable margin % and allowance % for a cost code / trade. Used when building rates."""
	date = frappe.utils.getdate(as_of_date) if as_of_date else frappe.utils.getdate()
	rules = frappe.get_all(
		"Construction Pricing Rule",
		filters={"enabled": 1},
		fields=["name", "cost_code", "trade", "margin_percent", "allowance_percent", "applicable_from", "applicable_to"],
	)
	margin = 0.0
	allowance = 0.0
	for r in rules:
		if r.get("applicable_from") and date < r.applicable_from:
			continue
		if r.get("applicable_to") and date > r.applicable_to:
			continue
		if r.get("cost_code") and r.cost_code != cost_code:
			continue
		if r.get("trade") and (trade or "").strip() and r.trade != trade:
			continue
		margin = r.get("margin_percent") or 0
		allowance = r.get("allowance_percent") or 0
		break
	return {"margin_percent": margin, "allowance_percent": allowance}
