# =========================================================
# FILE: vms_account/api.py
# PURPOSE: Whitelisted ERPNext integration APIs for VMS accounting,
#          inventory consumption, billing, invoices, and payments.
# =========================================================

import frappe
from frappe import _
from vms_account import services
from vms_account.utils.validators import parse_json


@frappe.whitelist()
def get_dashboard_data(
    inspection_page: int | str | None = None,
    invoice_page: int | str | None = None,
    item_page: int | str | None = None,
    page: int | str | None = None,
) -> dict:
    """Return dashboard metrics, billing data, invoices, and spare part items."""
    if inspection_page is None:
        inspection_page = frappe.form_dict.get("inspection_page") or page or 1
    if invoice_page is None:
        invoice_page = frappe.form_dict.get("invoice_page") or page or 1
    if item_page is None:
        item_page = frappe.form_dict.get("item_page") or page or 1

    return services.get_accountant_dashboard_data(
        inspection_page=inspection_page,
        invoice_page=invoice_page,
        item_page=item_page,
    )


@frappe.whitelist()
def get_spare_part_items(page: int | str | None = None, search: str | None = None) -> list:
    """Get active ERPNext Items for spare parts."""
    return services.get_spare_part_items(page=page, search=search)


@frappe.whitelist()
def get_item_stock_availability(item_code: str, warehouse: str | None = None) -> dict:
    """Get stock availability for an Item in a warehouse or total."""
    return services.get_item_stock_availability(item_code=item_code, warehouse=warehouse)


@frappe.whitelist()
def get_warehouses() -> list:
    """Get list of active non-group Warehouses."""
    return services.get_warehouses()


@frappe.whitelist()
def get_customers(page: int | str | None = None, search: str | None = None) -> list:
    """Get list of ERPNext Customers."""
    return services.get_customers(page=page, search=search)


@frappe.whitelist()
def get_suppliers(page: int | str | None = None, search: str | None = None) -> list:
    """Get list of ERPNext Suppliers."""
    return services.get_suppliers(page=page, search=search)


@frappe.whitelist()
def get_service_billing_data(page: int | str | None = None) -> list:
    """Get completed vehicle service inspections awaiting billing."""
    return services.get_service_billing_data(page=page)


@frappe.whitelist()
def get_consumed_spare_parts(inspection_name: str) -> list:
    """Get consumed spare part items for an inspection."""
    return services.get_consumed_spare_parts(inspection_name=inspection_name)


@frappe.whitelist()
def create_stock_consumption_entry(data: dict | str = None, inspection_name: str | None = None, warehouse: str | None = None) -> dict:
    """Create and submit an ERPNext Stock Entry (Material Issue) for consumed spare parts."""
    if data:
        p = parse_json(data)
        inspection_name = p.get("inspection_name") or inspection_name
        warehouse = p.get("warehouse") or warehouse

    inspection_name = inspection_name or frappe.form_dict.get("inspection_name")
    return services.create_stock_consumption_entry(inspection_name=inspection_name, warehouse=warehouse)


@frappe.whitelist()
def create_sales_invoice(data: dict | str = None, inspection_name: str | None = None, posting_date: str | None = None, due_date: str | None = None, submit: bool | str = False) -> dict:
    """Create an ERPNext Sales Invoice for a completed vehicle service inspection."""
    if data:
        p = parse_json(data)
        inspection_name = p.get("inspection_name") or inspection_name
        posting_date = p.get("posting_date") or posting_date
        due_date = p.get("due_date") or due_date
        submit = p.get("submit") if "submit" in p else submit

    inspection_name = inspection_name or frappe.form_dict.get("inspection_name")
    sub = True if str(submit).lower() in ["true", "1"] else False
    return services.create_sales_invoice(
        inspection_name=inspection_name,
        posting_date=posting_date,
        due_date=due_date,
        submit=sub
    )


@frappe.whitelist()
def get_sales_invoice(name: str | None = None) -> dict:
    """Get ERPNext Sales Invoice document details."""
    name = name or frappe.form_dict.get("name")
    return services.get_sales_invoice(name=name)


@frappe.whitelist()
def get_invoice_list(page: int | str | None = None, status: str | None = None, customer: str | None = None) -> list:
    """Get paginated list of ERPNext Sales Invoice records."""
    return services.get_invoice_list(page=page, status=status, customer=customer)


