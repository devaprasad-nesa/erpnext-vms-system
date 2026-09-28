
frappe.ready(() => {
    const root = document.getElementById(
        "vms-account-dashboard"
    );

    if (!root) return;

    const $ = id => document.getElementById(id);

    const escapeHTML = value =>
        frappe.utils.escape_html(String(value ?? ""));

    const money = value =>
        "₹" + Number(value || 0).toLocaleString(
            "en-IN",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );

    function showMessage(message) {
        $("account-message").textContent = message;
    }

    function createButton(label, action, id) {
        return `
            <button
                class="vms-btn vms-btn-small"
                data-action="${action}"
                data-id="${escapeHTML(id)}">
                ${escapeHTML(label)}
            </button>
        `;
    }

    function renderInspections(rows) {
        const tbody = $("inspection-list");

        if (!rows.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8">
                        No released inspections available.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = rows.map(row => `
            <tr>
                <td>${escapeHTML(row.name)}</td>
                <td>${escapeHTML(row.customer_name)}</td>
                <td>${escapeHTML(row.vehicle_number)}</td>
                <td>${escapeHTML(row.spare_parts || "-")}</td>
                <td>${escapeHTML(
                    row.spare_part_quantity ?? "-"
                )}</td>
                <td>${escapeHTML(row.labour_hour ?? 0)}</td>
                <td>${money(row.part_cost)}</td>
                <td>
                    ${createButton(
                        "Create Invoice",
                        "create",
                        row.name
                    )}
                </td>
            </tr>
        `).join("");
    }

    function renderInvoices(rows) {
        const tbody = $("invoice-list");

        if (!rows.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7">No invoices found.</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = rows.map(row => `
            <tr>
                <td>${escapeHTML(row.name)}</td>
                <td>${escapeHTML(row.customer_name)}</td>
                <td>${escapeHTML(row.vehicle_number)}</td>
                <td>${escapeHTML(row.invoice_date || "-")}</td>
                <td>${money(row.total_bill)}</td>
                <td>
                    <span class="vms-status ${
                        row.payment
                            ? "vms-status-success"
                            : "vms-status-pending"
                    }">
                        ${row.payment ? "Enabled" : "Disabled"}
                    </span>
                </td>
                <td>
                    <span class="vms-status ${
                        row.audited
                            ? "vms-status-success"
                            : "vms-status-pending"
                    }">
                        ${row.audited ? "Paid" : "Pending"}
                    </span>
                </td>
                <td>
                    ${createButton(
                        "Open",
                        "open",
                        row.name
                    )}
                </td>
            </tr>
        `).join("");
    }

    function renderStats(inspections, invoices) {
        $("stat-inspections").textContent =
            inspections.length;

        $("stat-invoices").textContent =
            invoices.length;

        $("stat-audited").textContent =
            invoices.filter(row => !!row.audited).length;

        $("stat-pending").textContent =
            invoices.filter(row => !row.audited).length;
    }

    let currentInspectionPage = 1;
    let totalInspectionPages = 1;
    let currentInvoicePage = 1;
    let totalInvoicePages = 1;

    function updatePaginationControls() {
        const inspectEl = $("inspection-page-info");
        const inspectPrev = $("inspection-prev-btn");
        const inspectNext = $("inspection-next-btn");
        const showInspectPagination = totalInspectionPages > 1;

        if (inspectPrev) {
            inspectPrev.style.display = showInspectPagination ? "" : "none";
            inspectPrev.disabled = currentInspectionPage <= 1;
        }
        if (inspectNext) {
            inspectNext.style.display = showInspectPagination ? "" : "none";
            inspectNext.disabled = currentInspectionPage >= totalInspectionPages;
        }
        if (inspectEl) {
            inspectEl.style.display = showInspectPagination ? "" : "none";
            inspectEl.textContent = `Page ${currentInspectionPage} of ${totalInspectionPages}`;
        }

        const invoiceEl = $("invoice-page-info");
        const invoicePrev = $("invoice-prev-btn");
        const invoiceNext = $("invoice-next-btn");
        const showInvoicePagination = totalInvoicePages > 1;

        if (invoicePrev) {
            invoicePrev.style.display = showInvoicePagination ? "" : "none";
            invoicePrev.disabled = currentInvoicePage <= 1;
        }
        if (invoiceNext) {
            invoiceNext.style.display = showInvoicePagination ? "" : "none";
            invoiceNext.disabled = currentInvoicePage >= totalInvoicePages;
        }
        if (invoiceEl) {
            invoiceEl.style.display = showInvoicePagination ? "" : "none";
            invoiceEl.textContent = `Page ${currentInvoicePage} of ${totalInvoicePages}`;
        }
    }

    function loadDashboard() {
        showMessage("Loading dashboard...");

        frappe.call({
            method: "vms_account.api.get_dashboard_data",
            args: {
                inspection_page: currentInspectionPage,
                invoice_page: currentInvoicePage
            },

            callback(r) {
                if (r.exc) {
                    showMessage(
                        "Unable to load dashboard."
                    );
                    return;
                }

                const data = r.message || {};
                const pagination = data.pagination || r.pagination || {};

                // Handle raw lists and pagination metadata from the response object
                const inspections = data.inspections || [];
                const inspectMeta = pagination[window.INSPECTION_DOCTYPE || "vms vehicle inspection"] || {};
                totalInspectionPages = inspectMeta.total_pages || data._total_pages || r.total_pages || 1;
                currentInspectionPage = inspectMeta.page || currentInspectionPage;
                
                const invoices = data.invoices || [];
                const invoiceMeta = pagination[window.ACCOUNT_DOCTYPE || "vms accounts"] || {};
                totalInvoicePages = invoiceMeta.total_pages || data._total_pages || r.total_pages || 1;
                currentInvoicePage = invoiceMeta.page || currentInvoicePage;

                renderInspections(inspections);
                renderInvoices(invoices);
                renderStats(inspections, invoices);
                
                updatePaginationControls();
                showMessage("");
            },

            error() {
                showMessage(
                    "Access denied or server error."
                );
            }
        });
    }

    $("inspection-prev-btn")?.addEventListener("click", () => {
        if (currentInspectionPage > 1) {
            currentInspectionPage--;
            loadDashboard();
        }
    });

    $("inspection-next-btn")?.addEventListener("click", () => {
        if (currentInspectionPage < totalInspectionPages) {
            currentInspectionPage++;
            loadDashboard();
        }
    });

    $("invoice-prev-btn")?.addEventListener("click", () => {
        if (currentInvoicePage > 1) {
            currentInvoicePage--;
            loadDashboard();
        }
    });

    $("invoice-next-btn")?.addEventListener("click", () => {
        if (currentInvoicePage < totalInvoicePages) {
            currentInvoicePage++;
            loadDashboard();
        }
    });

    root.addEventListener("click", event => {
        const button = event.target.closest(
            "button[data-action]"
        );

        if (!button) return;

        const id = button.dataset.id;
        const action = button.dataset.action;

        if (action === "create") {
            window.location.href =
                "/vms_user_dashboard/accountant_dashboard/account-invoice?inspection=" +
                encodeURIComponent(id);
        }

        if (action === "open") {
            window.location.href =
                "/vms_user_dashboard/accountant_dashboard/account-invoice?invoice=" +
                encodeURIComponent(id);
        }
    });

    $("vms-refresh").addEventListener(
        "click",
        () => {
            currentInspectionPage = 1;
            currentInvoicePage = 1;
            loadDashboard();
        }
    );

    loadDashboard();
});