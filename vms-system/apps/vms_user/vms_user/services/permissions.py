import frappe
from vms_user.login_service import get_current_user_context, get_user_identities


def vms_customer_profile_query(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"

    ctx = get_current_user_context(user)

    if ctx["is_admin"] or ctx["is_manager"] or ctx["is_technician"]:
        return ""

    if ctx["is_customer"]:
        escaped_user = frappe.db.escape(user)
        return f"`tabvms customer profile`.`user_name` = {escaped_user}"

    return "1=0"


def vms_customer_profile_has_permission(doc=None, ptype=None, user=None, debug=False, permission_type=None, **kwargs):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    ctx = get_current_user_context(user)

    if ctx["is_admin"] or ctx["is_manager"] or ctx["is_technician"]:
        return True

    if not ctx["is_customer"]:
        return False

    if not doc:
        return True

    doc_user = getattr(doc, "user_name", None)
    if not doc_user and isinstance(doc, str):
        doc_user = frappe.db.get_value("vms customer profile", doc, "user_name")

    allowed_identities = set(get_user_identities(user))

    if doc_user and doc_user not in allowed_identities and doc_user != user:
        return False

    return True


def vms_user_query(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"

    ctx = get_current_user_context(user)
    if ctx["is_admin"] or ctx["is_manager"]:
        return ""

    # User isolation: technicians can only access users with 'vms customer' role
    if ctx["is_technician"]:
        return "`tabUser`.name IN (SELECT parent FROM `tabHas Role` WHERE role='vms customer')"

    if ctx["is_customer"] or ctx["is_mechanic"] or ctx["is_accountant"]:
        escaped_user = frappe.db.escape(user)
        return f"`tabUser`.name = {escaped_user}"

    return "1=0"


def vms_user_has_permission(doc=None, ptype=None, user=None, debug=False, permission_type=None, **kwargs):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    ctx = get_current_user_context(user)
    if ctx["is_admin"] or ctx["is_manager"]:
        return True

    effective_ptype = ptype or permission_type or "read"
    doc_name = doc if isinstance(doc, str) else getattr(doc, "name", None)

    if ctx["is_technician"]:
        # Technicians only have read/select access to customers
        if effective_ptype not in ("read", "select"):
            return False
        if not doc_name:
            return True
        if frappe.db.exists("Has Role", {"parent": doc_name, "role": "vms customer"}):
            return True
        return False

    if not doc_name:
        return True

    allowed_identities = set(get_user_identities(user))
    if doc_name in allowed_identities or doc_name == user:
        return True

    return False