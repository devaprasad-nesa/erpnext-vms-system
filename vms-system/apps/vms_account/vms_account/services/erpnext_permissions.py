# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ACCOUNTANT_ROLES = {
    "vms accountant",
    "vms manager",
    "accounts user",
    "accounts manager",
    "system manager",
    "administrator",
}

TECHNICIAN_ROLES = {
    "vms technician",
    "technician",
    "vms manager",
    "system manager",
    "administrator",
}

STAFF_ROLES = ACCOUNTANT_ROLES.union(TECHNICIAN_ROLES).union({"vms mechanic", "mechanic"})


def get_current_user_roles():
    """Return lowercase roles of current session user."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if user == "Guest":
        return set()
    return {r.strip().lower() for r in frappe.get_roles(user)}


def require_accountant():
    """Ensure session user has accountant or accounting manager privileges."""
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(_("Please log in to continue."), frappe.PermissionError)

    if user == "Administrator":
        return user

    roles = get_current_user_roles()
    if not roles.intersection(ACCOUNTANT_ROLES):
        frappe.throw(_("Only VMS Accountants and managers can access this service."), frappe.PermissionError)

    return user


def require_technician():
    """Ensure session user has technician or manager privileges."""
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(_("Please log in to continue."), frappe.PermissionError)

    if user == "Administrator":
        return user

    roles = get_current_user_roles()
    if not roles.intersection(TECHNICIAN_ROLES):
        frappe.throw(_("Only authorized technicians can access this service."), frappe.PermissionError)

    return user


def require_staff():
    """Ensure session user is workshop staff."""
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(_("Please log in to continue."), frappe.PermissionError)

    if user == "Administrator":
        return user

    roles = get_current_user_roles()
    if not roles.intersection(STAFF_ROLES):
        frappe.throw(_("Only workshop staff can access this service."), frappe.PermissionError)

    return user
