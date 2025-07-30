# LiveFxHub CRM Views Documentation

This document provides an in-depth explanation of all views in the LiveFxHub CRM system.

## Main Views (views.py)

### Authentication Views

#### login_view
- **Purpose**: Authenticates users and creates session
- **Logic**:
  - Validates user credentials
  - Creates session token
  - Redirects to dashboard on success
  - Shows error message on failure
- **URL**: `/accounts/login/`
- **Template**: `login.html`
- **Decorators**: None (accessible to unauthenticated users)

#### logout_view
- **Purpose**: Logs out users and destroys session
- **Logic**:
  - Invalidates current session
  - Redirects to login page
- **URL**: `/accounts/logout/`
- **Template**: Redirects to login page
- **Decorators**: `login_required`

#### register_view
- **Purpose**: Creates new user accounts
- **Logic**:
  - Validates registration form data
  - Creates new User and UserProfile objects
  - Sends welcome email
  - Redirects to login page
- **URL**: `/accounts/register/`
- **Template**: `register.html`
- **Decorators**: None (accessible to unauthenticated users)

### Dashboard Views

#### dashboard_view
- **Purpose**: Main dashboard showing overview
- **Logic**:
  - Retrieves counts of leads, contacts, accounts, deals, tasks
  - Calculates revenue metrics
  - Fetches recent activities
  - Provides upcoming tasks
- **URL**: `/dashboard/`
- **Template**: `dashboard.html`
- **Decorators**: `login_required`

#### dashboard (API)
- **Purpose**: Provides data for dashboard via REST API
- **Logic**:
  - Aggregates statistics for leads, contacts, accounts, deals, tasks
  - Categorizes deals by stage
  - Provides serialized data for recent leads, deals, tasks
- **URL**: `/api/dashboard/`
- **Returns**: JSON data
- **Decorators**: `login_required`, `api_view(['GET'])`

### Entity Views

#### AccountViews

##### account_list
- **Purpose**: Displays list of accounts
- **Logic**:
  - Fetches all accounts
  - Provides filtering and sorting
  - Handles pagination
- **URL**: `/accounts/`
- **Template**: `accounts/list.html`
- **Decorators**: `login_required`

##### account_detail
- **Purpose**: Shows detailed view of an account
- **Logic**:
  - Retrieves specific account
  - Fetches related contacts, deals, tasks, notes
  - Provides activity timeline
- **URL**: `/accounts/<id>/`
- **Template**: `accounts/detail.html`
- **Decorators**: `login_required`

##### account_create
- **Purpose**: Creates new account
- **Logic**:
  - Validates form data
  - Creates account in database
  - Associates with current user
- **URL**: `/accounts/create/`
- **Template**: `accounts/form.html`
- **Decorators**: `login_required`

##### account_update
- **Purpose**: Updates existing account
- **Logic**:
  - Pre-populates form with existing data
  - Validates changes
  - Updates record
- **URL**: `/accounts/<id>/edit/`
- **Template**: `accounts/form.html`
- **Decorators**: `login_required`

##### account_delete
- **Purpose**: Deletes account
- **Logic**:
  - Confirms deletion
  - Removes record and related data
- **URL**: `/accounts/<id>/delete/`
- **Template**: Confirmation page
- **Decorators**: `login_required`

#### ContactViews

Similar structure to AccountViews with the following endpoints:
- `contact_list`: `/contacts/`
- `contact_detail`: `/contacts/<id>/`
- `contact_create`: `/contacts/create/`
- `contact_update`: `/contacts/<id>/edit/`
- `contact_delete`: `/contacts/<id>/delete/`

#### LeadViews

Similar structure with the following endpoints:
- `lead_list`: `/leads/`
- `lead_detail`: `/leads/<id>/`
- `lead_create`: `/leads/create/`
- `lead_update`: `/leads/<id>/edit/`
- `lead_delete`: `/leads/<id>/delete/`
- `lead_convert`: `/leads/<id>/convert/` (Special function to convert lead to account/contact/deal)

#### DealViews

Similar structure with the following endpoints:
- `deal_list`: `/deals/`
- `deal_detail`: `/deals/<id>/`
- `deal_create`: `/deals/create/`
- `deal_update`: `/deals/<id>/edit/`
- `deal_delete`: `/deals/<id>/delete/`
- `deal_kanban`: `/deals/kanban/` (Special view for kanban board visualization)
- `deal_stage_update`: `/deals/<id>/stage/` (API endpoint to update deal stage via drag-and-drop)

#### TaskViews

Similar structure with task-specific views and status updates.

#### EventViews

Calendar-focused views for managing appointments and meetings.

#### TransactionViews

##### transaction_list
- **Purpose**: Lists all transactions
- **Logic**:
  - Fetches transactions
  - Calculates totals
  - Provides filtering by date, type, account
- **URL**: `/transactions/`
- **Template**: `transactions/list.html`
- **Decorators**: `login_required`
- **Security**: Enforces the "from_dashboard" check for enhanced security

##### transaction_detail
- **Purpose**: Shows transaction details
- **Logic**:
  - Retrieves specific transaction
  - Shows related documents
- **URL**: `/transactions/<id>/`
- **Template**: `transactions/detail.html`
- **Decorators**: `login_required`
- **Security**: Only accessible if user came from dashboard (session variable check)

##### transaction_create
- **Purpose**: Creates new transaction
- **Logic**:
  - Validates form
  - Creates record
  - Updates account/deal balances
