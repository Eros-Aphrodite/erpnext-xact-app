# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from datetime import datetime

import frappe
from frappe.model.document import Document


class DeputySettings(Document):
	@frappe.whitelist()
	def sync_timesheets(self):
		"""Fetch approved timesheets from Deputy and create ERPNext Timesheets."""
		if not self.enabled or not self.deputy_install or not self.deputy_api_key:
			frappe.throw(frappe._("Enable Deputy sync and set API credentials."))
		from erpnext_xact_qfinishes_app.construction.deputy_sync import sync_deputy_timesheets

		result = sync_deputy_timesheets(self)
		self.last_sync = datetime.now()
		self.sync_notes = json.dumps(result, indent=2)
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return result
