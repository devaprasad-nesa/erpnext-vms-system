# =========================================================
# FILE: vms_vehicle/service_registration.py
# PURPOSE: Service slot booking, capacity validation, and
#          deadlock/race-condition restrictions.
# =========================================================

import random
import time
from functools import wraps

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
import MySQLdb

# =========================================================
# CONFIGURATION
# =========================================================

VEHICLE_DOCTYPE = "vms vehicle registration"
SERVICE_DOCTYPE = "vms vehicle service registration"
SLOT_DOCTYPE = "vms service slot"

# Vehicle Registration fields
VEHICLE_OWNER_FIELD = "owner_name"

# Vehicle Service Registration fields
SERVICE_CUSTOMER_FIELD = "customer_name"
SERVICE_VEHICLE_FIELD = "vehicle"
SERVICE_DATE_FIELD = "service_date"
SERVICE_SLOT_FIELD = "service_slot"
SERVICE_STATUS_FIELD = "booking_status"
SERVICE_USER_FIELD = "user_id"

# VMS Service Slot fields
SLOT_NAME_FIELD = "slot_name"
SLOT_START_FIELD = "start_time"
SLOT_END_FIELD = "end_time"
SLOT_WEEKDAY_CAPACITY_FIELD = "weekday_capacity"
SLOT_SATURDAY_CAPACITY_FIELD = "saturday_capacity"
SLOT_ENABLED_FIELD = "enabled"

# Booking rules
DAILY_WEEKDAY_CAPACITY = 15
DAILY_SATURDAY_CAPACITY = 10

HOLIDAY_WEEKDAY = 0  # Monday
DEFAULT_SLOT_CAPACITY = 2

NON_CAPACITY_STATUSES = ["Cancelled"]


# =========================================================
# DEADLOCK RESTRICTION & RETRY HANDLER
# =========================================================

