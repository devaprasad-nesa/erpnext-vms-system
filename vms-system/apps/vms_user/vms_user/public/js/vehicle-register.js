/* =========================================================
   VMS VEHICLE REGISTRATION
   vehicle-register.js

   Responsibilities:
   1. Load logged-in user
   2. Fetch dynamic Vehicle Brands on page load
   3. Dependent dropdown handling for Brand -> Model -> Fuel Type
   4. Prevent duplicate submissions
   5. Validate input & show error/success feedback
   6. Call Frappe create_vehicle API
   7. Redirect to customer vehicles page
   ========================================================= */

(function () {
    "use strict";

    function initVehicleRegister() {
        const form = document.getElementById("vehicle-form");
        const saveButton = document.getElementById("save-vehicle-btn");
        const loggedUser = document.getElementById("logged-user");
        const logoutButton = document.getElementById("logout-btn");
        const messageBox = document.getElementById("vehicle-form-message");

        const brandSelect = document.getElementById("vehicle-brand");
        const modelSelect = document.getElementById("vehicle-model");
        const fuelSelect = document.getElementById("fuel-type");

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
           LOAD CURRENT LOGGED-IN USER & INITIALIZE DROPDOWNS
           ===================================================== */
        loadLoggedInUser();
        loadBrands();

        /* =====================================================
           EVENT LISTENERS FOR DEPENDENT DROPDOWNS
           ===================================================== */
        if (brandSelect) {
            brandSelect.addEventListener("change", onBrandChanged);
        }

        if (modelSelect) {
            modelSelect.addEventListener("change", onModelChanged);
        }

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
           FUNCTION: LOAD BRANDS
           ===================================================== */
        function loadBrands() {
            if (!brandSelect) return;

            // Only show "Loading..." if no options were server pre-rendered
            const existingOptions = brandSelect.querySelectorAll("option[value]:not([value=''])");
            if (existingOptions.length === 0) {
                brandSelect.innerHTML = `<option value="">Loading brands...</option>`;
                brandSelect.disabled = true;
            }
            resetModelSelect("Select Brand First");
            resetFuelSelect("Select Model First");

            fetchAPI("vms_vehicle.api.get_vehicle_brands", {}, function (err, brands) {
                brandSelect.disabled = false;
                if (err || !Array.isArray(brands)) {
                    if (existingOptions.length === 0) {
                        brandSelect.innerHTML = `<option value="">Failed to load brands</option>`;
                        showError("Unable to load vehicle brands. Please refresh the page.");
                    }
                    return;
                }

                if (brands.length === 0) {
                    brandSelect.innerHTML = `<option value="">No brands available</option>`;
                    return;
                }

                const currentVal = brandSelect.value;
                let optionsHtml = `<option value="">Select Brand</option>`;
                brands.forEach(function (b) {
                    const brandName = b.brand_name || b.name;
                    const isSelected = currentVal && currentVal === brandName ? " selected" : "";
                    optionsHtml += `<option value="${escapeHTML(brandName)}"${isSelected}>${escapeHTML(brandName)}</option>`;
                });
                brandSelect.innerHTML = optionsHtml;
            });
        }

        /* =====================================================
           FUNCTION: ON BRAND CHANGED
           ===================================================== */
        function onBrandChanged() {
            const selectedBrand = (brandSelect.value || "").trim();

            resetModelSelect("Select Brand First");
            resetFuelSelect("Select Model First");

            if (!selectedBrand) {
                return;
            }

            modelSelect.innerHTML = `<option value="">Loading models...</option>`;
            modelSelect.disabled = true;

            fetchAPI("vms_vehicle.api.get_vehicle_models", { brand: selectedBrand }, function (err, models) {
                if (err || !Array.isArray(models)) {
                    modelSelect.innerHTML = `<option value="">Failed to load models</option>`;
                    modelSelect.disabled = true;
                    showError("Unable to load models for selected brand.");
                    return;
                }

                if (models.length === 0) {
                    modelSelect.innerHTML = `<option value="">No models available for ${escapeHTML(selectedBrand)}</option>`;
                    modelSelect.disabled = true;
                    return;
                }

                let optionsHtml = `<option value="">Select Model</option>`;
                models.forEach(function (m) {
                    const modelName = m.model_name || m.name;
                    optionsHtml += `<option value="${escapeHTML(modelName)}">${escapeHTML(modelName)}</option>`;
                });
                modelSelect.innerHTML = optionsHtml;
                modelSelect.disabled = false;
            });
        }

        /* =====================================================
           FUNCTION: ON MODEL CHANGED
           ===================================================== */
        function onModelChanged() {
            const selectedModel = (modelSelect.value || "").trim();
            const selectedBrand = (brandSelect.value || "").trim();

            resetFuelSelect("Select Model First");

            if (!selectedModel) {
                return;
            }

            fuelSelect.innerHTML = `<option value="">Loading fuel types...</option>`;
            fuelSelect.disabled = true;

            fetchAPI("vms_vehicle.api.get_vehicle_fuel_types", { model: selectedModel, brand: selectedBrand }, function (err, fuels) {
                if (err || !Array.isArray(fuels)) {
                    fuelSelect.innerHTML = `<option value="">Failed to load fuel types</option>`;
                    fuelSelect.disabled = true;
                    showError("Unable to load fuel types for selected model.");
                    return;
                }

                if (fuels.length === 0) {
                    fuelSelect.innerHTML = `<option value="">No fuel types configured for ${escapeHTML(selectedModel)}</option>`;
                    fuelSelect.disabled = true;
                    return;
                }

                let optionsHtml = `<option value="">Select Fuel Type</option>`;
                fuels.forEach(function (f) {
                    const fuelName = f.fuel_type || f.name;
                    optionsHtml += `<option value="${escapeHTML(fuelName)}">${escapeHTML(fuelName)}</option>`;
                });
                fuelSelect.innerHTML = optionsHtml;
                fuelSelect.disabled = false;
            });
        }

        function resetModelSelect(placeholder) {
            if (modelSelect) {
                modelSelect.innerHTML = `<option value="">${escapeHTML(placeholder || "Select Brand First")}</option>`;
                modelSelect.disabled = true;
                modelSelect.value = "";
            }
        }

        function resetFuelSelect(placeholder) {
            if (fuelSelect) {
                fuelSelect.innerHTML = `<option value="">${escapeHTML(placeholder || "Select Model First")}</option>`;
                fuelSelect.disabled = true;
                fuelSelect.value = "";
            }
        }

        /* =====================================================
           FUNCTION: REGISTER VEHICLE
           ===================================================== */
        function registerVehicle() {
            if (isSubmitting) {
                return;
            }

            hideMessage();

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
                vehicle_fuel_type: cleanValue(formData.get("fuel_type")),
                manufacturing_year: cleanValue(formData.get("manufacturing_year")),
                color: cleanValue(formData.get("color")),
                chassis_number: cleanValue(formData.get("chassis_number")),
                engine_number: cleanValue(formData.get("engine_number")),
                registration_date: cleanValue(formData.get("registration_date")),
                notes: cleanValue(formData.get("notes"))
            };

            values.vehicle_number = (values.vehicle_number || "").toUpperCase();

            if (!values.vehicle_number) {
                showError("Please enter the vehicle registration number.");
                return;
            }

            if (!values.vehicle_brand) {
                showError("Please select the vehicle brand.");
                return;
            }

            if (!values.vehicle_model) {
                showError("Please select the vehicle model.");
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

            fetchAPI("vms_vehicle.api.create_vehicle", values, function (err, result) {
                isSubmitting = false;
                setLoadingState(false);

                if (err) {
                    showError(err.message || "Failed to register vehicle. Please verify brand, model, and fuel type.");
                    return;
                }

                showSuccess("Vehicle registered successfully! Redirecting...");
                form.reset();
                resetModelSelect("Select Brand First");
                resetFuelSelect("Select Model First");

                setTimeout(function () {
                    window.location.href = "/my-vehicles";
                }, 1200);
            });
        }

        /* =====================================================
           HELPER: FETCH API
           ===================================================== */
        function fetchAPI(method, args, callback) {
            const isGetMethod = method.startsWith("vms_vehicle.api.get_");

            if (isGetMethod) {
                let url = `/api/method/${method}`;
                const queryParams = new URLSearchParams();
                for (const key in (args || {})) {
                    if (args[key] !== undefined && args[key] !== null) {
                        queryParams.append(key, args[key]);
                    }
                }
                const qs = queryParams.toString();
                if (qs) url += `?${qs}`;

                fetch(url, {
                    method: "GET",
                    headers: {
                        "Accept": "application/json",
                        "X-Frappe-CSRF-Token": getCsrfToken()
                    }
                })
                .then(function (res) {
                    return res.json().then(function (data) {
                        if (!res.ok || data.exc || data.exception) {
                            let msg = data.message || data.exception || res.statusText;
                            throw new Error(msg);
                        }
                        return data.message;
                    });
                })
                .then(function (result) {
                    callback(null, result);
                })
                .catch(function (err) {
                    // Fallback to frappe.call if available
                    if (window.frappe?.call) {
                        frappe.call({
                            method: method,
                            args: args,
                            callback: function (response) {
                                if (response.exc || response.error) {
                                    callback(new Error(response.message || "Request failed"));
                                } else {
                                    callback(null, response.message);
                                }
                            },
                            error: function (xhr) {
                                callback(new Error(xhr?.responseJSON?.message || xhr?.statusText || "Request failed"));
                            }
                        });
                    } else {
                        callback(err);
                    }
                });
                return;
            }

            // POST methods
            if (window.frappe?.call) {
                frappe.call({
                    method: method,
                    args: args,
                    callback: function (response) {
                        if (response.exc || response.error) {
                            callback(new Error(response.message || "Request failed"));
                        } else {
                            callback(null, response.message);
                        }
                    },
                    error: function (xhr) {
                        let msg = "An error occurred";
                        try {
                            if (xhr?.responseJSON?._server_messages) {
                                const msgs = JSON.parse(xhr.responseJSON._server_messages);
                                const parsed = JSON.parse(msgs[0]);
                                msg = parsed.message || msg;
                            } else if (xhr?.message) {
                                msg = xhr.message;
                            }
                        } catch (e) {
                            msg = xhr?.statusText || msg;
                        }
                        callback(new Error(msg));
                    }
                });
            } else {
                fetch(`/api/method/${method}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-Frappe-CSRF-Token": getCsrfToken()
                    },
                    body: JSON.stringify(args)
                })
                .then(function (res) {
                    return res.json().then(function (data) {
                        if (!res.ok || data.exc || data.exception) {
                            let msg = data.message || data.exception || data.exc || res.statusText;
                            if (data._server_messages) {
                                try {
                                    const msgs = JSON.parse(data._server_messages);
                                    const parsed = JSON.parse(msgs[0]);
                                    msg = parsed.message || msg;
                                } catch (e) {}
                            }
                            throw new Error(msg);
                        }
                        return data.message;
                    });
                })
                .then(function (result) {
                    callback(null, result);
                })
                .catch(function (err) {
                    callback(err);
                });
            }
        }

        function getCsrfToken() {
            return window.frappe?.csrf_token || (document.querySelector('meta[name="csrf-token"]')?.content) || "";
        }

        function setLoadingState(loading) {
            if (!saveButton) return;
            saveButton.disabled = loading;
            const btnText = saveButton.querySelector(".btn-text") || saveButton;
            if (loading) {
                btnText.textContent = "Registering Vehicle...";
            } else {
                btnText.textContent = "Save Vehicle";
            }
        }

        function showError(message) {
            if (!messageBox) return;
            messageBox.className = "form-message error-message";
            messageBox.textContent = message;
            messageBox.hidden = false;
            messageBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        function showSuccess(message) {
            if (!messageBox) return;
            messageBox.className = "form-message success-message";
            messageBox.textContent = message;
            messageBox.hidden = false;
        }

        function hideMessage() {
            if (messageBox) {
                messageBox.hidden = true;
                messageBox.textContent = "";
            }
        }

        function cleanValue(val) {
            return val ? String(val).trim() : null;
        }

        function escapeHTML(str) {
            if (!str) return "";
            return String(str)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function logoutUser() {
            if (window.frappe?.call) {
                frappe.call({
                    method: "logout",
                    callback: function () {
                        window.location.href = "/login";
                    }
                });
            } else {
                fetch("/api/method/logout", { method: "POST" }).finally(function () {
                    window.location.href = "/login";
                });
            }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initVehicleRegister);
    } else {
        initVehicleRegister();
    }
})();
