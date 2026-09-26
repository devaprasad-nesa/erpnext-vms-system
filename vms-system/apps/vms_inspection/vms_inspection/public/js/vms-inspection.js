frappe.ready(function() {
    // Set default date to today
    const dateInput = document.getElementById("inspection_date");
    if (dateInput) {
        dateInput.value = new Date().toISOString().split("T")[0];
    }
    
    // Set default issue text if empty
    const issueInput = document.getElementById("issue");
    if (issueInput && !issueInput.value) {
        issueInput.value = "General Inspection & Service Booking Checkup";
    }

    const form = document.getElementById("vms-inspection-form");
    if (form && !form.dataset.listenerAttached) {
        form.dataset.listenerAttached = "true";
        form.addEventListener("submit", async function(e) {
            e.preventDefault();
            
            const btn = document.getElementById("btn-save-inspection");
            const msgEl = document.getElementById("create-inspection-msg");
            
            btn.disabled = true;
            btn.textContent = "Saving...";
            msgEl.className = "vms-action-msg";
            msgEl.textContent = "Creating vehicle inspection...";
            
            const payload = {
                vehicle_number: document.getElementById("vehicle_number").value,
                customer_name: document.getElementById("customer_name").value,
                inspection_date: document.getElementById("inspection_date").value,
                issue: document.getElementById("issue").value,
                spare_parts: document.getElementById("spare_parts").value || undefined,
                spare_part_quantity: document.getElementById("spare_part_quantity").value || "1",
                mechanic: document.getElementById("mechanic").value || undefined,
                labour_hour: parseFloat(document.getElementById("labour_hour").value) || 0,
                inspected: document.getElementById("inspected").checked ? 1 : 0
            };
            
            const bookingId = document.getElementById("booking_id").value;
            
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
                    msgEl.innerHTML = `✓ Inspection <strong>${docName}</strong> created successfully! <a href="/app/vms-vehicle-inspection/${encodeURIComponent(docName)}" target="_blank" style="color: #2563eb; text-decoration: underline; margin-left: 8px;">Open in Desk ↗</a>`;
                    
                    if (bookingId && payload.inspected) {
                        // Attempt to update the booking status to Under Work
                        try {
                            await frappe.call({
                                method: "vms_vehicle.api.update_technician_service_booking",
                                args: {
                                    name: bookingId,
                                    booking_status: "Under Work"
                                }
                            });
                        } catch (err) {
                            console.warn("Failed to update booking status automatically", err);
                        }
                    }
                    
                    setTimeout(() => {
                        window.location.href = "/technician-dashboard/vehicle-service-list";
                    }, 2500);
                } else {
                    throw new Error("Inspection creation failed.");
                }
            } catch (err) {
                console.error(err);
                msgEl.className = "vms-action-msg error";
                msgEl.textContent = "Failed to create: " + (err.message || "Please check permissions.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<span>✓</span> Save Vehicle Inspection`;
            }
        });
    }
});
