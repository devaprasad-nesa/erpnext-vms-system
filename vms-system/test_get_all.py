import frappe
import json
def run():
    frappe.set_user('mechuser1@gmail.com')
    try:
        data = frappe.get_all("vms vehicle inspection")
        return json.dumps(data, default=str)
    except Exception as e:
        import traceback
        return traceback.format_exc()
