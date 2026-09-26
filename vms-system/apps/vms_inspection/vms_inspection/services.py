# =========================================================
# FILE: vms_inspection/services.py
# PURPOSE: Vehicle inspection and spare parts workflow services,
#          optimized queries, and cross-module synchronization.
# =========================================================

import frappe
from frappe import _
from frappe.utils import flt, getdate
from vms_user.pagination import apply_pagination

INSPECTION_DOCTYPE = "vms vehicle inspection"
SPARE_PARTS_DOCTYPE = "vms spare parts"
VEHICLE_DOCTYPE = "vms vehicle registration"
SERVICE_DOCTYPE = "vms vehicle service registration"


# =========================================================
# AUTHENTICATION & ACCESS GUARDS
# =========================================================

def _get_user_identities(user: str) -> list[str]:
    try:
        from vms_user.login_service import get_user_identities
        return get_user_identities(user)
    except Exception:
        return [user]


def require_staff():
    """Ensure user is a technician, mechanic, manager, or administrator."""
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(
            _("Please log in to continue."),
            frappe.PermissionError,
        )

    if user == "Administrator":
        return user

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    allowed = {
        "vms technician",
        "vms mechanic",
        "technician",
        "vms manager",
        "system manager",
        "vms accountant",
    }
    if not roles.intersection(allowed):
        frappe.throw(
            _("Only workshop staff can access this service."),
            frappe.PermissionError,
        )

    return user


def require_technician():
    """Compatibility wrapper for technician-only functions."""
    return require_staff()


