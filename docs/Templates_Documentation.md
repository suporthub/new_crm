# LiveFxHub CRM Templates Documentation

This document provides an in-depth explanation of all templates in the LiveFxHub CRM system.

## Base Templates

### base.html

- **Purpose**: Main template used as the foundation for all client-facing pages
- **Key Features**:
  - Bootstrap 5 responsive layout
  - Navigation sidebar
  - Header with user profile dropdown
  - Notifications area
  - Footer with copyright and links
  - JavaScript includes (jQuery, Bootstrap, Custom JS)
- **Blocks**:
  - `{% block title %}` - Page title
  - `{% block extra_css %}` - Additional CSS for specific pages
  - `{% block content %}` - Main content area
  - `{% block extra_js %}` - Additional JavaScript for specific pages
- **Context Required**:
  - `user` - Current logged-in user
  - `notifications` - User notifications
  - `active_page` - Current active page for nav highlighting

### base_admin.html

- **Purpose**: Foundation template for all admin interface pages
- **Key Features**:
  - Dark-themed admin layout
  - Admin-specific navigation
  - Dashboard shortcuts
  - Admin notifications panel
  - Enhanced JavaScript for admin functions
- **Blocks**:
  - `{% block admin_title %}` - Admin page title
  - `{% block admin_css %}` - Admin-specific CSS
  - `{% block admin_content %}` - Main admin content area
  - `{% block admin_js %}` - Admin-specific JavaScript
- **Context Required**:
  - `user` - Admin user
  - `admin_notifications` - Admin-specific notifications
  - `active_page` - Current admin page for nav highlighting

## Authentication Templates

### login.html

- **Purpose**: User login screen
- **Key Components**:
  - Login form with username/email and password fields
  - "Remember me" checkbox
  - Forgot password link
  - Register new account link
  - Error message display area
- **Form Processing**:
  - Submits to `/accounts/login/`
  - Validates credentials
  - Redirects to dashboard on success
- **Context Required**:
  - `form` - LoginForm instance
  - `error` - Error message (if any)

### register.html

- **Purpose**: New user registration
- **Key Components**:
  - Registration form with fields:
    - Username
    - Email
    - Password
    - Confirm password
    - First name
    - Last name
  - Terms and conditions checkbox
  - Login link for existing users
- **Form Processing**:
  - Submits to `/accounts/register/`
  - Validates form data
  - Creates new user account
  - Displays success message
- **Context Required**:
  - `form` - RegistrationForm instance
  - `error` - Error message (if any)

### password_reset.html

- **Purpose**: Password recovery form
- **Key Components**:
  - Email input field
  - Submit button
  - Login link
  - Instructions for password recovery
- **Form Processing**:
  - Submits to `/accounts/password/reset/`
  - Sends password reset email
  - Shows confirmation
- **Context Required**:
  - `form` - PasswordResetForm instance

## Main Templates

### dashboard.html

- **Purpose**: Main user dashboard
- **Key Sections**:
  - Summary statistics cards (leads, contacts, deals, etc.)
  - Recent activities list
  - Upcoming tasks
  - Deals pipeline visualization
  - Quick action buttons
- **JavaScript Features**:
  - Chart.js visualizations
  - AJAX data refreshing
  - Task completion toggles
  - `showTransaction()` function - Sets session flag and redirects to transaction view
- **Context Required**:
  - `stats` - Dashboard statistics
  - `recent_activities` - Recent activity list
  - `upcoming_tasks` - Pending tasks
  - `deals_by_stage` - Deal pipeline data

### index.html

- **Purpose**: Landing page for non-authenticated users
- **Key Sections**:
  - Hero section with CRM benefits
  - Feature highlights
  - Testimonials
  - Call-to-action buttons
  - Login/register links
- **Context Required**:
  - None (static content)

## Entity Templates

### accounts/list.html

- **Purpose**: Lists all accounts
- **Key Components**:
  - Search and filter panel
  - Accounts table with columns:
    - Name
    - Industry
    - Location
    - Phone
    - Assigned To
    - Actions
  - Pagination controls
  - "Create Account" button
- **JavaScript Features**:
  - Sorting functionality
  - Filter toggling
  - AJAX pagination
