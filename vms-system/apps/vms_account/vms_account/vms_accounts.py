
# vms_account/vms_account/doctype/vms_accounts/vms_accounts.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


HOURLY_LABOUR_RATE = 500.0


class vmsaccounts(Document):

    def validate(self):
        self.check_audit_permission()
        self.populate_from_inspection()
        self.validate_invoice_links()
        self.calculate_total_bill()

    def check_audit_permission(self):
        """
        Only the manager or System Manager can audit an invoice.
        Once audited, the invoice becomes locked.
        """

        if self.is_new():
            if self.get("audited"):
                frappe.throw(
                    _("A new invoice cannot be created as audited.")
                )
            return

        old_audited = frappe.db.get_value(
            self.doctype,
            self.name,
            "audited"
        )

        if old_audited and not frappe.has_permission(
            self.doctype,
            "write",
            self.name
        ):
            frappe.throw(
                _("You cannot modify an audited invoice.")
            )

        if self.get("audited") and not (
            "System Manager" in frappe.get_roles()
            or "vms manager" in frappe.get_roles()
        ):
            frappe.throw(
                _("Only a manager can audit an invoice.")
            )

    def populate_from_inspection(self):
        if not self.vehicle_inspection:
            return

        inspection = frappe.db.get_value(
            "vms vehicle inspection",
            self.vehicle_inspection,
            [
                "vehicle_number",
                "customer_name",
                "spare_parts",
                "spare_part_quantity",
                "labour_hour",
            ],
            as_dict=True,
        )

        if not inspection:
            frappe.throw(
                _("Selected inspection does not exist.")
            )

        if not self.vehicle_number:
            self.vehicle_number = inspection.vehicle_number

        if not self.customer_name:
            self.customer_name = inspection.customer_name

        if (
            not self.vehicle_spare_parts
            and inspection.spare_parts
        ):
            self.vehicle_spare_parts = inspection.spare_parts

    def validate_invoice_links(self):
        if not self.customer_name:
            frappe.throw(_("Customer is required."))

        if not self.vehicle_number:
            frappe.throw(_("Vehicle is required."))

        if not self.vehicle_inspection:
            frappe.throw(_("Inspection is required."))

        inspection = frappe.db.get_value(
            "vms vehicle inspection",
            self.vehicle_inspection,
            [
                "vehicle_number",
                "customer_name",
            ],
            as_dict=True,
        )

        if not inspection:
            frappe.throw(_("Inspection not found."))

        if inspection.vehicle_number != self.vehicle_number:
            frappe.throw(
                _("Inspection does not belong to this vehicle.")
            )

        if inspection.customer_name != self.customer_name:
            frappe.throw(
                _("Inspection does not belong to this customer.")
            )

        if not self.invoice_date:
            self.invoice_date = today()

        if getdate(self.invoice_date) > getdate(today()):
            frappe.throw(
                _("Invoice date cannot be in the future.")
            )

    def calculate_total_bill(self):
        """
        Uses the existing spare_parts_amount and total_bill
        fields. No additional DocType fields are required.
        """

        parts_cost = 0.0
        labour_cost = 0.0

        if self.vehicle_spare_parts:
            part = frappe.db.get_value(
                "vms spare parts",
                self.vehicle_spare_parts,
                ["cost"],
                as_dict=True,
            )

            if not part:
                frappe.throw(
                    _("Selected spare part was not found.")
                )

            quantity = 1.0

            if self.vehicle_inspection:
                inspection_quantity = frappe.db.get_value(
                    "vms vehicle inspection",
                    self.vehicle_inspection,
                    "spare_part_quantity",
                )

                if inspection_quantity:
                    quantity = flt(inspection_quantity)

            if quantity < 0:
                frappe.throw(
                    _("Spare part quantity cannot be negative.")
                )

            parts_cost = flt(part.cost) * quantity

        if self.vehicle_inspection:
            hours = flt(
                frappe.db.get_value(
                    "vms vehicle inspection",
                    self.vehicle_inspection,
                    "labour_hour",
                ) or 0
            )

            if hours < 0:
                frappe.throw(
                    _("Labour hours cannot be negative.")
                )

            labour_cost = hours * HOURLY_LABOUR_RATE

        self.spare_parts_amount = round(parts_cost, 2)

        self.total_bill = round(
            parts_cost + labour_cost,
            2
        )

    def on_update(self):
        """
        Invoice sharing is performed by an explicit API call,
        not automatically on every save.
        """
        pass