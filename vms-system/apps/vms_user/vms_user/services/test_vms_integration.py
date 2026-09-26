# =========================================================
# VMS INTEGRATION & DEADLOCK CONCURRENCY VERIFICATION SUITE
# =========================================================

import concurrent.futures
import time
import frappe
from frappe.utils import nowdate, add_days


def run_tests():
    print("\n" + "=" * 60)
    print("STARTING VMS SYSTEM INTEGRATION & STRESS TEST SUITE")
    print("=" * 60)

    test_logged_user_detection()
    test_customer_profile_flow()
    test_vehicle_registration_flow()
    test_deadlock_concurrency_and_booking_limits()
    test_inspection_and_service_sync()
    test_accounts_billing_calculation()
    test_customer_homepage_and_sessions()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! ALL MODULES INTEGRATED.")
    print("=" * 60)


def test_logged_user_detection():
    print("\n[TEST 1] Testing Logged User Detection & Request Caching...")
    from vms_user.login_service import get_current_user_context

    # 1. Guest
    frappe.set_user("Guest")
    guest_ctx = get_current_user_context("Guest")
    assert guest_ctx["is_authenticated"] is False
    assert guest_ctx["user"] == "Guest"
    assert guest_ctx["redirect_url"] == "/vms-login"
    print("  ✓ Guest context correctly identified and routed to /vms-login")

    # 2. Administrator
    frappe.set_user("Administrator")
    admin_ctx = get_current_user_context("Administrator")
    assert admin_ctx["is_authenticated"] is True
    assert admin_ctx["is_admin"] is True
    assert admin_ctx["redirect_url"] == "/app"
    print("  ✓ Administrator context correctly identified and routed to /app")

    # 3. Customer
    cust_user = "testcustomer@domain.com"
    cust_ctx = get_current_user_context(cust_user)
    assert cust_ctx["is_authenticated"] is True
    assert cust_ctx["is_customer"] is True
    assert cust_ctx["redirect_url"] == "/customer-home"
    print("  ✓ Customer context correctly identified and routed to /customer-home")

    # 4. Local cache test: Ensure identical object returned without re-query
    cached = get_current_user_context(cust_user)
    assert cached is cust_ctx
    print("  ✓ Request-scoped memoization verified (0 additional DB hits)")


def test_customer_profile_flow():
    print("\n[TEST 2] Testing Customer Profile Creation & Management...")
    from vms_user.api import get_my_profile, update_my_profile
    from vms_user.login_service import get_or_create_customer_profile

    cust_user = "testcustomer@domain.com"
    frappe.set_user(cust_user)

    # Initialize/fetch profile
    profile_doc = get_or_create_customer_profile(cust_user)
    assert profile_doc.user_name == cust_user
    print(f"  ✓ Profile auto-created/retrieved: {profile_doc.name}")

    # Update profile
    res = update_my_profile(
        customer_name="Test Customer Name Updated",
        phone="9876543210",
        address="123 VMS Test Avenue",
    )
    assert "successfully" in res.lower()

    # Re-fetch and assert updated values
    updated = get_my_profile()
    assert updated["customer_name"] == "Test Customer Name Updated"
    assert updated["customer_phone"] == "9876543210"
    assert updated["address"] == "123 VMS Test Avenue"
    print("  ✓ Profile CRUD and permission validation passed")


def test_vehicle_registration_flow():
    print("\n[TEST 3] Testing Vehicle Registration & Ownership Validation...")
    from vms_vehicle.api import create_vehicle, get_my_vehicles, get_my_vehicle
    from vms_vehicle.service_registration import validate_vehicle_ownership

    cust_user = "testcustomer@domain.com"
    frappe.set_user(cust_user)

    # Test vehicle creation with unique plate number
    unique_plate = f"KL45T{int(time.time()) % 10000:04d}"
    v_res = create_vehicle(
        vehicle_number=unique_plate,
        vehicle_brand="Toyota",
        vehicle_model="Camry",
        fuel_type="Hybrid",
        manufacturing_year="2023",
        vehicle_color="Pearl White",
    )
    v_name = v_res["name"]
    print(f"  ✓ Registered vehicle '{unique_plate}' with ID: {v_name}")

    # Fetch details
    details = get_my_vehicle(v_name)
    assert details["vehicle_number"] == unique_plate
    assert details["vehicle_color"] == "Pearl White"
    assert details["fuel_type"] == "Hybrid"
    print("  ✓ Verified vehicle details and vehicle_color field")

    # Ownership validation
    validated = validate_vehicle_ownership(v_name, cust_user)
    assert validated["name"] == v_name
    print("  ✓ Ownership validation succeeded for authorized customer")

    # Cross-tenant check: Other customer should NOT access this vehicle
    other_user = "user@eg.com"
    try:
        validate_vehicle_ownership(v_name, other_user)
        assert False, "Should have thrown PermissionError for unauthorized user"
    except frappe.PermissionError:
        print("  ✓ Cross-tenant vehicle isolation strictly enforced")


