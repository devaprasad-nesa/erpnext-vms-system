
import frappe
from frappe import _
from frappe.utils import cint


INSPECTION_DOCTYPE = "VMS Vehicle Inspection"
EMPLOYEE_DOCTYPE = "Employee"

MECHANIC_ROLE = "VMS Mechanic"

# Adjust these values to the exact existing Select options
# in your VMS Vehicle Inspection.status field.
MECHANIC_STATUS_OPTIONS = {
    "Assigned",
    "In Progress",
    "Awaiting Accounts",
    "Completed",
}


def _require_mechanic():
    """Allow only logged-in users with the mechanic role."""
    if frappe.session.user == "Guest":
        frappe.throw(
            _("Please log in to access the mechanic dashboard."),
            frappe.PermissionError,
        )

    if not frappe.db.exists(
        "Has Role",
        {
            "parent": frappe.session.user,
            "role": MECHANIC_ROLE,
        },
    ):
        frappe.throw(
            _("You are not authorized to access the mechanic dashboard."),
            frappe.PermissionError,
        )


def _get_mechanic_employee():
    """Resolve the current login to its Employee record."""
    _require_mechanic()

    employee = frappe.db.get_value(
        EMPLOYEE_DOCTYPE,
        {"user_id": frappe.session.user},
        "name",
    )

    if not employee:
        frappe.throw(
            _("Your login is not linked to an Employee record."),
            frappe.PermissionError,
        )

    return employee


def _get_assigned_inspection(name):
    """Return an inspection only if assigned to this mechanic."""
    employee = _get_mechanic_employee()

    if not name:
        frappe.throw(_("Inspection ID is required."))

    # This query is intentionally scoped to the logged-in
    # mechanic's Employee ID.
    docname = frappe.db.get_value(
        INSPECTION_DOCTYPE,
        {
            "name": name,
            "mechanic": employee,
        },
        "name",
    )

    if not docname:
        frappe.throw(
            _("Inspection not found or not assigned to you."),
            frappe.PermissionError,
        )

    return employee, frappe.get_doc(
        INSPECTION_DOCTYPE,
        docname,
    )


@frappe.whitelist()
def get_my_inspections():
    """Return assigned inspections for the logged-in mechanic."""
    employee = _get_mechanic_employee()

    rows = frappe.get_all(
        INSPECTION_DOCTYPE,
        filters={
            "mechanic": employee,
        },
        fields=[
            "name",
            "vehicle",
            "service_booking",
            "service_date",
            "service_slot",
            "issue_description",
            "modification_instructions",
            "estimated_labor_hours",
            "status",
        ],
        order_by="service_date asc",
        limit_page_length=500,
    )

    for row in rows:
        row["vehicle_number"] = row.get("vehicle")
        row["working_hours"] = row.get("estimated_labor_hours")
        row["date"] = row.get("service_date")

    return rows


@frappe.whitelist()
def get_inspection_details(name):
    """Return the details of one assigned inspection."""
    employee, doc = _get_assigned_inspection(name)

    return {
        "name": doc.name,
        "vehicle": doc.get("vehicle"),
        "service_booking": doc.get("service_booking"),
        "service_date": doc.get("service_date"),
        "service_slot": doc.get("service_slot"),
        "issue_description": doc.get("issue_description"),
        "modification_instructions": doc.get(
            "modification_instructions"
        ),
        "estimated_labor_hours": doc.get(
            "estimated_labor_hours"
        ),
        "status": doc.get("status"),
        "vehicle_number": doc.get("vehicle"),
        "working_hours": doc.get("estimated_labor_hours"),
        "date": doc.get("service_date"),
    }


@frappe.whitelist()
def update_inspection_status(name, status):
    """Update only the existing status field."""
    employee, doc = _get_assigned_inspection(name)

    # Explicitly verify the field exists and has Perm Level 1.
    meta = frappe.get_meta(INSPECTION_DOCTYPE)
    status_field = meta.get_field("status")

    if not status_field:
        frappe.throw(_("The status field does not exist."))

    if cint(status_field.permlevel) != 1:
        frappe.throw(
            _("The status field is not configured at Perm Level 1.")
        )

    # Do not accept arbitrary values from the browser.
    if status not in MECHANIC_STATUS_OPTIONS:
        frappe.throw(_("This status is not permitted."))

    # Confirm the requested value is an existing Select option.
    configured_options = {
        line.strip()
        for line in (status_field.options or "").splitlines()
        if line.strip()
    }

    if status not in configured_options:
        frappe.throw(
            _("The requested status is not configured in the DocType.")
        )

    # Optional: prevent mechanics from changing status
    # on work that has already reached a terminal state.
    if doc.status in {"Completed", "Rejected"}:
        frappe.throw(
            _("This inspection is closed and cannot be updated.")
        )

    # Ensure the Employee association has not changed.
    if doc.mechanic != employee:
        frappe.throw(
            _("This inspection is not assigned to you."),
            frappe.PermissionError,
        )

    # Change only the existing status field.
    doc.set("status", status)

    # Do not bypass document validation or permissions.
    doc.save()

    return {
        "name": doc.name,
        "status": doc.status,
        "message": _("Inspection status updated successfully."),
    }