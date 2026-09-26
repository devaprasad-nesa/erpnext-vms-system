# =========================================================
# FILE: vms_account/permissions.py
# PURPOSE: Role-based permissions for invoices & billing records.
# =========================================================

import frappe


def _is_accountant_or_admin(user: str | None = None) -> bool:
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    staff_roles = {
        "system manager",
        "administrator",
        "vms manager",
        "vms accountant",
        "accounts manager",
        "accounts user",
    }
    return bool(roles.intersection(staff_roles))


def accounts_query(user=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return "1=0"

    if _is_accountant_or_admin(user):
        return ""

    escaped_user = frappe.db.escape(user)
    return f"`tabvms accounts`.`customer_name` = {escaped_user}"


def accounts_has_permission(doc, user=None, permission_type=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    if _is_accountant_or_admin(user):
        return True

    if not doc:
        return True

    # Customers have read-only access to their own invoices
    if permission_type in ("write", "delete", "cancel", "submit"):
        return False

    customer = getattr(doc, "customer_name", None)
    if customer and customer == user:
        return True

    return False
