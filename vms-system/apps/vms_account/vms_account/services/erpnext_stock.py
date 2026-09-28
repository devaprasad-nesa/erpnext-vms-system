# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today
from vms_account.services.erpnext_permissions import require_accountant, require_staff
from vms_user.services.seed_vms_erpnext_data import get_default_company, get_default_warehouse


def get_warehouses():
    """Return active ERPNext non-group Warehouses."""
    require_staff()
    company = get_default_company()
    return frappe.get_all(
        "Warehouse",
        filters={"company": company, "is_group": 0, "disabled": 0},
        fields=["name", "warehouse_name", "company", "parent_warehouse"],
        order_by="warehouse_name asc"
    )


def get_item_stock_availability(item_code: str, warehouse: str = None) -> dict:
    """Return stock balance for an Item in a warehouse or total balance."""
    require_staff()
    if not item_code:
        frappe.throw(_("Item code is required."))

    filters = {"item_code": item_code}
    if warehouse:
        filters["warehouse"] = warehouse

    actual_qty = flt(frappe.db.get_value("Bin", filters, "sum(actual_qty)") or 0.0)
    reserved_qty = flt(frappe.db.get_value("Bin", filters, "sum(reserved_qty)") or 0.0)

    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"

    return {
        "item_code": item_code,
        "warehouse": warehouse or "All Warehouses",
        "actual_qty": actual_qty,
        "reserved_qty": reserved_qty,
        "available_qty": max(0.0, actual_qty - reserved_qty),
        "stock_uom": stock_uom,
        "formatted": f"{actual_qty} {stock_uom}"
    }


def create_stock_consumption_entry(inspection_name: str, warehouse: str = None) -> dict:
    """
    Record inventory consumption for spare parts used in a completed Vehicle Inspection.
    Creates and submits an ERPNext Stock Entry of type 'Material Issue'.
    """
    require_accountant()
    if not inspection_name:
        frappe.throw(_("Inspection name is required."))

    if not frappe.db.exists("vms vehicle inspection", inspection_name):
        frappe.throw(_("Inspection '{0}' does not exist.").format(inspection_name))

    inspection = frappe.get_doc("vms vehicle inspection", inspection_name)
    child_parts = inspection.get("spare_parts") or []

    if not child_parts:
        return {
            "success": True,
            "message": _("No spare parts attached to this inspection. Stock entry not required."),
            "stock_entry": None,
        }

    # Check if a Stock Entry has already been submitted for this inspection
    existing_se = frappe.db.get_value(
        "Stock Entry",
        {"remarks": ["like", f"%VMS Vehicle Inspection {inspection_name}%"], "docstatus": 1},
        "name"
    )
    if existing_se:
        return {
            "success": True,
            "message": _("Stock Entry '{0}' already submitted for this inspection.").format(existing_se),
            "stock_entry": existing_se,
        }

    company = get_default_company()
    source_wh = warehouse or get_default_warehouse(company)

    items_to_issue = []
    for row in child_parts:
        code = row.item_code or row.part_name
        qty = flt(row.qty)
        if not code or qty <= 0:
            continue

        # Verify Item exists in ERPNext
        if not frappe.db.exists("Item", code):
            alt_code = frappe.db.get_value("Item", {"item_name": code}, "name")
            if alt_code:
                code = alt_code
            else:
                frappe.throw(_("Item '{0}' not found in ERPNext Item master.").format(code))

        item_wh = row.get("warehouse") or source_wh
        uom = frappe.db.get_value("Item", code, "stock_uom") or "Nos"
        rate = flt(row.cost or frappe.db.get_value("Item", code, "standard_rate") or 0.0)

        items_to_issue.append({
            "item_code": code,
            "qty": qty,
            "s_warehouse": item_wh,
            "uom": uom,
            "stock_uom": uom,
            "conversion_factor": 1.0,
            "basic_rate": rate,
        })

    if not items_to_issue:
        frappe.throw(_("No valid stock Items found to issue for this inspection."))

    se_doc = frappe.get_doc({
        "doctype": "Stock Entry",
        "purpose": "Material Issue",
        "stock_entry_type": "Material Issue",
        "company": company,
        "from_warehouse": source_wh,
        "posting_date": today(),
        "remarks": f"Stock consumption for VMS Vehicle Inspection {inspection_name}",
        "items": items_to_issue,
    })

    se_doc.insert(ignore_permissions=True)
    se_doc.submit()

    return {
        "success": True,
        "message": _("Stock Entry '{0}' submitted successfully.").format(se_doc.name),
        "stock_entry": se_doc.name,
    }
