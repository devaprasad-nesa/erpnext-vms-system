import json
import frappe
from frappe import _
from vms_user.pagination import apply_pagination, get_paginated_data

from vms_vehicle.service_registration import (
    get_available_service_slots,
    get_my_vehicles,
    register_vehicle_service,
    get_my_service_registrations,
    get_my_service_registration,
    validate_service_document,
    get_technician_service_bookings,
)

# ============================================================
# CONFIGURATION
# ============================================================

DOCTYPE = "vms vehicle registration"

# ============================================================
# AUTHENTICATION AND CUSTOMER / ADMIN ACCESS
# ============================================================

def require_customer():
    """
    Require an authenticated VMS customer.
    The logged-in user is obtained from the server-side
    Frappe session. The browser cannot choose the identity
    used for authorization.
    """
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            _("Please log in to continue."),
            frappe.PermissionError
        )

    return user


def _require_logged_in_customer():
    """
    Require an authenticated VMS customer.
    Kept as a compatibility wrapper for existing methods.
    """
    return require_customer()


def require_admin():
    """
    Verify that the current user is an authorized Administrator or Manager.
    Enforces Frappe's role-based security on the server side.
    """
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            _("Please log in as an administrator to continue."),
            frappe.PermissionError
        )

    if user == "Administrator":
        return user

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    admin_roles = {"system manager", "administrator", "vms manager"}

    if not roles.intersection(admin_roles):
        frappe.throw(
            _("Permission denied. Only authorized administrators can manage vehicle master data."),
            frappe.PermissionError
        )

    return user


# ============================================================
# USER IDENTITY RESOLUTION
# ============================================================

def get_user_identity_values(user: str) -> list:
    """
    Return the identity values that may be used to match
    vehicle owner_user and owner_name fields using the cached context.
    """
    if user == "Administrator":
        return [user]

    try:
        from vms_user.login_service import get_user_identities
        return get_user_identities(user)
    except Exception:
        identity_values = [user]
        user_data = frappe.db.get_value(
            "User",
            user,
            ["name", "email", "full_name"],
            as_dict=True
        )
        if user_data:
            for value in [user_data.name, user_data.email, user_data.full_name]:
                if value and value not in identity_values:
                    identity_values.append(value)
        return identity_values


# ============================================================
# VEHICLE OWNERSHIP FILTERS
# ============================================================

def get_vehicle_owner_filters(user: str) -> list:
    """
    Build ownership filters for the authenticated user.
    """
    identity_values = get_user_identity_values(user)

    return [
        {"owner_user": ["in", identity_values]},
        {"owner_name": ["in", identity_values]},
    ]


def get_owned_vehicle(name: str):
    """
    Fetch a single vehicle only when it belongs to
    the authenticated customer.
    """
    user = require_customer()

    if not name:
        frappe.throw(
            _("Vehicle ID is required.")
        )

    # Preserve Administrator access.
    if user == "Administrator":
        vehicle = frappe.db.get_value(
            DOCTYPE,
            name,
            "name"
        )

        if not vehicle:
            frappe.throw(
                _("Vehicle not found."),
                frappe.DoesNotExistError
            )

        return frappe.get_doc(DOCTYPE, vehicle)

    # Check against logged-in user's ownership values.
    vehicle_name = frappe.get_all(
        DOCTYPE,
        filters={"name": name},
        or_filters=get_vehicle_owner_filters(user),
        pluck="name",
        limit_page_length=1
    )

    if not vehicle_name:
        frappe.throw(
            _("Vehicle not found."),
            frappe.DoesNotExistError
        )

    return frappe.get_doc(
        DOCTYPE,
        vehicle_name[0]
    )


# ============================================================
# GET MY VEHICLES
# ============================================================

@frappe.whitelist()
def get_my_vehicles():
    """
    Return only vehicles belonging to the currently
    authenticated VMS customer.
    """
    user = require_customer()

    if user == "Administrator":
        filters = {}
        or_filters = []
    else:
        filters = {}
        or_filters = get_vehicle_owner_filters(user)

    vehicles = get_paginated_data(
        DOCTYPE,
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "vehicle_number",
            "vehicle_brand",
            "vehicle_model",
            "fuel_type",
            "vehicle_color",
        ],
        order_by="creation desc"
    )

    return vehicles


# ============================================================
# GET MY VEHICLE DETAILS
# ============================================================

@frappe.whitelist()
def get_my_vehicle(name: str) -> dict:
    """
    Return detailed information about a vehicle only
    when it belongs to the authenticated customer.
    """
    vehicle = get_owned_vehicle(name)

    return {
        "name": vehicle.name,
        "vehicle_number": vehicle.vehicle_number,
        "vehicle_brand": vehicle.vehicle_brand,
        "vehicle_model": vehicle.vehicle_model,
        "fuel_type": getattr(vehicle, "fuel_type", None) or getattr(vehicle, "vehicle_fuel_type", None),
        "vehicle_fuel_type": getattr(vehicle, "fuel_type", None) or getattr(vehicle, "vehicle_fuel_type", None),
        "manufacturing_year": getattr(vehicle, "manufacturing_year", None),
        "vehicle_color": getattr(vehicle, "vehicle_color", None) or getattr(vehicle, "color", None),
        "chassis_number": vehicle.chassis_number,
        "engine_number": vehicle.engine_number,
        "registration_date": vehicle.registration_date,
        "notes": vehicle.notes,
    }