@frappe.whitelist()
def create_payment_entry(data: dict | str = None, sales_invoice: str | None = None, paid_amount: float | str | None = None, mode_of_payment: str | None = None) -> dict:
    """Create and submit an ERPNext Payment Entry against a Sales Invoice."""
    if data:
        p = parse_json(data)
        sales_invoice = p.get("sales_invoice") or sales_invoice
        paid_amount = p.get("paid_amount") or paid_amount
        mode_of_payment = p.get("mode_of_payment") or mode_of_payment

    sales_invoice = sales_invoice or frappe.form_dict.get("sales_invoice")
    amount = frappe.utils.flt(paid_amount or frappe.form_dict.get("paid_amount"))
    mode = mode_of_payment or frappe.form_dict.get("mode_of_payment") or "Cash"

    return services.create_payment_entry(
        sales_invoice=sales_invoice,
        paid_amount=amount,
        mode_of_payment=mode
    )


@frappe.whitelist()
def get_customer_outstanding(customer: str | None = None) -> dict:
    """Get total outstanding balance for a customer."""
    customer = customer or frappe.form_dict.get("customer")
    return services.get_customer_outstanding(customer_name=customer)


@frappe.whitelist()
def get_purchase_billing_info(page: int | str | None = None) -> list:
    """Get ERPNext Purchase Invoices."""
    return services.get_purchase_billing_info(page=page)


@frappe.whitelist()
def get_accounting_reports() -> dict:
    """Get ERPNext General Ledger & AR reports."""
    return services.get_accounting_reports()


# =========================================================
# LEGACY & FRONTEND ALIAS ENDPOINTS
# =========================================================

@frappe.whitelist()
def create_invoice(
    customer_name: str | None = None,
    vehicle_inspection: str | None = None,
    inspection_name: str | None = None,
    invoice_date: str | None = None,
    total_bill: float | str | None = None,
    **kwargs
) -> dict:
    """Legacy alias: Create an ERPNext Sales Invoice for a vehicle inspection."""
    insp = vehicle_inspection or inspection_name or frappe.form_dict.get("vehicle_inspection") or frappe.form_dict.get("inspection_name")
    if not insp:
        frappe.throw(_("Vehicle Inspection is required to create invoice."))
    return create_sales_invoice(
        inspection_name=insp,
        posting_date=invoice_date or frappe.form_dict.get("invoice_date"),
        submit=True
    )


@frappe.whitelist()
def get_customer_invoice_details(invoice_name: str | None = None, name: str | None = None) -> dict:
    """Legacy alias: Get ERPNext Sales Invoice details."""
    inv_name = invoice_name or name or frappe.form_dict.get("invoice_name") or frappe.form_dict.get("name")
    return get_sales_invoice(name=inv_name)


@frappe.whitelist()
def update_invoice(invoice_name: str | None = None, name: str | None = None, **kwargs) -> dict:
    """Legacy alias: Return Sales Invoice details or update if draft."""
    inv_name = invoice_name or name or frappe.form_dict.get("invoice_name") or frappe.form_dict.get("name")
    return get_sales_invoice(name=inv_name)


@frappe.whitelist()
def audit_invoice(invoice_name: str | None = None, name: str | None = None) -> dict:
    """Legacy alias: Process payment audit by creating ERPNext Payment Entry."""
    inv_name = invoice_name or name or frappe.form_dict.get("invoice_name") or frappe.form_dict.get("name")
    if not inv_name:
        frappe.throw(_("Invoice Name is required"))
    inv = frappe.get_doc("Sales Invoice", inv_name)
    if inv.outstanding_amount > 0:
        return create_payment_entry(sales_invoice=inv_name, paid_amount=inv.outstanding_amount)
    return {"success": True, "message": _("Invoice is already fully paid.")}


@frappe.whitelist()
def toggle_payment(invoice_name: str | None = None, payment: int | str | bool = 1) -> dict:
    """Customer or accountant toggling payment creates an ERPNext Payment Entry."""
    inv_name = invoice_name or frappe.form_dict.get("invoice_name")
    if not inv_name:
        frappe.throw(_("Invoice Name is required"))
    inv = frappe.get_doc("Sales Invoice", inv_name)
    if inv.outstanding_amount > 0:
        res = create_payment_entry(sales_invoice=inv_name, paid_amount=inv.outstanding_amount)
        return {"success": True, "message": _("Payment Entry created successfully."), "doc": res}
    return {"success": True, "message": _("Invoice is already paid.")}


@frappe.whitelist()
def get_my_invoices(only_audited: int | str | None = 0) -> list:
    """Get Sales Invoices for logged in customer."""
    user = frappe.session.user
    customer = frappe.db.get_value("Customer", {"custom_vms_user": user}, "name")
    if not customer:
        customer = frappe.db.get_value("Customer", {"customer_name": user}, "name")
    if not customer:
        return []
    return get_invoice_list(customer=customer)