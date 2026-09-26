frappe.ready(function () {
    const API = {
        vehicles: "vms_vehicle.api.get_my_vehicles",
        slots: "vms_vehicle.api.get_available_service_slots",
        create: "vms_vehicle.api.register_vehicle_service",
        bookings: "vms_vehicle.api.get_my_service_registrations",
        bookingDetails: "vms_vehicle.api.get_my_service_registration"
    };

    const $vehicle = $("#vms-vehicle");
    const $date = $("#vms-service-date");
    const $slot = $("#vms-service-slot");
    const $description = $("#vms-service-description");
    const $form = $("#vms-service-form");
    const $message = $("#vms-booking-message");
    const $bookingsBody = $("#vms-bookings-body");
    const $loading = $("#vms-bookings-loading");
    const $empty = $("#vms-bookings-empty");
    const $details = $("#vms-booking-details");
    const $detailsContent = $("#vms-booking-details-content");

    function escapeHtml(value) {
        return $("<div>").text(value == null ? "" : String(value)).html();
    }

    function showMessage(message, type) {
        $message
            .removeClass("success error")
            .addClass(type || "")
            .text(message || "");
    }

    function setLoadingSlots(message) {
        $slot.empty().append(
            $("<option>", {
                value: "",
                text: message
            })
        );
    }

    function callApi(method, args) {
        return new Promise(function (resolve, reject) {
            frappe.call({
                method: method,
                args: args || {},
                callback: function (response) {
                    if (response && response.exc) {
                        reject(response);
                        return;
                    }

                    resolve(response ? response.message : null);
                },
                error: function (error) {
                    reject(error);
                }
            });
        });
    }

    async function loadVehicles() {
        $vehicle.empty().append(
            $("<option>", {
                value: "",
                text: "Loading your vehicles..."
            })
        );

        try {
            const vehicles = await callApi(API.vehicles);

            $vehicle.empty().append(
                $("<option>", {
                    value: "",
                    text: "Select a vehicle"
                })
            );

            if (!vehicles || vehicles.length === 0) {
                $vehicle.empty().append(
                    $("<option>", {
                        value: "",
                        text: "No vehicles registered to your account"
                    })
                );
                return;
            }

            vehicles.forEach(function (vehicle) {
                const vehicleLabel = [
                    vehicle.vehicle_number,
                    vehicle.vehicle_brand,
                    vehicle.vehicle_model
                ].filter(Boolean).join(" - ");

                $vehicle.append(
                    $("<option>", {
                        value: vehicle.name,
                        text: vehicleLabel || vehicle.name
                    })
                );
            });
        } catch (error) {
            $vehicle.empty().append(
                $("<option>", {
                    value: "",
                    text: "Unable to load vehicles"
                })
            );
            showMessage("Could not load your vehicles. Please refresh.", "error");
        }
    }

    async function loadSlots() {
        const serviceDate = $date.val();

        if (!serviceDate) {
            setLoadingSlots("Choose a date first");
            return;
        }

        setLoadingSlots("Checking availability...");

        try {
            const slots = await callApi(API.slots, {
                service_date: serviceDate
            });

            setLoadingSlots(
                slots && slots.length
                    ? "Select an available slot"
                    : "No slots available for this date"
            );

            (slots || []).forEach(function (slot) {
                $slot.append(
                    $("<option>", {
                        value: slot.name,
                        text: slot.label + " — " + slot.remaining + " remaining"
                    })
                );
            });
        } catch (error) {
            setLoadingSlots("Could not load slots");
            showMessage(
                "Unable to load availability. Check the selected date.",
                "error"
            );
        }
    }

    function statusClass(status) {
        const normalized = String(status || "").toLowerCase();

        if (normalized === "completed") return "completed";
        if (normalized === "confirmed") return "confirmed";
        if (normalized === "under work" || normalized === "in progress") return "in-progress";
        if (normalized === "rejected") return "rejected";
        if (normalized === "cancelled") return "cancelled";

        return "pending";
    }

    async function loadBookings() {
        $loading.prop("hidden", false).text("Loading your bookings...");
        $empty.prop("hidden", true);
        $bookingsBody.empty();

        try {
            const bookings = await callApi(API.bookings);

            $loading.prop("hidden", true);

            if (!bookings || bookings.length === 0) {
                $empty.prop("hidden", false);
                return;
            }

            bookings.forEach(function (booking) {
                const $row = $("<tr>");

                $row.append($("<td>").text(booking.name || ""));
                $row.append($("<td>").text(booking.vehicle_number || booking.vehicle_registration || booking.vehicle || ""));
                $row.append($("<td>").text(booking.service_date || ""));
                $row.append($("<td>").text(booking.slot_label || booking.service_slot || ""));

                const currentStatus = booking.status || booking.booking_status || "Pending";
                const $status = $("<span>")
                    .addClass("vms-status")
                    .addClass(statusClass(currentStatus))
                    .text(currentStatus);

                $row.append($("<td>").append($status));

                const $button = $("<button>", {
                    type: "button",
                    class: "btn btn-default btn-xs",
                    text: "View"
                });

                $button.on("click", function () {
                    loadBookingDetails(booking.name);
                });

                $row.append($("<td>").append($button));
                $bookingsBody.append($row);
            });
        } catch (error) {
            $loading.text("Unable to load bookings. Please refresh.");
            showMessage("Could not load your service bookings.", "error");
        }
    }

    async function loadBookingDetails(bookingName) {
        try {
            const booking = await callApi(API.bookingDetails, {
                registration_name: bookingName
            });

            $detailsContent.empty();

            const fields = [
                ["Booking ID", booking.name],
                ["Vehicle", booking.vehicle_registration || booking.vehicle_number || booking.vehicle],
                ["Service Date", booking.service_date],
                ["Service Slot", booking.slot_label || booking.service_slot],
                ["Description", booking.service_description],
                ["Status", booking.status || booking.booking_status]
            ];

            fields.forEach(function (field) {
                const $line = $("<p>");
                $line.append(
                    $("<strong>").text(field[0] + ": ")
                );
                $line.append(
                    $("<span>").text(field[1] || "—")
                );
                $detailsContent.append($line);
            });

            $details.prop("hidden", false);
            $details[0].scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        } catch (error) {
            showMessage(
                "You cannot view this booking, or it no longer exists.",
                "error"
            );
        }
    }

    $date.on("change", loadSlots);

    $form.on("submit", async function (event) {
        event.preventDefault();
        showMessage("", "");

        const vehicle = $vehicle.val();
        const serviceDate = $date.val();
        const serviceSlot = $slot.val();
        const description = $description.val();

        if (!vehicle || !serviceDate || !serviceSlot) {
            showMessage("Please select a vehicle, date, and slot.", "error");
            return;
        }

        const $submit = $("#vms-submit-booking");
        $submit.prop("disabled", true).text("Submitting...");

        try {
            const result = await callApi(API.create, {
                vehicle_registration: vehicle,
                service_date: serviceDate,
                service_slot: serviceSlot,
                service_description: description
            });

            showMessage(
                "Booking submitted. Your booking ID is " +
                (result.name || "") +
                ".",
                "success"
            );

            $description.val("");
            await loadSlots();
            await loadBookings();
        } catch (error) {
            showMessage(
                "Booking could not be submitted. The slot may be full or the date may be invalid.",
                "error"
            );
        } finally {
            $submit.prop("disabled", false).text("Submit Booking");
        }
    });

    $("#vms-refresh-bookings").on("click", loadBookings);

    $("#vms-close-details").on("click", function () {
        $details.prop("hidden", true);
    });

    // Set minimum date to today in the browser.
    const today = new Date();
    const localToday = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    $date.attr("min", localToday);

    loadVehicles();
    loadBookings();
});