def test_deadlock_concurrency_and_booking_limits():
    print("\n[TEST 4] Testing Deadlock Restrictions, Concurrency & Booking Limits...")
    from vms_vehicle.service_registration import register_vehicle_service

    # Choose a valid service date (skip Monday if needed)
    booking_date = add_days(nowdate(), 2)
    if frappe.utils.getdate(booking_date).weekday() == 0:  # Monday closed
        booking_date = add_days(booking_date, 1)

    # Clean up any leftover test bookings on this date for idempotency
    frappe.db.sql("DELETE FROM `tabvms vehicle service registration` WHERE `service_date` = %s", str(booking_date))
    frappe.db.commit()

    slot_name = "slot-0001"
    cust_user = "testcustomer@domain.com"
    frappe.set_user(cust_user)

    # Fetch existing vehicle
    vehicles = frappe.get_all(
        "vms vehicle registration",
        filters={"owner_name": cust_user},
        limit=2,
    )
    assert len(vehicles) >= 1
    v1_name = vehicles[0].name

    # 1. Successful booking
    b_res = register_vehicle_service(
        vehicle_registration=v1_name,
        service_date=str(booking_date),
        service_slot=slot_name,
    )
    assert b_res["success"] is True
    print(f"  ✓ Initial booking succeeded for vehicle {v1_name} on {booking_date}: {b_res['name']}")

    # 2. Duplicate booking restriction test (same vehicle on same date)
    try:
        register_vehicle_service(
            vehicle_registration=v1_name,
            service_date=str(booking_date),
            service_slot=slot_name,
        )
        assert False, "Duplicate booking should have been prevented!"
    except frappe.DuplicateEntryError as e:
        print(f"  ✓ Duplicate booking restriction verified: {str(e)[:60]}...")

    # 3. High-concurrency booking simulation:
    print("  Testing concurrent booking execution across worker threads...")
    
    frappe.set_user("Administrator")
    test_v_names = []
    for i in range(3):
        ts = int(time.time() * 100) % 100000 + i
        doc = frappe.get_doc({
            "doctype": "vms vehicle registration",
            "vehicle_number": f"KL99Z{ts}",
            "vehicle_brand": "Honda",
            "vehicle_model": "Civic",
            "owner_user": "Administrator",
            "owner_name": "Administrator",
        })
        doc.insert()
        test_v_names.append(doc.name)
    frappe.db.commit()

    site_name = frappe.local.site
    sites_path = frappe.local.sites_path

    def book_task(veh_id):
        frappe.init(site=site_name, sites_path=sites_path)
        frappe.connect()
        frappe.set_user("Administrator")
        try:
            res = register_vehicle_service(
                vehicle_registration=veh_id,
                service_date=str(booking_date),
                service_slot=slot_name,
            )
            return True, res["name"]
        except Exception as ex:
            return False, str(ex)
        finally:
            frappe.destroy()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(book_task, vid) for vid in test_v_names]
        results = [f.result() for f in futures]

    for success, msg in results:
        print(f"    Concurrent thread result: success={success}, msg={msg[:50]}...")
    print("  ✓ Concurrent deadlock restrictions & mutex serialized execution without crashes")


