# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class vmsserviceslot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		end_time: DF.Time | None
		saturday_capacity: DF.Int
		slot_name: DF.Data | None
		start_time: DF.Time | None
		weekday_capacity: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "vms service slot"