# ============================================================
# CREATE VEHICLE
# ============================================================

@frappe.whitelist()
def create_vehicle(
    vehicle_number: str | None = None,
    vehicle_brand: str | None = None,
    vehicle_model: str | None = None,
    vehicle_type: str | None = None,
    fuel_type: str | None = None,
    vehicle_fuel_type: str | None = None,
    manufacturing_year: str | int | None = None,
    vehicle_color: str | None = None,
    color: str | None = None,
    chassis_number: str | None = None,
    engine_number: str | None = None,
    registration_date: str | None = None,
    notes: str | None = None,
    **kwargs
) -> dict:
    """
    Create a vehicle for the currently authenticated VMS customer.
    Validates Brand, Model, and Fuel Type relationships server-side.
    """
    user = require_customer()

    fuel_type_val = fuel_type or vehicle_fuel_type or kwargs.get("fuel_type") or kwargs.get("vehicle_fuel_type")
    brand_val = vehicle_brand or kwargs.get("vehicle_brand")
    model_val = vehicle_model or kwargs.get("vehicle_model")
    v_number = vehicle_number or kwargs.get("vehicle_number")
    v_type = vehicle_type or kwargs.get("vehicle_type")
    m_year = manufacturing_year or kwargs.get("manufacturing_year")
    v_color = vehicle_color or color or kwargs.get("vehicle_color") or kwargs.get("color")
    c_number = chassis_number or kwargs.get("chassis_number")
    e_number = engine_number or kwargs.get("engine_number")
    r_date = registration_date or kwargs.get("registration_date")
    v_notes = notes or kwargs.get("notes")

    # Strict server-side relationship validation
    validate_vehicle_relationships(brand_val, model_val, fuel_type_val)

    doc = frappe.get_doc({
        "doctype": DOCTYPE,
        "owner_user": user,
        "owner_name": user,
        "vehicle_number": v_number,
        "vehicle_brand": brand_val,
        "vehicle_model": model_val,
        "vehicle_type": v_type,
        "fuel_type": fuel_type_val,
        "manufacturing_year": m_year,
        "vehicle_color": v_color,
        "chassis_number": c_number,
        "engine_number": e_number,
        "registration_date": r_date,
        "notes": v_notes,
    })

    doc.insert(ignore_permissions=True)

    return {
        "message": "Vehicle registered successfully",
        "name": doc.name
    }


# ============================================================
# UPDATE VEHICLE
# ============================================================

@frappe.whitelist()
def update_vehicle(
    name: str,
    vehicle_number: str | None = None,
    vehicle_brand: str | None = None,
    vehicle_model: str | None = None,
    vehicle_type: str | None = None,
    fuel_type: str | None = None,
    vehicle_fuel_type: str | None = None,
    manufacturing_year: str | int | None = None,
    vehicle_color: str | None = None,
    color: str | None = None,
    chassis_number: str | None = None,
    engine_number: str | None = None,
    registration_date: str | None = None,
    notes: str | None = None,
    **kwargs
) -> dict:
    """
    Update a vehicle only when it belongs to
    the authenticated customer.
    """
    vehicle = get_owned_vehicle(name)

    fuel_type_val = fuel_type or vehicle_fuel_type or kwargs.get("fuel_type") or kwargs.get("vehicle_fuel_type") or vehicle.fuel_type
    brand_val = vehicle_brand or kwargs.get("vehicle_brand") or vehicle.vehicle_brand
    model_val = vehicle_model or kwargs.get("vehicle_model") or vehicle.vehicle_model

    validate_vehicle_relationships(brand_val, model_val, fuel_type_val)

    allowed_updates = {
        "vehicle_number": vehicle_number or kwargs.get("vehicle_number"),
        "vehicle_brand": brand_val,
        "vehicle_model": model_val,
        "vehicle_type": vehicle_type or kwargs.get("vehicle_type"),
        "fuel_type": fuel_type_val,
        "manufacturing_year": manufacturing_year or kwargs.get("manufacturing_year"),
        "vehicle_color": vehicle_color or color or kwargs.get("vehicle_color") or kwargs.get("color"),
        "chassis_number": chassis_number or kwargs.get("chassis_number"),
        "engine_number": engine_number or kwargs.get("engine_number"),
        "registration_date": registration_date or kwargs.get("registration_date"),
        "notes": notes or kwargs.get("notes"),
    }

    for field, val in allowed_updates.items():
        if val is not None:
            vehicle.set(field, val)

    vehicle.save(ignore_permissions=True)

    return {
        "message": "Vehicle updated successfully",
        "name": vehicle.name
    }


