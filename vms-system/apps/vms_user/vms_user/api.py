
# ============================================================
# File: vms_user/api.py
#
# PURPOSE:
# This file exposes whitelisted API endpoints for the VMS User
# application.
#
# The business logic is implemented in:
# vms_user/services/services.py
#
# Existing frontend calls can continue using:
# vms_user.api.register_customer
# vms_user.api.get_current_user
# vms_user.api.get_my_profile
# vms_user.api.update_my_profile
# vms_user.api.delete_my_profile
# vms_user.api.get_login_redirect
# vms_user.api.assign_user_roles
# vms_user.api.add_user_role
# vms_user.api.remove_user_role
# vms_user.api.get_user_roles
# vms_user.api.get_assignable_roles
# ============================================================


# ============================================================
# SECTION 1: IMPORTS
# ============================================================

# Frappe is required for whitelisted endpoint decorators.
import frappe

# Import the business logic module.
# All the API functions delegate to this module.
from vms_user.services import services as user_services


# ============================================================
# SECTION 2: CUSTOMER REGISTRATION API
# ============================================================

@frappe.whitelist(allow_guest=True, methods=["POST"])
def register_customer(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
) -> dict:
    """
    Public customer registration endpoint.

    The service validates registration data, creates the User,
    sets the password, and initializes the customer profile.
    """

    return user_services.register_customer(
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
    )


# ============================================================
# SECTION 3: CURRENT USER API
# ============================================================

@frappe.whitelist()
def get_current_user() -> dict:
    """
    Return information about the logged-in user.
    """

    return user_services.get_current_user()


# ============================================================
# SECTION 4: GET MY PROFILE API
# ============================================================

@frappe.whitelist()
def get_my_profile() -> dict:
    """
    Return the authenticated customer's profile.
    """

    return user_services.get_my_profile()


# ============================================================
# SECTION 5: UPDATE MY PROFILE API
# ============================================================

@frappe.whitelist()
def update_my_profile(
    customer_name: str,
    phone: str | None = None,
    address: str | None = None,
) -> str:
    """
    Update the authenticated customer's profile.
    """

    return user_services.update_my_profile(
        customer_name=customer_name,
        phone=phone,
        address=address,
    )


# ============================================================
# SECTION 6: DELETE MY PROFILE API
# ============================================================

@frappe.whitelist()
def delete_my_profile() -> str:
    """
    Delete the authenticated customer's profile.
    """

    return user_services.delete_my_profile()


# ============================================================
# SECTION 7: LOGIN REDIRECT API
# ============================================================

@frappe.whitelist()
def get_login_redirect() -> str:
    """
    Return the dashboard URL associated with the current user.
    """

    return user_services.get_login_redirect()


# ============================================================
# SECTION 8: ASSIGN USER ROLES API
# ============================================================

@frappe.whitelist()
def assign_user_roles(
    user: str,
    roles: list | str,
) -> dict:
    """
    Replace the target user's roles with the supplied roles.

    Only administrators and managers are authorized.
    """

    return user_services.assign_user_roles(
        user=user,
        roles=roles,
    )


# ============================================================
# SECTION 9: ADD USER ROLE API
# ============================================================

@frappe.whitelist()
def add_user_role(
    user: str,
    role: str,
) -> dict:
    """
    Add one role to the specified user.
    """

    return user_services.add_user_role(
        user=user,
        role=role,
    )


# ============================================================
# SECTION 10: REMOVE USER ROLE API
# ============================================================

@frappe.whitelist()
def remove_user_role(
    user: str,
    role: str,
) -> dict:
    """
    Remove one role from the specified user.
    """

    return user_services.remove_user_role(
        user=user,
        role=role,
    )


# ============================================================
# SECTION 11: GET USER ROLES API
# ============================================================

@frappe.whitelist()
def get_user_roles(
    user: str | None = None,
) -> dict:
    """
    Retrieve the roles assigned to a user.

    Ordinary users can retrieve their own roles.
    Administrators and managers can retrieve other users' roles.
    """

    return user_services.get_user_roles(
        user=user,
    )


# ============================================================
# SECTION 12: GET ASSIGNABLE ROLES API
# ============================================================

@frappe.whitelist()
def get_assignable_roles() -> list[str]:
    """
    Return enabled assignable roles.

    Only administrators and managers are authorized.
    """

    return user_services.get_assignable_roles()


# ============================================================
# END OF API
# ============================================================