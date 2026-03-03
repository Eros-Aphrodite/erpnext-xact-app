"""Add Cost Code custom fields to Material Request Item, Purchase Order Item, Purchase Invoice Item, and Timesheet Detail."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Material Request Item": [
			{
				"fieldname": "cost_code",
				"fieldtype": "Link",
				"label": "Cost Code",
				"options": "Cost Code",
				"insert_after": "project",
			},
		],
		"Purchase Order Item": [
			{
				"fieldname": "cost_code",
				"fieldtype": "Link",
				"label": "Cost Code",
				"options": "Cost Code",
				"insert_after": "project",
			},
		],
		"Purchase Invoice Item": [
			{
				"fieldname": "cost_code",
				"fieldtype": "Link",
				"label": "Cost Code",
				"options": "Cost Code",
				"insert_after": "project",
			},
		],
		"Timesheet Detail": [
			{
				"fieldname": "cost_code",
				"fieldtype": "Link",
				"label": "Cost Code",
				"options": "Cost Code",
				"insert_after": "project",
			},
		],
	}

	create_custom_fields(custom_fields, ignore_validate=True, update=True)
	frappe.msgprint("✅ Cost Code fields added to MR/PO/PI items and Timesheet Detail")
