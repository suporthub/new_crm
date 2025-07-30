# LiveFxHub CRM System Documentation

## Overview

LiveFxHub CRM is a comprehensive Customer Relationship Management system built with Django. It follows the MVT (Model-View-Template) architecture and provides a robust platform for managing customer relationships, sales pipelines, and business operations.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Models](#models)
3. [Views](#views)
4. [Templates](#templates)
5. [URLs](#urls)
6. [APIs](#apis)
7. [Authentication](#authentication)
8. [Admin Interface](#admin-interface)

## System Architecture

The CRM system is built on Django's MVT architecture:

- **Models**: Database schema definitions for storing application data
- **Views**: Business logic that processes HTTP requests and returns responses
- **Templates**: HTML files that define the user interface
- **URLs**: Routing configuration that maps URLs to view functions

## Models

The CRM system uses the following primary models to store data:

### User and UserProfile

- **User**: Django's built-in user model for authentication
- **UserProfile**: Extended user information including role, department, and contact details

### Business Entities

- **Industry**: Sectors and industries for categorizing accounts
- **Account**: Organizations or companies (clients/prospects)
- **Contact**: Individual people associated with accounts
- **Lead**: Potential customers not yet qualified as accounts
- **Deal**: Sales opportunities with accounts

### Sales and Activities

- **Task**: Actionable items assigned to users
- **Event**: Scheduled activities like meetings or calls
- **Note**: Text entries associated with business entities
- **Document**: Files attached to business entities
- **Transaction**: Financial transactions linked to accounts or deals
- **Product**: Items or services sold to customers
- **DealProduct**: Many-to-many relationship between deals and products

## Views

The system utilizes two types of views:

### Regular Views

These handle the client-facing interfaces and API endpoints:

- **Authentication Views**: Login, logout, registration, and password management
- **Dashboard Views**: Main dashboard with statistics and recent activities
- **Entity Management Views**: CRUD operations for all models
- **API Views**: RESTful endpoints for mobile apps and integrations

### Admin Views

Special views for administrators to manage the system:

- **admin_dashboard**: Main admin control panel
- **admin_accounts**: Account management for administrators
- **admin_contacts**: Contact management interface
- **admin_leads**: Lead tracking and management
- **admin_deals**: Deal pipeline management
- **admin_tasks**: Task tracking and assignment
- **admin_products**: Product catalog management
- **admin_reports**: Business intelligence and reporting
- **admin_settings**: System configuration

## Templates

The system uses Bootstrap-based templates organized into logical sections:

### Authentication Templates

- **login.html**: User login form
- **register.html**: User registration
- **password_reset.html**: Password recovery

### Main Templates

- **base.html**: Main template with navigation and common elements
- **dashboard.html**: Main user dashboard
- **index.html**: Landing page for unauthenticated users

### Entity Templates

- **accounts/**: Templates for account management
- **contacts/**: Templates for contact management
- **leads/**: Templates for lead management
- **deals/**: Templates for deal pipeline
- **tasks/**: Templates for task management
- **products/**: Templates for product catalog

### Admin Templates

Located in **templates/admin/**:

- **base_admin.html**: Base template for admin interface
- **dashboard.html**: Admin dashboard with global statistics
- **accounts.html**: Account management interface
- **contacts.html**: Contact management interface
- **leads.html**: Lead management interface
- **deals.html**: Deal pipeline management with drag-and-drop functionality
- **tasks.html**: Task management interface
- **products.html**: Product catalog management
- **reports.html**: Reporting and analytics interface
- **settings.html**: System settings and configuration

## URLs

The URL structure is organized as follows:

### Authentication URLs

- **/accounts/login/**: User login
- **/accounts/logout/**: User logout
- **/accounts/register/**: User registration
- **/accounts/password/reset/**: Password reset

### Main App URLs

- **/**: Landing page/dashboard
- **/dashboard/**: User dashboard with statistics and recent activities
- **/api/dashboard/**: API endpoint for dashboard data

### Entity Management URLs

- **/accounts/**: Account list and management
- **/contacts/**: Contact list and management
- **/leads/**: Lead list and management
- **/deals/**: Deal list and pipeline view
- **/tasks/**: Task list and management
- **/products/**: Product catalog

### Admin URLs

- **/admin/dashboard/**: Admin dashboard
- **/admin/accounts/**: Admin account management
- **/admin/contacts/**: Admin contact management
- **/admin/leads/**: Admin lead management
- **/admin/deals/**: Admin deal management
- **/admin/tasks/**: Admin task management
- **/admin/products/**: Admin product management
- **/admin/reports/**: Admin reporting interface
- **/admin/settings/**: Admin system settings

### API URLs

- **/api/**: API root
- **/api/accounts/**: Account API endpoints
- **/api/contacts/**: Contact API endpoints
- **/api/leads/**: Lead API endpoints
- **/api/deals/**: Deal API endpoints
- **/api/tasks/**: Task API endpoints
- **/api/products/**: Product API endpoints

## APIs

The system provides a comprehensive REST API using Django REST Framework:

### Authentication API

- JWT token-based authentication
- Endpoints for login, token refresh, and validation

### Entity APIs

- CRUD operations for all main entities
- Filtering, sorting, and pagination
- Custom actions for specific business processes

### Dashboard API

- Aggregated statistics and metrics
- Recent activities and upcoming tasks
- Deal pipeline and sales forecasts

## Authentication

The system uses Django's authentication system with the following enhancements:

- JWT token authentication for API access
- Role-based access control
- Custom user profiles with extended attributes
- Password policy enforcement

## Admin Interface

The admin interface is a custom-built dashboard for system administrators with:

### Dashboard

- Global statistics and KPIs
- Recent activities across the system
- Quick access to main functions

### Reporting

- Sales performance metrics
- Deal pipeline analytics
- User activity reports
- Financial summaries

### User Management

- User account creation and management
- Role and permission assignment
- Department and team organization

### System Settings

- General system configuration
- Email templates and notifications
- Integration settings
- Backup and maintenance tools

## Security Features

The CRM implements several security measures:

1. **Authentication protection**: All views are protected with login_required decorator
2. **Admin access control**: Admin views have additional user_passes_test(is_admin) checks
3. **Transaction security**: Special security for transaction views, requiring access from dashboard
4. **CSRF protection**: All forms have CSRF protection enabled
5. **Password policies**: Enforced through custom validation
6. **API security**: JWT tokens with expiration and refresh mechanism

## Special Features

### Client Transaction Security
A special security feature requires users to access transaction details only from the dashboard:
- In dashboard.html - showTransaction() function sets a session flag and redirects
- In transaction views - Authorization checks prevent direct access
- Only users coming from dashboard can view transaction details

### Deal Pipeline Management
The deals interface includes a drag-and-drop kanban board for easy visualization and management of the sales pipeline:
- Deals are organized by stages (Qualification, Needs Analysis, etc.)
- Users can drag deals between stages to update their status
- Visual indicators show deal value and priority

### CSV Import/Export
Several interfaces provide functionality to import and export data in CSV format:
- admin_deal_import: Handles CSV imports for deals
- admin_download_deal_template: Enables downloading a CSV template for deals
- Similar functionality exists for accounts, contacts, and other entities
