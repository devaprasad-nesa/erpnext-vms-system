# Copyright (c) 2026, vms developer and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, flt
from vms_inspection import services, api


def run_tests():
    print("\n=======================================================")
    print("STARTING VMS TECHNICIAN SPARE PARTS WORKFLOW TESTS")
    print("=======================================================")

    # 1. Setup Test Master Data
    admin_user = "Administrator"
    frappe.set_user(admin_user)

    # Ensure Technician Role & User
    tech_email = "test_technician@example.com"
    if not frappe.db.exists("User", tech_email):
        tech_doc = frappe.get_doc({
            "doctype": "User",
            "email": tech_email,
            "first_name": "Test",
            "last_name": "Technician",
            "enabled": 1,
            "roles": [{"doctype": "Has Role", "role": "vms technician"}]
        }).insert(ignore_permissions=True)
    else:
        tech_doc = frappe.get_doc("User", tech_email)
        roles = [r.role for r in tech_doc.roles]
        if "vms technician" not in roles:
            tech_doc.append("roles", {"doctype": "Has Role", "role": "vms technician"})
            tech_doc.save(ignore_permissions=True)

    # Ensure Customer User
    cust_email = "test_customer_parts@example.com"
    if not frappe.db.exists("User", cust_email):
        frappe.get_doc({
            "doctype": "User",
            "email": cust_email,
            "first_name": "Test",
            "last_name": "Customer",
            "enabled": 1,
            "roles": [{"doctype": "Has Role", "role": "vms customer"}]
        }).insert(ignore_permissions=True)

    # Ensure Vehicle
    veh_docname = None
    existing_veh = frappe.get_all("vms vehicle registration", limit=1, fields=["name", "vehicle_number", "owner_name"])
    if existing_veh:
        veh_docname = existing_veh[0].name
    else:
        new_veh = frappe.get_doc({
            "doctype": "vms vehicle registration",
            "vehicle_number": "KL07AA9999",
            "owner_name": cust_email,
            "owner_user": cust_email,
            "vehicle_type": "Car"
        }).insert(ignore_permissions=True)
        veh_docname = new_veh.name

    # Ensure Master Spare Parts exist
    part1_name = "Brake Pad Test"
    part1 = frappe.db.get_value("vms spare parts", {"part_name": part1_name}, ["name", "part_name", "cost", "quantity"], as_dict=True)
    if not part1:
        p1_doc = frappe.get_doc({
            "doctype": "vms spare parts",
            "part_name": part1_name,
            "quantity": "10 units",
            "cost": 1200.0
        }).insert(ignore_permissions=True)
        part1 = {"name": p1_doc.name, "part_name": part1_name, "cost": 1200.0, "quantity": "10 units"}

    part2_name = "Air Filter Test"
    part2 = frappe.db.get_value("vms spare parts", {"part_name": part2_name}, ["name", "part_name", "cost", "quantity"], as_dict=True)
    if not part2:
        p2_doc = frappe.get_doc({
            "doctype": "vms spare parts",
            "part_name": part2_name,
            "quantity": "5 units",
            "cost": 450.0
        }).insert(ignore_permissions=True)
        part2 = {"name": p2_doc.name, "part_name": part2_name, "cost": 450.0, "quantity": "5 units"}

    frappe.db.commit()

    test_inspection_name = None

    try:
        # TEST 1: Technician Permission Check
        print("\n[TEST 1] Testing permission enforcement for inspection creation...")
        frappe.set_user(cust_email)
        try:
            services.create_inspection({
                "vehicle_number": veh_docname,
                "inspection_date": today(),
                "issue": "Unauthorized creation attempt",
            })
            assert False, "Customer should NOT be able to create an inspection!"
        except frappe.PermissionError:
            print("  ✓ PASSED: Customer correctly denied from creating inspection.")

        # TEST 2: Multi-selection and Child Table creation by Technician
        print("\n[TEST 2] Technician creating inspection with multiple spare parts child rows...")
        frappe.set_user(tech_email)

        parts_payload = [
            {
                "part_name": part1["part_name"],
                "qty": 2,
                "cost": part1["cost"],
                "available_qty": part1["quantity"]
            },
            {
                "part_name": part2["name"],  # Referencing by docname
                "qty": 3,
                "cost": part2["cost"],
                "available_qty": part2["quantity"]
            }
        ]

        create_res = services.create_inspection({
            "vehicle_number": veh_docname,
            "customer_name": cust_email,
            "inspection_date": today(),
            "issue": "Brake pad replacement and air filter cleaning",
            "labour_hour": 2.5,
            "spare_parts": parts_payload,
            "inspected": 1
        })

        assert create_res.get("success"), f"Failed to create inspection: {create_res}"
        test_inspection_name = create_res["name"]
        print(f"  ✓ Inspection created: {test_inspection_name}")

        # Verify child table records in database
        child_rows = frappe.db.sql(
            """
            SELECT name, part_name, qty, cost, amount, available_qty
            FROM `tabvms spare part`
            WHERE parent = %s AND parentfield = 'spare_parts'
            ORDER BY idx ASC
            """,
            (test_inspection_name,),
            as_dict=True
        )

        assert len(child_rows) == 2, f"Expected 2 child rows, got {len(child_rows)}"
        assert child_rows[0].part_name == part1_name
        assert flt(child_rows[0].qty) == 2.0
        assert flt(child_rows[0].cost) == 1200.0
        assert flt(child_rows[0].amount) == 2400.0

        assert child_rows[1].part_name == part2_name
        assert flt(child_rows[1].qty) == 3.0
        assert flt(child_rows[1].cost) == 450.0
        assert flt(child_rows[1].amount) == 1350.0
        print("  ✓ PASSED: Child table rows accurately created with correct amounts (₹2400.00 + ₹1350.00).")

        # TEST 3: Duplicate Prevention in Child Table
        print("\n[TEST 3] Testing duplicate prevention in spare parts selection...")
        dup_payload = [
            {"part_name": part1_name, "qty": 1, "cost": 1200.0},
            {"part_name": part1_name, "qty": 2, "cost": 1200.0},  # Duplicate
        ]
        parsed = services.parse_inspection_spare_parts(dup_payload)
        assert len(parsed) == 1, f"Duplicate was not prevented: {parsed}"
        assert parsed[0]["part_name"] == part1_name
        print("  ✓ PASSED: Duplicate spare part selections correctly filtered.")

        # TEST 4: Quantity Validation (Positive and Stock limits)
        print("\n[TEST 4] Testing quantity validation (<= 0 and exceeding stock)...")
        try:
            services.parse_inspection_spare_parts([{"part_name": part1_name, "qty": -1}])
            assert False, "Negative quantity should fail!"
        except Exception as e:
            print(f"  ✓ Negative quantity correctly rejected: {e}")

        try:
            services.parse_inspection_spare_parts([{"part_name": part1_name, "qty": 50, "available_qty": "10 units"}])
            assert False, "Exceeding available stock should fail!"
        except Exception as e:
            print(f"  ✓ Exceeding stock correctly rejected: {e}")

        # TEST 5: Inspection Details API Retrieval
        print("\n[TEST 5] Testing get_inspection_details API endpoint...")
        details = api.get_inspection_details(test_inspection_name)
        assert details["name"] == test_inspection_name
        assert len(details["spare_parts"]) == 2
        assert flt(details["total_parts_cost"]) == 3750.0  # 2400 + 1350
        print(f"  ✓ API returned details with total_parts_cost: ₹{details['total_parts_cost']}")

        # TEST 6: Updating Inspection Spare Parts
        print("\n[TEST 6] Testing updating inspection spare parts child table...")
        updated_parts_payload = [
            {
                "part_name": part1_name,
                "qty": 1,  # updated from 2 to 1
                "cost": 1200.0,
                "available_qty": "10 units"
            }
        ]
        services.update_inspection(test_inspection_name, {
            "spare_parts": updated_parts_payload,
            "labour_hour": 3.0
        })

        updated_details = api.get_inspection_details(test_inspection_name)
        assert len(updated_details["spare_parts"]) == 1
        assert flt(updated_details["spare_parts"][0]["qty"]) == 1.0
        assert flt(updated_details["total_parts_cost"]) == 1200.0
        print(f"  ✓ PASSED: Inspection updated. New total parts cost: ₹{updated_details['total_parts_cost']}")

        # TEST 7: Accounting Integration Verification
        print("\n[TEST 7] Testing accounts invoice integration with child spare parts table...")
        frappe.set_user(admin_user)
        acc_doc = frappe.get_doc({
            "doctype": "vms accounts",
            "vehicle_inspection": test_inspection_name,
            "vehicle_number": veh_docname,
            "customer_name": cust_email,
            "invoice_date": today(),
        })
        acc_doc.validate()
        # 1200 (spare parts) + 3.0 * 500 (labour) = 1200 + 1500 = 2700
        assert flt(acc_doc.spare_parts_amount) == 1200.0, f"Expected spare_parts_amount 1200, got {acc_doc.spare_parts_amount}"
        assert flt(acc_doc.total_bill) == 2700.0, f"Expected total_bill 2700, got {acc_doc.total_bill}"
        print(f"  ✓ PASSED: Account invoice correctly computed spare_parts_amount=₹{acc_doc.spare_parts_amount} and total_bill=₹{acc_doc.total_bill}")

        print("\n=======================================================")
        print("ALL TECHNICIAN SPARE PARTS WORKFLOW TESTS PASSED (7/7)!")
        print("=======================================================\n")

    finally:
        # Cleanup
        frappe.set_user(admin_user)
        if test_inspection_name and frappe.db.exists("vms vehicle inspection", test_inspection_name):
            frappe.delete_doc("vms vehicle inspection", test_inspection_name, force=True)
            frappe.db.commit()
            print(f"Cleanup: Deleted test inspection {test_inspection_name}")

    return "all_tests_passed"