# ============================================================
# DELETE VEHICLE
# ============================================================

@frappe.whitelist()
def delete_vehicle(name: str) -> dict:
    """
    Delete a vehicle only when it belongs to
    the authenticated customer.
    """
    vehicle = get_owned_vehicle(name)

    frappe.delete_doc(
        DOCTYPE,
        vehicle.name,
        ignore_permissions=True
    )

    return {
        "message": "Vehicle deleted successfully"
    }


# ============================================================
# USER VEHICLE LINKING
# ============================================================

@frappe.whitelist()
def get_my_vehicle_details(vehicle_name: str) -> dict:
    """
    Return vehicle details only if the requested vehicle
    belongs to the currently logged-in VMS customer.
    """
    vehicle = get_owned_vehicle(vehicle_name)

    return {
        "name": vehicle.name,
        "vehicle_number": vehicle.vehicle_number,
        "vehicle_brand": vehicle.vehicle_brand,
        "vehicle_model": vehicle.vehicle_model,
        "fuel_type": getattr(vehicle, "fuel_type", None) or getattr(vehicle, "vehicle_fuel_type", None),
        "user_id": vehicle.owner_user,
    }


# ============================================================
# RELATIONSHIP VALIDATION HELPER
# ============================================================

def validate_vehicle_relationships(brand: str, model: str, fuel_type: str):
    """
    Server-side validation for Brand -> Model -> Fuel Type combinations:
    1. Brand exists in vms brand (or Vehicle Brand fallback).
    2. Model exists in child table vms model for that Brand (or Vehicle Model fallback).
    3. Fuel Type is defined and supported for that Model in vms model.
    """
    if not brand:
        frappe.throw(_("Vehicle Brand is required."), frappe.ValidationError)

    if not model:
        frappe.throw(_("Vehicle Model is required."), frappe.ValidationError)

    if not fuel_type:
        frappe.throw(_("Fuel Type is required."), frappe.ValidationError)

    brand_clean = str(brand).strip()
    model_clean = str(model).strip()
    fuel_clean = str(fuel_type).strip()

    # 1. Check in 'vms brand' & child table 'vms model'
    if frappe.db.exists("DocType", "vms brand"):
        brand_rows = frappe.db.sql(
            "SELECT name, vehicle_brand FROM `tabvms brand` WHERE LOWER(vehicle_brand) = %s OR LOWER(name) = %s",
            (brand_clean.lower(), brand_clean.lower()),
            as_dict=True
        )
        if brand_rows:
            parent_ids = [b.name for b in brand_rows]

            if frappe.db.exists("DocType", "vms model"):
                model_rows = frappe.db.sql(
                    """
                    SELECT model_name, fuel_type FROM `tabvms model`
                    WHERE parent IN %s AND parenttype = 'vms brand' AND LOWER(model_name) = %s
                    """,
                    (tuple(parent_ids), model_clean.lower()),
                    as_dict=True
                )
                if not model_rows:
                    frappe.throw(
                        _("Vehicle Model '{0}' is not defined for Vehicle Brand '{1}' in VMS Brand table.").format(model, brand),
                        frappe.ValidationError
                    )

                allowed_fuels = set()
                for r in model_rows:
                    raw_ft = r.fuel_type or ""
                    for p in raw_ft.replace("/", ",").split(","):
                        if p.strip():
                            allowed_fuels.add(p.strip().lower())

                if allowed_fuels and fuel_clean.lower() not in allowed_fuels:
                    frappe.throw(
                        _("Fuel Type '{0}' is not supported by Vehicle Model '{1}' under Brand '{2}'. Allowed: {3}").format(
                            fuel_type, model, brand, ", ".join(sorted(f.title() for f in allowed_fuels))
                        ),
                        frappe.ValidationError
                    )
            return

    # 2. Check in standalone 'Vehicle Brand' & 'Vehicle Model' fallback
    vb_brand_exists = False
    vb_model_valid = False
    vb_fuel_valid = False

    if frappe.db.exists("DocType", "Vehicle Brand"):
        b_doc = frappe.db.get_value("Vehicle Brand", brand_clean, ["name", "enabled"], as_dict=True)
        if b_doc and b_doc.enabled:
            vb_brand_exists = True

    if frappe.db.exists("DocType", "Vehicle Model"):
        m_doc = frappe.db.get_value("Vehicle Model", model_clean, ["name", "vehicle_brand", "enabled"], as_dict=True)
        if m_doc and m_doc.enabled and str(m_doc.vehicle_brand).strip().lower() == brand_clean.lower():
            vb_model_valid = True
            if frappe.db.exists("DocType", "Vehicle Model Fuel Type"):
                supp_fuels = frappe.get_all(
                    "Vehicle Model Fuel Type",
                    filters={"parent": model_clean, "parenttype": "Vehicle Model"},
                    pluck="fuel_type"
                )
                if not supp_fuels or any(str(f).strip().lower() == fuel_clean.lower() for f in supp_fuels):
                    vb_fuel_valid = True
            else:
                vb_fuel_valid = True

    if not vb_brand_exists:
        frappe.throw(_("Vehicle Brand '{0}' does not exist in the database.").format(brand), frappe.DoesNotExistError)

    if not vb_model_valid:
        frappe.throw(_("Vehicle Model '{0}' does not belong to Brand '{1}'.").format(model, brand), frappe.ValidationError)

    if not vb_fuel_valid:
        frappe.throw(_("Fuel Type '{0}' is not supported by Vehicle Model '{1}'.").format(fuel_type, model), frappe.ValidationError)


