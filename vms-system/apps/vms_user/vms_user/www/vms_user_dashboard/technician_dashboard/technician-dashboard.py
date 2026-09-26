import frappe
from vms_user.services.login_service import get_current_user_context


def get_context(context):
    """
    Context for Technician Dashboard.
    Ensures guest users are redirected to login and default headers/sidebars are disabled.
    """
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    user = frappe.session.user
    context.user = user
    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = 1
    context.title = "Technician Dashboard | VMS"

    try:
        ctx = get_current_user_context(user)
        context.full_name = ctx.get("full_name") or user
    except Exception:
        context.full_name = user

    return context
