# Copyright (c) 2026, vmsdeveloper and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class vmscustomerprofile(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.Text | None
		customer_email: DF.Data | None
		customer_name: DF.Data | None
		customer_phone: DF.Phone | None
		user_name: DF.Link | None
	# end: auto-generated types

	def validate(self):
		user = getattr(frappe.session, "user", None) or "Guest"

		if user == "Administrator":
			return

		roles = {r.strip().lower() for r in frappe.get_roles(user)}
		is_staff = bool("system manager" in roles or "vms manager" in roles or "administrator" in roles)

		if not is_staff and "vms customer" not in roles and "customer" not in roles:
			frappe.throw(
				_("You are not authorized to manage a customer profile."),
				frappe.PermissionError,
			)

		# Auto-assign username if new
		if self.is_new() and not self.user_name:
			self.user_name = user

		if not is_staff and self.user_name and self.user_name != user:
			frappe.throw(
				_("You can only manage your own customer profile."),
				frappe.PermissionError,
			)

		# Populate from User doctype if email/name are missing
		if self.user_name and (not self.customer_email or not self.customer_name):
			user_data = frappe.db.get_value(
				"User",
				self.user_name,
				["email", "full_name", "first_name", "mobile_no", "phone"],
				as_dict=True,
			)
			if user_data:
				if not self.customer_email:
					self.customer_email = user_data.get("email")
				if not self.customer_name:
					self.customer_name = user_data.get("full_name") or user_data.get("first_name") or self.user_name
				if not self.customer_phone:
					self.customer_phone = user_data.get("mobile_no") or user_data.get("phone")

	_DOCTYPE_NAME = "vms customer profile"
