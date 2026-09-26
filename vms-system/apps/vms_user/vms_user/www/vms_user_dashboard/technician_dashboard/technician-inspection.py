import frappe

def get_context(context):
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
        
    context.spare_parts = frappe.get_all("vms spare parts", fields=["name", "part_name", "quantity"])
    
    # Fetch all users who have the 'vms mechanic' role
    roles = frappe.db.get_all("Has Role", filters={"role": "vms mechanic"}, fields=["parent"])
    mechanic_users = [r.parent for r in roles] if roles else []
    
    if mechanic_users:
        context.mechanics = frappe.get_all(
            "User", 
            filters={"name": ["in", mechanic_users], "enabled": 1}, 
            fields=["name", "full_name"],
            ignore_permissions=True
        )
    else:
        context.mechanics = []
        
    return context
