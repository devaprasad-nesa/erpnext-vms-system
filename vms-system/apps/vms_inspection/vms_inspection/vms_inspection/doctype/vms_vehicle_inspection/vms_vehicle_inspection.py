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
		from vms_inspection.vms_inspection.doctype.vms_spare_part.vms_spare_part import vmssparepart

		customer_name: DF.Data | None
		inspected: DF.Check
		inspection_date: DF.Date | None
		issue: DF.Text | None
		labour_hour: DF.Float
		mechanic: DF.Data | None
		spare_part_quantity: DF.Data | None
		spare_parts: DF.Table[vmssparepart]
		technician: DF.Link | None
		vehicle_number: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.resolve_vehicle_link()
		self.populate_customer()
		self.assign_default_technician()
		self.validate_values()
		self.validate_spare_parts()

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

	def validate_spare_parts(self):
		"""
		Validate child spare_parts table:
		- Prevent duplicate spare parts
		- Ensure Qty Used > 0
		- Validate against available stock where applicable
		- Compute row amount (Qty * Cost)
		"""
		seen_parts = set()
		for row in self.get("spare_parts") or []:
			part_name = (row.part_name or "").strip()
			if not part_name:
				frappe.throw(_("Spare part name is required."))

			norm_part = part_name.lower()
			if norm_part in seen_parts:
				frappe.throw(_("Duplicate spare part '{0}' in inspection.").format(part_name))
			seen_parts.add(norm_part)

			qty = flt(row.qty)
			if qty <= 0:
				frappe.throw(_("Quantity used for spare part '{0}' must be greater than 0.").format(part_name))

			# Fetch master details to check stock and cost
			master_part = frappe.db.sql(
				"""
				SELECT name, part_name, quantity, cost
				FROM `tabvms spare parts`
				WHERE name = %s OR LOWER(part_name) = LOWER(%s)
				LIMIT 1
				""",
				(part_name, part_name),
				as_dict=True
			)
			if master_part:
				mp = master_part[0]
				if not flt(row.cost) and flt(mp.cost):
					row.cost = flt(mp.cost)

				raw_stock = str(mp.quantity or "").strip()
				row.available_qty = raw_stock
				stock_num = None
				try:
					stock_num = flt(raw_stock.split()[0]) if raw_stock else None
				except Exception:
					stock_num = None

				if stock_num is not None and stock_num > 0 and qty > stock_num:
					frappe.throw(
						_("Quantity used ({0}) for spare part '{1}' cannot exceed available stock ({2}).").format(
							qty, part_name, stock_num
						)
					)

			row.cost = flt(row.cost)
			row.qty = qty
			row.amount = round(row.qty * row.cost, 2)

	def on_update(self):
		if self.inspected and self.vehicle_number:
			from vms_inspection.services import sync_service_status_on_inspection
			sync_service_status_on_inspection(
				vehicle_docname=self.vehicle_number,
				inspection_date=self.inspection_date,
				inspected=self.inspected,
			)

	_DOCTYPE_NAME = "vms vehicle inspection"
