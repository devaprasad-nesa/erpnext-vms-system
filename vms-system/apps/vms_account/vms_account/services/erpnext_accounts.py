# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from vms_account.services.erpnext_permissions import require_accountant
from vms_account.services.erpnext_sales import get_service_billing_data, get_invoice_list
from vms_account.services.erpnext_item import get_spare_part_items
from vms_account.services.erpnext_customer import get_customers
from vms_account.services.erpnext_stock import get_warehouses


def get_accountant_dashboard_data(
    inspection_page: int = None,
    invoice_page: int = None,
    item_page: int = None,
) -> dict:
    """
    Return comprehensive dashboard data for VMS Accountant using ERPNext native data.
    """
    require_accountant()

    inspections = get_service_billing_data(page=inspection_page)
    invoices = get_invoice_list(page=invoice_page)
    spare_parts = get_spare_part_items(page=item_page)
    warehouses = get_warehouses()
    customers = get_customers()

    # Calculate Summary Stats
    total_sales_res = frappe.db.sql(
        """
        SELECT SUM(grand_total) as total_sales, SUM(outstanding_amount) as total_outstanding
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        """,
        as_dict=True
    )

    total_revenue = flt(total_sales_res[0]["total_sales"]) if total_sales_res and total_sales_res[0]["total_sales"] else 0.0
    total_outstanding = flt(total_sales_res[0]["total_outstanding"]) if total_sales_res and total_sales_res[0]["total_outstanding"] else 0.0
    total_paid = round(total_revenue - total_outstanding, 2)

    pending_billing_count = sum(1 for i in inspections if not i.get("billed"))
    low_stock_count = sum(1 for s in spare_parts if flt(str(s.get("quantity", "0")).split()[0]) <= 5.0)

    pagination_data = getattr(frappe.local, "response", {}).get("pagination", {})

    return {
        "inspections": inspections,
        "invoices": invoices,
        "spare_parts": spare_parts,
        "warehouses": warehouses,
        "customers": customers,
        "stats": {
            "total_revenue": round(total_revenue, 2),
            "total_outstanding": round(total_outstanding, 2),
            "total_paid": round(total_paid, 2),
            "pending_billing_count": pending_billing_count,
            "low_stock_count": low_stock_count,
            "total_invoices_count": len(invoices),
        },
        "pagination": pagination_data,
    }


def get_accounting_reports() -> dict:
    """Return summary reports for General Ledger & Accounts Receivable."""
    require_accountant()

    monthly_sales = frappe.db.sql(
        """
        SELECT DATE_FORMAT(posting_date, '%%Y-%%m') as month, SUM(grand_total) as total
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month desc
        LIMIT 12
        """,
        as_dict=True
    )

    top_customers = frappe.db.sql(
        """
        SELECT customer_name, SUM(grand_total) as total_billed, SUM(outstanding_amount) as outstanding
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        GROUP BY customer_name
        ORDER BY total_billed desc
        LIMIT 5
        """,
        as_dict=True
    )

    return {
        "monthly_sales": monthly_sales,
        "top_customers": top_customers,
    }
