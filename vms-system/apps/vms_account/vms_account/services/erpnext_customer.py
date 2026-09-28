# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from vms_account.services.erpnext_permissions import require_staff
from vms_user.pagination import get_paginated_data


def get_customers(page=None, search=None):
    """Return ERPNext Customer list."""
    require_staff()
    filters = [["Customer", "disabled", "!=", 1]]

    if search:
        search_str = str(search).strip()
        or_filters = [
            {"name": ["like", f"%{search_str}%"]},
            {"customer_name": ["like", f"%{search_str}%"]},
        ]
    else:
        or_filters = None

    customers = get_paginated_data(
        "Customer",
        page=page,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "customer_name", "customer_type", "customer_group", "territory", "creation"],
        order_by="customer_name asc"
    )

    if customers:
        c_names = [c["name"] for c in customers]
        # Query total outstanding amount for each customer from Sales Invoices
        outstandings = frappe.db.sql(
            """
            SELECT customer, SUM(outstanding_amount) as total_outstanding
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND customer IN %s
            GROUP BY customer
            """,
            (tuple(c_names),),
            as_dict=True
        )
        out_map = {o["customer"]: flt(o["total_outstanding"]) for o in outstandings}
        for c in customers:
            c["outstanding_amount"] = round(out_map.get(c["name"], 0.0), 2)

    return customers


def get_customer_outstanding(customer_name: str) -> dict:
    """Return total outstanding amount for a customer across all Sales Invoices."""
    require_staff()
    if not customer_name:
        frappe.throw(_("Customer name is required."))

    res = frappe.db.sql(
        """
        SELECT SUM(outstanding_amount) as total_outstanding, COUNT(name) as invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND (customer = %s OR customer_name = %s)
        """,
        (customer_name, customer_name),
        as_dict=True
    )

    total_out = flt(res[0]["total_outstanding"]) if res and res[0]["total_outstanding"] else 0.0
    count = int(res[0]["invoice_count"]) if res and res[0]["invoice_count"] else 0

    return {
        "customer": customer_name,
        "outstanding_amount": round(total_out, 2),
        "unpaid_invoices_count": count,
    }


def create_or_update_customer(customer_name: str, customer_type: str = "Individual", custom_vms_user: str | None = None) -> dict:
    """Create or update an ERPNext Customer record."""
    require_staff()
    if not customer_name:
        frappe.throw(_("Customer name is required."))

    c_name = customer_name.strip()
    existing = frappe.db.get_value("Customer", {"customer_name": c_name}, "name")
    if existing:
        cust = frappe.get_doc("Customer", existing)
        if custom_vms_user and hasattr(cust, "custom_vms_user"):
            cust.custom_vms_user = custom_vms_user
            cust.save(ignore_permissions=True)
        return {"success": True, "name": cust.name, "customer_name": cust.customer_name}

    cust = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": c_name,
        "customer_type": customer_type,
        "customer_group": "All Customer Groups",
        "territory": "All Territories",
    })
    if custom_vms_user and hasattr(cust, "custom_vms_user"):
        cust.custom_vms_user = custom_vms_user

    cust.insert(ignore_permissions=True, ignore_mandatory=True)
    return {"success": True, "name": cust.name, "customer_name": cust.customer_name}

