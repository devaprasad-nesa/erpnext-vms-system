
# ============================================================
# File: vms_user/services/services.py
#
# PURPOSE:
# This file contains the business logic for the VMS User app.
#
# api.py will call these functions instead of implementing
# the business logic directly.
#
# Functionalities:
# 1. Customer registration
# 2. Current user information
# 3. Customer profile retrieval
# 4. Customer profile update
# 5. Customer profile deletion
# 6. Login redirect
# 7. Assign multiple roles
# 8. Add a role
# 9. Remove a role
# 10. Get user roles
# 11. Get assignable roles
#
# NOTE:
# Login and profile helper functions remain in login_service.py.
# ============================================================


# ============================================================
# SECTION 1: IMPORTS
# ============================================================

# json is used to decode role lists submitted as JSON strings.
import json

# Frappe provides database access, document handling,
# session information, permissions, and exception handling.
import frappe

# _() is Frappe's translation function.
from frappe import _
from vms_user.pagination import apply_pagination

# Used to securely set a user's password through Frappe.
from frappe.utils.password import update_password


# Import existing login and customer-profile functionality.
# These functions remain in the separate login_service.py file.
from .login_service import (
    get_current_user_context,
    get_logged_user,
    get_dashboard_for_user,
    get_or_create_customer_profile,
    require_login,
)


# ============================================================
# SECTION 2: CONSTANTS
# ============================================================

# Centralized DocType name.
# This avoids repeating the DocType string throughout the file.
CUSTOMER_PROFILE_DOCTYPE = "vms customer profile"


# ============================================================
# SECTION 3: CUSTOMER REGISTRATION
# ============================================================

def register_customer(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
) -> dict:
    """
    Create a website customer account.

    Responsibilities:
    - Validate registration fields.
    - Check password confirmation and minimum length.
    - Prevent duplicate emails and usernames.
    - Assign the VMS Customer role.
    - Create the User document.
    - Set the password.
    - Initialize the customer's profile.
    """

    # Normalize user input to prevent whitespace-related issues.
    username = (username or "").strip()
    email = (email or "").strip().lower()

    # Validate that all required registration fields are supplied.
    if not username or not email or not password or not confirm_password:
        frappe.throw(_("All fields are required."))

    # Ensure that the two password fields match.
    if password != confirm_password:
        frappe.throw(_("Passwords do not match."))

    # Enforce the minimum password length from the original API.
    if len(password) < 8:
        frappe.throw(_("Password must be at least 8 characters."))

    # Prevent registering an email that already exists.
    if frappe.db.exists("User", email):
        frappe.throw(_("Email already registered."))

    # Prevent duplicate usernames.
    if frappe.db.exists("User", {"username": username}):
        frappe.throw(_("Username already taken."))

    # Prepare the role list.
    # The Customer role is added only if it exists.
    roles = []

    for role_name in ("vms customer", "Customer"):
        if frappe.db.exists("Role", role_name):
            roles.append({"role": role_name})

    # The VMS Customer role is mandatory for registration.
    if not any(row["role"] == "vms customer" for row in roles):
        frappe.throw(
            _(
                "Required role 'vms customer' does not exist. "
                "Please contact the administrator."
            )
        )

    # Create the Frappe User document.
    # Website User prevents this account from automatically
    # being treated as a Desk user.
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "username": username,
        "first_name": username,
        "enabled": 1,
        "user_type": "Website User",
        "send_welcome_email": 0,
        "roles": roles,
    })

    # This is a guest registration operation.
    # Ignore User DocType insertion permissions only here.
    user.flags.ignore_permissions = True
    user.insert()

    # Set the user's password using Frappe's password utility.
    update_password(email, password)

    # Initialize the VMS customer profile.
    # The original behavior logs an error if profile creation fails
    # instead of raising the profile error to the registration caller.
    try:
        get_or_create_customer_profile(email)

    except Exception as e:
        frappe.log_error(
            f"Failed to auto-create customer profile for {email}: {str(e)}",
            "Customer Registration",
        )

    # Return a response suitable for the registration webpage.
    return {
        "message": _("Account created successfully"),
        "user": email,
    }


# ============================================================
# SECTION 4: GET CURRENT USER
# ============================================================

def get_current_user() -> dict:
    """
    Return the currently logged-in user's information.

    The login_service module handles the actual user context
    and cached user information.
    """

    return get_logged_user()


# ============================================================
# SECTION 5: GET CUSTOMER PROFILE
# ============================================================

def get_my_profile() -> dict:
    """
    Return the customer profile associated with the
    currently authenticated user.
    """

    # Ensure the caller is authenticated.
    user = require_login()

    # Retrieve the existing profile or create one if necessary.
    profile_doc = get_or_create_customer_profile(user)

    # Return only the profile fields exposed by the original API.
    return {
        "name": profile_doc.name,
        "user_name": profile_doc.user_name,
        "customer_name": profile_doc.customer_name,
        "customer_phone": profile_doc.customer_phone,
        "customer_email": profile_doc.customer_email,
        "address": profile_doc.address,
    }