- **Context Required**:
  - `accounts` - List of accounts
  - `industries` - List of industries (for filtering)
  - `page_obj` - Pagination object

### accounts/detail.html

- **Purpose**: Detailed view of single account
- **Key Sections**:
  - Account information card
  - Related contacts list
  - Related deals table
  - Recent activities timeline
  - Notes and documents section
  - Edit/delete buttons
- **Tabs**:
  - Overview
  - Contacts
  - Deals
  - Documents
  - Notes
  - Activities
- **Context Required**:
  - `account` - Account object
  - `contacts` - Related contacts
  - `deals` - Related deals
  - `notes` - Account notes
  - `documents` - Account documents
  - `activities` - Account activity history

### accounts/form.html

- **Purpose**: Form for creating/editing accounts
- **Form Fields**:
  - Name
  - Website
  - Phone
  - Email
  - Industry (dropdown)
  - Address fields
  - Assigned To (user dropdown)
  - Description (rich text)
- **Form Processing**:
  - Submits to create/update view
  - Client-side validation
  - Server-side validation
  - Success/error feedback
- **Context Required**:
  - `form` - AccountForm instance
  - `industries` - Industries for dropdown
  - `users` - Users for assignment dropdown
  - `is_edit` - Boolean for create/edit mode

### contacts/list.html, contacts/detail.html, contacts/form.html

Similar structure to account templates but with contact-specific fields and relationships.

### leads/list.html, leads/detail.html, leads/form.html

Similar structure with lead-specific fields and conversion functionality.

### deals/list.html

- **Purpose**: Lists all deals
- **Key Components**:
  - Search and filter panel
  - Deals table with columns:
    - Name
    - Account
    - Stage
    - Amount
    - Expected Close Date
    - Assigned To
    - Actions
  - Pagination controls
  - "Create Deal" button
- **Context Required**:
  - `deals` - List of deals
  - `stages` - Deal stages (for filtering)
  - `page_obj` - Pagination object

### deals/kanban.html

- **Purpose**: Kanban board visualization of deal pipeline
- **Key Components**:
  - Stage columns (one for each deal stage)
  - Deal cards within each column
  - Stage totals (count and value)
  - Drag-and-drop interface
- **JavaScript Features**:
  - Drag-and-drop between stages
  - AJAX stage updates
  - Deal details modal
- **Context Required**:
  - `stages` - Deal stages
  - `deals_by_stage` - Deals organized by stage
  - `stage_totals` - Count and value by stage

### tasks/list.html, tasks/detail.html, tasks/form.html

Task management templates with task-specific components.

### events/list.html, events/detail.html, events/form.html

Event management templates with calendar integration.

### transactions/list.html

- **Purpose**: Lists all transactions
- **Key Components**:
  - Date range filter
  - Transaction type filter (income/expense)
  - Transactions table with columns:
    - Date
    - Account
    - Deal
    - Type
    - Amount
    - Category
    - Actions
  - Totals summary
- **Context Required**:
  - `transactions` - List of transactions
  - `total_income` - Sum of income transactions
  - `total_expense` - Sum of expense transactions
  - `net` - Net balance

### transactions/detail.html

- **Purpose**: Detailed view of single transaction
- **Key Components**:
  - Transaction information card
  - Related account/deal links
  - Documents section
  - Notes section
  - Edit/delete buttons
  - "Back to Dashboard" button
- **JavaScript Features**:
  - Security check for access from dashboard
  - "Refresh" button functionality
- **Context Required**:
  - `transaction` - Transaction object
  - `documents` - Related documents
  - `notes` - Transaction notes
  - `from_dashboard` - Boolean from session

### products/list.html, products/detail.html, products/form.html

Product management templates with product-specific components.

## Admin Templates

### admin/dashboard.html

- **Purpose**: Admin control center
- **Key Sections**:
  - System overview statistics
  - Recent user activity
  - Sales metrics
  - Task completion metrics
  - Admin quick actions
- **Visualizations**:
  - Sales trend chart
  - User activity chart
  - Deal pipeline funnel
- **Context Required**:
  - `stats` - System statistics
  - `recent_activities` - Recent system activity
  - `users` - User list with activity metrics
  - `sales_data` - Sales performance data

