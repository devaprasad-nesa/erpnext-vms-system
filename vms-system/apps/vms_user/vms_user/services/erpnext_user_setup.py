# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _

VMS_ROLES = [
    "vms technician",
    "vms mechanic",
    "vms customer",
    "vms accountant",
    "vms manager",
]


def setup_roles():
    """Ensure all required VMS roles exist in ERPNext."""
    for role_name in VMS_ROLES:
        if not frappe.db.exists("Role", role_name):
            role = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1 if role_name in ["vms accountant", "vms manager"] else 0,
            })
            role.insert(ignore_permissions=True)
            print(f"✓ Created Role: {role_name}")


def setup_role_profiles():
    """Ensure Role Profiles exist for VMS user types."""
    profiles = {
        "VMS Accountant": ["vms accountant", "Accounts User", "Stock User"],
        "VMS Technician": ["vms technician"],
        "VMS Mechanic": ["vms mechanic"],
        "VMS Customer": ["vms customer"],
        "VMS Manager": ["vms manager", "Accounts Manager", "Stock Manager", "System Manager"],
    }

    for profile_name, roles in profiles.items():
        if not frappe.db.exists("Role Profile", profile_name):
            role_list = [{"role": r} for r in roles if frappe.db.exists("Role", r)]
            profile = frappe.get_doc({
                "doctype": "Role Profile",
                "role_profile": profile_name,
                "roles": role_list,
            })
            profile.insert(ignore_permissions=True)
            print(f"✓ Created Role Profile: {profile_name}")


def setup_doctype_permissions():
    """Configure ERPNext DocType permissions for VMS roles."""
    permissions_config = [
        # Accountant permissions
        {"doctype": "Sales Invoice", "role": "vms accountant", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        {"doctype": "Purchase Invoice", "role": "vms accountant", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Payment Entry", "role": "vms accountant", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Stock Entry", "role": "vms accountant", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Item", "role": "vms accountant", "read": 1, "write": 1, "create": 1},
        {"doctype": "Warehouse", "role": "vms accountant", "read": 1},
        {"doctype": "Customer", "role": "vms accountant", "read": 1, "write": 1, "create": 1},
        {"doctype": "Supplier", "role": "vms accountant", "read": 1, "write": 1, "create": 1},

        # Technician permissions
        {"doctype": "Item", "role": "vms technician", "read": 1},
        {"doctype": "Warehouse", "role": "vms technician", "read": 1},
        {"doctype": "Item Group", "role": "vms technician", "read": 1},
        {"doctype": "vms vehicle inspection", "role": "vms technician", "read": 1, "write": 1, "create": 1, "delete": 1},

        # Mechanic permissions
        {"doctype": "vms vehicle service registration", "role": "vms mechanic", "read": 1, "write": 1},
        {"doctype": "vms vehicle inspection", "role": "vms mechanic", "read": 1},

        # Customer permissions
        {"doctype": "vms vehicle registration", "role": "vms customer", "read": 1, "write": 1, "create": 1},
        {"doctype": "vms vehicle service registration", "role": "vms customer", "read": 1, "write": 1, "create": 1},
        {"doctype": "Sales Invoice", "role": "vms customer", "read": 1},
    ]

    for p in permissions_config:
        dt = p["doctype"]
        role = p["role"]
        if not frappe.db.exists("DocType", dt):
            continue

        exists = frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role})
        if not exists:
            try:
                docperm = frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": dt,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": role,
                    "read": p.get("read", 0),
                    "write": p.get("write", 0),
                    "create": p.get("create", 0),
                    "submit": p.get("submit", 0),
                    "cancel": p.get("cancel", 0),
                    "delete": p.get("delete", 0),
                })
                docperm.insert(ignore_permissions=True)
                print(f"✓ Added Permission for {role} on {dt}")
            except Exception as e:
                print(f"Notice: Permission setup for {dt} ({role}): {e}")


def setup_erpnext_user_roles_and_permissions():
    """Master entry point for user and permission setup."""
    setup_roles()
    setup_role_profiles()
    setup_doctype_permissions()
    frappe.db.commit()
    return "User roles and permissions setup successfully."
