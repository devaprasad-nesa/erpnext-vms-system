app_name = "vms_user"
app_title = "Vms User"
app_publisher = "vmsdeveloper"
app_description = "vms user application"
app_email = "developer@vmssoftware.com"
app_license = "mit"

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "vms_user",
# 		"logo": "/assets/vms_user/logo.png",
# 		"title": "Vms User",
# 		"route": "/vms_user",
# 		"has_permission": "vms_user.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `vms_user/dock/vms_user/vms_user.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/vms_user/css/vms_user.css"
# app_include_js = "/assets/vms_user/js/vms_user.js"

# include js, css files in header of web template
web_include_css = "/assets/vms_user/css/vms-login.css"
web_include_js = "/assets/vms_user/js/customer_login.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "vms_user/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "vms_user/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "login"

website_route_rules = [
    {"from_route": "/customer-dashboard", "to_route": "vms_user_dashboard/user_dashboard/customer-home"},
    {"from_route": "/customer-home", "to_route": "vms_user_dashboard/user_dashboard/customer-home"},
    {"from_route": "/vehicle-register", "to_route": "vms_user_dashboard/user_dashboard/vehicle-register"},
    {"from_route": "/my-vehicles", "to_route": "vms_user_dashboard/user_dashboard/my-vehicles"},
    {"from_route": "/customer-vehicles", "to_route": "vms_user_dashboard/user_dashboard/my-vehicles"},
    {"from_route": "/technician-dashboard", "to_route": "vms_user_dashboard/technician_dashboard/technician-dashboard"},
    {"from_route": "/technician-dashboard/vehicle-service-list", "to_route": "technician-dashboard/vehicle-service-list"},
    {"from_route": "/vehicle-service-list", "to_route": "technician-dashboard/vehicle-service-list"},
    {"from_route": "/technician-dashboard/technician-inspection", "to_route": "vms_user_dashboard/technician_dashboard/technician-inspection"},
    {"from_route": "/vms-inspection", "to_route": "vms_user_dashboard/technician_dashboard/technician-inspection"},
    {"from_route": "/login-page/login", "to_route": "login"},
    {"from_route": "/login-page/vms-login", "to_route": "login"},
    {"from_route": "/vms-login", "to_route": "login"},
    {"from_route": "/account-dashboard", "to_route": "vms_user_dashboard/accountant_dashboard/account-dashboard"},
    {"from_route": "/vms-account-invoice", "to_route": "vms_user_dashboard/accountant_dashboard/account-invoice"},
    {"from_route": "/account-invoice", "to_route": "vms_user_dashboard/accountant_dashboard/account-invoice"},
    {"from_route": "/mechanic-dashboard", "to_route": "vms_user_dashboard/mechanic_dashboard/mechanic_dashboard"},
]


# website user home page (by Role)
# See the canonical role_home_page dict at the bottom of this file.


# Setup Wizard
# ------------

# open a fresh site's setup in this app's own UI instead of the desk wizard.
# must be a non-desk route (not under /desk or /app); to customize setup within
# desk, use setup_wizard_stages / setup_wizard_complete instead.
# setup_wizard_url = "/vms_user/setup"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "vms_user.utils.jinja_methods",
# 	"filters": "vms_user.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "vms_user.install.before_install"
# after_install = "vms_user.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "vms_user.uninstall.before_uninstall"
# after_uninstall = "vms_user.uninstall.after_uninstall"

# Disable / Enable
# ----------------
# Called when this app is logically disabled or re-enabled on a site,
# without uninstalling it. Use this to hide/restore fields this app adds
# to other apps' doctypes.

# before_disable = "vms_user.uninstall.before_disable"
# after_disable = "vms_user.uninstall.after_disable"
# before_enable = "vms_user.install.before_enable"
# after_enable = "vms_user.install.after_enable"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "vms_user.utils.before_app_install"
# after_app_install = "vms_user.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "vms_user.utils.before_app_uninstall"
# after_app_uninstall = "vms_user.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "vms_user.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "vms_user.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "vms_user.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["vms_user.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
    "vms customer profile": "vms_user.services.permissions.vms_customer_profile_query",
    "User": "vms_user.services.permissions.vms_user_query"
}

has_permission = {
	"Event": "frappe.desk.doctype.event.event.has_permission",
    "vms customer profile": "vms_user.services.permissions.vms_customer_profile_has_permission",
    "User": "vms_user.services.permissions.vms_user_has_permission"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User": {
        "before_insert": "vms_user.services.user_events.assign_customer_role"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"vms_user.tasks.all"
# 	],
# 	"daily": [
# 		"vms_user.tasks.daily"
# 	],
# 	"hourly": [
# 		"vms_user.tasks.hourly"
# 	],
# 	"weekly": [
# 		"vms_user.tasks.weekly"
# 	],
# 	"monthly": [
# 		"vms_user.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "vms_user.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "vms_user.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "vms_user.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "vms_user.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["vms_user.utils.before_request"]
# after_request = ["vms_user.utils.after_request"]

# Job Events
# ----------
# before_job = ["vms_user.utils.before_job"]
# after_job = ["vms_user.utils.after_job"]

# after_file_upload = ["vms_user.utils.after_file_upload"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"vms_user.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


role_home_page = {
    "Administrator": "app",
    "vms customer": "customer-home",
    "Customer": "customer-home",
    "vms technician": "technician-dashboard",
    "vms mechanic": "mechanic-dashboard",
    "vms accountant": "account-dashboard",
    "vms manager": "app",
    "System Manager": "app",
}