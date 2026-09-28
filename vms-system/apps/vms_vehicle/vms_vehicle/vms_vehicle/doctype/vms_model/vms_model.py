# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class vmsmodel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fuel_type: DF.Data | None
		model_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	_DOCTYPE_NAME = "vms model"
