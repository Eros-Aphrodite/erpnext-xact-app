frappe.ui.form.on("Job", {
	refresh(frm) {
		if (frm.doc.__islocal) return;
		// Auto-refresh summary on load if never populated
		if (frm.doc.project && (frm.doc.contract_value == null || frm.doc.contract_value === 0) && frm.doc.progress_invoiced == null) {
			frappe.call({
				method: "refresh_summary",
				doc: frm.doc,
				callback() {
					frm.reload();
				},
			});
			return;
		}
		if (frm.doc.project) {
			frm.add_custom_button(__("Refresh Summary"), () => {
				frappe.call({
					method: "refresh_summary",
					doc: frm.doc,
					freeze: true,
					freeze_message: __("Updating summary..."),
					callback() {
						frm.reload();
					},
				});
			});
			frm.add_custom_button(__("Job Costing Summary"), () => {
				frappe.set_route("query-report", "Job Costing Summary", { project: frm.doc.project });
			}, __("Reports"));
			frm.add_custom_button(__("Progress Billing Summary"), () => {
				frappe.set_route("query-report", "Progress Billing Summary", { project: frm.doc.project });
			}, __("Reports"));
			// Scheduling: quick access to project tasks and Gantt
			frm.add_custom_button(__("Project Tasks"), () => {
				frappe.route_options = { project: frm.doc.project };
				frappe.set_route("List", "Task");
			}, __("Schedule"));
			frm.add_custom_button(__("Project Gantt"), () => {
				frappe.route_options = { project: frm.doc.project };
				frappe.set_route("Gantt", "Task");
			}, __("Schedule"));
		}
		if (frm.doc.project) {
			frm.add_custom_button(__("Open Project"), () => frappe.set_route("Form", "Project", frm.doc.project));
		}
		if (frm.doc.construction_estimate) {
			frm.add_custom_button(__("Open Estimate"), () => frappe.set_route("Form", "Construction Estimate", frm.doc.construction_estimate));
		}
		if (frm.doc.sales_order) {
			frm.add_custom_button(__("Open Sales Order"), () => frappe.set_route("Form", "Sales Order", frm.doc.sales_order));
		}
		if (frm.doc.material_request_ref) {
			frm.add_custom_button(__("Open Material Request"), () => frappe.set_route("Form", "Material Request", frm.doc.material_request_ref));
		}
		if (frm.doc.project) {
			frm.add_custom_button(__("Job Documents"), () => {
				frappe.set_route("List", "Job Document", { project: frm.doc.project });
			});
			frm.add_custom_button(__("Subcontractors"), () => {
				frappe.set_route("List", "Subcontractor", { project: frm.doc.project });
			});
			frm.add_custom_button(__("Job Expenses"), () => {
				frappe.set_route("List", "Job Expense", { project: frm.doc.project });
			});
		}
	},
});
