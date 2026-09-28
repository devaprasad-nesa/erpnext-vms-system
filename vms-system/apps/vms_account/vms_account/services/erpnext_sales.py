# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today, add_days
from vms_account.services.erpnext_permissions import require_accountant, require_staff, get_current_user_roles
from vms_user.pagination import get_paginated_data
from vms_user.services.seed_vms_erpnext_data import get_default_company, get_default_warehouse


def resolve_erpnext_customer(customer_input: str) -> str:
    """Ensure customer exists in ERPNext Customer master."""
    if not customer_input:
        frappe.throw(_("Customer name is required."))

    val = str(customer_input).strip()

    # 1. Exact match by name
    if frappe.db.exists("Customer", val):
        return val

    # 2. Match by customer_name
    c_name = frappe.db.get_value("Customer", {"customer_name": val}, "name")
    if c_name:
        return c_name

    # 3. Create missing ERPNext Customer automatically
    cust_doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": val,
        "customer_type": "Individual",
        "customer_group": "All Customer Groups",
        "territory": "All Territories",
    })
    cust_doc.insert(ignore_permissions=True, ignore_mandatory=True)
    return cust_doc.name


def get_service_billing_data(page=None) -> list[dict]:
    """Fetch completed vehicle inspections ready for ERPNext Sales Invoice creation."""
    require_accountant()
    inspections = get_paginated_data(
        "vms vehicle inspection",
        page=page,
        filters={"inspected": 1},
        fields=[
            "name",
            "vehicle_number",
            "customer_name",
            "inspection_date",
            "issue",
            "labour_hour",
            "technician",
            "mechanic",
            "creation",
            "modified",
        ],
        order_by="modified desc"
    )

    if inspections:
        insp_names = [i["name"] for i in inspections]
        # Fetch linked ERPNext Sales Invoices
        invoices = frappe.db.sql(
            """
            SELECT name, customer, grand_total, outstanding_amount, status, docstatus, remarks
            FROM `tabSales Invoice`
            WHERE remarks LIKE '%%Inspection Billing for%%' OR remarks LIKE '%%Vehicle Inspection%%'
            """,
            as_dict=True
        )
        invoice_map = {}
        for inv in invoices:
            rem = inv.get("remarks") or ""
            for name in insp_names:
                if name in rem:
                    invoice_map[name] = inv

        # Load child spare parts for each inspection
        child_parts = frappe.db.sql(
            """
            SELECT parent, item_code, part_name, qty, cost, amount
            FROM `tabvms spare part`
            WHERE parent IN %s AND parenttype = 'vms vehicle inspection' AND parentfield = 'spare_parts'
            ORDER BY idx ASC
            """,
            (tuple(insp_names),),
            as_dict=True
        )
        parts_map = {}
        for cp in child_parts:
            parts_map.setdefault(cp.parent, []).append({
                "item_code": cp.item_code or cp.part_name,
                "part_name": cp.part_name,
                "qty": flt(cp.qty),
                "cost": flt(cp.cost),
                "amount": flt(cp.amount or (flt(cp.qty) * flt(cp.cost))),
            })

        for i in inspections:
            name = i["name"]
            p_list = parts_map.get(name, [])
            i["spare_parts"] = p_list
            i["parts_cost"] = round(sum(p["amount"] for p in p_list), 2)
            i["labour_cost"] = round(flt(i.get("labour_hour") or 0) * 500.0, 2)
            i["total_estimated_bill"] = round(i["parts_cost"] + i["labour_cost"], 2)

            inv = invoice_map.get(name)
            if inv:
                i["invoice_name"] = inv["name"]
                i["invoice_status"] = inv["status"]
                i["invoice_grand_total"] = flt(inv["grand_total"])
                i["invoice_outstanding"] = flt(inv["outstanding_amount"])
                i["billed"] = True
            else:
                i["invoice_name"] = None
                i["invoice_status"] = "Pending Invoice"
                i["invoice_grand_total"] = 0.0
                i["invoice_outstanding"] = 0.0
                i["billed"] = False

    return inspections


