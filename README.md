# Vehicle Management System (VMS)

A web-based **Vehicle Management System (VMS)** built using the **Frappe Framework** and **ERPNext 14**.

The system manages the complete vehicle service workflow, including customer registration, vehicle registration, service booking, technician inspection, mechanic operations, spare parts, and accounts/invoicing.

---

## 🚀 Features

### Customer Management

* Customer registration and login
* Customer dashboard
* Customer profile management
* View registered vehicles
* Register new vehicles
* View vehicle service requests
* Book vehicle service slots
* Track service/booking status

### Vehicle Management

* Vehicle registration
* Vehicle brand selection
* Vehicle model selection based on the selected brand
* Fuel type selection
* Customer-vehicle association
* View vehicles belonging to the logged-in customer

### Vehicle Service Registration

* Service booking by customers
* Date-based service booking
* Available service-slot selection
* Booking status tracking
* Vehicle and customer association
* Daily vehicle intake restrictions

### Technician Management

* Technician dashboard
* View vehicle service requests
* Vehicle inspection
* Add service descriptions
* Identify vehicle issues
* Add required spare parts
* Assign information to mechanics
* Send inspection information to accounts and management

### Mechanic Management

* Mechanic dashboard
* View vehicles assigned to the logged-in mechanic
* View vehicle inspection details
* View required spare parts
* Update service/booking status

### Accounts Management

* Accounts dashboard
* View vehicle service information
* Calculate service amount
* Calculate spare-part costs
* Generate invoices
* Manage customer billing information

### Role-Based Access

The project uses Frappe's role and permission system.

Example roles include:

* `vms customer`
* `vms technician`
* `vms mechanic`
* `vms accounts`
* `System Manager`

Users are provided access to dashboards and operations based on their assigned roles.

---

# 🏗️ Project Architecture

The project is based on the Frappe Framework and ERPNext.

```text
erpnext-vms-system/
│
├── vms-system/
│   │
│   ├── apps/
│   │   ├── frappe/
│   │   ├── erpnext/
│   │   ├── vms_user/
│   │   ├── vms_vehicle/
│   │   ├── vms_inspection/
│   │   └── vms_account/
│   │
│   ├── sites/
│   │   ├── apps.txt
│   │   └── vms.localhost/
│   │
│   ├── config/
│   │
│   └── Procfile
│
└── README.md
```

> The exact application names may vary depending on the branch/version of the project.

---

# 🛠️ Technology Stack

| Technology       | Purpose                       |
| ---------------- | ----------------------------- |
| Frappe Framework | Backend framework             |
| ERPNext 14       | ERP functionality             |
| Python           | Backend development           |
| MariaDB          | Database                      |
| Redis            | Cache and background jobs     |
| Node.js          | Frontend asset building       |
| npm              | JavaScript package management |
| Yarn             | Frappe asset management       |
| Nginx            | Web server                    |
| Git              | Version control               |

---

# 📋 Prerequisites

Before installing the project, make sure the following software is installed.

### Required

* Git
* Python 3
* Node.js
* npm
* Yarn
* MariaDB
* Redis
* wkhtmltopdf
* Frappe Bench dependencies

For ERPNext 14, use versions compatible with the Frappe/ERPNext 14 branch.

Check the installed versions:

```bash
git --version
python3 --version
node --version
npm --version
yarn --version
mariadb --version
redis-server --version
```

---

# 📥 Clone the Project

Clone the repository:

```bash
git clone https://github.com/devaprasad-nesa/erpnext-vms-system.git
```

Enter the project directory:

```bash
cd erpnext-vms-system
```

Check the available branches:

```bash
git branch -a
```

Switch to the required branch.

For example:

```bash
git checkout develop
```

Or:

```bash
git checkout main
```

Pull the latest changes:

```bash
git pull origin develop
```

---

# 📂 Enter the Frappe Bench

The Frappe bench is located inside the project directory.

```bash
cd vms-system
```

Check the bench:

```bash
bench --version
```

Check the installed applications:

```bash
bench list-apps
```

You should see applications similar to:

```text
frappe
erpnext
vms_user
vms_vehicle
vms_inspection
vms_account
```

---

# 🔧 Install Python Dependencies

Activate the bench environment if required:

```bash
source env/bin/activate
```

Then install/update dependencies:

```bash
bench setup requirements
```

If the project already contains the required environment, you can normally proceed with the bench commands.

---

# 📦 Install Node Dependencies

Install the required JavaScript packages:

```bash
yarn install
```

If dependencies need to be rebuilt:

```bash
bench setup requirements
```

Then build the Frappe assets:

```bash
bench build
```

For development, you can also use:

```bash
bench watch
```

---

# 🗄️ Database Setup

Make sure MariaDB is running:

```bash
sudo systemctl start mariadb
```

Check its status:

```bash
sudo systemctl status mariadb
```

Start Redis:

```bash
sudo systemctl start redis-server
```

Check Redis:

```bash
redis-cli ping
```

Expected output:

```text
PONG
```

---

