from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import admin_views
from . import api_views
from . import settings_views

router = DefaultRouter()
router.register(r'industries', views.IndustryViewSet)
router.register(r'accounts', views.AccountViewSet)
router.register(r'contacts', views.ContactViewSet)
router.register(r'leads', views.LeadViewSet)
router.register(r'deals', views.DealViewSet)
router.register(r'tasks', views.TaskViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'notes', views.NoteViewSet)
router.register(r'documents', views.DocumentViewSet)
router.register(r'transactions', views.TransactionViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'deal-products', views.DealProductViewSet)
router.register(r'users', api_views.UserViewSet)
router.register(r'allot-managers', api_views.AllotManagerViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/allotleadmanager/', views.allot_lead_manager, name='allot-lead-manager'),
    path('api/users-by-manager/', api_views.get_users_by_manager, name='users-by-manager'),
    
    # Authentication endpoints
    path('api/register/', views.register_user, name='register'),
    path('api/login/', views.login_user, name='login'),
    path('api/current-user/', views.get_current_user, name='current-user'),
    path('api/change-password/', views.change_password, name='change-password'),
    path('api/profile/', views.get_user_profile, name='get-profile'),
    path('api/profile/update/', views.update_user_profile, name='update-profile'),
    
    # Dashboard endpoint
    path('api/dashboard/', views.dashboard, name='dashboard'),
    
    # Settings endpoints
    path('api/settings/', settings_views.user_settings, name='user-settings'),
    path('api/settings/general/', settings_views.update_general_settings, name='general-settings'),
    path('api/settings/notifications/', settings_views.update_notification_settings, name='notification-settings'),
    path('api/settings/security/', settings_views.update_security_settings, name='security-settings'),
    path('api/settings/appearance/', settings_views.update_appearance_settings, name='appearance-settings'),
    
    # Web pages
    path('', views.index, name='index'),
    path('login/', views.login_page, name='login-page'),
    path('dashboard/', views.dashboard_page, name='dashboard-page'),
    path('leads/', views.leads_page, name='leads-page'),
    path('leads/<int:lead_id>/', views.lead_detail_page, name='lead-detail-page'),
    path('leads/<int:lead_id>/edit/', views.lead_edit_page, name='lead-edit-page'),
    path('contacts/', views.contacts_page, name='contacts-page'),  # Keep the old name for backward compatibility
    path('contacts/', views.contacts_page, name='contacts'),  # New name for future use
    path('contacts/<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path('contacts/<int:contact_id>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:contact_id>/add-note/', views.contact_add_note, name='contact_add_note'),
    path('contacts/<int:contact_id>/delete-note/<int:note_id>/', views.contact_delete_note, name='contact_delete_note'),
    
    path('accounts/', views.accounts_page, name='accounts-page'),  # Keep the old name for backward compatibility
    path('accounts/', views.accounts_page, name='accounts'),  # New name for future use
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/<int:account_id>/edit/', views.account_edit, name='account_edit'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:account_id>/add-note/', views.account_add_note, name='account_add_note'),
    path('accounts/<int:account_id>/delete-note/<int:note_id>/', views.account_delete_note, name='account_delete_note'),
    path('deals/', views.deals_page, name='deals-page'),
    path('tasks/', views.tasks_page, name='tasks-page'),
    path('calendar/', views.calendar_page, name='calendar-page'),
    path('reports/', views.reports_page, name='reports-page'),
    path('settings/', views.settings_page, name='settings-page'),
    path('profile/', views.profile_page, name='profile-page'),
    path('transaction/', views.transaction_page, name='transaction-page'),
    
    # Custom Admin Interface URLs
    path('admin/login/', admin_views.admin_login, name='admin_login'),
    path('admin/logout/', admin_views.admin_logout, name='admin_logout'),
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.admin_users, name='admin_users'),
    path('admin/users/create/', admin_views.admin_user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/edit/', admin_views.admin_user_edit, name='admin_user_edit'),
    path('admin/profile/', admin_views.admin_profile, name='admin_profile'),
    path('admin/settings/', admin_views.admin_settings, name='admin_settings'),
    path('admin/logs/', admin_views.admin_logs, name='admin_logs'),
    path('admin/leads/', admin_views.admin_leads, name='admin_leads'),
    path('admin/leads/create/', admin_views.admin_lead_create, name='admin_lead_create'),
    path('admin/leads/<int:lead_id>/', admin_views.admin_lead_detail, name='admin_lead_detail'),
    path('admin/leads/<int:lead_id>/edit/', admin_views.admin_lead_edit, name='admin_lead_edit'),
    path('admin/leads/import/', admin_views.admin_lead_import, name='admin_lead_import'),
    path('admin/leads/convert/<int:lead_id>/', admin_views.admin_lead_convert, name='admin_lead_convert'),
    path('admin/download-lead-template/', admin_views.admin_download_lead_template, name='admin_download_lead_template'),
    path('admin/contacts/', admin_views.admin_contacts, name='admin_contacts'),
    path('admin/contacts/create/', admin_views.admin_contact_create, name='admin_contact_create'),
    path('admin/contacts/<int:contact_id>/', admin_views.admin_contact_detail, name='admin_contact_detail'),
    path('admin/contacts/<int:contact_id>/edit/', admin_views.admin_contact_edit, name='admin_contact_edit'),
    path('admin/contacts/<int:contact_id>/add-note/', admin_views.admin_contact_add_note, name='admin_contact_add_note'),
    path('admin/contacts/<int:contact_id>/delete-note/', admin_views.admin_contact_delete_note, name='admin_contact_delete_note'),
    path('admin/contacts/import/', admin_views.admin_contact_import, name='admin_contact_import'),
    path('admin/download-contact-template/', admin_views.admin_download_contact_template, name='admin_download_contact_template'),
    path('admin/accounts/', admin_views.admin_accounts, name='admin_accounts'),
    path('admin/accounts/create/', admin_views.admin_account_create, name='admin_account_create'),
    path('admin/accounts/<int:account_id>/', admin_views.admin_account_detail, name='admin_account_detail'),
    path('admin/accounts/<int:account_id>/edit/', admin_views.admin_account_edit, name='admin_account_edit'),
    path('admin/accounts/<int:account_id>/delete/', admin_views.admin_account_delete, name='admin_account_delete'),
    path('admin/accounts/import/', admin_views.admin_account_import, name='admin_account_import'),
    path('admin/download-account-template/', admin_views.admin_download_account_template, name='admin_download_account_template'),
    path('admin/deals/', admin_views.admin_deals, name='admin_deals'),
    path('admin/deals/create/', admin_views.admin_deal_create, name='admin_deal_create'),
    path('admin/deals/<int:deal_id>/', admin_views.admin_deal_detail, name='admin_deal_detail'),
    path('admin/deals/<int:deal_id>/edit/', admin_views.admin_deal_edit, name='admin_deal_edit'),
    path('admin/deals/import/', admin_views.admin_deal_import, name='admin_deal_import'),
    path('admin/download-deal-template/', admin_views.admin_download_deal_template, name='admin_download_deal_template'),
    path('admin/tasks/', admin_views.admin_tasks, name='admin_tasks'),
    path('admin/tasks/create/', admin_views.admin_task_create, name='admin_task_create'),
    path('admin/tasks/<int:task_id>/edit/', admin_views.admin_task_edit, name='admin_task_edit'),
    path('admin/calendar/', admin_views.admin_calendar, name='admin_calendar'),
    path('admin/products/', admin_views.admin_products, name='admin_products'),
    path('admin/products/create/', admin_views.admin_product_create, name='admin_product_create'),
    path('admin/products/<int:product_id>/', admin_views.admin_product_detail, name='admin_product_detail'),
    path('admin/products/<int:product_id>/edit/', admin_views.admin_product_edit, name='admin_product_edit'),
    path('admin/products/import/', admin_views.admin_product_import, name='admin_product_import'),
    path('admin/download-product-template/', admin_views.admin_download_product_template, name='admin_download_product_template'),
    path('admin/transactions/', admin_views.admin_transactions, name='admin_transactions'),
    path('admin/transactions/create/', admin_views.admin_transaction_create, name='admin_transaction_create'),
    path('admin/transactions/<int:transaction_id>/', admin_views.admin_transaction_detail, name='admin_transaction_detail'),
    path('admin/transactions/<int:transaction_id>/edit/', admin_views.admin_transaction_edit, name='admin_transaction_edit'),
    path('admin/transactions/import/', admin_views.admin_transaction_import, name='admin_transaction_import'),
    path('admin/download-transaction-template/', admin_views.admin_download_transaction_template, name='admin_download_transaction_template'),
    path('admin/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin/download-user-template/', admin_views.admin_download_user_template, name='admin_download_user_template'),
    path('admin/api/dashboard-data/', admin_views.admin_api_dashboard_data, name='admin_api_dashboard_data'),
]
