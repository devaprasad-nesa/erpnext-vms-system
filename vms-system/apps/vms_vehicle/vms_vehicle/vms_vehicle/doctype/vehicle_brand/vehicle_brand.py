# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleBrand(Document):
    def validate(self):
        if self.brand_name:
            self.brand_name = self.brand_name.strip()
        if not self.brand_name:
            frappe.throw(_("Brand Name is required."))
