from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Count, Sum, Q
from django.utils import timezone

from .utils import log_user_activity

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Industry, Account, Contact, Lead, Deal, Task, Event, 
    Note, Document, Transaction, Product, DealProduct, UserProfile
)
from .serializers import (
    UserSerializer, UserProfileSerializer, IndustrySerializer, AccountSerializer,
    ContactSerializer, LeadSerializer, DealSerializer, TaskSerializer, EventSerializer,
    NoteSerializer, DocumentSerializer, TransactionSerializer, ProductSerializer,
    DealProductSerializer, UserRegistrationSerializer, ChangePasswordSerializer,
    DashboardSerializer
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
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        # Store the user ID in the session for tracking
        if hasattr(request, 'session'):
            request.session['auth_user_id'] = user.id
            request.session.save()
            print(f"Stored user ID {user.id} in session")
        
        # Get the real client IP address
        ip_address = get_client_ip(request)
        print(f"User login: {user.username} (ID: {user.id}) from IP: {ip_address}")
        
        # Log the login activity with the correct user ID
        log_user_activity(
            user=user,
            action_type='login',
            action_detail=f'User logged in: {user.username}',
            ip_address=ip_address
        )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })
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
        # Start with tasks assigned to the current user
        queryset = Task.objects.filter(assigned_to=self.request.user)
        
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
        
        # Date range filtering for calendar view
        if due_date_start_param and due_date_end_param:
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

def leads_page(request):
    return render(request, 'crm_app/leads.html')

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
    return render(request, 'crm_app/contacts.html')

def accounts_page(request):
    return render(request, 'crm_app/accounts.html')

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
