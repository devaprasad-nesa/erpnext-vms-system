/* ======================================================
   FILE: signup.js
   PURPOSE: Customer Account Registration Handler
   ====================================================== */

frappe.ready(function () {
    $("#vms-signup-form").on("submit", function (event) {
        event.preventDefault();

        const username = ($("#username").val() || "").trim();
        const email = ($("#email").val() || "").trim().toLowerCase();
        const password = $("#password").val();
        const confirm_password = $("#confirm_password").val();

        if (!username || !email || !password || !confirm_password) {
            frappe.msgprint(__("All fields are required."));
            return;
        }

        if (password !== confirm_password) {
            frappe.msgprint(__("Passwords do not match."));
            return;
        }

        if (password.length < 8) {
            frappe.msgprint(__("Password must be at least 8 characters."));
            return;
        }

        frappe.call({
            method: "vms_user.api.register_customer",
            args: {
                username: username,
                email: email,
                password: password,
                confirm_password: confirm_password
            },
            freeze: true,
            freeze_message: __("Creating your account..."),

            callback: function (response) {
                if (response.message) {
                    frappe.msgprint({
                        title: __("Registration successful"),
                        message: __("Your account has been created. Please log in."),
                        indicator: "green"
                    });

                    setTimeout(function () {
                        window.location.href = "../login";
                    }, 1500);
                }
            },
            error: function (err) {
                console.error("Registration error:", err);
            }
        });
    });
});
