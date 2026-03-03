"""Add Construction Estimate link on Purchase Order (for POs created from estimate by supplier)."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Purchase Order": [
			{
				"fieldname": "construction_estimate",
				"fieldtype": "Link",
				"label": "Construction Estimate",
				"options": "Construction Estimate",
				"insert_after": "project",
				"description": "Set when PO is created from Construction Estimate (Create Purchase Order(s)).",
			},
		],
	}
	create_custom_fields(custom_fields, ignore_validate=True, update=True)
