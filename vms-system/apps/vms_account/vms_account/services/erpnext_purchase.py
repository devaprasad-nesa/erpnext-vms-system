# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from vms_account.services.erpnext_permissions import require_staff
from vms_user.pagination import get_paginated_data


def get_suppliers(page=None, search=None):
    """Return ERPNext Supplier list."""
    require_staff()
    filters = {"disabled": 0}

    if search:
        search_str = str(search).strip()
        or_filters = [
            {"name": ["like", f"%{search_str}%"]},
            {"supplier_name": ["like", f"%{search_str}%"]},
        ]
    else:
        or_filters = None

    return get_paginated_data(
        "Supplier",
        page=page,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "supplier_name", "supplier_group", "country", "creation"],
        order_by="supplier_name asc"
    )


def get_purchase_billing_info(page=None):
    """Return recent ERPNext Purchase Invoices."""
    require_staff()
    return get_paginated_data(
        "Purchase Invoice",
        page=page,
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "posting_date",
            "grand_total",
            "outstanding_amount",
            "status",
            "docstatus",
            "creation"
        ],
        order_by="posting_date desc, creation desc"
    )
