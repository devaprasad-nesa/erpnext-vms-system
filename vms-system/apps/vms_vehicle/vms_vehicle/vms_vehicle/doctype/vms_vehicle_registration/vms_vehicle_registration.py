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
        fuel_type: DF.Link | None
        notes: DF.Data | None
        owner_name: DF.Link | None
        owner_user: DF.Link | None
        registration_date: DF.Date | None
        vehicle_brand: DF.Link | None
        vehicle_color: DF.Data | None
        vehicle_model: DF.Link | None
        vehicle_number: DF.Data | None
    # end: auto-generated types

    def before_insert(self):
        user = getattr(frappe.session, "user", None) or "Guest"
        if user != "Administrator" and not self._is_manager_or_staff(user):
            self.owner_user = user
            self.owner_name = user

    def validate(self):
        # Support vehicle_fuel_type alias if set
        if not self.fuel_type and getattr(self, "vehicle_fuel_type", None):
            self.fuel_type = getattr(self, "vehicle_fuel_type")

        self.normalize_vehicle_number()
        self.validate_owner()
        self.validate_vehicle_number()
        self.validate_brand_model_fuel()

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

    def validate_brand_model_fuel(self):
        """
        Validates the strict relationship between Brand, Model, and Fuel Type:
        1. Brand must exist in vms brand (or Vehicle Brand fallback).
        2. Model must exist in child table vms model for that Brand.
        3. Fuel Type must be valid for the Model in vms model.
        """
        from vms_vehicle.api import validate_vehicle_relationships
        validate_vehicle_relationships(self.vehicle_brand, self.vehicle_model, self.fuel_type)

    _DOCTYPE_NAME = DOCTYPE_NAME