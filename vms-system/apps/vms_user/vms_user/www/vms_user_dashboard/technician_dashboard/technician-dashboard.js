(() => {
    "use strict";

    /* =====================================================
       VMS TECHNICIAN DASHBOARD
       File:
       public/js/technician-dashboard.js

       Responsibilities:
       1. Authenticate technician
       2. Verify dashboard access
       3. Load inspections
       4. Load vehicles
       5. Load spare parts
       6. Create inspections
       7. Edit inspections
       8. Delete inspections
       9. Toggle inspection status
       10. Logout technician
       ===================================================== */


    /* =====================================================
       CONFIGURATION
       ===================================================== */

    const ROOT = "#vms-technician-dashboard";

    const ROUTE = "technician-dashboard";

    const LOGIN_URL = "/vms-login";

    const UNAUTHORIZED_URL = "/customer-home";


    /* =====================================================
       DOCTYPES
       ===================================================== */

    const DOCTYPES = {

        inspection: "vms vehicle inspection",

        vehicle: "vms vehicle registration",

        sparePart: "vms spare parts",

        user: "User"

    };


    /* =====================================================
       FIELD NAMES
       ===================================================== */

    const FIELD = {

        customer: "customer_name",

        vehicle: "vehicle_number",

        date: "inspection_date",

        issue: "issue",

        spareParts: "spare_parts",

        spareQuantity: "spare_part_quantity",

        technician: "technician",

        mechanic: "mechanic",

        labour: "labour_hour",

        inspected: "inspected"

    };


    /* =====================================================
       GLOBAL STATE
       ===================================================== */

    let inspections = [];

    let vehicles = [];

    let spareParts = [];

    let users = [];

    let customers = [];

    let currentUser = "";

    let initialized = false;


    /* =====================================================
       DOM HELPER
       ===================================================== */

    const $ = selector =>
        document.querySelector(`${ROOT} ${selector}`);


    /* =====================================================
       HTML ESCAPING
       Prevents HTML injection when rendering database
       values inside tables and dropdowns.
       ===================================================== */

    const escapeHTML = value =>
        String(value ?? "").replace(
            /[&<>"']/g,
            char => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            })[char]
        );


    /* =====================================================
       MESSAGE HANDLING
       ===================================================== */

    function showMessage(message, type = "success") {

        const el = $("#vms-message");

        if (!el) {
            return;
        }

        el.textContent = message;

        el.className = `vms-message ${type}`;

        el.hidden = false;
    }


    function hideMessage() {

        const el = $("#vms-message");

        if (!el) {
            return;
        }

        el.hidden = true;

        el.textContent = "";
    }


    /* =====================================================
       DATE HELPER
       ===================================================== */

    function today() {

        const d = new Date();

        return [
            d.getFullYear(),

            String(d.getMonth() + 1).padStart(2, "0"),

            String(d.getDate()).padStart(2, "0")

        ].join("-");
    }


    /* =====================================================
       DATE FORMATTER
       ===================================================== */

    function formatDate(value) {

        return value
            ? escapeHTML(String(value).slice(0, 10))
            : "-";
    }


    /* =====================================================
       NUMBER FORMATTER
       ===================================================== */

    function formatNumber(value) {

        const n = Number(value || 0);

        return Number.isFinite(n)
            ? String(n)
            : "0";
    }


    /* =====================================================
       BUTTON LOADING STATE
       ===================================================== */

    function setLoading(
        button,
        loading,
        text = "Saving..."
    ) {

        if (!button) {
            return;
        }

        if (loading) {

            button.dataset.originalText =
                button.textContent;

            button.textContent = text;

            button.disabled = true;

        } else {

            button.textContent =
                button.dataset.originalText ||
                button.textContent;

            delete button.dataset.originalText;

            button.disabled = false;
        }
    }


    /* =====================================================
       SERVER MESSAGE PARSER
       ===================================================== */

    function parseServerMessages(value) {

        if (!value) {
            return "";
        }

        try {

            const parsed = JSON.parse(value);

            if (Array.isArray(parsed)) {

                return parsed
                    .map(item => {

                        try {

                            const entry =
                                typeof item === "string"
                                    ? JSON.parse(item)
                                    : item;

                            return entry.message || entry;

                        } catch {

                            return item;
                        }

                    })
                    .join("\n");
            }

            return parsed.message || String(value);

        } catch {

            return String(value);
        }
    }


    /* =====================================================
       CSRF TOKEN
       ===================================================== */

    function getCsrfToken() {

        /*
         * First use the token exposed by Frappe.
         */
        if (window.frappe?.csrf_token) {

            return window.frappe.csrf_token;
        }


        /*
         * Otherwise try the browser cookie.
         */
        const cookie = document.cookie
            .split("; ")
            .find(
                item =>
                    item.startsWith("csrf_token=")
            );


        if (cookie) {

            return decodeURIComponent(
                cookie.substring(
                    "csrf_token=".length
                )
            );
        }


        /*
         * Finally check the HTML meta tag.
         */
        return document.querySelector(
            'meta[name="csrf-token"]'
        )?.content || "";
    }


    /* =====================================================
       GENERIC FRAPPE API CALL
       ===================================================== */

    async function apiCall(
        method,
        args = {},
        httpMethod = "POST"
    ) {

        const options = {

            method: httpMethod,

            credentials: "same-origin",

            headers: {

                "Accept": "application/json"

            }

        };


        let url =
            "/api/method/" + method;


        /* -------------------------------------------------
           POST / PUT / DELETE STYLE REQUEST
           ------------------------------------------------- */

        if (httpMethod !== "GET") {

            options.headers[
                "Content-Type"
            ] = "application/json";


            options.headers[
                "X-Frappe-CSRF-Token"
            ] = getCsrfToken();


            options.body =
                JSON.stringify(args);

        }


        /* -------------------------------------------------
           GET REQUEST
           ------------------------------------------------- */

        else if (
            args &&
            Object.keys(args).length > 0
        ) {

            const params =
                new URLSearchParams();


            for (
                const [key, val]
                of Object.entries(args)
            ) {

                if (
                    val !== undefined &&
                    val !== null
                ) {

                    params.append(
                        key,

                        typeof val === "object"
                            ? JSON.stringify(val)
                            : val
                    );
                }
            }


            const qs =
                params.toString();


            if (qs) {

                url += "?" + qs;
            }
        }


        /* -------------------------------------------------
           SEND REQUEST
           ------------------------------------------------- */

        let response;


        try {

            response = await fetch(
                url,
                options
            );

        } catch (error) {

            console.error(
                "[VMS API NETWORK ERROR]",
                {
                    method,
                    error
                }
            );


            throw new Error(
                `Network error calling ${method}: ${error.message}`
            );
        }


        /* -------------------------------------------------
           PARSE RESPONSE
           ------------------------------------------------- */

        let data;


        try {

            data =
                await response.json();

        } catch {

            const error =
                new Error(
                    `${method} returned non-JSON data. HTTP ${response.status}`
                );


            console.error(
                "[VMS API INVALID RESPONSE]",
                error
            );


            throw error;
        }


        /* -------------------------------------------------
           CHECK API FAILURE
           ------------------------------------------------- */

        const failed =
            !response.ok ||
            Boolean(data?.exc) ||
            Boolean(data?.exception);


        if (failed) {

            const serverMessage =
                parseServerMessages(
                    data?._server_messages
                );


            const message =
                serverMessage ||
                data?.message ||
                data?.exception ||
                data?.exc ||
                response.statusText ||
                "Unknown API error";


            console.error(
                "[VMS API ERROR]",
                {
                    method,
                    status: response.status,
                    statusText:
                        response.statusText,
                    message,
                    exception:
                        data?.exception,
                    exc:
                        data?.exc,
                    response:
                        data
                }
            );


            throw new Error(
                `${method} failed (HTTP ${response.status}): ${message}`
            );
        }


        return data?.message;
    }


    /* =====================================================
       FRAPPE CLIENT METHODS
       ===================================================== */

    const getList =
        (
            doctype,
            fields,
            filters = []
        ) =>
            apiCall(
                "frappe.client.get_list",
                {
                    doctype,
                    fields,
                    filters,
                    limit_page_length: 500
                }
            );


    const getDocument =
        (doctype, name) =>
            apiCall(
                "frappe.client.get",
                {
                    doctype,
                    name
                }
            );


    const insertDocument =
        doc =>
            apiCall(
                "frappe.client.insert",
                {
                    doc
                }
            );


    const saveDocument =
        doc =>
            apiCall(
                "frappe.client.save",
                {
                    doc
                }
            );


    const deleteDocument =
        (doctype, name) =>
            apiCall(
                "frappe.client.delete",
                {
                    doctype,
                    name
                }
            );


    /* =====================================================
       SESSION
       ===================================================== */

    async function getSessionUser() {

        /*
         * Ask the backend who is currently logged in.
         */
        const result =
            await apiCall(
                "vms_user.login_service.get_logged_user",
                {},
                "GET"
            );


        /*
         * Guest users are not allowed.
         */
        if (
            !result?.is_authenticated ||
            !result?.user ||
            result.user === "Guest"
        ) {

            window.location.replace(
                LOGIN_URL
            );

            return "";
        }


        return result.user;
    }


    /* =====================================================
       DASHBOARD ACCESS CHECK
       ===================================================== */

    async function verifyDashboardAccess() {

        const result =
            await apiCall(
                "vms_user.login_service.check_dashboard_access",
                {
                    route: ROUTE
                }
            );


        return Boolean(
            result?.allowed
        );
    }


    /* =====================================================
       DROPDOWN HELPER
       ===================================================== */

    function fillDropdown(
        selector,
        records,
        placeholder,
        labelFn,
        valueFn = record => record.name
    ) {

        const select =
            $(selector);


        if (!select) {
            return;
        }


        const previousValue =
            select.value;


        select.replaceChildren();


        const option =
            document.createElement(
                "option"
            );


        option.value = "";

        option.textContent =
            placeholder;


        select.appendChild(
            option
        );


        records.forEach(record => {

            const item =
                document.createElement(
                    "option"
                );


            item.value =
                valueFn(record);


            item.textContent =
                labelFn(record);


            select.appendChild(
                item
            );
        });


        if (
            records.some(
                record =>
                    valueFn(record) ===
                    previousValue
            )
        ) {

            select.value =
                previousValue;
        }
    }


    /* =====================================================
       VEHICLE DROPDOWN
       ===================================================== */

    function populateVehicleDropdown() {

        fillDropdown(

            "#inspection-vehicle",

            vehicles,

            "Select vehicle",

            vehicle =>

                vehicle.name +

                (
                    vehicle.owner_name
                        ? ` — ${vehicle.owner_name}`
                        : ""
                )
        );


        const customerMap =
            new Map();


        (customers || [])
            .forEach(c => {

                customerMap.set(

                    c.name,

                    c.full_name
                        ? `${c.full_name} (${c.name})`
                        : c.name
                );
            });


        vehicles.forEach(v => {

            if (
                v.owner_name &&
                !customerMap.has(
                    v.owner_name
                )
            ) {

                customerMap.set(
                    v.owner_name,
                    v.owner_name
                );
            }
        });


        const customerOptions =
            Array.from(
                customerMap.entries()
            )
                .map(
                    ([name, label]) => ({
                        name,
                        label
                    })
                );


        fillDropdown(

            "#inspection-customer",

            customerOptions,

            "Select customer",

            customer =>
                customer.label,

            customer =>
                customer.name
        );
    }


    /* =====================================================
       SPARE PART DROPDOWNS
       ===================================================== */

    function populateSparePartDropdowns() {

        fillDropdown(

            "#inspection-spare-parts",

            spareParts,

            "Select spare part",

            part =>
                part.part_name
                    ? `${part.part_name} (${part.name})`
                    : part.name
        );


        fillDropdown(

            "#inspection-spare-quantity",

            spareParts,

            "Select quantity record",

            part =>
                `${part.name} — Quantity: ${part.quantity ?? "-"}`
        );
    }


    /* =====================================================
       MECHANIC DROPDOWN
       ===================================================== */

    function populateMechanicDropdown() {

        /*
         * User records are not automatically mechanics.
         *
         * The backend should ideally return only users
         * who have permission to act as mechanics.
         */
        fillDropdown(

            "#inspection-mechanic",

            users,

            "Select mechanic",

            user =>
                user.full_name
                    ? `${user.full_name} (${user.name})`
                    : user.name
        );
    }


    /* =====================================================
       LOAD DASHBOARD DATA
       ===================================================== */

    async function loadDashboard() {

        hideMessage();


        try {

            const data =
                await apiCall(
                    "vms_inspection.api.get_dashboard_data",
                    {},
                    "GET"
                );


            vehicles =
                data.vehicles || [];


            spareParts =
                data.spare_parts || [];


            users =
                data.users || [];


            customers =
                data.customers || [];


            inspections =
                data.inspections || [];


            populateVehicleDropdown();

            populateSparePartDropdowns();

            populateMechanicDropdown();

            renderSpareParts();

            renderInspections();


        } catch (error) {

            console.error(
                "[VMS DASHBOARD LOAD FAILURE]",
                error
            );


            showMessage(
                "Dashboard load failed: " +
                error.message,

                "error"
            );
        }


        const currentUserElement =
            $("#vms-current-user");


        if (currentUserElement) {

            currentUserElement.textContent =
                currentUser;
        }


        const technicianElement =
            $("#inspection-technician");


        if (technicianElement) {

            technicianElement.value =
                currentUser;
        }
    }


    /* =====================================================
       INSPECTION TABLE
       ===================================================== */

    function renderInspections() {

        const tbody =
            $("#vms-inspection-table");


        if (!tbody) {
            return;
        }


        if (!inspections.length) {

            tbody.innerHTML = `

                <tr>

                    <td
                        colspan="9"
                        class="vms-empty"
                    >
                        No inspection records found.
                    </td>

                </tr>

            `;

            return;
        }


        tbody.innerHTML =
            inspections
                .map(item => {

                    const completed =
                        Boolean(
                            Number(
                                item[
                                FIELD.inspected
                                ]
                            )
                        );


                    return `

                        <tr>

                            <td>
                                ${escapeHTML(item.name)}
                            </td>


                            <td>
                                ${escapeHTML(
                        item[
                        FIELD.customer
                        ] || "-"
                    )}
                            </td>


                            <td>
                                ${escapeHTML(
                        item[
                        FIELD.vehicle
                        ] || "-"
                    )}
                            </td>


                            <td>
                                ${formatDate(
                        item[
                        FIELD.date
                        ]
                    )}
                            </td>


                            <td class="vms-issue-cell">
                                ${escapeHTML(
                        item[
                        FIELD.issue
                        ] || "-"
                    )}
                            </td>


                            <td>
                                ${escapeHTML(
                        item[
                        FIELD.technician
                        ] || "-"
                    )}
                            </td>


                            <td>
                                ${formatNumber(
                        item[
                        FIELD.labour
                        ]
                    )}
                            </td>


                            <td>

                                <button
                                    type="button"
                                    class="vms-status ${completed
                            ? "done"
                            : "pending"
                        }"
                                    data-action="toggle-status"
                                    data-name="${escapeHTML(
                            item.name
                        )}"
                                    data-status="${completed
                            ? 1
                            : 0
                        }"
                                    title="Click to toggle status"
                                >

                                    ${completed
                            ? "Completed"
                            : "Pending"
                        }

                                </button>

                            </td>


                            <td>

                                <div class="vms-actions">

                                    <button
                                        type="button"
                                        class="vms-btn vms-btn-secondary"
                                        data-action="edit-inspection"
                                        data-name="${escapeHTML(
                            item.name
                        )}"
                                    >
                                        Edit
                                    </button>


                                    <button
                                        type="button"
                                        class="vms-btn vms-btn-danger"
                                        data-action="delete-inspection"
                                        data-name="${escapeHTML(
                            item.name
                        )}"
                                    >
                                        Delete
                                    </button>

                                </div>

                            </td>

                        </tr>

                    `;

                })
                .join("");
    }


    /* =====================================================
       LOAD SPARE PARTS
       ===================================================== */

    async function loadSpareParts() {

        try {

            const data =
                await apiCall(
                    "vms_inspection.api.get_spare_parts",
                    {},
                    "GET"
                );


            spareParts =
                data || [];


            populateSparePartDropdowns();

            renderSpareParts();


        } catch (error) {

            console.error(
                "[VMS SPARE PARTS LOAD FAILURE]",
                error
            );


            showMessage(
                "Failed to load spare parts: " +
                error.message,

                "error"
            );
        }
    }


    /* =====================================================
       SPARE PART TABLE
       ===================================================== */

    function renderSpareParts() {

        const tbody =
            $("#vms-spare-part-table");


        if (!tbody) {
            return;
        }


        if (!spareParts.length) {

            tbody.innerHTML = `

                <tr>

                    <td
                        colspan="4"
                        class="vms-empty"
                    >
                        No spare-parts records found.
                    </td>

                </tr>

            `;

            return;
        }


        tbody.innerHTML =
            spareParts
                .map(
                    part => `

                        <tr>

                            <td>
                                ${escapeHTML(
                        part.name
                    )}
                            </td>


                            <td>
                                ${escapeHTML(
                        part.part_name ||
                        "-"
                    )}
                            </td>


                            <td>
                                ${escapeHTML(
                        part.quantity ??
                        "-"
                    )}
                            </td>


                            <td>
                                ${escapeHTML(
                        part.cost ??
                        "-"
                    )}
                            </td>

                        </tr>

                    `
                )
                .join("");
    }


    /* =====================================================
       RESET INSPECTION FORM
       ===================================================== */

    function resetInspectionForm() {

        const form =
            $("#vms-inspection-form");


        if (!form) {
            return;
        }


        form.reset();


        $("#inspection-name").value = "";

        $("#inspection-date").value =
            today();

        $("#inspection-technician").value =
            currentUser;

        $("#inspection-labour").value =
            "0";

        $("#inspection-inspected").checked =
            false;


        $("#vms-inspection-form-title")
            .textContent =
            "Create Vehicle Inspection";
    }


    /* =====================================================
       OPEN NEW INSPECTION FORM
       ===================================================== */

    function openNewInspection() {

        resetInspectionForm();


        $("#vms-inspection-form").hidden =
            false;


        $("#vms-inspection-form")
            .scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
    }


    /* =====================================================
       EDIT INSPECTION
       ===================================================== */

    async function editInspection(name) {

        try {

            const item =
                await apiCall(
                    "vms_inspection.api.get_inspection_details",
                    {
                        name
                    },
                    "GET"
                );


            /*
             * A technician should only edit their own
             * inspection records.
             */
            if (
                item[FIELD.technician] &&
                currentUser &&
                item[FIELD.technician] !==
                currentUser &&
                currentUser.toLowerCase() !==
                "administrator"
            ) {

                throw new Error(
                    "You cannot edit another technician's inspection."
                );
            }


            resetInspectionForm();


            $("#inspection-name").value =
                item.name;


            $("#inspection-customer").value =
                item[FIELD.customer] || "";


            $("#inspection-vehicle").value =
                item[FIELD.vehicle] || "";


            $("#inspection-date").value =
                item[FIELD.date] || "";


            $("#inspection-issue").value =
                item[FIELD.issue] || "";


            $("#inspection-spare-parts").value =
                item[FIELD.spareParts] || "";


            $("#inspection-spare-quantity").value =
                item[FIELD.spareQuantity] || "";


            $("#inspection-mechanic").value =
                item[FIELD.mechanic] || "";


            $("#inspection-labour").value =
                item[FIELD.labour] || 0;


            $("#inspection-inspected").checked =
                Boolean(
                    Number(
                        item[FIELD.inspected]
                    )
                );


            $("#vms-inspection-form-title")
                .textContent =
                "Edit Vehicle Inspection";


            $("#vms-inspection-form").hidden =
                false;


            $("#vms-inspection-form")
                .scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });


        } catch (error) {

            showMessage(
                error.message,
                "error"
            );
        }
    }


    /* =====================================================
       GET INSPECTION FORM DATA
       ===================================================== */

    function getInspectionFormData() {

        return {

            doctype:
                DOCTYPES.inspection,


            [FIELD.customer]:
                $("#inspection-customer")
                    .value || null,


            [FIELD.vehicle]:
                $("#inspection-vehicle")
                    .value,


            [FIELD.date]:
                $("#inspection-date")
                    .value,


            [FIELD.issue]:
                $("#inspection-issue")
                    .value
                    .trim() ||
                "General Inspection / Routine Checkup",


            [FIELD.spareParts]:
                $("#inspection-spare-parts")
                    .value || null,


            [FIELD.spareQuantity]:
                $("#inspection-spare-quantity")
                    .value || null,


            /*
             * Server must independently validate
             * technician ownership.
             */
            [FIELD.technician]:
                currentUser,


            [FIELD.mechanic]:
                $("#inspection-mechanic")
                    .value || null,


            [FIELD.labour]:
                Number(
                    $("#inspection-labour")
                        .value || 0
                ),


            [FIELD.inspected]:
                $("#inspection-inspected")
                    .checked
                    ? 1
                    : 0
        };
    }


    /* =====================================================
       SAVE INSPECTION
       ===================================================== */

    async function saveInspection(event) {

        event.preventDefault();


        const button =
            event.submitter ||
            $("#vms-inspection-form button[type='submit']");


        setLoading(
            button,
            true,
            "Saving..."
        );


        try {

            const name =
                $("#inspection-name")
                    .value;


            const data =
                getInspectionFormData();


            if (!data[FIELD.vehicle]) {

                throw new Error(
                    "Please select a vehicle."
                );
            }


            if (!data[FIELD.date]) {

                throw new Error(
                    "Please select the inspection date."
                );
            }


            if (data[FIELD.labour] < 0) {

                throw new Error(
                    "Labour hours cannot be negative."
                );
            }


            /* ------------------------------------------------
               UPDATE EXISTING RECORD
               ------------------------------------------------ */

            if (name) {

                await apiCall(
                    "vms_inspection.api.update_inspection",
                    {
                        name,
                        data
                    }
                );


            }

            /* ------------------------------------------------
               CREATE NEW RECORD
               ------------------------------------------------ */

            else {

                await apiCall(
                    "vms_inspection.api.create_inspection",
                    {
                        data
                    }
                );
            }


            $("#vms-inspection-form")
                .hidden = true;


            resetInspectionForm();


            showMessage(

                name
                    ? "Inspection updated successfully."
                    : "Inspection created successfully."

            );


            await loadDashboard();


        } catch (error) {

            console.error(
                "[VMS SAVE INSPECTION ERROR]",
                error
            );


            showMessage(
                error.message,
                "error"
            );


        } finally {

            setLoading(
                button,
                false
            );
        }
    }


    /* =====================================================
       DELETE INSPECTION
       ===================================================== */

    async function deleteInspection(name) {

        if (
            !window.confirm(
                "Delete this inspection record?"
            )
        ) {
            return;
        }


        try {

            await apiCall(
                "vms_inspection.api.delete_inspection",
                {
                    name
                }
            );


            showMessage(
                "Inspection deleted successfully."
            );


            await loadDashboard();


        } catch (error) {

            showMessage(
                error.message,
                "error"
            );
        }
    }


    /* =====================================================
       TOGGLE INSPECTION STATUS
       ===================================================== */

    async function toggleInspectionStatus(
        name,
        currentStatus
    ) {

        try {

            const nextStatus =
                (
                    currentStatus === "1" ||
                    currentStatus === 1
                )
                    ? 0
                    : 1;


            await apiCall(
                "vms_inspection.api.update_inspection",
                {
                    name,

                    data: {

                        inspected:
                            nextStatus
                    }
                }
            );


            showMessage(

                `Inspection marked as ${nextStatus
                    ? "Completed"
                    : "Pending"
                }.`
            );


            await loadDashboard();


        } catch (error) {

            showMessage(
                error.message,
                "error"
            );
        }
    }


    /* =====================================================
       TAB SWITCHING
       ===================================================== */

    function switchTab(tabName) {

        document
            .querySelectorAll(
                `${ROOT} .vms-tab`
            )
            .forEach(button => {

                button.classList.toggle(
                    "active",

                    button.dataset.tab ===
                    tabName
                );
            });


        const inspectionsTab =
            $("#tab-inspections");


        const sparePartsTab =
            $("#tab-spare-parts");


        if (inspectionsTab) {

            inspectionsTab.hidden =
                tabName !== "inspections";
        }


        if (sparePartsTab) {

            sparePartsTab.hidden =
                tabName !== "spare-parts";
        }
    }


    /* =====================================================
       LOGOUT
       ===================================================== */

    async function logout() {

        const logoutButton =
            $("#vms-logout");


        if (logoutButton) {

            logoutButton.disabled =
                true;

            logoutButton.dataset.originalText =
                logoutButton.innerHTML;

            logoutButton.innerHTML =
                "<span>⏳</span><span>Logging out...</span>";
        }


        try {

            /*
             * Frappe's logout endpoint destroys the
             * authenticated session on the server.
             */
            await apiCall(
                "logout",
                {},
                "POST"
            );


        } catch (error) {

            /*
             * Even if the server returns an error,
             * redirect the browser to the login page.
             *
             * This prevents the user from remaining
             * on the technician dashboard.
             */
            console.error(
                "[VMS LOGOUT ERROR]",
                error
            );

        } finally {

            /*
             * Force navigation to the VMS login page.
             */
            window.location.replace(
                LOGIN_URL
            );
        }
    }


    /* =====================================================
       EVENT BINDING
       ===================================================== */

    function bindEvents() {

        /* -------------------------------------------------
           TABS
           ------------------------------------------------- */

        document
            .querySelectorAll(
                `${ROOT} .vms-tab`
            )
            .forEach(button => {

                button.addEventListener(
                    "click",
                    () => {

                        switchTab(
                            button.dataset.tab
                        );
                    }
                );
            });


        /* -------------------------------------------------
           NEW INSPECTION
           ------------------------------------------------- */

        const newInspectionButton =
            $("#vms-new-inspection");


        if (newInspectionButton) {

            newInspectionButton.addEventListener(
                "click",
                openNewInspection
            );
        }


        /* -------------------------------------------------
           CANCEL INSPECTION
           ------------------------------------------------- */

        const cancelButton =
            $("#vms-cancel-inspection");


        if (cancelButton) {

            cancelButton.addEventListener(
                "click",
                () => {

                    $("#vms-inspection-form")
                        .hidden = true;

                    resetInspectionForm();
                }
            );
        }


        /* -------------------------------------------------
           INSPECTION FORM SUBMIT
           ------------------------------------------------- */

        const inspectionForm =
            $("#vms-inspection-form");


        if (inspectionForm) {

            inspectionForm.addEventListener(
                "submit",
                saveInspection
            );
        }


        /* -------------------------------------------------
           INSPECTION TABLE ACTIONS
           ------------------------------------------------- */

        const inspectionTable =
            $("#vms-inspection-table");


        if (inspectionTable) {

            inspectionTable.addEventListener(
                "click",
                event => {

                    const button =
                        event.target.closest(
                            "[data-action]"
                        );


                    if (!button) {
                        return;
                    }


                    const {
                        action,
                        name
                    } = button.dataset;


                    if (
                        action ===
                        "edit-inspection"
                    ) {

                        editInspection(
                            name
                        );
                    }


                    if (
                        action ===
                        "delete-inspection"
                    ) {

                        deleteInspection(
                            name
                        );
                    }


                    if (
                        action ===
                        "toggle-status"
                    ) {

                        toggleInspectionStatus(
                            name,
                            button.dataset.status
                        );
                    }
                }
            );
        }


        /* -------------------------------------------------
           CHECKBOX
           ------------------------------------------------- */

        const checkboxField =
            document.querySelector(
                `${ROOT} .vms-checkbox-field`
            );


        if (checkboxField) {

            checkboxField.addEventListener(
                "click",
                event => {

                    if (
                        event.target.tagName !==
                        "INPUT" &&
                        event.target.tagName !==
                        "LABEL"
                    ) {

                        const checkbox =
                            $("#inspection-inspected");


                        if (checkbox) {

                            checkbox.checked =
                                !checkbox.checked;
                        }
                    }
                }
            );
        }


        /* -------------------------------------------------
           REFRESH SPARE PARTS
           ------------------------------------------------- */

        const refreshSparePartsButton =
            $("#vms-refresh-spare-parts");


        if (refreshSparePartsButton) {

            refreshSparePartsButton.addEventListener(
                "click",
                loadSpareParts
            );
        }


        /* -------------------------------------------------
           VEHICLE CHANGE
           ------------------------------------------------- */

        const vehicleSelect =
            $("#inspection-vehicle");


        if (vehicleSelect) {

            vehicleSelect.addEventListener(
                "change",
                () => {

                    const vehicle =
                        vehicles.find(
                            item =>
                                item.name ===
                                vehicleSelect.value
                        );


                    if (
                        vehicle?.owner_name
                    ) {

                        $("#inspection-customer")
                            .value =
                            vehicle.owner_name;
                    }
                }
            );
        }


        /* -------------------------------------------------
           LOGOUT
           ------------------------------------------------- */

        const logoutButton =
            $("#vms-logout");


        if (logoutButton) {

            logoutButton.addEventListener(
                "click",
                logout
            );
        }
    }


    /* =====================================================
       INITIALIZE DASHBOARD
       ===================================================== */

    async function initializeDashboard() {

        if (initialized) {
            return;
        }


        const root =
            document.querySelector(
                ROOT
            );


        if (!root) {
            return;
        }


        try {

            /* ---------------------------------------------
               STEP 1:
               Get authenticated Frappe user
               --------------------------------------------- */

            currentUser =
                await getSessionUser();


            if (!currentUser) {
                return;
            }


            /* ---------------------------------------------
               STEP 2:
               Verify technician dashboard permission
               --------------------------------------------- */

            const allowed =
                await verifyDashboardAccess();


            if (!allowed) {

                window.location.replace(
                    UNAUTHORIZED_URL
                );

                return;
            }


            /* ---------------------------------------------
               STEP 3:
               Dashboard is authorized
               --------------------------------------------- */

            initialized = true;


            /* ---------------------------------------------
               STEP 4:
               Bind all UI events
               --------------------------------------------- */

            bindEvents();


            /* ---------------------------------------------
               STEP 5:
               Load dashboard data
               --------------------------------------------- */

            await loadDashboard();


        } catch (error) {

            console.error(
                "[VMS DASHBOARD INITIALIZATION ERROR]",
                error
            );


            showMessage(
                error.message,
                "error"
            );
        }
    }


    /* =====================================================
       START DASHBOARD
       ===================================================== */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initializeDashboard,
            {
                once: true
            }
        );

    } else {

        initializeDashboard();
    }

})();