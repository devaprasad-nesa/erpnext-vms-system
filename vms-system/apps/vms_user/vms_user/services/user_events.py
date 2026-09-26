import frappe


def assign_customer_role(doc, method=None):
    """Add the VMS customer role to new website users without saving recursively."""
    if doc.name == "Administrator" or doc.user_type != "Website User":
        return

    role_name = "vms customer"
    if not frappe.db.exists("Role", role_name):
        frappe.log_error(
            f"Role '{role_name}' does not exist.",
            "VMS Customer Role Assignment",
        )
        return

    # Add to the in-memory child table during insertion. Do not call add_roles()
    # here: it can trigger another User save/doc event and cause recursive behavior.
    existing_roles = {row.role for row in (doc.get("roles") or [])}
    if role_name not in existing_roles:
        doc.append("roles", {"role": role_name})