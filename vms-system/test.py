import frappe
import json
def run():
    frappe.set_user('mechuser1@gmail.com')
    from vms_user.www.vms_user_dashboard.mechanic_dashboard.mechanic_dashboard import get_dashboard_data
    return json.dumps(get_dashboard_data(), default=str)
