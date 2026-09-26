# Copyright (c) 2026, developer vms and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class vmsvehicleinspection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer_name: DF.Data | None
		inspected: DF.Check
		inspection_date: DF.Date | None
		issue: DF.Text | None
		labour_hour: DF.Float
		mechanic: DF.Data | None
		spare_part_quantity: DF.Data | None
		spare_parts: DF.Link | None
		technician: DF.Link | None
		vehicle_number: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.resolve_vehicle_link()
		self.populate_customer()
		self.assign_default_technician()
		self.validate_values()

	def resolve_vehicle_link(self):
		if not self.vehicle_number:
			frappe.throw(_("Vehicle is required."))

		# If input matches a registration plate instead of docname, resolve it
		if not frappe.db.exists("vms vehicle registration", self.vehicle_number):
			alt_name = frappe.db.get_value(
				"vms vehicle registration",
				{"vehicle_number": str(self.vehicle_number).strip().upper()},
				"name",
			)
			if alt_name:
				self.vehicle_number = alt_name
			else:
				frappe.throw(_("Vehicle '{0}' does not exist.").format(self.vehicle_number))

	def populate_customer(self):
		if not self.customer_name and self.vehicle_number:
			owner_info = frappe.db.get_value(
				"vms vehicle registration",
				self.vehicle_number,
				["owner_name", "owner_user"],
				as_dict=True,
			)
			if owner_info:
				self.customer_name = owner_info.get("owner_name") or owner_info.get("owner_user")

	def assign_default_technician(self):
		user = getattr(frappe.session, "user", None) or "Guest"
		if not self.technician and user != "Guest":
			self.technician = user

	def validate_values(self):
		if flt(self.labour_hour) < 0:
			frappe.throw(_("Labour hours cannot be negative."))

	def on_update(self):
		if self.inspected and self.vehicle_number:
			from vms_inspection.services import sync_service_status_on_inspection
			sync_service_status_on_inspection(
				vehicle_docname=self.vehicle_number,
				inspection_date=self.inspection_date,
				inspected=self.inspected,
			)

	_DOCTYPE_NAME = "vms vehicle inspection"
