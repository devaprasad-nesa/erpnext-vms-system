import time
import frappe
from frappe import _

def run_tests():
    print("==================================================================")
    print("RUNNING VEHICLE MASTER DATA & REGISTRATION VALIDATION TEST SUITE")
    print("==================================================================")

    frappe.set_user("Administrator")

    # 1. Test Master Data Read APIs
    test_master_read_apis()

    # 2. Test Admin CRUD APIs & Permissions
    test_admin_crud_apis()

    # 3. Test Registration Validation (Brand -> Model -> Fuel Type)
    test_registration_relationship_validation()

    # 4. Test Customer Vehicle Registration Flow
    test_customer_registration_flow()

    print("\n==================================================================")
    print("ALL VEHICLE MASTER DATA TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("==================================================================")


def test_master_read_apis():
    print("\n[TEST 1] Testing Master Data Read APIs from vms brand & vms model...")
    from vms_vehicle.api import get_vehicle_brands, get_vehicle_models, get_vehicle_fuel_types

    # Read Brands
    brands = get_vehicle_brands()
    assert isinstance(brands, list) and len(brands) > 0, "get_vehicle_brands should return list of brands"
    brand_names = [b["brand_name"] for b in brands]
    assert "Toyota" in brand_names, "Toyota should be in brands from vms brand"
    assert "Maruthi Suzuki" in brand_names, "Maruthi Suzuki should be in brands from vms brand"
    print(f"  ✓ get_vehicle_brands() returned {len(brands)} brands from vms brand: {brand_names}")

    # Read Models for Toyota from child table vms model
    toyota_models = get_vehicle_models(brand="Toyota")
    toyota_model_names = [m["model_name"] for m in toyota_models]
    assert "Innova" in toyota_model_names or "Crysta" in toyota_model_names, "Toyota models should include Innova/Crysta"
    print(f"  ✓ get_vehicle_models('Toyota') returned {len(toyota_models)} models from vms model: {toyota_model_names}")

    # Ensure model from another brand is NOT in Toyota models
    maruthi_models = get_vehicle_models(brand="Maruthi Suzuki")
    maruthi_model_names = [m["model_name"] for m in maruthi_models]
    assert "Swift" in maruthi_model_names, "Maruthi Suzuki models should include Swift"
    assert "Swift" not in toyota_model_names, "Swift must NOT be returned for Toyota"
    print("  ✓ Strict brand filtering verified: Swift is not returned under Toyota")

    # Read Fuel Types for Innova
    innova_fuels = get_vehicle_fuel_types(model="Innova", brand="Toyota")
    innova_fuel_names = [f["fuel_type"] for f in innova_fuels]
    assert "Diesel" in innova_fuel_names, "Innova should support Diesel"
    print(f"  ✓ get_vehicle_fuel_types('Innova', 'Toyota') returned valid fuels from vms model: {innova_fuel_names}")


def test_admin_crud_apis():
    print("\n[TEST 2] Testing Admin Master Data CRUD APIs & Permissions...")
    from vms_vehicle.api import (
        create_vehicle_brand, update_vehicle_brand, toggle_vehicle_brand, delete_vehicle_brand,
        create_vehicle_model, update_vehicle_model, toggle_vehicle_model, delete_vehicle_model,
        create_vehicle_fuel_type, update_vehicle_fuel_type, toggle_vehicle_fuel_type, delete_vehicle_fuel_type,
        get_admin_vehicle_masters,
    )

    test_brand = f"TestBrand_{int(time.time())}"
    test_model = f"TestModel_{int(time.time())}"
    test_fuel = f"TestFuel_{int(time.time())}"

    # Permission check: Normal customer cannot create brand
    frappe.set_user("testcustomer@domain.com")
    try:
        create_vehicle_brand(brand_name="UnauthorizedBrand")
        assert False, "Non-admin user should not be able to create brand"
    except frappe.PermissionError:
        print("  ✓ Permission check: Customer cannot create vehicle brand")

    frappe.set_user("Administrator")

    # Admin: Create Brand
    b_res = create_vehicle_brand(brand_name=test_brand, description="Automated test brand")
    assert b_res["success"] is True
    print(f"  ✓ Admin created brand '{test_brand}'")

    # Admin: Create Fuel Type
    f_res = create_vehicle_fuel_type(fuel_type=test_fuel, description="Automated test fuel")
    assert f_res["success"] is True
    print(f"  ✓ Admin created fuel type '{test_fuel}'")

    # Clean up test brand, fuel
    delete_vehicle_brand(test_brand)
    delete_vehicle_fuel_type(test_fuel)
    print("  ✓ Cleaned up test CRUD records")


def test_registration_relationship_validation():
    print("\n[TEST 3] Testing Strict Relationship Validation (Brand -> Model -> Fuel Type)...")
    from vms_vehicle.api import create_vehicle

    cust_user = "testcustomer@domain.com"
    frappe.set_user(cust_user)

    ts = int(time.time())

    # Case A: Model does not belong to Brand (e.g. Brand: Toyota, Model: Swift [Maruthi Suzuki])
    try:
        create_vehicle(
            vehicle_number=f"KL99INV{ts % 10000:04d}",
            vehicle_brand="Toyota",
            vehicle_model="Swift",  # Swift belongs to Maruthi Suzuki!
            fuel_type="Petrol",
        )
        assert False, "Should reject model belonging to another brand"
    except frappe.ValidationError as e:
        print("  ✓ Successfully rejected mismatch: Model 'Swift' with Brand 'Toyota'")

    # Case B: Fuel Type not supported by Model (e.g. Model: Innova [Diesel], Fuel: Petrol)
    try:
        create_vehicle(
            vehicle_number=f"KL99INV{ts % 10000:04d}",
            vehicle_brand="Toyota",
            vehicle_model="Innova",
            fuel_type="Electric",  # Innova in vms model only supports Diesel!
        )
        assert False, "Should reject unsupported fuel type for model"
    except frappe.ValidationError as e:
        print("  ✓ Successfully rejected mismatch: Fuel 'Electric' with Model 'Innova'")

    # Case C: Non-existent Brand
    try:
        create_vehicle(
            vehicle_number=f"KL99INV{ts % 10000:04d}",
            vehicle_brand="NonExistentBrandXYZ",
            vehicle_model="Innova",
            fuel_type="Diesel",
        )
        assert False, "Should reject non-existent brand"
    except (frappe.DoesNotExistError, frappe.ValidationError):
        print("  ✓ Successfully rejected non-existent Brand")

    # Case D: Non-existent Model
    try:
        create_vehicle(
            vehicle_number=f"KL99INV{ts % 10000:04d}",
            vehicle_brand="Toyota",
            vehicle_model="NonExistentModelXYZ",
            fuel_type="Diesel",
        )
        assert False, "Should reject non-existent model"
    except (frappe.DoesNotExistError, frappe.ValidationError):
        print("  ✓ Successfully rejected non-existent Model")


def test_customer_registration_flow():
    print("\n[TEST 4] Testing Valid Customer Vehicle Registration Flow...")
    from vms_vehicle.api import create_vehicle, get_my_vehicle, delete_vehicle

    cust_user = "testcustomer@domain.com"
    frappe.set_user(cust_user)

    unique_plate = f"KL07TEST{int(time.time()) % 10000:04d}"

    # Valid Registration 1: Toyota -> Crysta -> Diesel
    plate_crysta = f"KL07CRY{int(time.time()) % 10000:04d}"
    res_crysta = create_vehicle(
        vehicle_number=plate_crysta,
        vehicle_brand="Toyota",
        vehicle_model="Crysta",
        vehicle_type="MUV",
        fuel_type="Diesel",
        manufacturing_year="2025",
        vehicle_color="Pearl White",
    )
    v_crysta_name = res_crysta["name"]
    print(f"  ✓ Successfully registered vehicle '{plate_crysta}' with Model 'Crysta' (Doc: {v_crysta_name})")

    # Verify Crysta details
    v_crysta_data = get_my_vehicle(v_crysta_name)
    assert v_crysta_data["vehicle_brand"] == "Toyota"
    assert v_crysta_data["vehicle_model"] == "Crysta"
    assert v_crysta_data["fuel_type"] == "Diesel"
    assert v_crysta_data["vehicle_number"] == plate_crysta
    print(f"  ✓ Verified stored vehicle: Brand='{v_crysta_data['vehicle_brand']}', Model='{v_crysta_data['vehicle_model']}', Fuel='{v_crysta_data['fuel_type']}'")
    delete_vehicle(v_crysta_name)

    # Valid Registration 2: Toyota -> Innova -> Diesel
    res = create_vehicle(
        vehicle_number=unique_plate,
        vehicle_brand="Toyota",
        vehicle_model="Innova",
        vehicle_type="MUV",
        fuel_type="Diesel",
        manufacturing_year="2024",
        vehicle_color="Silver Metallic",
    )
    v_name = res["name"]
    print(f"  ✓ Successfully registered vehicle '{unique_plate}' (Doc: {v_name})")

    # Verify details
    v_data = get_my_vehicle(v_name)
    assert v_data["vehicle_brand"] == "Toyota"
    assert v_data["vehicle_model"] == "Innova"
    assert v_data["fuel_type"] == "Diesel"
    assert v_data["vehicle_number"] == unique_plate
    print(f"  ✓ Verified stored vehicle links: Brand='{v_data['vehicle_brand']}', Model='{v_data['vehicle_model']}', Fuel='{v_data['fuel_type']}'")

    # Clean up test vehicle
    delete_vehicle(v_name)
    print("  ✓ Deleted test customer vehicle")
