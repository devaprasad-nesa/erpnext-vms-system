import frappe
from vms_inspection.api import get_my_vehicle_inspections, get_inspections, get_inspection_details

def run():
    print("\n--- TEST: Customer Isolation for Vehicle Inspections ---")
    
    # Test 1: caruser1@gmail.com
    frappe.set_user("caruser1@gmail.com")
    inspections_car1 = get_my_vehicle_inspections()
    print(f"caruser1 count: {len(inspections_car1)}")
    for i in inspections_car1:
        print(f"  [caruser1] name: {i['name']}, vehicle: {i['vehicle_number']}, customer: {i['customer_name']}")
        assert i['customer_name'] == "caruser1@gmail.com" or "veh-00058" in i['vehicle_number']
    
    # Test 2: testuser3@gmail.com
    frappe.set_user("testuser3@gmail.com")
    inspections_u3 = get_my_vehicle_inspections()
    print(f"\ntestuser3 count: {len(inspections_u3)}")
    for i in inspections_u3:
        print(f"  [testuser3] name: {i['name']}, vehicle: {i['vehicle_number']}, customer: {i['customer_name']}")
        assert i['customer_name'] == "testuser3@gmail.com" or i['vehicle_number'] in ["veh-00047", "veh-00048", "veh-00049", "veh-00056"]
    
    # Test 3: testuser4@gmail.com
    frappe.set_user("testuser4@gmail.com")
    inspections_u4 = get_my_vehicle_inspections()
    print(f"\ntestuser4 count: {len(inspections_u4)}")
    for i in inspections_u4:
        print(f"  [testuser4] name: {i['name']}, vehicle: {i['vehicle_number']}, customer: {i['customer_name']}")
        assert i['customer_name'] == "testuser4@gmail.com" or i['vehicle_number'] == "veh-00053"

    # Test 4: Cross-tenant direct detail access should fail
    print("\nTesting cross-tenant access restriction...")
    frappe.set_user("caruser1@gmail.com")
    # Attempt to access testuser3 inspection odjfau3191
    try:
        get_inspection_details("odjfau3191")
        assert False, "Should have blocked access to another customer's inspection!"
    except frappe.PermissionError:
        print("  ✓ Cross-tenant inspection detail access properly blocked (PermissionError)")

    # Test 5: Customer calling general get_inspections should also only see their own
    inspections_via_general = get_inspections()
    print(f"  ✓ Customer calling get_inspections sees only {len(inspections_via_general)} records (their own)")
    assert len(inspections_via_general) == len(inspections_car1)

    print("\nALL CUSTOMER ISOLATION TESTS PASSED SUCCESSFULLY! ✓✓✓")
