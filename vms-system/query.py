import frappe
def execute():
    return frappe.db.sql("SELECT name, mechanic, booking_status FROM `tabvms vehicle service registration`", as_dict=1)
