
# vms_account/vms_account/api.py

import frappe
from frappe import _
from frappe.utils import today, flt
from vms_user.pagination import apply_pagination


ACCOUNTANT_ROLE = "vms accountant"
MANAGER_ROLE = "vms manager"
CUSTOMER_ROLE = "vms customer"
TECHNICIAN_ROLE = "vms technician"

INSPECTION_DOCTYPE = "vms vehicle inspection"
SPARE_PARTS_DOCTYPE = "vms spare parts"
VEHICLE_DOCTYPE = "vms vehicle registration"
ACCOUNT_DOCTYPE = "vms accounts"

# "inspected" is the Check field on vms vehicle inspection that the technician
# sets when an inspection is complete and ready for invoicing.
INSPECTION_RELEASE_FIELD = "inspected"


def require_role(*roles):
    user = getattr(frappe.session, "user", None) or "Guest"
    if user == "Administrator":
        return
    user_roles = frappe.get_roles()
    if "System Manager" in user_roles:
        return

    if not any(role in user_roles for role in roles):
        frappe.throw(
            _("You do not have permission to perform this action."),
            frappe.PermissionError,
        )


def check_release_field():
    meta = frappe.get_meta(INSPECTION_DOCTYPE)

    if not meta.has_field(INSPECTION_RELEASE_FIELD):
        frappe.throw(
            _(
                "Inspection release field is not configured. "
                "Update INSPECTION_RELEASE_FIELD in api.py."
            )
        )


def get_released_inspections():
    check_release_field()

    filters = {
        INSPECTION_RELEASE_FIELD: 1,
    }

    inspections = frappe.get_all(
        INSPECTION_DOCTYPE,
        **apply_pagination({
            "filters": filters,
            "fields": [
                "name",
                "vehicle_number",
                "customer_name",
                "spare_parts",
                "spare_part_quantity",
                "labour_hour",
            ],
            "order_by": "modified desc",
        })
    )

    return inspections


def get_spare_part_info(part_name):
    if not part_name:
        return None

    return frappe.db.get_value(
        SPARE_PARTS_DOCTYPE,
        part_name,
        [
            "name",
            "cost",
            "quantity",
        ],
        as_dict=True,
    )


@frappe.whitelist()
def get_dashboard_data() -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE, TECHNICIAN_ROLE)

    inspections = get_released_inspections()

    inspection_rows = []

    for inspection in inspections:
        part = get_spare_part_info(
            inspection.get("spare_parts")
        )

        inspection_rows.append({
            "name": inspection.name,
            "vehicle_number": inspection.vehicle_number,
            "customer_name": inspection.customer_name,
            "spare_parts": inspection.spare_parts,
            "spare_part_quantity": (
                inspection.spare_part_quantity
            ),
            "labour_hour": inspection.labour_hour,
            "part_cost": (
                flt(part.cost) if part else 0
            ),
        })

    invoices = frappe.get_all(
        ACCOUNT_DOCTYPE,
        **apply_pagination({
            "fields": [
                "name",
                "customer_name",
                "vehicle_number",
                "invoice_date",
                "total_bill",
                "audited",
                "payment",
            ],
            "order_by": "modified desc",
        })
    )

    vehicles_raw = frappe.get_all(
        VEHICLE_DOCTYPE,
        **apply_pagination({
            "fields": ["name", "vehicle_number", "owner_name", "vehicle_brand"],
            "order_by": "creation desc",
        })
    )
    vehicles = [dict(v) for v in vehicles_raw]

    bookings_raw = frappe.get_all(
        "vms vehicle service registration",
        **apply_pagination({
            "fields": ["name", "customer_name", "vehicle", "service_date", "booking_status", "service_slot", "owner"],
            "order_by": "creation desc",
        })
    )
    service_bookings = []
    for b in bookings_raw:
        service_bookings.append({
            "name": b.name,
            "customer_name": b.customer_name,
            "vehicle_number": b.vehicle,
            "booking_date": b.service_date,
            "service_slot": b.service_slot,
            "booking_status": b.booking_status,
            "owner": b.owner,
        })

    slots_raw = frappe.get_all(
        "vms service slot",
        **apply_pagination({
            "fields": ["name", "start_time", "end_time", "weekday_capacity", "saturday_capacity"],
            "order_by": "creation desc",
        })
    )
    service_slots = []
    for s in slots_raw:
        service_slots.append({
            "name": s.name,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "weekday_limit": s.weekday_capacity,
            "saturday_limit": s.saturday_capacity,
        })

    return {
        "inspections": inspection_rows,
        "invoices": invoices,
        "vehicles": vehicles,
        "service_bookings": service_bookings,
        "service_slots": service_slots,
    }