def check_doctype_permission(doctype: str, permission_type: str):
    """Verify standard doc permission or custom hook."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if not frappe.has_permission(doctype, ptype=permission_type, user=user):
        frappe.throw(
            _("You do not have permission to {0} {1}.").format(permission_type, doctype),
            frappe.PermissionError,
        )


# =========================================================
# VEHICLE & SPARE PART RESOLUTION
# =========================================================

def resolve_vehicle_record(vehicle_input: str) -> dict:
    """
    Resolve vehicle docname from either registration docname (veh-00001)
    or vehicle registration number plate (e.g. KL45E1281).
    """
    if not vehicle_input:
        frappe.throw(_("Please select a vehicle."))

    val = str(vehicle_input).strip()

    # 1. Exact match by docname
    vehicle = frappe.db.get_value(
        VEHICLE_DOCTYPE,
        val,
        ["name", "vehicle_number", "owner_name", "owner_user"],
        as_dict=True,
    )

    # 2. Match by plate number
    if not vehicle:
        vehicle = frappe.db.get_value(
            VEHICLE_DOCTYPE,
            {"vehicle_number": val.upper()},
            ["name", "vehicle_number", "owner_name", "owner_user"],
            as_dict=True,
        )

    if not vehicle:
        frappe.throw(_("Selected vehicle '{0}' does not exist.").format(val))

    return vehicle


def resolve_spare_part(spare_part_val: str | None) -> tuple[str | None, str | None]:
    """
    Optimized single-query resolution of spare part name and available quantity.
    """
    if not spare_part_val:
        return None, None

    val = str(spare_part_val).strip()
    if not val:
        return None, None

    # Single parameterized query matching either primary docname or part_name
    part = frappe.db.sql(
        f"""
        SELECT name, quantity, part_name, cost
        FROM `tab{SPARE_PARTS_DOCTYPE}`
        WHERE name = %s OR LOWER(part_name) = LOWER(%s)
        LIMIT 1
        """,
        (val, val),
        as_dict=True,
    )

    if part:
        return part[0].name, str(part[0].quantity or "1")

    # If part is not found, create new spare part record safely
    try:
        new_doc = frappe.get_doc({
            "doctype": SPARE_PARTS_DOCTYPE,
            "part_name": val,
            "quantity": "1",
            "cost": 0.0,
        })
        new_doc.flags.ignore_permissions = True
        new_doc.insert()
        return new_doc.name, "1"
    except Exception:
        return None, None


# =========================================================
# VALIDATIONS & DATA PREPARATION
# =========================================================

def validate_inspection_data(data: dict) -> dict:
    """Validate and sanitize inspection payload."""
    if not isinstance(data, dict):
        frappe.throw(_("Invalid inspection data."))

    vehicle = resolve_vehicle_record(data.get("vehicle_number"))
    vehicle_docname = vehicle["name"]

    if not data.get("inspection_date"):
        frappe.throw(_("Inspection date is required."))

    inspection_date = getdate(data.get("inspection_date"))

    issue = str(data.get("issue") or "").strip()
    if not issue:
        issue = "General Inspection / Routine Checkup"

    labour_hour = flt(data.get("labour_hour") or 0)
    if labour_hour < 0:
        frappe.throw(_("Labour hours cannot be negative."))

    inspected = 1 if data.get("inspected") else 0

    spare_part_name, spare_part_qty = resolve_spare_part(data.get("spare_parts"))
    if data.get("spare_part_quantity"):
        spare_part_qty = str(data.get("spare_part_quantity")).strip()

    customer_name = data.get("customer_name") or vehicle.get("owner_name") or vehicle.get("owner_user")
    mechanic = str(data.get("mechanic") or "").strip() or None

    return {
        "vehicle_number": vehicle_docname,
        "customer_name": customer_name,
        "inspection_date": inspection_date,
        "issue": issue,
        "spare_parts": spare_part_name,
        "spare_part_quantity": spare_part_qty,
        "mechanic": mechanic,
        "labour_hour": labour_hour,
        "inspected": inspected,
    }


def validate_spare_part_data(data: dict) -> dict:
    """Validate spare part payload."""
    if not isinstance(data, dict):
        frappe.throw(_("Invalid spare-part data."))

    part_name = str(data.get("part_name") or "").strip()
    quantity = str(data.get("quantity") or "").strip()
    cost = flt(data.get("cost") or 0)

    if not part_name:
        frappe.throw(_("Part name is required."))
    if not quantity:
        frappe.throw(_("Quantity is required."))
    if cost < 0:
        frappe.throw(_("Cost cannot be negative."))

    return {
        "part_name": part_name,
        "quantity": quantity,
        "cost": cost,
    }


# =========================================================
# CROSS-MODULE SERVICE STATUS SYNCHRONIZATION
# =========================================================

def sync_service_status_on_inspection(vehicle_docname: str, inspection_date, inspected: int):
    """
    When an inspection is completed (inspected=1), advance active service
    registration(s) for that vehicle to 'Under Work'.
    When inspection is unmarked (inspected=0) and no other completed inspections
    exist for this vehicle, revert 'Under Work' service registrations to 'Applied'.
    """
    if not vehicle_docname:
        return

    try:
        if inspected:
            active_services = frappe.get_all(
                SERVICE_DOCTYPE,
                filters={
                    "vehicle": vehicle_docname,
                    "booking_status": ["in", ["Applied", "Confirmed", "Updated", "Rescheduled"]],
                },
                fields=["name", "booking_status"],
            )
            for s in active_services:
                frappe.db.set_value(
                    SERVICE_DOCTYPE,
                    s.name,
                    "booking_status",
                    "Under Work",
                    update_modified=True,
                )
            if active_services:
                frappe.db.commit()
        else:
            other_completed = frappe.db.exists(
                INSPECTION_DOCTYPE,
                {
                    "vehicle_number": vehicle_docname,
                    "inspected": 1,
                },
            )
            if not other_completed:
                under_work_services = frappe.get_all(
                    SERVICE_DOCTYPE,
                    filters={
                        "vehicle": vehicle_docname,
                        "booking_status": "Under Work",
                    },
                    fields=["name"],
                )
                for s in under_work_services:
                    frappe.db.set_value(
                        SERVICE_DOCTYPE,
                        s.name,
                        "booking_status",
                        "Applied",
                        update_modified=True,
                    )
                if under_work_services:
                    frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Failed to sync service status for vehicle {vehicle_docname}: {str(e)}", "VMS Inspection Sync")


# =========================================================
# TECHNICIAN DASHBOARD & LISTING APIS
# =========================================================

def list_inspections() -> list[dict]:
    """Return inspections visible to the logged-in user."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if user == "Guest":
        return []

    filters = {}
    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    if "vms technician" in roles and "vms manager" not in roles and "system manager" not in roles and "administrator" != user.lower():
        filters["technician"] = user

    return frappe.get_list(
        INSPECTION_DOCTYPE,
        **apply_pagination({
            "filters": filters,
            "fields": [
                "name",
                "customer_name",
                "vehicle_number",
                "inspection_date",
                "issue",
                "spare_parts",
                "spare_part_quantity",
                "technician",
                "mechanic",
                "labour_hour",
                "inspected",
                "creation",
                "modified",
            ],
            "order_by": "modified desc",
        })
    )


def list_spare_parts() -> list[dict]:
    """Return all active spare parts."""
    require_staff()
    return frappe.get_list(
        SPARE_PARTS_DOCTYPE,
        **apply_pagination({
            "fields": ["name", "part_name", "quantity", "cost", "owner", "creation", "modified"],
            "order_by": "modified desc",
        })
    )


def list_vehicles() -> list[dict]:
    """Return registered vehicles for the selection dropdown."""
    require_staff()
    return frappe.get_list(
        VEHICLE_DOCTYPE,
        **apply_pagination({
            "fields": ["name", "vehicle_number", "vehicle_brand", "vehicle_model", "owner_name"],
            "order_by": "modified desc",
        })
    )


