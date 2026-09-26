
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

    function loadDashboard() {
        showMessage("Loading dashboard...");

        frappe.call({
            method: "vms_account.api.get_dashboard_data",

            callback(r) {
                if (r.exc) {
                    showMessage(
                        "Unable to load dashboard."
                    );
                    return;
                }

                const data = r.message || {};

                const inspections = data.inspections || [];
                const invoices = data.invoices || [];

                renderInspections(inspections);
                renderInvoices(invoices);
                renderStats(inspections, invoices);

                showMessage("");
            },

            error() {
                showMessage(
                    "Access denied or server error."
                );
            }
        });
    }

    root.addEventListener("click", event => {
        const button = event.target.closest(
            "button[data-action]"
        );

        if (!button) return;

        const id = button.dataset.id;
        const action = button.dataset.action;

        if (action === "create") {
            window.location.href =
                "/vms-account-invoice?inspection=" +
                encodeURIComponent(id);
        }

        if (action === "open") {
            window.location.href =
                "/app/vms-accounts/" +
                encodeURIComponent(id);
        }
    });

    $("vms-refresh").addEventListener(
        "click",
        loadDashboard
    );

    loadDashboard();
});