# ============================================================
# VEHICLE MASTER DATA APIS (PUBLIC / CUSTOMER READ-ONLY)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_vehicle_brands() -> list:
    """
    Return available vehicle brands from the `vms brand` table in database.
    Only brands defined in `vms brand` will be returned.
    """
    brands = []
    seen = set()

    # 1. Fetch strictly from 'vms brand' table
    if frappe.db.exists("DocType", "vms brand"):
        vms_brands = frappe.db.sql(
            """
            SELECT name, vehicle_brand
            FROM `tabvms brand`
            WHERE IFNULL(vehicle_brand, '') != ''
            ORDER BY vehicle_brand ASC
            """,
            as_dict=True
        )
        for b in vms_brands:
            b_name = (b.vehicle_brand or b.name or "").strip()
            if b_name and b_name.lower() not in seen:
                seen.add(b_name.lower())
                brands.append({
                    "name": b_name,
                    "brand_name": b_name,
                    "id": b.name
                })

    # Return only vms brand records if present
    if brands:
        brands.sort(key=lambda x: x["brand_name"].lower())
        return brands

    # Fallback to Vehicle Brand only if vms brand table is empty
    if frappe.db.exists("DocType", "Vehicle Brand"):
        vb_brands = frappe.db.get_all(
            "Vehicle Brand",
            filters={"enabled": 1},
            fields=["name", "brand_name"],
            order_by="brand_name asc"
        )
        for b in vb_brands:
            b_name = (b.brand_name or b.name or "").strip()
            if b_name and b_name.lower() not in seen:
                seen.add(b_name.lower())
                brands.append({"name": b_name, "brand_name": b_name, "id": b.name})

    brands.sort(key=lambda x: x["brand_name"].lower())
    return brands


@frappe.whitelist(allow_guest=True)
def get_vehicle_models(brand: str | None = None) -> list:
    """
    Return models belonging to the given brand from vms brand -> vms model child table.
    """
    if not brand:
        return []

    brand_clean = str(brand).strip()
    models = []
    seen = set()

    # 1. Search in 'vms brand' -> 'vms model' child table
    if frappe.db.exists("DocType", "vms brand") and frappe.db.exists("DocType", "vms model"):
        brand_parents = frappe.db.sql(
            """
            SELECT name, vehicle_brand FROM `tabvms brand`
            WHERE LOWER(vehicle_brand) = %s OR LOWER(name) = %s
            """,
            (brand_clean.lower(), brand_clean.lower()),
            as_dict=True
        )
        parent_ids = [bp.name for bp in brand_parents]

        if parent_ids:
            child_models = frappe.db.sql(
                """
                SELECT DISTINCT model_name, fuel_type
                FROM `tabvms model`
                WHERE parent IN %s AND parenttype = 'vms brand'
                  AND IFNULL(model_name, '') != ''
                ORDER BY model_name ASC
                """,
                (tuple(parent_ids),),
                as_dict=True
            )
            for m in child_models:
                m_name = (m.model_name or "").strip()
                if m_name and m_name.lower() not in seen:
                    seen.add(m_name.lower())
                    models.append({
                        "name": m_name,
                        "model_name": m_name,
                        "vehicle_brand": brand_clean
                    })

    if models:
        models.sort(key=lambda x: x["model_name"].lower())
        return models

    # Fallback to Vehicle Model only if no vms model records found
    if frappe.db.exists("DocType", "Vehicle Model"):
        vb_models = frappe.db.get_all(
            "Vehicle Model",
            filters={"vehicle_brand": brand_clean, "enabled": 1},
            fields=["name", "model_name", "vehicle_brand"],
            order_by="model_name asc"
        )
        for m in vb_models:
            m_name = (m.model_name or m.name or "").strip()
            if m_name and m_name.lower() not in seen:
                seen.add(m_name.lower())
                models.append({
                    "name": m_name,
                    "model_name": m_name,
                    "vehicle_brand": brand_clean
                })

    models.sort(key=lambda x: x["model_name"].lower())
    return models


