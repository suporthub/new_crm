from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Industry, Account, Contact, Lead, Deal, Task, Event, 
    Note, Document, Transaction, Product, DealProduct, UserProfile,
    UserSettings, UserActivityLog, AllotManager
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        read_only_fields = ['is_active']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'phone', 'address', 'profile_picture', 'role', 'department', 'manager_username']

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = '__all__'

class AccountSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = Account
        fields = '__all__'
        extra_fields = ['industry_name', 'assigned_to_name']

class ContactSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = '__all__'
        extra_fields = ['account_name', 'assigned_to_name', 'full_name']
    
    def get_full_name(self, obj):
        salutation = obj.get_salutation_display() if obj.salutation else ''
        return f"{salutation} {obj.first_name} {obj.last_name}".strip()

class LeadSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = '__all__'
        extra_fields = ['industry_name', 'assigned_to_name', 'full_name']
    
    def get_full_name(self, obj):
        salutation = obj.get_salutation_display() if obj.salutation else ''
        return f"{salutation} {obj.first_name} {obj.last_name}".strip()

class DealSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = '__all__'
        extra_fields = ['account_name', 'assigned_to_name', 'stage_display', 'contacts_count']
    
    def get_contacts_count(self, obj):
        return obj.contacts.count()

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    related_to = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = '__all__'
        extra_fields = ['assigned_to_name', 'status_display', 'priority_display', 'related_to']
    
    def get_related_to(self, obj):
        if obj.related_lead:
            return {'type': 'lead', 'id': obj.related_lead.id, 'name': f"{obj.related_lead.first_name} {obj.related_lead.last_name}"}
        elif obj.related_contact:
            return {'type': 'contact', 'id': obj.related_contact.id, 'name': f"{obj.related_contact.first_name} {obj.related_contact.last_name}"}
        elif obj.related_account:
            return {'type': 'account', 'id': obj.related_account.id, 'name': obj.related_account.name}
        elif obj.related_deal:
            return {'type': 'deal', 'id': obj.related_deal.id, 'name': obj.related_deal.name}
        return None

class EventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    attendees_names = serializers.SerializerMethodField()
    related_to = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
        extra_fields = ['created_by_name', 'attendees_names', 'related_to']
    
    def get_attendees_names(self, obj):
        return [{'id': user.id, 'name': user.get_full_name()} for user in obj.attendees.all()]
    
    def get_related_to(self, obj):
        if obj.related_lead:
            return {'type': 'lead', 'id': obj.related_lead.id, 'name': f"{obj.related_lead.first_name} {obj.related_lead.last_name}"}
        elif obj.related_contact:
            return {'type': 'contact', 'id': obj.related_contact.id, 'name': f"{obj.related_contact.first_name} {obj.related_contact.last_name}"}
        elif obj.related_account:
            return {'type': 'account', 'id': obj.related_account.id, 'name': obj.related_account.name}
        elif obj.related_deal:
            return {'type': 'deal', 'id': obj.related_deal.id, 'name': obj.related_deal.name}
        return None

class NoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    related_to = serializers.SerializerMethodField()
    
    class Meta:
        model = Note
        fields = '__all__'
        extra_fields = ['created_by_name', 'related_to']
    
    def get_related_to(self, obj):
        if obj.related_lead:
            return {'type': 'lead', 'id': obj.related_lead.id, 'name': f"{obj.related_lead.first_name} {obj.related_lead.last_name}"}
        elif obj.related_contact:
            return {'type': 'contact', 'id': obj.related_contact.id, 'name': f"{obj.related_contact.first_name} {obj.related_contact.last_name}"}
        elif obj.related_account:
            return {'type': 'account', 'id': obj.related_account.id, 'name': obj.related_account.name}
        elif obj.related_deal:
            return {'type': 'deal', 'id': obj.related_deal.id, 'name': obj.related_deal.name}
        return None

class DocumentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    related_to = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = '__all__'
        extra_fields = ['created_by_name', 'related_to', 'file_url']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_related_to(self, obj):
        if obj.related_lead:
            return {'type': 'lead', 'id': obj.related_lead.id, 'name': f"{obj.related_lead.first_name} {obj.related_lead.last_name}"}
        elif obj.related_contact:
            return {'type': 'contact', 'id': obj.related_contact.id, 'name': f"{obj.related_contact.first_name} {obj.related_contact.last_name}"}
        elif obj.related_account:
            return {'type': 'account', 'id': obj.related_account.id, 'name': obj.related_account.name}
        elif obj.related_deal:
            return {'type': 'deal', 'id': obj.related_deal.id, 'name': obj.related_deal.name}
        return None

class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    deal_name = serializers.CharField(source='deal.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        extra_fields = ['account_name', 'deal_name', 'transaction_type_display']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class DealProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    deal_name = serializers.CharField(source='deal.name', read_only=True)
    
    class Meta:
        model = DealProduct
        fields = '__all__'
        extra_fields = ['product_name', 'deal_name']

# Authentication serializers
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name']
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        return data

# Dashboard serializers
class DashboardTaskSerializer(serializers.Serializer):
    """Custom serializer for tasks in the dashboard to avoid related_lead errors"""
    id = serializers.IntegerField()
    subject = serializers.CharField()  # Changed from title to subject to match Task model
    due_date = serializers.DateTimeField()
    status = serializers.CharField()
    priority = serializers.CharField()
    status_display = serializers.CharField(required=False)
    priority_display = serializers.CharField(required=False)
    assigned_to_name = serializers.CharField(required=False, allow_blank=True)
    related_to = serializers.DictField(required=False, allow_null=True)

class DashboardSerializer(serializers.Serializer):
    leads_count = serializers.IntegerField()
    contacts_count = serializers.IntegerField()
    accounts_count = serializers.IntegerField()
    deals_count = serializers.IntegerField()
    tasks_count = serializers.IntegerField()
    deals_by_stage = serializers.DictField()
    recent_leads = LeadSerializer(many=True)
    recent_deals = DealSerializer(many=True)
    upcoming_tasks = DashboardTaskSerializer(many=True)


class UserSettingsSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSettings
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class AllotManagerSerializer(serializers.ModelSerializer):
    country_display = serializers.CharField(source='get_country_display', read_only=True)
    
    class Meta:
        model = AllotManager
        fields = '__all__'
        extra_fields = ['country_display']


class UserActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = UserActivityLog
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']
