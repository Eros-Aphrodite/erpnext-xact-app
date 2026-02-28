frappe.ui.form.on("Construction Estimate", {
	refresh(frm) {
		// Actions available even on new doc (will save first)
		frm.add_custom_button(__("Calculate Quantities"), () => {
			if (frm.doc.__islocal) {
				frm.save(() => run_calculate_quantities(frm));
			} else {
				run_calculate_quantities(frm);
			}
		}, __("Tools"));
		frm.add_custom_button(__("Recalculate Rates"), () => {
			if (frm.doc.__islocal) {
				frm.save(() => run_recalculate_rates(frm));
			} else {
				run_recalculate_rates(frm);
			}
		}, __("Tools"));
		if (frm.doc.__islocal) return;
		frm.add_custom_button(__("Create Quotation"), () => {
			frappe.call({
				method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.make_quotation",
				args: { estimate_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Quotation..."),
				callback(r) {
					if (r.message) frappe.set_route("Form", "Quotation", r.message);
				},
			});
		}, __("Create"));
		if (frm.doc.quotation_ref) {
			frm.add_custom_button(__("Open Quotation"), () => frappe.set_route("Form", "Quotation", frm.doc.quotation_ref));
		}
	},
});

function run_calculate_quantities(frm) {
	frappe.call({
		method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.calculate_quantities",
		args: { estimate_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Calculating quantities..."),
		callback(r) {
			if (!r.exc) frm.reload_doc();
		},
	});
}

function run_recalculate_rates(frm) {
	frappe.call({
		method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.recalculate_rates",
		args: { estimate_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Recalculating rates..."),
		callback(r) {
			if (!r.exc) frm.reload_doc();
		},
	});
}
