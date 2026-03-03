// Copyright (c) 2026, Q Finishes and contributors
// For license information, please see license.txt

frappe.ui.form.on("Takeoff", {
	refresh(frm) {
		if (frm.doc.project) {
			frm.add_custom_button(__("Open Project"), () => frappe.set_route("Form", "Project", frm.doc.project));
		}
		if (frm.doc.construction_estimate) {
			frm.add_custom_button(__("Open Estimate"), () => frappe.set_route("Form", "Construction Estimate", frm.doc.construction_estimate));
		}
	},
});