@frappe.whitelist(allow_guest=True)
def get_vehicle_fuel_types(model: str | None = None, brand: str | None = None) -> list:
    """
    Return valid fuel types for the given model (and brand) strictly from vms model child table.
    """
    fuels = []
    seen = set()

    def _add_fuel(raw_val: str):
        if not raw_val:
            return
        parts = [p.strip() for p in raw_val.replace("/", ",").split(",") if p.strip()]
        for p in parts:
            p_formatted = p.title()
            if p_formatted and p_formatted.lower() not in seen:
                seen.add(p_formatted.lower())
                fuels.append({
                    "name": p_formatted,
                    "fuel_type": p_formatted
                })

    model_clean = str(model).strip() if model else ""
    brand_clean = str(brand).strip() if brand else ""

    # 1. Look up in 'vms model' child table
    if frappe.db.exists("DocType", "vms model") and frappe.db.exists("DocType", "vms brand"):
        if model_clean and brand_clean:
            brand_parents = frappe.db.sql(
                "SELECT name FROM `tabvms brand` WHERE LOWER(vehicle_brand) = %s OR LOWER(name) = %s",
                (brand_clean.lower(), brand_clean.lower()),
                as_dict=True
            )
            parent_ids = [bp.name for bp in brand_parents]
            if parent_ids:
                vm_fuels = frappe.db.sql(
                    """
                    SELECT fuel_type
                    FROM `tabvms model`
                    WHERE parent IN %s AND parenttype = 'vms brand'
                      AND LOWER(model_name) = %s AND IFNULL(fuel_type, '') != ''
                    """,
                    (tuple(parent_ids), model_clean.lower()),
                    as_dict=True
                )
                for f in vm_fuels:
                    _add_fuel(f.fuel_type)

        if model_clean and not fuels:
            vm_fuels = frappe.db.sql(
                """
                SELECT fuel_type
                FROM `tabvms model`
                WHERE LOWER(model_name) = %s AND parenttype = 'vms brand'
                  AND IFNULL(fuel_type, '') != ''
                """,
                (model_clean.lower(),),
                as_dict=True
            )
            for f in vm_fuels:
                _add_fuel(f.fuel_type)

        if not model_clean:
            vm_fuels = frappe.db.sql(
                """
                SELECT DISTINCT fuel_type FROM `tabvms model`
                WHERE parenttype = 'vms brand' AND IFNULL(fuel_type, '') != ''
                """,
                as_dict=True
            )
            for f in vm_fuels:
                _add_fuel(f.fuel_type)

    if fuels:
        fuels.sort(key=lambda x: x["fuel_type"].lower())
        return fuels

    # Fallback to Vehicle Model Fuel Type / Vehicle Fuel Type only if no vms model entries
    if model_clean and frappe.db.exists("DocType", "Vehicle Model Fuel Type"):
        vm_fuels2 = frappe.get_all(
            "Vehicle Model Fuel Type",
            filters={"parent": model_clean, "parenttype": "Vehicle Model"},
            pluck="fuel_type"
        )
        for f in vm_fuels2:
            _add_fuel(str(f))

    if not fuels and frappe.db.exists("DocType", "Vehicle Fuel Type"):
        vf_fuels = frappe.db.get_all("Vehicle Fuel Type", filters={"enabled": 1}, fields=["name", "fuel_type"])
        for f in vf_fuels:
            _add_fuel(f.fuel_type or f.name)

    fuels.sort(key=lambda x: x["fuel_type"].lower())
    return fuels


@frappe.whitelist(allow_guest=True)
def get_fuel_types(model: str | None = None, brand: str | None = None) -> list:
    """
    Compatibility alias for get_vehicle_fuel_types().
    """
    return get_vehicle_fuel_types(model=model, brand=brand)


# ============================================================
# ADMIN VEHICLE MASTER DATA MANAGEMENT (CRUD APIS)
# ============================================================

@frappe.whitelist()
def get_admin_vehicle_masters() -> dict:
    """
    Fetch all Brands, Models (with brand & fuel types), and Fuel Types for the Admin UI.
    Requires Admin / Manager permissions.
    """
    require_admin()

    brands = []
    if frappe.db.exists("DocType", "vms brand"):
        vms_b = frappe.db.get_all("vms brand", fields=["name", "vehicle_brand"])
        for b in vms_b:
            b_name = b.vehicle_brand or b.name
            brands.append({"name": b.name, "brand_name": b_name, "enabled": 1, "description": ""})

    if frappe.db.exists("DocType", "Vehicle Brand"):
        vb_b = frappe.get_all("Vehicle Brand", fields=["name", "brand_name", "enabled", "description"])
        for b in vb_b:
            if not any(x["brand_name"].lower() == b.brand_name.lower() for x in brands):
                brands.append(b)

    models = []
    if frappe.db.exists("DocType", "vms model") and frappe.db.exists("DocType", "vms brand"):
        vms_m = frappe.db.sql(
            """
            SELECT m.model_name, m.fuel_type, b.vehicle_brand
            FROM `tabvms model` m
            JOIN `tabvms brand` b ON m.parent = b.name
            WHERE m.parenttype = 'vms brand'
            """,
            as_dict=True
        )
        m_map = {}
        for m in vms_m:
            key = (m.model_name, m.vehicle_brand)
            if key not in m_map:
                m_map[key] = {"name": m.model_name, "model_name": m.model_name, "vehicle_brand": m.vehicle_brand, "fuel_types": [], "enabled": 1}
            if m.fuel_type and m.fuel_type.title() not in m_map[key]["fuel_types"]:
                m_map[key]["fuel_types"].append(m.fuel_type.title())
        models.extend(m_map.values())

    fuel_types = get_vehicle_fuel_types()

    return {
        "brands": brands,
        "models": models,
        "fuel_types": fuel_types
    }


