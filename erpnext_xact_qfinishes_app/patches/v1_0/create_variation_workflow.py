# Copyright (c) 2026, Q Finishes and contributors
# Create Variation workflow: Draft -> Submitted -> Approved/Rejected -> (Resubmit from Rejected)

import frappe


def execute():
	if frappe.db.exists("Workflow", {"document_type": "Variation"}):
		return

	# Workflow States (create if not exist)
	for state_name, style in [
		("Draft", "Inverse"),
		("Submitted", "Info"),
		("Approved", "Success"),
		("Rejected", "Danger"),
	]:
		if not frappe.db.exists("Workflow State", state_name):
			frappe.get_doc({
				"doctype": "Workflow State",
				"workflow_state_name": state_name,
				"style": style,
			}).insert(ignore_permissions=True)

	# Workflow Action Master (create if not exist)
	for action_name in ["Submit for Approval", "Approve", "Reject", "Resubmit"]:
		if not frappe.db.exists("Workflow Action Master", action_name):
			frappe.get_doc({
				"doctype": "Workflow Action Master",
				"workflow_action_name": action_name,
			}).insert(ignore_permissions=True)

	# Workflow
	workflow = frappe.new_doc("Workflow")
	workflow.workflow_name = "Variation Workflow"
	workflow.document_type = "Variation"
	workflow.workflow_state_field = "status"
	workflow.is_active = 1

	workflow.append("states", {"state": "Draft", "allow_edit": "System Manager", "update_field": "status", "update_value": "Draft"})
	workflow.append("states", {"state": "Submitted", "allow_edit": "System Manager", "update_field": "status", "update_value": "Submitted"})
	workflow.append("states", {"state": "Approved", "allow_edit": "System Manager", "update_field": "status", "update_value": "Approved"})
	workflow.append("states", {"state": "Rejected", "allow_edit": "System Manager", "update_field": "status", "update_value": "Rejected"})

	workflow.append("transitions", {
		"state": "Draft",
		"action": "Submit for Approval",
		"next_state": "Submitted",
		"allowed": "System Manager",
		"allow_self_approval": 1,
	})
	workflow.append("transitions", {
		"state": "Submitted",
		"action": "Approve",
		"next_state": "Approved",
		"allowed": "System Manager",
		"allow_self_approval": 1,
	})
	workflow.append("transitions", {
		"state": "Submitted",
		"action": "Reject",
		"next_state": "Rejected",
		"allowed": "System Manager",
		"allow_self_approval": 1,
	})
	workflow.append("transitions", {
		"state": "Rejected",
		"action": "Resubmit",
		"next_state": "Draft",
		"allowed": "System Manager",
		"allow_self_approval": 1,
	})

	workflow.insert(ignore_permissions=True)
	frappe.db.commit()
