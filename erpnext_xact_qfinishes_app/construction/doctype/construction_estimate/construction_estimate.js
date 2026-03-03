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
		if (!frm.doc.material_request_ref) {
			frm.add_custom_button(__("Create Material Request"), () => {
				frappe.call({
					method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.make_material_request",
					args: { estimate_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Material Request..."),
					callback(r) {
						if (r.message) {
							frm.reload_doc();
							frappe.set_route("Form", "Material Request", r.message);
						}
					},
				});
			}, __("Create"));
		}
		if (frm.doc.quotation_ref) {
			frm.add_custom_button(__("Open Quotation"), () => frappe.set_route("Form", "Quotation", frm.doc.quotation_ref));
		}
		if (frm.doc.material_request_ref) {
			frm.add_custom_button(__("Open Material Request"), () => frappe.set_route("Form", "Material Request", frm.doc.material_request_ref));
		}
		frm.add_custom_button(__("Create Purchase Order(s)"), () => {
			frappe.call({
				method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.make_purchase_orders_by_supplier",
				args: { estimate_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Purchase Orders by supplier..."),
				callback(r) {
					if (r.exc) return;
					const list = r.message || [];
					if (list.length === 0) return;
					if (list.length === 1) {
						frappe.set_route("Form", "Purchase Order", list[0]);
					} else {
						frappe.msgprint({
							title: __("Purchase Orders Created"),
							message: __("Created {0} POs: {1}. Opening first.").format(list.length, list.join(", ")),
							indicator: "green",
						});
						frappe.set_route("Form", "Purchase Order", list[0]);
					}
				},
			});
		}, __("Create"));
		// Retention: refresh summary when retention % is set
		if (frm.doc.retention_percent && frm.doc.retention_percent > 0) {
			frappe.call({
				method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.get_retention_summary",
				args: { estimate_name: frm.doc.name },
				callback(r) {
					if (r.message) {
						frm.set_value("total_retention_held", r.message.total_retention_held);
						frm.set_value("retention_released_amount", r.message.retention_released_amount);
					}
				},
			});
			frm.add_custom_button(__("Refresh retention summary"), () => {
				frappe.call({
					method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.get_retention_summary",
					args: { estimate_name: frm.doc.name },
					callback(r) {
						if (r.message) {
							frm.set_value("total_retention_held", r.message.total_retention_held);
							frm.set_value("retention_released_amount", r.message.retention_released_amount);
							frm.dashboard.set_headline_alert(
								__("Remaining to release: {0}").format(format_currency(r.message.remaining_to_release, frm.doc.currency))
							);
						}
					},
				});
			}, __("Retention"));
			frm.add_custom_button(__("Release retention"), () => {
				frappe.call({
					method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.get_retention_summary",
					args: { estimate_name: frm.doc.name },
					callback(r) {
						if (r.exc || !r.message) return;
						const s = r.message;
						if (s.remaining_to_release <= 0) {
							frappe.msgprint({ title: __("Retention"), message: __("No retention left to release."), indicator: "blue" });
							return;
						}
						const d = new frappe.ui.Dialog({
							title: __("Release retention"),
							fields: [
								{ fieldtype: "HTML", fieldname: "summary", options: `<p>${__("Total held")}: ${format_currency(s.total_retention_held, frm.doc.currency)}<br>${__("Already released")}: ${format_currency(s.retention_released_amount, frm.doc.currency)}<br><b>${__("To release")}: ${format_currency(s.remaining_to_release, frm.doc.currency)}</b></p>` },
								{ fieldname: "item_code", fieldtype: "Link", label: __("Item (optional)"), options: "Item", description: __("Leave blank to use first item from Sales Order.") },
							],
							primary_action_label: __("Create invoice"),
							primary_action(values) {
								frappe.call({
									method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.make_retention_release_invoice",
									args: { estimate_name: frm.doc.name, item_code: values.item_code || undefined },
									freeze: true,
									freeze_message: __("Creating retention release invoice..."),
									callback(r) {
										if (r.message) {
											d.hide();
											frm.reload_doc();
											frappe.set_route("Form", "Sales Invoice", r.message);
										}
									},
								});
							},
						});
						d.show();
					},
				});
			}, __("Retention"));
		}
		if (frm.doc.retention_release_invoice) {
			frm.add_custom_button(__("Open retention invoice"), () => frappe.set_route("Form", "Sales Invoice", frm.doc.retention_release_invoice), __("Retention"));
		}
		frm.add_custom_button(__("Send quote to client"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Send quote to client"),
				fields: [
					{ fieldname: "recipient_email", fieldtype: "Data", label: __("Recipient email (optional)"), description: __("Leave blank to use customer's default contact email.") },
				],
				primary_action_label: __("Send"),
				primary_action(values) {
					frappe.call({
						method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.send_quote_to_client",
						args: { estimate_name: frm.doc.name, recipient_email: values.recipient_email || undefined },
						freeze: true,
						freeze_message: __("Sending..."),
						callback(r) {
							if (r.exc) return;
							d.hide();
							frm.reload_doc();
							const link = r.message.view_link;
							const msg = (r.message.email_sent ? __("Email sent. ") : __("Share this link: ")) + link;
							frappe.msgprint({ title: __("Quote link"), message: msg, indicator: "green" });
						},
					});
				},
			});
			d.show();
		}, __("Create"));
		const uninvoiced_stages = (frm.doc.billing_stages || []).filter(s => !s.invoiced);
		if (uninvoiced_stages.length > 0) {
			frm.add_custom_button(__("Create Progress Invoice"), () => {
				const stage_options = uninvoiced_stages.map(s => ({ label: `${s.stage_name} (${s.percent}%)`, value: s.stage_name }));
				const d = new frappe.ui.Dialog({
					title: __("Create Progress Invoice"),
					fields: [
						{ fieldname: "stage_name", fieldtype: "Select", label: __("Stage"), options: stage_options, reqd: 1 },
						{ fieldname: "item_code", fieldtype: "Link", label: __("Item (optional)"), options: "Item", description: __("Leave blank to use first item from Sales Order.") },
					],
					primary_action_label: __("Create"),
					primary_action(values) {
						frappe.call({
							method: "erpnext_xact_qfinishes_app.construction.doctype.construction_estimate.construction_estimate.make_progress_invoice",
							args: { estimate_name: frm.doc.name, stage_name: values.stage_name, item_code: values.item_code || undefined },
							freeze: true,
							freeze_message: __("Creating Progress Invoice..."),
							callback(r) {
								if (r.message) {
									d.hide();
									frm.reload_doc();
									frappe.set_route("Form", "Sales Invoice", r.message);
								}
							},
						});
					},
				});
				d.show();
			}, __("Create"));
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
