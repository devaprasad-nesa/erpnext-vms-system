# =========================================================
# FILE: vms_account/test_erpnext_accounting_workflow.py
# PURPOSE: Integration test suite for ERPNext Accounts, Stock,
#          Selling, and Payment workflows in VMS.
# =========================================================

import unittest
import frappe
from frappe.utils import nowdate, flt
from vms_account import services, api
from vms_user.services.seed_vms_erpnext_data import run_seed_vms_erpnext_data


class TestERPNextAccountingWorkflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.db.rollback()
        # Seed ERPNext master data, company, item groups, warehouses, items, customers
        run_seed_vms_erpnext_data()
        cls.company = services.get_default_company()
        cls.warehouse = services.get_default_warehouse(cls.company)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_01_master_data_seeded(self):
        """Verify ERPNext Items, Customer, Supplier, and Warehouse exist."""
        items = api.get_spare_part_items()
        self.assertTrue(len(items) > 0, "Spare part items should be seeded in ERPNext")

        warehouses = api.get_warehouses()
        self.assertTrue(len(warehouses) > 0, "Warehouses should exist in ERPNext")

        customers = api.get_customers()
        self.assertTrue(len(customers) > 0, "Customers should exist in ERPNext")

        suppliers = api.get_suppliers()
        self.assertTrue(len(suppliers) > 0, "Suppliers should exist in ERPNext")

    def test_02_complete_service_billing_stock_payment_flow(self):
        """Verify full path: Vehicle -> Inspection -> Spare Parts -> Stock Issue -> Sales Invoice -> Payment Entry."""
        cust_name = "vms customer"
        if not frappe.db.exists("Customer", cust_name):
            services.erpnext_customer.create_or_update_customer(customer_name=cust_name)

        customer_doc = frappe.get_doc("Customer", cust_name)
        
        # 1. Fetch or create Vehicle Registration
        existing_vehicle = frappe.db.get_value("vms vehicle registration", {}, ["name", "vehicle_number", "vehicle_brand", "vehicle_model", "fuel_type"], as_dict=True)
        if existing_vehicle:
            vehicle_number = existing_vehicle.vehicle_number
        else:
            # Query first valid VMS Brand & Model
            brand_doc = frappe.get_doc("VMS Brand", frappe.db.get_value("VMS Brand", {}))
            vehicle_number = "KA-01-EXP-9999"
            vehicle = frappe.get_doc({
                "doctype": "vms vehicle registration",
                "vehicle_number": vehicle_number,
                "owner_name": "Administrator",
                "vehicle_brand": brand_doc.vehicle_brand or brand_doc.name,
                "vehicle_model": brand_doc.vms_models[0].vehicle_model if brand_doc.vms_models else "Default",
                "fuel_type": brand_doc.vms_models[0].fuel_type if brand_doc.vms_models else "Petrol",
            })
            vehicle.flags.ignore_permissions = True
            vehicle.insert(ignore_permissions=True)

        # 2. Create Service Booking
        booking = frappe.get_doc({
            "doctype": "vms vehicle service registration",
            "customer_name": customer_doc.name,
            "vehicle_number": vehicle_number,
            "service_date": nowdate(),
            "status": "In Progress",
            "service_issue": "Full inspection and brake replace",
        })
        booking.flags.ignore_links = True
        booking.insert(ignore_permissions=True, ignore_links=True)

        # 3. Create Vehicle Inspection with ERPNext Spare Parts
        items = api.get_spare_part_items()
        test_item = items[0]
        item_code = test_item["item_code"]

        inspection = frappe.get_doc({
            "doctype": "vms vehicle inspection",
            "customer_name": customer_doc.name,
            "vehicle_number": vehicle_number,
            "inspection_date": nowdate(),
            "released_to_accountant": 1,
        })
        inspection.append("spare_parts", {
            "item_code": item_code,
            "part_name": test_item["item_name"],
            "qty": 2,
            "cost": test_item.get("standard_rate", 500),
            "amount": 2 * test_item.get("standard_rate", 500),
            "warehouse": self.warehouse,
        })
        inspection.flags.ignore_links = True
        inspection.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.commit()

        # 4. Stock Consumption Entry (Material Issue)
        stock_res = api.create_stock_consumption_entry(inspection_name=inspection.name, warehouse=self.warehouse)
        self.assertTrue(stock_res.get("success"), f"Stock consumption failed: {stock_res}")
        stock_entry_name = stock_res.get("stock_entry")
        self.assertTrue(frappe.db.exists("Stock Entry", stock_entry_name))
        
        st_doc = frappe.get_doc("Stock Entry", stock_entry_name)
        self.assertEqual(st_doc.docstatus, 1, "Stock Entry must be submitted")
        self.assertEqual(st_doc.stock_entry_type, "Material Issue")

        # 5. Sales Invoice Creation
        inv_res = api.create_sales_invoice(inspection_name=inspection.name, submit=True)
        self.assertTrue(inv_res.get("success"), f"Sales invoice creation failed: {inv_res}")
        inv_name = inv_res.get("name")
        self.assertTrue(frappe.db.exists("Sales Invoice", inv_name))

        inv_doc = frappe.get_doc("Sales Invoice", inv_name)
        self.assertEqual(inv_doc.docstatus, 1, "Sales Invoice must be submitted")
        self.assertGreater(inv_doc.grand_total, 0, "Grand total must be > 0")

        # 6. Payment Entry Creation
        pay_res = api.create_payment_entry(sales_invoice=inv_name, paid_amount=inv_doc.grand_total)
        self.assertTrue(pay_res.get("success"), f"Payment entry failed: {pay_res}")
        pay_name = pay_res.get("name")
        self.assertTrue(frappe.db.exists("Payment Entry", pay_name))

        inv_doc.reload()
        self.assertEqual(inv_doc.status, "Paid", "Sales Invoice status must update to Paid")
        self.assertEqual(flt(inv_doc.outstanding_amount), 0, "Outstanding amount must be 0")

        # 7. Check Dashboard Data & Customer Outstanding
        dashboard = api.get_dashboard_data()
        self.assertIn("inspections", dashboard)
        self.assertIn("invoices", dashboard)
        
        outstanding = api.get_customer_outstanding(customer=customer_doc.name)
        self.assertEqual(flt(outstanding.get("outstanding_amount", 0)), 0)

        reports = api.get_accounting_reports()
        self.assertIn("monthly_sales", reports)
