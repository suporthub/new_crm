# LiveFxHub CRM - Technical Documentation (Continued)

## Frontend Implementation

The frontend of LiveFxHub CRM uses a combination of Django templates, Bootstrap 5 for styling, and JavaScript for interactivity.

### Template Structure

The templates follow a hierarchical structure with base templates that are extended by specific page templates:

```
templates/
└── crm_app/
    ├── base.html                # Main base template with common structure
    ├── index.html               # Landing page
    ├── login.html               # Login page
    ├── dashboard.html           # Dashboard
    ├── leads.html               # Leads list and management
    ├── contacts.html            # Contacts list and management
    ├── accounts.html            # Accounts list and management
    ├── deals.html               # Deals list and pipeline
    ├── tasks.html               # Tasks management
    ├── calendar.html            # Calendar and events
    ├── products.html            # Products management
    ├── reports.html             # Reports and analytics
    ├── settings.html            # User and system settings
    └── transaction.html         # Transaction details
```

### Base Template

The `base.html` template defines the common structure used across all pages:

- HTML5 doctype and responsive meta tags
- CSS includes (Bootstrap, Font Awesome, custom CSS)
- Navigation sidebar with links to all modules
- Top navigation bar with user menu and search
- Main content container with {% block content %}{% endblock %}
- Footer with copyright information
- JavaScript includes and common script functions
- JWT token handling

### Template Blocks

Each template uses a block system to extend the base template:

- `{% block title %}{% endblock %}`: Page title
- `{% block extra_css %}{% endblock %}`: Page-specific CSS
- `{% block content %}{% endblock %}`: Main content area
- `{% block extra_js %}{% endblock %}`: Page-specific JavaScript

### Bootstrap Components

The UI makes extensive use of Bootstrap 5 components:

- Grid system for responsive layouts
- Cards for container elements
- Tables for data display
- Forms for data input
- Modals for dialogs
- Navs and tabs for navigation
- Alerts for notifications
- Badges for status indicators
- Buttons and button groups
- Pagination for multi-page content

### Custom CSS

Custom CSS is used to extend Bootstrap and provide LiveFxHub CRM-specific styling:

- Brand colors and theme
- Custom sidebar styling
- Dashboard widget styles
- Deal pipeline visualization
- Form enhancements
- Responsive adjustments
- Dark/light mode toggles

## JavaScript Integration

The frontend uses JavaScript for client-side functionality and API communication:

### Core JavaScript Modules

- **Authentication**: JWT token management and user session handling
- **API Client**: Functions for making API requests
- **Form Handling**: Validation and submission of forms
- **Data Display**: Rendering data in tables and charts
- **Notifications**: User notifications and alerts

### API Communication

All API requests follow a standard pattern:

```javascript
// Generic API request function
async function apiRequest(endpoint, method = 'GET', data = null, isFormData = false) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Authorization': `Bearer ${token}`
    };
    
    if (!isFormData && method !== 'GET') {
        headers['Content-Type'] = 'application/json';
    }
    
    const options = {
        method,
        headers
    };
    
    if (data) {
        if (isFormData) {
            options.body = data;
        } else if (method !== 'GET') {
            options.body = JSON.stringify(data);
        }
    }
    
    try {
        const response = await fetch(`/api/${endpoint}`, options);
        
        // Handle token expiry
        if (response.status === 401) {
            // Try to refresh token
            const refreshed = await refreshToken();
            if (refreshed) {
                // Retry the request with new token
                return apiRequest(endpoint, method, data, isFormData);
            } else {
                // Redirect to login
                window.location.href = '/login/';
                return null;
            }
        }
        
        // For successful responses, parse JSON
        if (response.ok) {
            if (method === 'DELETE') {
                return true;
            }
            return await response.json();
        }
        
        // Handle errors
        const errorData = await response.json();
        showNotification('Error', errorData.detail || 'An error occurred', 'error');
        return null;
    } catch (error) {
        console.error('API request error:', error);
        showNotification('Error', 'Network or server error', 'error');
        return null;
    }
}
```

### Form Serialization

Forms are serialized for API submission:

```javascript
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    return data;
}
```

### Dashboard Charts

The dashboard uses Chart.js for data visualization:

```javascript
function createSalesChart(elementId, labels, data) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sales',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}
```

### Event Handling

