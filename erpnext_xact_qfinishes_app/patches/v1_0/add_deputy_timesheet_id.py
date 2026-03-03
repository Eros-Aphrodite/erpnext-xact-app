"""Add deputy_timesheet_id on Timesheet for Deputy sync deduplication."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Timesheet": [
			{
				"fieldname": "deputy_timesheet_id",
				"fieldtype": "Data",
				"label": "Deputy Timesheet ID",
				"insert_after": "employee",
				"description": "Set when synced from Deputy.",
				"read_only": 1,
			},
		],
	}
	create_custom_fields(custom_fields, ignore_validate=True, update=True)
