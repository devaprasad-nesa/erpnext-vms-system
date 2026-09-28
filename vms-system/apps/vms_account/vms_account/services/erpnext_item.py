# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from vms_account.services.erpnext_permissions import require_staff
from vms_user.pagination import get_paginated_data


def get_spare_part_items(page=None, search=None):
    """
    Return available spare-part Items from ERPNext Item master.
    Includes item_code, item_name, rate, and total stock balance.
    """
    require_staff()
    filters = {"disabled": 0, "is_stock_item": 1}

    if search:
        search_str = str(search).strip()
        or_filters = [
            {"item_code": ["like", f"%{search_str}%"]},
            {"item_name": ["like", f"%{search_str}%"]},
        ]
    else:
        or_filters = None

    items = get_paginated_data(
        "Item",
        page=page,
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "item_code",
            "item_name",
            "item_group",
            "stock_uom",
            "standard_rate",
            "valuation_rate",
        ],
        order_by="item_name asc"
    )

    if items:
        item_codes = [i["item_code"] for i in items]
        # Query total actual_qty across all warehouses from Bin table
        bins = frappe.db.sql(
            """
            SELECT item_code, SUM(actual_qty) as total_qty
            FROM `tabBin`
            WHERE item_code IN %s
            GROUP BY item_code
            """,
            (tuple(item_codes),),
            as_dict=True
        )
        qty_map = {b["item_code"]: flt(b["total_qty"]) for b in bins}

        for i in items:
            code = i["item_code"]
            total_qty = qty_map.get(code, 0.0)
            uom = i.get("stock_uom") or "Nos"
            i["quantity"] = f"{total_qty} {uom}".strip() if total_qty > 0 else f"0 {uom}"
            i["cost"] = flt(i.get("standard_rate") or i.get("valuation_rate") or 0.0)
            i["part_name"] = i.get("item_name") or code

    return items


def get_item_details(item_code: str) -> dict:
    """Load an ERPNext Item document by code."""
    require_staff()
    if not item_code:
        frappe.throw(_("Item code is required."))

    item = frappe.db.get_value(
        "Item",
        item_code,
        ["name", "item_code", "item_name", "item_group", "stock_uom", "standard_rate", "valuation_rate", "disabled"],
        as_dict=True,
    )

    if not item:
        frappe.throw(_("Item '{0}' not found.").format(item_code))

    res = frappe.db.sql("SELECT SUM(actual_qty) FROM `tabBin` WHERE item_code = %s", (item_code,))
    total_qty = flt(res[0][0]) if res and res[0][0] is not None else 0.0
    uom = item.get("stock_uom") or "Nos"
    item["quantity"] = f"{total_qty} {uom}".strip()
    item["cost"] = flt(item.get("standard_rate") or item.get("valuation_rate") or 0.0)
    item["part_name"] = item.get("item_name") or item_code

    return item
