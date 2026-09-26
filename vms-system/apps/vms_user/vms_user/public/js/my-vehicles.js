/* ============================================================
   VMS - MY VEHICLES
   ============================================================

   Responsibilities:
   1. Load vehicles belonging to the logged-in user
   2. Render vehicle cards
   3. Handle refresh
   4. Handle empty vehicle state
   5. Handle API errors
   6. Handle logout
   7. Redirect logout to /login

   The browser does NOT send a user ID.

   The server-side API must use:

       frappe.session.user

   to determine the currently logged-in customer.
   ============================================================ */


frappe.ready(function () {

    initializeMyVehiclesPage();

});


/* ============================================================
   INITIALIZE PAGE
   ============================================================ */

function initializeMyVehiclesPage() {

    const refreshButton =
        document.getElementById("refresh-vehicles");

    const logoutButton =
        document.getElementById("logout-btn");


    /* Load vehicles when page opens */
    loadMyVehicles();


    /* Refresh button */
    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            function () {

                loadMyVehicles();

            }
        );

    }


    /* Logout button */
    if (logoutButton) {

        logoutButton.addEventListener(
            "click",
            function () {

                logoutUser();

            }
        );

    }

}


/* ============================================================
   LOAD MY VEHICLES
   ============================================================ */

function loadMyVehicles() {

    const container =
        document.getElementById("vehicle-list");

    if (!container) {
        return;
    }


    const refreshButton =
        document.getElementById("refresh-vehicles");


    /* Add refreshing state */
    if (refreshButton) {

        refreshButton.classList.add("refreshing");

        refreshButton.disabled = true;

    }


    /* Loading UI */

    container.innerHTML = `
        <div class="vehicle-loading">

            <div class="loading-spinner"></div>

            <p>
                Loading your vehicles...
            </p>

        </div>
    `;


    /*
     * IMPORTANT:
     *
     * No user ID is sent from the browser.
     *
     * The backend should identify the user using:
     *
     *     frappe.session.user
     *
     */

    frappe.call({

        method: "vms_vehicle.api.get_my_vehicles",

        callback: function (response) {

            finishRefresh();


            if (
                response.exc ||
                !response.message
            ) {

                showVehicleError();

                return;

            }


            const vehicles =
                response.message;


            if (!Array.isArray(vehicles)) {

                showVehicleError();

                return;

            }


            renderMyVehicles(vehicles);

        },

        error: function () {

            finishRefresh();

            showVehicleError();

        }

    });

}


/* ============================================================
   FINISH REFRESH
   ============================================================ */

function finishRefresh() {

    const refreshButton =
        document.getElementById("refresh-vehicles");


    if (!refreshButton) {
        return;
    }


    refreshButton.classList.remove(
        "refreshing"
    );


    refreshButton.disabled = false;

}


/* ============================================================
   RENDER VEHICLES
   ============================================================ */