def retry_on_deadlock(max_retries: int = 3, initial_delay: float = 0.05, max_delay: float = 0.5):
    """
    Decorator that detects MariaDB/InnoDB Deadlock (1213) and
    Lock Wait Timeout (1205) errors. Automatically rolls back
    the aborted transaction and retries with randomized backoff.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_err = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (MySQLdb.OperationalError, frappe.db.OperationalError) as err:
                    last_err = err
                    errno = err.args[0] if getattr(err, "args", None) else None
                    if errno in (1213, 1205, 1020) and attempt < max_retries - 1:
                        try:
                            frappe.db.rollback()
                        except Exception:
                            pass
                        # Exponential backoff with random jitter to prevent repeat collisions
                        sleep_duration = delay + random.uniform(0.01, 0.05)
                        time.sleep(sleep_duration)
                        delay = min(delay * 2, max_delay)
                        continue
                    raise
            if last_err:
                raise last_err
        return wrapper
    return decorator


# =========================================================
# USER IDENTITY & SESSION HELPERS
# =========================================================

def get_logged_in_customer() -> str:
    """
    Return the authenticated user from the Frappe session.
    """
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        frappe.throw(
            _("Please log in to continue."),
            frappe.PermissionError,
        )
    return user


def get_user_allowed_identities(user: str | None = None) -> list[str]:
    """
    Resolve identities using vms_user cached context or local fallback.
    """
    user = user or get_logged_in_customer()
    try:
        from vms_user.login_service import get_user_identities
        return get_user_identities(user)
    except Exception:
        identities = [user]
        user_record = frappe.db.get_value(
            "User",
            user,
            ["name", "email", "full_name", "username"],
            as_dict=True,
        )
        if user_record:
            for val in [user_record.name, user_record.email, user_record.full_name, user_record.username]:
                if val and val not in identities:
                    identities.append(val)
        return identities


def is_staff_user(user: str | None = None) -> bool:
    """
    Check if the user has management or technician privileges.
    """
    user = user or getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True

    roles = {r.strip().lower() for r in frappe.get_roles(user)}
    staff_roles = {
        "system manager",
        "administrator",
        "vms manager",
        "vms technician",
        "vms mechanic",
        "vms accountant",
    }
    return bool(roles.intersection(staff_roles))


# =========================================================
# VEHICLE OWNERSHIP & VALIDATION
# =========================================================

def get_customer_vehicles():
    """
    Return vehicles owned by the logged-in customer or all vehicles for staff.
    """
    user = get_logged_in_customer()

    if is_staff_user(user):
        return frappe.get_list(
            VEHICLE_DOCTYPE,
            fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "fuel_type", "owner_name"],
            order_by="creation desc",
            limit_page_length=500,
        )

    allowed_identities = get_user_allowed_identities(user)

    return frappe.get_list(
        VEHICLE_DOCTYPE,
        or_filters=[
            {VEHICLE_OWNER_FIELD: ["in", allowed_identities]},
            {"owner_user": ["in", allowed_identities]},
        ],
        fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "fuel_type", "owner_name"],
        order_by="creation desc",
        limit_page_length=200,
    )


def validate_vehicle_ownership(vehicle_name: str, user: str | None = None):
    """
    Verify that the selected vehicle belongs to the user or that the user is staff.
    """
    user = user or get_logged_in_customer()

    if not vehicle_name:
        frappe.throw(_("Please select a vehicle."))

    # Accept either doc name (veh-00001) or registration plate (KL45E1281)
    vehicle = frappe.db.get_value(
        VEHICLE_DOCTYPE,
        vehicle_name,
        ["name", VEHICLE_OWNER_FIELD, "owner_user", "vehicle_number"],
        as_dict=True,
    )

    if not vehicle:
        # Check by plate number
        alt_name = frappe.db.get_value(
            VEHICLE_DOCTYPE,
            {"vehicle_number": str(vehicle_name).strip().upper()},
            "name",
        )
        if alt_name:
            vehicle = frappe.db.get_value(
                VEHICLE_DOCTYPE,
                alt_name,
                ["name", VEHICLE_OWNER_FIELD, "owner_user", "vehicle_number"],
                as_dict=True,
            )

    if not vehicle:
        frappe.throw(_("The selected vehicle does not exist."))

    if is_staff_user(user):
        return vehicle

    allowed_identities = set(get_user_allowed_identities(user))
    owner_name = vehicle.get(VEHICLE_OWNER_FIELD)
    owner_user = vehicle.get("owner_user")

    if owner_name not in allowed_identities and owner_user not in allowed_identities:
        frappe.throw(
            _("You can only register service for your own vehicles."),
            frappe.PermissionError,
        )

    return vehicle


def validate_service_date(service_date):
    """
    Validate service date against past dates and Monday closure.
    """
    if not service_date:
        frappe.throw(_("Please select a service date."))

    service_date = getdate(service_date)
    today = getdate(nowdate())

    if service_date < today:
        frappe.throw(_("You cannot book a past date."))

    if service_date.weekday() == HOLIDAY_WEEKDAY:
        frappe.throw(_("The workshop is closed on Mondays."))

    return service_date


# =========================================================
# CAPACITY RULES & CALCULATIONS
# =========================================================

def get_daily_capacity(service_date) -> int:
    """
    Monday: 0 (closed)
    Saturday: 10 vehicles
    Sunday, Tuesday-Friday: 15 vehicles
    """
    weekday = getdate(service_date).weekday()
    if weekday == HOLIDAY_WEEKDAY:
        return 0
    if weekday == 5:
        return DAILY_SATURDAY_CAPACITY
    return DAILY_WEEKDAY_CAPACITY


def get_slot_capacity(slot: dict, service_date) -> int:
    """
    Return slot capacity based on weekday vs Saturday.
    """
    service_date = getdate(service_date)
    if service_date.weekday() == 5:
        capacity = slot.get(SLOT_SATURDAY_CAPACITY_FIELD)
    else:
        capacity = slot.get(SLOT_WEEKDAY_CAPACITY_FIELD)

    if capacity is None:
        return DEFAULT_SLOT_CAPACITY
    return max(int(capacity), 0)


def get_booked_count(service_date, slot_name: str | None = None) -> int:
    """
    Count active bookings for a date or specific slot.
    """
    filters = {
        SERVICE_DATE_FIELD: getdate(service_date),
        SERVICE_STATUS_FIELD: ["not in", NON_CAPACITY_STATUSES],
    }
    if slot_name:
        filters[SERVICE_SLOT_FIELD] = slot_name

    return frappe.db.count(SERVICE_DOCTYPE, filters=filters)


def get_enabled_slot(slot_name: str) -> dict:
    """
    Retrieve and validate an active service slot.
    """
    if not slot_name:
        frappe.throw(_("Please select a service slot."))

    slot = frappe.db.get_value(
        SLOT_DOCTYPE,
        slot_name,
        [
            "name",
            SLOT_NAME_FIELD,
            SLOT_START_FIELD,
            SLOT_END_FIELD,
            SLOT_WEEKDAY_CAPACITY_FIELD,
            SLOT_SATURDAY_CAPACITY_FIELD,
            SLOT_ENABLED_FIELD,
        ],
        as_dict=True,
    )

    if not slot:
        # Try finding by slot_name field
        alt_name = frappe.db.get_value(SLOT_DOCTYPE, {SLOT_NAME_FIELD: slot_name}, "name")
        if alt_name:
            slot = frappe.db.get_value(
                SLOT_DOCTYPE,
                alt_name,
                [
                    "name",
                    SLOT_NAME_FIELD,
                    SLOT_START_FIELD,
                    SLOT_END_FIELD,
                    SLOT_WEEKDAY_CAPACITY_FIELD,
                    SLOT_SATURDAY_CAPACITY_FIELD,
                    SLOT_ENABLED_FIELD,
                ],
                as_dict=True,
            )

    if not slot:
        frappe.throw(_("The selected service slot does not exist."))

    if not slot.get(SLOT_ENABLED_FIELD):
        frappe.throw(_("The selected service slot is disabled."))

    return slot


def validate_slot_capacity(service_date, slot_name: str) -> dict:
    """
    Validate booking date and slot capacity limits.
    """
    service_date = validate_service_date(service_date)
    slot = get_enabled_slot(slot_name)

    daily_capacity = get_daily_capacity(service_date)
    daily_booked = get_booked_count(service_date)

    if daily_booked >= daily_capacity:
        frappe.throw(_("The daily booking limit ({0} vehicles) has been reached.").format(daily_capacity))

    slot_capacity = get_slot_capacity(slot, service_date)
    slot_booked = get_booked_count(service_date, slot.get("name"))

    if slot_booked >= slot_capacity:
        frappe.throw(_("The selected time slot '{0}' is fully booked.").format(slot.get(SLOT_NAME_FIELD) or slot.get("name")))

    return slot


# =========================================================
# APIS: SLOTS & BOOKINGS
# =========================================================

@frappe.whitelist()
def get_my_vehicles():
    """Return vehicles belonging to current customer or all vehicles for staff."""
    return get_customer_vehicles()


@frappe.whitelist()
def get_available_service_slots(service_date: str) -> list[dict]:
    """
    Return active slots with remaining capacity for the given date.
    """
    get_logged_in_customer()
    service_date = validate_service_date(service_date)

    daily_capacity = get_daily_capacity(service_date)
    daily_booked = get_booked_count(service_date)
    remaining_daily = daily_capacity - daily_booked

    if remaining_daily <= 0:
        return []

    slots = frappe.get_list(
        SLOT_DOCTYPE,
        filters={SLOT_ENABLED_FIELD: 1},
        fields=[
            "name",
            SLOT_NAME_FIELD,
            SLOT_START_FIELD,
            SLOT_END_FIELD,
            SLOT_WEEKDAY_CAPACITY_FIELD,
            SLOT_SATURDAY_CAPACITY_FIELD,
        ],
        order_by=f"{SLOT_START_FIELD} asc",
    )

    available_slots = []
    for slot in slots:
        capacity = get_slot_capacity(slot, service_date)
        booked = get_booked_count(service_date, slot.name)
        remaining_slot = max(capacity - booked, 0)
        remaining = min(remaining_slot, remaining_daily)

        if remaining <= 0:
            continue

        slot_label = slot.get(SLOT_NAME_FIELD) or slot.name
        start_time_str = str(slot.get(SLOT_START_FIELD) or "")
        end_time_str = str(slot.get(SLOT_END_FIELD) or "")

        available_slots.append({
            "name": slot.name,
            "slot_name": slot_label,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "remaining": remaining,
            "label": f"{slot_label} ({start_time_str} - {end_time_str}) - {remaining} vehicle(s) available",
        })

    return available_slots


@frappe.whitelist()
@retry_on_deadlock(max_retries=3, initial_delay=0.05, max_delay=0.4)
def register_vehicle_service(
    vehicle_registration: str,
    service_date: str,
    service_slot: str,
) -> dict:
    """
    Register a vehicle service with strict deadlock restrictions,
    atomic mutex locking, double-booking prevention, and capacity enforcement.
    """
    user = get_logged_in_customer()

    # 1. Validate vehicle ownership
    vehicle = validate_vehicle_ownership(
        vehicle_name=vehicle_registration,
        user=user,
    )
    vehicle_docname = vehicle["name"]

    # 2. Validate date
    parsed_date = validate_service_date(service_date)

    # 3. Resolve slot
    slot = get_enabled_slot(service_slot)
    slot_docname = slot["name"]

    # 4. Acquire named database lock to serialize concurrent bookings on (date, slot)
    # This prevents concurrent race conditions and eliminates InnoDB gap-lock deadlocks.
    lock_key = f"vms_book_{str(parsed_date)}_{slot_docname}"
    lock_acquired = False

    try:
        res = frappe.db.sql("SELECT GET_LOCK(%s, 10)", lock_key)
        lock_acquired = bool(res and res[0][0] == 1)

        if not lock_acquired:
            frappe.throw(
                _("The booking system is currently busy. Please retry in a few moments."),
                frappe.ValidationError,
            )

        # 5. Row-level lock on the service slot in deterministic order
        frappe.db.sql(
            f"SELECT name FROM `tab{SLOT_DOCTYPE}` WHERE name = %s FOR UPDATE",
            slot_docname,
        )

        # 6. Check duplicate active booking for the same vehicle on the same date
        existing_booking = frappe.db.get_value(
            SERVICE_DOCTYPE,
            {
                SERVICE_VEHICLE_FIELD: vehicle_docname,
                SERVICE_DATE_FIELD: parsed_date,
                SERVICE_STATUS_FIELD: ["not in", NON_CAPACITY_STATUSES],
            },
            ["name", SERVICE_STATUS_FIELD],
            as_dict=True,
        )

        if existing_booking:
            frappe.throw(
                _("Vehicle '{0}' already has an active service booking on {1} ({2}).").format(
                    vehicle.get("vehicle_number") or vehicle_docname,
                    str(parsed_date),
                    existing_booking.name,
                ),
                frappe.DuplicateEntryError,
            )

        # 7. Atomic capacity re-validation under lock
        daily_capacity = get_daily_capacity(parsed_date)
        daily_booked = get_booked_count(parsed_date)
        if daily_booked >= daily_capacity:
            frappe.throw(_("Daily booking limit ({0} vehicles) has been reached.").format(daily_capacity))

        slot_capacity = get_slot_capacity(slot, parsed_date)
        slot_booked = get_booked_count(parsed_date, slot_docname)
        if slot_booked >= slot_capacity:
            frappe.throw(_("The selected time slot is now fully booked."))

        # 8. Create and insert service registration document
        doc = frappe.get_doc({
            "doctype": SERVICE_DOCTYPE,
            SERVICE_CUSTOMER_FIELD: user,
            SERVICE_USER_FIELD: user,
            SERVICE_VEHICLE_FIELD: vehicle_docname,
            SERVICE_DATE_FIELD: parsed_date,
            SERVICE_SLOT_FIELD: slot_docname,
            SERVICE_STATUS_FIELD: "Applied",
        })

        if doc.meta.has_field("start_time"):
            doc.set("start_time", None)

        doc.insert()
        frappe.db.commit()

        return {
            "success": True,
            "name": doc.name,
            "status": doc.get(SERVICE_STATUS_FIELD),
            "service_date": str(parsed_date),
            "service_slot": slot_docname,
            "message": _("Vehicle service request registered successfully."),
        }

    finally:
        if lock_acquired:
            try:
                frappe.db.sql("SELECT RELEASE_LOCK(%s)", lock_key)
            except Exception:
                pass


def _format_service_record(r: dict) -> dict:
    status_val = r.get(SERVICE_STATUS_FIELD) or "Applied"
    vehicle_val = r.get(SERVICE_VEHICLE_FIELD) or ""
    slot_val = r.get(SERVICE_SLOT_FIELD) or ""
    r["status"] = status_val
    r["booking_status"] = status_val
    r["vehicle"] = vehicle_val
    r["vehicle_number"] = vehicle_val
    r["vehicle_registration"] = vehicle_val
    r["service_slot"] = slot_val
    r["slot_label"] = slot_val
    return r


@frappe.whitelist()
def get_my_service_registrations() -> list[dict]:
    """
    Return service requests for the logged-in customer, or all requests for staff.
    """
    user = get_logged_in_customer()

    if is_staff_user(user):
        raw_list = frappe.get_list(
            SERVICE_DOCTYPE,
            fields=[
                "name",
                SERVICE_CUSTOMER_FIELD,
                SERVICE_USER_FIELD,
                SERVICE_VEHICLE_FIELD,
                SERVICE_DATE_FIELD,
                SERVICE_SLOT_FIELD,
                SERVICE_STATUS_FIELD,
                "creation",
            ],
            order_by="creation desc",
            limit_page_length=500,
        )
        return [_format_service_record(r) for r in raw_list]

    allowed_identities = get_user_allowed_identities(user)

    raw_list = frappe.get_all(
        SERVICE_DOCTYPE,
        or_filters=[
            {SERVICE_CUSTOMER_FIELD: ["in", allowed_identities]},
            {SERVICE_USER_FIELD: ["in", allowed_identities]},
        ],
        fields=[
            "name",
            SERVICE_CUSTOMER_FIELD,
            SERVICE_USER_FIELD,
            SERVICE_VEHICLE_FIELD,
            SERVICE_DATE_FIELD,
            SERVICE_SLOT_FIELD,
            SERVICE_STATUS_FIELD,
            "creation",
        ],
        order_by="creation desc",
        limit_page_length=200,
    )
    return [_format_service_record(r) for r in raw_list]


@frappe.whitelist()
def get_my_service_registration(registration_name: str) -> dict:
    """
    Fetch a single service registration ensuring ownership or staff privileges.
    """
    user = get_logged_in_customer()

    registration = frappe.db.get_value(
        SERVICE_DOCTYPE,
        registration_name,
        [
            "name",
            SERVICE_CUSTOMER_FIELD,
            SERVICE_USER_FIELD,
            SERVICE_VEHICLE_FIELD,
            SERVICE_DATE_FIELD,
            SERVICE_SLOT_FIELD,
            SERVICE_STATUS_FIELD,
            "creation",
        ],
        as_dict=True,
    )

    if not registration:
        frappe.throw(_("Service registration not found."), frappe.DoesNotExistError)

    if is_staff_user(user):
        return _format_service_record(registration)

    allowed_identities = set(get_user_allowed_identities(user))
    customer_val = registration.get(SERVICE_CUSTOMER_FIELD)
    user_id_val = registration.get(SERVICE_USER_FIELD)

    if customer_val not in allowed_identities and user_id_val not in allowed_identities:
        frappe.throw(
            _("You are not allowed to view this registration."),
            frappe.PermissionError,
        )

    return _format_service_record(registration)


def validate_service_document(doc, method=None):
    """
    Validate customer/vehicle relationship on service registration save.
    """
    session_user = getattr(frappe.session, "user", None) or "Guest"
    if session_user == "Guest":
        frappe.throw(_("Please log in to continue."), frappe.PermissionError)

    customer = doc.get(SERVICE_CUSTOMER_FIELD)
    vehicle_name = doc.get(SERVICE_VEHICLE_FIELD)

    if not customer and vehicle_name:
        vehicle_owner = frappe.db.get_value(
            VEHICLE_DOCTYPE,
            vehicle_name,
            [VEHICLE_OWNER_FIELD, "owner_user"],
            as_dict=True,
        )
        if vehicle_owner:
            customer = vehicle_owner.get(VEHICLE_OWNER_FIELD) or vehicle_owner.get("owner_user")
            doc.set(SERVICE_CUSTOMER_FIELD, customer)
            doc.set(SERVICE_USER_FIELD, customer)

    if not customer:
        frappe.throw(_("Customer is required."))

    staff = is_staff_user(session_user)
    allowed_identities = set(get_user_allowed_identities(session_user))

    if doc.is_new() and not staff and customer not in allowed_identities:
        frappe.throw(_("You cannot register a service for another customer."), frappe.PermissionError)

    if not doc.is_new() and not staff and customer not in allowed_identities:
        frappe.throw(_("You cannot modify another customer's registration."), frappe.PermissionError)


@frappe.whitelist()
def get_technician_service_bookings(status: str | None = None) -> list[dict]:
    """
    Fetch all vehicle service bookings for technicians, managers, and administrators.
    Supports filtering by booking_status (Applied, Confirmed, Rescheduled, Cancelled, etc.).
    """
    user = get_logged_in_customer()

    if not is_staff_user(user):
        frappe.throw(
            _("You do not have permission to view technician service bookings."),
            frappe.PermissionError,
        )

    filters = {}
    if status and str(status).strip():
        filters[SERVICE_STATUS_FIELD] = str(status).strip()

    bookings = frappe.get_list(
        SERVICE_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            SERVICE_CUSTOMER_FIELD,
            SERVICE_USER_FIELD,
            SERVICE_VEHICLE_FIELD,
            SERVICE_DATE_FIELD,
            SERVICE_SLOT_FIELD,
            SERVICE_STATUS_FIELD,
            "creation",
            "modified",
        ],
        order_by="service_date desc, creation desc",
        limit_page_length=500,
        ignore_permissions=True,
    )

    # Fetch vehicle registration details for enriched display
    vehicle_names = [b.get(SERVICE_VEHICLE_FIELD) for b in bookings if b.get(SERVICE_VEHICLE_FIELD)]
    vehicle_map = {}
    if vehicle_names:
        vehicles = frappe.get_all(
            VEHICLE_DOCTYPE,
            filters={"name": ["in", list(set(vehicle_names))]},
            fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "owner_name"],
        )
        for v in vehicles:
            vehicle_map[v.name] = v

    result = []
    for b in bookings:
        veh = vehicle_map.get(b.get(SERVICE_VEHICLE_FIELD)) or {}
        veh_num = veh.get("vehicle_number")

        result.append({
            "name": b.name,
            "customer_name": b.get(SERVICE_CUSTOMER_FIELD),
            "user_id": b.get(SERVICE_USER_FIELD) or b.get(SERVICE_CUSTOMER_FIELD),
            "vehicle": b.get(SERVICE_VEHICLE_FIELD),
            "vehicle_number": veh_num or b.get(SERVICE_VEHICLE_FIELD),
            "vehicle_brand": veh.get("vehicle_brand"),
            "vehicle_model": veh.get("vehicle_model"),
            "service_date": str(b.get(SERVICE_DATE_FIELD)) if b.get(SERVICE_DATE_FIELD) else None,
            "service_slot": b.get(SERVICE_SLOT_FIELD),
            "booking_status": b.get(SERVICE_STATUS_FIELD),
            "status": b.get(SERVICE_STATUS_FIELD),
            "creation": str(b.creation),
        })

    return result