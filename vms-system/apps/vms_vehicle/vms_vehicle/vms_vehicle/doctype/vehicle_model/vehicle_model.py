# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleModel(Document):
    def validate(self):
        if self.model_name:
            self.model_name = self.model_name.strip()
        if not self.model_name:
            frappe.throw(_("Model Name is required."))
        if not self.vehicle_brand:
            frappe.throw(_("Vehicle Brand is required."))

        # Verify that vehicle_brand exists
        if not frappe.db.exists("Vehicle Brand", self.vehicle_brand):
            frappe.throw(_("Vehicle Brand '{0}' does not exist.").format(self.vehicle_brand))