@frappe.whitelist()
def create_vehicle_brand(brand_name: str, enabled: int = 1, description: str = "") -> dict:
    """
    Create a new Vehicle Brand in vms brand (and Vehicle Brand).
    """
    require_admin()

    if not brand_name or not str(brand_name).strip():
        frappe.throw(_("Brand Name is required."))

    brand_name = str(brand_name).strip()

    # Create in vms brand
    if frappe.db.exists("DocType", "vms brand"):
        if not frappe.db.exists("vms brand", {"vehicle_brand": brand_name}):
            frappe.get_doc({
                "doctype": "vms brand",
                "vehicle_brand": brand_name
            }).insert(ignore_permissions=True)

    # Create in Vehicle Brand
    if frappe.db.exists("DocType", "Vehicle Brand"):
        if not frappe.db.exists("Vehicle Brand", brand_name):
            frappe.get_doc({
                "doctype": "Vehicle Brand",
                "brand_name": brand_name,
                "enabled": int(enabled) if enabled is not None else 1,
                "description": description or ""
            }).insert(ignore_permissions=True)

    return {
        "success": True,
        "message": _("Brand '{0}' created successfully.").format(brand_name)
    }


@frappe.whitelist()
def update_vehicle_brand(brand_name: str, new_name: str | None = None, enabled: int | None = None, description: str | None = None) -> dict:
    require_admin()

    if not brand_name:
        frappe.throw(_("Brand name is required."))

    if frappe.db.exists("DocType", "vms brand"):
        v_b = frappe.db.get_value("vms brand", {"vehicle_brand": brand_name}, "name")
        if v_b and new_name:
            frappe.db.set_value("vms brand", v_b, "vehicle_brand", str(new_name).strip())

    if frappe.db.exists("DocType", "Vehicle Brand") and frappe.db.exists("Vehicle Brand", brand_name):
        doc = frappe.get_doc("Vehicle Brand", brand_name)
        if enabled is not None:
            doc.enabled = int(enabled)
        if description is not None:
            doc.description = description
        if new_name and str(new_name).strip() and str(new_name).strip() != brand_name:
            new_brand_name = str(new_name).strip()
            doc.brand_name = new_brand_name
            doc.save()
            frappe.rename_doc("Vehicle Brand", brand_name, new_brand_name, force=True)
        else:
            doc.save()

    return {
        "success": True,
        "message": _("Brand updated successfully.")
    }


@frappe.whitelist()
def toggle_vehicle_brand(brand_name: str, enabled: int | None = None) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "Vehicle Brand") and frappe.db.exists("Vehicle Brand", brand_name):
        doc = frappe.get_doc("Vehicle Brand", brand_name)
        if enabled is None:
            doc.enabled = 0 if doc.enabled else 1
        else:
            doc.enabled = int(enabled)
        doc.save()
        return {
            "success": True,
            "enabled": doc.enabled,
            "message": _("Brand '{0}' is now {1}.").format(brand_name, "enabled" if doc.enabled else "disabled")
        }

    return {"success": True, "message": "Brand updated."}


@frappe.whitelist()
def delete_vehicle_brand(brand_name: str) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "vms brand"):
        v_b = frappe.db.get_value("vms brand", {"vehicle_brand": brand_name}, "name")
        if v_b:
            frappe.delete_doc("vms brand", v_b, ignore_permissions=True)

    if frappe.db.exists("DocType", "Vehicle Brand") and frappe.db.exists("Vehicle Brand", brand_name):
        frappe.delete_doc("Vehicle Brand", brand_name, ignore_permissions=True)

    return {
        "success": True,
        "message": _("Brand '{0}' deleted successfully.").format(brand_name)
    }


