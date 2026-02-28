frappe.ui.form.on("Variation", {
	refresh(frm) {
		if (frm.doc.__islocal) return;
		if (frm.doc.status === "Approved" && !frm.doc.sales_order_ref) {
			frm.add_custom_button(__("Create Change Order"), () => {
				frappe.call({
					method: "erpnext_xact_qfinishes_app.construction.doctype.variation.variation.create_change_order",
					args: { variation_name: frm.doc.name },
					freeze: true,
					callback(r) {
						if (r.message) frappe.set_route("Form", "Sales Order", r.message);
					},
				});
			}, __("Create"));
		}
		if (frm.doc.sales_order_ref) {
			frm.add_custom_button(__("Open Sales Order"), () => frappe.set_route("Form", "Sales Order", frm.doc.sales_order_ref));
		}
	},
});
