"""Add Construction Lead link on Construction Estimate (for estimates created from lead)."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Construction Estimate": [
			{
				"fieldname": "construction_lead",
				"fieldtype": "Link",
				"label": "Lead",
				"options": "Construction Lead",
				"insert_after": "customer",
				"description": "Source lead when quote was created from a lead.",
			},
		],
	}
	create_custom_fields(custom_fields, ignore_validate=True, update=True)
