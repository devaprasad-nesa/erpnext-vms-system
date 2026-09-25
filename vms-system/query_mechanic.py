import frappe
import json

frappe.init(site="vms.localhost", sites_path="sites")
frappe.connect()
frappe.set_user('mechuser1@gmail.com')
from vms_user.www.vms_user_dashboard.mechanic_dashboard.mechanic_dashboard import get_dashboard_data
print(json.dumps(get_dashboard_data(), default=str))
