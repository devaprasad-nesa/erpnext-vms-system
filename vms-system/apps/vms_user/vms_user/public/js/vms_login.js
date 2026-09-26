/* ======================================================
   FILE: vms_login.js
   SECTION: Login and Role-Based Redirect JavaScript
   ====================================================== */

(() => {
    "use strict";

    const form          = document.getElementById("vms-login-form");
    const userInput     = document.getElementById("vms-login-user");
    const passwordInput = document.getElementById("vms-login-password");
    const loginButton   = document.getElementById("vms-login-button");
    const messageBox    = document.getElementById("vms-login-message");

    if (!form || !userInput || !passwordInput || !loginButton) return;

    // ── helpers ────────────────────────────────────────────────────────────

    const showMessage = (msg, type = "error") => {
        if (!messageBox) return;
        messageBox.textContent = msg;
        messageBox.className   = `vms-login-message ${type}`.trim();
    };

    const clearMessage = () => {
        if (messageBox) {
            messageBox.textContent = "";
            messageBox.className   = "vms-login-message";
        }
    };

    const setLoading = (loading) => {
        loginButton.disabled    = loading;
        loginButton.textContent = loading ? "Signing in..." : "Login";
    };

    /**
     * Return the current CSRF token from wherever Frappe stashed it.
     * Note: this token belongs to the *current* (pre-login) session.
     * After authenticate() creates a new session, the server issues a
     * new csrf_token; the JS variable still holds the old Guest token.
     * That is intentional — we only send this token for the login POST
     * itself; the destination lookup uses GET which is CSRF-exempt.
     */
    const getCsrfToken = () =>
        window.frappe?.csrf_token ||
        document.querySelector('meta[name="csrf-token"]')?.content ||
        "";

    // ── core functions ─────────────────────────────────────────────────────

    /**
     * POST credentials to Frappe's built-in /api/method/login.
     * Uses the pre-login (Guest) CSRF token which is valid at this point.
     */
    async function authenticate(username, password) {
        const body = new URLSearchParams({ usr: username, pwd: password });

        const response = await fetch("/api/method/login", {
            method:      "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type":        "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Frappe-CSRF-Token": getCsrfToken(),
            },
            body: body.toString(),
        });

        let result;
        try {
            result = await response.json();
        } catch {
            throw new Error("The server returned an invalid login response.");
        }

        // FIX: was `result.message === "Logged In" === false` — a broken
        // chained comparison that only sometimes worked by accident.
        // Rewritten as an explicit, unambiguous boolean check.
        if (!response.ok || result.exc || result.message !== "Logged In") {
            const serverMsg = result?.message;
            throw new Error(
                serverMsg && serverMsg !== "Logged In"
                    ? serverMsg
                    : "Login failed. Check your username and password."
            );
        }

        return result;
    }

    /**
     * Fetch the role-based dashboard URL for the freshly-authenticated user.
     *
     * FIX (root cause of broken role redirect after every successful login):
     *
     *   The user's original snippet used `frappe.call()` with `type: "GET"`,
     *   which has two separate fatal problems on website/portal pages:
     *
     *   (a) `frappe.call` is a Desk-only helper. It is NOT available on
     *       website pages, so calling it causes an immediate ReferenceError.
     *
     *   (b) `frappe.call` defaults to POST regardless of the `type` option
     *       on older SDK versions. POST is CSRF-validated against the
     *       *current* session token. After authenticate() the server has
     *       already issued a brand-new session with a NEW csrf_token, but
     *       the JS still holds the stale Guest-session token. The POST would
     *       therefore always be rejected with a CSRFTokenError — causing
     *       every login to fail at the destination-lookup step even though
     *       the authentication itself succeeded.
     *
     * Solution: use a plain `fetch()` with method: "GET".
     *   - Frappe only CSRF-validates UNSAFE_HTTP_METHODS (POST/PUT/PATCH/DELETE).
     *   - GET is fully exempt, so the stale Guest token is irrelevant.
     *   - get_login_destination is decorated with methods=["GET","POST"] and
     *     allow_guest=True; `require_login()` inside still rejects Guests
     *     server-side with PermissionError, so there is no security regression.
     */
    async function getLoginDestination() {
        const response = await fetch(
            "/api/method/vms_user.login_service.get_login_destination",
            {
                method:      "GET",
                credentials: "same-origin",
                headers: { "Accept": "application/json" },
            }
        );

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error("Unable to determine your dashboard (bad JSON).");
        }

        // Frappe wraps the return value in { "message": <return_value> }.
        if (!response.ok || !data?.message) {
            throw new Error("Unable to verify your dashboard access.");
        }

        return data.message; // { user, roles, redirect_url }
    }

    // ── submit handler ─────────────────────────────────────────────────────

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearMessage();

        const username = userInput.value.trim();
        const password = passwordInput.value;

        if (!username || !password) {
            showMessage("Enter both username and password.");
            return;
        }

        setLoading(true);

        try {
            await authenticate(username, password);

            const destination = await getLoginDestination();

            if (!destination?.redirect_url) {
                throw new Error("No dashboard is configured for your account.");
            }

            showMessage("Login successful. Redirecting...", "success");
            window.location.replace(destination.redirect_url);

        } catch (error) {
            showMessage(error.message || "Unable to log in. Please try again.");
            passwordInput.value = "";
            passwordInput.focus();

        } finally {
            setLoading(false);
        }
    });

})();
