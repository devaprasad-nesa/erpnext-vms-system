frappe.ready(() => {
    const root = document.getElementById("mechanic-dashboard-page");
    if (!root) return;

    const $ = id => document.getElementById(id);
    const escapeHTML = value => frappe.utils.escape_html(String(value ?? ""));

    let currentBookings = [];
    let currentInspections = [];

    // Utility to show global messages
    function showMessage(message, type = "info") {
        const msgDiv = $("mechanic-message");
        if (!message) {
            msgDiv.hidden = true;
            return;
        }
        msgDiv.textContent = message;
        msgDiv.className = `dashboard-message ${type}`;
        msgDiv.hidden = false;
    }

    // Modal elements
    const statusModal = $("booking-status-modal");
    const inspectModal = $("inspection-details-modal");
    let activeBookingId = null;

    // Render summary stats
    function renderStats() {
        $("total-bookings").textContent = currentBookings.length;
        $("applied-bookings").textContent = currentBookings.filter(b => b.booking_status === "Applied").length;
        $("under-work-bookings").textContent = currentBookings.filter(b => b.booking_status === "Under Work").length;
        $("total-inspections").textContent = currentInspections.length;
    }

    // Render bookings table
    function renderBookings() {
        const searchTerm = ($("booking-search").value || "").toLowerCase();
        const statusFilter = $("booking-status-filter").value;

        const filtered = currentBookings.filter(row => {
            if (statusFilter && row.booking_status !== statusFilter) return false;
            
            if (searchTerm) {
                const searchStr = `${row.name} ${row.customer_name} ${row.vehicle}`.toLowerCase();
                if (!searchStr.includes(searchTerm)) return false;
            }
            return true;
        });

        const tbody = $("bookings-table-body");
        
        $("bookings-loading").hidden = true;

        if (!filtered.length) {
            $("bookings-table-wrapper").hidden = true;
            $("bookings-empty").hidden = false;
            return;
        }

        $("bookings-table-wrapper").hidden = false;
        $("bookings-empty").hidden = true;

        tbody.innerHTML = filtered.map(row => {
            const statusClass = row.booking_status ? `status-${row.booking_status.toLowerCase().replace(/\s+/g, '-')}` : '';
            return `
                <tr>
                    <td><strong>${escapeHTML(row.name)}</strong></td>
                    <td>${escapeHTML(row.customer_name)}</td>
                    <td>${escapeHTML(row.vehicle)}</td>
                    <td>${escapeHTML(row.service_date)}</td>
                    <td>${escapeHTML(row.service_slot)}</td>
                    <td><span class="booking-status ${statusClass}">${escapeHTML(row.booking_status)}</span></td>
                    <td>
                        <button class="table-action-btn" data-action="update-status" data-id="${escapeHTML(row.name)}" data-status="${escapeHTML(row.booking_status)}">
                            Update Status
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // Render inspections table
    function renderInspections() {
        const tbody = $("inspections-table-body");
        
        $("inspections-loading").hidden = true;

        if (!currentInspections.length) {
            $("inspections-table-wrapper").hidden = true;
            $("inspections-empty").hidden = false;
            return;
        }

        $("inspections-table-wrapper").hidden = false;
        $("inspections-empty").hidden = true;

        tbody.innerHTML = currentInspections.map(row => `
            <tr>
                <td><strong>${escapeHTML(row.name)}</strong></td>
                <td>${escapeHTML(row.vehicle_number || row.vehicle || "-")}</td>
                <td>${escapeHTML(row.inspection_date || "-")}</td>
                <td>${escapeHTML(row.inspected ? "Completed" : "Pending")}</td>
                <td>${escapeHTML(row.issue || "-")}</td>
                <td>${escapeHTML(row.spare_parts || "-")}</td>
                <td>
                    <button class="table-action-btn" data-action="view-inspection" data-id="${escapeHTML(row.name)}">
                        View Details
                    </button>
                </td>
            </tr>
        `).join("");
    }

    // Load data from backend
    function loadDashboard() {
        showMessage("Loading dashboard...", "info");
        $("mechanic-dashboard-content").hidden = true;
        $("mechanic-access-denied").hidden = true;

        frappe.call({
            method: "vms_user.www.vms_user_dashboard.mechanic_dashboard.mechanic_dashboard.get_dashboard_data",
            callback(r) {
                if (r.exc) {
                    showMessage("Error loading dashboard data.", "error");
                    return;
                }

                $("mechanic-dashboard-content").hidden = false;
                $("mechanic-access-denied").hidden = true;
                showMessage("");

                const data = r.message || {};
                $("mechanic-user-name").textContent = data.user || "Unknown";

                currentBookings = data.service_registrations || [];
                
                if (data.vehicle_inspections && !data.vehicle_inspections.error) {
                    currentInspections = data.vehicle_inspections.records || [];
                } else {
                    currentInspections = [];
                }

                renderStats();
                renderBookings();
                renderInspections();
            },
            error() {
                $("mechanic-dashboard-content").hidden = true;
                $("mechanic-access-denied").hidden = false;
                showMessage("");
            }
        });
    }

    // Setup event listeners
    $("mechanic-refresh-btn").addEventListener("click", loadDashboard);
    $("refresh-bookings-btn").addEventListener("click", loadDashboard);
    $("refresh-inspections-btn").addEventListener("click", loadDashboard);

    $("mechanic-logout-btn").addEventListener("click", () => {
        frappe.call({
            method: "logout",
            callback: function() {
                window.location.href = "/login";
            }
        });
    });

    $("access-denied-login-btn").addEventListener("click", () => {
        window.location.href = "/login";
    });

    $("booking-search").addEventListener("input", renderBookings);
    $("booking-status-filter").addEventListener("change", renderBookings);

    // Modal event handlers
    root.addEventListener("click", e => {
        const btn = e.target.closest("button[data-action]");
        if (!btn) return;

        const action = btn.dataset.action;
        const id = btn.dataset.id;

        if (action === "update-status") {
            activeBookingId = id;
            $("modal-booking-id").textContent = id;
            $("modal-current-status").textContent = btn.dataset.status;
            $("new-booking-status").value = btn.dataset.status;
            $("status-update-message").hidden = true;
            statusModal.hidden = false;
        }

        if (action === "view-inspection") {
            openInspectionModal(id);
        }
    });

    // Save status
    $("save-status-update").addEventListener("click", () => {
        if (!activeBookingId) return;

        const newStatus = $("new-booking-status").value;
        const msgDiv = $("status-update-message");
        
        msgDiv.textContent = "Updating...";
        msgDiv.className = "modal-message info";
        msgDiv.hidden = false;

        frappe.call({
            method: "vms_user.www.vms_user_dashboard.mechanic_dashboard.mechanic_dashboard.update_booking_status",
            args: {
                name: activeBookingId,
                booking_status: newStatus
            },
            callback(r) {
                if (!r.exc && r.message && r.message.success) {
                    msgDiv.textContent = r.message.message;
                    msgDiv.className = "modal-message success";
                    
                    // Update local state
                    const booking = currentBookings.find(b => b.name === activeBookingId);
                    if (booking) {
                        booking.booking_status = newStatus;
                    }
                    
                    renderBookings();
                    renderStats();

                    setTimeout(() => {
                        statusModal.hidden = true;
                    }, 1000);
                } else {
                    msgDiv.textContent = "Error updating status.";
                    msgDiv.className = "modal-message error";
                }
            },
            error(r) {
                msgDiv.textContent = "Error updating status.";
                msgDiv.className = "modal-message error";
            }
        });
    });

    $("cancel-status-update").addEventListener("click", () => {
        statusModal.hidden = true;
    });

    $("close-status-modal").addEventListener("click", () => {
        statusModal.hidden = true;
    });

    // Inspection details modal
    function openInspectionModal(id) {
        frappe.call({
            method: "vms_user.www.vms_user_dashboard.mechanic_dashboard.mechanic_dashboard.get_vehicle_inspection",
            args: { name: id },
            callback(r) {
                if (r.exc) {
                    frappe.msgprint("Error loading inspection details.");
                    return;
                }
                
                const data = r.message;
                const container = $("inspection-details-content");
                
                let html = '<div class="inspection-detail-grid">';
                for (const [key, value] of Object.entries(data)) {
                    html += `
                        <div class="inspection-detail-item">
                            <div class="inspection-detail-label">${escapeHTML(key.replace(/_/g, ' '))}</div>
                            <div class="inspection-detail-value">${escapeHTML(value || "-")}</div>
                        </div>
                    `;
                }
                html += '</div>';
                
                container.innerHTML = html;
                inspectModal.hidden = false;
            }
        });
    }

    $("close-inspection-modal").addEventListener("click", () => {
        inspectModal.hidden = true;
    });

    // Initial load
    loadDashboard();
});