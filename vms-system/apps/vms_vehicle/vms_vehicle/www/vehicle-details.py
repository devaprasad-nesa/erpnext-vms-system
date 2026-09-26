import frappe
from vms_user.services.login_service import get_current_user_context, get_or_create_customer_profile


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login-page/vms-login"
        raise frappe.Redirect

    user = frappe.session.user
    context.user = user
    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = 1
    context.title = "Vehicle Details - VMS"

    context.customer_name = user
    context.customer_profile = {
        "name": "",
        "customer_name": user,
        "customer_email": user,
        "customer_phone": "",
        "address": "",
    }

    try:
        profile = get_or_create_customer_profile(user)
        if profile:
            context.customer_profile = profile
            context.customer_name = profile.get("customer_name") or user
    except Exception as e:
        frappe.log_error(f"Error resolving customer profile in vehicle-details: {e}")

    return context