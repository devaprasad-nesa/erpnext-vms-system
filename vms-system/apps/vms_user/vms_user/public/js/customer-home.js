/* ================================================================
   VMS CUSTOMER HOME
   ---------------------------------------------------------------
   Handles:
   1. Loading customer's vehicles
   2. Loading available service slots
   3. Creating service bookings
   4. Loading customer's service bookings
   5. Loading inspection reports
   6. Loading audited invoices
   7. Updating customer profile
================================================================ */


/* ================================================================
   DOCUMENT READY
================================================================ */

frappe.ready(function () {

    /* ------------------------------------------------------------
       Set minimum service date to today
    ------------------------------------------------------------ */

    const dateInput = document.getElementById("booking-date");

    if (dateInput) {

        const today =
            new Date().toISOString().split("T")[0];

        dateInput.min = today;

    }


    /* ------------------------------------------------------------
       Load initial dashboard data
    ------------------------------------------------------------ */

    loadVehicles();

    loadBookings();

    loadInspections();

    loadHomeInvoices();


    /* ------------------------------------------------------------
       Service date change
    ------------------------------------------------------------ */

    if (dateInput) {

        dateInput.addEventListener("change", function () {

            const selectedDate = this.value;

            const slotSelect =
                document.getElementById("booking-slot");


            /* No date */

            if (!selectedDate) {

                slotSelect.innerHTML =
                    `<option value="">
                        Select a date first
                    </option>`;

                slotSelect.disabled = true;

                return;
            }


            /* ----------------------------------------------------
               Check Monday
            ---------------------------------------------------- */

            const dateObj =
                new Date(selectedDate + "T00:00:00");

            if (dateObj.getDay() === 1) {

                frappe.msgprint(
                    __("The workshop is closed on Mondays. Please choose another date.")
                );

                this.value = "";

                slotSelect.innerHTML =
                    `<option value="">
                        Closed on Mondays
                    </option>`;

                slotSelect.disabled = true;

                return;
            }


            /* ----------------------------------------------------
               Load available slots
            ---------------------------------------------------- */

            slotSelect.innerHTML =
                `<option value="">
                    Loading available slots...
                </option>`;

            slotSelect.disabled = true;


            frappe.call({

                method:
                    "vms_vehicle.service_registration.get_available_service_slots",

                args: {
                    service_date: selectedDate
                },

                callback: function (r) {

                    const slots =
                        r.message || [];


                    /* No slots */

                    if (!slots.length) {

                        slotSelect.innerHTML =
                            `<option value="">
                                No slots available on this date
                            </option>`;

                        slotSelect.disabled = true;

                        return;
                    }


                    /* Build slot options */

                    slotSelect.innerHTML =
                        `<option value="">
                            -- Select Time Slot --
                        </option>` +
                        slots.map(function (slot) {

                            return `
                                <option value="${escapeHTML(slot.name)}">
                                    ${escapeHTML(slot.label)}
                                </option>
                            `;

                        }).join("");


                    slotSelect.disabled = false;

                },

                error: function () {

                    slotSelect.innerHTML =
                        `<option value="">
                            Unable to load slots
                        </option>`;

                    slotSelect.disabled = true;

                }

            });

        });

    }


    /* ============================================================
       SERVICE BOOKING FORM
    ============================================================ */

    const bookingForm =
        document.getElementById("service-booking-form");


    if (bookingForm) {

        bookingForm.addEventListener("submit", function (e) {

            e.preventDefault();


            const vehicle =
                document.getElementById("booking-vehicle").value;

            const date =
                document.getElementById("booking-date").value;

            const slot =
                document.getElementById("booking-slot").value;

            const btn =
                document.getElementById("submit-booking-btn");

            const msg =
                document.getElementById("booking-message");


            /* ----------------------------------------------------
               Validate fields
            ---------------------------------------------------- */

            if (!vehicle || !date || !slot) {

                frappe.msgprint(
                    __("Please fill in all booking fields.")
                );

                return;
            }


            /* ----------------------------------------------------
               Disable button while booking
            ---------------------------------------------------- */

            btn.disabled = true;

            btn.textContent =
                __("Booking slot...");

            msg.innerHTML = "";


            /* ----------------------------------------------------
               Create booking
            ---------------------------------------------------- */

            frappe.call({

                method:
                    "vms_vehicle.service_registration.register_vehicle_service",

                args: {

                    vehicle_registration:
                        vehicle,

                    service_date:
                        date,

                    service_slot:
                        slot
                },

                freeze: true,

                freeze_message:
                    __("Securing service slot..."),


                callback: function (r) {

                    btn.disabled = false;

                    btn.textContent =
                        __("Confirm Service Booking");


                    if (
                        r.message &&
                        r.message.success
                    ) {

                        msg.innerHTML = `
                            <div class="booking-success">
                                ${escapeHTML(r.message.message)}
                                <br>
                                Booking ID:
                                <strong>
                                    ${escapeHTML(r.message.name)}
                                </strong>
                            </div>
                        `;


                        bookingForm.reset();


                        document
                            .getElementById("booking-slot")
                            .innerHTML =
                            `<option value="">
                                Select a date first
                            </option>`;


                        document
                            .getElementById("booking-slot")
                            .disabled = true;


                        loadBookings();

                    }

                },


                error: function () {

                    btn.disabled = false;

                    btn.textContent =
                        __("Confirm Service Booking");

                }

            });

        });

    }


    /* ============================================================
       EDIT PROFILE BUTTON
    ============================================================ */

    const editProfileBtn =
        document.getElementById("edit-profile-btn");


    if (editProfileBtn) {

        editProfileBtn.addEventListener(
            "click",
            function () {

                $("#editProfileModal").modal("show");

            }
        );

    }


    /* ============================================================
       EDIT PROFILE FORM
    ============================================================ */

    const editProfileForm =
        document.getElementById("edit-profile-form");


    if (editProfileForm) {

        editProfileForm.addEventListener(
            "submit",
            function (e) {

                e.preventDefault();


                const name =
                    document
                        .getElementById("modal-name")
                        .value
                        .trim();


                const phone =
                    document
                        .getElementById("modal-phone")
                        .value
                        .trim();


                const address =
                    document
                        .getElementById("modal-address")
                        .value
                        .trim();


                frappe.call({

                    method:
                        "vms_user.api.update_my_profile",

                    args: {

                        customer_name:
                            name,

                        phone:
                            phone,

                        address:
                            address
                    },

                    freeze: true,


                    callback: function () {

                        $("#editProfileModal")
                            .modal("hide");


                        frappe.msgprint(
                            __("Profile updated successfully.")
                        );


                        document
                            .getElementById(
                                "display-customer-name"
                            )
                            .textContent =
                            name;


                        document
                            .getElementById(
                                "display-customer-phone"
                            )
                            .textContent =
                            phone ||
                            "Not provided";


                        document
                            .getElementById(
                                "display-customer-address"
                            )
                            .textContent =
                            address ||
                            "Not provided";

                    }

                });

            }
        );

    }

});


