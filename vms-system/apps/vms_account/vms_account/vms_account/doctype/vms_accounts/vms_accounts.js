// Copyright (c) 2026, vms developer and contributors
// For license information, please see license.txt

// frappe.ui.form.on("vms accounts", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("vms accounts", {
    refresh(frm) {
        const roles = frappe.user_roles || [];

        const is_manager =
            roles.includes("vms manager") ||
            roles.includes("System Manager");

        const is_accountant =
            roles.includes("vms accountant");

        if (frm.doc.audited) {
            frm.set_read_only();
        }

        if (
            !frm.is_new() &&
            (is_accountant || is_manager) &&
            !frm.doc.audited
        ) {
            frm.add_custom_button(
                __("Share Invoice"),
                () => {
                    frappe.call({
                        method:
                            "vms_account.api.share_invoice",
                        args: {
                            invoice_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message:
                            __("Sharing invoice..."),
                        callback(r) {
                            if (!r.exc) {
                                frappe.msgprint(
                                    r.message.message
                                );
                            }
                        }
                    });
                }
            );
        }

        if (
            !frm.is_new() &&
            is_manager &&
            !frm.doc.audited
        ) {
            frm.add_custom_button(
                __("Audit Invoice"),
                () => {
                    frappe.confirm(
                        __("Mark this invoice as audited?"),
                        () => {
                            frappe.call({
                                method:
                                    "vms_account.api.audit_invoice",
                                args: {
                                    invoice_name: frm.doc.name
                                },
                                freeze: true,
                                callback(r) {
                                    if (!r.exc) {
                                        frappe.msgprint(
                                            __("Invoice audited.")
                                        );

                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }
            );
        }
    },

    vehicle_inspection(frm) {
        if (!frm.doc.vehicle_inspection) {
            return;
        }

        frappe.db.get_doc(
            "vms vehicle inspection",
            frm.doc.vehicle_inspection
        ).then(inspection => {
            frm.set_value(
                "customer_name",
                inspection.customer_name
            );

            frm.set_value(
                "vehicle_number",
                inspection.vehicle_number
            );

            frm.set_value(
                "vehicle_spare_parts",
                inspection.spare_parts
            );
        });
    }
});