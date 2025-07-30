from django.contrib import admin
from .models import (
    Industry, Account, Contact, Lead, Deal, Task, Event, 
    Note, Document, Transaction, Product, DealProduct, UserProfile
)

# Register your models here.
@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'phone', 'website', 'industry', 'assigned_to', 'created_at')
    list_filter = ('account_type', 'industry', 'created_at')
    search_fields = ('name', 'website', 'phone', 'description')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'account', 'job_title', 'assigned_to')
    list_filter = ('account', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'job_title')

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'company', 'email', 'phone', 'lead_status', 'lead_source', 'assigned_to')
    list_filter = ('lead_status', 'lead_source', 'industry', 'created_at')
    search_fields = ('first_name', 'last_name', 'company', 'email', 'phone')

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('name', 'account', 'amount', 'closing_date', 'stage', 'probability', 'assigned_to')
    list_filter = ('stage', 'created_at', 'closing_date')
    search_fields = ('name', 'description')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('subject', 'due_date', 'status', 'priority', 'assigned_to')
    list_filter = ('status', 'priority', 'due_date')
    search_fields = ('subject', 'description')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'location', 'created_by')
    list_filter = ('start_time', 'end_time', 'all_day')
    search_fields = ('title', 'description', 'location')

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('subject', 'content')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'reference_number', 'amount', 'date', 'due_date', 'status', 'account')
    list_filter = ('transaction_type', 'status', 'date', 'due_date')
    search_fields = ('reference_number', 'description')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_code', 'category', 'unit_price', 'active')
    list_filter = ('active', 'category')
    search_fields = ('name', 'product_code', 'description')

@admin.register(DealProduct)
class DealProductAdmin(admin.ModelAdmin):
    list_display = ('deal', 'product', 'quantity', 'unit_price', 'discount_percentage', 'total_price')
    list_filter = ('deal', 'product')
    search_fields = ('deal__name', 'product__name', 'description')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'role', 'department')
    search_fields = ('user__username', 'user__email', 'phone', 'role', 'department')
