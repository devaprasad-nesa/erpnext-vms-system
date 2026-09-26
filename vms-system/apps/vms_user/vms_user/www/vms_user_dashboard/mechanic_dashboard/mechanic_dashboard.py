# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

import frappe
from frappe import _


SERVICE_DOCTYPE = "vms vehicle service registration"
INSPECTION_DOCTYPE = "vms vehicle inspection"

ALLOWED_ROLE = "vms mechanic"

ALLOWED_BOOKING_STATUSES = [
    "Applied",
    "Confirmed",
    "Under Work",
    "Updated",
    "Cancelled",
    "Rescheduled",
]


# ============================================================
# ROLE SECURITY
# ============================================================

def _check_mechanic_role():
    """
    Allow access only to users having the exact
    'vms mechanic' role.
    """

    if frappe.session.user == "Guest":
        frappe.throw(
            _("Please login to access the mechanic dashboard."),
            frappe.PermissionError,
        )

    roles = frappe.get_roles(frappe.session.user)

    if ALLOWED_ROLE not in roles:
        frappe.throw(
            _("Only users with the 'vms mechanic' role can access this dashboard."),
            frappe.PermissionError,
        )


def _get_current_user():
    _check_mechanic_role()
    return frappe.session.user


# ============================================================
# DASHBOARD DATA
# ============================================================

@frappe.whitelist()
def get_dashboard_data():
    """
    Return all data required by the mechanic dashboard.

    Returns:
        {
            "user": "...",
            "service_registrations": [...],
            "vehicle_inspections": [...]
        }
    """

    _check_mechanic_role()

    return {
        "user": frappe.session.user,
        "service_registrations": get_service_registrations(),
        "vehicle_inspections": get_vehicle_inspections(),
    }


# ============================================================
# VEHICLE SERVICE REGISTRATION
# ============================================================

@frappe.whitelist()
def get_service_registrations():
    """
    Return vehicle service registrations for mechanics.

    The mechanic can VIEW service registrations.

    The mechanic is allowed to update only booking_status
    through update_booking_status().
    """

    _check_mechanic_role()

    meta = frappe.get_meta(SERVICE_DOCTYPE)

    fields = [
        "name",
        "customer_name",
        "user_id",
        "vehicle",
        "service_date",
        "service_slot",
        "booking_status",
        "creation",
        "modified",
    ]

    # Only request fields that actually exist.
    available_fields = []

    for field in fields:
        if field == "name" or meta.has_field(field):
            available_fields.append(field)

    # --------------------------------------------------------
    # Determine which vehicles are assigned to this mechanic
    # based on the `vms vehicle inspection` DocType.
    # --------------------------------------------------------
    assigned_vehicles = []
    if frappe.db.exists("DocType", INSPECTION_DOCTYPE):
        inspections = frappe.get_all(
            INSPECTION_DOCTYPE,
            filters={"mechanic": frappe.session.user},
            fields=["vehicle_number"]
        )
        for ins in inspections:
            if ins.vehicle_number:
                assigned_vehicles.append(ins.vehicle_number)

    if not assigned_vehicles:
        return []

    filters = [
        ["vehicle", "in", assigned_vehicles],
        ["booking_status", "in", ["Under Work", "", None]]
    ]

    registrations = frappe.get_all(
        SERVICE_DOCTYPE,
        fields=available_fields,
        filters=filters,
        order_by="service_date asc, creation desc",
        limit_page_length=500,
    )

    return registrations


@frappe.whitelist()
def get_service_registration(name: str):
    """
    Return one service registration.
    """

    _check_mechanic_role()

    if not name:
        frappe.throw(_("Service registration name is required."))

    if not frappe.db.exists(SERVICE_DOCTYPE, name):
        frappe.throw(_("Service registration {0} does not exist.").format(name))

    doc = frappe.get_doc(SERVICE_DOCTYPE, name)

    # Check if the vehicle is assigned to the current mechanic via inspection
    is_assigned = False
    if frappe.db.exists("DocType", INSPECTION_DOCTYPE):
        is_assigned = frappe.db.exists(
            INSPECTION_DOCTYPE,
            {"mechanic": frappe.session.user, "vehicle_number": doc.vehicle}
        )

    if not is_assigned:
        frappe.throw(_("You are not assigned to this service registration."), frappe.PermissionError)

    if doc.get("booking_status") not in ["Under Work", "", None]:
        frappe.throw(_("You can only view registrations with status 'Under Work' or empty."), frappe.PermissionError)

    meta = frappe.get_meta(SERVICE_DOCTYPE)

    data = {
        "name": doc.name,
    }

    fields = [
        "customer_name",
        "user_id",
        "vehicle",
        "service_date",
        "service_slot",
        "booking_status",
        "creation",
        "modified",
    ]

    for field in fields:
        if meta.has_field(field):
            data[field] = doc.get(field)

    return data


