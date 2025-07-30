# LiveFxHub CRM - Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Authentication System](#authentication-system)
6. [Frontend Implementation](#frontend-implementation)
7. [Template Structure](#template-structure)
8. [Static Files](#static-files)
9. [JavaScript Integration](#javascript-integration)
10. [Development and Deployment](#development-and-deployment)

## Project Overview

LiveFxHub CRM is built using the Django web framework with a REST API backend and a template-based frontend. The system follows the Model-View-Template (MVT) architecture pattern, which is Django's implementation of the Model-View-Controller (MVC) pattern.

### Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Authentication**: JWT (JSON Web Tokens)
- **Additional Libraries**:
  - Chart.js (for data visualization)
  - FullCalendar.js (for calendar functionality)
  - jQuery (for DOM manipulation and AJAX)
  - FontAwesome (for icons)

### Project Structure

```
crm/                      # Project root
├── crm/                  # Project settings
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py       # Django settings
│   ├── urls.py           # Main URL routing
│   └── wsgi.py
├── crm_app/              # Main application
│   ├── __init__.py
│   ├── admin.py          # Admin panel configuration
│   ├── apps.py
│   ├── migrations/       # Database migrations
│   ├── models.py         # Database models
│   ├── serializers.py    # API serializers
│   ├── tests.py          # Unit tests
│   ├── urls.py           # App URL routing
│   ├── views.py          # View functions and classes
│   ├── api.py            # API view functions
│   ├── static/           # Static files (CSS, JS, images)
│   └── templates/        # HTML templates
│       └── crm_app/      # App-specific templates
└── manage.py             # Django management script
```

## System Architecture

LiveFxHub CRM follows a layered architecture:

1. **Presentation Layer**: HTML templates, CSS and JavaScript for the frontend
2. **Application Layer**: Django views and REST API endpoints
3. **Business Logic Layer**: Service classes and model methods
4. **Data Access Layer**: Django models and ORM for database interaction

### Flow of a Typical Request

1. A request is received by Django's URL dispatcher
2. The URL pattern is matched to a view function or class
3. The view processes the request, interacts with models as needed
4. For page requests, the view renders a template with context data
5. For API requests, the view serializes data and returns JSON
6. The response is sent back to the client

## Database Models

The system is built around the following core models:

### Core Models

#### User and Authentication

- **UserProfile**: Extends Django's built-in User model with additional fields:
  - `user`: OneToOneField to Django's User model
  - `phone`: Phone number
  - `role`: User role (Admin, Manager, Sales, Support)
  - `department`: Department name
  - `profile_picture`: Profile image
  - `bio`: Short biography
  - `preferences`: JSON field for user preferences

#### Customer Relationship

- **Industry**: Industry categories
  - `name`: Industry name
  - `description`: Description of the industry

- **Account**: Organizations or companies
  - `name`: Account name
  - `account_type`: Type (Customer, Partner, Vendor, etc.)
  - `industry`: ForeignKey to Industry
  - `website`: Website URL
  - `phone`: Phone number
  - `address`: Physical address
  - `city`: City
  - `state`: State/Province
  - `zipcode`: Postal code
  - `country`: Country
  - `description`: Account description
  - `assigned_to`: ForeignKey to User
  - `parent_account`: Self-referential ForeignKey (for account hierarchy)
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **Contact**: Individual people
  - `first_name`: First name
  - `last_name`: Last name
  - `account`: ForeignKey to Account
  - `email`: Email address
  - `phone`: Phone number
  - `mobile`: Mobile number
  - `job_title`: Job title
  - `department`: Department
  - `address`: Physical address
  - `description`: Additional notes
  - `assigned_to`: ForeignKey to User
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **Lead**: Potential customer
  - `first_name`: First name
  - `last_name`: Last name
  - `company`: Company name
  - `title`: Job title
  - `email`: Email address
  - `phone`: Phone number
  - `address`: Address
  - `website`: Website URL
  - `lead_source`: Source (Web, Phone, Email, etc.)
  - `lead_status`: Status (New, Contacted, Qualified, etc.)
  - `industry`: ForeignKey to Industry
  - `description`: Additional notes
  - `assigned_to`: ForeignKey to User
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
  - `converted`: Boolean indicating if lead is converted
  - `converted_date`: Date of conversion

#### Sales Process

- **Deal**: Sales opportunity
  - `name`: Deal name
  - `amount`: Deal value
  - `stage`: Pipeline stage
  - `close_date`: Expected close date
  - `probability`: Success probability percentage
  - `description`: Deal description
  - `lead`: ForeignKey to Lead (optional)
  - `account`: ForeignKey to Account
  - `contact`: ForeignKey to Contact
  - `assigned_to`: ForeignKey to User
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **Product**: Product or service
  - `name`: Product name
  - `product_code`: Unique code
  - `description`: Product description
  - `unit_price`: Price per unit
  - `category`: Product category
  - `active`: Active status
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **DealProduct**: Products associated with a deal
  - `deal`: ForeignKey to Deal
  - `product`: ForeignKey to Product
  - `quantity`: Quantity
  - `unit_price`: Price per unit (can differ from product's standard price)
  - `discount_percentage`: Discount percentage
  - `total_price`: Total price
  - `description`: Additional notes

#### Activities

- **Task**: To-do items
  - `subject`: Task subject
  - `due_date`: Due date
  - `status`: Status (Not Started, In Progress, Completed, etc.)
  - `priority`: Priority (High, Medium, Low)
  - `description`: Task description
  - `related_lead`: ForeignKey to Lead (optional)
  - `related_contact`: ForeignKey to Contact (optional)
  - `related_account`: ForeignKey to Account (optional)
  - `related_deal`: ForeignKey to Deal (optional)
  - `assigned_to`: ForeignKey to User
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **Event**: Meetings and appointments
  - `title`: Event title
  - `start_time`: Start date and time
  - `end_time`: End date and time
  - `all_day`: Boolean for all-day events
  - `location`: Event location
  - `description`: Event description
  - `related_lead`: ForeignKey to Lead (optional)
  - `related_contact`: ForeignKey to Contact (optional)
  - `related_account`: ForeignKey to Account (optional)
  - `related_deal`: ForeignKey to Deal (optional)
  - `attendees`: ManyToManyField to User
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

- **Note**: Notes on records
  - `subject`: Note subject
  - `content`: Note content
  - `related_lead`: ForeignKey to Lead (optional)
  - `related_contact`: ForeignKey to Contact (optional)
  - `related_account`: ForeignKey to Account (optional)
  - `related_deal`: ForeignKey to Deal (optional)
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

#### Document Management

- **Document**: Files and documents
  - `title`: Document title
  - `file`: File field
  - `description`: Document description
  - `document_type`: Type (Contract, Proposal, etc.)
  - `related_lead`: ForeignKey to Lead (optional)
  - `related_contact`: ForeignKey to Contact (optional)
  - `related_account`: ForeignKey to Account (optional)
  - `related_deal`: ForeignKey to Deal (optional)
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

#### Financial

- **Transaction**: Financial transactions
  - `transaction_type`: Type (Invoice, Payment, etc.)
  - `reference_number`: Reference/invoice number
  - `amount`: Transaction amount
  - `date`: Transaction date
  - `due_date`: Due date (for invoices)
  - `status`: Status (Draft, Sent, Paid, etc.)
  - `description`: Transaction description
  - `account`: ForeignKey to Account
  - `deal`: ForeignKey to Deal (optional)
  - `created_by`: ForeignKey to User
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

### Model Relationships

The models are connected through various relationships:

- One-to-Many: ForeignKey fields (e.g., Contact belongs to Account)
- Many-to-Many: ManyToManyField (e.g., Event has multiple attendees)
- One-to-One: OneToOneField (e.g., User has one UserProfile)

### Model Methods

Each model includes methods to enhance functionality:

- `__str__`: String representation
- `get_absolute_url`: URL for detail view
- Custom methods for business logic (e.g., Lead.convert_to_opportunity())

## API Endpoints

The REST API is implemented using Django REST Framework and provides endpoints for all models:

### Authentication Endpoints

- `POST /api/token/`: Obtain JWT token
- `POST /api/token/refresh/`: Refresh JWT token
- `POST /api/token/verify/`: Verify JWT token
- `POST /api/register/`: Register new user

### Core Endpoints

Each model has standard CRUD endpoints:

- `GET /api/<model>/`: List all records (with pagination)
- `POST /api/<model>/`: Create a new record
- `GET /api/<model>/<id>/`: Retrieve a specific record
- `PUT /api/<model>/<id>/`: Update a specific record
- `DELETE /api/<model>/<id>/`: Delete a specific record

### Specific Endpoints

- `GET /api/dashboard/`: Dashboard statistics
- `POST /api/leads/<id>/convert/`: Convert lead to contact/account/deal
- `GET /api/deals/pipeline/`: Deal pipeline statistics
- `POST /api/tasks/<id>/mark_complete/`: Mark task as complete
- `GET /api/reports/<report-type>/`: Generate specific reports
- `GET /api/products/<id>/deals/`: Get deals associated with a product

### API Request/Response Format

Requests and responses use JSON format:

**Example Request:**
```json
POST /api/leads/
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "company": "ABC Corp",
  "lead_source": "website",
  "lead_status": "new"
}
```

**Example Response:**
```json
{
  "id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "company": "ABC Corp",
  "lead_source": "website",
  "lead_status": "new",
  "created_at": "2025-05-10T10:30:00Z",
  "updated_at": "2025-05-10T10:30:00Z"
}
```

## Authentication System

LiveFxHub CRM uses JSON Web Tokens (JWT) for authentication:

### JWT Authentication Flow

1. User submits credentials (username/password)
2. Server validates credentials and returns JWT token
3. Client stores token (in localStorage)
4. Client includes token in Authorization header for subsequent requests
5. Server validates token on each request
6. Token expires after a set time; client uses refresh token to get a new one

### Security Measures

- Tokens expire after 24 hours
- HTTPS for all communications
- CSRF protection for non-API endpoints
- Password hashing with PBKDF2
- Rate limiting for login attempts
- All API endpoints require authentication except for login and registration
