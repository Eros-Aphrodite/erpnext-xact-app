# Copyright (c) 2026, Q Finishes and contributors
# Minimal client portal: My Jobs (projects with contract value, progress invoiced, invoices list)

import frappe
from frappe import _
from frappe.utils import flt

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view your jobs."), frappe.PermissionError)

	from erpnext.controllers.website_list_for_contact import get_customers_suppliers

	customers, _ = get_customers_suppliers("Project", frappe.session.user)
	if not customers:
		context.jobs = []
		context.no_customer = True
		context.show_sidebar = True
		return context

	# Projects for this customer (with contract value from SO or estimate)
	projects = frappe.db.sql(
		"""
		select
			p.name as project,
			p.project_name,
			coalesce(so_totals.contract_value, est_totals.est_total, 0) as contract_value,
			coalesce(si_totals.invoiced, 0) as progress_invoiced
		from `tabProject` p
		left join (
			select project, sum(grand_total) as contract_value
			from `tabSales Order` where docstatus = 1 group by project
		) so_totals on so_totals.project = p.name
		left join (
			select project, sum(total_amount) as est_total
			from `tabConstruction Estimate` group by project
		) est_totals on est_totals.project = p.name
		left join (
			select project, sum(grand_total) as invoiced
			from `tabSales Invoice` where docstatus = 1 group by project
		) si_totals on si_totals.project = p.name
		where p.customer in %(customers)s
		and coalesce(so_totals.contract_value, est_totals.est_total, 0) > 0
		order by p.modified desc
		""",
		{"customers": customers},
		as_dict=True,
	)

	# Build job list with invoices per project
	context.jobs = []
	for p in projects:
		contract = flt(p.contract_value)
		invoiced = flt(p.progress_invoiced)
		remaining = max(0, contract - invoiced)
		invoices = frappe.get_all(
			"Sales Invoice",
			filters={"project": p.project, "customer": ["in", customers], "docstatus": 1},
			fields=["name", "posting_date", "grand_total", "status"],
			order_by="posting_date desc",
			limit=20,
		)
		variations = frappe.get_all(
			"Variation",
			filters={"project": p.project},
			fields=["name", "title", "total_amount", "transaction_date", "client_approval_status", "client_approved_date", "client_comment"],
			order_by="modified desc",
			limit=50,
		)
		job_documents = frappe.get_all(
			"Job Document",
			filters={"project": p.project},
			fields=["name", "title", "category", "file"],
			order_by="category asc, modified desc",
			limit=50,
		)
		context.jobs.append({
			"project": p.project,
			"project_name": p.project_name or p.project,
			"contract_value": contract,
			"progress_invoiced": invoiced,
			"remaining_to_bill": remaining,
			"percent_invoiced": round((invoiced / contract * 100), 1) if contract else 0,
			"invoices": invoices,
			"variations": variations,
			"job_documents": job_documents,
			"currency": frappe.defaults.get_defaults().get("currency") or "AUD",
		})

	context.no_customer = False
	context.show_sidebar = True
	return context
