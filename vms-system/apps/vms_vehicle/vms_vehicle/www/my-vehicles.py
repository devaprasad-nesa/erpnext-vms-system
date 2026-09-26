import frappe


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    user = frappe.session.user
    if user == "Administrator":
        pass
    else:
        roles = set(frappe.get_roles(user))
        if not ({"vms customer", "Customer", "System Manager", "vms manager"} & roles):
            frappe.throw(
                "Only VMS customers can access this page.",
                frappe.PermissionError
            )

    context.no_cache = 1
    context.title = "My Vehicles"

    return context