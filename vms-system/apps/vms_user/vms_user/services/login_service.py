# ==========================================================
# FILE: vms_user/login_service.py
# PURPOSE: Role-based dashboard routing, access control, and
#          high-efficiency request-cached user detection.
# ==========================================================

import frappe
from frappe import _

# ----------------------------------------------------------
# SECTION 1: Configure role names and dashboard routes
# ----------------------------------------------------------

ROLE_DASHBOARDS = {
    "Administrator": "/app",
    "System Manager": "/app",
    "vms manager": "/app",
    "vms accountant": "/account-dashboard",
    "vms technician": "/technician-dashboard",
    "vms mechanic": "/mechanic-dashboard",
    "vms customer": "/customer-home",
    "Customer": "/customer-home",
}

# The first matching role in this list takes priority.
ROLE_PRIORITY = [
    "Administrator",
    "System Manager",
    "vms manager",
    "vms accountant",
    "vms technician",
    "vms mechanic",
    "vms customer",
    "Customer",
]

PROTECTED_ROUTES = {
    "/technician-dashboard": ["vms technician", "System Manager", "vms manager"],
    "/mechanic-dashboard": ["vms mechanic", "System Manager", "vms manager"],
    "/customer-home": ["vms customer", "System Manager"],
    "/manager-dashboard": ["vms manager", "System Manager"],
    "/accounts-dashboard": ["vms accountant", "vms manager", "System Manager"],
    "/account-dashboard": ["vms accountant", "vms manager", "System Manager"],
    "/my-invoices": ["vms customer", "Customer", "System Manager", "vms manager"],
    "/my-invoice": ["vms customer", "Customer", "System Manager", "vms manager"],
}

CUSTOMER_PROFILE_DOCTYPE = "vms customer profile"


# ----------------------------------------------------------
# SECTION 2: Efficient Logged-In User Detection & Context
# ----------------------------------------------------------

def get_current_user_context(user: str | None = None) -> dict:
    """
    Return a comprehensive, request-cached context for the user.
    Results are cached in frappe.local to eliminate duplicate DB queries
    across function calls within the same HTTP request cycle.
    """
    current_session_user = getattr(frappe.session, "user", None) or "Guest"
    target_user = user or current_session_user

    # Request-level cache key
    cache_store = getattr(frappe.local, "vms_user_contexts", None)
    if cache_store is None:
        cache_store = {}
        frappe.local.vms_user_contexts = cache_store

    if target_user in cache_store:
        return cache_store[target_user]

    is_authenticated = bool(target_user and target_user != "Guest")

    if not is_authenticated:
        context = {
            "user": "Guest",
            "is_authenticated": False,
            "user_type": "Guest",
            "roles": [],
            "role_set": set(),
            "is_admin": False,
            "is_manager": False,
            "is_technician": False,
            "is_mechanic": False,
            "is_customer": False,
            "is_accountant": False,
            "identities": ["Guest"],
            "profile": None,
            "redirect_url": "/vms-login",
        }
        cache_store[target_user] = context
        return context

    # Resolve roles once
    raw_roles = frappe.get_roles(target_user)
    role_set = {r.strip().lower() for r in raw_roles}
    exact_roles = set(raw_roles)

    is_admin = bool("administrator" == target_user.lower() or "system manager" in role_set or "administrator" in role_set)
    is_manager = bool(is_admin or "vms manager" in role_set)
    is_mechanic = bool(is_manager or "vms mechanic" in role_set or "mechanic" in role_set)
    is_technician = bool(is_manager or "vms technician" in role_set or "technician" in role_set)
    is_accountant = bool(is_manager or "vms accountant" in role_set or "accounts user" in role_set or "accounts manager" in role_set)
    is_customer = bool("vms customer" in role_set or "customer" in role_set)

    # Resolve user identities (name, email, full_name, username) with single DB fetch
    identities = [target_user]
    user_record = frappe.db.get_value(
        "User",
        target_user,
        ["name", "email", "full_name", "username", "user_type", "mobile_no", "phone"],
        as_dict=True,
    ) or {}

    for val in [
        user_record.get("name"),
        user_record.get("email"),
        user_record.get("full_name"),
        user_record.get("username"),
    ]:
        if val and val not in identities:
            identities.append(val)

    # Resolve customer profile if customer or exists
    profile = None
    if is_customer or not is_admin:
        profile_data = frappe.db.get_value(
            CUSTOMER_PROFILE_DOCTYPE,
            {"user_name": target_user},
            ["name", "customer_name", "customer_phone", "customer_email", "address"],
            as_dict=True,
        )
        if profile_data:
            profile = dict(profile_data)

    # Determine dashboard route
    redirect_url = "/vms-login"
    for role in ROLE_PRIORITY:
        if role in exact_roles or role.lower() in role_set:
            redirect_url = ROLE_DASHBOARDS[role]
            break
    if redirect_url == "/vms-login" and is_authenticated:
        redirect_url = "/app" if user_record.get("user_type") == "System User" else "/customer-home"

    context = {
        "user": target_user,
        "is_authenticated": True,
        "user_type": user_record.get("user_type", "Website User"),
        "full_name": user_record.get("full_name") or target_user,
        "email": user_record.get("email") or target_user,
        "roles": raw_roles,
        "role_set": role_set,
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_technician": is_technician,
        "is_mechanic": is_mechanic,
        "is_customer": is_customer,
        "is_accountant": is_accountant,
        "identities": identities,
        "profile": profile,
        "redirect_url": redirect_url,
    }

    cache_store[target_user] = context
    return context