/* ================================================================
   LOAD CUSTOMER VEHICLES
================================================================ */

function loadVehicles() {

    frappe.call({

        method:
            "vms_vehicle.api.get_my_vehicles",

        callback: function (r) {

            const vehicles =
                r.message || [];


            const select =
                document.getElementById(
                    "booking-vehicle"
                );


            if (!select) {
                return;
            }


            /* ----------------------------------------------------
               No vehicles
            ---------------------------------------------------- */

            if (!vehicles.length) {

                select.innerHTML =
                    `<option value="">
                        No vehicles found (Register one first)
                    </option>`;

                return;
            }


            /* ----------------------------------------------------
               Create vehicle options
            ---------------------------------------------------- */

            select.innerHTML =
                `<option value="">
                    -- Choose a Vehicle --
                </option>` +
                vehicles.map(function (vehicle) {

                    return `
                        <option value="${escapeHTML(vehicle.name)}">
                            ${escapeHTML(vehicle.vehicle_number)}
                            (${escapeHTML(
                        vehicle.vehicle_brand || ""
                    )}
                            ${escapeHTML(
                        vehicle.vehicle_model || ""
                    )})
                        </option>
                    `;

                }).join("");


            /* ----------------------------------------------------
               Pre-select vehicle from URL
               Example:
               /customer-home?vehicle=VEH-00001
            ---------------------------------------------------- */

            const urlParams =
                new URLSearchParams(
                    window.location.search
                );


            const preselect =
                urlParams.get("vehicle");


            if (
                preselect &&
                select.querySelector(
                    `option[value="${CSS.escape(preselect)}"]`
                )
            ) {

                select.value = preselect;

            }

        },

        error: function () {

            const select =
                document.getElementById(
                    "booking-vehicle"
                );


            if (select) {

                select.innerHTML =
                    `<option value="">
                        Unable to load vehicles
                    </option>`;

            }

        }

    });

}


