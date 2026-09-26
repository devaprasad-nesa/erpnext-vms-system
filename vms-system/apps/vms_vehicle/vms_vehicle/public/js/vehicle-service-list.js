frappe.ready(function () {
    "use strict";


    /* ============================================================
       CONFIGURATION
       ============================================================ */

    const ROOT = "#vms-technician-dashboard";

    const PAGE_SIZE = 10;

    const root = document.querySelector(ROOT);


    // Stop execution if the page container does not exist.
    if (!root) {
        return;
    }


    /* ============================================================
       STATE
       ============================================================ */

    let allBookings = [];

    let filteredBookings = [];

    let currentPage = 1;

    let currentBooking = null;

    let formMeta = { slots: [], spare_parts: [], mechanics: [] };

    let metaLoaded = false;


    /* ============================================================
       DOM HELPER
       ============================================================ */

    const $ = function (selector) {
        return root.querySelector(selector);
    };


    const tableBody = $("#booking-table-body");

    const message = $("#booking-message");


    /* ============================================================
       ESCAPE HTML
       ------------------------------------------------------------
       Prevents user/database values from being inserted as raw
       HTML into the page.
       ============================================================ */

    function escapeHTML(value) {

        return String(value ?? "").replace(
            /[&<>"']/g,
            function (char) {

                return {
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                    "'": "&#39;"
                }[char];

            }
        );
    }


    /* ============================================================
       DATE FORMATTER
       ------------------------------------------------------------
       Converts:
       
       YYYY-MM-DD

       into:

       DD-MM-YYYY

       without timezone conversion.
       ============================================================ */

    function formatDate(value) {

        if (!value) {
            return "—";
        }


        const parts = String(value).split("-");


        if (parts.length !== 3) {
            return escapeHTML(value);
        }


        return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }


    /* ============================================================
       STATUS CSS CLASS
       ============================================================ */

    function statusClass(status) {

        const classes = {

            Applied: "status-applied",

            Confirmed: "status-confirmed",

            "Under Work": "status-under-work",

            Updated: "status-updated",

            Cancelled: "status-cancelled",

            Rescheduled: "status-rescheduled"

        };


        return classes[status] || "";
    }


    /* ============================================================
       RENDER STATISTICS
       ============================================================ */

    function renderStats() {

        // Total bookings
        $("#total-count").textContent =
            allBookings.length;


        // Applied bookings
        $("#applied-count").textContent =
            allBookings.filter(function (booking) {

                return booking.booking_status === "Applied";

            }).length;


        // Confirmed and Under Work
        $("#confirmed-count").textContent =
            allBookings.filter(function (booking) {

                return (
                    booking.booking_status === "Confirmed" ||
                    booking.booking_status === "Under Work"
                );

            }).length;


        // Rescheduled
        $("#rescheduled-count").textContent =
            allBookings.filter(function (booking) {

                return booking.booking_status === "Rescheduled";

            }).length;
    }


    /* ============================================================
       RENDER TABLE
       ============================================================ */

    function renderTable() {

        const total = filteredBookings.length;


        const totalPages =
            Math.max(
                1,
                Math.ceil(total / PAGE_SIZE)
            );


        // Prevent current page from exceeding available pages.
        currentPage =
            Math.min(
                currentPage,
                totalPages
            );


        const start =
            (currentPage - 1) * PAGE_SIZE;


        const pageItems =
            filteredBookings.slice(
                start,
                start + PAGE_SIZE
            );


        /* --------------------------------------------------------
           Booking count
           -------------------------------------------------------- */

        $("#booking-count").textContent =
            `${total} booking${total === 1 ? "" : "s"}`;


        /* --------------------------------------------------------
           Page number
           -------------------------------------------------------- */

        $("#page-number").textContent =
            `Page ${currentPage} of ${totalPages}`;


        /* --------------------------------------------------------
           Pagination button states
           -------------------------------------------------------- */

        $("#previous-page").disabled =
            currentPage <= 1;


        $("#next-page").disabled =
            currentPage >= totalPages;


        /* --------------------------------------------------------
           Empty result
           -------------------------------------------------------- */

        if (!pageItems.length) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7">
                        No service bookings found.
                    </td>
                </tr>
            `;

            return;
        }


        /* --------------------------------------------------------
           Generate table rows
           -------------------------------------------------------- */

        tableBody.innerHTML = pageItems.map(function (booking) {

            return `

                <tr>

                    <td>
                        <strong>
                            ${escapeHTML(booking.name)}
                        </strong>
                    </td>


                    <td>
                        ${escapeHTML(
                booking.customer_name || "—"
            )}
                    </td>


                    <td>
                        ${escapeHTML(
                booking.vehicle || "—"
            )}
                    </td>


                    <td>
                        ${formatDate(
                booking.service_date
            )}
                    </td>


                    <td>
                        ${escapeHTML(
                booking.service_slot || "—"
            )}
                    </td>


                    <td>

                        <span
                            class="vms-status ${statusClass(
                booking.booking_status
            )}"
                        >
                            ${escapeHTML(
                booking.booking_status || "—"
            )}
                        </span>

                    </td>


                    <td>

                        <button
                            type="button"
                            class="vms-view-btn"
                            data-booking="${escapeHTML(
                booking.name
            )}"
                        >
                            View
                        </button>

                    </td>

                </tr>

            `;

        }).join("");
    }


    /* ============================================================
       APPLY SEARCH AND STATUS FILTER
       ============================================================ */

    function applyFilters() {

        const searchText =
            $("#booking-search")
                .value
                .trim()
                .toLowerCase();


        const selectedStatus =
            $("#status-filter").value;


        filteredBookings =
            allBookings.filter(function (booking) {


                /* ------------------------------------------------
                   Fields included in search
                   ------------------------------------------------ */

                const searchableText = [

                    booking.name,

                    booking.customer_name,

                    booking.vehicle,

                    booking.user_id,

                    booking.service_slot

                ]
                    .join(" ")
                    .toLowerCase();


                /* ------------------------------------------------
                   Search condition
                   ------------------------------------------------ */

                const matchesSearch =
                    !searchText ||
                    searchableText.includes(searchText);


                /* ------------------------------------------------
                   Status condition
                   ------------------------------------------------ */

                const matchesStatus =
                    !selectedStatus ||
                    booking.booking_status === selectedStatus;


                return (
                    matchesSearch &&
                    matchesStatus
                );

            });


        // Return to first page after filtering.
        currentPage = 1;


        renderTable();
    }


    /* ============================================================
       FORM METADATA LOADER (SLOTS, SPARE PARTS, MECHANICS)
       ============================================================ */

    async function loadFormMeta() {

        if (metaLoaded) {
            return;
        }

        try {

            const resp = await frappe.call({
                method: "vms_vehicle.api.get_technician_inspection_form_meta"
            });

            if (resp && resp.message) {
                formMeta = resp.message;
                metaLoaded = true;
                populateMetaDropdowns();
            }

        } catch (err) {
            console.warn("Could not load form metadata:", err);
        }
    }


    function populateMetaDropdowns() {

        // Service slots dropdown
        const slotSelect = $("#edit-booking-slot");
        if (slotSelect && formMeta.slots && formMeta.slots.length) {
            const currentVal = slotSelect.value;
            slotSelect.innerHTML = `
                <option value="">Select slot</option>
                ${formMeta.slots.map(function (s) {
                    return `
                        <option value="${escapeHTML(s.name)}">
                            ${escapeHTML(s.slot_name || s.name)} (${escapeHTML(s.start_time || "")} - ${escapeHTML(s.end_time || "")})
                        </option>
                    `;
                }).join("")}
            `;
            if (currentVal) {
                slotSelect.value = currentVal;
            }
        }

        // Spare parts dropdown
        const spareSelect = $("#insp-spare-parts");
        if (spareSelect && formMeta.spare_parts) {
            const currentVal = spareSelect.value;
            spareSelect.innerHTML = `
                <option value="">None / Select spare part</option>
                ${formMeta.spare_parts.map(function (p) {
                    return `
                        <option value="${escapeHTML(p.name)}">
                            ${escapeHTML(p.part_name || p.name)} (Stock: ${escapeHTML(p.quantity || "1")})
                        </option>
                    `;
                }).join("")}
            `;
            if (currentVal) {
                spareSelect.value = currentVal;
            }
        }

        // Mechanics dropdown
        const mechSelect = $("#insp-mechanic");
        if (mechSelect && formMeta.mechanics) {
            const currentVal = mechSelect.value;
            mechSelect.innerHTML = `
                <option value="">Select mechanic</option>
                ${formMeta.mechanics.map(function (m) {
                    return `
                        <option value="${escapeHTML(m.name)}">
                            ${escapeHTML(m.full_name ? `${m.full_name} (${m.name})` : m.name)}
                        </option>
                    `;
                }).join("")}
            `;
            if (currentVal) {
                mechSelect.value = currentVal;
            }
        }
    }


    /* ============================================================
       SHOW BOOKING DETAILS
       ============================================================ */

    function showDetails(booking) {

        currentBooking = booking;

        const vehicleDisplay = booking.vehicle_number
            ? `${booking.vehicle_number} (${booking.vehicle})`
            : booking.vehicle;

        const details = [

            [
                "Booking ID",
                booking.name
            ],

            [
                "Customer",
                booking.customer_name
            ],

            [
                "User ID",
                booking.user_id
            ],

            [
                "Vehicle",
                vehicleDisplay
            ],

            [
                "Service Date",
                formatDate(
                    booking.service_date
                )
            ],

            [
                "Service Slot",
                booking.service_slot
            ],

            [
                "Booking Status",
                booking.booking_status
            ]

        ];


        /* --------------------------------------------------------
           Generate details grid
           -------------------------------------------------------- */

        $("#booking-details-content").innerHTML = `

            <div class="vms-detail-grid">

                ${details.map(function ([label, value]) {

            return `

                        <div class="vms-detail-item">

                            <span>
                                ${escapeHTML(label)}
                            </span>

                            <strong>
                                ${escapeHTML(
                value || "—"
            )}
                            </strong>

                        </div>

                    `;

        }).join("")}

            </div>

        `;


        /* --------------------------------------------------------
           Configure Desk button link
           -------------------------------------------------------- */

        const deskBtn = $("#btn-desk-booking");
        if (deskBtn) {
            deskBtn.href = `/app/vms-vehicle-service-registration/${encodeURIComponent(booking.name)}`;
        }


        /* --------------------------------------------------------
           Hide subpanels & clear messages
           -------------------------------------------------------- */

        const editPanel = $("#edit-booking-panel");
        if (editPanel) {
            editPanel.hidden = true;
        }

        const inspPanel = $("#create-inspection-panel");
        if (inspPanel) {
            inspPanel.hidden = true;
        }

        const editMsg = $("#edit-booking-msg");
        if (editMsg) {
            editMsg.textContent = "";
        }

        const inspMsg = $("#create-inspection-msg");
        if (inspMsg) {
            inspMsg.textContent = "";
        }


        /* --------------------------------------------------------
           Display details panel
           -------------------------------------------------------- */

        $("#booking-details").hidden = false;


        /* --------------------------------------------------------
           Preload dropdown metadata
           -------------------------------------------------------- */

        loadFormMeta();


        /* --------------------------------------------------------
           Scroll to details
           -------------------------------------------------------- */

        $("#booking-details").scrollIntoView({

            behavior: "smooth",

            block: "start"

        });
    }



    /* ============================================================
       LOAD BOOKINGS FROM FRAPPE
       ============================================================ */

    async function loadBookings() {


        message.textContent =
            "Loading service bookings...";


        tableBody.innerHTML = `

            <tr>

                <td colspan="7">

                    Loading service bookings...

                </td>

            </tr>

        `;


        $("#refresh-bookings").disabled = true;


        try {


            /* ----------------------------------------------------
               Call Frappe backend method
               ---------------------------------------------------- */

            const response =
                await frappe.call({

                    method:
                        "vms_vehicle.api.get_technician_service_bookings"

                });


            /* ----------------------------------------------------
               Store returned data
               ---------------------------------------------------- */

            allBookings =
                response.message || [];


            /* ----------------------------------------------------
               Render dashboard
               ---------------------------------------------------- */

            renderStats();

            applyFilters();


            /* ----------------------------------------------------
               Clear loading message
               ---------------------------------------------------- */

            message.textContent = "";


        } catch (error) {


            /* ----------------------------------------------------
               Log error
               ---------------------------------------------------- */

            console.error(
                "Unable to load service bookings:",
                error
            );


            /* ----------------------------------------------------
               Display user-friendly message
               ---------------------------------------------------- */

            message.textContent =
                "Unable to load bookings. Check your login and permissions.";


            tableBody.innerHTML = `

                <tr>

                    <td colspan="7">

                        Failed to load service bookings.

                    </td>

                </tr>

            `;


        } finally {


            $("#refresh-bookings").disabled = false;

        }

    }


    /* ============================================================
       REFRESH BUTTON
       ============================================================ */

    $("#refresh-bookings").addEventListener(
        "click",
        loadBookings
    );


    /* ============================================================
       SEARCH
       ============================================================ */

    $("#booking-search").addEventListener(
        "input",
        applyFilters
    );


    /* ============================================================
       STATUS FILTER
       ============================================================ */

    $("#status-filter").addEventListener(
        "change",
        applyFilters
    );


    /* ============================================================
       PREVIOUS PAGE
       ============================================================ */

    $("#previous-page").addEventListener(
        "click",
        function () {

            if (currentPage > 1) {

                currentPage--;

                renderTable();

            }

        }
    );


    /* ============================================================
       NEXT PAGE
       ============================================================ */

    $("#next-page").addEventListener(
        "click",
        function () {


            const totalPages =
                Math.max(
                    1,
                    Math.ceil(
                        filteredBookings.length /
                        PAGE_SIZE
                    )
                );


            if (currentPage < totalPages) {

                currentPage++;

                renderTable();

            }

        }
    );


    /* ============================================================
       VIEW BOOKING
       ============================================================ */

    tableBody.addEventListener(
        "click",
        function (event) {


            const button =
                event.target.closest(
                    "[data-booking]"
                );


            if (!button) {
                return;
            }


            const booking =
                allBookings.find(function (item) {

                    return (
                        item.name ===
                        button.dataset.booking
                    );

                });


            if (booking) {

                showDetails(booking);

            }

        }
    );


    /* ============================================================
       CLOSE DETAILS
       ============================================================ */

    $("#close-details").addEventListener(
        "click",
        function () {

            $("#booking-details").hidden = true;
            if ($("#edit-booking-panel")) $("#edit-booking-panel").hidden = true;
            if ($("#create-inspection-panel")) $("#create-inspection-panel").hidden = true;
            currentBooking = null;

        }
    );


    /* ============================================================
       EDIT APPLICATION (BOOKING) HANDLERS
       ============================================================ */

    const btnEditBooking = $("#btn-edit-booking");
    if (btnEditBooking) {
        btnEditBooking.addEventListener("click", function () {
            if (!currentBooking) return;

            const panel = $("#edit-booking-panel");
            const inspPanel = $("#create-inspection-panel");
            if (inspPanel) inspPanel.hidden = true;

            const isCurrentlyHidden = panel.hidden;
            panel.hidden = !isCurrentlyHidden;

            if (!panel.hidden) {
                $("#edit-booking-id").textContent = currentBooking.name;
                $("#edit-booking-status").value = currentBooking.booking_status || "Applied";
                $("#edit-booking-date").value = currentBooking.service_date || "";

                populateMetaDropdowns();
                if (currentBooking.service_slot) {
                    $("#edit-booking-slot").value = currentBooking.service_slot;
                }

                $("#edit-booking-msg").textContent = "";
                panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        });
    }

    const btnCancelEditBooking = $("#btn-cancel-edit-booking");
    if (btnCancelEditBooking) {
        btnCancelEditBooking.addEventListener("click", function () {
            const panel = $("#edit-booking-panel");
            if (panel) panel.hidden = true;
        });
    }

    const editBookingForm = $("#edit-booking-form");
    if (editBookingForm) {
        editBookingForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            if (!currentBooking) return;

            const saveBtn = $("#btn-save-booking");
            const msgEl = $("#edit-booking-msg");

            const newStatus = $("#edit-booking-status").value;
            const newDate = $("#edit-booking-date").value;
            const newSlot = $("#edit-booking-slot").value;

            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            msgEl.className = "vms-action-msg";
            msgEl.textContent = "Updating application...";

            try {
                const resp = await frappe.call({
                    method: "vms_vehicle.api.update_technician_service_booking",
                    args: {
                        name: currentBooking.name,
                        booking_status: newStatus,
                        service_date: newDate,
                        service_slot: newSlot
                    }
                });

                if (resp && resp.message && resp.message.success) {
                    msgEl.className = "vms-action-msg success";
                    msgEl.textContent = "✓ Application updated successfully!";

                    currentBooking.booking_status = newStatus;
                    currentBooking.status = newStatus;
                    currentBooking.service_date = newDate;
                    currentBooking.service_slot = newSlot;

                    const match = allBookings.find(b => b.name === currentBooking.name);
                    if (match) {
                        match.booking_status = newStatus;
                        match.status = newStatus;
                        match.service_date = newDate;
                        match.service_slot = newSlot;
                    }

                    renderStats();
                    renderTable();
                    showDetails(currentBooking);

                    setTimeout(() => {
                        $("#edit-booking-panel").hidden = true;
                        msgEl.textContent = "";
                    }, 1200);
                } else {
                    throw new Error("Update failed.");
                }
            } catch (err) {
                console.error("Failed to update booking:", err);
                msgEl.className = "vms-action-msg error";
                msgEl.textContent = "Failed to update: " + (err.message || "Please check permissions.");
            } finally {
                saveBtn.disabled = false;
                saveBtn.innerHTML = `<span>✓</span> Save Application`;
            }
        });
    }


    /* ============================================================
       CREATE VEHICLE INSPECTION HANDLERS
       ============================================================ */

    const btnCreateInspection = $("#btn-create-inspection");
    if (btnCreateInspection) {
        btnCreateInspection.addEventListener("click", function () {
            if (!currentBooking) return;

            const panel = $("#create-inspection-panel");
            const editPanel = $("#edit-booking-panel");
            if (editPanel) editPanel.hidden = true;

            const isCurrentlyHidden = panel.hidden;
            panel.hidden = !isCurrentlyHidden;

            if (!panel.hidden) {
                $("#insp-customer-name").value = currentBooking.customer_name || currentBooking.user_id || "";
                $("#insp-vehicle-number").value = currentBooking.vehicle_number ? `${currentBooking.vehicle_number} (${currentBooking.vehicle})` : (currentBooking.vehicle || "");
                $("#insp-vehicle-docname").value = currentBooking.vehicle || "";

                // Today's date by default
                const todayStr = new Date().toISOString().split("T")[0];
                $("#insp-date").value = todayStr;

                $("#insp-technician").value = window.current_vms_user || frappe.session.user || "Technician";
                $("#insp-issue").value = "General Inspection & Service Booking Checkup";

                populateMetaDropdowns();

                $("#insp-spare-quantity").value = "1";
                $("#insp-labour").value = "1.0";
                $("#insp-inspected").checked = true;

                $("#create-inspection-msg").textContent = "";
                panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        });
    }

    const btnCancelInspection = $("#btn-cancel-inspection");
    if (btnCancelInspection) {
        btnCancelInspection.addEventListener("click", function () {
            const panel = $("#create-inspection-panel");
            if (panel) panel.hidden = true;
        });
    }

    const createInspectionForm = $("#create-inspection-form");
    if (createInspectionForm) {
        createInspectionForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            if (!currentBooking) return;

            const saveBtn = $("#btn-save-inspection");
            const msgEl = $("#create-inspection-msg");

            const vehicleDocname = $("#insp-vehicle-docname").value || currentBooking.vehicle;
            const customerName = $("#insp-customer-name").value || currentBooking.customer_name;
            const inspectionDate = $("#insp-date").value;
            const issue = $("#insp-issue").value;
            const spareParts = $("#insp-spare-parts").value || undefined;
            const spareQuantity = $("#insp-spare-quantity").value || "1";
            const mechanic = $("#insp-mechanic").value || undefined;
            const labour = parseFloat($("#insp-labour").value) || 0;
            const inspected = $("#insp-inspected").checked ? 1 : 0;

            const payload = {
                vehicle_number: vehicleDocname,
                customer_name: customerName,
                inspection_date: inspectionDate,
                issue: issue,
                spare_parts: spareParts,
                spare_part_quantity: spareQuantity,
                mechanic: mechanic,
                labour_hour: labour,
                inspected: inspected
            };

            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            msgEl.className = "vms-action-msg";
            msgEl.textContent = "Creating vehicle inspection...";

            try {
                const resp = await frappe.call({
                    method: "vms_inspection.api.create_inspection",
                    args: {
                        data: payload
                    }
                });

                if (resp && resp.message && resp.message.success) {
                    const docName = resp.message.name || "";
                    msgEl.className = "vms-action-msg success";
                    msgEl.innerHTML = `✓ Inspection <strong>${escapeHTML(docName)}</strong> created successfully! <a href="/app/vms-vehicle-inspection/${encodeURIComponent(docName)}" target="_blank" style="color: #2563eb; text-decoration: underline; margin-left: 8px;">Open in Desk ↗</a>`;

                    // If inspected was checked, reload bookings to reflect updated status
                    await loadBookings();

                    if (currentBooking) {
                        const refreshed = allBookings.find(b => b.name === currentBooking.name);
                        if (refreshed) {
                            showDetails(refreshed);
                        }
                    }

                    setTimeout(() => {
                        $("#create-inspection-panel").hidden = true;
                    }, 2500);
                } else {
                    throw new Error("Inspection creation failed.");
                }
            } catch (err) {
                console.error("Failed to create inspection:", err);
                msgEl.className = "vms-action-msg error";
                msgEl.textContent = "Failed to create: " + (err.message || "Please check permissions.");
            } finally {
                saveBtn.disabled = false;
                saveBtn.innerHTML = `<span>✓</span> Save Vehicle Inspection`;
            }
        });
    }


    /* ============================================================
       INITIAL PAGE LOAD
       ============================================================ */

    loadBookings();

});