def get_user_identities(user: str | None = None) -> list[str]:
    """
    Quick helper to return all identity strings (email, name, username, full_name)
    for the user using the cached context.
    """
    ctx = get_current_user_context(user)
    return ctx.get("identities") or [user or "Guest"]


# ----------------------------------------------------------
# SECTION 3: Guards and Authentication Verification
# ----------------------------------------------------------

def require_login() -> str:
    """
    Ensure the current request is from an authenticated user.
    Throws PermissionError if user is Guest.
    """
    ctx = get_current_user_context()
    if not ctx["is_authenticated"]:
        frappe.throw(
            _("Please log in to continue."),
            frappe.PermissionError,
        )
    return ctx["user"]


def require_role(allowed_roles: list[str] | set[str] | str, user: str | None = None) -> str:
    """
    Verify that the user possesses at least one of the allowed roles.
    Administrators and System Managers always satisfy role checks.
    """
    ctx = get_current_user_context(user)
    if not ctx["is_authenticated"]:
        frappe.throw(_("Please log in to continue."), frappe.PermissionError)

    if ctx["is_admin"]:
        return ctx["user"]

    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    allowed_set = {r.strip().lower() for r in allowed_roles}
    if not ctx["role_set"].intersection(allowed_set):
        frappe.throw(
            _("You do not have permission to access this resource."),
            frappe.PermissionError,
        )

    return ctx["user"]


# ----------------------------------------------------------
# SECTION 4: Customer Profile Initialization Helper
# ----------------------------------------------------------

def get_or_create_customer_profile(user: str) -> dict:
    """
    Retrieve existing customer profile or safely initialize one for the user.
    """
    if not user or user == "Guest":
        frappe.throw(_("Valid user is required to resolve customer profile."))

    existing_name = frappe.db.get_value(
        CUSTOMER_PROFILE_DOCTYPE,
        {"user_name": user},
        "name",
    )

    if existing_name:
        doc = frappe.get_doc(CUSTOMER_PROFILE_DOCTYPE, existing_name)
        return doc

    # Fetch user data to populate initial profile
    user_doc = frappe.get_doc("User", user)
    full_name = user_doc.full_name or user_doc.first_name or user
    phone = user_doc.mobile_no or user_doc.phone or ""

    profile_doc = frappe.get_doc({
        "doctype": CUSTOMER_PROFILE_DOCTYPE,
        "user_name": user,
        "customer_name": full_name,
        "customer_email": user_doc.email,
        "customer_phone": phone,
        "address": "",
    })
    profile_doc.flags.ignore_permissions = True
    profile_doc.insert()

    # Invalidate cached context so new profile is immediately visible
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    return profile_doc


