# Copyright (c) 2026, vms developer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

HOURLY_LABOUR_RATE = 500.0


class vmsaccounts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		audited: DF.Check
		customer_name: DF.Link | None
		invoice_date: DF.Date | None
		spare_parts_amount: DF.Currency
		total_bill: DF.Currency
		vehicle_inspection: DF.Link | None
		vehicle_number: DF.Link | None
		vehicle_spare_parts: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.populate_from_inspection()
		self.calculate_total_bill()

	def populate_from_inspection(self):
		if not self.vehicle_inspection:
			return

		inspection = frappe.db.get_value(
			"vms vehicle inspection",
			self.vehicle_inspection,
			["vehicle_number", "customer_name", "spare_parts", "spare_part_quantity", "labour_hour"],
			as_dict=True,
		)
		if not inspection:
			return

		if not self.vehicle_number:
			self.vehicle_number = inspection.vehicle_number

		if not self.customer_name:
			self.customer_name = inspection.customer_name

		if not self.vehicle_spare_parts and inspection.spare_parts:
			self.vehicle_spare_parts = inspection.spare_parts

	def calculate_total_bill(self):
		spare_parts_cost = 0.0
		labour_cost = 0.0

		# 1. Calculate spare parts cost
		if self.vehicle_spare_parts:
			part_info = frappe.db.get_value(
				"vms spare parts",
				self.vehicle_spare_parts,
				["cost", "quantity"],
				as_dict=True,
			)
			if part_info:
				unit_cost = flt(part_info.cost)
				# Check if inspection specified an explicit quantity
				qty = 1.0
				if self.vehicle_inspection:
					insp_qty = frappe.db.get_value("vms vehicle inspection", self.vehicle_inspection, "spare_part_quantity")
					if insp_qty:
						try:
							qty = flt("".join(c for c in str(insp_qty) if c.isdigit() or c == ".")) or 1.0
						except Exception:
							qty = 1.0
				spare_parts_cost = unit_cost * qty

		# 2. Calculate labour cost from inspection hours
		if self.vehicle_inspection:
			hours = flt(frappe.db.get_value("vms vehicle inspection", self.vehicle_inspection, "labour_hour") or 0)
			labour_cost = hours * HOURLY_LABOUR_RATE

		self.spare_parts_amount = round(spare_parts_cost, 2)
		computed = round(spare_parts_cost + labour_cost, 2)

		# Allow accountant to manually set/override total_bill:
		# If total_bill has already been entered (> 0), preserve it.
		if not flt(self.total_bill) or flt(self.total_bill) <= 0:
			self.total_bill = computed

	_DOCTYPE_NAME = "vms accounts"
