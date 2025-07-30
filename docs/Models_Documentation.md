# LiveFxHub CRM Models Documentation

This document provides an in-depth explanation of all models in the LiveFxHub CRM system.

## User & Authentication Models

### User

The base User model is Django's built-in authentication model.

**Key fields:**
- `username`: Unique identifier for login
- `password`: Hashed password
- `email`: Email address
- `first_name`: User's first name
- `last_name`: User's last name
- `is_active`: Whether the user account is active
- `is_staff`: Whether the user can access the admin site
- `is_superuser`: Whether the user has all permissions
- `date_joined`: When the user joined
- `last_login`: When the user last logged in

### UserProfile

Extends the base User model with additional information.

**Key fields:**
- `user`: One-to-one relationship with User model
- `phone`: Contact phone number
- `address`: Physical address
- `profile_picture`: Profile image
- `role`: User's role in the organization (e.g., 'admin', 'manager', 'staff')
- `department`: Department the user belongs to
- `created_at`: When the profile was created
- `updated_at`: When the profile was last updated

**Methods:**
- `__str__()`: Returns username
- `get_full_name()`: Returns the first and last name
- `get_short_name()`: Returns the first name

## Business Entity Models

### Industry

Represents business sectors for categorizing accounts.

**Key fields:**
- `name`: Industry name (e.g., "Technology", "Healthcare")
- `description`: Detailed description
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns industry name

### Account

Represents organizations or businesses that are clients or prospects.

**Key fields:**
- `name`: Company name
- `website`: Company website URL
- `phone`: Contact phone number
- `email`: Contact email address
- `industry`: ForeignKey to Industry
- `address`: Physical address
- `city`: City
- `state`: State/Province
- `zipcode`: Postal code
- `country`: Country
- `assigned_to`: ForeignKey to User who manages this account
- `description`: Detailed account description
- `created_by`: ForeignKey to User who created the account
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns account name
- `get_absolute_url()`: Returns URL to account detail view
- `get_contacts()`: Returns related contacts
- `get_deals()`: Returns related deals
- `get_transactions()`: Returns related transactions

### Contact

Represents individuals associated with accounts.

**Key fields:**
- `salutation`: Title (Mr., Ms., Dr., etc.)
- `first_name`: First name
- `last_name`: Last name
- `email`: Email address
- `phone`: Phone number
- `mobile`: Mobile phone
- `account`: ForeignKey to Account
- `position`: Job title/position
- `address`: Physical address
- `city`: City
- `state`: State/Province
- `zipcode`: Postal code
- `country`: Country
- `assigned_to`: ForeignKey to User who manages this contact
- `description`: Additional information
- `created_by`: ForeignKey to User who created the contact
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns full name
- `get_full_name()`: Returns formatted full name with salutation
- `get_absolute_url()`: Returns URL to contact detail view

### Lead

Represents potential customers not yet converted to accounts.

**Key fields:**
- `salutation`: Title (Mr., Ms., Dr., etc.)
- `first_name`: First name
- `last_name`: Last name
- `email`: Email address
- `phone`: Phone number
- `mobile`: Mobile phone
- `company`: Company name
- `position`: Job title/position
- `website`: Company website
- `industry`: ForeignKey to Industry
- `address`: Physical address
- `city`: City
- `state`: State/Province
- `zipcode`: Postal code
- `country`: Country
- `status`: Lead status (e.g., 'new', 'contacted', 'qualified', 'unqualified')
- `source`: Where the lead came from (e.g., 'website', 'referral', 'advertisement')
- `assigned_to`: ForeignKey to User who manages this lead
- `description`: Additional information
- `created_by`: ForeignKey to User who created the lead
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `converted`: Boolean indicating if lead is converted
- `converted_to_account`: ForeignKey to Account if converted
- `converted_to_contact`: ForeignKey to Contact if converted
- `converted_to_deal`: ForeignKey to Deal if converted

**Methods:**
- `__str__()`: Returns full name
- `get_full_name()`: Returns formatted full name with salutation
- `get_absolute_url()`: Returns URL to lead detail view
- `convert_to_account()`: Converts lead to account, contact, and optionally a deal

### Deal

Represents sales opportunities.

**Key fields:**
- `name`: Deal name
- `account`: ForeignKey to Account
- `contacts`: ManyToManyField to Contact
- `stage`: Deal stage (choices from DEAL_STAGES)
- `DEAL_STAGES`: Tuple of choices for deal stages:
  - `qualification`: "Qualification"
  - `needs_analysis`: "Needs Analysis"
  - `value_proposition`: "Value Proposition"
  - `id_decision_makers`: "Identify Decision Makers"
  - `proposal`: "Proposal/Price Quote"
  - `negotiation`: "Negotiation/Review"
  - `closed_won`: "Closed Won"
  - `closed_lost`: "Closed Lost"
