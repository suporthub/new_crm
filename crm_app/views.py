from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .utils import log_user_activity

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Industry, Account, Contact, Lead, Deal, Task, Event, 
    Note, Document, Transaction, Product, DealProduct, UserProfile, AllotManager
)
from .serializers import (
    UserSerializer, UserProfileSerializer, IndustrySerializer, AccountSerializer,
    ContactSerializer, LeadSerializer, DealSerializer, TaskSerializer, EventSerializer,
    NoteSerializer, DocumentSerializer, TransactionSerializer, ProductSerializer,
    DealProductSerializer, UserRegistrationSerializer, ChangePasswordSerializer,
    DashboardSerializer, AllotManagerSerializer
)

# Authentication views
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    import logging
    logger = logging.getLogger(__name__)
    from django.contrib.auth import login # Import Django's login function
    
    logger.info("=== Starting login_user view ===")
    username = request.data.get('username')
    password = request.data.get('password')
    
    logger.info(f"Login attempt for username: '{username}' (received from request data)")
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        logger.info(f"authenticate() returned User: ID={user.id}, Username='{user.username}', IsActive={user.is_active}")
    else:
        logger.warning(f"authenticate() failed for username: '{username}'")
    
    logger.info(f"Authentication result (overall): {'Success' if user else 'Failed'}")
    
    if user:
        # Ensure the user is active
        if not user.is_active:
            logger.warning(f"User {username} is not active")
            return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)
        
        # Log the user into the Django session framework
        logger.info(f"Calling django.contrib.auth.login() with User: ID={user.id}, Username='{user.username}'")
        login(request, user)
        logger.info(f"After login() call, request.user is: ID={request.user.id if hasattr(request.user, 'id') else 'N/A'}, Username='{request.user.username if hasattr(request.user, 'username') else 'N/A'}'")
        logger.info(f"Session _auth_user_id after login(): {request.session.get('_auth_user_id')}")
        logger.info(f"Session auth_user_id (custom) after login(): {request.session.get('auth_user_id')}") # This is your custom one
        
        # Get user profile information
        try:
            profile = UserProfile.objects.get(user=user)
            logger.info(f"Found user profile - Manager username: {profile.manager_username}")
            
            # Store user info in session
            request.session['auth_user_id'] = user.id
            request.session['manager_username'] = profile.manager_username
            request.session.save()
            
            logger.info(f"Stored in session - User ID: {user.id}, Manager: {profile.manager_username}")
        except UserProfile.DoesNotExist:
            logger.warning(f"No profile found for user {username}")
            profile = None
        
        # Get the real client IP address
        ip_address = get_client_ip(request)
        logger.info(f"Login from IP: {ip_address}")
        
        # Log the login activity
        log_user_activity(
            user=user,
            action_type='login',
            action_detail=f'User logged in: {username}',
            ip_address=ip_address
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Prepare response data
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        }
        
        # Add profile data if available
        if profile:
            response_data['user']['manager_username'] = profile.manager_username
            response_data['user']['profile_id'] = profile.id
        
        logger.info("=== Login successful ===")
        return Response(response_data)
    
    logger.warning(f"Login failed for username: {username}")
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get the currently authenticated user's information"""
    user = request.user
    return Response(UserSerializer(user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if user.check_password(serializer.validated_data['old_password']):
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response({'error': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

# Dashboard view
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    # Get counts - filter leads by current user
    leads_count = Lead.objects.filter(assigned_to=request.user).count()
    contacts_count = Contact.objects.count()
    accounts_count = Account.objects.count()
    deals_count = Deal.objects.count()
    tasks_count = Task.objects.count()
    
    # Get deals by stage
    deals_by_stage = {}
    for stage_choice in Deal.DEAL_STAGES:
        stage_code = stage_choice[0]
        stage_name = stage_choice[1]
        count = Deal.objects.filter(stage=stage_code).count()
        deals_by_stage[stage_name] = count
    
    # Get recent leads (last 5)
    recent_leads = Lead.objects.all().order_by('-created_at')[:5]
    
    # Get recent deals (last 5)
    recent_deals = Deal.objects.all().order_by('-created_at')[:5]
    
    # Get upcoming tasks (next 5 due) assigned to the current user
    upcoming_tasks = Task.objects.filter(
        status__in=['not_started', 'in_progress', 'waiting'],
        due_date__gte=timezone.now(),
        assigned_to=request.user  # Only show tasks assigned to the current user
    ).order_by('due_date')[:5]
    
    # Safe serialization of tasks using the proper field names
    try:
        # Try to use the TaskSerializer first
        upcoming_tasks_data = TaskSerializer(upcoming_tasks, many=True).data
    except Exception as e:
        # Fallback to basic task data with the correct field names
        upcoming_tasks_data = [
            {
                'id': task.id,
                'subject': task.subject,  # Use subject instead of title
                'due_date': task.due_date,
                'status': task.status,
                'priority': task.priority,
                'status_display': task.get_status_display(),
                'priority_display': task.get_priority_display(),
                'assigned_to_name': task.assigned_to.get_full_name() if task.assigned_to else ''
            } for task in upcoming_tasks
        ]
    
    # Create serialized data for leads and deals first
    serialized_leads = []
    for lead in recent_leads:
        lead_data = {
            'id': lead.id,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'company': lead.company,
            'email': lead.email,
            'phone': lead.phone,
            'lead_status': lead.lead_status,
            'lead_source': lead.lead_source,
            'created_at': lead.created_at
        }
        # Add assigned_to if it exists
        if lead.assigned_to:
            lead_data['assigned_to'] = lead.assigned_to.id
            lead_data['assigned_to_name'] = lead.assigned_to.get_full_name()
        serialized_leads.append(lead_data)
    
    serialized_deals = []
    for deal in recent_deals:
        deal_data = {
            'id': deal.id,
            'name': deal.name,
            'amount': deal.amount,
            'stage': deal.stage,
            'expected_close_date': deal.expected_close_date,
            'created_at': deal.created_at
        }
        # Add assigned_to if it exists
        if deal.assigned_to:
            deal_data['assigned_to'] = deal.assigned_to.id
            deal_data['assigned_to_name'] = deal.assigned_to.get_full_name()
        # Add account if it exists
        if deal.account:
            deal_data['account'] = deal.account.id
            deal_data['account_name'] = deal.account.name
        # Add stage display
        deal_data['stage_display'] = deal.get_stage_display()
        serialized_deals.append(deal_data)
    
    dashboard_data = {
        'leads_count': leads_count,
        'contacts_count': contacts_count,
        'accounts_count': accounts_count,
        'deals_count': deals_count,
        'tasks_count': tasks_count,
        'deals_by_stage': deals_by_stage,
        'recent_leads': serialized_leads,
        'recent_deals': serialized_deals,
        'upcoming_tasks': upcoming_tasks_data
    }
    
    return Response(dashboard_data)

# ViewSets for all models
class IndustryViewSet(viewsets.ModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'website', 'phone', 'description']
    ordering_fields = ['name', 'created_at', 'annual_revenue']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        account = self.get_object()
        contacts = Contact.objects.filter(account=account)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def deals(self, request, pk=None):
        account = self.get_object()
        deals = Deal.objects.filter(account=account)
        serializer = DealSerializer(deals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        account = self.get_object()
        tasks = Task.objects.filter(related_account=account)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        account = self.get_object()
        notes = Note.objects.filter(related_account=account)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        account = self.get_object()
        documents = Document.objects.filter(related_account=account)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        account = self.get_object()
        transactions = Transaction.objects.filter(account=account)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'mobile', 'job_title']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def deals(self, request, pk=None):
        contact = self.get_object()
        deals = Deal.objects.filter(contacts=contact)
        serializer = DealSerializer(deals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        contact = self.get_object()
        tasks = Task.objects.filter(related_contact=contact)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        contact = self.get_object()
        notes = Note.objects.filter(related_contact=contact)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        contact = self.get_object()
        documents = Document.objects.filter(related_contact=contact)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'company', 'email', 'phone', 'mobile']
    ordering_fields = ['first_name', 'last_name', 'created_at', 'lead_status']
    
    def get_queryset(self):
        """
        This view should return a list of all leads that are either:
        1. Assigned to the currently authenticated user, OR
        2. Not assigned to any user (assigned_to is null)
        """
        user = self.request.user
        # Filter leads to show only those assigned to current user or with null assigned_to
        return Lead.objects.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        lead = self.get_object()
        
        # Check if lead is already converted
        if lead.lead_status == 'converted':
            return Response({'error': 'Lead is already converted'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create account if it doesn't exist
        account_data = request.data.get('account', {})
        if not account_data.get('id'):
            account_serializer = AccountSerializer(data={
                'name': lead.company or f"{lead.first_name} {lead.last_name}'s Company",
                'phone': lead.phone,
                'email': lead.email,
                'website': lead.website,
                'industry': lead.industry.id if lead.industry else None,
                'annual_revenue': lead.annual_revenue,
                'employees': lead.employees,
                'description': lead.description,
                'billing_address': lead.address,
                'manager_username': lead.manager_username,
                'assigned_to': lead.assigned_to.id if lead.assigned_to else None
            })
            if account_serializer.is_valid():
                account = account_serializer.save(created_by=request.user)
            else:
                return Response(account_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            account = get_object_or_404(Account, id=account_data.get('id'))
        
        # Create contact
        contact_serializer = ContactSerializer(data={
            'salutation': lead.salutation,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'mobile': lead.mobile,
            'job_title': lead.title,
            'account': account.id,
            'mailing_address': lead.address,
            'description': lead.description,
            'manager_username': lead.manager_username,
            'assigned_to': lead.assigned_to.id if lead.assigned_to else None
        })
        if contact_serializer.is_valid():
            contact = contact_serializer.save(created_by=request.user)
        else:
            return Response(contact_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create deal if requested
        deal = None
        deal_data = request.data.get('deal', {})
        if deal_data.get('create_deal', False):
            deal_serializer = DealSerializer(data={
                'name': deal_data.get('name', f"Deal for {lead.first_name} {lead.last_name}"),
                'account': account.id,
                'amount': deal_data.get('amount', 0),
                'closing_date': deal_data.get('closing_date', timezone.now().date()),
                'stage': deal_data.get('stage', 'qualification'),
                'probability': deal_data.get('probability', 10),
                'description': deal_data.get('description', ''),
                'assigned_to': lead.assigned_to.id if lead.assigned_to else None
            })
            if deal_serializer.is_valid():
                deal = deal_serializer.save(created_by=request.user)
                # Add contact to deal
                deal.contacts.add(contact)
            else:
                return Response(deal_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update lead as converted
        lead.lead_status = 'converted'
        lead.converted_account = account
        lead.converted_contact = contact
        lead.save()
        
        return Response({
            'message': 'Lead converted successfully',
            'account': AccountSerializer(account).data,
            'contact': ContactSerializer(contact).data,
            'deal': DealSerializer(deal).data if deal else None
        })
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        lead = self.get_object()
        tasks = Task.objects.filter(related_lead=lead)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        lead = self.get_object()
        notes = Note.objects.filter(related_lead=lead)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        lead = self.get_object()
        documents = Document.objects.filter(related_lead=lead)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)

class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'amount', 'closing_date', 'stage', 'probability']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        deal = self.get_object()
        contacts = deal.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_contact(self, request, pk=None):
        deal = self.get_object()
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'error': 'Contact ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            contact = Contact.objects.get(id=contact_id)
            deal.contacts.add(contact)
            return Response({'message': 'Contact added to deal'})
        except Contact.DoesNotExist:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_contact(self, request, pk=None):
        deal = self.get_object()
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'error': 'Contact ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            contact = Contact.objects.get(id=contact_id)
            deal.contacts.remove(contact)
            return Response({'message': 'Contact removed from deal'})
        except Contact.DoesNotExist:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        deal = self.get_object()
        products = DealProduct.objects.filter(deal=deal)
        serializer = DealProductSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        deal = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        unit_price = request.data.get('unit_price')
        discount_percentage = request.data.get('discount_percentage', 0)
        description = request.data.get('description', '')
        
        if not product_id or not unit_price:
            return Response({'error': 'Product ID and unit price are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
            deal_product = DealProduct.objects.create(
                deal=deal,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount_percentage=discount_percentage,
                description=description,
                total_price=quantity * float(unit_price) * (1 - float(discount_percentage) / 100)
            )
            serializer = DealProductSerializer(deal_product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        deal = self.get_object()
        tasks = Task.objects.filter(related_deal=deal)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        deal = self.get_object()
        notes = Note.objects.filter(related_deal=deal)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        deal = self.get_object()
        documents = Document.objects.filter(related_deal=deal)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        deal = self.get_object()
        transactions = Transaction.objects.filter(deal=deal)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'description']
    ordering_fields = ['subject', 'due_date', 'status', 'priority', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.completed_date = timezone.now()
        task.save()
        serializer = TaskSerializer(task)
        return Response(serializer.data)
    
    def get_queryset(self):
        """Return tasks visible to the requesting user.
        Logic:
        • Staff/superuser → all tasks.
        • Manager → tasks they created/assigned plus tasks involving managed users (assigned_to/created_by) or with matching manager_username.
        • Regular user → tasks assigned to or created by them.
        Supports same filter query-params as before.
        """
        from django.db.models import Q as models_Q
        user = self.request.user

        # Determine role
        is_staff = user.is_staff or user.is_superuser
        is_manager = False
        if hasattr(user, 'profile') and user.profile and user.profile.role:
            is_manager = user.profile.role.lower() == 'manager'

        if is_staff:
            queryset = Task.objects.all()
        elif is_manager:
            manager_username = user.username
            managed_user_ids = User.objects.filter(profile__manager_username=manager_username).values_list('id', flat=True)
            queryset = Task.objects.filter(
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id__in=managed_user_ids) |
                models_Q(assigned_to=user) |
                models_Q(created_by=user)
            ).distinct()
        else:
            queryset = Task.objects.filter(models_Q(assigned_to=user) | models_Q(created_by=user))

        # Get filter parameters
        status_param = self.request.query_params.get('status')
        priority_param = self.request.query_params.get('priority')
        due_date_param = self.request.query_params.get('due_date')
        due_date_start_param = self.request.query_params.get('due_date_start')
        due_date_end_param = self.request.query_params.get('due_date_end')
        all_tasks_param = self.request.query_params.get('all_tasks')
        
        # If the all_tasks parameter is set to 'true' and the user is staff/admin,
        # show all tasks (for admin purposes)
        if all_tasks_param == 'true' and self.request.user.is_staff:
            queryset = Task.objects.all()
        
        # Apply filters
        if status_param:
            queryset = queryset.filter(status=status_param)
        if priority_param:
            queryset = queryset.filter(priority=priority_param)
        if due_date_param:
            queryset = queryset.filter(due_date__date=due_date_param)
        
        # Date range filtering for calendar view (timezone-aware & full-day inclusive)
        if due_date_start_param and due_date_end_param:
            from datetime import datetime, time as dt_time
            from django.utils.dateparse import parse_date
            from django.utils.timezone import make_aware, get_default_timezone, is_naive

            start_date_obj = parse_date(due_date_start_param)
            end_date_obj = parse_date(due_date_end_param)
            if start_date_obj and end_date_obj:
                tz = get_default_timezone()
                start_dt = datetime.combine(start_date_obj, dt_time.min)
                end_dt = datetime.combine(end_date_obj, dt_time.max)
                # Make timezone-aware if naive
                if is_naive(start_dt):
                    start_dt = make_aware(start_dt, tz)
                if is_naive(end_dt):
                    end_dt = make_aware(end_dt, tz)
                queryset = queryset.filter(due_date__range=(start_dt, end_dt))
            queryset = queryset.filter(
                due_date__date__gte=due_date_start_param,
                due_date__date__lte=due_date_end_param
            )
        
        return queryset

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['title', 'start_time', 'end_time', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            event.attendees.add(user)
            return Response({'message': 'Attendee added to event'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            event.attendees.remove(user)
            return Response({'message': 'Attendee removed from event'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def get_queryset(self):
        queryset = Event.objects.all()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(
                Q(start_time__date__gte=start_date, start_time__date__lte=end_date) |
                Q(end_time__date__gte=start_date, end_time__date__lte=end_date) |
                Q(start_time__date__lte=start_date, end_time__date__gte=end_date)
            )
        
        return queryset

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'content']
    ordering_fields = ['subject', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference_number', 'description']
    ordering_fields = ['date', 'due_date', 'amount', 'status', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        queryset = Transaction.objects.all()
        transaction_type = self.request.query_params.get('transaction_type')
        status_param = self.request.query_params.get('status')
        account_id = self.request.query_params.get('account_id')
        deal_id = self.request.query_params.get('deal_id')
        
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'product_code', 'category', 'description']
    ordering_fields = ['name', 'category', 'unit_price', 'created_at']
    
    def get_queryset(self):
        queryset = Product.objects.all()
        active_only = self.request.query_params.get('active_only')
        category = self.request.query_params.get('category')
        
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(active=True)
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset

class DealProductViewSet(viewsets.ModelViewSet):
    queryset = DealProduct.objects.all()
    serializer_class = DealProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['deal__name', 'product__name', 'quantity', 'unit_price', 'total_price']
    
    def get_queryset(self):
        queryset = DealProduct.objects.all()
        deal_id = self.request.query_params.get('deal_id')
        product_id = self.request.query_params.get('product_id')
        
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset

# Web views for frontend
def index(request):
    return render(request, 'crm_app/index.html')

def login_page(request):
    return render(request, 'crm_app/login.html')

def dashboard_page(request):
    return render(request, 'crm_app/dashboard.html')

@login_required
def leads_page(request):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== Starting leads_page view ===")
    
    # request.user is populated by @login_required due to `django.contrib.auth.login()` in `login_user` view.
    # No need to manually set request.user from session or JWT here.
    logger.info(f"Authenticated user (from @login_required): {request.user.username} (ID: {request.user.id}), IsAuthenticated: {request.user.is_authenticated}")

    # Defensive check, though @login_required should handle this.
    if not request.user.is_authenticated:
        logger.warning("User is not authenticated despite @login_required. Redirecting to login.")
        return redirect('login')

    user_manager_username = None  # Default
    user_profile = None           # Default
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_manager_username = user_profile.manager_username
        
        # Log current user and their manager for debugging.
        # Session 'manager_username' (set at login) can be logged for comparison if needed:
        # session_manager_at_login = request.session.get('manager_username')
        # logger.info(f"UserProfile found for {request.user.username}. Manager from profile: {user_manager_username}. Manager from session at login: {session_manager_at_login}")
        logger.info(f"UserProfile found for {request.user.username}. Manager from profile: {user_manager_username}.")

        # The print statements for debugging can remain if the user finds them helpful.
        print(f"Current user: {request.user.username}") # Should now be the correct logged-in user
        print(f"User profile: {user_profile}")
        print(f"Manager username: {user_manager_username}")

    except UserProfile.DoesNotExist:
        logger.warning(f"No UserProfile found for user {request.user.username}. Lead filtering might be affected.")
        # user_manager_username remains None.
    
    # Get sorting parameters from request
    sort_field = request.GET.get('sort', '-created_at')
    sort_direction = request.GET.get('direction', 'desc')
    logger.info(f"Sort parameters - field: {sort_field}, direction: {sort_direction}")
    
    # Validate sort field
    valid_sort_fields = ['first_name', 'last_name', 'email', 'company', 'lead_status', 'lead_source', 'created_at']
    if sort_field.lstrip('-') not in valid_sort_fields:
        logger.warning(f"Invalid sort field: {sort_field}, defaulting to -created_at")
        sort_field = '-created_at'
    
    # Build the queryset with new visibility rules
    logger.info("Building leads queryset with conditions:")

    # Condition 1: Leads assigned directly to the current user
    q_assigned_to_me = Q(assigned_to=request.user)
    logger.info(f" - Including leads assigned to: {request.user.username} (ID: {request.user.id})")

    # Condition 2: Unassigned leads within managerial scope
    q_unassigned_criteria = Q(assigned_to__isnull=True)
    
    # Managerial visibility for unassigned leads includes:
    # a) Leads where Lead.manager_username is the current user's username (current user is the direct manager for these leads)
    q_managerial_scope_for_unassigned = Q(manager_username=request.user.username)
    logger.info(f" - Including unassigned leads where Lead.manager_username is: '{request.user.username}' (current user)")

    # b) Leads where Lead.manager_username is the current user's manager (from UserProfile)
    if user_manager_username and user_manager_username != request.user.username:
        q_managerial_scope_for_unassigned |= Q(manager_username=user_manager_username)
        logger.info(f" - Including unassigned leads where Lead.manager_username is: '{user_manager_username}' (current user's manager)")
    elif not user_manager_username:
        logger.info(" - Current user has no manager specified in UserProfile, so manager's scope for unassigned leads is not applied.")
    
    q_visible_unassigned = q_unassigned_criteria & q_managerial_scope_for_unassigned
    
    # Combine: (Assigned to me) OR (Visible Unassigned)
    final_query = q_assigned_to_me | q_visible_unassigned
    
    logger.info(f"Final query structure: (Assigned to '{request.user.username}') OR (IsUnassigned AND (LeadManager='{request.user.username}' OR LeadManager='{user_manager_username if user_manager_username else 'N/A'}'))")

    # Query for leads
    leads = Lead.objects.filter(final_query).distinct()
    
    # Log the initial query results
    logger.info(f"Initial query count: {leads.count()}")
    logger.info("Sample of leads found:")
    for lead in leads[:5]:  # Log first 5 leads for debugging
        logger.info(f"- Lead ID: {lead.id}, Name: {lead.first_name} {lead.last_name}")
        logger.info(f"  Assigned to: {lead.assigned_to}")
        logger.info(f"  Manager username: {lead.manager_username}")
    
    # Apply sorting
    try:
        if sort_field.startswith('-'):
            actual_field = sort_field[1:]
            is_descending = True
        else:
            actual_field = sort_field
            is_descending = False
        
        # Apply requested sort direction
        if sort_direction == 'asc' and is_descending:
            sort_field = actual_field
        elif sort_direction == 'desc' and not is_descending:
            sort_field = f'-{actual_field}'
        
        leads = leads.order_by(sort_field)
        logger.info(f"Applied sorting: {sort_field}")
    except Exception as e:
        logger.error(f"Error applying sort: {str(e)}")
        leads = leads.order_by('-created_at')
        logger.info("Fell back to default sorting")
    
    # Final count after all filters and sorting
    final_count = leads.count()
    logger.info(f"Final leads count: {final_count}")
    
    # Log user activity
    log_user_activity(
        user=request.user,
        action_type='view',
        action_detail=f'Viewed leads page (found {final_count} leads)'
    )
    
    context = {
        'leads': leads,
        'active_page': 'leads',
        'sort_field': actual_field,
        'sort_direction': sort_direction,
        'total_leads': final_count,
        'user_profile': user_profile if 'user_profile' in locals() else None,
        'logged_in_user_manager_username': user_manager_username, # Pass the manager's username
    }
    
    logger.info("=== Finishing leads_page view ===")
    return render(request, 'crm_app/leads.html', context)

def lead_detail_page(request, lead_id):
    # Pass the lead_id to the template
    context = {
        'lead_id': lead_id
    }
    return render(request, 'crm_app/lead_detail.html', context)

def lead_edit_page(request, lead_id):
    # Pass the lead_id to the template
    context = {
        'lead_id': lead_id
    }
    return render(request, 'crm_app/lead_edit.html', context)

def contacts_page(request):
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='view',
            action_detail='Viewed contacts page',
            ip_address=ip_address
        )
    return render(request, 'crm_app/contacts.html')


def contact_detail(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    
    # Get related notes
    notes = Note.objects.filter(related_contact=contact).order_by('-created_at')
    
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='view',
            action_detail=f'Viewed contact detail: {contact.first_name} {contact.last_name}',
            ip_address=ip_address
        )
    
    context = {
        'contact': contact,
        'notes': notes
    }
    
    return render(request, 'crm_app/contact_detail.html', context)


def contact_edit(request, contact_id=None):
    # If contact_id is provided, we're editing an existing contact
    # Otherwise, we're creating a new contact
    if contact_id:
        contact = get_object_or_404(Contact, id=contact_id)
        action_type = 'update'
        action_detail = f'Updated contact: {contact.first_name} {contact.last_name}'
    else:
        contact = None
        action_type = 'create'
        action_detail = 'Created new contact'
    
    # Get all accounts for the dropdown
    accounts = Account.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Validate required fields
        errors = []
        if not first_name:
            errors.append('First name is required')
        if not last_name:
            errors.append('Last name is required')
        if not email:
            errors.append('Email is required')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'contact': contact,
                'accounts': accounts
            }
            return render(request, 'crm_app/contact_edit.html', context)
        
        # Create or update contact
        if not contact:
            contact = Contact()
            contact.created_by = request.user
        
        # Update contact fields
        contact.first_name = first_name
        contact.last_name = last_name
        contact.email = email
        
        # Optional fields
        phone = request.POST.get('phone', '')
        contact.phone = phone if phone.strip() else None
        
        job_title = request.POST.get('job_title', '')
        contact.job_title = job_title if job_title.strip() else None
        
        
        address = request.POST.get('address', '')
        contact.address = address if address.strip() else None
        
        # Handle account if selected
        account_id = request.POST.get('account', '')
        if account_id and account_id.strip():
            try:
                account = Account.objects.get(id=account_id)
                contact.account = account
            except (Account.DoesNotExist, ValueError):
                contact.account = None
        else:
            contact.account = None
        
        # Handle status
        status = request.POST.get('status', 'active')
        contact.is_active = (status == 'active')
        
        # Handle lead source
        lead_source = request.POST.get('lead_source', '')
        if lead_source and lead_source.strip():
            contact.lead_source = lead_source
        else:
            contact.lead_source = None
        
        # Save the contact
        try:
            contact.save()
            
            # Add note if provided
            note_content = request.POST.get('notes', '')
            if note_content and note_content.strip():
                note = Note(
                    content=note_content,
                    created_by=request.user,
                    related_contact=contact
                )
                note.save()
            
            # Log user activity
            if request.user.is_authenticated:
                ip_address = get_client_ip(request)
                log_user_activity(
                    user=request.user,
                    action_type=action_type,
                    action_detail=action_detail,
                    ip_address=ip_address
                )
            
            messages.success(request, f'Contact "{contact.first_name} {contact.last_name}" saved successfully!')
            return redirect('contact_detail', contact_id=contact.id)
        except Exception as e:
            messages.error(request, f'Error saving contact: {str(e)}')
    
    context = {
        'contact': contact,
        'accounts': accounts
    }
    
    return render(request, 'crm_app/contact_edit.html', context)


def contact_create(request):
    return contact_edit(request)


def contact_add_note(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '')
        content = request.POST.get('content', '')
        
        if subject.strip() and content.strip():
            note = Note(
                subject=subject,
                content=content,
                created_by=request.user,
                related_contact=contact
            )
            note.save()
            
            # Log user activity
            if request.user.is_authenticated:
                ip_address = get_client_ip(request)
                log_user_activity(
                    user=request.user,
                    action_type='create',
                    action_detail=f'Added note to contact: {contact.first_name} {contact.last_name}',
                    ip_address=ip_address
                )
            
            # For AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Note added successfully!'})
            
            messages.success(request, 'Note added successfully!')
        else:
            error_message = 'Both subject and content are required'
            
            # For AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_message}, status=400)
            
            messages.error(request, error_message)
    
    return redirect('contact_detail', contact_id=contact.id)


def contact_delete_note(request, contact_id, note_id):
    contact = get_object_or_404(Contact, id=contact_id)
    note = get_object_or_404(Note, id=note_id, related_contact=contact)
    
    if request.method == 'POST':
        note.delete()
        
        # Log user activity
        if request.user.is_authenticated:
            ip_address = get_client_ip(request)
            log_user_activity(
                user=request.user,
                action_type='delete',
                action_detail=f'Deleted note from contact: {contact.first_name} {contact.last_name}',
                ip_address=ip_address
            )
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Note deleted successfully!'})
        
        messages.success(request, 'Note deleted successfully!')
    
    return redirect('contact_detail', contact_id=contact.id)


def accounts_page(request):
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='view',
            action_detail='Viewed accounts page',
            ip_address=ip_address
        )
    return render(request, 'crm_app/accounts.html')


def account_detail(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    
    # Get related contacts, deals and notes
    contacts = Contact.objects.filter(account=account).order_by('first_name', 'last_name')
    deals = Deal.objects.filter(account=account).order_by('-created_at')
    notes = Note.objects.filter(related_account=account).order_by('-created_at')
    
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='view',
            action_detail=f'Viewed account detail: {account.name}',
            ip_address=ip_address
        )
    
    context = {
        'account': account,
        'contacts': contacts,
        'deals': deals,
        'notes': notes
    }
    
    return render(request, 'crm_app/account_detail.html', context)


def account_edit(request, account_id=None):
    # If account_id is provided, we're editing an existing account
    # Otherwise, we're creating a new account
    if account_id:
        account = get_object_or_404(Account, id=account_id)
        action_type = 'update'
        action_detail = f'Updated account: {account.name}'
    else:
        account = None
        action_type = 'create'
        action_detail = 'Created new account'
    
    # Get all industries for the dropdown
    industries = Industry.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        
        # Validate required fields
        if not name:
            messages.error(request, 'Account name is required')
            context = {
                'account': account,
                'industries': industries
            }
            return render(request, 'crm_app/account_edit.html', context)
        
        # Create or update account
        if not account:
            account = Account()
            account.created_by = request.user
            account.manager_username = request.user.username
        
        # Update account fields
        account.name = name
        
        # Optional fields
        account_type = request.POST.get('account_type', '')
        account.account_type = account_type if account_type.strip() else None
        
        phone = request.POST.get('phone', '')
        account.phone = phone if phone.strip() else None
        
        email = request.POST.get('email', '')
        account.email = email if email.strip() else None
        
        website = request.POST.get('website', '')
        account.website = website if website.strip() else None
        
        billing_address = request.POST.get('billing_address', '')
        account.billing_address = billing_address if billing_address.strip() else None
        
        shipping_address = request.POST.get('shipping_address', '')
        account.shipping_address = shipping_address if shipping_address.strip() else None
        
        description = request.POST.get('description', '')
        account.description = description if description.strip() else None
        
        # Handle numeric fields
        employees = request.POST.get('employees', '')
        if employees and employees.strip():
            try:
                account.employees = int(employees)
            except ValueError:
                account.employees = None
        else:
            account.employees = None
        
        annual_revenue = request.POST.get('annual_revenue', '')
        if annual_revenue and annual_revenue.strip():
            try:
                # Clean the input
                annual_revenue = annual_revenue.replace('$', '').replace(',', '')
                account.annual_revenue = float(annual_revenue)
            except ValueError:
                account.annual_revenue = None
        else:
            account.annual_revenue = None
        
        # Handle industry if selected
        industry_id = request.POST.get('industry', '')
        if industry_id and industry_id.strip():
            try:
                industry = Industry.objects.get(id=industry_id)
                account.industry = industry
            except (Industry.DoesNotExist, ValueError):
                account.industry = None
        else:
            account.industry = None
        
        # Save the account
        try:
            account.save()
            
            # Log user activity
            if request.user.is_authenticated:
                ip_address = get_client_ip(request)
                log_user_activity(
                    user=request.user,
                    action_type=action_type,
                    action_detail=action_detail,
                    ip_address=ip_address
                )
            
            messages.success(request, f'Account "{account.name}" saved successfully!')
            return redirect('account_detail', account_id=account.id)
        except Exception as e:
            messages.error(request, f'Error saving account: {str(e)}')
    
    context = {
        'account': account,
        'industries': industries
    }
    
    return render(request, 'crm_app/account_edit.html', context)


def account_create(request):
    return account_edit(request)


def account_add_note(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '')
        content = request.POST.get('content', '')
        
        if subject.strip() and content.strip():
            note = Note(
                subject=subject,
                content=content,
                created_by=request.user,
                related_account=account
            )
            note.save()
            
            # Log user activity
            if request.user.is_authenticated:
                ip_address = get_client_ip(request)
                log_user_activity(
                    user=request.user,
                    action_type='create',
                    action_detail=f'Added note to account: {account.name}',
                    ip_address=ip_address
                )
            
            # For AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Note added successfully!'})
            
            messages.success(request, 'Note added successfully!')
        else:
            error_message = 'Both subject and content are required'
            
            # For AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_message}, status=400)
            
            messages.error(request, error_message)
    
    return redirect('account_detail', account_id=account.id)


def account_delete_note(request, account_id, note_id):
    account = get_object_or_404(Account, id=account_id)
    note = get_object_or_404(Note, id=note_id, related_account=account)
    
    if request.method == 'POST':
        note.delete()
        
        # Log user activity
        if request.user.is_authenticated:
            ip_address = get_client_ip(request)
            log_user_activity(
                user=request.user,
                action_type='delete',
                action_detail=f'Deleted note from account: {account.name}',
                ip_address=ip_address
            )
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Note deleted successfully!'})
        
        messages.success(request, 'Note deleted successfully!')
    
    return redirect('account_detail', account_id=account.id)

def deals_page(request):
    return render(request, 'crm_app/deals.html')

def tasks_page(request):
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Get the actual user from the session if available
        user = request.user
        if hasattr(request, 'session') and 'auth_user_id' in request.session:
            try:
                user_id = request.session.get('auth_user_id')
                if user_id and int(user_id) != user.id:
                    from django.contrib.auth.models import User
                    actual_user = User.objects.get(id=user_id)
                    print(f"Using session user: {actual_user.username} (ID: {actual_user.id})")
                    user = actual_user
            except Exception as e:
                print(f"Error getting session user: {str(e)}")
        
        # Print debug information
        print(f"Logging tasks view for user: {user.username} (ID: {user.id}) from IP: {ip_address}")
        
        # Log the activity
        log_user_activity(
            user=user,
            action_type='view',
            action_detail='Viewed tasks page',
            ip_address=ip_address
        )
    return render(request, 'crm_app/tasks.html')

def calendar_page(request):
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Get the actual user from the session if available
        user = request.user
        if hasattr(request, 'session') and 'auth_user_id' in request.session:
            try:
                user_id = request.session.get('auth_user_id')
                if user_id and int(user_id) != user.id:
                    from django.contrib.auth.models import User
                    actual_user = User.objects.get(id=user_id)
                    print(f"Using session user: {actual_user.username} (ID: {actual_user.id})")
                    user = actual_user
            except Exception as e:
                print(f"Error getting session user: {str(e)}")
        
        # Print debug information
        print(f"Logging calendar view for user: {user.username} (ID: {user.id}) from IP: {ip_address}")
        
        # Log the activity
        log_user_activity(
            user=user,
            action_type='view',
            action_detail='Viewed calendar page',
            ip_address=ip_address
        )
    return render(request, 'crm_app/calendar.html')

def reports_page(request):
    return render(request, 'crm_app/reports.html')

def settings_page(request):
    # Log user activity if user is authenticated
    if request.user.is_authenticated:
        # Get the real client IP address
        ip_address = get_client_ip(request)
        
        # Get the actual user from the session if available
        user = request.user
        if hasattr(request, 'session') and 'auth_user_id' in request.session:
            try:
                user_id = request.session.get('auth_user_id')
                if user_id and int(user_id) != user.id:
                    from django.contrib.auth.models import User
                    actual_user = User.objects.get(id=user_id)
                    print(f"Using session user: {actual_user.username} (ID: {actual_user.id})")
                    user = actual_user
            except Exception as e:
                print(f"Error getting session user: {str(e)}")
        
        # Print debug information
        print(f"Logging settings view for user: {user.username} (ID: {user.id}) from IP: {ip_address}")
        
        # Log the activity
        log_user_activity(
            user=user,
            action_type='view',
            action_detail='Viewed settings page',
            ip_address=ip_address
        )
    return render(request, 'crm_app/settings.html')

def profile_page(request):
    return render(request, 'crm_app/profile.html')

def transaction_page(request):
    return render(request, 'crm_app/transaction.html')

@api_view(['POST'])
@permission_classes([AllowAny])
def allot_lead_manager(request):
    """
    API endpoint to create a new lead and automatically assign a manager based on the country.
    """
    # Validate the incoming data using the LeadSerializer
    serializer = LeadSerializer(data=request.data)
    if serializer.is_valid():
        # Get the country from the request data (from address or explicitly provided)
        country = request.data.get('country')
        
        # If country is not provided, try to extract it from the address
        if not country and 'address' in request.data and request.data['address']:
            # This is a simple approach - in a real application, you might use a geocoding service
            # to extract the country from the address
            address = request.data['address']
            # For now, we'll just check if any country name appears in the address
            # In a real app, you'd use a more sophisticated approach
            try:
                # Try to find a matching country in the AllotManager table
                allot_managers = AllotManager.objects.all()
                for manager in allot_managers:
                    country_name = dict(AllotManager.COUNTRIES).get(manager.country)
                    if country_name and country_name.lower() in address.lower():
                        country = manager.country
                        break
            except Exception as e:
                print(f"Error extracting country from address: {e}")
        
        if country:
            try:
                # Look up the manager for this country
                manager = AllotManager.objects.filter(country=country).first()
                if manager and manager.manager_username:
                    # Set the manager_username in the lead data
                    serializer.validated_data['manager_username'] = manager.manager_username
            except Exception as e:
                print(f"Error finding manager for country {country}: {e}")
        
        # Save the lead with the assigned manager (if any)
        lead = serializer.save()
        
        # Return the created lead with status 201
        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)
    
    # If validation fails, return the errors
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Helper function to get client IP address
def get_client_ip(request):
    """Get the client's IP address from the request"""
    # Try multiple headers to find the real IP
    headers = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_CLIENT_IP',
        'REMOTE_ADDR'
    ]
    
    for header in headers:
        ip = request.META.get(header)
        if ip:
            # If it's a comma-separated list, take the first one
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            # Don't return localhost if we can help it
            if ip != '127.0.0.1' and ip != 'localhost':
                return ip
    
    # If we got here, use REMOTE_ADDR as fallback
    return request.META.get('REMOTE_ADDR', '')