@frappe.whitelist()
def create_vehicle_model(model_name: str, vehicle_brand: str, fuel_types: list | str | None = None, enabled: int = 1) -> dict:
    require_admin()

    if not model_name or not str(model_name).strip():
        frappe.throw(_("Model Name is required."))
    if not vehicle_brand or not str(vehicle_brand).strip():
        frappe.throw(_("Vehicle Brand is required."))

    model_name = str(model_name).strip()
    vehicle_brand = str(vehicle_brand).strip()

    if isinstance(fuel_types, str):
        try:
            fuel_types = json.loads(fuel_types)
        except Exception:
            fuel_types = [f.strip() for f in fuel_types.split(",") if f.strip()]

    # Add to vms brand -> vms model child table
    if frappe.db.exists("DocType", "vms brand"):
        v_b_name = frappe.db.get_value("vms brand", {"vehicle_brand": vehicle_brand}, "name")
        if not v_b_name:
            brand_doc = frappe.get_doc({"doctype": "vms brand", "vehicle_brand": vehicle_brand}).insert(ignore_permissions=True)
            v_b_name = brand_doc.name

        b_doc = frappe.get_doc("vms brand", v_b_name)
        if fuel_types:
            for f in fuel_types:
                f_val = f if isinstance(f, str) else f.get("fuel_type")
                b_doc.append("vehicle_model", {"model_name": model_name, "fuel_type": f_val})
        else:
            b_doc.append("vehicle_model", {"model_name": model_name, "fuel_type": "Petrol"})
        b_doc.save(ignore_permissions=True)

    # Also sync into Vehicle Model
    if frappe.db.exists("DocType", "Vehicle Model"):
        if not frappe.db.exists("Vehicle Brand", vehicle_brand):
            frappe.get_doc({"doctype": "Vehicle Brand", "brand_name": vehicle_brand, "enabled": 1}).insert(ignore_permissions=True)
        if not frappe.db.exists("Vehicle Model", model_name):
            fuel_table = []
            if fuel_types:
                for f in fuel_types:
                    f_val = f if isinstance(f, str) else f.get("fuel_type")
                    if f_val and frappe.db.exists("Vehicle Fuel Type", f_val):
                        fuel_table.append({"fuel_type": f_val})
            frappe.get_doc({
                "doctype": "Vehicle Model",
                "model_name": model_name,
                "vehicle_brand": vehicle_brand,
                "enabled": int(enabled) if enabled is not None else 1,
                "fuel_types": fuel_table
            }).insert(ignore_permissions=True)

    return {
        "success": True,
        "message": _("Model '{0}' created successfully.").format(model_name)
    }


@frappe.whitelist()
def update_vehicle_model(model_name: str, new_name: str | None = None, vehicle_brand: str | None = None, fuel_types: list | str | None = None, enabled: int | None = None) -> dict:
    require_admin()

    if not model_name:
        frappe.throw(_("Model name is required."))

    if isinstance(fuel_types, str):
        try:
            fuel_types = json.loads(fuel_types)
        except Exception:
            fuel_types = [f.strip() for f in fuel_types.split(",") if f.strip()]

    # Update in vms model table
    if frappe.db.exists("DocType", "vms model"):
        if new_name:
            frappe.db.sql("UPDATE `tabvms model` SET model_name = %s WHERE LOWER(model_name) = %s", (new_name, model_name.lower()))

    # Update in Vehicle Model
    if frappe.db.exists("DocType", "Vehicle Model") and frappe.db.exists("Vehicle Model", model_name):
        doc = frappe.get_doc("Vehicle Model", model_name)
        if vehicle_brand:
            doc.vehicle_brand = vehicle_brand
        if enabled is not None:
            doc.enabled = int(enabled)
        if fuel_types is not None:
            doc.set("fuel_types", [])
            for f in fuel_types:
                f_val = f if isinstance(f, str) else f.get("fuel_type")
                if f_val and frappe.db.exists("Vehicle Fuel Type", f_val):
                    doc.append("fuel_types", {"fuel_type": f_val})
        if new_name and str(new_name).strip() and str(new_name).strip() != model_name:
            new_model_name = str(new_name).strip()
            doc.model_name = new_model_name
            doc.save()
            frappe.rename_doc("Vehicle Model", model_name, new_model_name, force=True)
        else:
            doc.save()

    return {
        "success": True,
        "message": _("Model updated successfully.")
    }


@frappe.whitelist()
def toggle_vehicle_model(model_name: str, enabled: int | None = None) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "Vehicle Model") and frappe.db.exists("Vehicle Model", model_name):
        doc = frappe.get_doc("Vehicle Model", model_name)
        if enabled is None:
            doc.enabled = 0 if doc.enabled else 1
        else:
            doc.enabled = int(enabled)
        doc.save()
        return {
            "success": True,
            "enabled": doc.enabled,
            "message": _("Model '{0}' is now {1}.").format(model_name, "enabled" if doc.enabled else "disabled")
        }

    return {"success": True, "message": "Model updated."}


@frappe.whitelist()
def delete_vehicle_model(model_name: str) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "vms model"):
        frappe.db.sql("DELETE FROM `tabvms model` WHERE LOWER(model_name) = %s", (model_name.lower(),))

    if frappe.db.exists("DocType", "Vehicle Model") and frappe.db.exists("Vehicle Model", model_name):
        frappe.delete_doc("Vehicle Model", model_name, ignore_permissions=True)

    return {
        "success": True,
        "message": _("Model '{0}' deleted successfully.").format(model_name)
    }


