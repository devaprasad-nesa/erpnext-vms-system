# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class vmsbrand(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from vms_vehicle.vms_vehicle.doctype.vms_model.vms_model import vmsmodel

		vehicle_brand: DF.Data | None
		vehicle_model: DF.Table[vmsmodel]
	# end: auto-generated types

	def autoname(self):
		if self.vehicle_brand:
			self.name = str(self.vehicle_brand).strip()
		else:
			from frappe.model.naming import set_name_by_naming_series
			set_name_by_naming_series(self)
	_DOCTYPE_NAME = "vms brand"