Event listeners are used for user interactions:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components on page load
    loadDashboardData();
    
    // Set up event listeners
    document.getElementById('create-lead-btn').addEventListener('click', function() {
        // Show create lead modal
        const modal = new bootstrap.Modal(document.getElementById('createLeadModal'));
        modal.show();
    });
    
    // Form submission
    document.getElementById('lead-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveLeadData();
    });
});
```

## Views and Routing

### URL Configuration

URLs are defined in `urls.py`:

```python
# Main project URLs (crm/urls.py)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('crm_app.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# App-specific URLs (crm_app/urls.py)
from django.urls import path
from . import views
from . import api
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Web pages
    path('', views.index, name='index'),
    path('login/', views.login_page, name='login-page'),
    path('dashboard/', views.dashboard_page, name='dashboard-page'),
    path('leads/', views.leads_page, name='leads-page'),
    path('contacts/', views.contacts_page, name='contacts-page'),
    path('accounts/', views.accounts_page, name='accounts-page'),
    path('deals/', views.deals_page, name='deals-page'),
    path('tasks/', views.tasks_page, name='tasks-page'),
    path('calendar/', views.calendar_page, name='calendar-page'),
    path('products/', views.products_page, name='products-page'),
    path('reports/', views.reports_page, name='reports-page'),
    path('settings/', views.settings_page, name='settings-page'),
    path('transaction/<int:id>/', views.transaction_page, name='transaction-page'),
    
    # API endpoints - Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('api/register/', api.register, name='register'),
    
    # API endpoints - Dashboard
    path('api/dashboard/', api.dashboard, name='dashboard-api'),
    
    # API endpoints - Core models
    path('api/leads/', api.LeadListCreate.as_view(), name='lead-list-create'),
    path('api/leads/<int:pk>/', api.LeadRetrieveUpdateDestroy.as_view(), name='lead-detail'),
    path('api/leads/<int:pk>/convert/', api.convert_lead, name='lead-convert'),
    # [Additional API endpoints for other models...]
]
```

### View Functions

Page views render templates:

```python
# Sample view function (crm_app/views.py)
def dashboard_page(request):
    """Render the dashboard page"""
    return render(request, 'crm_app/dashboard.html')

def leads_page(request):
    """Render the leads page"""
    return render(request, 'crm_app/leads.html')
```

### API Views

API views use Django REST Framework:

```python
# Sample API views (crm_app/api.py)
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Lead, Contact, Account, Deal
from .serializers import LeadSerializer, ContactSerializer, AccountSerializer, DealSerializer

class LeadListCreate(generics.ListCreateAPIView):
    """API view for listing and creating leads"""
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class LeadRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating, and deleting a lead"""
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def convert_lead(request, pk):
    """Convert a lead to contact, account, and deal"""
    try:
        lead = Lead.objects.get(pk=pk)
    except Lead.DoesNotExist:
        return Response({'detail': 'Lead not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Create account if it doesn't exist
    account, created = Account.objects.get_or_create(
        name=lead.company,
        defaults={
            'phone': lead.phone,
            'website': lead.website,
            'industry': lead.industry,
            'created_by': request.user,
            'assigned_to': lead.assigned_to or request.user
        }
    )
    
    # Create contact
    contact = Contact.objects.create(
        first_name=lead.first_name,
        last_name=lead.last_name,
        account=account,
        email=lead.email,
        phone=lead.phone,
        created_by=request.user,
        assigned_to=lead.assigned_to or request.user
    )
    
    # Create deal if requested
    deal = None
    if request.data.get('create_deal', False):
        deal = Deal.objects.create(
            name=f"Deal with {lead.company}",
            account=account,
            contact=contact,
            stage='qualification',
            created_by=request.user,
            assigned_to=lead.assigned_to or request.user
        )
    
    # Mark lead as converted
    lead.converted = True
    lead.converted_date = timezone.now()
    lead.save()
    
    # Return the created objects
    return Response({
        'account': AccountSerializer(account).data,
        'contact': ContactSerializer(contact).data,
        'deal': DealSerializer(deal).data if deal else None
    }, status=status.HTTP_201_CREATED)
```

## Serializers

Serializers handle conversion between Django models and JSON:

```python
# Sample serializers (crm_app/serializers.py)
from rest_framework import serializers
from .models import Lead, Contact, Account, Deal

class LeadSerializer(serializers.ModelSerializer):
    """Serializer for Lead model"""
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}"
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None
```

## Settings Configuration

Key settings in `settings.py`:

```python
# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Authentication settings
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Template configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'crm_app', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static files configuration
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'crm_app', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}
```

## Development and Deployment

### Local Development Environment

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: 
   - Windows: `venv\Scripts\activate`
   - Unix/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run migrations: `python manage.py migrate`
6. Create a superuser: `python manage.py createsuperuser`
7. Run the development server: `python manage.py runserver`

### Production Deployment

For production deployment, consider the following:

1. Use PostgreSQL instead of SQLite
2. Set `DEBUG = False` in settings
3. Configure proper `ALLOWED_HOSTS`
4. Use a production-ready web server (e.g., Gunicorn)
5. Use Nginx or Apache as a reverse proxy
6. Implement HTTPS with proper SSL certificates
7. Set up proper logging
8. Configure email settings for notifications
9. Use a process manager (e.g., Supervisor)
10. Set up regular database backups

### Requirements

The main dependencies for the project are:

```
Django==4.2.0
djangorestframework==3.14.0
djangorestframework-simplejwt==5.2.2
psycopg2-binary==2.9.6  # For PostgreSQL
Pillow==9.5.0  # For image handling
django-filter==23.2
django-cors-headers==4.0.0
gunicorn==20.1.0  # For production
whitenoise==6.4.0  # For static files
dj-database-url==1.3.0  # For database configuration
```

## Conclusion

LiveFxHub CRM is a comprehensive system built with Django and modern web technologies. This technical documentation covers the key aspects of the system's architecture, implementation, and deployment. Developers can use this as a reference for understanding, maintaining, and extending the system.

For any questions or issues, please contact the development team at developer@livefxhub.com.