# ----------------------------------------------------------
# SECTION 5: Dashboard Destination & Redirection
# ----------------------------------------------------------

def get_dashboard_for_user(user: str | None = None) -> str:
    """
    Return the dashboard route for the user based on role priority.
    """
    ctx = get_current_user_context(user)
    if not ctx["is_authenticated"]:
        return "/vms-login"

    return ctx.get("redirect_url") or "/customer-home"


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_logged_user() -> dict:
    """
    Whitelisted API returning the full logged-in user context.
    Safe for frontend callers to inspect login status, roles, and profile.
    Accessible via GET so stale CSRF tokens (held by website pages right after
    a new login) do not block the response — GET is CSRF-exempt in Frappe.
    """
    ctx = get_current_user_context()
    return {
        "user": ctx["user"],
        "is_authenticated": ctx["is_authenticated"],
        "full_name": ctx.get("full_name"),
        "email": ctx.get("email"),
        "roles": ctx["roles"],
        "is_admin": ctx["is_admin"],
        "is_manager": ctx["is_manager"],
        "is_technician": ctx["is_technician"],
        "is_mechanic": ctx["is_mechanic"],
        "is_customer": ctx["is_customer"],
        "is_accountant": ctx["is_accountant"],
        "profile": ctx.get("profile"),
        "redirect_url": ctx["redirect_url"],
    }


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_login_destination() -> dict:
    """
    Returns the role-based redirect URL for the current session user.

    Accepts both GET and POST so that the browser can call it via a plain GET
    request immediately after login — before the page has had a chance to
    refresh the CSRF token for the newly-created session.  GET requests are
    not CSRF-validated by Frappe (only POST/PUT/DELETE/PATCH are).

    `require_login()` is still enforced inside, so Guests receive a
    PermissionError rather than a redirect URL.
    """
    require_login()
    ctx = get_current_user_context()
    return {
        "user": ctx["user"],
        "roles": ctx["roles"],
        "redirect_url": ctx["redirect_url"],
    }


# ----------------------------------------------------------
# SECTION 6: Check Protected Dashboard Access
# ----------------------------------------------------------

@frappe.whitelist()
def check_dashboard_access(route: str | None = None) -> dict:
    """
    Validate the user's permissions for the requested route.
    """
    user = require_login()

    if not route:
        frappe.throw(_("Dashboard route is required."), frappe.ValidationError)

    normalized_route = "/" + route.strip().strip("/")
    allowed_roles = PROTECTED_ROUTES.get(normalized_route)

    if allowed_roles is None:
        frappe.throw(
            _("This route is not configured as a protected dashboard."),
            frappe.PermissionError,
        )

    ctx = get_current_user_context(user)
    if ctx["is_admin"]:
        return {"allowed": True, "user": user, "route": normalized_route}

    allowed_set = {r.strip().lower() for r in allowed_roles}
    if not ctx["role_set"].intersection(allowed_set):
        frappe.throw(
            _("You do not have permission to access this dashboard."),
            frappe.PermissionError,
        )

    return {
        "allowed": True,
        "user": user,
        "route": normalized_route,
    }


# ----------------------------------------------------------
# SECTION 7: Logout Helper & Website User Home Page
# ----------------------------------------------------------

@frappe.whitelist()
def logout_user() -> dict:
    """
    End the current session using Frappe's logout method.
    """
    require_login()
    if hasattr(frappe.local, "login_manager"):
        frappe.local.login_manager.logout()

    return {"message": _("Logged out successfully.")}


def get_website_user_home_page(user: str | None = None) -> str:
    """
    Return the website home page for the logged-in user.
    """
    ctx = get_current_user_context(user)
    if not ctx["is_authenticated"]:
        return "/vms-login"
    return ctx["redirect_url"]