### admin/accounts.html

- **Purpose**: Admin account management
- **Key Components**:
  - Advanced filtering options
  - Accounts table with all fields
  - Bulk action dropdown
  - Export to CSV button
  - Account creation form
- **JavaScript Features**:
  - Bulk operations
  - Advanced filtering
  - Export functionality
- **Context Required**:
  - `accounts` - All accounts
  - `industries` - All industries
  - `users` - All users for assignment
  - `metrics` - Account-related metrics

### admin/deals.html

- **Purpose**: Admin deal management
- **Key Sections**:
  - Deal statistics (total value, avg deal size, etc.)
  - Stage distribution chart
  - Deals table with all fields
  - Deal creation/edit form
  - CSV import interface
- **Key Features**:
  - Import deals from CSV
  - Download CSV template
  - Filter by multiple criteria
  - Advanced sorting
- **JavaScript Features**:
  - Chart.js visualizations
  - AJAX form submissions
  - CSV processing
  - Deal stage updates
- **Data Attributes**:
  - `data-deal-stages` - JSON-formatted deal stage data
  - `data-deal-values` - JSON-formatted deal value data
- **Context Required**:
  - `deals` - All deals
  - `stages` - Deal stages
  - `accounts` - All accounts
  - `users` - All users
  - `deal_stage_data` - Data for stage distribution chart
  - `deal_value_data` - Data for value charts

### admin/leads.html

- **Purpose**: Admin lead management
- **Key Components**:
  - Lead source distribution chart
  - Conversion rate metrics
  - Leads table with all fields
  - Lead creation/edit form
  - Bulk conversion tool
- **Context Required**:
  - `leads` - All leads
  - `sources` - Lead sources
  - `conversion_rates` - Lead conversion metrics
  - `users` - All users for assignment

### admin/reports.html

- **Purpose**: Advanced reporting and analytics
- **Key Sections**:
  - Date range selector
  - Sales performance metrics
  - Customer acquisition metrics
  - Product performance table
  - Sales by account table
  - Export options
- **Visualizations**:
  - Sales trend line chart
  - Deal stage funnel chart
  - Top products bar chart
  - Revenue by account chart
- **Data Display Features**:
  - Trend indicators with arrows
  - Percentage changes
  - Color-coding for positive/negative trends
- **JavaScript Features**:
  - Chart.js interactive visualizations
  - Date range filtering
  - PDF/CSV export options
- **Context Required**:
  - `total_sales` - Total sales figure
  - `deals_closed` - Number of closed deals
  - `avg_deal_size` - Average deal size
  - `new_customers` - Number of new customers
  - `top_products` - Top selling products with trends
  - `accounts` - Account sales data with trends
  - Each data element includes `trend_abs` values for displaying absolute trend values

### admin/tasks.html

- **Purpose**: Admin task management
- **Key Components**:
  - Task status distribution chart
  - Overdue tasks alert section
  - Tasks table with all fields
  - Task assignment tool
  - Task creation form
- **Context Required**:
  - `tasks` - All tasks
  - `status_distribution` - Task status metrics
  - `overdue_tasks` - List of overdue tasks
  - `users` - All users for assignment

### admin/products.html

- **Purpose**: Admin product management
- **Key Components**:
  - Product category distribution chart
  - Inventory status alerts
  - Products table with all fields
  - Product creation/edit form
  - Pricing tool
- **Context Required**:
  - `products` - All products
  - `categories` - Product categories
  - `inventory_status` - Inventory metrics
  - `sales_by_product` - Sales metrics by product

### admin/settings.html

- **Purpose**: System configuration
- **Key Sections**:
  - User management
  - Email templates
  - System preferences
  - Backup/restore options
  - API configuration
- **Form Sections**:
  - General Settings
  - User Permissions
  - Email Settings
  - Security Settings
  - Integration Settings
- **JavaScript Features**:
  - Form validation
  - Setting toggles
  - Test connection buttons
- **Template Tag Usage**:
  - `{% load static %}` - Required for loading static assets
- **Context Required**:
  - `settings` - System settings
  - `users` - All users
  - `roles` - User roles
  - `email_templates` - Available email templates