def get_inspection(name: str):
    """Load an inspection with authorization checks."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if not name:
        frappe.throw(_("Inspection name is required."))

    doc = frappe.get_doc(INSPECTION_DOCTYPE, name)

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    is_staff = bool("administrator" == user.lower() or roles.intersection({"system manager", "vms manager", "vms technician", "vms mechanic", "vms accountant"}))

    if is_staff:
        return doc

    # Customer authorization: verify customer owns the inspected vehicle
    allowed_identities = set(_get_user_identities(user))
    if doc.customer_name in allowed_identities:
        return doc

    vehicle_owner = frappe.db.get_value(
        VEHICLE_DOCTYPE,
        doc.vehicle_number,
        ["owner_name", "owner_user"],
        as_dict=True,
    )
    if vehicle_owner and (vehicle_owner.get("owner_name") in allowed_identities or vehicle_owner.get("owner_user") in allowed_identities):
        return doc

    frappe.throw(_("You can only access your own vehicle inspection records."), frappe.PermissionError)


def create_inspection(data: dict) -> dict:
    """Create a new vehicle inspection."""
    user = require_technician()
    check_doctype_permission(INSPECTION_DOCTYPE, "create")

    values = validate_inspection_data(data)

    # Prevent duplicate submissions with the same data
    if frappe.db.exists(
        INSPECTION_DOCTYPE,
        {
            "vehicle_number": values["vehicle_number"],
            "inspection_date": values["inspection_date"],
            "issue": values["issue"],
            "technician": user,
        },
    ):
        frappe.throw(_("An identical inspection has already been submitted for this vehicle by you on this date."))

    doc = frappe.get_doc({
        "doctype": INSPECTION_DOCTYPE,
        **values,
        "technician": user,
    })
    doc.insert()

    sync_service_status_on_inspection(
        vehicle_docname=doc.vehicle_number,
        inspection_date=doc.inspection_date,
        inspected=doc.inspected,
    )

    return {
        "success": True,
        "name": doc.name,
        "message": _("Inspection created successfully."),
    }


def update_inspection(name: str, data: dict) -> dict:
    """Update an existing inspection."""
    user = require_technician()
    check_doctype_permission(INSPECTION_DOCTYPE, "write")

    doc = get_inspection(name)
    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    if doc.technician != user and "vms manager" not in roles and "system manager" not in roles and "administrator" != user.lower():
        frappe.throw(_("You cannot update another technician's inspection."), frappe.PermissionError)

    # Allow partial updates by merging with existing doc values
    merged_data = {
        "vehicle_number": doc.vehicle_number,
        "customer_name": doc.customer_name,
        "inspection_date": str(doc.inspection_date),
        "issue": doc.issue,
        "spare_parts": doc.spare_parts,
        "spare_part_quantity": doc.spare_part_quantity,
        "mechanic": doc.mechanic,
        "labour_hour": doc.labour_hour,
        "inspected": doc.inspected,
    }
    merged_data.update(data)
    values = validate_inspection_data(merged_data)

    for field, value in values.items():
        doc.set(field, value)

    doc.save()

    sync_service_status_on_inspection(
        vehicle_docname=doc.vehicle_number,
        inspection_date=doc.inspection_date,
        inspected=doc.inspected,
    )

    return {
        "success": True,
        "name": doc.name,
        "message": _("Inspection updated successfully."),
    }


def delete_inspection(name: str) -> dict:
    """Delete an inspection record."""
    user = require_technician()
    check_doctype_permission(INSPECTION_DOCTYPE, "delete")

    doc = get_inspection(name)
    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    if doc.technician != user and "vms manager" not in roles and "system manager" not in roles and "administrator" != user.lower():
        frappe.throw(_("You cannot delete another technician's inspection."), frappe.PermissionError)

    frappe.delete_doc(INSPECTION_DOCTYPE, doc.name)

    return {"message": _("Inspection deleted successfully.")}


def create_spare_part(data: dict) -> dict:
    """Create a new spare part."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "create")

    values = validate_spare_part_data(data)
    
    if frappe.db.exists(SPARE_PARTS_DOCTYPE, {"part_name": values["part_name"]}):
        frappe.throw(_("A spare part with this name already exists."))
        
    doc = frappe.get_doc({"doctype": SPARE_PARTS_DOCTYPE, **values})
    doc.insert()

    return {"name": doc.name, "message": _("Spare part created successfully.")}


def update_spare_part(name: str, data: dict) -> dict:
    """Update an existing spare part."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "write")

    doc = frappe.get_doc(SPARE_PARTS_DOCTYPE, name)
    values = validate_spare_part_data(data)
    for field, value in values.items():
        doc.set(field, value)
    doc.save()

    return {"name": doc.name, "message": _("Spare part updated successfully.")}


def delete_spare_part(name: str) -> dict:
    """Delete a spare part."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "delete")

    frappe.delete_doc(SPARE_PARTS_DOCTYPE, name)
    return {"message": _("Spare part deleted successfully.")}


def list_customer_vehicle_inspections(vehicle_name: str | None = None) -> list[dict]:
    """
    Return inspections for vehicles owned by the logged-in customer.
    """
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(_("Please log in."), frappe.PermissionError)

    filters = {}
    if vehicle_name:
        resolved = resolve_vehicle_record(vehicle_name)
        filters["vehicle_number"] = resolved["name"]

    # frappe.get_list automatically applies our vehicle_inspection_query permission condition
    return frappe.get_list(
        INSPECTION_DOCTYPE,
        **apply_pagination({
            "filters": filters,
            "fields": [
                "name",
                "vehicle_number",
                "customer_name",
                "inspection_date",
                "issue",
                "spare_parts",
                "spare_part_quantity",
                "mechanic",
                "labour_hour",
                "inspected",
                "creation",
            ],
            "order_by": "inspection_date desc",
        })
    )