# 🌐 Configure the Site

The project uses the site:

```text
vms.localhost
```

Check the available sites:

```bash
ls sites
```

You should see:

```text
vms.localhost
```

Set the default site:

```bash
bench use vms.localhost
```

Verify the current site:

```bash
bench use
```

---

# 📱 Install VMS Applications

Check installed applications:

```bash
bench list-apps
```

If the custom VMS applications are already present in the repository but not installed on the site, install them.

For example:

```bash
bench --site vms.localhost install-app vms_user
```

```bash
bench --site vms.localhost install-app vms_vehicle
```

```bash
bench --site vms.localhost install-app vms_inspection
```

```bash
bench --site vms.localhost install-app vms_account
```

Install ERPNext if it is not already installed:

```bash
bench --site vms.localhost install-app erpnext
```

> Do not run an `install-app` command for an application that is already installed on the site.

Check the final application list:

```bash
bench --site vms.localhost list-apps
```

---

# 🔄 Run Database Migrations

After cloning or updating the project, run:

```bash
bench --site vms.localhost migrate
```

Clear the cache:

```bash
bench --site vms.localhost clear-cache
```

Clear website cache:

```bash
bench --site vms.localhost clear-website-cache
```

---

# 🏗️ Build Frontend Assets

Build the application assets:

```bash
bench build
```

If you are actively developing the frontend:

```bash
bench watch
```

---

# ▶️ Start the VMS Project

Start the Frappe development server:

```bash
bench start
```

You should see services similar to:

```text
web
socketio
watch
schedule
worker
redis_cache
redis_queue
```

The development server will normally be available at:

```text
http://vms.localhost:8000
```

You can also use:

```text
http://127.0.0.1:8000
```

---

# 🔐 Login

Open:

```text
http://vms.localhost:8000
```

For administrator access, use the administrator credentials configured for the site.

If the administrator password needs to be reset:

```bash
bench --site vms.localhost set-admin-password
```

The command will prompt you for a new password.

---

# 👤 User Roles

The VMS application uses role-based access.

## Customer

Role:

```text
vms customer
```

Customer functionality includes:

* Customer dashboard
* Vehicle registration
* Vehicle list
* Service booking
* Service status

---

## Technician

Role:

```text
vms technician
```

Technician functionality includes:

* Technician dashboard
* Vehicle service requests
* Vehicle inspection
* Issue reporting
* Spare-part requirements
* Service information

---

## Mechanic

Role:

```text
vms mechanic
```

Mechanic functionality includes:

* Assigned vehicle list
* Vehicle inspection information
* Required spare parts
* Service status updates

---

## Accounts

Role:

```text
vms accounts
```

Accounts functionality includes:

* Service information
* Spare-part information
* Cost calculation
* Invoice management
* Customer billing

---

# 🔄 VMS Service Workflow

The general workflow is:

```text
Customer
   │
   ▼
Customer Registration / Login
   │
   ▼
Vehicle Registration
   │
   ▼
Service Booking
   │
   ▼
Vehicle Service Registration
   │
   ▼
Technician Inspection
   │
   ├──► Issue Description
   │
   └──► Required Spare Parts
   │
   ▼
Mechanic
   │
   └──► Vehicle Service
   │
   ▼
Accounts
   │
   ├──► Spare Parts Cost
   ├──► Service Cost
   └──► Invoice
   │
   ▼
Customer
```

---

# 🗓️ Service Slot Management

The VMS supports service-slot-based booking.

A customer selects:

```text
Vehicle
   ↓
Service Date
   ↓
Available Slot
```

The system validates the booking against the configured vehicle intake limits.

The project can be configured to restrict:

* Vehicles per service slot
* Vehicles per day
* Saturday capacity
* Monday holidays
* Already-booked slots

---

# 🧩 Custom VMS Applications

## vms_user

Responsible for:

* Customer authentication
* Customer dashboard
* Customer-related webpages
* User-specific operations
* Customer portal

---

## vms_vehicle

Responsible for:

* Vehicle registration
* Vehicle information
* Vehicle brands
* Vehicle models
* Fuel types
* Customer-vehicle relationships

---

## vms_inspection

Responsible for:

* Vehicle inspection
* Technician dashboard
* Spare parts
* Service issues
* Mechanic assignments
* Inspection workflow

---

## vms_account

Responsible for:

* Accounts dashboard
* Service billing
* Cost calculation
* Invoice-related operations
* Customer billing

---

# 🔌 Frappe API

The project uses Frappe whitelisted Python methods for communication between webpages and the backend.

Example:

```python
@frappe.whitelist()
def get_my_vehicles():
    ...
```

The API can then be called from JavaScript:

```javascript
frappe.call({
    method: "vms_vehicle.api.get_my_vehicles",
    callback: function (response) {
        console.log(response.message);
    }
});
```

For APIs that require authentication, the logged-in Frappe session is used.

---

# 🧹 Useful Development Commands

### Check site

```bash
bench --site vms.localhost list-apps
```

### Migrate database

