// Copyright (c) 2026, Q Finishes and contributors
frappe.ui.form.on("Deputy Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Sync Timesheets from Deputy"), () => {
			frappe.call({
				method: "sync_timesheets",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Syncing from Deputy..."),
				callback(r) {
					if (!r.exc) {
						frm.reload_doc();
						frappe.msgprint({ title: __("Deputy Sync"), message: __("Sync completed."), indicator: "green" });
					}
				},
			});
		});
	},
});