def get_consumed_spare_parts(inspection_name: str) -> list[dict]:
    """Get spare parts consumed in a specific vehicle inspection."""
    require_staff()
    if not inspection_name:
        frappe.throw(_("Inspection name is required."))

    child_rows = frappe.db.sql(
        """
        SELECT name, item_code, part_name, qty, cost, amount, available_qty, warehouse
        FROM `tabvms spare part`
        WHERE parent = %s AND parenttype = 'vms vehicle inspection' AND parentfield = 'spare_parts'
        ORDER BY idx ASC
        """,
        (inspection_name,),
        as_dict=True
    )

    for row in child_rows:
        row["qty"] = flt(row["qty"])
        row["cost"] = flt(row["cost"])
        row["amount"] = flt(row["amount"] or (row["qty"] * row["cost"]))

    return child_rows


def create_sales_invoice(
    inspection_name: str,
    posting_date: str = None,
    due_date: str = None,
    items: list = None,
    submit: bool = False,
) -> dict:
    """
    Create an ERPNext Sales Invoice for a completed vehicle service inspection.
    Includes used spare-part Items and service labour charges.
    """
    require_accountant()
    if not inspection_name:
        frappe.throw(_("Inspection name is required."))

    if not frappe.db.exists("vms vehicle inspection", inspection_name):
        frappe.throw(_("Inspection '{0}' does not exist.").format(inspection_name))

    inspection = frappe.get_doc("vms vehicle inspection", inspection_name)

    # Prevent duplicate sales invoice creation for the same inspection
    existing_inv = frappe.db.get_value(
        "Sales Invoice",
        {"remarks": ["like", f"%Inspection Billing for {inspection_name}%"], "docstatus": ["in", [0, 1]]},
        ["name", "docstatus", "status"],
        as_dict=True
    )
    if existing_inv:
        return {
            "success": True,
            "message": _("Sales Invoice '{0}' already exists for this inspection.").format(existing_inv["name"]),
            "invoice_name": existing_inv["name"],
            "status": existing_inv["status"],
            "docstatus": existing_inv["docstatus"],
        }

    company = get_default_company()
    customer = resolve_erpnext_customer(inspection.customer_name)
    warehouse = get_default_warehouse(company)
    p_date = posting_date or today()
    d_date = due_date or add_days(p_date, 7)

    invoice_items = []

    # 1. Add consumed spare part items
    child_parts = inspection.get("spare_parts") or []
    for cp in child_parts:
        code = cp.item_code or cp.part_name
        qty = flt(cp.qty)
        rate = flt(cp.cost)

        if not code or qty <= 0:
            continue

        if not frappe.db.exists("Item", code):
            alt_code = frappe.db.get_value("Item", {"item_name": code}, "name")
            if alt_code:
                code = alt_code
            else:
                # Fallback: seed/create item
                item_doc = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": code,
                    "item_name": cp.part_name or code,
                    "item_group": "Spare Parts",
                    "stock_uom": "Nos",
                    "is_stock_item": 1,
                    "standard_rate": rate,
                })
                item_doc.insert(ignore_permissions=True)

        uom = frappe.db.get_value("Item", code, "stock_uom") or "Nos"
        if not rate:
            rate = flt(frappe.db.get_value("Item", code, "standard_rate") or 0.0)

        invoice_items.append({
            "item_code": code,
            "item_name": cp.part_name or code,
            "qty": qty,
            "rate": rate,
            "uom": uom,
            "warehouse": cp.get("warehouse") or warehouse,
            "description": f"Spare Part: {cp.part_name or code}",
        })

    # 2. Add Labour Service Item if labour hours > 0
    labour_hours = flt(inspection.labour_hour or 0)
    if labour_hours > 0:
        labour_item_code = "INSP-LABOUR"
        if not frappe.db.exists("Item", labour_item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": labour_item_code,
                "item_name": "Vehicle Inspection & Diagnostic Labour",
                "item_group": "Vehicle Services",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "standard_rate": 500.0,
            }).insert(ignore_permissions=True)

        invoice_items.append({
            "item_code": labour_item_code,
            "item_name": "Vehicle Inspection & Diagnostic Labour",
            "qty": labour_hours,
            "rate": 500.0,
            "uom": "Nos",
            "description": f"Labour charges for {labour_hours} hours @ ₹500/hr",
        })

    if not invoice_items:
        frappe.throw(_("No items or labour hours found to bill for this inspection."))

    inv_doc = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": company,
        "customer": customer,
        "posting_date": p_date,
        "due_date": d_date,
        "remarks": f"Inspection Billing for {inspection_name}, Vehicle: {inspection.vehicle_number}",
        "items": invoice_items,
    })

    inv_doc.insert(ignore_permissions=True)

    if submit:
        inv_doc.submit()

    # Trigger stock consumption if spare parts were used
    if child_parts:
        try:
            from vms_account.services.erpnext_stock import create_stock_consumption_entry
            create_stock_consumption_entry(inspection_name=inspection_name, warehouse=warehouse)
        except Exception as e:
            frappe.log_error(f"Stock consumption creation notice for inspection {inspection_name}: {str(e)}", "VMS Stock Notice")

    return {
        "success": True,
        "message": _("Sales Invoice '{0}' created successfully.").format(inv_doc.name),
        "invoice_name": inv_doc.name,
        "grand_total": flt(inv_doc.grand_total),
        "outstanding_amount": flt(inv_doc.outstanding_amount),
        "status": inv_doc.status,
        "docstatus": inv_doc.docstatus,
    }