- **URL**: `/transactions/create/`
- **Template**: `transactions/form.html`
- **Decorators**: `login_required`

#### ProductViews

Standard CRUD views for product management.

## Admin Views (admin_views.py)

### Dashboard

#### admin_dashboard
- **Purpose**: Main admin control panel
- **Logic**:
  - Aggregates system-wide metrics
  - Shows recent activity across all users
  - Provides quick links to all admin functions
- **URL**: `/admin/dashboard/`
- **Template**: `admin/dashboard.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Account Management

#### admin_accounts
- **Purpose**: Admin interface for account management
- **Logic**:
  - Lists all accounts
  - Provides advanced filtering and sorting
  - Shows account metrics and statistics
- **URL**: `/admin/accounts/`
- **Template**: `admin/accounts.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

#### admin_account_detail
- **Purpose**: Detailed admin view of account
- **Logic**:
  - Shows complete account information
  - Provides access to all related entities
  - Displays activity history
- **URL**: `/admin/accounts/<id>/`
- **Template**: `admin/account_detail.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Lead Management

#### admin_leads
- **Purpose**: Admin interface for lead management
- **Logic**:
  - Lists all leads
  - Shows conversion rates
  - Provides lead source analytics
- **URL**: `/admin/leads/`
- **Template**: `admin/leads.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Deal Management

#### admin_deals
- **Purpose**: Admin interface for deal pipeline
- **Logic**:
  - Shows deals by stage
  - Calculates win rates and pipeline value
  - Provides forecasting tools
- **URL**: `/admin/deals/`
- **Template**: `admin/deals.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

#### admin_deal_import
- **Purpose**: Bulk import deals from CSV
- **Logic**:
  - Validates CSV format
  - Maps columns to database fields
  - Creates deal records
  - Reports success/failures
- **URL**: `/admin/deals/import/`
- **Template**: Uses AJAX/form submission in `admin/deals.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

#### admin_download_deal_template
- **Purpose**: Provides CSV template for deal import
- **Logic**:
  - Generates CSV file with correct headers
  - Sends file as download response
- **URL**: `/admin/deals/template/`
- **Template**: None (file download)
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Task Management

#### admin_tasks
- **Purpose**: Admin interface for task management
- **Logic**:
  - Lists all tasks
  - Shows completion rates
  - Provides assignment tools
- **URL**: `/admin/tasks/`
- **Template**: `admin/tasks.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Product Management

#### admin_products
- **Purpose**: Admin interface for product catalog
- **Logic**:
  - Lists all products
  - Shows inventory status
  - Provides sales metrics
- **URL**: `/admin/products/`
- **Template**: `admin/products.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Reporting

#### admin_reports
- **Purpose**: Business intelligence dashboard
- **Logic**:
  - Aggregates sales data
  - Calculates key performance indicators
  - Generates charts and visualizations
  - Shows deals closed, average deal size, new customers
  - Includes top products data with trend information
  - Provides account sales data with trend metrics
- **URL**: `/admin/reports/`
- **Template**: `admin/reports.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

### Settings

#### admin_settings
- **Purpose**: System configuration
- **Logic**:
  - Provides access to global settings
  - Allows customization of system behavior
  - Manages user permissions
- **URL**: `/admin/settings/`
- **Template**: `admin/settings.html`
- **Decorators**: `login_required`, `user_passes_test(is_admin)`

## API ViewSets (views.py)

### IndustryViewSet
- **Purpose**: REST API for Industry model
- **Operations**: CRUD operations
- **URL**: `/api/industries/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, description
- **Ordering**: name, created_at

### AccountViewSet
- **Purpose**: REST API for Account model
- **Operations**: CRUD operations
- **URL**: `/api/accounts/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, industry, city, state
- **Ordering**: name, created_at, updated_at

### ContactViewSet
- **Purpose**: REST API for Contact model
- **Operations**: CRUD operations
- **URL**: `/api/contacts/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, account, email
- **Ordering**: last_name, created_at

### LeadViewSet
- **Purpose**: REST API for Lead model
- **Operations**: CRUD operations
- **URL**: `/api/leads/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, company, status, source
- **Ordering**: created_at, status
- **Custom Actions**: convert (POST)

### DealViewSet
- **Purpose**: REST API for Deal model
- **Operations**: CRUD operations
- **URL**: `/api/deals/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, account, stage, amount
- **Ordering**: amount, expected_close_date, stage
- **Custom Actions**: update_stage (PATCH)

### TaskViewSet
- **Purpose**: REST API for Task model
- **Operations**: CRUD operations
- **URL**: `/api/tasks/`
- **Permissions**: `IsAuthenticated`
- **Filters**: title, status, priority, due_date
- **Ordering**: due_date, priority, status
- **Custom Actions**: complete (PATCH)

### EventViewSet
- **Purpose**: REST API for Event model
- **Operations**: CRUD operations
- **URL**: `/api/events/`
- **Permissions**: `IsAuthenticated`
- **Filters**: title, start_date, end_date
- **Ordering**: start_date

### TransactionViewSet
- **Purpose**: REST API for Transaction model
- **Operations**: CRUD operations
- **URL**: `/api/transactions/`
- **Permissions**: `IsAuthenticated`
- **Filters**: account, deal, transaction_type, amount
- **Ordering**: transaction_date, amount

### ProductViewSet
- **Purpose**: REST API for Product model
- **Operations**: CRUD operations
- **URL**: `/api/products/`
- **Permissions**: `IsAuthenticated`
- **Filters**: name, category, unit_price
- **Ordering**: name, unit_price
