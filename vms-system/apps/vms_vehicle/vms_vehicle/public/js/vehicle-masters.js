/* =========================================================
   VMS VEHICLE MASTER DATA MANAGEMENT - CLIENT SCRIPT
   ========================================================= */

(function () {
    "use strict";

    let masterData = {
        brands: [],
        models: [],
        fuel_types: []
    };

    let activeTab = "brands";

    window.switchMasterTab = function (tab) {
        activeTab = tab;
        document.querySelectorAll(".tab-btn").forEach(function (btn) {
            btn.classList.remove("active");
        });
        document.querySelectorAll(".master-section").forEach(function (sec) {
            sec.style.display = "none";
        });

        const targetBtn = document.getElementById(`tab-${tab}-btn`);
        const targetSec = document.getElementById(`section-${tab}`);
        if (targetBtn) targetBtn.classList.add("active");
        if (targetSec) targetSec.style.display = "block";
    };

    window.loadAllMasters = function () {
        callAPI("vms_vehicle.api.get_admin_vehicle_masters", {}, function (err, res) {
            if (err) {
                showToast("Failed to load vehicle master data: " + (err.message || "Unknown error"), "error");
                return;
            }
            masterData = res || { brands: [], models: [], fuel_types: [] };
            renderBrands();
            renderModels();
            renderFuels();
            updateBrandDropdowns();
            updateFuelCheckboxes();
        });
    };

    /* =====================================================
       1. BRANDS
       ===================================================== */
    function renderBrands() {
        const tbody = document.getElementById("brands-table-body");
        const countSpan = document.getElementById("brand-count");
        if (countSpan) countSpan.textContent = masterData.brands.length;

        const query = (document.getElementById("search-brands")?.value || "").toLowerCase();
        const filtered = masterData.brands.filter(function (b) {
            return (b.brand_name || "").toLowerCase().includes(query) || (b.description || "").toLowerCase().includes(query);
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No brands found.</td></tr>`;
            return;
        }

        let html = "";
        filtered.forEach(function (b) {
            const isEnabled = Boolean(b.enabled);
            html += `
                <tr>
                    <td><strong>${escapeHTML(b.brand_name)}</strong></td>
                    <td><span style="color:var(--vms-text-muted);">${escapeHTML(b.description || "-")}</span></td>
                    <td>
                        <span class="badge-status ${isEnabled ? "enabled" : "disabled"}">
                            ${isEnabled ? "Enabled" : "Disabled"}
                        </span>
                    </td>
                    <td style="text-align:right;">
                        <div class="action-btn-group" style="justify-content:flex-end;">
                            <button class="btn-icon" onclick="openEditBrandModal('${escapeJS(b.brand_name)}', '${escapeJS(b.description || "")}', ${isEnabled ? 1 : 0})">✏️ Edit</button>
                            <button class="btn-icon toggle-btn" onclick="toggleBrand('${escapeJS(b.brand_name)}', ${isEnabled ? 0 : 1})">
                                ${isEnabled ? "🚫 Disable" : "✅ Enable"}
                            </button>
                            <button class="btn-icon delete-btn" onclick="deleteBrand('${escapeJS(b.brand_name)}')">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    }

    window.filterBrands = function () {
        renderBrands();
    };

    window.openAddBrandModal = function () {
        document.getElementById("brand-modal-title").textContent = "Add Vehicle Brand";
        document.getElementById("brand-original-name").value = "";
        document.getElementById("brand-name-input").value = "";
        document.getElementById("brand-desc-input").value = "";
        document.getElementById("brand-enabled-input").checked = true;
        openModal("brand-modal");
    };

    window.openEditBrandModal = function (name, desc, enabled) {
        document.getElementById("brand-modal-title").textContent = "Edit Vehicle Brand";
        document.getElementById("brand-original-name").value = name;
        document.getElementById("brand-name-input").value = name;
        document.getElementById("brand-desc-input").value = desc;
        document.getElementById("brand-enabled-input").checked = Boolean(enabled);
        openModal("brand-modal");
    };

    window.saveBrand = function (e) {
        e.preventDefault();
        const origName = document.getElementById("brand-original-name").value.trim();
        const name = document.getElementById("brand-name-input").value.trim();
        const desc = document.getElementById("brand-desc-input").value.trim();
        const enabled = document.getElementById("brand-enabled-input").checked ? 1 : 0;

        if (!name) return;

        if (origName) {
            // Update
            callAPI("vms_vehicle.api.update_vehicle_brand", {
                brand_name: origName,
                new_name: name,
                description: desc,
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to update brand", "error");
                } else {
                    closeModal("brand-modal");
                    showToast(res.message || "Brand updated successfully", "success");
                    loadAllMasters();
                }
            });
        } else {
            // Create
            callAPI("vms_vehicle.api.create_vehicle_brand", {
                brand_name: name,
                description: desc,
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to create brand", "error");
                } else {
                    closeModal("brand-modal");
                    showToast(res.message || "Brand created successfully", "success");
                    loadAllMasters();
                }
            });
        }
    };

    window.toggleBrand = function (name, targetState) {
        callAPI("vms_vehicle.api.toggle_vehicle_brand", {
            brand_name: name,
            enabled: targetState
        }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to toggle brand status", "error");
            } else {
                showToast(res.message || "Brand status updated", "success");
                loadAllMasters();
            }
        });
    };

    window.deleteBrand = function (name) {
        if (!confirm(`Are you sure you want to delete brand "${name}"?`)) return;
        callAPI("vms_vehicle.api.delete_vehicle_brand", { brand_name: name }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to delete brand", "error");
            } else {
                showToast(res.message || "Brand deleted successfully", "success");
                loadAllMasters();
            }
        });
    };

    /* =====================================================
       2. MODELS
       ===================================================== */
    function renderModels() {
        const tbody = document.getElementById("models-table-body");
        const countSpan = document.getElementById("model-count");
        if (countSpan) countSpan.textContent = masterData.models.length;

        const query = (document.getElementById("search-models")?.value || "").toLowerCase();
        const brandFilter = document.getElementById("filter-model-brand")?.value || "";

        const filtered = masterData.models.filter(function (m) {
            const matchesQuery = (m.model_name || "").toLowerCase().includes(query) || (m.vehicle_brand || "").toLowerCase().includes(query);
            const matchesBrand = !brandFilter || m.vehicle_brand === brandFilter;
            return matchesQuery && matchesBrand;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No models found.</td></tr>`;
            return;
        }

        let html = "";
        filtered.forEach(function (m) {
            const isEnabled = Boolean(m.enabled);
            const fuels = (m.fuel_types || []).map(function (f) {
                return `<span class="fuel-pill">${escapeHTML(f)}</span>`;
            }).join("");

            html += `
                <tr>
                    <td><strong>${escapeHTML(m.model_name)}</strong></td>
                    <td><span class="badge-status" style="background:rgba(255,255,255,0.08); color:#e2e8f0;">${escapeHTML(m.vehicle_brand)}</span></td>
                    <td>${fuels || "<span style='color:var(--vms-text-muted);'>None assigned</span>"}</td>
                    <td>
                        <span class="badge-status ${isEnabled ? "enabled" : "disabled"}">
                            ${isEnabled ? "Enabled" : "Disabled"}
                        </span>
                    </td>
                    <td style="text-align:right;">
                        <div class="action-btn-group" style="justify-content:flex-end;">
                            <button class="btn-icon" onclick="openEditModelModal('${escapeJS(m.model_name)}', '${escapeJS(m.vehicle_brand)}', ${JSON.stringify(m.fuel_types || [])}, ${isEnabled ? 1 : 0})">✏️ Edit</button>
                            <button class="btn-icon toggle-btn" onclick="toggleModel('${escapeJS(m.model_name)}', ${isEnabled ? 0 : 1})">
                                ${isEnabled ? "🚫 Disable" : "✅ Enable"}
                            </button>
                            <button class="btn-icon delete-btn" onclick="deleteModel('${escapeJS(m.model_name)}')">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    }

    window.filterModels = function () {
        renderModels();
    };

    function updateBrandDropdowns() {
        const filterSelect = document.getElementById("filter-model-brand");
        const modalSelect = document.getElementById("model-brand-select");

        let filterHtml = `<option value="">All Brands</option>`;
        let modalHtml = `<option value="">Select Brand</option>`;

        masterData.brands.forEach(function (b) {
            filterHtml += `<option value="${escapeHTML(b.brand_name)}">${escapeHTML(b.brand_name)}</option>`;
            if (b.enabled) {
                modalHtml += `<option value="${escapeHTML(b.brand_name)}">${escapeHTML(b.brand_name)}</option>`;
            }
        });

        if (filterSelect) filterSelect.innerHTML = filterHtml;
        if (modalSelect) modalSelect.innerHTML = modalHtml;
    }

    function updateFuelCheckboxes() {
        const container = document.getElementById("model-fuels-checkboxes");
        if (!container) return;

        let html = "";
        masterData.fuel_types.forEach(function (f) {
            html += `
                <label class="fuel-checkbox-label">
                    <input type="checkbox" name="model_fuels" value="${escapeHTML(f.fuel_type)}">
                    <span>${escapeHTML(f.fuel_type)}</span>
                </label>
            `;
        });
        container.innerHTML = html || "<span style='color:var(--vms-text-muted); font-size:0.85rem;'>No fuel types configured yet.</span>";
    }

    window.openAddModelModal = function () {
        document.getElementById("model-modal-title").textContent = "Add Vehicle Model";
        document.getElementById("model-original-name").value = "";
        document.getElementById("model-name-input").value = "";
        document.getElementById("model-brand-select").value = "";
        document.getElementById("model-enabled-input").checked = true;

        document.querySelectorAll("input[name='model_fuels']").forEach(function (cb) {
            cb.checked = false;
        });

        openModal("model-modal");
    };

    window.openEditModelModal = function (name, brand, fuels, enabled) {
        document.getElementById("model-modal-title").textContent = "Edit Vehicle Model";
        document.getElementById("model-original-name").value = name;
        document.getElementById("model-name-input").value = name;
        document.getElementById("model-brand-select").value = brand;
        document.getElementById("model-enabled-input").checked = Boolean(enabled);

        const fuelsArr = Array.isArray(fuels) ? fuels : [];
        document.querySelectorAll("input[name='model_fuels']").forEach(function (cb) {
            cb.checked = fuelsArr.includes(cb.value);
        });

        openModal("model-modal");
    };

    window.saveModel = function (e) {
        e.preventDefault();
        const origName = document.getElementById("model-original-name").value.trim();
        const name = document.getElementById("model-name-input").value.trim();
        const brand = document.getElementById("model-brand-select").value.trim();
        const enabled = document.getElementById("model-enabled-input").checked ? 1 : 0;

        const selectedFuels = [];
        document.querySelectorAll("input[name='model_fuels']:checked").forEach(function (cb) {
            selectedFuels.push(cb.value);
        });

        if (!name || !brand) return;

        if (selectedFuels.length === 0) {
            showToast("Please assign at least one supported fuel type to this model.", "error");
            return;
        }

        if (origName) {
            callAPI("vms_vehicle.api.update_vehicle_model", {
                model_name: origName,
                new_name: name,
                vehicle_brand: brand,
                fuel_types: JSON.stringify(selectedFuels),
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to update model", "error");
                } else {
                    closeModal("model-modal");
                    showToast(res.message || "Model updated successfully", "success");
                    loadAllMasters();
                }
            });
        } else {
            callAPI("vms_vehicle.api.create_vehicle_model", {
                model_name: name,
                vehicle_brand: brand,
                fuel_types: JSON.stringify(selectedFuels),
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to create model", "error");
                } else {
                    closeModal("model-modal");
                    showToast(res.message || "Model created successfully", "success");
                    loadAllMasters();
                }
            });
        }
    };

    window.toggleModel = function (name, targetState) {
        callAPI("vms_vehicle.api.toggle_vehicle_model", {
            model_name: name,
            enabled: targetState
        }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to toggle model status", "error");
            } else {
                showToast(res.message || "Model status updated", "success");
                loadAllMasters();
            }
        });
    };

    window.deleteModel = function (name) {
        if (!confirm(`Are you sure you want to delete model "${name}"?`)) return;
        callAPI("vms_vehicle.api.delete_vehicle_model", { model_name: name }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to delete model", "error");
            } else {
                showToast(res.message || "Model deleted successfully", "success");
                loadAllMasters();
            }
        });
    };

    /* =====================================================
       3. FUEL TYPES
       ===================================================== */
    function renderFuels() {
        const tbody = document.getElementById("fuels-table-body");
        const countSpan = document.getElementById("fuel-count");
        if (countSpan) countSpan.textContent = masterData.fuel_types.length;

        const query = (document.getElementById("search-fuels")?.value || "").toLowerCase();
        const filtered = masterData.fuel_types.filter(function (f) {
            return (f.fuel_type || "").toLowerCase().includes(query) || (f.description || "").toLowerCase().includes(query);
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No fuel types found.</td></tr>`;
            return;
        }

        let html = "";
        filtered.forEach(function (f) {
            const isEnabled = Boolean(f.enabled);
            html += `
                <tr>
                    <td><strong>${escapeHTML(f.fuel_type)}</strong></td>
                    <td><span style="color:var(--vms-text-muted);">${escapeHTML(f.description || "-")}</span></td>
                    <td>
                        <span class="badge-status ${isEnabled ? "enabled" : "disabled"}">
                            ${isEnabled ? "Enabled" : "Disabled"}
                        </span>
                    </td>
                    <td style="text-align:right;">
                        <div class="action-btn-group" style="justify-content:flex-end;">
                            <button class="btn-icon" onclick="openEditFuelModal('${escapeJS(f.fuel_type)}', '${escapeJS(f.description || "")}', ${isEnabled ? 1 : 0})">✏️ Edit</button>
                            <button class="btn-icon toggle-btn" onclick="toggleFuel('${escapeJS(f.fuel_type)}', ${isEnabled ? 0 : 1})">
                                ${isEnabled ? "🚫 Disable" : "✅ Enable"}
                            </button>
                            <button class="btn-icon delete-btn" onclick="deleteFuel('${escapeJS(f.fuel_type)}')">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    }

    window.filterFuels = function () {
        renderFuels();
    };

    window.openAddFuelModal = function () {
        document.getElementById("fuel-modal-title").textContent = "Add Fuel Type";
        document.getElementById("fuel-original-name").value = "";
        document.getElementById("fuel-name-input").value = "";
        document.getElementById("fuel-desc-input").value = "";
        document.getElementById("fuel-enabled-input").checked = true;
        openModal("fuel-modal");
    };

    window.openEditFuelModal = function (name, desc, enabled) {
        document.getElementById("fuel-modal-title").textContent = "Edit Fuel Type";
        document.getElementById("fuel-original-name").value = name;
        document.getElementById("fuel-name-input").value = name;
        document.getElementById("fuel-desc-input").value = desc;
        document.getElementById("fuel-enabled-input").checked = Boolean(enabled);
        openModal("fuel-modal");
    };

    window.saveFuel = function (e) {
        e.preventDefault();
        const origName = document.getElementById("fuel-original-name").value.trim();
        const name = document.getElementById("fuel-name-input").value.trim();
        const desc = document.getElementById("fuel-desc-input").value.trim();
        const enabled = document.getElementById("fuel-enabled-input").checked ? 1 : 0;

        if (!name) return;

        if (origName) {
            callAPI("vms_vehicle.api.update_vehicle_fuel_type", {
                fuel_type: origName,
                new_name: name,
                description: desc,
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to update fuel type", "error");
                } else {
                    closeModal("fuel-modal");
                    showToast(res.message || "Fuel type updated successfully", "success");
                    loadAllMasters();
                }
            });
        } else {
            callAPI("vms_vehicle.api.create_vehicle_fuel_type", {
                fuel_type: name,
                description: desc,
                enabled: enabled
            }, function (err, res) {
                if (err) {
                    showToast(err.message || "Failed to create fuel type", "error");
                } else {
                    closeModal("fuel-modal");
                    showToast(res.message || "Fuel type created successfully", "success");
                    loadAllMasters();
                }
            });
        }
    };

    window.toggleFuel = function (name, targetState) {
        callAPI("vms_vehicle.api.toggle_vehicle_fuel_type", {
            fuel_type: name,
            enabled: targetState
        }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to toggle fuel type status", "error");
            } else {
                showToast(res.message || "Fuel type status updated", "success");
                loadAllMasters();
            }
        });
    };

    window.deleteFuel = function (name) {
        if (!confirm(`Are you sure you want to delete fuel type "${name}"?`)) return;
        callAPI("vms_vehicle.api.delete_vehicle_fuel_type", { fuel_type: name }, function (err, res) {
            if (err) {
                showToast(err.message || "Failed to delete fuel type", "error");
            } else {
                showToast(res.message || "Fuel type deleted successfully", "success");
                loadAllMasters();
            }
        });
    };

    /* =====================================================
       MODAL & UTILITY HELPERS
       ===================================================== */
    window.openModal = function (id) {
        const modal = document.getElementById(id);
        if (modal) modal.style.display = "flex";
    };

    window.closeModal = function (id) {
        const modal = document.getElementById(id);
        if (modal) modal.style.display = "none";
    };

    function showToast(msg, type) {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast-msg ${type === "error" ? "error" : "success"}`;
        toast.textContent = msg;
        container.innerHTML = "";
        container.appendChild(toast);

        setTimeout(function () {
            toast.remove();
        }, 4000);
    }

    function callAPI(method, args, callback) {
        if (window.frappe?.call) {
            frappe.call({
                method: method,
                args: args,
                callback: function (r) {
                    if (r.exc || r.error) {
                        callback(new Error(r.message || "Operation failed"));
                    } else {
                        callback(null, r.message);
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
                    "X-Frappe-CSRF-Token": window.frappe?.csrf_token || (document.querySelector('meta[name="csrf-token"]')?.content) || ""
                },
                body: JSON.stringify(args)
            })
            .then(function (res) {
                return res.json().then(function (data) {
                    if (!res.ok) {
                        let msg = data.message || data.exc || res.statusText;
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

    function escapeHTML(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function escapeJS(str) {
        if (!str) return "";
        return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/"/g, "\\\"");
    }

    document.addEventListener("DOMContentLoaded", function () {
        loadAllMasters();
    });
})();
