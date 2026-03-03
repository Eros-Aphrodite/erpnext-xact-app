# Copyright (c) 2026, Q Finishes and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class ConstructionSupplierPrice(Document):
	def validate(self):
		if self.item and self.supplier:
			self.item_supplier = f"{self.item}-{self.supplier}"
		if not self.currency:
			self.currency = frappe.defaults.get_defaults().get("currency")
