# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class vmsvehicleserviceregistration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		booking_status: DF.Literal["Applied", "Confirmed", "Under Work", "Updated", "Cancelled", "Rescheduled"]
		customer_name: DF.Link | None
		service_date: DF.Date | None
		service_slot: DF.Link | None
		user_id: DF.Link | None
		vehicle: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "vms vehicle service registration"
