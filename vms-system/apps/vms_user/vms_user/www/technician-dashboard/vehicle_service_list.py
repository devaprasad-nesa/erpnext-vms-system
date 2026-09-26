import frappe
from vms_vehicle.service_registration import is_staff_user


def get_context(context):
    """
    Context for Technician Vehicle Service List.
    """
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/vms-login"
        raise frappe.Redirect

    user = frappe.session.user

    # Require staff or technician role
    if not is_staff_user(user):
        frappe.local.flags.redirect_location = "/customer-home"
        raise frappe.Redirect

    roles = [r.strip().lower() for r in frappe.get_roles(user)]
    is_technician = (
        "vms technician" in roles
        or "system manager" in roles
        or "administrator" == user.lower()
        or "vms manager" in roles
    )

    context.no_cache = 1
    context.show_sidebar = False
    context.title = "Vehicle Service List - VMS"
    context.user = user
    context.is_technician = 1 if is_technician else 0

    return context
