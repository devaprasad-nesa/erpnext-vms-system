# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import getdate, flt


def parse_json(data):
    """Accept a dictionary or parse JSON string into a dictionary."""
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            frappe.throw(_("Invalid JSON format."))
    frappe.throw(_("Expected data object."))


def validate_required(data: dict, fields: list[str]):
    """Verify that all required keys are present and non-empty."""
    missing = []
    for f in fields:
        val = data.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(f)

    if missing:
        frappe.throw(_("Missing required fields: {0}").format(", ".join(missing)))


def validate_positive_number(value, field_name: str):
    """Ensure value is numeric and > 0."""
    num = flt(value)
    if num <= 0:
        frappe.throw(_("{0} must be greater than 0.").format(field_name))
    return num


def validate_date_value(date_val, field_name: str = "Date"):
    """Parse and validate date format."""
    if not date_val:
        frappe.throw(_("{0} is required.").format(field_name))
    try:
        return getdate(date_val)
    except Exception:
        frappe.throw(_("Invalid date format for {0}.").format(field_name))
