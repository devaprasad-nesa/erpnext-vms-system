# =========================================================
# FILE: vms_inspection/api.py
# PURPOSE: Whitelisted endpoints for inspection management,
#          technician workflows, and customer vehicle reports.
# =========================================================

import json

import frappe
from frappe import _
from vms_user.pagination import apply_pagination
from vms_inspection import services


def parse_data(data: dict | str) -> dict:
    """Accept either a Python dictionary or JSON string."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            frappe.throw(_("Invalid JSON data."))

    if not isinstance(data, dict):
        frappe.throw(_("Data must be an object."))

    return data


@frappe.whitelist()
def get_dashboard_data() -> dict:
    """Fetch dashboard data for the logged-in technician."""
    services.require_technician()

    mechanic_roles = frappe.db.get_all("Has Role", filters={"role": "vms mechanic"}, fields=["parent"])
    mechanic_names = [m.parent for m in mechanic_roles]
    users = []
    if mechanic_names:
        users = frappe.get_all("User", **apply_pagination({
            "filters": {"name": ["in", mechanic_names], "enabled": 1},
            "fields": ["name", "full_name"],
            "ignore_permissions": True
        }))

    customer_roles = frappe.db.get_all("Has Role", filters={"role": "vms customer"}, fields=["parent"])
    customer_names = [c.parent for c in customer_roles]
    customers = []
    if customer_names:
        customers = frappe.get_all("User", **apply_pagination({
            "filters": {"name": ["in", customer_names], "enabled": 1},
            "fields": ["name", "full_name"],
            "ignore_permissions": True
        }))

    return {
        "inspections": services.list_inspections(),
        "spare_parts": services.list_spare_parts(),
        "vehicles": services.list_vehicles(),
        "users": users,
        "customers": customers,
    }


@frappe.whitelist()
def get_inspections() -> list:
    return services.list_inspections()


@frappe.whitelist()
def get_my_vehicle_inspections(vehicle_name: str | None = None) -> list:
    """Return inspections for vehicles belonging to the logged-in customer."""
    return services.list_customer_vehicle_inspections(vehicle_name)


@frappe.whitelist()
def get_inspection_details(name: str | None = None) -> dict:
    """Retrieve full details of an inspection document."""
    name = name or frappe.form_dict.get("name")
    if not name:
        frappe.throw(_("Inspection name is required."))
    doc = services.get_inspection(name)
    return {
        "name": doc.name,
        "vehicle_number": doc.vehicle_number,
        "customer_name": doc.customer_name,
        "inspection_date": str(doc.inspection_date),
        "issue": doc.issue,
        "spare_parts": doc.spare_parts,
        "spare_part_quantity": doc.spare_part_quantity,
        "technician": doc.technician,
        "mechanic": doc.mechanic,
        "labour_hour": doc.labour_hour,
        "inspected": doc.inspected,
    }


@frappe.whitelist()
def get_spare_parts() -> list:
    return services.list_spare_parts()


@frappe.whitelist()
def get_vehicles() -> list:
    return services.list_vehicles()


@frappe.whitelist()
def create_inspection(data: dict | str) -> dict:
    return services.create_inspection(parse_data(data))


@frappe.whitelist()
def update_inspection(name: str, data: dict | str) -> dict:
    return services.update_inspection(name, parse_data(data))


@frappe.whitelist()
def delete_inspection(name: str) -> dict:
    return services.delete_inspection(name)


@frappe.whitelist()
def create_spare_part(data: dict | str) -> dict:
    return services.create_spare_part(parse_data(data))


@frappe.whitelist()
def update_spare_part(name: str, data: dict | str) -> dict:
    return services.update_spare_part(name, parse_data(data))


@frappe.whitelist()
def delete_spare_part(name: str) -> dict:
    return services.delete_spare_part(name)


def dump_technician_dashboard():
    doc = frappe.get_doc("Web Page", "technician-dashboard")
    with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/technician-dashboard.css", "w") as f:
        f.write(doc.css or "")
    with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/technician-dashboard.html", "w") as f:
        f.write(doc.main_section_html or "")
    return "dumped"


def sync_technician_dashboard():
    doc = frappe.get_doc("Web Page", "technician-dashboard")

    import os
    base_dir = frappe.get_app_path("vms_user")
    
    js_paths = [
        os.path.join(base_dir, "public", "js", "technician-dashboard.js"),
        os.path.join(base_dir, "www", "vms_user_dashboard", "technician_dashboard", "technician-dashboard.js"),
    ]
    for p in js_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                doc.javascript = f.read()
            break

    css_paths = [
        os.path.join(base_dir, "public", "css", "technician-dashboard.css"),
        os.path.join(base_dir, "www", "vms_user_dashboard", "technician_dashboard", "technician-dashboard.css"),
    ]
    for p in css_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                doc.css = f.read()
            break

    html_paths = [
        os.path.join(base_dir, "www", "vms_user_dashboard", "technician_dashboard", "technician-dashboard.html"),
    ]
    for p in html_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                doc.main_section_html = f.read()
            break

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return "synced"