@frappe.whitelist()
def get_invoice_form_data() -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE)

    inspections = get_released_inspections()

    customers = frappe.get_all(
        "User",
        **apply_pagination({
            "filters": {"enabled": 1},
            "fields": ["name", "full_name"],
        })
    )

    return {
        "inspections": inspections,
        "customers": customers,
    }


@frappe.whitelist()
def create_invoice(
    customer_name: str,
    vehicle_inspection: str,
    invoice_date: str | None = None,
    total_bill: float | int | str | None = None,
) -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE)

    if not customer_name or not vehicle_inspection:
        frappe.throw(
            _("Customer and inspection are required.")
        )

    check_release_field()

    inspection = frappe.db.get_value(
        INSPECTION_DOCTYPE,
        vehicle_inspection,
        [
            "vehicle_number",
            "customer_name",
        ],
        as_dict=True,
    )

    if not inspection:
        frappe.throw(_("Inspection does not exist."))

    released = frappe.db.get_value(
        INSPECTION_DOCTYPE,
        vehicle_inspection,
        INSPECTION_RELEASE_FIELD,
    )

    if not released:
        frappe.throw(
            _("This inspection has not been released to accounts.")
        )

    if inspection.customer_name != customer_name:
        frappe.throw(
            _("The selected customer does not own this inspection.")
        )

    doc = frappe.new_doc(ACCOUNT_DOCTYPE)

    doc.customer_name = customer_name
    doc.vehicle_number = inspection.vehicle_number
    doc.vehicle_inspection = vehicle_inspection
    doc.invoice_date = invoice_date or today()
    if total_bill is not None and str(total_bill).strip():
        doc.total_bill = flt(total_bill)

    doc.insert()

    return {
        "success": True,
        "name": doc.name,
        "customer_name": doc.customer_name,
        "vehicle_number": doc.vehicle_number,
        "invoice_date": str(doc.invoice_date),
        "spare_parts_amount": flt(doc.spare_parts_amount),
        "total_bill": flt(doc.total_bill),
    }


@frappe.whitelist()
def update_invoice(
    invoice_name: str,
    total_bill: float | int | str | None = None,
    invoice_date: str | None = None,
) -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE)

    if not invoice_name:
        frappe.throw(_("Invoice name is required."))

    doc = frappe.get_doc(ACCOUNT_DOCTYPE, invoice_name)
    if doc.audited:
        frappe.throw(_("Audited invoices cannot be edited."))

    if total_bill is not None and str(total_bill).strip():
        doc.total_bill = flt(total_bill)

    if invoice_date:
        doc.invoice_date = invoice_date

    doc.save()

    return {
        "success": True,
        "name": doc.name,
        "customer_name": doc.customer_name,
        "vehicle_number": doc.vehicle_number,
        "invoice_date": str(doc.invoice_date),
        "spare_parts_amount": flt(doc.spare_parts_amount),
        "total_bill": flt(doc.total_bill),
        "message": _("Invoice updated successfully."),
    }


@frappe.whitelist()
def share_invoice(invoice_name: str) -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE)

    doc = frappe.get_doc(
        ACCOUNT_DOCTYPE,
        invoice_name
    )

    if doc.audited:
        frappe.throw(
            _("This invoice is already audited.")
        )

    customer = doc.customer_name

    manager_users = frappe.get_all(
        "Has Role",
        filters={"role": MANAGER_ROLE},
        fields=["parent"],
        limit_page_length=500,
    )

    manager_emails = []

    for row in manager_users:
        email = frappe.db.get_value(
            "User",
            row.parent,
            "email",
        )

        if email:
            manager_emails.append(email)

    customer_email = frappe.db.get_value(
        "User",
        customer,
        "email",
    )

    if not customer_email:
        frappe.throw(
            _("Customer does not have an email address.")
        )

    # Give the customer read-only access to this invoice.
    frappe.share.add(
        ACCOUNT_DOCTYPE,
        invoice_name,
        customer,
        read=1,
        write=0,
        share=0,
        notify=0,
    )

    # Give each manager read-only access.
    for manager in manager_users:
        frappe.share.add(
            ACCOUNT_DOCTYPE,
            invoice_name,
            manager.parent,
            read=1,
            write=0,
            share=0,
            notify=0,
        )

    recipients = list(set(
        [customer_email] + manager_emails
    ))

    frappe.sendmail(
        recipients=recipients,
        subject=f"VMS Invoice {invoice_name}",
        message=f"""
            <p>Dear recipient,</p>

            <p>A vehicle service invoice is ready for review.</p>

            <p><b>Invoice:</b> {invoice_name}</p>
            <p><b>Vehicle:</b> {doc.vehicle_number}</p>
            <p><b>Total:</b> {doc.total_bill}</p>

            <p>Please log in to the VMS portal to view the invoice.</p>
        """,
        reference_doctype=ACCOUNT_DOCTYPE,
        reference_name=invoice_name,
    )

    return {
        "message": _("Invoice shared successfully."),
        "invoice": invoice_name,
    }