function renderMyVehicles(vehicles) {

    const container =
        document.getElementById("vehicle-list");


    if (!container) {
        return;
    }


    /* ========================================================
       NO VEHICLES
       ======================================================== */

    if (vehicles.length === 0) {

        container.innerHTML = `

            <div class="vehicle-empty">

                <div class="vehicle-empty-icon">

                    <i class="fa fa-car"></i>

                </div>


                <h3>
                    No vehicles registered yet
                </h3>


                <p>
                    Register your first vehicle
                    to get started.
                </p>


                <a
                    href="/vehicle-register"
                    class="empty-register-btn">

                    <i class="fa fa-plus"></i>

                    Register Your First Vehicle

                </a>

            </div>

        `;

        return;

    }


    /* ========================================================
       VEHICLE CARDS
       ======================================================== */

    let vehicleHTML = `

        <div class="vehicle-grid">

    `;


    vehicles.forEach(function (vehicle) {

        const vehicleName =
            escapeHTML(
                vehicle.name || ""
            );


        const vehicleNumber =
            escapeHTML(
                vehicle.vehicle_number || "N/A"
            );


        const vehicleBrand =
            escapeHTML(
                vehicle.vehicle_brand || ""
            );


        const vehicleModel =
            escapeHTML(
                vehicle.vehicle_model || ""
            );


        const vehicleType =
            escapeHTML(
                vehicle.vehicle_type || ""
            );


        /* Vehicle brand/model */
        let vehicleDescription = "";


        if (
            vehicleBrand &&
            vehicleModel
        ) {

            vehicleDescription =
                `${vehicleBrand} ${vehicleModel}`;

        }

        else if (vehicleBrand) {

            vehicleDescription =
                vehicleBrand;

        }

        else if (vehicleModel) {

            vehicleDescription =
                vehicleModel;

        }

        else {

            vehicleDescription =
                "Vehicle details";

        }


        vehicleHTML += `

            <article class="vehicle-card">

                <!-- Card Header -->

                <div class="vehicle-card-header">

                    <div class="vehicle-icon">

                        <i class="fa fa-car"></i>

                    </div>


                    <span class="vehicle-badge">

                        Registered

                    </span>

                </div>


                <!-- Vehicle Number -->

                <h3 class="vehicle-number">

                    ${vehicleNumber}

                </h3>


                <!-- Brand / Model -->

                <p class="vehicle-model">

                    ${vehicleDescription}

                </p>


                <!-- Vehicle Type -->

                <p class="vehicle-type">

                    ${vehicleType || "Vehicle"}

                </p>


                <!-- Details Button -->

                <a
                    class="vehicle-details-btn"
                    href="/vehicle-details?name=${encodeURIComponent(vehicleName)}">

                    <span>
                        View Details
                    </span>

                    <i class="fa fa-arrow-right"></i>

                </a>

            </article>

        `;

    });


    vehicleHTML += `

        </div>

    `;


    container.innerHTML =
        vehicleHTML;

}


/* ============================================================
   SHOW ERROR
   ============================================================ */

function showVehicleError() {

    const container =
        document.getElementById("vehicle-list");


    if (!container) {
        return;
    }


    container.innerHTML = `

        <div class="vehicle-error">

            <div class="vehicle-error-icon">

                <i class="fa fa-exclamation-triangle"></i>

            </div>


            <h3>
                Unable to load your vehicles
            </h3>


            <p>
                Something went wrong while
                loading your registered vehicles.
            </p>


            <button
                type="button"
                id="retry-vehicles"
                class="retry-btn">

                <i class="fa fa-refresh"></i>

                Try Again

            </button>

        </div>

    `;


    const retryButton =
        document.getElementById(
            "retry-vehicles"
        );


    if (retryButton) {

        retryButton.addEventListener(
            "click",
            function () {

                loadMyVehicles();

            }
        );

    }

}


/* ============================================================
   LOGOUT USER
   ============================================================ */

function logoutUser() {

    const overlay =
        document.getElementById(
            "logout-overlay"
        );


    const logoutButton =
        document.getElementById(
            "logout-btn"
        );


    /* Prevent multiple logout requests */

    if (logoutButton) {

        logoutButton.disabled = true;

    }


    /* Display logout overlay */

    if (overlay) {

        overlay.classList.add("active");

    }


    /*
     * Use Frappe's server-side logout method.
     *
     * After the session is destroyed, redirect
     * to the custom VMS login page.
     */

    frappe.call({

        method: "frappe.auth.logout",

        callback: function () {

            redirectToLogin();

        },

        error: function () {

            /*
             * Even if the server returns an error,
             * redirect the user to the login page.
             */

            redirectToLogin();

        }

    });

}


/* ============================================================
   REDIRECT TO LOGIN
   ============================================================ */

function redirectToLogin() {

    window.location.href =
        "/login";

}


/* ============================================================
   HTML ESCAPING
   ============================================================ */

function escapeHTML(value) {

    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}