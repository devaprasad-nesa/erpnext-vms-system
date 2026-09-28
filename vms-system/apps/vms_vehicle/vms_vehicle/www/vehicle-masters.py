import frappe
from frappe import _

def get_context(context):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/vehicle-masters"
        raise frappe.Redirect

    if user != "Administrator":
        roles = {r.strip().lower() for r in frappe.get_roles(user)}
        admin_roles = {"system manager", "administrator", "vms manager"}
        if not roles.intersection(admin_roles):
            frappe.throw(_("Access Restricted: Only Administrators and VMS Managers can manage master data."), frappe.PermissionError)

    context.no_cache = 1
    context.user = user
    user_doc = frappe.db.get_value("User", user, ["full_name", "email"], as_dict=True)
    context.user_full_name = (user_doc and user_doc.full_name) or user
    return context
