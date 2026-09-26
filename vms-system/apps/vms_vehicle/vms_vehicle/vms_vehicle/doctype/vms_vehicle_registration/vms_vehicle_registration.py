# Copyright (c) 2026, vms developer nesa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

DOCTYPE_NAME = "vms vehicle registration"


class vmsvehicleregistration(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chassis_number: DF.Data | None
        engine_number: DF.Data | None
        fuel_type: DF.Data | None
        notes: DF.Data | None
        owner_name: DF.Link | None
        owner_user: DF.Link | None
        registration_date: DF.Date | None
        vehicle_brand: DF.Data | None
        vehicle_color: DF.Data | None
        vehicle_model: DF.Data | None
        vehicle_number: DF.Data | None
    # end: auto-generated types

    def before_insert(self):
        user = getattr(frappe.session, "user", None) or "Guest"
        if user != "Administrator" and not self._is_manager_or_staff(user):
            self.owner_user = user
            self.owner_name = user

    def validate(self):
        self.normalize_vehicle_number()
        self.validate_owner()
        self.validate_vehicle_number()

    def _is_manager_or_staff(self, user: str) -> bool:
        if not user or user == "Guest":
            return False
        if user == "Administrator":
            return True
        roles = {r.strip().lower() for r in frappe.get_roles(user)}
        return bool(roles.intersection({"system manager", "administrator", "vms manager", "vms technician"}))

    def validate_owner(self):
        user = getattr(frappe.session, "user", None) or "Guest"

        if user == "Administrator" or self._is_manager_or_staff(user):
            # Staff can register vehicles on behalf of customers
            if not self.owner_user and self.owner_name:
                self.owner_user = self.owner_name
            elif not self.owner_name and self.owner_user:
                self.owner_name = self.owner_user
            return

        # For customers, strictly bind to the authenticated session
        if self.owner_user and self.owner_user != user:
            frappe.throw(
                _("You cannot register or modify another customer's vehicle."),
                frappe.PermissionError,
            )

        self.owner_user = user
        self.owner_name = user

    def normalize_vehicle_number(self):
        if self.vehicle_number:
            self.vehicle_number = str(self.vehicle_number).strip().upper()

    def validate_vehicle_number(self):
        if not self.vehicle_number:
            frappe.throw(_("Vehicle Number is required."))

        existing = frappe.db.exists(
            DOCTYPE_NAME,
            {
                "vehicle_number": self.vehicle_number,
                "name": ["!=", self.name or ""],
            },
        )

        if existing:
            frappe.throw(
                _("A vehicle with registration number '{0}' already exists.").format(self.vehicle_number),
                frappe.DuplicateEntryError,
            )

    _DOCTYPE_NAME = DOCTYPE_NAME