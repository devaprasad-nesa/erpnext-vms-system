# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleFuelType(Document):
    def validate(self):
        if self.fuel_type:
            self.fuel_type = self.fuel_type.strip()
        if not self.fuel_type:
            frappe.throw(_("Fuel Type is required."))
