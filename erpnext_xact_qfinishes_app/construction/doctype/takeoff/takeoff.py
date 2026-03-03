# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Takeoff(Document):
	def validate(self):
		if not self.company:
			self.company = frappe.defaults.get_defaults().get("company")
		for row in self.items or []:
			row.area = row.area or (flt(row.length) * flt(row.width) if row.measurement_type in ("m²", "SF") else row.quantity or 0)
