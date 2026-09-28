# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today
from vms_account.services.erpnext_permissions import require_accountant
from vms_user.services.seed_vms_erpnext_data import get_default_company


def create_payment_entry(
    sales_invoice: str,
    paid_amount: float,
    mode_of_payment: str = "Cash",
    reference_no: str = None,
) -> dict:
    """
    Create and submit an ERPNext Payment Entry against a Sales Invoice.
    Automatically updates invoice status, outstanding balance, and GL entries in ERPNext.
    """
    require_accountant()
    if not sales_invoice:
        frappe.throw(_("Sales Invoice is required."))

    if not frappe.db.exists("Sales Invoice", sales_invoice):
        frappe.throw(_("Sales Invoice '{0}' does not exist.").format(sales_invoice))

    inv = frappe.get_doc("Sales Invoice", sales_invoice)

    if inv.docstatus == 0:
        inv.submit()

    outstanding = flt(inv.outstanding_amount)
    if outstanding <= 0:
        return {
            "success": True,
            "message": _("Sales Invoice '{0}' is already fully paid.").format(sales_invoice),
            "payment_entry": None,
            "outstanding_amount": 0.0,
            "status": inv.status,
        }

    amount = flt(paid_amount)
    if amount <= 0:
        frappe.throw(_("Paid amount must be greater than 0."))

    if amount > outstanding:
        amount = outstanding

    company = get_default_company()

    # Get Mode of Payment
    mop = mode_of_payment or "Cash"
    if not frappe.db.exists("Mode of Payment", mop):
        mops = frappe.get_all("Mode of Payment", limit=1, pluck="name")
        mop = mops[0] if mops else "Cash"
        if not mops:
            frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Cash"}).insert(ignore_permissions=True)
            mop = "Cash"

    # Get Default Bank/Cash account for company
    paid_to_account = frappe.db.get_value("Account", {"company": company, "account_type": ["in", ["Cash", "Bank"]], "is_group": 0}, "name")
    if not paid_to_account:
        paid_to_account = frappe.db.get_value("Account", {"company": company, "is_group": 0}, "name")

    pe_doc = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "posting_date": today(),
        "company": company,
        "mode_of_payment": mop,
        "party_type": "Customer",
        "party": inv.customer,
        "paid_amount": amount,
        "received_amount": amount,
        "target_exchange_rate": 1.0,
        "paid_to": paid_to_account,
        "reference_no": reference_no or f"PAY-{inv.name}",
        "reference_date": today(),
        "references": [{
            "reference_doctype": "Sales Invoice",
            "reference_name": inv.name,
            "total_amount": flt(inv.grand_total),
            "outstanding_amount": outstanding,
            "allocated_amount": amount,
        }]
    })

    pe_doc.insert(ignore_permissions=True)
    pe_doc.submit()

    # Reload invoice to get updated status
    inv.reload()

    return {
        "success": True,
        "message": _("Payment Entry '{0}' created and submitted successfully.").format(pe_doc.name),
        "payment_entry": pe_doc.name,
        "paid_amount": amount,
        "outstanding_amount": flt(inv.outstanding_amount),
        "status": inv.status,
    }
