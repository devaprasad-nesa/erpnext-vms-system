import frappe
from vms_user.services.login_service import get_current_user_context, get_or_create_customer_profile


def get_context(context):
    """
    Context for My Vehicles page.
    """
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    user = frappe.session.user
    context.user = user
    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = 1
    context.title = "My Vehicles | VMS Customer Portal"

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
        if isinstance(profile, dict):
            context.customer_name = profile.get("customer_name") or user
            context.customer_profile = profile
        elif profile:
            context.customer_name = getattr(profile, "customer_name", None) or user
            context.customer_profile = {
                "name": getattr(profile, "name", ""),
                "customer_name": getattr(profile, "customer_name", user),
                "customer_email": getattr(profile, "customer_email", user),
                "customer_phone": getattr(profile, "customer_phone", ""),
                "address": getattr(profile, "address", ""),
            }
    except Exception:
        try:
            ctx = get_current_user_context(user)
            context.customer_name = ctx.get("full_name") or user
            context.customer_profile["customer_name"] = context.customer_name
        except Exception:
            pass

    return context