def get_sales_invoice(name: str) -> dict:
    """Retrieve full details of an ERPNext Sales Invoice."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if not name:
        frappe.throw(_("Sales Invoice name is required."))

    if not frappe.db.exists("Sales Invoice", name):
        frappe.throw(_("Sales Invoice '{0}' does not exist.").format(name))

    doc = frappe.get_doc("Sales Invoice", name)

    roles = get_current_user_roles()
    is_staff = bool(user == "Administrator" or roles.intersection({"system manager", "vms manager", "vms accountant", "vms technician"}))

    if not is_staff:
        # Customer authorization check: verify customer owns the invoice
        if doc.customer != user and doc.customer_name != user:
            frappe.throw(_("You can only access your own Sales Invoices."), frappe.PermissionError)

    items_list = []
    for item in doc.items:
        items_list.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": flt(item.qty),
            "rate": flt(item.rate),
            "amount": flt(item.amount),
            "description": item.description or "",
        })

    return {
        "name": doc.name,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "posting_date": str(doc.posting_date),
        "due_date": str(doc.due_date),
        "grand_total": flt(doc.grand_total),
        "outstanding_amount": flt(doc.outstanding_amount),
        "status": doc.status,
        "docstatus": doc.docstatus,
        "remarks": doc.remarks or "",
        "items": items_list,
    }


def get_invoice_list(page=None, status=None, customer=None) -> list[dict]:
    """Return paginated list of ERPNext Sales Invoice records."""
    user = getattr(frappe.session, "user", None) or "Guest"
    roles = get_current_user_roles()
    is_staff = bool(user == "Administrator" or roles.intersection({"system manager", "vms manager", "vms accountant", "vms technician"}))

    filters = {}
    if not is_staff:
        filters["customer"] = user

    if status:
        filters["status"] = status
    if customer and is_staff:
        filters["customer"] = customer

    invoices = get_paginated_data(
        "Sales Invoice",
        page=page,
        filters=filters,
        fields=[
            "name",
            "customer",
            "customer_name",
            "posting_date",
            "due_date",
            "grand_total",
            "outstanding_amount",
            "status",
            "docstatus",
            "remarks",
            "creation"
        ],
        order_by="posting_date desc, creation desc"
    )

    for inv in invoices:
        inv["grand_total"] = flt(inv["grand_total"])
        inv["outstanding_amount"] = flt(inv["outstanding_amount"])
        inv["paid_amount"] = round(inv["grand_total"] - inv["outstanding_amount"], 2)

    return invoices
