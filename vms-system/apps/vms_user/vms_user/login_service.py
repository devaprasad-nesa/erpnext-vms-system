# ==========================================================
# FILE: vms_user/login_service.py
# PURPOSE: Compatibility wrapper to expose the login_service module
#          at the original import path `vms_user.login_service`.
# ----------------------------------------------------------
# The core implementation resides in `vms_user.services.login_service`.
# This file re-exports the public API so that existing imports and
# Frappe whitelisted methods (e.g., `/api/method/vms_user.login_service.get_login_destination`)
# continue to work without having to modify all callers.
# ----------------------------------------------------------

# Import the actual implementation
from .services.login_service import (
    get_current_user_context,
    get_user_identities,
    require_login,
    require_role,
    get_or_create_customer_profile,
    get_dashboard_for_user,
    get_logged_user,
    get_login_destination,
    check_dashboard_access,
    logout_user,
    get_website_user_home_page,
)

# Define __all__ to expose the intended public symbols
__all__ = [
    "get_current_user_context",
    "get_user_identities",
    "require_login",
    "require_role",
    "get_or_create_customer_profile",
    "get_dashboard_for_user",
    "get_logged_user",
    "get_login_destination",
    "check_dashboard_access",
    "logout_user",
    "get_website_user_home_page",
]
