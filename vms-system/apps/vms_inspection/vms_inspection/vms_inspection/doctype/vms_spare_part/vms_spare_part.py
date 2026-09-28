# Copyright (c) 2026, developer vms and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class vmssparepart(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		available_qty: DF.Data | None
		cost: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		part_name: DF.Data | None
		qty: DF.Float
	# end: auto-generated types

	def validate(self):
		if not self.item_code and self.part_name:
			self.item_code = self.part_name

		if self.item_code and frappe.db.exists("Item", self.item_code):
			item_data = frappe.db.get_value("Item", self.item_code, ["item_name", "standard_rate"], as_dict=True)
			if item_data:
				if not self.part_name:
					self.part_name = item_data.item_name or self.item_code
				if not flt(self.cost):
					self.cost = flt(item_data.standard_rate)

		self.qty = flt(self.qty)
		self.cost = flt(self.cost)
		self.amount = round(self.qty * self.cost, 2)

	_DOCTYPE_NAME = "vms spare part"
