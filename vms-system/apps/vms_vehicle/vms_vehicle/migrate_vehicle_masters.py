import os
import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.model.sync import sync_for

def run():
    print("0. Cleaning old obsolete master records...")
    frappe.db.sql("TRUNCATE `tabVehicle Model`")
    frappe.db.sql("TRUNCATE `tabVehicle Brand`")
    frappe.db.sql("TRUNCATE `tabVehicle Fuel Type`")
    frappe.db.sql("TRUNCATE `tabVehicle Model Fuel Type`")
    frappe.db.commit()

    print("1. Importing DocType JSON schemas...")
    base_dir = frappe.get_app_path("vms_vehicle")
    doctypes_to_import = [
        os.path.join(base_dir, "vms_vehicle/doctype/vehicle_brand/vehicle_brand.json"),
        os.path.join(base_dir, "vms_vehicle/doctype/vehicle_fuel_type/vehicle_fuel_type.json"),
        os.path.join(base_dir, "vms_vehicle/doctype/vehicle_model_fuel_type/vehicle_model_fuel_type.json"),
        os.path.join(base_dir, "vms_vehicle/doctype/vehicle_model/vehicle_model.json"),
        os.path.join(base_dir, "vms_vehicle/doctype/vms_vehicle_registration/vms_vehicle_registration.json"),
    ]

    for dt_path in doctypes_to_import:
        try:
            import_file_by_path(dt_path, force=True)
            print(f"  Successfully imported {dt_path}")
        except Exception as e:
            print(f"  Error importing {dt_path}: {e}")

    frappe.db.commit()

    print("\n2. Updating DocType DB schemas (sync)...")
    sync_for("vms_vehicle", force=True)
    frappe.db.commit()

    print("\n3. Migrating existing vehicle records...")
    existing_vehicles = frappe.db.get_all(
        "vms vehicle registration",
        fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "fuel_type"],
    )

    def normalize_title(val):
        if not val:
            return ""
        val = str(val).strip()
        norm_map = {
            "HONDA": "Honda",
            "honda": "Honda",
            "MARUTHI SUZUKI": "Maruti Suzuki",
            "Maruti Suzuki": "Maruti Suzuki",
            "MAHINDRA": "Mahindra",
            "mahindra": "Mahindra",
            "TATA": "Tata",
            "tata": "Tata",
            "OTHER": "Other",
            "other": "Other",
            "CITY": "City",
            "city": "City",
            "SWIFT": "Swift",
            "swift": "Swift",
            "SCORPIO": "Scorpio",
            "scorpio": "Scorpio",
            "NEXON": "Nexon",
            "nexon": "Nexon",
            "HUNK": "Hunk",
            "hunk": "Hunk",
            "CB100": "CB100",
            "CT100": "CT100",
            "PETROL": "Petrol",
            "petrol": "Petrol",
            "DIESEL": "Diesel",
            "diesel": "Diesel",
            "ELECTRIC": "Electric",
            "electric": "Electric",
            "HYBRID": "Hybrid",
            "hybrid": "Hybrid",
            "CNG": "CNG",
            "cng": "CNG",
        }
        return norm_map.get(val, norm_map.get(val.upper(), val.title()))

    # Common default fuel types
    default_fuels = ["Petrol", "Diesel", "Electric", "Hybrid", "CNG", "LPG"]
    for fuel in default_fuels:
        if not frappe.db.exists("Vehicle Fuel Type", fuel):
            frappe.get_doc({
                "doctype": "Vehicle Fuel Type",
                "fuel_type": fuel,
                "enabled": 1,
            }).insert(ignore_permissions=True)
            print(f"  Created default Vehicle Fuel Type: {fuel}")

    frappe.db.commit()

    # Populate standard vehicle catalog first so all existing and common vehicles have proper links
    standard_catalog = {
        "Toyota": {
            "Corolla": ["Petrol", "Hybrid"],
            "Camry": ["Petrol", "Hybrid"],
            "Innova": ["Petrol", "Diesel", "Hybrid"],
            "Fortuner": ["Petrol", "Diesel"],
            "Yaris": ["Petrol"],
            "RAV4": ["Petrol", "Hybrid", "Electric"],
        },
        "Honda": {
            "City": ["Petrol", "Hybrid"],
            "Civic": ["Petrol", "Hybrid"],
            "Amaze": ["Petrol", "Diesel"],
            "CR-V": ["Petrol", "Hybrid"],
            "Elevate": ["Petrol"],
            "Hunk": ["Petrol", "Diesel"],
        },
        "Hyundai": {
            "i20": ["Petrol", "Diesel"],
            "Creta": ["Petrol", "Diesel"],
            "Verna": ["Petrol", "Diesel"],
            "Tucson": ["Petrol", "Diesel"],
            "Ioniq 5": ["Electric"],
            "Kona Electric": ["Electric"],
        },
        "Maruti Suzuki": {
            "Swift": ["Petrol", "CNG", "Diesel"],
            "Baleno": ["Petrol", "CNG"],
            "Dzire": ["Petrol", "CNG"],
            "Brezza": ["Petrol", "CNG"],
            "Ertiga": ["Petrol", "CNG"],
            "Grand Vitara": ["Petrol", "Hybrid", "CNG"],
        },
        "Tata": {
            "Nexon": ["Petrol", "Diesel", "Electric", "CNG"],
            "Harrier": ["Diesel"],
            "Safari": ["Diesel"],
            "Punch": ["Petrol", "Electric", "CNG"],
            "Tiago": ["Petrol", "Electric", "CNG"],
            "Altroz": ["Petrol", "Diesel", "CNG"],
        },
        "Mahindra": {
            "Scorpio": ["Petrol", "Diesel"],
            "XUV700": ["Petrol", "Diesel"],
            "Thar": ["Petrol", "Diesel"],
            "Bolero": ["Diesel"],
            "XUV400": ["Electric"],
        },
        "Other": {
            "CB100": ["Petrol"],
            "CT100": ["Petrol"],
            "Hunk": ["Petrol", "Diesel"],
        }
    }

    # Sync all models from vms brand / vms model child table
    if frappe.db.exists("DocType", "vms brand") and frappe.db.exists("DocType", "vms model"):
        vms_b_list = frappe.get_all("vms brand", fields=["name", "vehicle_brand"])
        for vb in vms_b_list:
            b_name = vb.vehicle_brand or vb.name
            if not frappe.db.exists("Vehicle Brand", b_name):
                frappe.get_doc({
                    "doctype": "Vehicle Brand",
                    "brand_name": b_name,
                    "enabled": 1,
                }).insert(ignore_permissions=True)
            
            child_models = frappe.db.sql(
                "SELECT model_name, fuel_type FROM `tabvms model` WHERE parent = %s AND parenttype = 'vms brand'",
                (vb.name,),
                as_dict=True
            )
            for cm in child_models:
                m_name = (cm.model_name or "").strip()
                ft_val = (cm.fuel_type or "").strip().title()
                if not m_name:
                    continue
                if not frappe.db.exists("Vehicle Model", m_name):
                    m_doc = frappe.get_doc({
                        "doctype": "Vehicle Model",
                        "model_name": m_name,
                        "vehicle_brand": b_name,
                        "enabled": 1,
                        "fuel_types": [{"fuel_type": ft_val}] if ft_val else [],
                    })
                    m_doc.insert(ignore_permissions=True)
                else:
                    m_doc = frappe.get_doc("Vehicle Model", m_name)
                    if ft_val:
                        existing_fuels = [r.fuel_type for r in (m_doc.fuel_types or [])]
                        if ft_val not in existing_fuels:
                            m_doc.append("fuel_types", {"fuel_type": ft_val})
                            m_doc.save(ignore_permissions=True)

    frappe.db.commit()

    # Collect brands, models, fuels from existing registrations
    for veh in existing_vehicles:
        raw_brand = veh.get("vehicle_brand")
        raw_model = veh.get("vehicle_model")
        raw_fuel = veh.get("fuel_type")

        brand_name = normalize_title(raw_brand)
        model_name = normalize_title(raw_model)
        fuel_name = normalize_title(raw_fuel)

        if not brand_name or not model_name:
            continue

        # Ensure Brand exists
        if not frappe.db.exists("Vehicle Brand", brand_name):
            frappe.get_doc({
                "doctype": "Vehicle Brand",
                "brand_name": brand_name,
                "enabled": 1,
            }).insert(ignore_permissions=True)
            print(f"  Created Vehicle Brand: {brand_name}")

        # Ensure Fuel Type exists
        if fuel_name and not frappe.db.exists("Vehicle Fuel Type", fuel_name):
            frappe.get_doc({
                "doctype": "Vehicle Fuel Type",
                "fuel_type": fuel_name,
                "enabled": 1,
            }).insert(ignore_permissions=True)
            print(f"  Created Vehicle Fuel Type: {fuel_name}")

        # Ensure Model exists
        if not frappe.db.exists("Vehicle Model", model_name):
            model_doc = frappe.get_doc({
                "doctype": "Vehicle Model",
                "model_name": model_name,
                "vehicle_brand": brand_name,
                "enabled": 1,
                "fuel_types": [{"fuel_type": fuel_name}] if fuel_name else [],
            })
            model_doc.insert(ignore_permissions=True)
            print(f"  Created Vehicle Model: {model_name} (Brand: {brand_name})")
        else:
            model_doc = frappe.get_doc("Vehicle Model", model_name)
            existing_model_fuels = [r.fuel_type for r in (model_doc.fuel_types or [])]
            if fuel_name and fuel_name not in existing_model_fuels:
                model_doc.append("fuel_types", {"fuel_type": fuel_name})
                model_doc.save(ignore_permissions=True)
                print(f"  Added fuel {fuel_name} to Model {model_name}")

        # Update the vehicle registration record
        frappe.db.set_value(
            "vms vehicle registration",
            veh["name"],
            {
                "vehicle_brand": brand_name,
                "vehicle_model": model_name,
                "fuel_type": fuel_name,
            },
            update_modified=False,
        )

    frappe.db.commit()

    print("\n4. Verifying migrated vehicle registrations:")
    all_vehicles = frappe.db.get_all(
        "vms vehicle registration",
        fields=["name", "vehicle_number", "vehicle_brand", "vehicle_model", "fuel_type"],
    )
    for v in all_vehicles:
        print(f"  {v.name}: {v.vehicle_number} | {v.vehicle_brand} -> {v.vehicle_model} -> {v.fuel_type}")

    print("\nMigration completed successfully!")
