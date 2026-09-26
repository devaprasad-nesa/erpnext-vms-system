/* =========================================================
   VMS VEHICLE REGISTRATION
   vehicle-register.js

   Responsibilities:
   1. Load logged-in user
   2. Handle vehicle registration form
   3. Prevent duplicate submissions
   4. Validate input
   5. Call Frappe API
   6. Show success/error messages
   7. Redirect to customer vehicles page
   ========================================================= */

(function () {
    "use strict";

    function initVehicleRegister() {
        const form = document.getElementById("vehicle-form");
        const saveButton = document.getElementById("save-vehicle-btn");
        const loggedUser = document.getElementById("logged-user");
        const logoutButton = document.getElementById("logout-btn");

        if (!form) {
            return;
        }

        // Prevent attaching duplicate event listeners
        if (form.dataset.listenerAttached === "true") {
            return;
        }
        form.dataset.listenerAttached = "true";

        let isSubmitting = false;

        /* =====================================================
           LOAD CURRENT LOGGED-IN USER
           ===================================================== */
        loadLoggedInUser();

        /* =====================================================
           FORM SUBMIT EVENT
           ===================================================== */
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            registerVehicle();
        });

        /* =====================================================
           LOGOUT EVENT
           ===================================================== */
        if (logoutButton) {
            logoutButton.addEventListener("click", logoutUser);
        }

        /* =====================================================
           FUNCTION: LOAD LOGGED-IN USER
           ===================================================== */
        function loadLoggedInUser() {
            if (!window.frappe?.session?.user) {
                if (loggedUser) {
                    loggedUser.textContent = "Guest";
                }
                return;
            }

            const currentUser = window.frappe.session.user;
            if (loggedUser) {
                loggedUser.textContent = currentUser;
            }
        }

        /* =====================================================
           FUNCTION: REGISTER VEHICLE
           ===================================================== */
        function registerVehicle() {
            // Guard against duplicate concurrent submissions
            if (isSubmitting) {
                return;
            }

            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const formData = new FormData(form);

            const values = {
                vehicle_number: cleanValue(formData.get("vehicle_number")),
                vehicle_brand: cleanValue(formData.get("vehicle_brand")),
                vehicle_model: cleanValue(formData.get("vehicle_model")),
                vehicle_type: cleanValue(formData.get("vehicle_type")),
                fuel_type: cleanValue(formData.get("fuel_type")),
                manufacturing_year: cleanValue(formData.get("manufacturing_year")),
                color: cleanValue(formData.get("color")),
                chassis_number: cleanValue(formData.get("chassis_number")),
                engine_number: cleanValue(formData.get("engine_number")),
                registration_date: cleanValue(formData.get("registration_date")),
                notes: cleanValue(formData.get("notes"))
            };

            values.vehicle_number = values.vehicle_number.toUpperCase();

            if (!values.vehicle_number) {
                showError("Please enter the vehicle registration number.");
                return;
            }

            if (!values.vehicle_brand) {
                showError("Please select the vehicle brand.");
                return;
            }

            if (!values.vehicle_model) {
                showError("Please enter the vehicle model.");
                return;
            }

            if (!values.vehicle_type) {
                showError("Please select the vehicle type.");
                return;
            }

            if (!values.fuel_type) {
                showError("Please select the fuel type.");
                return;
            }

            if (values.manufacturing_year) {
                const year = parseInt(values.manufacturing_year, 10);
                if (isNaN(year) || year < 1900 || year > 2100) {
                    showError("Please enter a valid manufacturing year.");
                    return;
                }
            }

            // Lock submission
            isSubmitting = true;
            setLoadingState(true);

            frappe.call({
                method: "vms_vehicle.api.create_vehicle",
                args: values,
                freeze: true,
                freeze_message: "Registering vehicle...",
                callback: function (response) {
                    isSubmitting = false;
                    setLoadingState(false);
                    handleCreateVehicleResponse(response);
                },
                error: function (error) {
                    isSubmitting = false;
                    setLoadingState(false);
                    console.error("Vehicle registration error:", error);
                    showError("Unable to register the vehicle. Please check the details and try again.");
                }
            });
        }

        /* =====================================================
           FUNCTION: HANDLE API RESPONSE
           ===================================================== */
        function handleCreateVehicleResponse(response) {
            if (response && response.message) {
                if (window.frappe?.show_alert) {
                    frappe.show_alert({
                        message: "Vehicle registered successfully.",
                        indicator: "green"
                    }, 5);
                }

                if (window.frappe?.msgprint) {
                    frappe.msgprint({
                        title: "Vehicle Registered",
                        message: "Your vehicle has been registered successfully.",
                        indicator: "green"
                    });
                }

                setTimeout(function () {
                    window.location.href = "/my-vehicles";
                }, 1000);
                return;
            }

            showError("Vehicle registration failed. No confirmation was received from the server.");
        }

        /* =====================================================
           FUNCTION: CLEAN VALUE
           ===================================================== */
        function cleanValue(value) {
            if (value === null || value === undefined) {
                return "";
            }
            return String(value).trim();
        }

        /* =====================================================
           FUNCTION: SET LOADING STATE
           ===================================================== */
        function setLoadingState(isLoading) {
            if (!saveButton) {
                return;
            }

            if (isLoading) {
                saveButton.disabled = true;
                saveButton.innerHTML = `
                    <span class="btn-icon">⏳</span>
                    <span>Registering...</span>
                `;
            } else {
                saveButton.disabled = false;
                saveButton.innerHTML = `
                    <span class="btn-icon">✓</span>
                    <span>Save Vehicle</span>
                `;
            }
        }

        /* =====================================================
           FUNCTION: SHOW ERROR
           ===================================================== */
        function showError(messageText) {
            const messageEl = document.getElementById("vehicle-form-message");
            if (messageEl) {
                messageEl.textContent = messageText;
                messageEl.className = "form-message error";
                messageEl.hidden = false;
            }

            if (window.frappe?.msgprint) {
                frappe.msgprint({
                    title: "Vehicle Registration",
                    message: messageText,
                    indicator: "red"
                });
            }
        }

        /* =====================================================
           FUNCTION: LOGOUT USER
           ===================================================== */
        function logoutUser() {
            if (!window.frappe?.confirm) {
                window.location.href = "/login-page/vms-login";
                return;
            }

            frappe.confirm("Are you sure you want to logout?", function () {
                frappe.call({
                    method: "logout",
                    freeze: true,
                    freeze_message: "Logging out...",
                    callback: function () {
                        window.location.href = "/login-page/vms-login";
                    },
                    error: function () {
                        window.location.href = "/login-page/vms-login";
                    }
                });
            });
        }
    }

    if (window.frappe?.ready) {
        frappe.ready(initVehicleRegister);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initVehicleRegister, { once: true });
    } else {
        initVehicleRegister();
    }
})();