# =========================================================
# FILE: vms_vehicle/permissions.py
# PURPOSE: Permission query conditions and checks for
#          vehicles and service registrations.
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
        "vms accountant",
    }
    return bool(staff_roles.intersection(roles))


def _get_identities(user: str) -> list[str]:
    try:
        from vms_user.login_service import get_user_identities
        return get_user_identities(user)
    except Exception:
        return [user]


def vehicle_registration_query(user=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return "1=0"

    if _is_staff_user(user):
        return ""

    escaped_user = frappe.db.escape(user)
    return (
        f"(`tabvms vehicle registration`.`owner_name` = {escaped_user} "
        f"OR `tabvms vehicle registration`.`owner_user` = {escaped_user})"
    )


def service_registration_query(user=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return "1=0"

    if _is_staff_user(user):
        return ""

    escaped_user = frappe.db.escape(user)
    return (
        f"(`tabvms vehicle service registration`.`customer_name` = {escaped_user} "
        f"OR `tabvms vehicle service registration`.`user_id` = {escaped_user})"
    )


def vehicle_has_permission(doc, user=None, permission_type=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    if _is_staff_user(user):
        return True

    if not doc:
        return True

    owner_name = getattr(doc, "owner_name", None)
    owner_user = getattr(doc, "owner_user", None)
    allowed_values = set(_get_identities(user))

    if owner_name not in allowed_values and owner_user not in allowed_values:
        return False

    # Customers may read their own vehicle, but deletions/cancel are staff-controlled
    if permission_type in ("delete", "submit", "cancel"):
        return False

    return True


def service_has_permission(doc, user=None, permission_type=None):
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    if _is_staff_user(user):
        return True

    if not doc:
        return True

    customer_name = getattr(doc, "customer_name", None)
    user_id = getattr(doc, "user_id", None)
    allowed_values = set(_get_identities(user))

    if customer_name not in allowed_values and user_id not in allowed_values:
        return False

    # Customers can read their own service requests; status mutations are managed by staff
    if permission_type in ("delete", "submit", "cancel"):
        return False

    return True


def has_app_permission(user=None):
    user = user or getattr(frappe.session, "user", None)
    return _is_staff_user(user)