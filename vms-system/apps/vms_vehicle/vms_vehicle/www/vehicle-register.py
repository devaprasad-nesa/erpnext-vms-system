import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/vms-login"
        raise frappe.Redirect

    context.no_cache = 1
    context.title = "Register Vehicle | VMS Customer Portal"
    context.user = frappe.session.user

    return context