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
		Validate child spare_parts table against ERPNext Item master and Stock Ledger:
		- Verify Item exists and is enabled
		- Prevent duplicate Item selections
		- Ensure Qty Used > 0
		- Validate against available stock in Bin
		- Auto-populate rate/cost and calculate row amount
		"""
		seen_items = set()
		for row in self.get("spare_parts") or []:
			code = (row.item_code or row.part_name or "").strip()
			if not code:
				frappe.throw(_("Item code or spare part name is required."))

			# Resolve Item Code
			item = frappe.db.get_value("Item", code, ["name", "item_name", "standard_rate", "valuation_rate", "disabled", "stock_uom"], as_dict=True)
			if not item:
				item_by_name = frappe.db.get_value("Item", {"item_name": code}, ["name", "item_name", "standard_rate", "valuation_rate", "disabled", "stock_uom"], as_dict=True)
				if item_by_name:
					item = item_by_name

			if not item:
				frappe.throw(_("Spare part Item '{0}' does not exist in ERPNext Item master.").format(code))

			if item.disabled:
				frappe.throw(_("Spare part Item '{0}' is disabled.").format(item.name))

			row.item_code = item.name
			row.part_name = item.item_name or item.name

			norm_code = item.name.lower()
			if norm_code in seen_items:
				frappe.throw(_("Duplicate spare part Item '{0}' in inspection.").format(row.part_name))
			seen_items.add(norm_code)

			qty = flt(row.qty)
			if qty <= 0:
				frappe.throw(_("Quantity used for spare part '{0}' must be greater than 0.").format(row.part_name))

			if not flt(row.cost):
				row.cost = flt(item.standard_rate or item.valuation_rate or 0.0)

			# Validate stock availability in Bin
			actual_qty = flt(frappe.db.get_value("Bin", {"item_code": item.name}, "sum(actual_qty)") or 0.0)
			uom = item.stock_uom or "Nos"
			row.available_qty = f"{actual_qty} {uom}"

			if actual_qty > 0 and qty > actual_qty:
				frappe.throw(
					_("Quantity used ({0}) for spare part '{1}' cannot exceed available stock ({2} {3}).").format(
						qty, row.part_name, actual_qty, uom
					)
				)

			row.qty = qty
			row.cost = flt(row.cost)
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
