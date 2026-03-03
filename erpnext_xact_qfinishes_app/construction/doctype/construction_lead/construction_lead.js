// Copyright (c) 2026, Q Finishes and contributors
// For license information, please see license.txt

frappe.ui.form.on("Construction Lead", {
	refresh(frm) {
		if (!frm.doc.customer && frm.doc.lead_name) {
			frm.add_custom_button(__("Convert to Customer"), () => {
				frappe.call({
					method: "convert_to_customer",
					doc: frm.doc,
					callback(r) {
						if (!r.exc) frm.reload_doc();
					},
				});
			}, __("Create"));
		}
		if (!frm.doc.construction_estimate && frm.doc.lead_name) {
			frm.add_custom_button(__("Create Quote"), () => {
				frappe.call({
					method: "create_quote",
					doc: frm.doc,
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
							if (r.message) frappe.set_route("Form", "Construction Estimate", r.message);
						}
					},
				});
			}, __("Create")).addClass("btn-primary");
		}
		if (frm.doc.construction_estimate) {
			frm.add_custom_button(__("Open Quote"), () => {
				frappe.set_route("Form", "Construction Estimate", frm.doc.construction_estimate);
			});
		}
		if (frm.doc.project) {
			frm.add_custom_button(__("Open Project"), () => {
				frappe.set_route("Form", "Project", frm.doc.project);
			});
		}
	},
});
