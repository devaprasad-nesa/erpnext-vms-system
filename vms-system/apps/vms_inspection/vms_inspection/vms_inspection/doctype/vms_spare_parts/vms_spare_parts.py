# Copyright (c) 2026, developer vms and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class vmsspareparts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost: DF.Currency
		part_name: DF.LongText | None
		quantity: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "vms spare parts"
