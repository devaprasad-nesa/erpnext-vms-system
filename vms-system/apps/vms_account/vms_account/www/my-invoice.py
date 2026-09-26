import frappe


def get_context(context):
    frappe.local.flags.redirect_location = "/my-invoices"
    raise frappe.Redirect
