import frappe


def get_context(context):
    user = getattr(frappe.session, "user", None) or "Guest"

    if user == "Guest":
        frappe.flags.redirect_location = "/vms-login"
        frappe.local.flags.redirect_location = "/vms-login"
        raise frappe.Redirect

    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = 1
    context.title = "My Invoices - VMS"
    context.user = user

    try:
        from vms_user.services.login_service import get_or_create_customer_profile
        profile = get_or_create_customer_profile(user)
        if isinstance(profile, dict):
            context.customer_name = profile.get("customer_name") or user
            context.customer_profile = profile
        else:
            context.customer_name = getattr(profile, "customer_name", None) or user
            context.customer_profile = profile
    except Exception:
        context.customer_name = user
        context.customer_profile = {"customer_name": user}

    return context

