/*
 * Include this script only on the login page (or guard it by the actual login route).
 * Do not run a role redirect globally: doing so can bounce users between pages.
 */
frappe.ready(function () {
    const normalizePath = (path) => {
        const normalized = (path || "/").replace(/\/+$/, "");
        return normalized || "/";
    };

    const currentPath = normalizePath(window.location.pathname);

    // Redirect only from login-related routes. Do not redirect from customer-home
    // or other application pages on every page load.
    const loginPaths = ["/login", "/customer-login"];
    if (!loginPaths.includes(currentPath)) {
        return;
    }

    if (!frappe.session || !frappe.session.user || frappe.session.user === "Guest") {
        return;
    }

    frappe.call({
        method: "vms_user.api.get_login_redirect",
        callback: function (response) {
            const route = response && response.message;
            if (typeof route !== "string" || !route.trim()) {
                return;
            }

            let targetPath;
            try {
                const targetUrl = new URL(route, window.location.origin);
                if (targetUrl.origin !== window.location.origin) {
                    console.error("Rejected external login redirect.");
                    return;
                }
                targetPath = normalizePath(targetUrl.pathname);
            } catch (error) {
                console.error("Invalid login redirect path:", error);
                return;
            }

            if (currentPath !== targetPath) {
                window.location.replace(targetPath);
            }
        },
        error: function (error) {
            console.error("Failed to retrieve login redirect:", error);
        }
    });
});