- `amount`: Deal value
- `expected_close_date`: Expected closing date
- `priority`: Priority level (high, medium, low)
- `probability`: Success probability percentage
- `assigned_to`: ForeignKey to User who manages this deal
- `description`: Additional information
- `created_by`: ForeignKey to User who created the deal
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `products`: ManyToManyField to Product through DealProduct

**Methods:**
- `__str__()`: Returns deal name
- `get_absolute_url()`: Returns URL to deal detail view
- `get_contacts()`: Returns related contacts
- `get_products()`: Returns related products
- `get_total_value()`: Returns calculated total value based on products

## Activity Models

### Task

Represents actionable items assigned to users.

**Key fields:**
- `title`: Task title
- `description`: Task description
- `status`: Task status (choices from TASK_STATUS)
- `TASK_STATUS`: Tuple of choices:
  - `not_started`: "Not Started"
  - `in_progress`: "In Progress"
  - `completed`: "Completed"
  - `waiting`: "Waiting"
  - `deferred`: "Deferred"
- `priority`: Priority level (choices from PRIORITY_CHOICES)
- `PRIORITY_CHOICES`: Tuple of choices:
  - `low`: "Low"
  - `medium`: "Medium"
  - `high`: "High"
- `due_date`: Deadline
- `assigned_to`: ForeignKey to User assigned to task
- `related_lead`: ForeignKey to Lead (optional)
- `related_contact`: ForeignKey to Contact (optional)
- `related_account`: ForeignKey to Account (optional)
- `related_deal`: ForeignKey to Deal (optional)
- `created_by`: ForeignKey to User who created the task
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns task title
- `get_absolute_url()`: Returns URL to task detail view
- `is_overdue()`: Checks if task is past due date
- `get_related_entity()`: Returns the related entity (lead, contact, account, or deal)

### Event

Represents calendar events like meetings and calls.

**Key fields:**
- `title`: Event title
- `description`: Event description
- `event_type`: Type of event (meeting, call, etc.)
- `start_date`: Start date and time
- `end_date`: End date and time
- `location`: Physical or virtual location
- `attendees`: ManyToManyField to User
- `related_lead`: ForeignKey to Lead (optional)
- `related_contact`: ForeignKey to Contact (optional)
- `related_account`: ForeignKey to Account (optional)
- `related_deal`: ForeignKey to Deal (optional)
- `created_by`: ForeignKey to User who created the event
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns event title
- `get_absolute_url()`: Returns URL to event detail view
- `get_duration()`: Returns duration in hours/minutes
- `get_related_entity()`: Returns the related entity

### Note

Represents text notes attached to entities.

**Key fields:**
- `title`: Note title
- `content`: Note content
- `related_lead`: ForeignKey to Lead (optional)
- `related_contact`: ForeignKey to Contact (optional)
- `related_account`: ForeignKey to Account (optional)
- `related_deal`: ForeignKey to Deal (optional)
- `created_by`: ForeignKey to User who created the note
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns note title
- `get_related_entity()`: Returns the related entity

### Document

Represents files attached to entities.

**Key fields:**
- `title`: Document title
- `file`: File field
- `file_type`: Type of document
- `related_lead`: ForeignKey to Lead (optional)
- `related_contact`: ForeignKey to Contact (optional)
- `related_account`: ForeignKey to Account (optional)
- `related_deal`: ForeignKey to Deal (optional)
- `created_by`: ForeignKey to User who created the document
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns document title
- `get_file_extension()`: Returns file extension
- `get_download_url()`: Returns URL for downloading
- `get_related_entity()`: Returns the related entity

## Sales Models

### Transaction

Represents financial transactions.

**Key fields:**
- `account`: ForeignKey to Account
- `deal`: ForeignKey to Deal (optional)
- `amount`: Transaction amount
- `transaction_type`: Type (income or expense)
- `transaction_date`: Date of transaction
- `category`: Transaction category
- `description`: Transaction description
- `created_by`: ForeignKey to User who created the transaction
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns transaction description and amount
- `get_absolute_url()`: Returns URL to transaction detail view

### Product

Represents products or services sold.

**Key fields:**
- `name`: Product name
- `description`: Product description
- `category`: Product category
- `unit_price`: Price per unit
- `sku`: Stock keeping unit
- `tax`: Tax percentage
- `is_active`: Whether product is active
- `created_by`: ForeignKey to User who created the product
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns product name
- `get_absolute_url()`: Returns URL to product detail view
- `get_price_with_tax()`: Returns price including tax

### DealProduct

Represents the many-to-many relationship between deals and products.

**Key fields:**
- `deal`: ForeignKey to Deal
- `product`: ForeignKey to Product
- `quantity`: Quantity of product
- `discount`: Discount percentage
- `total_price`: Total price (calculated)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- `__str__()`: Returns deal and product names
- `calculate_total()`: Calculates total price based on quantity, unit price, and discount
