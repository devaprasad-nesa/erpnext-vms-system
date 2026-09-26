
import frappe
from frappe import _
from vms_user.pagination import apply_pagination



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
# AUTHENTICATION AND CUSTOMER ACCESS
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

    Kept as a compatibility wrapper for the existing
    customer API methods.
    """

    return require_customer()


# ============================================================
# USER IDENTITY RESOLUTION
# ============================================================

def get_user_identity_values(user):
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

def get_vehicle_owner_filters(user):
    """
    Build ownership filters for the authenticated user.

    A vehicle is considered owned by the user when either:

        owner_user matches the user's identity
        OR
        owner_name matches the user's identity

    This function never accepts a user ID from the browser.
    """

    identity_values = get_user_identity_values(user)

    return [
        {"owner_user": ["in", identity_values]},
        {"owner_name": ["in", identity_values]},
    ]


def get_owned_vehicle(name):
    """
    Fetch a single vehicle only when it belongs to
    the authenticated customer.

    Administrator is allowed to access any vehicle.
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

    # Check the requested vehicle against the logged-in
    # user's ownership values.
    vehicle_name = frappe.get_all(
        DOCTYPE,
        filters={"name": name},
        or_filters=get_vehicle_owner_filters(user),
        pluck="name",
        limit_page_length=1
    )

    if not vehicle_name:
        # Do not reveal whether another customer's vehicle exists.
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

    Ownership is determined using the server-side session.

    The browser cannot pass another customer's user ID
    to retrieve that customer's vehicles.
    """

    user = require_customer()

    # Preserve Administrator access.
    if user == "Administrator":
        filters = {}
        or_filters = []
    else:
        filters = {}
        or_filters = get_vehicle_owner_filters(user)

    vehicles = frappe.get_all(
        DOCTYPE,
        **apply_pagination({
            "filters": filters,
            "or_filters": or_filters,
            "fields": [
                "name",
                "vehicle_number",
                "vehicle_brand",
                "vehicle_model",
                "fuel_type",
                "vehicle_color",
            ],
            "order_by": "creation desc"
        })
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
        "fuel_type": vehicle.fuel_type,
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
def create_vehicle(**kwargs):
    """
    Create a vehicle for the currently authenticated
    VMS customer.

    owner_user and owner_name are assigned on the server.
    They cannot be overridden using browser arguments.
    """

    user = require_customer()

    doc = frappe.get_doc({
        "doctype": DOCTYPE,

        # Secure ownership assignment.
        "owner_user": user,
        "owner_name": user,

        "vehicle_number": kwargs.get("vehicle_number"),
        "vehicle_brand": kwargs.get("vehicle_brand"),
        "vehicle_model": kwargs.get("vehicle_model"),
        "vehicle_type": kwargs.get("vehicle_type"),
        "fuel_type": kwargs.get("fuel_type"),
        "manufacturing_year": kwargs.get("manufacturing_year"),
        "vehicle_color": kwargs.get("vehicle_color") or kwargs.get("color"),
        "chassis_number": kwargs.get("chassis_number"),
        "engine_number": kwargs.get("engine_number"),
        "registration_date": kwargs.get("registration_date"),
        "notes": kwargs.get("notes"),
    })

    doc.insert()

    return {
        "message": "Vehicle registered successfully",
        "name": doc.name
    }


# ============================================================
# UPDATE VEHICLE
# ============================================================

@frappe.whitelist()
def update_vehicle(name: str, **kwargs) -> dict:
    """
    Update a vehicle only when it belongs to
    the authenticated customer.

    Ownership fields are deliberately excluded.
    """

    vehicle = get_owned_vehicle(name)

    allowed_fields = [
        "vehicle_number",
        "vehicle_brand",
        "vehicle_model",
        "fuel_type",
        "manufacturing_year",
        "vehicle_color",
        "chassis_number",
        "engine_number",
        "registration_date",
        "notes",
    ]

    for field in allowed_fields:
        if field in kwargs:
            vehicle.set(field, kwargs[field])

    # owner_user and owner_name are deliberately excluded.
    vehicle.save()

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
        ignore_permissions=False
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

    This method supports the existing vehicle dashboard
    details page, if it calls get_my_vehicle_details().
    """

    vehicle = get_owned_vehicle(vehicle_name)

    return {
        "name": vehicle.name,
        "vehicle_number": vehicle.vehicle_number,
        "vehicle_brand": vehicle.vehicle_brand,
        "vehicle_model": vehicle.vehicle_model,
        "fuel_type": vehicle.fuel_type,
        "user_id": vehicle.owner_user,
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
    """
    Allow technician/staff to update a service booking application.
    """
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
    """
    Return service slots, spare parts, and mechanics for the technician forms.
    """
    from vms_vehicle.service_registration import is_staff_user, get_logged_in_customer

    user = get_logged_in_customer()
    if not is_staff_user(user):
        frappe.throw(_("Permission denied."), frappe.PermissionError)

    slots = frappe.get_all(
        "vms service slot",
        **apply_pagination({
            "fields": ["name", "slot_name", "start_time", "end_time"],
            "order_by": "name asc",
        })
    )

    spare_parts = []
    if frappe.db.exists("DocType", "vms spare parts"):
        spare_parts = frappe.get_all(
            "vms spare parts",
            **apply_pagination({
                "fields": ["name", "part_name", "quantity"],
                "order_by": "part_name asc",
            })
        )

    mechanics = []
    roles = frappe.db.get_all("Has Role", filters={"role": "vms mechanic"}, fields=["parent"])
    if roles:
        mechanic_users = [r.parent for r in roles]
        mechanics = frappe.get_all(
            "User",
            **apply_pagination({
                "filters": {"name": ["in", mechanic_users], "enabled": 1},
                "fields": ["name", "full_name"],
                "ignore_permissions": True,
            })
        )

    return {
        "slots": slots,
        "spare_parts": spare_parts,
        "mechanics": mechanics,
    }

# ============================================================
# VEHICLE MASTER DATA
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_vehicle_brands():
    """
    Return all enabled vehicle brands.
    """

    brands = frappe.get_all(
        "Vehicle Brand",
        fields=[
            "name",
            "brand_name"
        ],
        order_by="brand_name asc"
    )

    return brands


@frappe.whitelist(allow_guest=True)
def get_vehicle_models(brand=None):
    """
    Return vehicle models.

    If a brand is supplied, only models belonging
    to that brand are returned.
    """

    filters = {}

    if brand:
        filters["parent"] = brand

    models = frappe.get_all(
        "Vehicle Model",
        filters=filters,
        fields=[
            "name",
            "model_name",
            "fuel_type"
        ],
        order_by="model_name asc"
    )

    return models


@frappe.whitelist(allow_guest=True)
def get_fuel_types():
    """
    Return all enabled fuel types.
    """

    models = frappe.get_all(
        "Vehicle Model",
        fields=["fuel_type"]
    )
    
    distinct_fuels = sorted(list(set([m.fuel_type for m in models if m.fuel_type])))
    
    return [{"fuel_type": f, "name": f} for f in distinct_fuels]