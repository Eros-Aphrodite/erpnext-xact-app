frappe.ui.form.on("Subcontractor", {
	refresh(frm) {
		if (frm.doc.__islocal) return;
		frm.add_custom_button(__("Create Purchase Order"), () => {
			frappe.call({
				method: "erpnext_xact_qfinishes_app.construction.doctype.subcontractor.subcontractor.create_purchase_order",
				args: { subcontractor_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Purchase Order..."),
				callback(r) {
					if (r.message) frappe.set_route("Form", "Purchase Order", r.message);
				},
			});
		}, __("Create"));
	},
});
