frappe.ready(() => {

    "use strict";


    /* =========================================================
       ROOT
       ========================================================= */

    const root =
        document.getElementById(
            "vms-account-invoice-page"
        );


    if (!root) {
        return;
    }


    /* =========================================================
       DOM HELPER
       ========================================================= */

    const $ = id =>
        document.getElementById(id);


    /* =========================================================
       STATE
       ========================================================= */

    let editMode = false;

    let currentInvoice = null;


    /* =========================================================
       URL PARAMETERS
       ========================================================= */

    const params =
        new URLSearchParams(
            window.location.search
        );


    const invoiceName =
        params.get("invoice");


    const inspectionName =
        params.get("inspection");


    /* =========================================================
       HTML ESCAPE
       ========================================================= */

    function escapeHTML(value) {

        return frappe.utils.escape_html(
            String(value ?? "")
        );

    }


    /* =========================================================
       MESSAGE
       ========================================================= */

    function showMessage(
        message,
        type = ""
    ) {

        const element =
            $("invoice-message");


        if (!element) {
            return;
        }


        element.textContent =
            message || "";


        element.className =
            "invoice-message";


        if (type === "success") {

            element.classList.add(
                "message-success"
            );

        }


        if (type === "error") {

            element.classList.add(
                "message-error"
            );

        }

    }


    /* =========================================================
       SAVE STATUS
       ========================================================= */

    function setSaveStatus(message) {

        const element =
            $("save-status");


        if (element) {

            element.textContent =
                message || "";

        }

    }


    /* =========================================================
       SET FIELD VALUE
       ========================================================= */

    function setValue(
        id,
        value
    ) {

        const element =
            $(id);


        if (!element) {
            return;
        }


        element.value =
            value ?? "";

    }


    /* =========================================================
       GET FIELD VALUE
       ========================================================= */

    function getValue(id) {

        const element =
            $(id);


        if (!element) {
            return "";
        }


        return element.value;

    }


    /* =========================================================
       DATE
       ========================================================= */

    function getToday() {

        const date =
            new Date();


        const year =
            date.getFullYear();


        const month =
            String(
                date.getMonth() + 1
            ).padStart(2, "0");


        const day =
            String(
                date.getDate()
            ).padStart(2, "0");


        return (
            `${year}-${month}-${day}`
        );

    }


    /* =========================================================
       CREATE MODE
       ========================================================= */

    function initializeCreateMode() {

        editMode = false;


        $("invoice-page-mode").textContent =
            "Create Invoice";


        $("invoice-form-title").textContent =
            "Create Invoice";


        $("invoice-form-description").textContent =
            "Create a new invoice from the vehicle inspection details.";


        $("invoice-mode-badge").textContent =
            "New";


        $("invoice-save-btn").textContent =
            "Create Invoice";


        $("invoice-status-container").innerHTML =
            "";


        setValue(
            "invoice-date",
            getToday()
        );


        if (inspectionName) {

            setValue(
                "inspection-name",
                inspectionName
            );


            loadInspection(
                inspectionName
            );

        }

    }


    /* =========================================================
       EDIT MODE
       ========================================================= */

    function initializeEditMode() {

        editMode = true;


        $("invoice-page-mode").textContent =
            "Edit Invoice";


        $("invoice-form-title").textContent =
            "Edit Invoice";


        $("invoice-form-description").textContent =
            `Update invoice ${invoiceName}.`;


        $("invoice-mode-badge").textContent =
            "Edit";


        $("invoice-save-btn").textContent =
            "Update Invoice";


        loadInvoice(
            invoiceName
        );

    }


    /* =========================================================
       LOAD EXISTING INVOICE
       ========================================================= */

    async function loadInvoice(name) {

        showMessage(
            "Loading invoice..."
        );


        setSaveStatus(
            "Loading..."
        );


        $("invoice-save-btn").disabled =
            true;


        try {

            const response =
                await frappe.call({

                    method:
                        "vms_account.api.get_customer_invoice_details",

                    args: {
                        invoice_name: name
                    }

                });


            if (
                !response ||
                !response.message
            ) {

                throw new Error(
                    "Invoice could not be found."
                );

            }


            currentInvoice =
                response.message;


            populateInvoice(
                currentInvoice
            );


            showMessage("");


            setSaveStatus("");


        } catch (error) {

            console.error(
                "Unable to load invoice:",
                error
            );


            showMessage(
                "Unable to load invoice. Check the invoice ID and permissions.",
                "error"
            );


            setSaveStatus(
                "Unable to load"
            );

        } finally {

            $("invoice-save-btn").disabled =
                false;

        }

    }


    /* =========================================================
       POPULATE INVOICE
       ========================================================= */

    function populateInvoice(
        invoice
    ) {

        setValue(
            "invoice-name",
            invoice.name
        );


        setValue(
            "inspection-name",
            invoice.inspection ||
            invoice.inspection_name
        );


        setValue(
            "customer-name",
            invoice.customer_name
        );


        setValue(
            "vehicle-number",
            invoice.vehicle_number
        );


        setValue(
            "invoice-date",
            invoice.invoice_date
        );


        setValue(
            "audited",
            invoice.audited
                ? "1"
                : "0"
        );


        setValue(
            "spare-parts",
            invoice.spare_parts
        );


        setValue(
            "spare-part-quantity",
            invoice.spare_part_quantity
        );


        setValue(
            "part-cost",
            invoice.part_cost
        );


        setValue(
            "labour-hour",
            invoice.labour_hour
        );


        setValue(
            "labour-cost",
            invoice.labour_cost
        );


        setValue(
            "total-bill",
            invoice.total_bill
        );


        setValue(
            "service-description",
            invoice.service_description
        );


        renderInvoiceStatus(
            invoice
        );

    }


    /* =========================================================
       INVOICE STATUS
       ========================================================= */

    function renderInvoiceStatus(
        invoice
    ) {

        const container =
            $("invoice-status-container");


        if (!container) {
            return;
        }


        const paid =
            !!invoice.audited;


        container.innerHTML = `

            <span class="invoice-status ${paid
                ? "status-paid"
                : "status-pending"
            }">

                ${paid
                ? "Paid"
                : "Pending"
            }

            </span>

        `;

    }


    /* =========================================================
       LOAD INSPECTION
       ========================================================= */

    async function loadInspection(
        name
    ) {

        showMessage(
            "Loading inspection details..."
        );


        try {

            const response =
                await frappe.call({

                    method:
                        "vms_inspection.api.get_inspection_details",

                    args: {
                        name: name
                    }

                });


            if (
                response &&
                response.message
            ) {

                populateInspection(
                    response.message
                );

            }


            showMessage("");


        } catch (error) {

            console.error(
                "Unable to load inspection:",
                error
            );


            showMessage(
                "Unable to load inspection details.",
                "error"
            );

        }

    }


    /* =========================================================
       POPULATE INSPECTION
       ========================================================= */

    function populateInspection(
        inspection
    ) {

        setValue(
            "inspection-name",
            inspection.name
        );


        setValue(
            "customer-name",
            inspection.customer_name
        );


        setValue(
            "vehicle-number",
            inspection.vehicle_number ||
            inspection.vehicle
        );


        setValue(
            "spare-parts",
            inspection.spare_parts
        );


        const sq = parseFloat(inspection.spare_part_quantity);
        setValue(
            "spare-part-quantity",
            isNaN(sq) ? "" : sq
        );


        const pc = parseFloat(inspection.part_cost);
        setValue(
            "part-cost",
            isNaN(pc) ? "" : pc
        );


        const lh = parseFloat(inspection.labour_hour);
        setValue(
            "labour-hour",
            isNaN(lh) ? "" : lh
        );


        const lc = parseFloat(inspection.labour_cost);
        setValue(
            "labour-cost",
            isNaN(lc) ? "" : lc
        );


        setValue(
            "service-description",
            inspection.service_description ||
            inspection.issue_description
        );


        calculateTotal();

    }


    /* =========================================================
       CALCULATE TOTAL
       ========================================================= */

    function calculateTotal() {

        const partCost =
            Number(
                getValue("part-cost") || 0
            );


        const labourCost =
            Number(
                getValue("labour-cost") || 0
            );


        const total =
            partCost +
            labourCost;


        /*
         * Only automatically calculate the total when
         * the user is creating a new invoice or when
         * the total field is empty.
         *
         * This prevents an existing invoice total from
         * being unexpectedly overwritten while editing.
         */

        if (
            !editMode ||
            !getValue("total-bill")
        ) {

            setValue(
                "total-bill",
                total.toFixed(2)
            );

        }

    }


    /* =========================================================
       FORM DATA
       ========================================================= */

    function getFormData() {

        return {

            name:
                getValue(
                    "invoice-name"
                ),


            inspection:
                getValue(
                    "inspection-name"
                ),


            customer_name:
                getValue(
                    "customer-name"
                ),


            vehicle_number:
                getValue(
                    "vehicle-number"
                ),


            invoice_date:
                getValue(
                    "invoice-date"
                ),


            audited:
                getValue(
                    "audited"
                ) || "0",


            spare_parts:
                getValue(
                    "spare-parts"
                ),


            spare_part_quantity:
                getValue(
                    "spare-part-quantity"
                ) || 0,


            part_cost:
                getValue(
                    "part-cost"
                ) || 0,


            labour_hour:
                getValue(
                    "labour-hour"
                ) || 0,


            labour_cost:
                getValue(
                    "labour-cost"
                ) || 0,


            total_bill:
                getValue(
                    "total-bill"
                ) || 0,


            service_description:
                getValue(
                    "service-description"
                )

        };

    }


    /* =========================================================
       CREATE INVOICE
       ========================================================= */

    async function createInvoice(
        data
    ) {

        return frappe.call({

            method:
                "vms_account.api.create_invoice",

            args: {

                customer_name:
                    data.customer_name,

                vehicle_inspection:
                    data.inspection,

                invoice_date:
                    data.invoice_date,

                total_bill:
                    data.total_bill

            }

        });

    }


    /* =========================================================
       UPDATE INVOICE
       ========================================================= */

    async function updateInvoice(
        data
    ) {

        return frappe.call({

            method:
                "vms_account.api.update_invoice",

            args: {

                invoice_name:
                    invoiceName,

                total_bill:
                    data.total_bill,

                invoice_date:
                    data.invoice_date

            }

        });

    }


    /* =========================================================
       SAVE FORM
       ========================================================= */

    async function handleSubmit(
        event
    ) {

        event.preventDefault();


        const button =
            $("invoice-save-btn");


        const data =
            getFormData();


        /*
         * Basic frontend validation.
         */

        if (
            !data.customer_name
        ) {

            showMessage(
                "Customer name is required.",
                "error"
            );

            return;

        }


        if (
            !data.vehicle_number
        ) {

            showMessage(
                "Vehicle number is required.",
                "error"
            );

            return;

        }


        if (
            !data.invoice_date
        ) {

            showMessage(
                "Invoice date is required.",
                "error"
            );

            return;

        }


        button.disabled =
            true;


        root.classList.add(
            "invoice-loading"
        );


        showMessage(
            editMode
                ? "Updating invoice..."
                : "Creating invoice..."
        );


        setSaveStatus(
            editMode
                ? "Updating..."
                : "Creating..."
        );


        try {

            let response;


            if (editMode) {

                response =
                    await updateInvoice(
                        data
                    );

            } else {

                response =
                    await createInvoice(
                        data
                    );

            }


            if (
                !response ||
                !response.message ||
                !response.message.success
            ) {

                throw new Error(
                    response?.message?.message ||
                    "Invoice operation failed."
                );

            }


            const savedName =
                response.message.name ||
                invoiceName;


            console.log(
                "Invoice saved:",
                savedName
            );


            frappe.show_alert({

                message:
                    editMode
                        ? "Invoice updated successfully"
                        : "Invoice created successfully",

                indicator:
                    "green"

            });


            showMessage(
                editMode
                    ? "Invoice updated successfully."
                    : "Invoice created successfully.",
                "success"
            );


            setSaveStatus(
                "Saved successfully"
            );


            /*
             * Redirect back to Account Dashboard.
             */

            setTimeout(
                () => {

                    window.location.href =
                        "/account-dashboard";

                },
                700
            );


        } catch (error) {

            console.error(
                "Invoice operation failed:",
                error
            );


            showMessage(
                error.message ||
                "Unable to save invoice.",
                "error"
            );


            setSaveStatus(
                "Save failed"
            );


            frappe.show_alert({

                message:
                    error.message ||
                    "Unable to save invoice.",

                indicator:
                    "red"

            });

        } finally {

            button.disabled =
                false;


            root.classList.remove(
                "invoice-loading"
            );

        }

    }


    /* =========================================================
       BACK TO DASHBOARD
       ========================================================= */

    function goToDashboard() {

        window.location.href =
            "/account-dashboard";

    }


    /* =========================================================
       CALCULATION EVENTS
       ========================================================= */

    const partCost =
        $("part-cost");


    const labourCost =
        $("labour-cost");


    if (partCost) {

        partCost.addEventListener(
            "input",
            () => {

                if (!editMode) {

                    calculateTotal();

                }

            }
        );

    }


    if (labourCost) {

        labourCost.addEventListener(
            "input",
            () => {

                if (!editMode) {

                    calculateTotal();

                }

            }
        );

    }


    /* =========================================================
       FORM SUBMIT
       ========================================================= */

    const form =
        $("account-invoice-form");


    if (form) {

        form.addEventListener(
            "submit",
            handleSubmit
        );

    }


    /* =========================================================
       BACK BUTTON
       ========================================================= */

    const backButton =
        $("invoice-back-btn");


    if (backButton) {

        backButton.addEventListener(
            "click",
            goToDashboard
        );

    }


    /* =========================================================
       CANCEL BUTTON
       ========================================================= */

    const cancelButton =
        $("invoice-cancel-btn");


    if (cancelButton) {

        cancelButton.addEventListener(
            "click",
            goToDashboard
        );

    }


    /* =========================================================
       INITIALIZATION
       ========================================================= */

    if (invoiceName) {

        /*
         * URL:
         *
         * account-invoice?invoice=INV-00006
         *
         * means EDIT mode.
         */

        initializeEditMode();

    } else {

        /*
         * URL:
         *
         * account-invoice?inspection=INS-00001
         *
         * means CREATE mode.
         */

        initializeCreateMode();

    }

});