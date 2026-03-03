# Copyright (c) 2026, Q Finishes and contributors
# Deputy API timesheet sync to ERPNext Timesheet

from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlencode

import frappe
from frappe import _


def sync_deputy_timesheets(settings) -> dict:
	"""Fetch approved timesheets from Deputy API and create ERPNext Timesheets."""
	install = (settings.deputy_install or "").strip()
	geo = (settings.deputy_geo or "au").strip().lower()
	api_key = settings.deputy_api_key
	api_secret = settings.deputy_api_secret

	if not install or not api_key:
		return {"error": "Missing Deputy install or API key", "created": 0}

	# Deputy OAuth2 / API - use token from API key (simplified: API key as bearer for dev)
	# Production: use OAuth2 flow to get access_token
	base_url = f"https://{install}.{geo}.deputy.com/api/v1"
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}

	# Employee mapping: Deputy Employee ID -> ERPNext Employee
	emp_map = {}
	if settings.employee_mapping:
		try:
			emp_map = json.loads(settings.employee_mapping)
		except Exception:
			pass

	# Query timesheets (last 7 days by default)
	from_date = datetime.now()
	from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
	from_ts = int(from_date.timestamp()) - (7 * 24 * 3600)

	payload = {
		"search": {
			"s1": {"field": "StartTime", "data": from_ts, "type": "gt"},
			"s2": {"field": "TimeApproved", "data": True, "type": "eq"},
		}
	}

	created = 0
	errors = []

	try:
		import requests

		resp = requests.post(
			f"{base_url}/resource/Timesheet/QUERY",
			headers=headers,
			json=payload,
			timeout=30,
		)
		resp.raise_for_status()
		data = resp.json()
	except ImportError:
		return {"error": "requests library required. Run: pip install requests", "created": 0}
	except Exception as e:
		return {"error": str(e), "created": 0}

	# data can be a list or dict with results
	timesheets = data if isinstance(data, list) else (data.get("results") or data.get("data") or [])
	if not isinstance(timesheets, list):
		timesheets = [timesheets] if timesheets else []

	for ts in timesheets:
		deputy_id = ts.get("Id") or ts.get("id")
		emp_id = ts.get("Employee") or ts.get("employee")
		start_ts = ts.get("StartTime") or ts.get("startTime")
		end_ts = ts.get("EndTime") or ts.get("endTime")
		total_hours = ts.get("TotalTime") or ts.get("totalTime") or 0

		if not start_ts or not end_ts:
			continue

		erp_employee = emp_map.get(str(emp_id)) if emp_id else None
		if not erp_employee and emp_id:
			# Try to find by Deputy custom field or skip
			continue

		# Check if already synced
		existing = frappe.db.exists(
			"Timesheet",
			{"deputy_timesheet_id": str(deputy_id)},
		)
		if existing:
			continue

		# Create ERPNext Timesheet
		try:
			start_dt = datetime.fromtimestamp(start_ts)
			end_dt = datetime.fromtimestamp(end_ts)

			timesheet = frappe.new_doc("Timesheet")
			timesheet.employee = erp_employee or frappe.db.get_value("Employee", {"status": "Active"}, "name")
			if not timesheet.employee:
				errors.append(f"Deputy TS {deputy_id}: No Employee mapped")
				continue

			timesheet.append(
				"time_logs",
				{
					"from_time": start_dt,
					"to_time": end_dt,
					"hours": total_hours,
					"activity_type": frappe.db.get_value("Activity Type", {"name": "Construction"}, "name") or "Construction",
				},
			)
			timesheet.flags.ignore_mandatory = True
			timesheet.insert(ignore_permissions=True)

			# Store Deputy ID for deduplication (custom field)
			if hasattr(timesheet, "deputy_timesheet_id"):
				frappe.db.set_value("Timesheet", timesheet.name, "deputy_timesheet_id", str(deputy_id), update_modified=False)

			created += 1
		except Exception as e:
			errors.append(f"Deputy TS {deputy_id}: {str(e)}")

	return {"created": created, "errors": errors[:10], "fetched": len(timesheets)}
