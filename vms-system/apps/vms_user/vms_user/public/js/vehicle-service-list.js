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

        const isTech = window.is_vms_technician || false;
        const statusOptions = ["Applied", "Confirmed", "Under Work", "Updated", "Cancelled", "Rescheduled"];

        tableBody.innerHTML = pageItems.map(function (booking) {

            let statusContent = `
                <span class="vms-status ${statusClass(booking.booking_status)}">
                    ${escapeHTML(booking.booking_status || "—")}
                </span>
            `;

            let inspectBtn = "";

            if (isTech) {
                statusContent = `
                    <select class="vms-status-select ${statusClass(booking.booking_status)}" data-booking-id="${escapeHTML(booking.name)}">
                        ${statusOptions.map(opt => `<option value="${opt}" ${opt === booking.booking_status ? 'selected' : ''}>${opt}</option>`).join("")}
                    </select>
                `;

                inspectBtn = `
                    <a href="/technician-dashboard/technician-inspection?customer_name=${encodeURIComponent(booking.customer_name || '')}&vehicle_number=${encodeURIComponent(booking.vehicle || '')}&booking_id=${encodeURIComponent(booking.name)}" class="vms-btn vms-btn-success vms-btn-sm" style="text-decoration:none; padding: 4px 8px; font-size: 12px;" target="_blank">
                        Inspect
                    </a>
                `;
            }

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
                        <div style="display: flex; gap: 8px; align-items: center;">
                            ${statusContent}
                            ${inspectBtn}
                        </div>
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

        const isTech = window.is_vms_technician || false;
        const statusOptions = ["Applied", "Confirmed", "Under Work", "Updated", "Cancelled", "Rescheduled"];

        $("#booking-details-content").innerHTML = `

            <div class="vms-detail-grid">

                ${details.map(function ([label, value]) {

            let displayValue = `<strong>${escapeHTML(value || "—")}</strong>`;

            if (label === "Booking Status") {
                if (isTech) {
                    displayValue = `
                        <select class="vms-status-select ${statusClass(value)}" data-booking-id="${escapeHTML(booking.name)}" style="width: 100%; max-width: 200px;">
                            ${statusOptions.map(opt => `<option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>`).join("")}
                        </select>
                    `;
                } else {
                    displayValue = `<span class="vms-status ${statusClass(value)}">${escapeHTML(value || "—")}</span>`;
                }
            }

            return `

                        <div class="vms-detail-item">

                            <span>
                                ${escapeHTML(label)}
                            </span>

                            ${displayValue}

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

    const btnCreateInspection = $("#btn-create-inspection");
    if (btnCreateInspection) {
        btnCreateInspection.addEventListener("click", function () {
            if (!currentBooking) return;
            const url = "/vms-inspection?customer_name=" + encodeURIComponent(currentBooking.customer_name || '') + "&vehicle_number=" + encodeURIComponent(currentBooking.vehicle || '') + "&booking_id=" + encodeURIComponent(currentBooking.name);
            window.open(url, "_self");
        });
    }


    /* ============================================================
       DELEGATED EVENT HANDLERS (BUTTONS)
       ============================================================ */

    root.addEventListener("change", async function (event) {
        if (event.target.classList.contains("vms-status-select")) {
            const selectEl = event.target;
            const bookingId = selectEl.dataset.bookingId;
            const newStatus = selectEl.value;

            // Optional: visual feedback
            selectEl.disabled = true;

            try {
                const resp = await frappe.call({
                    method: "vms_vehicle.api.update_technician_service_booking",
                    args: {
                        name: bookingId,
                        booking_status: newStatus
                    }
                });

                if (resp && resp.message && resp.message.success) {
                    frappe.show_alert({ message: "Status updated successfully", indicator: "green" });

                    // Update local state
                    const match = allBookings.find(b => b.name === bookingId);
                    if (match) {
                        match.booking_status = newStatus;
                        match.status = newStatus;
                    }

                    // Update class list for color
                    selectEl.className = `vms-status-select ${statusClass(newStatus)}`;

                    renderStats();
                } else {
                    throw new Error("Update failed.");
                }
            } catch (err) {
                console.error("Failed to update status:", err);
                frappe.show_alert({ message: "Failed to update status", indicator: "red" });
                // Revert to old value
                const match = allBookings.find(b => b.name === bookingId);
                if (match) {
                    selectEl.value = match.booking_status;
                }
            } finally {
                selectEl.disabled = false;
            }
        }
    });

    /* ============================================================
       INITIAL PAGE LOAD
       ============================================================ */

    loadBookings();

});