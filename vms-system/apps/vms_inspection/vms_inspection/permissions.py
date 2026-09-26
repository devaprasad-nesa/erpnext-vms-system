# =========================================================
# FILE: vms_inspection/permissions.py
# PURPOSE: Role-based permission queries and access controls
#          for vehicle inspections and spare parts.
# =========================================================

import frappe


def _is_staff_user(user: str | None = None) -> bool:
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    staff_roles = {
        "system manager",
        "administrator",
        "vms manager",
        "vms technician",
        "vms mechanic",
        "technician",
        "vms accountant",
    }
    return bool(roles.intersection(staff_roles))


def _get_identities(user: str) -> list[str]:
    try:
        from vms_user.login_service import get_user_identities
        return get_user_identities(user)
    except Exception:
        return [user]


def vehicle_inspection_query(user=None):
    """
    Query conditions for vms vehicle inspection:
    - Staff (technicians, managers, accountants, admins) see all records.
    - Customers see inspections only for vehicles registered to them.
    """
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return "1=0"

    if _is_staff_user(user):
        return ""

    escaped_user = frappe.db.escape(user)
    return f"""
        (`tabvms vehicle inspection`.`vehicle_number` IN (
            SELECT `name` FROM `tabvms vehicle registration`
            WHERE `owner_name` = {escaped_user} OR `owner_user` = {escaped_user}
        ) OR `tabvms vehicle inspection`.`customer_name` = {escaped_user})
    """


def vehicle_inspection_has_permission(doc, user=None, permission_type=None):
    """
    Document permission check for vms vehicle inspection:
    - Staff have full permission (create, read, write, delete).
    - Customers have read-only access to inspections for their vehicles.
    """
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    if _is_staff_user(user):
        return True

    if not doc:
        return True

    # Customers cannot modify or delete inspections
    if permission_type in ("write", "delete", "cancel", "submit"):
        return False

    allowed_values = set(_get_identities(user))
    doc_customer = getattr(doc, "customer_name", None)
    if doc_customer and doc_customer in allowed_values:
        return True

    vehicle_name = getattr(doc, "vehicle_number", None)
    if vehicle_name:
        vehicle_owner = frappe.db.get_value(
            "vms vehicle registration",
            vehicle_name,
            ["owner_name", "owner_user"],
            as_dict=True,
        )
        if vehicle_owner:
            if vehicle_owner.get("owner_name") in allowed_values or vehicle_owner.get("owner_user") in allowed_values:
                return True

    return False


def spare_parts_query(user=None):
    """
    All authenticated users can read spare parts catalog; staff have full access.
    """
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return "1=0"

    return ""


def spare_parts_has_permission(doc, user=None, permission_type=None):
    """
    Staff can manage spare parts; authenticated users can read.
    """
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    if _is_staff_user(user):
        return True

    if permission_type in ("read", "select"):
        return True

    return False
