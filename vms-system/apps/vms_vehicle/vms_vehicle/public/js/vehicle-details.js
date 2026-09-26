/* ================================================================
   VMS VEHICLE DETAILS JAVASCRIPT
================================================================ */

document.addEventListener("DOMContentLoaded", function () {
    loadVehicleDetails();
});

function loadVehicleDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    const vehicleName = urlParams.get("name");

    const loadingEl = document.getElementById("vehicle-loading");
    const cardEl = document.getElementById("vehicle-card");
    const errorEl = document.getElementById("vehicle-error");
    const errorMessageEl = document.getElementById("vehicle-error-message");

    if (!vehicleName) {
        showError("No vehicle specified. Please select a vehicle from My Vehicles.");
        return;
    }

    // Call Frappe API to load owned vehicle details
    if (window.frappe && frappe.call) {
        frappe.call({
            method: "vms_vehicle.api.get_my_vehicle",
            args: { name: vehicleName },
            callback: function (r) {
                const v = r.message;
                if (!v) {
                    showError("Vehicle not found or you do not have permission to view it.");
                    return;
                }
                renderVehicleData(v);
            },
            error: function (err) {
                showError("Failed to load vehicle details. Please try again.");
            }
        });
    } else {
        // Fallback to fetch API if frappe.call is not available
        fetch(`/api/method/vms_vehicle.api.get_my_vehicle?name=${encodeURIComponent(vehicleName)}`, {
            headers: { "Accept": "application/json" }
        })
        .then(res => res.json())
        .then(data => {
            const v = data.message;
            if (!v) {
                showError("Vehicle not found or you do not have permission to view it.");
                return;
            }
            renderVehicleData(v);
        })
        .catch(err => {
            showError("Failed to load vehicle details. Please check your connection.");
        });
    }

    function showError(msg) {
        if (loadingEl) loadingEl.style.display = "none";
        if (cardEl) cardEl.style.display = "none";
        if (errorEl) {
            errorEl.style.display = "block";
            if (errorMessageEl) errorMessageEl.textContent = msg;
        }
    }

    function renderVehicleData(v) {
        if (loadingEl) loadingEl.style.display = "none";
        if (errorEl) errorEl.style.display = "none";
        if (cardEl) cardEl.style.display = "block";

        const plate = v.vehicle_number || v.name || "-";
        const brandModel = [v.vehicle_brand, v.vehicle_model].filter(Boolean).join(" ") || "Vehicle Details";

        setText("v-number", plate);
        setText("v-brand-model", brandModel);
        setText("v-fuel", v.fuel_type || "N/A");
        setText("v-color", v.vehicle_color || "N/A");
        setText("v-chassis", v.chassis_number || "N/A");
        setText("v-engine", v.engine_number || "N/A");
        setText("v-year", v.manufacturing_year || "N/A");
        setText("v-date", v.registration_date || "N/A");
        setText("v-notes", v.notes && v.notes.trim() ? v.notes : "No special notes recorded for this vehicle.");

        // Update hero title
        const heroTitle = document.getElementById("vehicle-hero-title");
        if (heroTitle) {
            heroTitle.textContent = `${plate} - ${brandModel}`;
        }

        // Configure Book Service buttons
        const bookBtns = document.querySelectorAll(".btn-book-service");
        bookBtns.forEach(btn => {
            btn.href = `/customer-home?vehicle=${encodeURIComponent(v.name)}`;
        });

        // Configure Delete Vehicle button
        const deleteBtn = document.getElementById("delete-vehicle-btn");
        if (deleteBtn) {
            deleteBtn.onclick = function () {
                confirmDeleteVehicle(v.name, plate);
            };
        }
    }

    function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }
}

function confirmDeleteVehicle(vehicleName, plate) {
    const confirmMsg = `Are you sure you want to delete vehicle ${plate || vehicleName}? This action cannot be undone.`;

    if (window.frappe && frappe.confirm) {
        frappe.confirm(confirmMsg, function () {
            executeDelete(vehicleName);
        });
    } else {
        if (confirm(confirmMsg)) {
            executeDelete(vehicleName);
        }
    }
}

function executeDelete(vehicleName) {
    const deleteBtn = document.getElementById("delete-vehicle-btn");
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.textContent = "Deleting...";
    }

    if (window.frappe && frappe.call) {
        frappe.call({
            method: "vms_vehicle.api.delete_vehicle",
            args: { name: vehicleName },
            freeze: true,
            callback: function (r) {
                if (window.frappe.show_alert) {
                    frappe.show_alert({ message: "Vehicle deleted successfully", indicator: "green" });
                }
                setTimeout(() => {
                    window.location.href = "/my-vehicles";
                }, 800);
            },
            error: function () {
                if (deleteBtn) {
                    deleteBtn.disabled = false;
                    deleteBtn.textContent = "Delete Vehicle";
                }
            }
        });
    } else {
        fetch("/api/method/vms_vehicle.api.delete_vehicle", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": window.frappe?.csrf_token || ""
            },
            body: JSON.stringify({ name: vehicleName })
        })
        .then(res => res.json())
        .then(() => {
            window.location.href = "/my-vehicles";
        })
        .catch(() => {
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.textContent = "Delete Vehicle";
            }
        });
    }
}
