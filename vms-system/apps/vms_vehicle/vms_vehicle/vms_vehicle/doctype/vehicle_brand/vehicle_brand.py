# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VehicleBrand(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from vms_vehicle.vms_vehicle.doctype.vehicle_model.vehicle_model import VehicleModel

		brand_name: DF.Data | None
		model_name: DF.Table[VehicleModel]
	# end: auto-generated types
	def self_name(self):
		self.name = self.brand_name + self.model_name
	
	

	_DOCTYPE_NAME = "Vehicle Brand"
