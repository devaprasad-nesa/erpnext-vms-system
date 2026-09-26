import frappe
from vms_user.services.login_service import get_current_user_context, get_or_create_customer_profile


def get_context(context):
    """
    Build the context used by customer-home.html / customer-dashboard.html.

    This page is intended for logged-in VMS customers.
    """

    # =========================================================
    # 1. Check whether the user is logged in
    # =========================================================
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    # =========================================================
    # 2. Get currently logged-in user
    # =========================================================
    user = frappe.session.user
    context.user = user
    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = 1
    context.title = "Customer Portal - VMS"

    # =========================================================
    # 3. Default values
    # =========================================================
    context.customer_name = user
    context.customer_profile = {
        "name": "",
        "customer_name": user,
        "customer_email": user,
        "customer_phone": "",
        "address": "",
    }

    # =========================================================
    # 4. Resolve customer profile from 'vms customer profile'
    # =========================================================
    try:
        profile = get_or_create_customer_profile(user)
        if profile:
            context.customer_name = profile.customer_name or user
            context.customer_profile = {
                "name": profile.name,
                "customer_name": profile.customer_name or user,
                "customer_email": profile.customer_email or user,
                "customer_phone": profile.customer_phone or "",
                "address": profile.address or "",
            }
    except Exception:
        try:
            ctx = get_current_user_context(user)
            context.customer_name = ctx.get("full_name") or user
            context.customer_profile["customer_name"] = context.customer_name
        except Exception:
            pass

    # =========================================================
    # 5. Return context
    # =========================================================
    return context