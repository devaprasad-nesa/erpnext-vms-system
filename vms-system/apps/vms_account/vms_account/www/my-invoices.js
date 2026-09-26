let currentOnlyAudited = true;
let invoicesCache = [];

function switchFilter(onlyAudited) {
    currentOnlyAudited = onlyAudited;

    const tabAudited = document.getElementById("tab-audited");
    const tabAll = document.getElementById("tab-all");
    const tableTitle = document.getElementById("table-title");

    if (onlyAudited) {
        tabAudited.classList.add("btn-primary", "active");
        tabAudited.classList.remove("btn-outline-secondary");
        tabAll.classList.add("btn-outline-secondary");
        tabAll.classList.remove("btn-primary", "active");
        tableTitle.textContent = "Paid Invoices";
    } else {
        tabAll.classList.add("btn-primary", "active");
        tabAll.classList.remove("btn-outline-secondary");
        tabAudited.classList.add("btn-outline-secondary");
        tabAudited.classList.remove("btn-primary", "active");
        tableTitle.textContent = "All Invoices";
    }

    renderInvoicesTable();
}

function loadCustomerInvoices() {
    const tbody = document.getElementById("invoices-table-body");
    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-4 text-muted">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                Loading your invoices...
            </td>
        </tr>
    `;

    frappe.call({
        method: "vms_account.api.get_my_invoices",
        args: {
            only_audited: 0 // fetch all to cache, filter client-side
        },
        callback: function (r) {
            invoicesCache = r.message || [];
            renderInvoicesTable();
        },
        error: function (err) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-danger font-weight-bold">
                        Failed to load invoices. Please refresh or try again later.
                    </td>
                </tr>
            `;
        }
    });
}

function enablePayment(invoiceName) {
    frappe.confirm('Are you sure you want to mark payment as done for this invoice?', () => {
        frappe.call({
            method: "vms_account.api.enable_payment",
            args: { invoice_name: invoiceName },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({message: "Payment marked as done.", indicator: "green"});
                    loadCustomerInvoices();
                }
            }
        });
    });
}