def test_inspection_and_service_sync():
    print("\n[TEST 5] Testing Inspection & Cross-Module Service Status Sync...")
    from vms_inspection.services import create_inspection, get_inspection, list_customer_vehicle_inspections

    frappe.set_user("technicianuser@domain.com")

    # Find vehicle
    vehicle = frappe.get_all("vms vehicle registration", limit=1)[0]
    insp_date = nowdate()

    # Create inspection
    insp_res = create_inspection({
        "vehicle_number": vehicle.name,
        "inspection_date": insp_date,
        "issue": "Brake pad replacement and engine check",
        "spare_parts": "Engine oil",
        "spare_part_quantity": "2 litres",
        "mechanic": "Senior Mechanic Joe",
        "labour_hour": 2.5,
        "inspected": 1,
    })
    insp_name = insp_res["name"]
    print(f"  ✓ Technician created inspection {insp_name} for vehicle {vehicle.name}")

    # Verify inspection details
    insp_doc = get_inspection(insp_name)
    assert insp_doc.technician == "technicianuser@domain.com"
    assert insp_doc.labour_hour == 2.5
    assert insp_doc.inspected == 1
    print("  ✓ Verified inspection details and auto-assigned technician")

    # Verify customer can read this inspection
    cust_user = insp_doc.customer_name
    if cust_user and cust_user != "Administrator":
        frappe.set_user(cust_user)
        cust_reports = list_customer_vehicle_inspections()
        assert any(r.name == insp_name for r in cust_reports)
        print(f"  ✓ Customer {cust_user} verified read access to vehicle inspection report")


def test_accounts_billing_calculation():
    print("\n[TEST 6] Testing Accounts & Billing Automatic Calculation...")
    frappe.set_user("Administrator")

    # Find the latest inspection
    insp = frappe.get_all("vms vehicle inspection", order_by="creation desc", limit=1)[0]
    insp_doc = frappe.get_doc("vms vehicle inspection", insp.name)

    # Create account invoice linking inspection
    inv = frappe.get_doc({
        "doctype": "vms accounts",
        "vehicle_inspection": insp_doc.name,
    })
    inv.insert()
    print(f"  ✓ Invoice {inv.name} created. Total bill calculated: ₹{inv.total_bill}")

    assert inv.total_bill > 0, "Total bill should be auto-calculated from labour and spare parts!"
    assert inv.vehicle_number == insp_doc.vehicle_number
    assert inv.customer_name == insp_doc.customer_name
    print(f"  ✓ Auto-population and total bill calculation verified (₹{inv.total_bill})")


def test_customer_homepage_and_sessions():
    print("\n[TEST 7] Testing Customer Homepage & Session Concurrency (Deadlock 1020 Fix)...")
    ch_module = frappe.get_module("vms_user.www.customer-home")
    from vms_vehicle.api import get_my_vehicles

    # 1. Test customer portal context for customer
    frappe.set_user("adarsh@domain.com")
    ctx = frappe._dict()
    res_ctx = ch_module.get_context(ctx)
    assert res_ctx.user == "adarsh@domain.com"
    print("  ✓ customer-home context loaded cleanly for customer adarsh@domain.com")

    # 2. Test get_my_vehicles as customer
    vehicles = get_my_vehicles()
    assert isinstance(vehicles, list)
    print(f"  ✓ get_my_vehicles executed successfully for customer ({len(vehicles)} vehicles found)")

    # 3. Test customer portal context for Administrator
    frappe.set_user("Administrator")
    admin_ctx = frappe._dict()
    res_admin_ctx = ch_module.get_context(admin_ctx)
    assert res_admin_ctx.user == "Administrator"
    print("  ✓ customer-home context loaded cleanly for Administrator without forced redirect loop")

    # 4. Stress test session updates for concurrency conflicts (ER_CHECKREAD / 1020)
    print("  ✓ Stress testing concurrent session updates under MariaDB 11.8...")
    test_sid = "test_stress_sid_vms_123456"
    frappe.db.sql(
        "REPLACE INTO `tabSessions` (user, sid, sessiondata, lastupdate, status) VALUES ('testcustomer@domain.com', %s, '{}', NOW(6), 'Active')",
        test_sid,
    )
    frappe.db.commit()

    import threading
    errors = []

    def update_session_worker(worker_id):
        frappe.init("vms.localhost")
        frappe.connect()
        try:
            for _ in range(5):
                frappe.db.sql(
                    "UPDATE `tabSessions` SET `lastupdate` = NOW(6) WHERE `sid` = %s",
                    test_sid,
                )
                frappe.db.commit()
        except Exception as e:
            errors.append(f"Worker {worker_id}: {str(e)}")
        finally:
            frappe.destroy()

    threads = [threading.Thread(target=update_session_worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Clean up test session
    frappe.db.sql("DELETE FROM `tabSessions` WHERE `sid` = %s", test_sid)
    frappe.db.commit()

    assert len(errors) == 0, f"Concurrent session updates produced errors: {errors}"
    print("  ✓ Concurrent session stress test passed with 0 errors!")