# ============================================================
# SECTION 6: UPDATE CUSTOMER PROFILE
# ============================================================

def update_my_profile(
    customer_name: str,
    phone: str | None = None,
    address: str | None = None,
) -> str:
    """
    Update the profile associated with the logged-in customer.

    The user is authenticated before the profile is accessed.
    The original authorization check is retained.
    """

    # Identify the authenticated user.
    user = require_login()

    # Find the profile associated with this user.
    profile_name = frappe.db.get_value(
        CUSTOMER_PROFILE_DOCTYPE,
        {"user_name": user},
        "name",
    )

    # Create the profile if it does not already exist.
    if not profile_name:
        doc = get_or_create_customer_profile(user)

    else:
        # Load the existing profile document.
        doc = frappe.get_doc(
            CUSTOMER_PROFILE_DOCTYPE,
            profile_name,
        )

    # Preserve the original authorization check.
    # A user cannot modify another user's profile unless
    # the user has manager or administrator privileges.
    if doc.user_name != user:
        ctx = get_current_user_context(user)

        if not ctx["is_manager"] and not ctx["is_admin"]:
            frappe.throw(
                _("Not authorized to modify another user's profile."),
                frappe.PermissionError,
            )

    # Update the customer name.
    doc.customer_name = (customer_name or "").strip()

    # Update the phone number only when it was supplied.
    if phone is not None:
        doc.customer_phone = str(phone).strip()

    # Update the address only when it was supplied.
    if address is not None:
        doc.address = str(address).strip()

    # Retain the original permission-bypass behavior.
    # Authorization has already been checked above.
    doc.flags.ignore_permissions = True
    doc.save()

    # Clear the cached user context so updated profile information
    # is reflected immediately in subsequent requests.
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    return _("Profile updated successfully.")


# ============================================================
# SECTION 7: DELETE CUSTOMER PROFILE
# ============================================================

def delete_my_profile() -> str:
    """
    Delete the customer profile associated with the
    currently authenticated user.
    """

    # Authenticate the caller before accessing profile data.
    user = require_login()

    # Find the profile belonging to the current user.
    profile_name = frappe.db.get_value(
        CUSTOMER_PROFILE_DOCTYPE,
        {"user_name": user},
        "name",
    )

    # Stop if the profile does not exist.
    if not profile_name:
        frappe.throw(_("Profile not found."))

    # Load the profile document.
    doc = frappe.get_doc(
        CUSTOMER_PROFILE_DOCTYPE,
        profile_name,
    )

    # Preserve the original authorization check.
    if doc.user_name != user:
        ctx = get_current_user_context(user)

        if not ctx["is_manager"] and not ctx["is_admin"]:
            frappe.throw(
                _("Not authorized."),
                frappe.PermissionError,
            )

    # Retain the original permission-bypass behavior.
    # The ownership/authorization check is performed above.
    doc.flags.ignore_permissions = True
    doc.delete()

    # Clear cached context after deleting the profile.
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    return _("Profile deleted successfully.")


# ============================================================
# SECTION 8: LOGIN REDIRECT
# ============================================================

def get_login_redirect() -> str:
    """
    Return the dashboard URL for the current session user.

    The role priority and dashboard mapping are managed by
    the existing login_service.py module.
    """

    # Read the current session user and delegate dashboard
    # selection to the existing service.
    return get_dashboard_for_user(
        getattr(frappe.session, "user", None)
    )


# ============================================================
# SECTION 9: ASSIGN MULTIPLE USER ROLES
# ============================================================

def assign_user_roles(
    user: str,
    roles: list | str,
) -> dict:
    """
    Assign a complete role list to a specified user.

    Only administrators and VMS managers are authorized.

    This replaces the user's existing role list with the
    validated roles supplied by the caller.
    """

    # Retrieve the current user's authorization context.
    ctx = get_current_user_context()

    # Restrict role assignment to authorized administrators
    # and managers.
    if not (ctx["is_admin"] or ctx["is_manager"]):
        frappe.throw(
            _("Not authorized to assign roles."),
            frappe.PermissionError,
        )

    # Normalize the target user identifier.
    user = (user or "").strip()

    # Confirm that the target user exists.
    if not user or not frappe.db.exists("User", user):
        frappe.throw(
            _("User '{0}' does not exist.").format(user),
            frappe.DoesNotExistError,
        )

    # Convert JSON or comma-separated role input into a list.
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)

        except Exception:
            roles = [
                role.strip()
                for role in roles.split(",")
                if role.strip()
            ]

    # Reject unsupported role input types.
    if not isinstance(roles, (list, tuple, set)):
        frappe.throw(
            _("Roles must be a list or comma-separated string.")
        )

    # Validate that each requested role exists in Frappe.
    clean_roles = []

    for role in roles:
        role_name = str(role).strip()

        if not frappe.db.exists("Role", role_name):
            frappe.throw(
                _("Role '{0}' does not exist.").format(role_name)
            )

        clean_roles.append(role_name)

    # Load the target user's document.
    user_doc = frappe.get_doc("User", user)

    # Remove the existing role table entries.
    user_doc.set("roles", [])

    # Add the newly validated roles.
    for role_name in clean_roles:
        user_doc.append(
            "roles",
            {"role": role_name},
        )

    # Preserve the original permission behavior.
    user_doc.flags.ignore_permissions = True
    user_doc.save()

    # Clear the target user's cached context.
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    # Return the resulting role list.
    return {
        "success": True,
        "user": user,
        "roles": [row.role for row in user_doc.roles],
        "message": _("Roles updated successfully."),
    }