function renderInvoicesTable() {
    const tbody = document.getElementById("invoices-table-body");
    const badge = document.getElementById("invoice-count-badge");

    const filtered = currentOnlyAudited
        ? invoicesCache.filter(inv => Boolean(Number(inv.audited)))
        : invoicesCache;

    badge.textContent = `${filtered.length} ${currentOnlyAudited ? "Paid" : "Total"} Invoice${filtered.length === 1 ? "" : "s"}`;

    if (!filtered || filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-muted">
                    <div class="mb-2" style="font-size: 2rem;">&#x1f9fe;</div>
                    <h6 class="font-weight-bold text-dark">No ${currentOnlyAudited ? "Paid " : ""}Invoices Found</h6>
                    <p class="small text-muted mb-3">
                        ${currentOnlyAudited
                            ? "Invoices will appear here once the workshop accountant confirms and marks your service bill as paid."
                            : "You do not have any invoices created yet."}
                    </p>
                    <a href="/customer-home" class="btn btn-outline-primary btn-sm font-weight-bold">Go to Customer Home</a>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(inv => {
        const isAudited = Boolean(Number(inv.audited));
        const statusBadge = isAudited
            ? `<span class="badge bg-success px-2 py-1">&#x2714; Paid</span>`
            : `<span class="badge bg-warning text-dark px-2 py-1">Pending</span>`;

        const totalFormatted = (inv.total_bill !== null && inv.total_bill !== undefined)
            ? Number(inv.total_bill).toLocaleString("en-IN", { style: "currency", currency: "INR" })
            : "₹0.00";

        const partsFormatted = (inv.spare_parts_amount !== null && inv.spare_parts_amount !== undefined)
            ? Number(inv.spare_parts_amount).toLocaleString("en-IN", { style: "currency", currency: "INR" })
            : "₹0.00";

        const isPayment = Boolean(Number(inv.payment));
        const paymentCheckbox = isPayment
            ? `<input type="checkbox" checked disabled class="form-check-input" /> <label class="small text-success mb-0 ms-1">Paid</label>`
            : `<input type="checkbox" class="form-check-input" onclick="enablePayment('${frappe.utils.escape_html(inv.name)}')"/> <label class="small text-muted mb-0 ms-1">Pay</label>`;

        return `
            <tr>
                <td><strong>${frappe.utils.escape_html(inv.name)}</strong></td>
                <td><span class="badge bg-light text-dark border font-weight-bold">${frappe.utils.escape_html(inv.vehicle_number || "-")}</span></td>
                <td>${frappe.utils.escape_html(inv.invoice_date || "-")}</td>
                <td>${partsFormatted}</td>
                <td><strong class="text-primary">${totalFormatted}</strong></td>
                <td>
                    <div class="form-check d-flex align-items-center m-0 p-0">
                        ${paymentCheckbox}
                    </div>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-primary font-weight-bold" onclick="viewInvoiceDetails('${frappe.utils.escape_html(inv.name)}')">
                        View Details
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

function viewInvoiceDetails(invoiceName) {
    frappe.call({
        method: "vms_account.api.get_customer_invoice_details",
        args: {
            invoice_name: invoiceName
        },
        callback: function (r) {
            const data = r.message;
            if (!data) return;

            document.getElementById("modal-invoice-id").textContent = `Invoice ${data.name}`;
            document.getElementById("modal-display-id").textContent = data.name;
            document.getElementById("modal-display-date").textContent = `Invoice Date: ${data.invoice_date || "-"}`;
            document.getElementById("modal-display-vehicle").textContent = data.vehicle_number || "-";
            document.getElementById("modal-display-customer").textContent = data.customer_name || "-";
            document.getElementById("modal-display-issue").textContent = data.inspection_issue || "Standard service inspection completed.";
            document.getElementById("modal-display-spare-name").textContent = data.vehicle_spare_parts || "None";

            const partsFormatted = Number(data.spare_parts_amount || 0).toLocaleString("en-IN", { style: "currency", currency: "INR" });
            const totalFormatted = Number(data.total_bill || 0).toLocaleString("en-IN", { style: "currency", currency: "INR" });

            document.getElementById("modal-display-parts-amount").textContent = partsFormatted;
            document.getElementById("modal-display-total").textContent = totalFormatted;

            const isAudited = Boolean(Number(data.audited));
            const statusEl = document.getElementById("modal-display-status");
            const alertEl = document.getElementById("modal-audit-alert");

            const isPayment = Boolean(Number(data.payment));
            const paymentCheckbox = document.getElementById("modal-payment-checkbox");
            
            paymentCheckbox.checked = isPayment;
            paymentCheckbox.disabled = isPayment;
            
            paymentCheckbox.onchange = function() {
                if (paymentCheckbox.checked) {
                    frappe.call({
                        method: "vms_account.api.enable_payment",
                        args: { invoice_name: invoiceName },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                paymentCheckbox.disabled = true;
                                loadCustomerInvoices();
                            } else {
                                paymentCheckbox.checked = false;
                            }
                        }
                    });
                }
            };

            if (isAudited) {
                statusEl.className = "badge bg-success px-3 py-2 font-weight-bold";
                statusEl.textContent = "Paid & Verified";
                alertEl.className = "alert alert-success d-flex align-items-center py-2 mb-0";
                alertEl.innerHTML = `<span class="me-2">&#x2714;</span><small><strong>Paid & Approved:</strong> This bill has been audited and finalized as Paid by Workshop Accounts.</small>`;
            } else {
                statusEl.className = "badge bg-warning text-dark px-3 py-2 font-weight-bold";
                statusEl.textContent = "Pending Payment";
                alertEl.className = "alert alert-warning d-flex align-items-center py-2 mb-0";
                alertEl.innerHTML = `<span class="me-2">&#x23f3;</span><small><strong>Pending Verification:</strong> Workshop Accounts has not marked this invoice as Paid yet.</small>`;
            }

            const modal = new bootstrap.Modal(document.getElementById("invoiceDetailsModal"));
            modal.show();
        }
    });
}

function logoutCustomer() {
    const btn = document.getElementById("customer-logout-btn");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>Logging out...</span>`;
    }
    frappe.call({
        method: "frappe.auth.logout",
        callback: function () {
            window.location.href = "/login-page/vms-login";
        },
        error: function () {
            window.location.href = "/login-page/vms-login";
        }
    });
}

frappe.ready(function () {
    loadCustomerInvoices();
});