/* ================================================================
   LOAD CUSTOMER SERVICE BOOKINGS
================================================================ */

function loadBookings() {

    frappe.call({

        method:
            "vms_vehicle.service_registration.get_my_service_registrations",

        callback: function (r) {

            const bookings =
                r.message || [];


            const tbody =
                document.getElementById(
                    "bookings-table-body"
                );


            if (!tbody) {
                return;
            }


            /* ----------------------------------------------------
               No bookings
            ---------------------------------------------------- */

            if (!bookings.length) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="4"
                            class="table-empty">

                            No service bookings yet.

                        </td>
                    </tr>
                `;

                return;
            }


            /* ----------------------------------------------------
               Render bookings
            ---------------------------------------------------- */

            tbody.innerHTML =
                bookings.map(function (booking) {

                    let badgeClass =
                        "status-badge status-default";


                    if (
                        booking.booking_status ===
                        "Applied"
                    ) {

                        badgeClass =
                            "status-badge status-applied";

                    }

                    else if (
                        booking.booking_status ===
                        "Under Work"
                    ) {

                        badgeClass =
                            "status-badge status-work";

                    }

                    else if (
                        booking.booking_status ===
                        "Confirmed"
                    ) {

                        badgeClass =
                            "status-badge status-confirmed";

                    }

                    else if (
                        booking.booking_status ===
                        "Cancelled"
                    ) {

                        badgeClass =
                            "status-badge status-cancelled";

                    }

                    else if (
                        booking.booking_status ===
                        "Rescheduled"
                    ) {

                        badgeClass =
                            "status-badge status-rescheduled";

                    }


                    return `
                        <tr>

                            <td class="booking-id">
                                ${escapeHTML(
                        booking.name
                    )}
                            </td>

                            <td>
                                ${escapeHTML(
                        booking.vehicle
                    )}
                            </td>

                            <td>
                                ${escapeHTML(
                        booking.service_date
                    )}
                            </td>

                            <td>

                                <span class="${badgeClass}">
                                    ${escapeHTML(
                        booking.booking_status
                    )}
                                </span>

                            </td>

                        </tr>
                    `;

                }).join("");

        },

        error: function () {

            const tbody =
                document.getElementById(
                    "bookings-table-body"
                );


            if (tbody) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="4"
                            class="table-empty">

                            Unable to load bookings.

                        </td>
                    </tr>
                `;

            }

        }

    });

}


/* ================================================================
   LOAD CUSTOMER INSPECTION REPORTS
================================================================ */

function loadInspections() {

    frappe.call({

        method:
            "vms_inspection.api.get_my_vehicle_inspections",

        callback: function (r) {

            const inspections =
                r.message || [];


            const tbody =
                document.getElementById(
                    "inspections-table-body"
                );


            if (!tbody) {
                return;
            }


            /* ----------------------------------------------------
               No inspection reports
            ---------------------------------------------------- */

            if (!inspections.length) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="5"
                            class="table-empty">

                            No inspection records found.

                        </td>
                    </tr>
                `;

                return;
            }


            /* ----------------------------------------------------
               Render inspection reports
            ---------------------------------------------------- */

            tbody.innerHTML =
                inspections.map(function (inspection) {

                    const statusBadge =
                        inspection.inspected

                            ? `
                                <span class="
                                    status-badge
                                    status-confirmed
                                ">
                                    Completed
                                </span>
                              `

                            : `
                                <span class="
                                    status-badge
                                    status-applied
                                ">
                                    Pending
                                </span>
                              `;


                    return `
                        <tr>

                            <td class="booking-id">
                                ${escapeHTML(
                        inspection.name
                    )}
                            </td>

                            <td>
                                ${escapeHTML(
                        inspection.vehicle_number
                    )}
                            </td>

                            <td>
                                ${escapeHTML(
                        inspection.inspection_date
                    )}
                            </td>

                            <td>
                                ${escapeHTML(
                        inspection.issue ||
                        "General Service"
                    )}
                            </td>

                            <td>
                                ${statusBadge}
                            </td>

                        </tr>
                    `;

                }).join("");

        },

        error: function () {

            const tbody =
                document.getElementById(
                    "inspections-table-body"
                );


            if (tbody) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="5"
                            class="table-empty">

                            Unable to load inspection reports.

                        </td>
                    </tr>
                `;

            }

        }

    });

}