# ============================================================
# SECTION 10: ADD A SINGLE USER ROLE
# ============================================================

def add_user_role(
    user: str,
    role: str,
) -> dict:
    """
    Add one role to an existing user.

    Existing roles are retained.
    """

    # Retrieve the current user's authorization context.
    ctx = get_current_user_context()

    # Only administrators and managers may assign roles.
    if not (ctx["is_admin"] or ctx["is_manager"]):
        frappe.throw(
            _("Not authorized to assign roles."),
            frappe.PermissionError,
        )

    # Normalize the target user and role names.
    user = (user or "").strip()
    role = (role or "").strip()

    # Verify that the target user exists.
    if not user or not frappe.db.exists("User", user):
        frappe.throw(
            _("User '{0}' does not exist.").format(user),
            frappe.DoesNotExistError,
        )

    # Verify that the requested role exists.
    if not role or not frappe.db.exists("Role", role):
        frappe.throw(
            _("Role '{0}' does not exist.").format(role)
        )

    # Load the user and add the requested role.
    user_doc = frappe.get_doc("User", user)
    user_doc.add_roles(role)

    # Clear cached context for the updated user.
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    # Return the updated role list.
    return {
        "success": True,
        "user": user,
        "roles": [row.role for row in user_doc.roles],
        "message": _("Role '{0}' added successfully.").format(role),
    }


# ============================================================
# SECTION 11: REMOVE A SINGLE USER ROLE
# ============================================================

def remove_user_role(
    user: str,
    role: str,
) -> dict:
    """
    Remove one role from an existing user.

    This function retains the original authorization behavior.
    """

    # Retrieve the current user's authorization context.
    ctx = get_current_user_context()

    # Only administrators and managers may modify roles.
    if not (ctx["is_admin"] or ctx["is_manager"]):
        frappe.throw(
            _("Not authorized to modify roles."),
            frappe.PermissionError,
        )

    # Normalize the supplied values.
    user = (user or "").strip()
    role = (role or "").strip()

    # Verify that the target user exists.
    if not user or not frappe.db.exists("User", user):
        frappe.throw(
            _("User '{0}' does not exist.").format(user),
            frappe.DoesNotExistError,
        )

    # Load the target user document.
    user_doc = frappe.get_doc("User", user)

    # Remove the specified role.
    user_doc.remove_roles(role)

    # Clear cached context for the modified user.
    if hasattr(frappe.local, "vms_user_contexts"):
        frappe.local.vms_user_contexts.pop(user, None)

    # Return the updated role list.
    return {
        "success": True,
        "user": user,
        "roles": [row.role for row in user_doc.roles],
        "message": _("Role '{0}' removed successfully.").format(role),
    }


# ============================================================
# SECTION 12: GET USER ROLES
# ============================================================

def get_user_roles(
    user: str | None = None,
) -> dict:
    """
    Return the assigned roles for a user.

    Users may retrieve their own roles.
    Administrators and managers may retrieve another
    user's roles.
    """

    # Retrieve the caller's authorization context.
    ctx = get_current_user_context()

    # Normalize the requested user identifier.
    target_user = (user or "").strip()

    # If no user is supplied, return the caller's own roles.
    if not target_user:
        target_user = ctx["user"]

    # Prevent ordinary users from viewing another user's roles.
    if (
        target_user != ctx["user"]
        and not (ctx["is_admin"] or ctx["is_manager"])
    ):
        frappe.throw(
            _("Not authorized to view roles for other users."),
            frappe.PermissionError,
        )

    # Retrieve roles through Frappe's role utility.
    roles = frappe.get_roles(target_user)

    return {
        "user": target_user,
        "roles": roles,
    }


# ============================================================
# SECTION 13: GET ASSIGNABLE ROLES
# ============================================================

def get_assignable_roles() -> list[str]:
    """
    Return enabled roles that can be assigned.

    Guest and All are excluded, matching the original API.
    Only administrators and managers can access this function.
    """

    # Retrieve the caller's authorization context.
    ctx = get_current_user_context()

    # Enforce the original role-management restriction.
    if not (ctx["is_admin"] or ctx["is_manager"]):
        frappe.throw(
            _("Not authorized."),
            frappe.PermissionError,
        )

    roles = frappe.get_all(
        "Role",
        **apply_pagination({
            "filters": {
                "disabled": 0,
                "name": ["not in", ["Guest", "All"]],
            },
            "pluck": "name",
            "order_by": "name asc",
        })
    )

    return roles


# ============================================================
# END OF SERVICES
# ============================================================