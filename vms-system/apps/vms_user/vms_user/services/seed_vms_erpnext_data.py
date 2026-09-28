# Copyright (c) 2026, VMS Developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today
from vms_user.services.erpnext_user_setup import setup_erpnext_user_roles_and_permissions


def get_default_company():
    """Return the default company or create a fallback company."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        companies = frappe.get_all("Company", limit=1, pluck="name")
        company = companies[0] if companies else None

    if not company:
        c_doc = frappe.get_doc({
            "doctype": "Company",
            "company_name": "DemoCompany",
            "abbr": "D",
            "default_currency": "INR",
            "country": "India",
        }).insert(ignore_permissions=True)
        company = c_doc.name
        frappe.db.set_single_value("Global Defaults", "default_company", company)

    return company


def get_default_warehouse(company=None):
    """Return a physical non-group warehouse for the company."""
    company = company or get_default_company()
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"company": company, "is_group": 0},
        fields=["name"]
    )
    wh = None
    for w in warehouses:
        if "stores" in w.name.lower() or "finished" in w.name.lower():
            wh = w.name
            break
    if not wh and warehouses:
        wh = warehouses[0].name

    if not wh:
        abbr = frappe.db.get_value("Company", company, "abbr") or "D"
        parent_wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
        wh_doc = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "Stores",
            "company": company,
            "parent_warehouse": parent_wh,
            "is_group": 0,
        }).insert(ignore_permissions=True)
        wh = wh_doc.name

    return wh


def seed_item_groups():
    """Ensure required Item Groups exist."""
    groups = [
        {"name": "Spare Parts", "parent": "All Item Groups"},
        {"name": "Vehicle Services", "parent": "All Item Groups"},
    ]
    for g in groups:
        if not frappe.db.exists("Item Group", g["name"]):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": g["name"],
                "parent_item_group": g["parent"],
                "is_group": 0,
            }).insert(ignore_permissions=True)
            print(f"✓ Created Item Group: {g['name']}")


def parse_uom_and_qty(raw_qty_str):
    """Extract numeric quantity and UOM from text like '10 units' or '1 litre'."""
    if not raw_qty_str:
        return 50.0, "Nos"

    s = str(raw_qty_str).strip()
    parts = s.split()
    qty = 50.0
    uom = "Nos"

    try:
        qty = flt(parts[0]) if parts else 50.0
        if qty <= 0:
            qty = 50.0
    except Exception:
        qty = 50.0

    if len(parts) > 1:
        unit = parts[1].lower()
        if "litre" in unit or "ltr" in unit:
            uom = "Litre"
        elif "unit" in unit or "pc" in unit or "nos" in unit:
            uom = "Nos"

    # Ensure UOM exists in ERPNext
    if not frappe.db.exists("UOM", uom):
        if frappe.db.exists("UOM", "Nos"):
            uom = "Nos"
        else:
            frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)

    return qty, uom


def seed_spare_part_items():
    """Migrate legacy VMS spare parts & create ERPNext Item records."""
    seed_item_groups()
    warehouse = get_default_warehouse()
    stock_items_to_receipt = []

    # 1. Migrate legacy 'tabvms spare parts' records if present
    legacy_parts = []
    if frappe.db.exists("DocType", "vms spare parts"):
        legacy_parts = frappe.db.sql(
            """
            SELECT name, part_name, quantity, cost
            FROM `tabvms spare parts`
            """,
            as_dict=True
        )

    items_data = [
        {"item_code": "Engine oil", "item_name": "Engine Oil 1L", "cost": 650.0, "qty_str": "50 litres"},
        {"item_code": "mirror", "item_name": "Rear View Mirror", "cost": 480.0, "qty_str": "20 units"},
        {"item_code": "tail light", "item_name": "Tail Light Assembly", "cost": 250.0, "qty_str": "30 units"},
        {"item_code": "Brake Pad Test", "item_name": "Brake Pad Test Set", "cost": 1200.0, "qty_str": "40 units"},
        {"item_code": "Air Filter Test", "item_name": "Air Filter Test Element", "cost": 450.0, "qty_str": "50 units"},
        {"item_code": "Oil Filter", "item_name": "Engine Oil Filter", "cost": 350.0, "qty_str": "50 units"},
        {"item_code": "Spark Plug", "item_name": "Iridium Spark Plug", "cost": 300.0, "qty_str": "60 units"},
    ]

    for lp in legacy_parts:
        pname = lp.get("part_name") or lp.get("name")
        if pname:
            items_data.append({
                "item_code": lp.name,
                "item_name": pname,
                "cost": flt(lp.cost or 500),
                "qty_str": str(lp.quantity or "50 units")
            })

    added_codes = set()
    for item in items_data:
        code = str(item["item_code"]).strip()
        if code.lower() in added_codes:
            continue
        added_codes.add(code.lower())

        rate = flt(item.get("cost") or 500.0)
        qty, uom = parse_uom_and_qty(item.get("qty_str"))

        if not frappe.db.exists("Item", code):
            item_doc = frappe.get_doc({
                "doctype": "Item",
                "item_code": code,
                "item_name": item.get("item_name") or code,
                "item_group": "Spare Parts",
                "stock_uom": uom,
                "is_stock_item": 1,
                "standard_rate": rate,
                "valuation_rate": rate,
                "opening_stock": 0,
            })
            item_doc.insert(ignore_permissions=True)
            print(f"✓ Created ERPNext Item: {code} ({item.get('item_name')})")

        stock_items_to_receipt.append({
            "item_code": code,
            "qty": qty,
            "rate": rate,
            "uom": uom
        })

    # 2. Seed Service Charges (Non-stock Items)
    service_items = [
        {"item_code": "INSP-LABOUR", "item_name": "Vehicle Inspection & Diagnostic Labour", "rate": 500.0},
        {"item_code": "REPAIR-LABOUR", "item_name": "General Vehicle Repair Labour", "rate": 500.0},
    ]

    for s_item in service_items:
        code = s_item["item_code"]
        if not frappe.db.exists("Item", code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": code,
                "item_name": s_item["item_name"],
                "item_group": "Vehicle Services",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "standard_rate": s_item["rate"],
            }).insert(ignore_permissions=True)
            print(f"✓ Created Service Item: {code}")

    # 3. Create initial Stock Entry (Material Receipt) if stock is empty
    create_initial_stock_receipt(stock_items_to_receipt, warehouse)


def create_initial_stock_receipt(items_list, warehouse):
    """Ensure stock balance exists in ERPNext Stock Ledger via Stock Entry (Material Receipt)."""
    company = get_default_company()
    items_to_add = []

    for item in items_list:
        code = item["item_code"]
        # Check actual stock balance in warehouse
        actual_qty = flt(frappe.db.get_value(
            "Bin",
            {"item_code": code, "warehouse": warehouse},
            "actual_qty"
        ) or 0)

        if actual_qty <= 0:
            items_to_add.append({
                "item_code": code,
                "qty": item["qty"],
                "basic_rate": item["rate"],
                "t_warehouse": warehouse,
                "uom": item["uom"],
                "stock_uom": item["uom"],
                "conversion_factor": 1.0,
            })

    if items_to_add:
        try:
            se = frappe.get_doc({
                "doctype": "Stock Entry",
                "purpose": "Material Receipt",
                "stock_entry_type": "Material Receipt",
                "company": company,
                "to_warehouse": warehouse,
                "posting_date": today(),
                "items": items_to_add,
            })
            se.insert(ignore_permissions=True)
            se.submit()
            print(f"✓ Created Stock Entry (Material Receipt) for {len(items_to_add)} Items in {warehouse}")
        except Exception as e:
            print(f"Notice: Initial stock receipt entry exception: {e}")


def seed_customers():
    """Ensure VMS users with 'vms customer' role exist as ERPNext Customers."""
    cust_roles = frappe.db.get_all("Has Role", filters={"role": "vms customer"}, fields=["parent"])
    cust_users = [c.parent for c in cust_roles] if cust_roles else []

    # Also check existing vehicle owners
    if frappe.db.exists("DocType", "vms vehicle registration"):
        owners = frappe.db.sql(
            """
            SELECT DISTINCT owner_name, owner_user
            FROM `tabvms vehicle registration`
            """,
            as_dict=True
        )
        for o in owners:
            if o.get("owner_name"):
                cust_users.append(o["owner_name"])
            if o.get("owner_user"):
                cust_users.append(o["owner_user"])

    unique_customers = set(cust_users)
    for c_identifier in unique_customers:
        if not c_identifier or c_identifier in ["Administrator", "Guest"]:
            continue

        c_name = str(c_identifier).strip()
        # Ensure name doesn't contain bad SQL characters if query is constructed
        if not frappe.db.exists("Customer", c_name):
            try:
                cust_doc = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": c_name,
                    "customer_type": "Individual",
                    "customer_group": "All Customer Groups",
                    "territory": "All Territories",
                })
                cust_doc.insert(ignore_permissions=True, ignore_mandatory=True)
                print(f"✓ Created ERPNext Customer: {c_name}")
            except Exception as e:
                print(f"Notice creating Customer '{c_name}': {e}")


def seed_suppliers():
    """Ensure standard Suppliers exist in ERPNext."""
    suppliers = [
        "AutoSpare Wholesalers Pvt Ltd",
        "Bosch Automotive Parts",
    ]
    for s_name in suppliers:
        if not frappe.db.exists("Supplier", s_name):
            try:
                frappe.get_doc({
                    "doctype": "Supplier",
                    "supplier_name": s_name,
                    "supplier_group": "All Supplier Groups",
                }).insert(ignore_permissions=True)
                print(f"✓ Created ERPNext Supplier: {s_name}")
            except Exception as e:
                print(f"Notice creating Supplier '{s_name}': {e}")


def run_seed_vms_erpnext_data():
    """Master automation script for seeding ERPNext VMS master data."""
    print("\n=======================================================")
    print("STARTING VMS ERPNEXT MASTER DATA & PERMISSION SEEDING")
    print("=======================================================")

    setup_erpnext_user_roles_and_permissions()
    company = get_default_company()
    warehouse = get_default_warehouse(company)
    print(f"Default Company: {company} | Default Warehouse: {warehouse}")

    seed_item_groups()
    seed_spare_part_items()
    seed_customers()
    seed_suppliers()

    frappe.db.commit()
    print("=======================================================")
    print("VMS ERPNEXT SEEDING COMPLETED SUCCESSFULLY!")
    print("=======================================================\n")
    return "Seeding completed successfully."