/* ================================================================
   LOAD AUDITED INVOICES
================================================================ */

function loadHomeInvoices() {

    frappe.call({

        method:
            "vms_account.api.get_my_invoices",

        args: {

            only_audited: 1

        },


        callback: function (r) {

            const invoices =
                r.message || [];


            const tbody =
                document.getElementById(
                    "home-invoices-table-body"
                );


            if (!tbody) {
                return;
            }


            /* ----------------------------------------------------
               No invoices
            ---------------------------------------------------- */

            if (!invoices.length) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="5"
                            class="table-empty">

                            No paid invoices found yet.
                            Once accounts audits your bill,
                            it will appear here.

                        </td>
                    </tr>
                `;

                return;
            }


            /* ----------------------------------------------------
               Show latest five invoices
            ---------------------------------------------------- */

            tbody.innerHTML =
                invoices
                    .slice(0, 5)
                    .map(function (invoice) {


                        let totalFormatted =
                            "₹0.00";


                        if (
                            invoice.total_bill !==
                            null &&
                            invoice.total_bill !==
                            undefined
                        ) {

                            totalFormatted =
                                Number(
                                    invoice.total_bill
                                ).toLocaleString(
                                    "en-IN",
                                    {
                                        style:
                                            "currency",

                                        currency:
                                            "INR"
                                    }
                                );

                        }


                        return `
                            <tr>

                                <td class="booking-id">

                                    <a
                                        href="/my-invoices"
                                        class="invoice-link">

                                        ${escapeHTML(
                            invoice.name
                        )}

                                    </a>

                                </td>


                                <td>

                                    <span class="vehicle-badge">

                                        ${escapeHTML(
                            invoice.vehicle_number ||
                            "-"
                        )}

                                    </span>

                                </td>


                                <td>
                                    ${escapeHTML(
                            invoice.invoice_date ||
                            "-"
                        )}
                                </td>


                                <td>

                                    <strong class="invoice-total">

                                        ${totalFormatted}

                                    </strong>

                                </td>


                                <td>

                                    <span class="
                                        status-badge
                                        status-confirmed
                                    ">

                                        &#x2714;
                                        Paid

                                    </span>

                                </td>

                            </tr>
                        `;

                    }).join("");

        },


        error: function () {

            const tbody =
                document.getElementById(
                    "home-invoices-table-body"
                );


            if (tbody) {

                tbody.innerHTML = `
                    <tr>
                        <td
                            colspan="5"
                            class="table-empty">

                            Invoice service unavailable.

                        </td>
                    </tr>
                `;

            }

        }

    });

}


/* ================================================================
   LOGOUT FUNCTION
================================================================ */

function logoutCustomer() {
    if (window.frappe?.call) {
        frappe.call({
            method: "logout",
            freeze: true,
            freeze_message: "Logging out...",
            callback: function () {
                window.location.replace("/login");
            },
            error: function () {
                window.location.replace("/login");
            }
        });
    } else {
        fetch("/api/method/logout", {
            method: "POST",
            credentials: "same-origin"
        }).finally(function () {
            window.location.replace("/login");
        });
    }
}


/* ================================================================
   HTML ESCAPE FUNCTION
   ---------------------------------------------------------------
   Prevents API values from being directly interpreted as HTML.
================================================================ */

function escapeHTML(value) {

    return String(value || "")

        .replace(/&/g, "&amp;")

        .replace(/</g, "&lt;")

        .replace(/>/g, "&gt;")

        .replace(/"/g, "&quot;")

        .replace(/'/g, "&#039;");
}