```bash
bench --site vms.localhost migrate
```

### Clear cache

```bash
bench --site vms.localhost clear-cache
```

### Clear website cache

```bash
bench --site vms.localhost clear-website-cache
```

### Build assets

```bash
bench build
```

### Restart bench

```bash
bench restart
```

### Check bench health

```bash
bench doctor
```

### Open Frappe console

```bash
bench --site vms.localhost console
```

### Open MariaDB console

```bash
bench --site vms.localhost mariadb
```

---

# 🐛 Troubleshooting

## Redis connection error

If you see:

```text
Could not connect to Redis
```

check Redis:

```bash
redis-cli ping
```

Then check:

```bash
bench doctor
```

Restart Redis if required:

```bash
sudo systemctl restart redis-server
```

---

## Site does not load

Check:

```bash
bench --site vms.localhost doctor
```

Then run:

```bash
bench --site vms.localhost migrate
```

Clear cache:

```bash
bench --site vms.localhost clear-cache
```

Restart:

```bash
bench start
```

---

## Whitelist API error

If you get:

```text
Function ... is not whitelisted
```

make sure the Python function contains:

```python
@frappe.whitelist()
```

Example:

```python
import frappe

@frappe.whitelist()
def get_my_vehicles():
    return []
```

Then clear the cache:

```bash
bench --site vms.localhost clear-cache
```

---

## Permission Error

If a user receives:

```text
PermissionError
```

check:

1. User role
2. Role permissions
3. DocType permissions
4. User permissions
5. API authentication
6. Whether the API requires a logged-in user

Check the user's roles from:

```text
Desk → User
```

---

# 🔄 Updating the Project

Before updating, check the current branch:

```bash
git branch
```

Pull the latest changes:

```bash
git pull origin develop
```

Then migrate:

```bash
bench --site vms.localhost migrate
```

Build assets:

```bash
bench build
```

Clear cache:

```bash
bench --site vms.localhost clear-cache
```

Start the server:

```bash
bench start
```

---

# 🌿 Git Branches

The project uses Git for version control.

Example workflow:

```text
develop
   │
   ├── Development
   ├── Testing
   └── Bug Fixes
          │
          ▼
        main
          │
          └── Stable Version
```

Switch to development:

```bash
git checkout develop
```

Update:

```bash
git pull origin develop
```

Push changes:

```bash
git add .
git commit -m "Update VMS application"
git push origin develop
```

After testing, merge the development branch into `main`.

---

# ⚠️ Important Git Files

Do not commit generated runtime data such as:

```text
sites/*/logs/
sites/*/private/backups/
```

Make sure these are handled by `.gitignore`.

The source code of your custom applications should be committed.

---

# 🔒 Security

Do not commit:

* Database passwords
* API keys
* Secret keys
* Production credentials
* Private certificates
* User passwords
* Sensitive configuration files

Before pushing changes:

```bash
git status
```

Review modified files:

```bash
git diff
```

Then commit only the required source files.

---

# 📁 Recommended Development Structure

Custom application code should remain inside:

```text
vms-system/apps/
```

For example:

```text
vms-system/apps/
├── frappe/
├── erpnext/
├── vms_user/
├── vms_vehicle/
├── vms_inspection/
└── vms_account/
```

Custom webpages should generally be maintained inside the corresponding custom app rather than directly modifying Frappe or ERPNext core files.

---

# 🧪 Development Checklist

After cloning the repository:

```bash
cd erpnext-vms-system
cd vms-system
```

Verify:

```bash
bench --version
bench list-apps
```

Then:

```bash
bench use vms.localhost
bench --site vms.localhost list-apps
bench --site vms.localhost migrate
bench --site vms.localhost clear-cache
bench build
bench start
```

Open:

```text
http://vms.localhost:8000
```

---

# 📌 Quick Start

For an already-configured project/site, the basic startup procedure is:

```bash
git clone https://github.com/devaprasad-nesa/erpnext-vms-system.git

cd erpnext-vms-system/vms-system

git checkout develop

bench use vms.localhost

bench --site vms.localhost migrate

bench --site vms.localhost clear-cache

bench build

bench start
```

Then open:

```text
http://vms.localhost:8000
```

---

# 📜 License

This project is intended for educational and development purposes.

---

# 👨‍💻 Author

**Deva Prasad NR**

Vehicle Management System built using:

```text
Frappe Framework
ERPNext 14
Python
MariaDB
Redis
JavaScript
HTML
CSS
```

---

# 🤝 Contributing

1. Clone the repository.

2. Create or switch to the development branch:

```bash
git checkout develop
```

3. Create your changes.

4. Test the changes locally.

5. Check the Git status:

```bash
git status
```

6. Stage the required files:

```bash
git add .
```

7. Commit:

```bash
git commit -m "Describe your changes"
```

8. Push:

```bash
git push origin develop
```

9. After testing, merge the changes into `main`.

---

# 📞 Project Repository

GitHub repository:

https://github.com/devaprasad-nesa/erpnext-vms-system.git
