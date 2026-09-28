# =========================================================
# FILE: vms_inspection/services.py
# PURPOSE: Vehicle inspection and spare parts workflow services,
#          optimized queries, and cross-module synchronization.
# =========================================================

import frappe
from frappe import _
from frappe.utils import flt, getdate
from vms_user.pagination import apply_pagination, get_paginated_data

INSPECTION_DOCTYPE = "vms vehicle inspection"
SPARE_PARTS_DOCTYPE = "vms spare parts"
CHILD_SPARE_PART_DOCTYPE = "vms spare part"
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
    """Ensure user is an authorized VMS technician, manager, or administrator."""
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
        "technician",
        "vms manager",
        "system manager",
    }
    if not roles.intersection(allowed):
        frappe.throw(
            _("Only authorized technicians can manage vehicle inspections and spare parts."),
            frappe.PermissionError,
        )

    return user


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


def parse_inspection_spare_parts(raw_parts) -> list[dict]:
    """
    Parse and validate spare parts list for the child table `vms spare part`.
    Ensures:
    - Parts reference existing master records in `vms spare parts`
    - No duplicate rows in the inspection
    - Qty used > 0
    - Available stock limits enforced
    - Amount = Qty * Cost auto-calculated
    """
    if not raw_parts:
        return []

    if isinstance(raw_parts, str):
        try:
            import json
            raw_parts = json.loads(raw_parts)
        except Exception:
            raw_parts = [{"part_name": raw_parts.strip(), "qty": 1}]

    if isinstance(raw_parts, dict):
        raw_parts = [raw_parts]

    if not isinstance(raw_parts, list):
        return []

    parsed_rows = []
    seen_parts = set()

    for item in raw_parts:
        if isinstance(item, str):
            item = {"part_name": item.strip(), "qty": 1}
        elif not isinstance(item, dict):
            continue

        part_input = (item.get("part_name") or item.get("name") or item.get("spare_part") or "").strip()
        if not part_input:
            continue

        norm_name = part_input.lower()
        if norm_name in seen_parts:
            # Avoid duplicate rows in child table
            continue
        seen_parts.add(norm_name)

        # Look up in master `vms spare parts` table
        master = frappe.db.sql(
            f"""
            SELECT name, part_name, quantity, cost
            FROM `tab{SPARE_PARTS_DOCTYPE}`
            WHERE name = %s OR LOWER(part_name) = LOWER(%s)
            LIMIT 1
            """,
            (part_input, part_input),
            as_dict=True
        )

        part_name = part_input
        cost = flt(item.get("cost") or 0)
        available_stock_str = str(item.get("available_qty") or item.get("quantity") or "").strip()

        if master:
            mp = master[0]
            part_name = mp.part_name or mp.name
            if not cost and flt(mp.cost):
                cost = flt(mp.cost)
            if not available_stock_str and mp.quantity:
                available_stock_str = str(mp.quantity).strip()

        qty = flt(item.get("qty") or item.get("quantity") or 1)
        if qty <= 0:
            frappe.throw(_("Quantity used for spare part '{0}' must be greater than 0.").format(part_name))

        # Check stock limits if numeric available stock exists
        stock_num = None
        if available_stock_str:
            try:
                stock_num = flt(available_stock_str.split()[0])
            except Exception:
                stock_num = None

        if stock_num is not None and stock_num > 0 and qty > stock_num:
            frappe.throw(
                _("Quantity used ({0}) for spare part '{1}' cannot exceed available stock ({2}).").format(
                    qty, part_name, stock_num
                )
            )

        amount = round(qty * cost, 2)

        parsed_rows.append({
            "doctype": CHILD_SPARE_PART_DOCTYPE,
            "part_name": part_name,
            "qty": qty,
            "cost": cost,
            "amount": amount,
            "available_qty": available_stock_str,
        })

    return parsed_rows


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

    spare_parts_rows = parse_inspection_spare_parts(data.get("spare_parts") or data.get("vms_spare_parts"))

    customer_name = data.get("customer_name") or vehicle.get("owner_name") or vehicle.get("owner_user")
    mechanic = str(data.get("mechanic") or "").strip() or None

    return {
        "vehicle_number": vehicle_docname,
        "customer_name": customer_name,
        "inspection_date": inspection_date,
        "issue": issue,
        "spare_parts": spare_parts_rows,
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

def list_inspections(page=None) -> list[dict]:
    """Return inspections visible to the logged-in user with child spare_parts."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if user == "Guest":
        return []

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    is_staff = bool(
        user == "Administrator"
        or roles.intersection({
            "system manager",
            "administrator",
            "vms manager",
            "vms technician",
            "vms mechanic",
            "technician",
            "vms accountant",
        })
    )

    if not is_staff:
        return list_customer_vehicle_inspections(page=page)

    filters = {}
    if "vms technician" in roles and "vms manager" not in roles and "system manager" not in roles and "administrator" != user.lower():
        filters["technician"] = user

    inspections = get_paginated_data(
        INSPECTION_DOCTYPE,
        page=page,
        filters=filters,
        fields=[
            "name",
            "customer_name",
            "vehicle_number",
            "inspection_date",
            "issue",
            "technician",
            "mechanic",
            "labour_hour",
            "inspected",
            "creation",
            "modified",
        ],
        order_by="modified desc"
    )

    if inspections:
        inspection_names = [i["name"] for i in inspections]
        child_rows = frappe.db.sql(
            """
            SELECT parent, name, part_name, qty, cost, amount, available_qty
            FROM `tabvms spare part`
            WHERE parent IN %s AND parenttype = 'vms vehicle inspection' AND parentfield = 'spare_parts'
            ORDER BY idx ASC, creation ASC
            """,
            (tuple(inspection_names),),
            as_dict=True
        )
        parts_by_parent = {}
        for cr in child_rows:
            p = cr.parent
            if p not in parts_by_parent:
                parts_by_parent[p] = []
            parts_by_parent[p].append({
                "name": cr.name,
                "part_name": cr.part_name,
                "qty": flt(cr.qty),
                "cost": flt(cr.cost),
                "amount": flt(cr.amount or (flt(cr.qty) * flt(cr.cost))),
                "available_qty": cr.available_qty or "",
            })

        for i in inspections:
            p_list = parts_by_parent.get(i["name"], [])
            i["spare_parts"] = p_list
            i["total_parts_cost"] = round(sum(flt(x["amount"]) for x in p_list), 2)
            i["spare_parts_summary"] = ", ".join(f"{x['part_name']} ({x['qty']})" for x in p_list) if p_list else "-"

    return inspections


def list_spare_parts(page=None) -> list[dict]:
    """Return all active master spare parts from vms spare parts."""
    require_staff()
    return get_paginated_data(
        SPARE_PARTS_DOCTYPE,
        page=page,
        fields=["name", "part_name", "quantity", "cost", "owner", "creation", "modified"],
        order_by="modified desc"
    )


def list_vehicles() -> list[dict]:
    """Return registered vehicles for the selection dropdown."""
    require_staff()
    return frappe.get_all(
        VEHICLE_DOCTYPE,
        fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "owner_name"],
        order_by="modified desc",
        limit_page_length=500
    )


def get_inspection(name: str):
    """Load an inspection with authorization checks."""
    user = getattr(frappe.session, "user", None) or "Guest"
    if not name:
        frappe.throw(_("Inspection name is required."))

    doc = frappe.get_doc(INSPECTION_DOCTYPE, name)

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    is_staff = bool("administrator" == user.lower() or roles.intersection({"system manager", "vms manager", "vms technician", "vms mechanic", "vms accountant", "technician"}))

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
    if not vehicle_owner and doc.vehicle_number:
        alt_name = frappe.db.get_value(
            VEHICLE_DOCTYPE,
            {"vehicle_number": str(doc.vehicle_number).strip().upper()},
            ["owner_name", "owner_user"],
            as_dict=True,
        )
        if alt_name:
            vehicle_owner = alt_name

    if vehicle_owner and (vehicle_owner.get("owner_name") in allowed_identities or vehicle_owner.get("owner_user") in allowed_identities):
        return doc

    frappe.throw(_("You can only access your own vehicle inspection records."), frappe.PermissionError)


def create_inspection(data: dict) -> dict:
    """Create a new vehicle inspection with child spare_parts table."""
    user = require_technician()
    check_doctype_permission(INSPECTION_DOCTYPE, "create")

    values = validate_inspection_data(data)
    spare_parts_rows = values.pop("spare_parts", [])

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

    for row in spare_parts_rows:
        doc.append("spare_parts", row)

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
    """Update an existing inspection and its child spare_parts table."""
    user = require_technician()
    check_doctype_permission(INSPECTION_DOCTYPE, "write")

    doc = get_inspection(name)
    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    if doc.technician != user and "vms manager" not in roles and "system manager" not in roles and "administrator" != user.lower():
        frappe.throw(_("You cannot update another technician's inspection."), frappe.PermissionError)

    # If data has spare_parts, parse and replace child table
    if "spare_parts" in data or "vms_spare_parts" in data:
        raw_parts = data.get("spare_parts") if "spare_parts" in data else data.get("vms_spare_parts")
        parsed_rows = parse_inspection_spare_parts(raw_parts)
        doc.set("spare_parts", [])
        for row in parsed_rows:
            doc.append("spare_parts", row)

    if "vehicle_number" in data and data["vehicle_number"]:
        veh = resolve_vehicle_record(data["vehicle_number"])
        doc.vehicle_number = veh["name"]
    if "customer_name" in data and data["customer_name"]:
        doc.customer_name = data["customer_name"]
    if "inspection_date" in data and data["inspection_date"]:
        doc.inspection_date = getdate(data["inspection_date"])
    if "issue" in data:
        doc.issue = str(data["issue"] or "").strip() or "General Inspection / Routine Checkup"
    if "mechanic" in data:
        doc.mechanic = str(data["mechanic"] or "").strip() or None
    if "labour_hour" in data:
        doc.labour_hour = flt(data["labour_hour"])
    if "inspected" in data:
        doc.inspected = 1 if data["inspected"] else 0

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
    """Create a new master spare part in vms spare parts."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "create")

    values = validate_spare_part_data(data)
    
    if frappe.db.exists(SPARE_PARTS_DOCTYPE, {"part_name": values["part_name"]}):
        frappe.throw(_("A spare part with this name already exists."))
        
    doc = frappe.get_doc({"doctype": SPARE_PARTS_DOCTYPE, **values})
    doc.insert()

    return {"name": doc.name, "message": _("Spare part created successfully.")}


def update_spare_part(name: str, data: dict) -> dict:
    """Update an existing master spare part."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "write")

    doc = frappe.get_doc(SPARE_PARTS_DOCTYPE, name)
    values = validate_spare_part_data(data)
    for field, value in values.items():
        doc.set(field, value)
    doc.save()

    return {"name": doc.name, "message": _("Spare part updated successfully.")}


def delete_spare_part(name: str) -> dict:
    """Delete a master spare part."""
    require_staff()
    check_doctype_permission(SPARE_PARTS_DOCTYPE, "delete")

    frappe.delete_doc(SPARE_PARTS_DOCTYPE, name)
    return {"message": _("Spare part deleted successfully.")}


def list_customer_vehicle_inspections(vehicle_name: str | None = None, page=None) -> list[dict]:
    """
    Return inspections for vehicles owned by the logged-in customer.
    """
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(_("Please log in."), frappe.PermissionError)

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    is_staff = bool(
        user == "Administrator"
        or roles.intersection({
            "system manager",
            "administrator",
            "vms manager",
            "vms technician",
            "vms mechanic",
            "technician",
            "vms accountant",
        })
    )

    filters = {}
    or_filters = None

    if not is_staff:
        identities = _get_user_identities(user)
        owned_vehicle_names = frappe.get_all(
            VEHICLE_DOCTYPE,
            or_filters=[
                {"owner_name": ["in", identities]},
                {"owner_user": ["in", identities]},
            ],
            pluck="name",
            limit_page_length=1000,
        )

        if vehicle_name:
            resolved = resolve_vehicle_record(vehicle_name)
            if resolved["name"] not in owned_vehicle_names:
                frappe.throw(_("You can only view inspections for your own vehicles."), frappe.PermissionError)
            filters["vehicle_number"] = resolved["name"]
        else:
            or_conditions = [{"customer_name": ["in", identities]}]
            if owned_vehicle_names:
                or_conditions.append({"vehicle_number": ["in", owned_vehicle_names]})
            or_filters = or_conditions
    else:
        if vehicle_name:
            resolved = resolve_vehicle_record(vehicle_name)
            filters["vehicle_number"] = resolved["name"]

    inspections = get_paginated_data(
        INSPECTION_DOCTYPE,
        page=page,
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "vehicle_number",
            "customer_name",
            "inspection_date",
            "issue",
            "mechanic",
            "labour_hour",
            "inspected",
            "creation",
        ],
        order_by="inspection_date desc"
    )

    if inspections:
        inspection_names = [i["name"] for i in inspections]
        child_rows = frappe.db.sql(
            """
            SELECT parent, name, part_name, qty, cost, amount, available_qty
            FROM `tabvms spare part`
            WHERE parent IN %s AND parenttype = 'vms vehicle inspection' AND parentfield = 'spare_parts'
            ORDER BY idx ASC, creation ASC
            """,
            (tuple(inspection_names),),
            as_dict=True
        )
        parts_by_parent = {}
        for cr in child_rows:
            p = cr.parent
            if p not in parts_by_parent:
                parts_by_parent[p] = []
            parts_by_parent[p].append({
                "name": cr.name,
                "part_name": cr.part_name,
                "qty": flt(cr.qty),
                "cost": flt(cr.cost),
                "amount": flt(cr.amount or (flt(cr.qty) * flt(cr.cost))),
                "available_qty": cr.available_qty or "",
            })

        for i in inspections:
            p_list = parts_by_parent.get(i["name"], [])
            i["spare_parts"] = p_list
            i["total_parts_cost"] = round(sum(flt(x["amount"]) for x in p_list), 2)
            i["spare_parts_summary"] = ", ".join(f"{x['part_name']} ({x['qty']})" for x in p_list) if p_list else "-"

    return inspections