@frappe.whitelist()
def create_vehicle_fuel_type(fuel_type: str, enabled: int = 1, description: str = "") -> dict:
    require_admin()

    if not fuel_type or not str(fuel_type).strip():
        frappe.throw(_("Fuel Type is required."))

    fuel_type = str(fuel_type).strip()

    if frappe.db.exists("DocType", "Vehicle Fuel Type"):
        if not frappe.db.exists("Vehicle Fuel Type", fuel_type):
            frappe.get_doc({
                "doctype": "Vehicle Fuel Type",
                "fuel_type": fuel_type,
                "enabled": int(enabled) if enabled is not None else 1,
                "description": description or ""
            }).insert(ignore_permissions=True)

    return {
        "success": True,
        "message": _("Fuel Type '{0}' created successfully.").format(fuel_type)
    }


@frappe.whitelist()
def update_vehicle_fuel_type(fuel_type: str, new_name: str | None = None, enabled: int | None = None, description: str | None = None) -> dict:
    require_admin()

    if not fuel_type:
        frappe.throw(_("Fuel type is required."))

    if frappe.db.exists("DocType", "Vehicle Fuel Type") and frappe.db.exists("Vehicle Fuel Type", fuel_type):
        doc = frappe.get_doc("Vehicle Fuel Type", fuel_type)
        if enabled is not None:
            doc.enabled = int(enabled)
        if description is not None:
            doc.description = description
        if new_name and str(new_name).strip() and str(new_name).strip() != fuel_type:
            new_fuel_name = str(new_name).strip()
            doc.fuel_type = new_fuel_name
            doc.save()
            frappe.rename_doc("Vehicle Fuel Type", fuel_type, new_fuel_name, force=True)
        else:
            doc.save()

    return {
        "success": True,
        "message": _("Fuel Type updated successfully.")
    }


@frappe.whitelist()
def toggle_vehicle_fuel_type(fuel_type: str, enabled: int | None = None) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "Vehicle Fuel Type") and frappe.db.exists("Vehicle Fuel Type", fuel_type):
        doc = frappe.get_doc("Vehicle Fuel Type", fuel_type)
        if enabled is None:
            doc.enabled = 0 if doc.enabled else 1
        else:
            doc.enabled = int(enabled)
        doc.save()
        return {
            "success": True,
            "enabled": doc.enabled,
            "message": _("Fuel Type '{0}' is now {1}.").format(fuel_type, "enabled" if doc.enabled else "disabled")
        }

    return {"success": True, "message": "Fuel Type updated."}


@frappe.whitelist()
def delete_vehicle_fuel_type(fuel_type: str) -> dict:
    require_admin()

    if frappe.db.exists("DocType", "Vehicle Fuel Type") and frappe.db.exists("Vehicle Fuel Type", fuel_type):
        frappe.delete_doc("Vehicle Fuel Type", fuel_type, ignore_permissions=True)

    return {
        "success": True,
        "message": _("Fuel Type '{0}' deleted successfully.").format(fuel_type)
    }


# ============================================================
# TECHNICIAN BOOKING EDIT & INSPECTION FORM META
# ============================================================

@frappe.whitelist()
def update_technician_service_booking(
    name: str,
    booking_status: str | None = None,
    service_date: str | None = None,
    service_slot: str | None = None,
) -> dict:
    from vms_vehicle.service_registration import is_staff_user, get_logged_in_customer, SERVICE_DOCTYPE

    user = get_logged_in_customer()
    if not is_staff_user(user):
        frappe.throw(_("Permission denied. Only staff can update bookings."), frappe.PermissionError)

    doc = frappe.get_doc(SERVICE_DOCTYPE, name)
    if booking_status:
        doc.booking_status = str(booking_status).strip()
    if service_date:
        doc.service_date = str(service_date).strip()
    if service_slot:
        doc.service_slot = str(service_slot).strip()

    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "name": doc.name,
        "booking_status": doc.booking_status,
        "service_date": str(doc.service_date),
        "service_slot": doc.service_slot,
        "message": _("Booking application updated successfully."),
    }


@frappe.whitelist()
def get_technician_inspection_form_meta() -> dict:
    from vms_vehicle.service_registration import is_staff_user, get_logged_in_customer

    user = get_logged_in_customer()
    if not is_staff_user(user):
        frappe.throw(_("Permission denied."), frappe.PermissionError)

    slots = get_paginated_data(
        "vms service slot",
        fields=["name", "slot_name", "start_time", "end_time"],
        order_by="name asc"
    )

    spare_parts = []
    if frappe.db.exists("DocType", "vms spare parts"):
        spare_parts = get_paginated_data(
            "vms spare parts",
            fields=["name", "part_name", "quantity"],
            order_by="part_name asc"
        )

    mechanics = []
    roles = frappe.db.get_all("Has Role", filters={"role": "vms mechanic"}, fields=["parent"])
    if roles:
        mechanic_users = [r.parent for r in roles]
        mechanics = get_paginated_data(
            "User",
            filters={"name": ["in", mechanic_users], "enabled": 1},
            fields=["name", "full_name"],
            ignore_permissions=True
        )

    return {
        "slots": slots,
        "spare_parts": spare_parts,
        "mechanics": mechanics,
    }