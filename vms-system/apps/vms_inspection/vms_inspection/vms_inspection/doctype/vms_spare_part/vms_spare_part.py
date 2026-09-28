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
		self.qty = flt(self.qty)
		self.cost = flt(self.cost)
		self.amount = round(self.qty * self.cost, 2)

	_DOCTYPE_NAME = "vms spare part"
