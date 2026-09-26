
frappe.ready(function () {
    $("#vms-signup-form").on("submit", function (event) {
        event.preventDefault();

        const username = $("#username").val().trim();
        const email = $("#email").val().trim();
        const password = $("#password").val();
        const confirm_password = $("#confirm_password").val();

        if (password !== confirm_password) {
            frappe.msgprint("Passwords do not match.");
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
            freeze_message: "Creating your account...",

            callback: function (response) {
                if (response.message) {
                    frappe.msgprint({
                        title: "Registration successful",
                        message: "Your account has been created. Please log in.",
                        indicator: "green"
                    });

                    setTimeout(function () {
                        window.location.href = "/login";
                    }, 1500);
                }
            }
        });
    });
});