@frappe.whitelist()
def audit_invoice(invoice_name: str) -> dict:
    require_role(ACCOUNTANT_ROLE, MANAGER_ROLE, "System Manager")

    doc = frappe.get_doc(
        ACCOUNT_DOCTYPE,
        invoice_name
    )

    if doc.audited:
        return {
            "message": _("Invoice is already audited.")
        }
        
    if not doc.payment:
        frappe.throw(_("Payment must be confirmed by the customer before auditing."))

    doc.audited = 1
    doc.save()

    return {
        "message": _("Invoice audited successfully."),
        "invoice": doc.name,
        "audited": doc.audited,
    }


@frappe.whitelist()
def enable_payment(invoice_name: str) -> dict:
    require_role(CUSTOMER_ROLE, "System Manager", "Administrator")

    doc = frappe.get_doc(ACCOUNT_DOCTYPE, invoice_name)
    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    is_admin = user == "Administrator" or "System Manager" in user_roles
    
    if not is_admin and doc.customer_name != user:
        frappe.throw(_("You can only access your own invoice."), frappe.PermissionError)

    if doc.payment:
        return {"message": _("Payment already enabled."), "success": True}

    doc.payment = 1
    doc.save()

    return {
        "message": _("Payment enabled successfully."),
        "success": True,
        "invoice": doc.name,
        "payment": doc.payment,
    }


@frappe.whitelist()
def get_my_invoices(only_audited: int | str | None = None) -> list:
    require_role(CUSTOMER_ROLE, "System Manager", "Administrator")

    user = frappe.session.user
    if not user or user == "Guest":
        return []

    filters = {
        "customer_name": user,
    }
    if only_audited and str(only_audited) in ("1", "true", "True"):
        filters["audited"] = 1

    invoices = frappe.get_all(
        ACCOUNT_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "vehicle_number",
            "vehicle_inspection",
            "invoice_date",
            "vehicle_spare_parts",
            "spare_parts_amount",
            "total_bill",
            "audited",
            "payment",
        ],
        order_by="invoice_date desc, creation desc",
        limit_page_length=200,
    )

    return invoices


@frappe.whitelist()
def get_customer_invoice_details(invoice_name: str) -> dict:
    require_role(CUSTOMER_ROLE, ACCOUNTANT_ROLE, MANAGER_ROLE, "System Manager", "Administrator")

    if not invoice_name:
        frappe.throw(_("Invoice name is required."))

    doc = frappe.get_doc(ACCOUNT_DOCTYPE, invoice_name)

    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    is_admin = user == "Administrator" or "System Manager" in user_roles or "vms accountant" in user_roles or "vms manager" in user_roles

    if not is_admin and doc.customer_name != user:
        frappe.throw(_("You can only access your own invoice."), frappe.PermissionError)

    spare_part_label = doc.vehicle_spare_parts
    if doc.vehicle_spare_parts:
        part_name = frappe.db.get_value("vms spare parts", doc.vehicle_spare_parts, "part_name")
        if part_name:
            spare_part_label = f"{part_name} ({doc.vehicle_spare_parts})"

    inspection_issue = None
    if doc.vehicle_inspection:
        inspection_issue = frappe.db.get_value("vms vehicle inspection", doc.vehicle_inspection, "issue")

    return {
        "name": doc.name,
        "customer_name": doc.customer_name,
        "vehicle_number": doc.vehicle_number,
        "vehicle_inspection": doc.vehicle_inspection,
        "inspection_issue": inspection_issue,
        "vehicle_spare_parts": spare_part_label,
        "spare_parts_amount": flt(doc.spare_parts_amount),
        "invoice_date": str(doc.invoice_date or ""),
        "total_bill": flt(doc.total_bill),
        "audited": int(doc.audited or 0),
        "payment": int(doc.payment or 0),
    }


def sync_account_webpages():
    try:
        wp_invoice = frappe.get_doc("Web Page", "account-invoice")
        with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/account-invoice.js", "r") as f:
            wp_invoice.javascript = f.read()
        with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/account-invoice.html", "r") as f:
            wp_invoice.main_section_html = f.read()
        wp_invoice.save(ignore_permissions=True)
    except Exception as e:
        print("sync account-invoice error:", e)

    try:
        wp_dash = frappe.get_doc("Web Page", "account-dashboard")
        with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/account-dashboard.js", "r") as f:
            wp_dash.javascript = f.read()
        with open("/home/admin/Documents/nesa_projects/erpnext-vms-system/vms-system/account-dashboard.html", "r") as f:
            wp_dash.main_section_html = f.read()
        wp_dash.save(ignore_permissions=True)
    except Exception as e:
        print("sync account-dashboard error:", e)

    frappe.db.commit()
    return "synced"