@frappe.whitelist()
def update_booking_status(name: str, booking_status: str):
    """
    Update ONLY booking_status of a service registration.

    Security:
    - User must be logged in.
    - User must have vms mechanic role.
    - Document must exist.
    - booking_status must be one of the allowed values.
    - No other field is changed.

    We intentionally do not give the mechanic general DocType
    write permission. The dashboard API is the controlled
    operation that changes this one field.
    """

    _check_mechanic_role()

    if not name:
        frappe.throw(_("Service registration name is required."))

    if not booking_status:
        frappe.throw(_("Booking status is required."))

    booking_status = booking_status.strip()

    if booking_status not in ALLOWED_BOOKING_STATUSES:
        frappe.throw(
            _("Invalid booking status: {0}").format(booking_status)
        )

    if not frappe.db.exists(SERVICE_DOCTYPE, name):
        frappe.throw(
            _("Service registration {0} does not exist.").format(name)
        )

    meta = frappe.get_meta(SERVICE_DOCTYPE)

    if not meta.has_field("booking_status"):
        frappe.throw(
            _("The booking_status field does not exist in {0}.").format(
                SERVICE_DOCTYPE
            )
        )

    # Load document.
    doc = frappe.get_doc(SERVICE_DOCTYPE, name)

    # Check if the vehicle is assigned to the current mechanic via inspection
    is_assigned = False
    if frappe.db.exists("DocType", INSPECTION_DOCTYPE):
        is_assigned = frappe.db.exists(
            INSPECTION_DOCTYPE,
            {"mechanic": frappe.session.user, "vehicle_number": doc.vehicle}
        )

    if not is_assigned:
        frappe.throw(_("You can only update your own assigned vehicles."), frappe.PermissionError)

    old_status = doc.get("booking_status")

    if old_status == booking_status:
        return {
            "success": True,
            "message": _("Booking status is already {0}.").format(
                booking_status
            ),
            "name": name,
            "old_status": old_status,
            "new_status": booking_status,
        }

    # --------------------------------------------------------
    # IMPORTANT:
    # The mechanic's DocType permission is intentionally read-only.
    #
    # We have already performed an explicit server-side role
    # check above. Therefore only this controlled field is
    # changed.
    # --------------------------------------------------------

    doc.db_set(
        "booking_status",
        booking_status,
        update_modified=True,
    )

    frappe.db.commit()

    return {
        "success": True,
        "message": _("Booking status updated successfully."),
        "name": name,
        "old_status": old_status,
        "new_status": booking_status,
    }


# ============================================================
# VEHICLE INSPECTION
# ============================================================

@frappe.whitelist()
def get_vehicle_inspections():
    """
    Return Vehicle Inspection records assigned to the currently
    logged-in mechanic.

    Expected field:
        mechanic

    The mechanic field should contain the User ID of the
    assigned mechanic.
    """

    _check_mechanic_role()

    current_user = frappe.session.user

    if not frappe.db.exists("DocType", INSPECTION_DOCTYPE):
        return {
            "error": True,
            "message": _(
                "The '{0}' DocType does not exist."
            ).format(INSPECTION_DOCTYPE),
            "records": [],
        }

    meta = frappe.get_meta(INSPECTION_DOCTYPE)

    # --------------------------------------------------------
    # The implementation expects a Link field named "mechanic"
    # pointing to User.
    # --------------------------------------------------------

    if not meta.has_field("mechanic"):
        return {
            "error": True,
            "message": _(
                "The '{0}' DocType does not contain a 'mechanic' field."
            ).format(INSPECTION_DOCTYPE),
            "records": [],
        }

    # Get all fields dynamically.
    #
    # This makes the dashboard more tolerant if your Vehicle
    # Inspection DocType has additional fields.
    fields = ["name"]

    for field in meta.fields:
        if field.fieldname == "name":
            continue

        # Avoid problematic virtual/system fields.
        if field.fieldtype in [
            "Section Break",
            "Column Break",
            "Tab Break",
            "HTML",
            "Button",
        ]:
            continue

        fields.append(field.fieldname)

    records = frappe.get_all(
        INSPECTION_DOCTYPE,
        filters={
            "mechanic": current_user,
        },
        fields=fields,
        order_by="creation desc",
        limit_page_length=500,
    )

    return {
        "error": False,
        "message": _("Inspection records loaded."),
        "records": records,
        "current_user": current_user,
    }


@frappe.whitelist()
def get_vehicle_inspection(name: str):
    """
    Return one inspection assigned to the current mechanic.
    """

    _check_mechanic_role()

    if not name:
        frappe.throw(_("Inspection name is required."))

    if not frappe.db.exists(INSPECTION_DOCTYPE, name):
        frappe.throw(
            _("Vehicle Inspection {0} does not exist.").format(name)
        )

    meta = frappe.get_meta(INSPECTION_DOCTYPE)

    if not meta.has_field("mechanic"):
        frappe.throw(
            _("Vehicle Inspection does not contain a mechanic field.")
        )

    current_user = frappe.session.user

    doc = frappe.get_doc(INSPECTION_DOCTYPE, name)

    # Critical security check:
    # A mechanic cannot retrieve another mechanic's inspection
    # through this API.
    if doc.get("mechanic") != current_user:
        frappe.throw(
            _("You are not assigned to this vehicle inspection."),
            frappe.PermissionError,
        )

    data = {}

    for field in meta.fields:
        if field.fieldtype in [
            "Section Break",
            "Column Break",
            "Tab Break",
            "HTML",
            "Button",
        ]:
            continue

        data[field.fieldname] = doc.get(field.fieldname)

    data["name"] = doc.name

    return data


# ============================================================
# WEBSITE PAGE CONTROLLER
# ============================================================

def get_context(context):
    """
    Frappe website page controller.

    The page itself is protected before rendering.
    """

    _check_mechanic_role()

    context.no_cache = 1
    context.show_sidebar = False
    context.title = _("Mechanic Dashboard")

    context.mechanic_user = frappe.session.user

    return context