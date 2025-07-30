from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Q as models_Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import random
import json
import decimal

from .models import (
    Industry, Account, Contact, Lead, Deal, Task, Event, 
    Note, Document, Transaction, Product, DealProduct, UserProfile, UserActivityLog
)

# Constants from models for use in views
DEAL_STAGE_CHOICES = Deal.DEAL_STAGES
LEAD_STATUS_CHOICES = Lead.LEAD_STATUSES
TASK_STATUS_CHOICES = Task.TASK_STATUSES
TASK_PRIORITY_CHOICES = Task.TASK_PRIORITIES

# Helper function to check if user is admin/superuser or manager
def is_admin(user):
    # First check if superuser
    if user.is_superuser:
        print(f"User {user.username} is superuser, allowing access")
        return True
    
    # Check for profile using the correct attribute name
    if hasattr(user, 'profile'):
        print(f"User {user.username} has profile with role: {user.profile.role}")
        if user.profile.role and user.profile.role.lower() in ['admin', 'manager']:
            print(f"User {user.username} has admin/manager role, allowing access")
            return True
    
    # Fallback check for userprofile attribute (if that's how it's defined)
    if hasattr(user, 'userprofile'):
        print(f"User {user.username} has userprofile with role: {user.userprofile.role}")
        if user.userprofile.role and user.userprofile.role.lower() in ['admin', 'manager']:
            print(f"User {user.username} has admin/manager role, allowing access")
            return True
    
    print(f"User {user.username} does not have admin/manager privileges")
    return False

# Admin Login View
def admin_login(request):
    # If user is already logged in and is an admin
    if request.user.is_authenticated and is_admin(request.user):
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Print for debugging (remove in production)
        print(f"Login attempt for username: {username}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"User authenticated: {user.username}")
            print(f"User has profile: {hasattr(user, 'profile')}")
            if hasattr(user, 'profile'):
                print(f"User role: {user.profile.role}")
            
            if is_admin(user):
                print(f"User passed is_admin check")
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect('admin_dashboard')
            else:
                print(f"User failed is_admin check")
                messages.error(request, 'Access denied: You do not have admin or manager privileges')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'admin/login.html')

# Admin Logout View
@login_required
@user_passes_test(is_admin)
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

# Admin Dashboard View
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get the manager's username and user ID if applicable
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if is_manager:
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Get IDs of users managed by this manager
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
    
    # Calculate dashboard statistics based on role
    if is_manager:
        # For managers, only count users they manage
        total_users = len(managed_user_ids) + 1  # +1 to include the manager
        new_users = User.objects.filter(
            models_Q(id__in=managed_user_ids) | models_Q(id=manager_id),
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Filter leads for this manager
        leads_filter = models_Q(manager_username=manager_username) | \
                      models_Q(assigned_to__id__in=managed_user_ids) | \
                      models_Q(created_by_id=manager_id)
        
        total_leads = Lead.objects.filter(leads_filter).distinct().count()
        new_leads = Lead.objects.filter(
            leads_filter,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).distinct().count()
        
        # Filter deals for this manager
        deals_filter = models_Q(assigned_to__id__in=managed_user_ids) | \
                      models_Q(created_by_id=manager_id)
        
        total_deals = Deal.objects.filter(deals_filter).distinct().count()
        new_deals = Deal.objects.filter(
            deals_filter,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).distinct().count()
        
        total_revenue = Deal.objects.filter(
            deals_filter,
            stage='closed_won'
        ).distinct().aggregate(Sum('amount'))['amount__sum'] or 0
        
        last_month_revenue = Deal.objects.filter(
            deals_filter,
            stage='closed_won', 
            created_at__gte=timezone.now() - timedelta(days=60),
            created_at__lt=timezone.now() - timedelta(days=30)
        ).distinct().aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Admin sees all statistics
        total_users = User.objects.count()
        new_users = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
        
        total_leads = Lead.objects.count()
        new_leads = Lead.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
        
        total_deals = Deal.objects.count()
        new_deals = Deal.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
        
        total_revenue = Deal.objects.filter(stage='closed_won').aggregate(Sum('amount'))['amount__sum'] or 0
        last_month_revenue = Deal.objects.filter(
            stage='closed_won', 
            created_at__gte=timezone.now() - timedelta(days=60),
            created_at__lt=timezone.now() - timedelta(days=30)
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_increase = total_revenue - last_month_revenue
    
    # Get recent activities from the activity log
    recent_activities_query = UserActivityLog.objects.all().order_by('-timestamp')[:5]
    recent_activities = []
    
    for activity in recent_activities_query:
        # Determine icon and color based on activity type
        icon = 'history'
        color = 'secondary'
        
        # Get the action detail or type for checking
        action_text = activity.action_detail.lower() if activity.action_detail else ''
        action_type = activity.action_type.lower() if activity.action_type else ''
        
        if 'user' in action_text or action_type == 'login' or action_type == 'logout':
            icon = 'user-plus'
            color = 'primary'
        elif 'lead' in action_text:
            icon = 'user'
            color = 'success'
        elif 'deal' in action_text:
            icon = 'handshake'
            color = 'info'
        elif 'task' in action_text:
            icon = 'tasks'
            color = 'warning'
        elif 'payment' in action_text or 'revenue' in action_text:
            icon = 'money-bill-wave'
            color = 'success'
        
        # Calculate time ago
        now = timezone.now()
        diff = now - activity.timestamp
        
        if diff.days > 0:
            time_ago = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            time_ago = "just now"
        
        recent_activities.append({
            'message': activity.action_detail,
            'timestamp': time_ago,
            'user': activity.user.get_full_name() if activity.user and hasattr(activity.user, 'get_full_name') else activity.user.username if activity.user else 'System',
            'icon': icon,
            'color': color
        })
    
    # Get system status (mock data for now)
    cpu_usage = random.randint(20, 60)
    memory_usage = random.randint(30, 70)
    disk_usage = random.randint(40, 70)
    
    db_type = 'PostgreSQL' if 'postgresql' in request.META.get('DATABASE_URL', 'sqlite') else 'SQLite'
    db_size = '250 MB'
    last_backup = (timezone.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M')
    uptime = '12 days, 5 hours'
    
    # Get recent users (mock data for now)
    recent_users = [
        {
            'id': 5,
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'role': 'Sales',
            'role_color': 'success',
            'registered_at': '2 hours ago',
            'avatar': ''
        },
        {
            'id': 4,
            'name': 'Mary Johnson',
            'email': 'mary.johnson@example.com',
            'role': 'Support',
            'role_color': 'info',
            'registered_at': '1 day ago',
            'avatar': ''
        },
        {
            'id': 3,
            'name': 'Robert Williams',
            'email': 'robert.williams@example.com',
            'role': 'Manager',
            'role_color': 'primary',
            'registered_at': '3 days ago',
            'avatar': ''
        },
    ]
    
    # Get pending tasks (mock data for now)
    pending_tasks = [
        {
            'id': 3,
            'subject': 'Follow up with potential client',
            'assigned_to': 'John Smith',
            'due_date': '2025-05-12',
            'status': 'In Progress',
            'status_color': 'primary'
        },
        {
            'id': 2,
            'subject': 'Prepare sales presentation',
            'assigned_to': 'Mary Johnson',
            'due_date': '2025-05-11',
            'status': 'Not Started',
            'status_color': 'secondary'
        },
        {
            'id': 1,
            'subject': 'Product demo meeting',
            'assigned_to': 'Robert Williams',
            'due_date': '2025-05-10',
            'status': 'Overdue',
            'status_color': 'danger'
        },
    ]
    
    # Get monthly revenue data for the sales chart
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    current_year = timezone.now().year
    monthly_revenue_data = [0] * 12
    monthly_deals_data = [0] * 12
    
    # Query deals for the current year
    deals_this_year = Deal.objects.filter(created_at__year=current_year, stage='closed_won')
    
    # Aggregate revenue and deals count by month
    for deal in deals_this_year:
        month_idx = deal.created_at.month - 1  # 0-based index for months
        monthly_revenue_data[month_idx] += deal.amount
        monthly_deals_data[month_idx] += 1
    
    # Get lead sources data for the pie chart
    lead_sources = {
        'website_demo': Lead.objects.filter(models_Q(lead_source='website_demo') | models_Q(lead_source='website')).count(),
        'website_live': Lead.objects.filter(lead_source='website_live').count(),
        'phone': Lead.objects.filter(lead_source='phone').count(),
        'referral': Lead.objects.filter(lead_source='referral').count(),
        'email': Lead.objects.filter(lead_source='email').count(),
        'social_media': Lead.objects.filter(lead_source='social_media').count(),
        'trade_show': Lead.objects.filter(lead_source='trade_show').count(),
        'email_campaign': Lead.objects.filter(lead_source='email_campaign').count(),
        'cold_call': Lead.objects.filter(lead_source='cold_call').count(),
        'event': Lead.objects.filter(lead_source='event').count(),
        'other': Lead.objects.filter(lead_source='other').count()
    }
    
    # Convert data to JSON for charts
    import json
    sales_chart_data = json.dumps({
        'labels': months,
        'revenue': monthly_revenue_data,
        'deals': monthly_deals_data
    })
    
    lead_sources_labels = ['Website - {Demo}', 'Website - {live}', 'Phone', 'Referral', 'Email', 'Social Media', 'Trade Show', 'Email Campaign', 'Cold Call', 'Event', 'Other']
    lead_sources_data = [
        lead_sources['website_demo'],
        lead_sources['website_live'],
        lead_sources['phone'],
        lead_sources['referral'],
        lead_sources['email'],
        lead_sources['social_media'],
        lead_sources['trade_show'],
        lead_sources['email_campaign'],
        lead_sources['cold_call'],
        lead_sources['event'],
        lead_sources['other']
    ]
    
    lead_sources_chart_data = json.dumps({
        'labels': lead_sources_labels,
        'data': lead_sources_data
    })
    
    context = {
        'active_page': 'dashboard',
        'total_users': total_users,
        'new_users': new_users,
        'total_leads': total_leads,
        'new_leads': new_leads,
        'total_deals': total_deals,
        'new_deals': new_deals,
        'total_revenue': int(total_revenue),
        'revenue_increase': int(revenue_increase),
        'recent_activities': recent_activities,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_usage': disk_usage,
        'db_type': db_type,
        'db_size': db_size,
        'last_backup': last_backup,
        'uptime': uptime,
        'recent_users': recent_users,
        'pending_tasks': pending_tasks,
        'sales_chart_data': sales_chart_data,
        'lead_sources_chart_data': lead_sources_chart_data
    }
    
    return render(request, 'admin/dashboard.html', context)

# Admin Profile View
@login_required
@user_passes_test(is_admin)
def admin_profile(request):
    user = request.user
    
    if request.method == 'POST':
        # Update user profile
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Update user object
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        # Update profile if it exists
        if hasattr(user, 'profile'):
            bio = request.POST.get('bio', '')
            phone = request.POST.get('phone', '')
            
            user.profile.bio = bio
            user.profile.phone = phone
            user.profile.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect('admin_profile')
    
    context = {
        'active_page': 'profile',
        'user': user
    }
    
    return render(request, 'admin/profile.html', context)

# Admin Settings View
@login_required
@user_passes_test(is_admin)
def admin_settings(request):
    user = request.user
    
    # Get or create user settings
    settings, created = UserSettings.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Determine which settings section is being updated
        section = request.POST.get('section', 'general')
        
        if section == 'general':
            # Update general settings
            settings.timezone = request.POST.get('timezone', settings.timezone)
            settings.date_format = request.POST.get('date_format', settings.date_format)
            settings.language = request.POST.get('language', settings.language)
        
        elif section == 'notifications':
            # Update notification settings
            settings.email_notifications = 'email_notifications' in request.POST
            settings.browser_notifications = 'browser_notifications' in request.POST
            settings.task_reminders = 'task_reminders' in request.POST
            settings.deal_updates = 'deal_updates' in request.POST
            settings.lead_notifications = 'lead_notifications' in request.POST
        
        elif section == 'security':
            # Update security settings
            settings.two_factor_auth = 'two_factor_auth' in request.POST
            settings.auto_logout = 'auto_logout' in request.POST
            settings.session_timeout = int(request.POST.get('session_timeout', 30))
        
        elif section == 'appearance':
            # Update appearance settings
            settings.theme = request.POST.get('theme', settings.theme)
            settings.color_scheme = request.POST.get('color_scheme', settings.color_scheme)
            settings.font_size = request.POST.get('font_size', settings.font_size)
            settings.compact_view = 'compact_view' in request.POST
        
        # Save settings
        settings.save()
        
        messages.success(request, f'{section.capitalize()} settings updated successfully')
        return redirect('admin_settings')
    
    context = {
        'active_page': 'settings',
        'settings': settings
    }
    
    return render(request, 'admin/settings.html', context)

# Admin User Management View
@login_required
@user_passes_test(is_admin)
def admin_users(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get users based on role
    users_query = User.objects.all()
    
    # If logged in as manager, only show users assigned to this manager
    if is_manager:
        # Get the manager's username
        manager_username = request.user.username
        
        # Filter users by manager_username in their profile
        users_with_profile = []
        for user in users_query:
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                users_with_profile.append(user.id)
        
        users_query = users_query.filter(id__in=users_with_profile)
    
    # Get all users with their profiles
    users_data = []
    for user in users_query.order_by('-date_joined'):
        # Default values
        role = 'User'
        role_color = 'secondary'
        department = ''
        
        # Get actual role from the database - using correct related_name 'profile'
        try:
            # UserProfile has related_name 'profile', not 'userprofile'
            if hasattr(user, 'profile') and user.profile:
                # Use the exact role from the database without altering case
                role = user.profile.role if user.profile.role else 'User'
                department = user.profile.department if user.profile.department else ''
                
                # Determine badge color based on role (case-insensitive)
                role_lower = role.lower() if role else ''
                if role_lower == 'admin':
                    role_color = 'danger'
                elif role_lower == 'manager':
                    role_color = 'primary'
                elif role_lower == 'sales':
                    role_color = 'success'
                elif role_lower == 'support':
                    role_color = 'info'
                else:
                    role_color = 'secondary'
        except Exception as e:
            print(f"Error getting user profile for {user.username}: {e}")
            role = 'User'
            department = ''
            role_color = 'secondary'
        
        # Format user name properly
        name = user.first_name + ' ' + user.last_name if (user.first_name and user.last_name) else user.username
        
        # Format last login
        last_login = 'Never' if not user.last_login else user.last_login.strftime('%Y-%m-%d %H:%M')
        
        # Get manager_username if it exists in the profile
        manager_username = ''
        if hasattr(user, 'profile') and user.profile and user.profile.manager_username:
            manager_username = user.profile.manager_username
            
        users_data.append({
            'id': user.id,
            'name': name,
            'username': user.username,
            'email': user.email,
            'role': role,
            'role_color': role_color,
            'department': department,
            'manager_username': manager_username,
            'is_active': user.is_active,
            'last_login': last_login,
            'date_joined': user.date_joined,
            'avatar': ''
        })
    
    # Get user statistics based on role
    if is_manager:
        # For managers, only count users assigned to them
        total_users = len(users_with_profile)
        active_users = User.objects.filter(id__in=users_with_profile, is_active=True).count()
        inactive_users = User.objects.filter(id__in=users_with_profile, is_active=False).count()
        new_users = User.objects.filter(
            id__in=users_with_profile,
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
    else:
        # Admin sees all users
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        new_users = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
    
    # Calculate role distribution for chart - use actual roles from database
    # First, collect all unique roles that exist in the data
    unique_roles = set()
    
    # If logged in as manager, only include users managed by this manager
    if is_manager:
        manager_username = request.user.username
        managed_user_ids = []
        
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
                if user.profile.role:
                    unique_roles.add(user.profile.role)
    else:
        # Admin sees all roles
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.role:
                # Keep the role exactly as it is in the database
                unique_roles.add(user.profile.role)
    
    # Create a counter for each unique role
    role_counts = {role: 0 for role in unique_roles}
    if not role_counts:  # If no roles were found, use default categories
        role_counts = {'User': 0}
    
    # Count users per role
    if is_manager:
        # Only count users managed by this manager
        for user in users_query:
            role = 'User'
            if hasattr(user, 'profile') and user.profile and user.profile.role:
                role = user.profile.role
            
            if role in role_counts:
                role_counts[role] += 1
            else:
                # Add the role if it wasn't in our initial set
                role_counts[role] = 1
    else:
        # Admin counts all users
        for user in User.objects.all():
            role = 'User'
            if hasattr(user, 'profile') and user.profile and user.profile.role:
                role = user.profile.role
            
            if role in role_counts:
                role_counts[role] += 1
            else:
                # Add the role if it wasn't in our initial set
                role_counts[role] = 1
    
    # Calculate monthly registration data for the chart
    current_year = timezone.now().year
    monthly_registrations = [0] * 12  # One entry per month
    
    if is_manager:
        # Only count users managed by this manager
        for user in users_query.filter(date_joined__year=current_year):
            month_idx = user.date_joined.month - 1  # Convert 1-12 to 0-11 for array index
            monthly_registrations[month_idx] += 1
    else:
        # Admin counts all users
        for user in User.objects.filter(date_joined__year=current_year):
            month_idx = user.date_joined.month - 1  # Convert 1-12 to 0-11 for array index
            monthly_registrations[month_idx] += 1
        
    # Convert data to JSON for JavaScript
    import json
    role_counts_json = json.dumps(role_counts)
    monthly_registrations_json = json.dumps(monthly_registrations)
    
    # Get current user's role
    current_user_role = 'admin'  # Default to admin
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        current_user_role = request.user.profile.role.lower()
    
    context = {
        'active_page': 'users',
        'users': users_data,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'new_users': new_users,
        'role_counts': role_counts_json,
        'monthly_registrations': monthly_registrations_json,
        'current_user_role': current_user_role
    }
    
    return render(request, 'admin/users.html', context)

# Admin User Detail View
@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Get user profile data
    try:
        profile = user.userprofile
    except:
        profile = None
    
    # Get user activity statistics - ensure we're counting only records created by this user
    leads_count = Lead.objects.filter(created_by=user).count()
    deals_count = Deal.objects.filter(created_by=user).count()
    tasks_count = Task.objects.filter(created_by=user).count()
    
    # Get real recent activity data
    recent_activity = []
    
    # Get recent leads created by this user
    recent_leads = Lead.objects.filter(created_by=user).order_by('-created_at')[:5]
    for lead in recent_leads:
        recent_activity.append({
            'action': 'Created lead',
            'target': f'{lead.first_name} {lead.last_name}',
            'timestamp': lead.created_at,
            'type': 'lead'
        })
    
    # Get recent deals created by this user
    recent_deals = Deal.objects.filter(created_by=user).order_by('-created_at')[:5]
    for deal in recent_deals:
        recent_activity.append({
            'action': 'Created deal',
            'target': f'{deal.account.name} - ${deal.amount}',
            'timestamp': deal.created_at,
            'type': 'deal'
        })
    
    # Get recent tasks created by this user
    recent_tasks = Task.objects.filter(created_by=user).order_by('-created_at')[:5]
    for task in recent_tasks:
        recent_activity.append({
            'action': 'Created task',
            'target': task.subject if hasattr(task, 'subject') else 'Task',
            'timestamp': task.created_at,
            'type': 'task'
        })
    
    # Sort all activities by timestamp (newest first) and limit to 10
    recent_activity = sorted(recent_activity, key=lambda x: x['timestamp'], reverse=True)[:10]
    
    # Get user activity logs with filtering if requested
    log_type = request.GET.get('log_type', None)
    activity_logs_query = UserActivityLog.objects.filter(user=user)
    
    if log_type:
        activity_logs_query = activity_logs_query.filter(action_type=log_type)
    
    # Order and limit the logs after all filters have been applied
    activity_logs = activity_logs_query.order_by('-timestamp')[:50]
    
    context = {
        'active_page': 'users',
        'user_data': user,
        'profile': profile,
        'leads_count': leads_count,
        'deals_count': deals_count,
        'tasks_count': tasks_count,
        'recent_activity': recent_activity,
        'activity_logs': activity_logs,
        'current_log_type': log_type
    }
    
    return render(request, 'admin/user_detail.html', context)

# Admin User Edit View
@login_required
@user_passes_test(is_admin)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user data
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.username = request.POST.get('username')
        user.is_active = request.POST.get('status') == 'active'
        
        # Update password if provided
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        
        user.save()
        
        # Update or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = request.POST.get('role')
        profile.department = request.POST.get('department')
        profile.phone = request.POST.get('phone')
        profile.save()
        
        messages.success(request, f"User {user.username} updated successfully")
        return redirect('admin_users')
    
    # Get user profile data
    try:
        profile = user.userprofile
    except:
        profile = None
    
    context = {
        'active_page': 'users',
        'user_data': user,
        'profile': profile
    }
    
    return render(request, 'admin/user_edit.html', context)

# Admin User Create View
@login_required
@user_passes_test(is_admin)
def admin_user_create(request):
    if request.method == 'POST':
        # Get user data from form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        department = request.POST.get('department')
        phone = request.POST.get('phone')
        status = request.POST.get('status')
        
        # Validate required fields
        if not (username and password and email):
            messages.error(request, "Username, password, and email are required")
            return redirect('admin_user_create')
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists")
            return redirect('admin_user_create')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' already exists")
            return redirect('admin_user_create')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=status == 'active'
        )
        
        # Set superuser status if role is admin
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        
        # Check if the current user is a manager
        manager_username = None
        if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
            if request.user.profile.role.lower() == 'manager':
                manager_username = request.user.username
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            role=role,
            department=department,
            phone=phone,
            manager_username=manager_username
        )
        
        messages.success(request, f"User {username} created successfully")
        return redirect('admin_users')
    
    context = {
        'active_page': 'users'
    }
    
    return render(request, 'admin/user_create.html', context)

# Download User Template View
@login_required
@user_passes_test(is_admin)
def admin_download_user_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'first_name', 'last_name', 'email', 'username', 'password',
        'role', 'department', 'phone', 'status'
    ])
    
    # Add sample row
    writer.writerow([
        'John', 'Doe', 'john.doe@example.com', 'johndoe', 'securepassword123',
        'sales', 'Sales Department', '+1234567890', 'active'
    ])
    
    return response

# Admin Profile View
@login_required
@user_passes_test(is_admin)
def admin_profile(request):
    user = request.user
    
    if request.method == 'POST':
        # Update user data
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        
        # Update password if provided
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        
        if current_password and new_password:
            # Verify current password
            if user.check_password(current_password):
                user.set_password(new_password)
                messages.success(request, "Password updated successfully")
            else:
                messages.error(request, "Current password is incorrect")
                return redirect('admin_profile')
        
        user.save()
        
        # Update profile
        if hasattr(user, 'userprofile'):
            profile = user.userprofile
            profile.phone = request.POST.get('phone')
            profile.save()
        
        messages.success(request, "Profile updated successfully")
        return redirect('admin_profile')
    
    context = {
        'active_page': 'profile',
        'user_data': user
    }
    
    return render(request, 'admin/profile.html', context)

# Admin Settings View
@login_required
@user_passes_test(is_admin)
def admin_settings(request):
    # Mock settings data
    settings = {
        'company_name': 'LiveFxHub',
        'company_email': 'admin@livefxhub.com',
        'company_phone': '+91 9060088555',
        'company_address': 'Bengaluru, Karnataka',
        'default_currency': 'USD',
        'timezone': 'Asia/Kolkata',
        'date_format': 'MM/DD/YYYY',
        'time_format': '12h',
        'enable_two_factor_auth': False,
        'enable_api_access': True,
        'max_login_attempts': 5,
        'session_timeout': 30,
        'email_notifications': True,
        'backup_frequency': 'daily',
        'backup_retention': 30,
        'logo_path': '/static/img/logo.png'
    }
    
    if request.method == 'POST':
        # Update settings (would connect to actual settings in real implementation)
        for key in settings.keys():
            if key in request.POST:
                settings[key] = request.POST.get(key)
        
        # Handle checkboxes
        settings['enable_two_factor_auth'] = 'enable_two_factor_auth' in request.POST
        settings['enable_api_access'] = 'enable_api_access' in request.POST
        settings['email_notifications'] = 'email_notifications' in request.POST
        
        messages.success(request, "Settings updated successfully")
    
    context = {
        'active_page': 'settings',
        'settings': settings
    }
    
    return render(request, 'admin/settings.html', context)

# Admin Logs View
@login_required
@user_passes_test(is_admin)
def admin_logs(request):
    # Mock logs data
    logs = [
        {
            'id': 1001,
            'user': 'admin',
            'action': 'User Login',
            'details': 'Admin user logged in successfully',
            'ip_address': '192.168.1.1',
            'timestamp': '2025-05-10 15:30:45',
            'level': 'info'
        },
        {
            'id': 1000,
            'user': 'system',
            'action': 'Backup Completed',
            'details': 'Daily database backup completed successfully',
            'ip_address': 'localhost',
            'timestamp': '2025-05-10 03:00:12',
            'level': 'info'
        },
        {
            'id': 999,
            'user': 'john.doe',
            'action': 'Failed Login Attempt',
            'details': 'Multiple failed login attempts detected',
            'ip_address': '203.0.113.1',
            'timestamp': '2025-05-10 12:45:30',
            'level': 'warning'
        },
        {
            'id': 998,
            'user': 'admin',
            'action': 'User Created',
            'details': 'Created new user: mary.johnson',
            'ip_address': '192.168.1.1',
            'timestamp': '2025-05-09 14:20:18',
            'level': 'info'
        },
        {
            'id': 997,
            'user': 'system',
            'action': 'Error',
            'details': 'Failed to send email notification due to SMTP connection error',
            'ip_address': 'localhost',
            'timestamp': '2025-05-09 10:15:42',
            'level': 'error'
        }
    ]
    
    context = {
        'active_page': 'logs',
        'logs': logs
    }
    
    return render(request, 'admin/logs.html', context)

# Admin Task Edit View
@login_required
@user_passes_test(is_admin)
def admin_task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        # Process form submission
        task.subject = request.POST.get('subject')
        task.status = request.POST.get('status')
        task.priority = request.POST.get('priority')
        task.due_date = request.POST.get('due_date')
        task.description = request.POST.get('description')
        
        # Get assigned user
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            task.assigned_to = User.objects.get(id=assigned_to_id)
        
        task.save()
        messages.success(request, 'Task updated successfully')
        return redirect('admin_tasks')
    
    # Get all users for assignment
    users = User.objects.filter(is_active=True)
    
    context = {
        'active_page': 'tasks',
        'task': task,
        'users': users
    }
    
    return render(request, 'admin/task_edit.html', context)

# Admin Leads Management View
@login_required
@user_passes_test(is_admin)
def admin_leads(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get leads based on role
    if is_manager:
        # Get the manager's username and user ID
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Get IDs of users managed by this manager
        managed_user_ids = []
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
        
        # Filter leads for managers to show:
        # 1. Leads assigned directly to the manager
        # 2. Unassigned leads that have this manager's username as manager_username
        # 3. Leads assigned to users managed by this manager
        leads = Lead.objects.filter(
            models_Q(assigned_to_id=manager_id) |
            models_Q(assigned_to__isnull=True, manager_username=manager_username) |
            models_Q(assigned_to_id__in=managed_user_ids)
        ).distinct().order_by('-created_at')
    else:
        # Admin sees all leads
        leads = Lead.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_leads = leads.count()
    new_leads = leads.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    converted_leads = leads.filter(lead_status='converted').count()
    
    # Calculate conversion rate
    conversion_rate = 0
    if total_leads > 0:
        conversion_rate = round((converted_leads / total_leads) * 100, 1)
    
    # Get lead sources data for pie chart
    lead_sources = {
        'website': leads.filter(lead_source='website').count(),
        'phone': leads.filter(lead_source='phone').count(),
        'referral': leads.filter(lead_source='referral').count(),
        'email': leads.filter(lead_source='email').count(),
        'social_media': leads.filter(lead_source='social_media').count(),
        'trade_show': leads.filter(lead_source='trade_show').count(),
        'other': leads.filter(lead_source='other').count(),
        'email_campaign': leads.filter(lead_source='email_campaign').count(),
        'cold_call': leads.filter(lead_source='cold_call').count(),
        'event': leads.filter(lead_source='event').count()
    }
    
    # Ensure there's at least some data for the chart to display
    has_source_data = any(count > 0 for count in lead_sources.values())
    if not has_source_data:
        # Add dummy data if no leads exist
        lead_sources = {
            'website': 1,
            'phone': 0,
            'referral': 0,
            'email': 0,
            'social_media': 0,
            'trade_show': 0,
            'other': 0,
            'email_campaign': 0,
            'cold_call': 0,
            'event': 0
        }
    
    # Convert lead sources data to JSON for the chart
    import json
    lead_sources_labels = ['Website', 'Phone', 'Referral', 'Email', 'Social Media', 'Trade Show', 'Other', 'Email Campaign', 'Cold Call', 'Event']
    lead_sources_data = [
        lead_sources['website'],
        lead_sources['phone'],
        lead_sources['referral'],
        lead_sources['email'],
        lead_sources['social_media'],
        lead_sources['trade_show'],
        lead_sources['other'],
        lead_sources['email_campaign'],
        lead_sources['cold_call'],
        lead_sources['event']
    ]
    # Ensure we have at least one non-zero value to make the chart visible
    if sum(lead_sources_data) == 0:
        lead_sources_data[0] = 1  # Set Website to 1 as a fallback
    
    try:
        lead_sources_json = json.dumps({
            'labels': lead_sources_labels,
            'data': lead_sources_data
        })
    except Exception as e:
        print(f"Error serializing lead sources data: {e}")
        # Provide a fallback JSON string
        lead_sources_json = '{"labels":["Website","Phone","Referral","Email","Social Media","Trade Show","Other","Email Campaign","Cold Call","Event"],"data":[1,0,0,0,0,0,0,0,0,0]}'
    
    # Get lead conversion trend data (monthly for the past year)
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    # Initialize data for all 12 months
    monthly_conversion_data = []
    month_labels = []
    
    # Calculate conversion rate for each month in the past year
    for i in range(12):
        # Calculate the month and year (going backwards from current month)
        month = (current_month - i) % 12
        if month == 0:
            month = 12
        year = current_year if month <= current_month else current_year - 1
        
        # Get month name
        month_name = datetime(year, month, 1).strftime('%b')
        month_labels.insert(0, month_name)
        
        # Get leads created in this month
        month_leads = leads.filter(
            created_at__year=year,
            created_at__month=month
        )
        month_total = month_leads.count()
        
        # Get converted leads in this month
        month_converted = month_leads.filter(lead_status='converted').count()
        
        # Calculate conversion rate for this month
        month_rate = 0
        if month_total > 0:
            month_rate = round((month_converted / month_total) * 100, 1)
        
        monthly_conversion_data.insert(0, month_rate)
    
    # Check if we have any conversion data
    has_conversion_data = any(rate > 0 for rate in monthly_conversion_data)
    
    # If there's no data, add a small value to make the chart visible
    if not has_conversion_data and len(monthly_conversion_data) > 0:
        # Add a small value to the current month to make the chart visible
        monthly_conversion_data[-1] = 0.1
    
    # Convert monthly conversion data to JSON for the chart
    try:
        monthly_conversion_json = json.dumps({
            'labels': month_labels,
            'data': monthly_conversion_data
        })
    except Exception as e:
        print(f"Error serializing monthly conversion data: {e}")
        # Provide a fallback JSON string with 12 months
        monthly_conversion_json = '{"labels":["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],"data":[0,0,0,0,0,0,0,0,0,0,0,0.1]}'
    
    # Get users for assignment dropdown
    if is_manager:
        # Only show users managed by this manager
        manager_username = request.user.username
        users = User.objects.filter(
            models_Q(profile__manager_username=manager_username) |
            models_Q(id=request.user.id)  # Include the manager themselves
        ).filter(is_active=True).distinct().order_by('first_name', 'last_name')
    else:
        # Admin sees all users
        users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
    # Get industries for the dropdown
    industries = Industry.objects.all().order_by('name')
    
    context = {
        'leads': leads,
        'total_leads': total_leads,
        'new_leads': new_leads,
        'converted_leads': converted_leads,
        'conversion_rate': conversion_rate,
        'users': users,
        'industries': industries,
        'lead_sources_json': lead_sources_json,
        'monthly_conversion_json': monthly_conversion_json,
        'active_page': 'leads'
    }
    
    return render(request, 'admin/leads.html', context)

# Admin Contacts Management View
@login_required
@user_passes_test(is_admin)
def admin_contacts(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get contacts based on role
    if is_manager:
        # Get the manager's username
        manager_username = request.user.username
        
        # For managers, only show contacts where manager_username matches the logged-in user's username
        contacts = Contact.objects.filter(manager_username=manager_username).order_by('-created_at')
    elif request.user.is_superuser or is_admin(request.user):
        # Superusers and admins see all contacts
        contacts = Contact.objects.all().order_by('-created_at')
    else:
        # Regular users don't see any contacts (fallback case)
        contacts = Contact.objects.none()
    
    # Calculate statistics
    total_contacts = contacts.count()
    new_contacts = contacts.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    
    # Since Contact model doesn't have a status field, we'll assume all contacts are active
    active_contacts = contacts.count()
    
    # Get contacts with deals
    contacts_with_deals_count = Contact.objects.filter(deals__isnull=False).distinct().count()
    
    # Get all accounts for filtering
    accounts = Account.objects.all().order_by('name')
    
    context = {
        'contacts': contacts,
        'total_contacts': total_contacts,
        'new_contacts': new_contacts,
        'active_contacts': active_contacts,
        'contacts_with_deals': contacts_with_deals_count,
        'accounts': accounts,
        'active_page': 'contacts'
    }
    
    return render(request, 'admin/contacts.html', context)

# Admin Accounts Management View
@login_required
@user_passes_test(is_admin)
def admin_accounts(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get accounts based on role
    if is_manager:
        # Get the manager's username
        manager_username = request.user.username
        
        # For managers, only show accounts where manager_username matches the logged-in user's username
        accounts = Account.objects.filter(manager_username=manager_username).order_by('-created_at')
    elif request.user.is_superuser or is_admin(request.user):
        # Superusers and admins see all accounts
        accounts = Account.objects.all().order_by('-created_at')
    else:
        # Regular users don't see any accounts (fallback case)
        accounts = Account.objects.none()
    
    # Calculate statistics
    total_accounts = accounts.count()
    new_accounts = accounts.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    
    # Get account values
    total_value = accounts.aggregate(Sum('annual_revenue'))['annual_revenue__sum'] or 0
    
    # Get industries for filtering
    industries = Industry.objects.all().order_by('name')
    
    # Count contacts per account
    accounts_with_counts = []
    for account in accounts:
        contact_count = Contact.objects.filter(account=account).count()
        deal_count = Deal.objects.filter(account=account).count()
        accounts_with_counts.append({
            'account': account,
            'contact_count': contact_count,
            'deal_count': deal_count
        })
    
    context = {
        'accounts_with_counts': accounts_with_counts,
        'total_accounts': total_accounts,
        'new_accounts': new_accounts,
        'total_value': total_value,
        'industries': industries,
        'active_page': 'accounts'
    }
    
    return render(request, 'admin/accounts.html', context)

# Admin Deals Management View
@login_required
@user_passes_test(is_admin)
def admin_deals(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get deals based on role
    if is_manager:
        # Get the manager's username and user ID
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Get IDs of users managed by this manager
        managed_user_ids = []
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
        
        # Filter deals by assigned_to is a user managed by this manager OR created_by is this manager
        deals = Deal.objects.filter(
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('-created_at')
    else:
        # Admin sees all deals
        deals = Deal.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_deals = deals.count()
    new_deals = deals.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    won_deals = deals.filter(stage='closed_won').count()
    lost_deals = deals.filter(stage='closed_lost').count()
    
    # Calculate total value and win rate
    total_value = deals.filter(stage='closed_won').aggregate(Sum('amount'))['amount__sum'] or 0
    pipeline_value = deals.exclude(stage__in=['closed_won', 'closed_lost']).aggregate(Sum('amount'))['amount__sum'] or 0
    
    win_rate = 0
    closed_deals = won_deals + lost_deals
    if closed_deals > 0:
        win_rate = round((won_deals / closed_deals) * 100, 1)
    
    # Get all accounts and users for filtering
    accounts = Account.objects.all().order_by('name')
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Get deal stages
    DEAL_STAGES = [
        ('prospecting', 'Prospecting'),
        ('qualification', 'Qualification'),
        ('needs_analysis', 'Needs Analysis'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost')
    ]
    
    context = {
        'deals': deals,
        'total_deals': total_deals,
        'new_deals': new_deals,
        'won_deals': won_deals,
        'lost_deals': lost_deals,
        'total_value': total_value,
        'pipeline_value': pipeline_value,
        'win_rate': win_rate,
        'accounts': accounts,
        'users': users,
        'deal_stages': DEAL_STAGES,
        'active_page': 'deals'
    }
    
    return render(request, 'admin/deals.html', context)

# Admin Tasks Management View
@login_required
@user_passes_test(is_admin)
def admin_tasks(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get tasks based on role
    if is_manager:
        # Get the manager's username and user ID
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Filter tasks by manager_username OR tasks assigned to users managed by this manager
        managed_user_ids = []
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
        
        # Filter tasks by manager_username OR assigned_to is a user managed by this manager OR created_by is this manager
        tasks = Task.objects.filter(
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('-created_at')
    else:
        # Admin sees all tasks
        tasks = Task.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    overdue_tasks = tasks.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress']).count()
    today_tasks = tasks.filter(
        due_date__date=timezone.now().date(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # Calculate completion rate
    completion_rate = 0
    if total_tasks > 0:
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)
    
    # Get all users for assignment/filtering
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Get task priorities and statuses
    TASK_PRIORITIES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    TASK_STATUSES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('deferred', 'Deferred'),
        ('canceled', 'Canceled')
    ]
    
    context = {
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'completion_rate': completion_rate,
        'users': users,
        'task_priorities': TASK_PRIORITIES,
        'task_statuses': TASK_STATUSES,
        'active_page': 'tasks'
    }
    
    return render(request, 'admin/tasks.html', context)

# Admin Products Management View
@login_required
@user_passes_test(is_admin)
def admin_products(request):
    # Get all products
    products = Product.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    
    # Calculate product values
    total_inventory_value = sum([p.price * p.stock for p in products])
    
    # Get product categories (unique values from products)
    categories = Product.objects.values_list('category', flat=True).distinct()
    
    # Get products with sales data
    products_with_sales = []
    for product in products:
        # Count how many deals include this product
        sales_count = DealProduct.objects.filter(product=product).count()
        sales_value = DealProduct.objects.filter(product=product).aggregate(
            total=Sum('price_at_purchase_time')
        )['total'] or 0
        
        products_with_sales.append({
            'product': product,
            'sales_count': sales_count,
            'sales_value': sales_value
        })
    
    context = {
        'products_with_sales': products_with_sales,
        'total_products': total_products,
        'active_products': active_products,
        'total_inventory_value': total_inventory_value,
        'categories': categories,
        'active_page': 'products'
    }
    
    return render(request, 'admin/products.html', context)

# Admin Transactions Management View
@login_required
@user_passes_test(is_admin)
def admin_transactions(request):
    # Get all transactions
    transactions = Transaction.objects.all().order_by('-transaction_date')
    
    # Calculate statistics
    total_transactions = transactions.count()
    total_transaction_value = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Last 30 days transactions
    recent_transactions = transactions.filter(
        transaction_date__gte=timezone.now() - timedelta(days=30)
    )
    recent_transaction_count = recent_transactions.count()
    recent_transaction_value = recent_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Transaction types
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
        ('expense', 'Expense'),
        ('other', 'Other')
    ]
    
    # Get related accounts and deals
    accounts = Account.objects.all().order_by('name')
    deals = Deal.objects.all().order_by('-amount')
    
    context = {
        'transactions': transactions,
        'total_transactions': total_transactions,
        'total_transaction_value': total_transaction_value,
        'recent_transaction_count': recent_transaction_count,
        'recent_transaction_value': recent_transaction_value,
        'transaction_types': TRANSACTION_TYPES,
        'accounts': accounts,
        'deals': deals,
        'active_page': 'transactions'
    }
    
    return render(request, 'admin/transactions.html', context)

# Admin Reports View
@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    # Get time range filter (default to last 30 days)
    time_range = request.GET.get('time_range', '30days')
    
    if time_range == '7days':
        start_date = timezone.now() - timedelta(days=7)
    elif time_range == '30days':
        start_date = timezone.now() - timedelta(days=30)
    elif time_range == '90days':
        start_date = timezone.now() - timedelta(days=90)
    elif time_range == 'year':
        start_date = timezone.now() - timedelta(days=365)
    elif time_range == 'custom':
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = timezone.now() - timedelta(days=30)
            end_date = timezone.now().date()
    else:
        start_date = timezone.now() - timedelta(days=30)
    
    if 'end_date' not in locals():
        end_date = timezone.now().date()
    
    # Get sales data for the period
    deals_in_period = Deal.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    won_deals = deals_in_period.filter(stage='closed_won')
    
    total_deals = deals_in_period.count()
    won_deals_count = won_deals.count()
    win_rate = 0 if total_deals == 0 else round((won_deals_count / total_deals) * 100, 1)
    
    total_revenue = won_deals.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get lead data for the period
    leads_in_period = Lead.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    new_leads = leads_in_period.count()
    converted_leads = leads_in_period.filter(lead_status='converted').count()
    conversion_rate = 0 if new_leads == 0 else round((converted_leads / new_leads) * 100, 1)
    
    # Get user performance data
    user_performance = []
    active_users = User.objects.filter(is_active=True)
    
    for user in active_users:
        user_won_deals = won_deals.filter(assigned_to=user)
        user_revenue = user_won_deals.aggregate(Sum('amount'))['amount__sum'] or 0
        user_performance.append({
            'user': user,
            'deals_count': user_won_deals.count(),
            'revenue': user_revenue
        })
    
    # Sort user performance by revenue descending
    user_performance.sort(key=lambda x: x['revenue'], reverse=True)
    
    # Get product performance data
    product_performance = []
    deal_products = DealProduct.objects.filter(
        deal__in=won_deals
    )
    
    # Group by product and sum quantities and revenue
    product_data = {}
    for dp in deal_products:
        if dp.product_id not in product_data:
            product_data[dp.product_id] = {
                'product': dp.product,
                'quantity': dp.quantity,
                'revenue': dp.price_at_purchase_time * dp.quantity
            }
        else:
            product_data[dp.product_id]['quantity'] += dp.quantity
            product_data[dp.product_id]['revenue'] += dp.price_at_purchase_time * dp.quantity
    
    product_performance = list(product_data.values())
    product_performance.sort(key=lambda x: x['revenue'], reverse=True)
    
    context = {
        'time_range': time_range,
        'start_date': start_date,
        'end_date': end_date,
        'total_deals': total_deals,
        'won_deals_count': won_deals_count,
        'win_rate': win_rate,
        'total_revenue': total_revenue,
        'new_leads': new_leads,
        'converted_leads': converted_leads,
        'conversion_rate': conversion_rate,
        'user_performance': user_performance,
        'product_performance': product_performance,
        'active_page': 'reports'
    }
    
    return render(request, 'admin/reports.html', context)

# Admin Lead Create View
@login_required
@user_passes_test(is_admin)
def admin_lead_create(request):
    if request.method == 'POST':
        try:
            # Extract lead data from POST request
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            company = request.POST.get('company', '')
            job_title = request.POST.get('job_title', '')
            lead_source = request.POST.get('lead_source')
            lead_status = request.POST.get('lead_status')  # Using lead_status which matches the form field
            assigned_to_id = request.POST.get('assigned_to')
            notes = request.POST.get('notes', '')
            
            # Print debug information
            print(f"Creating lead with data: {request.POST}")
            print(f"Lead status: {lead_status}")
            
            # Check if the current user is a manager
            manager_username = None
            if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
                if request.user.profile.role.lower() == 'manager':
                    manager_username = request.user.username
            
            # Get additional fields from the form
            salutation = request.POST.get('salutation', '')
            mobile = request.POST.get('mobile', '')
            website = request.POST.get('website', '')
            address = request.POST.get('address', '')
            industry_id = request.POST.get('industry', '')
            annual_revenue = request.POST.get('annual_revenue', None)
            employees = request.POST.get('employees', None)
            description = request.POST.get('description', '')
            
            # Create the lead with all fields
            lead = Lead(
                salutation=salutation,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                mobile=mobile,
                company=company,
                title=job_title,  # Using title which is the correct field name in the Lead model
                website=website,
                lead_source=lead_source,
                lead_status=lead_status,
                address=address,
                description=description,
                created_by=request.user,
                manager_username=manager_username
            )
            
            # Handle numeric fields
            if annual_revenue and annual_revenue.strip():
                try:
                    lead.annual_revenue = float(annual_revenue)
                except ValueError:
                    pass  # Ignore if not a valid number
                    
            if employees and employees.strip():
                try:
                    lead.employees = int(employees)
                except ValueError:
                    pass  # Ignore if not a valid number
                    
            # Handle industry if selected
            if industry_id and industry_id != '':
                try:
                    industry = Industry.objects.get(id=industry_id)
                    lead.industry = industry
                except Industry.DoesNotExist:
                    pass  # Ignore if industry doesn't exist
            
            # Assign to user if selected
            if assigned_to_id and assigned_to_id != 'Unassigned':
                try:
                    assigned_user = User.objects.get(id=assigned_to_id)
                    lead.assigned_to = assigned_user
                except User.DoesNotExist:
                    print(f"User with ID {assigned_to_id} not found")
            
            # Save the lead
            lead.save()
            
            # Add notes if provided
            if notes:
                Note.objects.create(
                    subject="Initial Lead Notes",
                    content=notes,
                    created_by=request.user,
                    related_lead=lead
                )
            
            messages.success(request, 'Lead created successfully!')
            return redirect('admin_leads')
            
        except Exception as e:
            print(f"Error creating lead: {str(e)}")
            messages.error(request, f'Error creating lead: {str(e)}')
    
    # If not POST or if there was an error, redirect back to leads page
    return redirect('admin_leads')

# Admin Lead Detail View
@login_required
@user_passes_test(is_admin)
def admin_lead_detail(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    context = {
        'lead': lead,
        'active_page': 'leads'
    }
    return render(request, 'admin/lead_detail.html', context)

# Admin Lead Convert View
@login_required
@user_passes_test(is_admin)
def admin_lead_convert(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    # Check if lead is already converted
    if lead.lead_status == 'converted':
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'Lead "{lead.first_name} {lead.last_name}" is already converted.'
            })
        else:
            messages.warning(request, f'Lead "{lead.first_name} {lead.last_name}" is already converted.')
            return redirect('admin_leads')
    
    try:
        # Create a new account from the lead
        account = Account()
        account.name = lead.company if lead.company else f"{lead.first_name} {lead.last_name}'s Company"
        account.website = lead.website
        account.phone = lead.phone
        account.email = lead.email  # Store email from lead
        account.industry = lead.industry
        account.annual_revenue = lead.annual_revenue
        account.employees = lead.employees
        account.description = lead.description
        account.billing_address = lead.address
        account.assigned_to = lead.assigned_to
        account.manager_username = lead.manager_username  # Store manager_username from lead
        account.created_by = request.user
        account.converted_by = request.user  # Set the converted_by field to the logged-in user
        account.save()
        
        # Create a contact from the lead
        contact = Contact()
        contact.salutation = lead.salutation
        contact.first_name = lead.first_name
        contact.last_name = lead.last_name
        contact.email = lead.email
        contact.phone = lead.phone
        contact.mobile = lead.mobile
        contact.job_title = lead.title
        contact.account = account
        contact.mailing_address = lead.address
        contact.description = lead.description
        contact.assigned_to = lead.assigned_to
        contact.manager_username = lead.manager_username  # Store manager_username from lead
        contact.created_by = request.user
        contact.save()
        
        # Update the lead as converted
        lead.lead_status = 'converted'
        lead.converted_account = account
        lead.converted_contact = contact
        lead.save()
        
        # Create activity log
        UserActivityLog.objects.create(
            user=request.user,
            action_type='other',  # Using 'other' from ACTION_TYPES choices
            action_detail=f"Converted lead '{lead.first_name} {lead.last_name}' to account '{account.name}'",
            model_affected='Lead',
            object_id=lead.id
        )
        
        # Get updated statistics for AJAX response
        if is_ajax:
            # Get all leads
            leads = Lead.objects.all()
            
            # Calculate statistics
            total_leads = leads.count()
            new_leads = leads.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
            converted_leads = leads.filter(lead_status='converted').count()
            
            # Calculate conversion rate
            conversion_rate = 0
            if total_leads > 0:
                conversion_rate = round((converted_leads / total_leads) * 100, 1)
            
            return JsonResponse({
                'success': True,
                'message': f'Lead "{lead.first_name} {lead.last_name}" successfully converted to account "{account.name}"!',
                'stats': {
                    'total_leads': total_leads,
                    'new_leads': new_leads,
                    'converted_leads': converted_leads,
                    'conversion_rate': conversion_rate
                }
            })
        else:
            messages.success(request, f'Lead "{lead.first_name} {lead.last_name}" successfully converted to account "{account.name}"!')
            return redirect('admin_leads')
            
    except Exception as e:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'Error converting lead: {str(e)}'
            })
        else:
            messages.error(request, f'Error converting lead: {str(e)}')
            return redirect('admin_leads')

# Admin Lead Edit View
@login_required
@user_passes_test(is_admin)
def admin_lead_edit(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Get industries for the dropdown
    industries = Industry.objects.all().order_by('name')
    
    if request.method == 'POST':
        try:
            # Update lead data from POST request
            lead.salutation = request.POST.get('salutation', '')
            lead.first_name = request.POST.get('first_name')
            lead.last_name = request.POST.get('last_name')
            lead.email = request.POST.get('email')
            lead.phone = request.POST.get('phone', '')
            lead.mobile = request.POST.get('mobile', '')
            lead.company = request.POST.get('company', '')
            lead.title = request.POST.get('job_title', '')
            lead.website = request.POST.get('website', '')
            lead.address = request.POST.get('address', '')
            lead.lead_source = request.POST.get('lead_source')
            lead.lead_status = request.POST.get('lead_status')
            lead.description = request.POST.get('description', '')  # Updated to use correct field name
            
            # Handle numeric fields
            annual_revenue = request.POST.get('annual_revenue')
            if annual_revenue and annual_revenue.strip():
                try:
                    lead.annual_revenue = float(annual_revenue)
                except ValueError:
                    pass  # Ignore if not a valid number
                    
            employees = request.POST.get('employees')
            if employees and employees.strip():
                try:
                    lead.employees = int(employees)
                except ValueError:
                    pass  # Ignore if not a valid number
                    
            # Handle industry if selected
            industry_id = request.POST.get('industry')
            if industry_id and industry_id != '':
                try:
                    industry = Industry.objects.get(id=industry_id)
                    lead.industry = industry
                except Industry.DoesNotExist:
                    lead.industry = None
            else:
                lead.industry = None
            
            # Update assigned user if provided
            assigned_to_id = request.POST.get('assigned_to')
            if assigned_to_id:
                try:
                    assigned_user = User.objects.get(id=assigned_to_id)
                    lead.assigned_to = assigned_user
                except User.DoesNotExist:
                    pass
            else:
                lead.assigned_to = None
            
            lead.save()
            
            messages.success(request, 'Lead updated successfully!')
            return redirect('admin_leads')
            
        except Exception as e:
            messages.error(request, f'Error updating lead: {str(e)}')
    
    # Get all users for assignment dropdown
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'lead': lead,
        'users': users,
        'industries': industries,
        'active_page': 'leads'
    }
    
    return render(request, 'admin/lead_edit.html', context)

# Admin Lead Import View
@login_required


# Admin Accounts View
@login_required
@user_passes_test(is_admin)
def admin_accounts(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get accounts based on role
    if is_manager:
        # Get the manager's username
        manager_username = request.user.username
        
        # For managers, only show accounts where manager_username matches the logged-in user's username
        accounts = Account.objects.filter(manager_username=manager_username).order_by('-created_at')
    elif request.user.is_superuser or is_admin(request.user):
        # Superusers and admins see all accounts
        accounts = Account.objects.all().order_by('-created_at')
    else:
        # Regular users don't see any accounts (fallback case)
        accounts = Account.objects.none()
    
    # Get all industries for filtering
    industries = Industry.objects.all().order_by('name')
    
    # Calculate account statistics
    total_accounts = accounts.count()
    new_accounts = accounts.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    
    # Calculate total value and average deal size
    total_value = Deal.objects.filter(stage='closed_won').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate average deal size
    deals = Deal.objects.filter(stage='closed_won')
    deal_count = deals.count()
    avg_deal_size = total_value / deal_count if deal_count > 0 else 0
    
    # Enhance accounts with related counts
    accounts_with_counts = []
    for account in accounts:
        contacts_count = Contact.objects.filter(account=account).count()
        deals_count = Deal.objects.filter(account=account).count()
        accounts_with_counts.append({
            'account': account,
            'contacts_count': contacts_count,
            'deals_count': deals_count
        })
    
    context = {
        'accounts_with_counts': accounts_with_counts,
        'total_accounts': total_accounts,
        'new_accounts': new_accounts,
        'total_value': total_value,
        'avg_deal_size': avg_deal_size,
        'industries': industries,
        'active_page': 'accounts'
    }
    
    return render(request, 'admin/accounts.html', context)

# Admin Account Detail View
@login_required
@user_passes_test(is_admin)
def admin_account_detail(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    
    # Get related contacts
    contacts = Contact.objects.filter(account=account).order_by('first_name', 'last_name')
    
    # Get related deals
    deals = Deal.objects.filter(account=account).order_by('-created_at')
    
    context = {
        'account': account,
        'contacts': contacts,
        'deals': deals,
        'active_page': 'accounts'
    }
    
    return render(request, 'admin/account_detail.html', context)

# Admin Account Create View
@login_required
@user_passes_test(is_admin)
def admin_account_create(request):
    # Get industries for dropdown
    industries = Industry.objects.all().order_by('name')
    
    # Get users for assignment dropdown
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        try:
            # Create new account from POST data
            account = Account()
            
            return redirect('admin_account_detail', account_id=account.id)
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    context = {
        'industries': industries,
        'users': users,
        'active_page': 'accounts'
    }
    
    return render(request, 'admin/account_edit.html', context)

# Admin Account Edit View
@login_required
@user_passes_test(is_admin)
def admin_account_edit(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    
    # Get industries for dropdown
    industries = Industry.objects.all().order_by('name')
    
    # Get users for assignment dropdown
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        try:
            # Required fields
            account.name = request.POST.get('name')
            
            # Optional fields - set to None if empty
            # Account type
            account_type = request.POST.get('account_type', '')
            account.account_type = account_type if account_type.strip() else None
            
            # Contact information
            phone = request.POST.get('phone', '')
            account.phone = phone if phone.strip() else None
            
            email = request.POST.get('email', '')
            account.email = email if email.strip() else None
            
            website = request.POST.get('website', '')
            account.website = website if website.strip() else None
            
            # Address fields
            billing_address = request.POST.get('billing_address', '')
            account.billing_address = billing_address if billing_address.strip() else None
            
            shipping_address = request.POST.get('shipping_address', '')
            account.shipping_address = shipping_address if shipping_address.strip() else None
            
            # Description
            description = request.POST.get('description', '')
            account.description = description if description.strip() else None
            
            # Handle numeric fields
            # Employees
            employees = request.POST.get('employees', '')
            if employees and employees.strip():
                try:
                    account.employees = int(employees)
                except ValueError:
                    account.employees = None
            else:
                account.employees = None
            
            # Annual revenue
            annual_revenue = request.POST.get('annual_revenue', '')
            if annual_revenue and annual_revenue.strip():
                try:
                    # Convert to Decimal to avoid precision issues
                    from decimal import Decimal
                    account.annual_revenue = Decimal(annual_revenue)
                except (ValueError, decimal.InvalidOperation):
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
            
            # Handle assigned user if selected
            assigned_to_id = request.POST.get('assigned_to', '')
            if assigned_to_id and assigned_to_id.strip():
                try:
                    assigned_user = User.objects.get(id=assigned_to_id)
                    account.assigned_to = assigned_user
                except (User.DoesNotExist, ValueError):
                    account.assigned_to = None
            else:
                account.assigned_to = None
            
            # Save the account
            account.save()
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='update',
                action_detail=f"Updated account '{account.name}'",
                model_affected='Account',
                object_id=account.id
            )
            
            messages.success(request, f'Account "{account.name}" updated successfully!')
            return redirect('admin_account_detail', account_id=account.id)
            
        except Exception as e:
            messages.error(request, f'Error updating account: {str(e)}')
    
    context = {
        'account': account,
        'industries': industries,
        'users': users,
        'active_page': 'accounts'
    }
    
    return render(request, 'admin/account_edit.html', context)

# Admin Account Delete View
@login_required
@user_passes_test(is_admin)
def admin_account_delete(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    try:
        account_name = account.name
        account.delete()
        
        # Create activity log
        UserActivityLog.objects.create(
            user=request.user,
            action_type='delete',
            action_detail=f"Deleted account '{account_name}'",
            model_affected='Account',
            object_id=account_id
        )
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Account "{account_name}" deleted successfully!'
            })
        else:
            messages.success(request, f'Account "{account_name}" deleted successfully!')
            return redirect('admin_accounts')
            
    except Exception as e:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'Error deleting account: {str(e)}'
            })
        else:
            messages.error(request, f'Error deleting account: {str(e)}')
            return redirect('admin_accounts')

# Admin Account Import View
@login_required
@user_passes_test(is_admin)
def admin_account_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        try:
            csv_file = request.FILES['import_file']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file.')
                return redirect('admin_accounts')
            
            # Decode the file
            file_data = csv_file.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(file_data)
            
            # Track import statistics
            total_rows = 0
            imported_count = 0
            error_count = 0
            error_messages = []
            
            # Process each row
            for row in reader:
                total_rows += 1
                try:
                    # Create a new account
                    account = Account()
                    account.name = row.get('Name', '').strip()
                    
                    # Skip if no name provided
                    if not account.name:
                        error_count += 1
                        error_messages.append(f"Row {total_rows}: Account name is required.")
                        continue
                    
                    # Set other fields
                    account.account_type = row.get('Type', '').strip().lower()
                    account.phone = row.get('Phone', '').strip()
                    account.email = row.get('Email', '').strip()
                    account.website = row.get('Website', '').strip()
                    account.billing_address = row.get('Billing Address', '').strip()
                    account.shipping_address = row.get('Shipping Address', '').strip()
                    account.description = row.get('Description', '').strip()
                    account.manager_username = request.user.username
                    
                    # Handle numeric fields
                    employees = row.get('Employees', '').strip()
                    if employees:
                        try:
                            account.employees = int(employees)
                        except ValueError:
                            pass
                    
                    annual_revenue = row.get('Annual Revenue', '').strip()
                    if annual_revenue:
                        try:
                            # Remove currency symbols and commas
                            annual_revenue = annual_revenue.replace('$', '').replace(',', '')
                            # Convert to Decimal to avoid precision issues
                            from decimal import Decimal
                            account.annual_revenue = Decimal(annual_revenue)
                        except (ValueError, decimal.InvalidOperation):
                            # If conversion fails, set to None
                            account.annual_revenue = None
                    
                    # Handle industry if provided
                    industry_name = row.get('Industry', '').strip()
                    if industry_name:
                        # Try to find existing industry or create new one
                        industry, created = Industry.objects.get_or_create(name=industry_name)
                        account.industry = industry
                    
                    # Set created_by to current user
                    account.created_by = request.user
                    
                    # Save the account
                    account.save()
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Row {total_rows}: {str(e)}")
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='import',
                action_detail=f"Imported {imported_count} accounts from CSV",
                model_affected='Account',
                object_id=None
            )
            
            # Show success message with statistics
            if imported_count > 0:
                messages.success(request, f'Successfully imported {imported_count} accounts. {error_count} errors occurred.')
            else:
                messages.warning(request, f'No accounts were imported. {error_count} errors occurred.')
            
            # Show error details if any
            if error_messages:
                for msg in error_messages[:5]:  # Show first 5 errors
                    messages.error(request, msg)
                if len(error_messages) > 5:
                    messages.error(request, f'... and {len(error_messages) - 5} more errors.')
            
        except Exception as e:
            messages.error(request, f'Error importing accounts: {str(e)}')
    
    return redirect('admin_accounts')

# Admin Download Account Template View
@login_required
@user_passes_test(is_admin)
def admin_download_account_template(request):
    # Create a response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="account_import_template.csv"'
    
    # Create CSV writer and write header row
    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Type', 'Phone', 'Email', 'Website', 'Industry', 
        'Employees', 'Annual Revenue', 'Billing Address', 'Shipping Address', 'Description'
    ])
    
    # Write a sample row
    writer.writerow([
        'Acme Corporation', 'customer', '555-123-4567', 'info@acme.com', 'https://www.acme.com', 'Technology',
        '100', '1000000', '123 Main St, City, State, ZIP', '123 Main St, City, State, ZIP', 'Sample account description'
    ])
    
    return response

# Admin Lead Import View
@login_required
@user_passes_test(is_admin)
def admin_lead_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_leads')
        
        # Process CSV file
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    # Create lead from CSV row
                    lead = Lead(
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        email=row.get('email', ''),
                        phone=row.get('phone', ''),
                        company=row.get('company', ''),
                        title=row.get('job_title', ''),
                        lead_source=row.get('lead_source', 'other'),
                        lead_status=row.get('lead_status', 'new'),
                        created_by=request.user
                    )
                    
                    # Set assigned_to if username provided
                    if row.get('assigned_to'):
                        try:
                            user = User.objects.get(username=row.get('assigned_to'))
                            lead.assigned_to = user
                        except User.DoesNotExist:
                            pass
                    
                    lead.save()
                    success_count += 1
                    
                except Exception:
                    error_count += 1
            
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} leads')
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} leads due to errors')
                
        except Exception as e:
            messages.error(request, f'Error importing leads: {str(e)}')
    
    return redirect('admin_leads')

# Admin Download Lead Template View
@login_required
@user_passes_test(is_admin)
def admin_download_lead_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lead_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['first_name', 'last_name', 'email', 'phone', 'company', 'job_title', 
                     'lead_source', 'lead_status', 'assigned_to', 'notes'])
    
    return response

# Admin Contact Create View
@login_required
@user_passes_test(is_admin)
def admin_contact_create(request):
    if request.method == 'POST':
        try:
            # Extract contact data from POST request
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            account_id = request.POST.get('account')
            job_title = request.POST.get('job_title', '')
            notes = request.POST.get('notes', '')
            
            # Create the contact
            contact = Contact(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                job_title=job_title,
                created_by=request.user
            )
            
            # Set account if selected
            if account_id:
                try:
                    account = Account.objects.get(id=account_id)
                    contact.account = account
                except Account.DoesNotExist:
                    pass
            
            contact.save()
            
            # Save notes if provided
            if notes:
                Note.objects.create(
                    contact=contact,
                    content=notes,
                    created_by=request.user
                )
            
            messages.success(request, 'Contact created successfully!')
            return redirect('admin_contacts')
            
        except Exception as e:
            messages.error(request, f'Error creating contact: {str(e)}')
    
    # If not POST or if there was an error, redirect back to contacts page
    return redirect('admin_contacts')

# Admin Contact Detail View
@login_required
@user_passes_test(is_admin)
def admin_contact_detail(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    
    # Get notes related to this contact
    notes = Note.objects.filter(related_contact=contact).order_by('-created_at')
    
    context = {
        'contact': contact,
        'notes': notes,
        'active_page': 'contacts'
    }
    return render(request, 'admin/contact_detail.html', context)

# Admin Contact Edit View
@login_required
@user_passes_test(is_admin)
def admin_contact_edit(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        try:
            # Required fields
            contact.first_name = request.POST.get('first_name')
            contact.last_name = request.POST.get('last_name')
            contact.email = request.POST.get('email')
            
            # Validate required fields
            if not contact.first_name or not contact.last_name or not contact.email:
                messages.error(request, 'First name, last name, and email are required fields.')
                raise ValueError("Required fields missing")
            
            # Optional fields
            phone = request.POST.get('phone', '')
            contact.phone = phone if phone.strip() else None
            
            job_title = request.POST.get('job_title', '')
            contact.job_title = job_title if job_title.strip() else None
            
            address = request.POST.get('address', '')
            if hasattr(contact, 'address'):
                contact.address = address if address.strip() else None
            
            # Handle lead source if available
            lead_source = request.POST.get('lead_source', '')
            if hasattr(contact, 'lead_source') and lead_source.strip():
                contact.lead_source = lead_source
            
            # Handle status (active/inactive)
            status = request.POST.get('status')
            if hasattr(contact, 'is_active'):
                contact.is_active = (status == 'active')
            
            # Update account if provided
            account_id = request.POST.get('account')
            if account_id and account_id.strip():
                try:
                    account = Account.objects.get(id=account_id)
                    contact.account = account
                except (Account.DoesNotExist, ValueError):
                    contact.account = None
            else:
                contact.account = None
            
            # Update assigned user if provided
            assigned_to_id = request.POST.get('assigned_to')
            if assigned_to_id and assigned_to_id.strip():
                try:
                    assigned_user = User.objects.get(id=assigned_to_id)
                    contact.assigned_to = assigned_user
                except (User.DoesNotExist, ValueError):
                    contact.assigned_to = None
            else:
                contact.assigned_to = None
            
            # Set manager username if not already set
            if hasattr(contact, 'manager_username') and not contact.manager_username:
                contact.manager_username = request.user.username
            
            contact.save()
            
            # Add note if provided
            notes = request.POST.get('notes', '')
            if notes and notes.strip():
                Note.objects.create(
                    related_contact=contact,
                    content=notes,
                    created_by=request.user
                )
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='update',
                action_detail=f"Updated contact '{contact.first_name} {contact.last_name}'",
                model_affected='Contact',
                object_id=contact.id
            )
            
            messages.success(request, f'Contact "{contact.first_name} {contact.last_name}" updated successfully!')
            return redirect('admin_contact_detail', contact_id=contact.id)
            
        except ValueError as ve:
            # Already displayed error message for validation errors
            pass
        except Exception as e:
            messages.error(request, f'Error updating contact: {str(e)}')
    
    # Get all accounts for dropdown
    accounts = Account.objects.all().order_by('name')
    
    # Get users for assignment dropdown
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'contact': contact,
        'accounts': accounts,
        'users': users,
        'active_page': 'contacts'
    }
    
    return render(request, 'admin/contact_edit.html', context)

# Admin Contact Add Note View
@login_required
@user_passes_test(is_admin)
def admin_contact_add_note(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            note = Note.objects.create(
                related_contact=contact,
                content=content,
                created_by=request.user
            )
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='create',
                action_detail=f"Added note to contact '{contact.first_name} {contact.last_name}'",
                model_affected='Note',
                object_id=note.id
            )
            
            messages.success(request, 'Note added successfully!')
        else:
            messages.error(request, 'Note content cannot be empty.')
    
    return redirect('admin_contact_detail', contact_id=contact.id)

# Admin Contact Delete Note View
@login_required
@user_passes_test(is_admin)
def admin_contact_delete_note(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    note_id = request.GET.get('note_id')
    
    if note_id:
        try:
            note = Note.objects.get(id=note_id, related_contact=contact)
            note_content = note.content[:30] + '...' if len(note.content) > 30 else note.content
            note.delete()
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='delete',
                action_detail=f"Deleted note from contact '{contact.first_name} {contact.last_name}'",
                model_affected='Note',
                object_id=note_id
            )
            
            messages.success(request, 'Note deleted successfully!')
        except Note.DoesNotExist:
            messages.error(request, 'Note not found or does not belong to this contact.')
    else:
        messages.error(request, 'Note ID not provided.')
    
    return redirect('admin_contact_detail', contact_id=contact.id)

# Admin Contact Import View
@login_required
@user_passes_test(is_admin)
def admin_contact_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_contacts')
        
        # Process CSV file
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    # Create contact from CSV row
                    contact = Contact(
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        email=row.get('email', ''),
                        phone=row.get('phone', ''),
                        job_title=row.get('job_title', ''),
                        created_by=request.user
                    )
                    
                    # Set account if account_id provided
                    if row.get('account_id'):
                        try:
                            account = Account.objects.get(id=row.get('account_id'))
                            contact.account = account
                        except Account.DoesNotExist:
                            pass
                    
                    contact.save()
                    success_count += 1
                    
                except Exception:
                    error_count += 1
            
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} contacts')
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} contacts due to errors')
                
        except Exception as e:
            messages.error(request, f'Error importing contacts: {str(e)}')
    
    return redirect('admin_contacts')

# Admin Download Contact Template View
@login_required
@user_passes_test(is_admin)
def admin_download_contact_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contact_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['first_name', 'last_name', 'email', 'phone', 'job_title', 'account_id'])
    
    return response

# Admin Account Create View
@login_required
@user_passes_test(is_admin)
def admin_account_create(request):
    # Get industries for dropdown
    industries = Industry.objects.all().order_by('name')
    
    # Get users for assignment dropdown
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        try:
            # Create new account from POST data
            account = Account()
            
            # Required field
            account.name = request.POST.get('name')
            
            # Validate required data
            if not account.name:
                messages.error(request, 'Account name is required')
                return render(request, 'admin/account_edit.html', {
                    'active_page': 'accounts',
                    'industries': industries,
                    'users': users,
                    'is_new': True
                })
            
            # Optional fields - set to None if empty
            # Account type
            account_type = request.POST.get('account_type', '')
            account.account_type = account_type if account_type.strip() else None
            
            # Contact information
            phone = request.POST.get('phone', '')
            account.phone = phone if phone.strip() else None
            
            email = request.POST.get('email', '')
            account.email = email if email.strip() else None
            
            website = request.POST.get('website', '')
            account.website = website if website.strip() else None
            
            # Address fields
            billing_address = request.POST.get('billing_address', '')
            account.billing_address = billing_address if billing_address.strip() else None
            
            shipping_address = request.POST.get('shipping_address', '')
            account.shipping_address = shipping_address if shipping_address.strip() else None
            
            # Description
            description = request.POST.get('description', '')
            account.description = description if description.strip() else None
            
            # Set manager username
            account.manager_username = request.user.username
            
            # Handle numeric fields
            # Employees
            employees = request.POST.get('employees', '')
            if employees and employees.strip():
                try:
                    account.employees = int(employees)
                except ValueError:
                    account.employees = None
            else:
                account.employees = None
            
            # Annual revenue
            annual_revenue = request.POST.get('annual_revenue', '')
            if annual_revenue and annual_revenue.strip():
                try:
                    # Convert to Decimal to avoid precision issues
                    from decimal import Decimal
                    account.annual_revenue = Decimal(annual_revenue)
                except (ValueError, decimal.InvalidOperation):
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
            
            # Handle assigned user if selected
            assigned_to_id = request.POST.get('assigned_to', '')
            if assigned_to_id and assigned_to_id.strip():
                try:
                    assigned_user = User.objects.get(id=assigned_to_id)
                    account.assigned_to = assigned_user
                except (User.DoesNotExist, ValueError):
                    account.assigned_to = None
            else:
                account.assigned_to = None
            
            # Set created_by to current user
            account.created_by = request.user
            
            # Save the account
            account.save()
            
            # Create activity log
            UserActivityLog.objects.create(
                user=request.user,
                action_type='create',
                action_detail=f"Created new account '{account.name}'",
                model_affected='Account',
                object_id=account.id
            )
            
            messages.success(request, f'Account "{account.name}" created successfully!')
            return redirect('admin_account_detail', account_id=account.id)
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    # Get all industries for dropdown
    industries = Industry.objects.all().order_by('name')
    
    context = {
        'active_page': 'accounts',
        'industries': industries
    }
    
    return render(request, 'admin/account_create.html', context)

# Admin Account Detail View
@login_required
@user_passes_test(is_admin)
def admin_account_detail(request, account_id):
    # Get account or 404
    account = get_object_or_404(Account, id=account_id)
    
    # Get account's contacts
    contacts = Contact.objects.filter(account=account).order_by('first_name', 'last_name')
    
    # Get account's deals
    deals = Deal.objects.filter(account=account).order_by('-created_at')
    
    context = {
        'active_page': 'accounts',
        'account': account,
        'contacts': contacts,
        'deals': deals
    }
    
    return render(request, 'admin/account_detail.html', context)

# Admin Account Edit View
@login_required
@user_passes_test(is_admin)
def admin_account_edit(request, account_id):
    # Get account or 404
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        try:
            # Required fields
            account.name = request.POST.get('name')
            
            # Validate required data
            if not account.name:
                messages.error(request, 'Account name is required')
                return redirect('admin_account_edit', account_id=account.id)
            
            # Optional fields - set to None if empty
            # Website
            website = request.POST.get('website', '')
            account.website = website if website.strip() else None
            
            # Phone
            phone = request.POST.get('phone', '')
            account.phone = phone if phone.strip() else None
            
            # Description
            description = request.POST.get('description', '')
            account.description = description if description.strip() else None
            
            # Address - handle both billing and shipping address fields
            address = request.POST.get('address', '')
            if hasattr(account, 'address'):
                account.address = address if address.strip() else None
            else:
                # If using separate billing/shipping addresses
                billing_address = request.POST.get('billing_address', '')
                if hasattr(account, 'billing_address'):
                    account.billing_address = billing_address if billing_address.strip() else None
                
                shipping_address = request.POST.get('shipping_address', '')
                if hasattr(account, 'shipping_address'):
                    account.shipping_address = shipping_address if shipping_address.strip() else None
            
            # Handle numeric fields
            # Employees
            employees = request.POST.get('employees', '')
            if employees and employees.strip():
                try:
                    account.employees = int(employees)
                except ValueError:
                    account.employees = None
            else:
                account.employees = None
            
            # Annual revenue
            annual_revenue = request.POST.get('annual_revenue', '')
            if annual_revenue and annual_revenue.strip():
                try:
                    # Clean the input - remove any non-numeric characters except decimal point
                    cleaned_revenue = annual_revenue.strip().replace(',', '')
                    if cleaned_revenue:
                        account.annual_revenue = decimal.Decimal(cleaned_revenue)
                    else:
                        account.annual_revenue = None
                except (ValueError, decimal.InvalidOperation):
                    account.annual_revenue = None
            else:
                account.annual_revenue = None
            
            # Update industry if provided
            industry_id = request.POST.get('industry', '')
            if industry_id and industry_id.strip():
                try:
                    account.industry = Industry.objects.get(id=industry_id)
                except (Industry.DoesNotExist, ValueError):
                    account.industry = None
            else:
                account.industry = None
            
            account.save()
            messages.success(request, 'Account updated successfully')
            return redirect('admin_accounts')
        except Exception as e:
            messages.error(request, f'Error updating account: {str(e)}')
    
    # Get all industries for dropdown
    industries = Industry.objects.all().order_by('name')
    
    context = {
        'active_page': 'accounts',
        'account': account,
        'industries': industries
    }
    
    return render(request, 'admin/account_edit.html', context)

# Admin Account Import View
@login_required
@user_passes_test(is_admin)
def admin_account_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_accounts')
            
        try:
            # Check if file is too large
            if csv_file.size > 1048576:  # 1 MB
                messages.error(request, 'The uploaded file is too large')
                return redirect('admin_accounts')
                
            # Process CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            
            # Skip header row if specified
            header_row = request.POST.get('header_row') == 'on'
            if header_row:
                next(reader)  # Skip the header row
                
            # Process rows
            accounts_created = 0
            for row in reader:
                if len(row) < 1:  # Must have at least name
                    continue
                    
                name = row[0].strip()
                if not name:  # Skip if name is empty
                    continue
                    
                # Get industry if provided (index 1)
                industry = None
                if len(row) > 1 and row[1].strip():
                    try:
                        industry_id = int(row[1].strip())
                        industry = Industry.objects.get(id=industry_id)
                    except (ValueError, Industry.DoesNotExist):
                        pass
                        
                # Create account with available data
                account = Account(
                    name=name,
                    industry=industry,
                    website=row[2].strip() if len(row) > 2 else '',
                    phone=row[3].strip() if len(row) > 3 else '',
                    annual_revenue=float(row[4]) if len(row) > 4 and row[4].strip() else 0,
                    employees=int(row[5]) if len(row) > 5 and row[5].strip() else 0,
                    address=row[6].strip() if len(row) > 6 else '',
                    description=row[7].strip() if len(row) > 7 else ''
                )
                account.save()
                accounts_created += 1
                
            messages.success(request, f'Successfully imported {accounts_created} accounts')
        except Exception as e:
            messages.error(request, f'Error importing accounts: {str(e)}')
            
        return redirect('admin_accounts')
    
    return redirect('admin_accounts')

# Admin Download Account Template View
@login_required
@user_passes_test(is_admin)
def admin_download_account_template(request):
    # Create a response object with appropriate headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="account_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'industry_id', 'website', 'phone', 'annual_revenue', 'employees', 'address', 'description'])
    
    return response

# Admin Deal Create View
@login_required
@user_passes_test(is_admin)
def admin_deal_create(request):
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        stage = request.POST.get('stage')
        amount = request.POST.get('amount', 0)
        close_date = request.POST.get('close_date')
        probability = request.POST.get('probability', 0)
        account_id = request.POST.get('account')
        contact_id = request.POST.get('contact')
        description = request.POST.get('description')
        
        # Validate required data
        if not name or not stage:
            messages.error(request, 'Deal name and stage are required')
            return redirect('admin_deals')
            
        # Create deal
        deal = Deal(
            name=name,
            stage=stage,
            amount=amount,
            close_date=close_date,
            probability=probability,
            description=description
        )
        
        # Set account if provided
        if account_id:
            try:
                deal.account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                pass
                
        # Set contact if provided
        if contact_id:
            try:
                deal.contact = Contact.objects.get(id=contact_id)
            except Contact.DoesNotExist:
                pass
                
        deal.save()
        messages.success(request, 'Deal created successfully')
        return redirect('admin_deals')
    
    # Get all accounts and contacts for dropdowns
    accounts = Account.objects.all().order_by('name')
    contacts = Contact.objects.all().order_by('first_name', 'last_name')
    
    # Pre-select account if provided in query params
    selected_account_id = request.GET.get('account')
    selected_account = None
    if selected_account_id:
        try:
            selected_account = Account.objects.get(id=selected_account_id)
            # If an account is pre-selected, filter contacts by that account
            contacts = contacts.filter(account=selected_account)
        except Account.DoesNotExist:
            pass
    
    context = {
        'active_page': 'deals',
        'accounts': accounts,
        'contacts': contacts,
        'selected_account': selected_account,
        'deal_stages': DEAL_STAGE_CHOICES
    }
    
    return render(request, 'admin/deal_create.html', context)

# Admin Deal Detail View
@login_required
@user_passes_test(is_admin)
def admin_deal_detail(request, deal_id):
    # Get deal or 404
    deal = get_object_or_404(Deal, id=deal_id)
    
    # Get deal's tasks
    tasks = Task.objects.filter(deal=deal).order_by('-created_at')
    
    # Get deal's notes
    notes = Note.objects.filter(deal=deal).order_by('-created_at')
    
    context = {
        'active_page': 'deals',
        'deal': deal,
        'tasks': tasks,
        'notes': notes
    }
    
    return render(request, 'admin/deal_detail.html', context)

# Admin Deal Edit View
@login_required
@user_passes_test(is_admin)
def admin_deal_edit(request, deal_id):
    # Get deal or 404
    deal = get_object_or_404(Deal, id=deal_id)
    
    if request.method == 'POST':
        # Get form data
        deal.name = request.POST.get('name')
        deal.stage = request.POST.get('stage')
        deal.amount = request.POST.get('amount', 0)
        deal.close_date = request.POST.get('close_date')
        deal.probability = request.POST.get('probability', 0)
        account_id = request.POST.get('account')
        contact_id = request.POST.get('contact')
        deal.description = request.POST.get('description')
        
        # Validate required data
        if not deal.name or not deal.stage:
            messages.error(request, 'Deal name and stage are required')
            return redirect('admin_deal_edit', deal_id=deal.id)
            
        # Update account if provided
        if account_id:
            try:
                deal.account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                pass
        else:
            deal.account = None
            
        # Update contact if provided
        if contact_id:
            try:
                deal.contact = Contact.objects.get(id=contact_id)
            except Contact.DoesNotExist:
                pass
        else:
            deal.contact = None
            
        deal.save()
        messages.success(request, 'Deal updated successfully')
        return redirect('admin_deals')
    
    # Get all accounts and contacts for dropdowns
    accounts = Account.objects.all().order_by('name')
    contacts = Contact.objects.all().order_by('first_name', 'last_name')
    
    # If deal has an account, filter contacts by that account
    if deal.account:
        account_contacts = contacts.filter(account=deal.account)
    else:
        account_contacts = contacts
    
    context = {
        'active_page': 'deals',
        'deal': deal,
        'accounts': accounts,
        'contacts': contacts,
        'account_contacts': account_contacts,
        'deal_stages': DEAL_STAGE_CHOICES
    }
    
    return render(request, 'admin/deal_edit.html', context)

@login_required
@user_passes_test(is_admin)
def admin_deal_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_deals')
        
        try:
            # Check if file is too large
            if csv_file.size > 1048576:  # 1 MB
                messages.error(request, 'The uploaded file is too large')
                return redirect('admin_deals')
            
            # Process CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            
            # Skip header row if specified
            header_row = request.POST.get('header_row') == 'on'
            if header_row:
                next(reader)  # Skip the header row
            
            # Process rows
            deals_created = 0
            for row in reader:
                if len(row) < 2:  # Must have at least name and amount
                    continue
                
                name = row[0].strip()
                amount = 0
                try:
                    amount = float(row[1].strip()) if row[1].strip() else 0
                except ValueError:
                    amount = 0
                
                if not name or amount <= 0:  # Skip if name is empty or amount is invalid
                    continue
                
                # Create deal with available data
                deal = Deal(
                    name=name,
                    amount=amount,
                    stage=row[2].strip() if len(row) > 2 and row[2].strip() else 'qualification',
                    expected_close_date=row[3].strip() if len(row) > 3 and row[3].strip() else timezone.now() + timedelta(days=30),
                    probability=float(row[4].strip()) if len(row) > 4 and row[4].strip() else 50,
                    created_by=request.user
                )
                
                # Set account if provided
                if len(row) > 5 and row[5].strip():
                    try:
                        account_id = int(row[5].strip())
                        deal.account = Account.objects.get(id=account_id)
                    except Exception:
                        pass
                
                # Set contact if provided
                if len(row) > 6 and row[6].strip():
                    try:
                        contact_id = int(row[6].strip())
                        deal.contact = Contact.objects.get(id=contact_id)
                    except Exception:
                        pass
                
                deal.save()
                deals_created += 1
            
            messages.success(request, f'Successfully imported {deals_created} deals')
        except Exception as e:
            messages.error(request, f'Error importing deals: {str(e)}')
        
        return redirect('admin_deals')
    
    return redirect('admin_deals')

@login_required
@user_passes_test(is_admin)
def admin_download_deal_template(request):
    # Create a response object with appropriate headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="deal_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'amount', 'stage', 'expected_close_date', 'probability', 'account_id', 'contact_id', 'description'])
    
    return response

# Admin Transactions View
@login_required
@user_passes_test(is_admin)
def admin_transactions(request):
    # Get all transactions
    transactions = Transaction.objects.all().order_by('-date')
    
    # Get transaction stats
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    # This month's revenue and expenses
    month_transactions = transactions.filter(date__month=current_month, date__year=current_year)
    income = month_transactions.filter(transaction_type='income').aggregate(Sum('amount'))
    expenses = month_transactions.filter(transaction_type='expense').aggregate(Sum('amount'))
    
    revenue = income['amount__sum'] if income['amount__sum'] else 0
    expense_total = expenses['amount__sum'] if expenses['amount__sum'] else 0
    profit = revenue - expense_total
    
    # Get accounts and deals for filters
    accounts = Account.objects.all().order_by('name')
    deals = Deal.objects.all().order_by('-created_at')
    
    context = {
        'active_page': 'transactions',
        'transactions': transactions,
        'revenue': revenue,
        'expenses': expense_total,
        'profit': profit,
        'accounts': accounts,
        'deals': deals
    }
    
    return render(request, 'admin/transactions.html', context)

# Admin Tasks View
@login_required
@user_passes_test(is_admin)
def admin_tasks(request):
    # Check if the current user is a manager
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'
    
    # Get tasks based on role
    if is_manager:
        # Get the manager's username and user ID
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Get IDs of users managed by this manager
        managed_user_ids = []
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
        
        # Filter tasks by manager_username OR assigned_to is a user managed by this manager OR created_by is this manager
        tasks = Task.objects.filter(
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('-due_date')
    else:
        # Admin sees all tasks
        tasks = Task.objects.all().order_by('-due_date')
    
    # Calculate task stats
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    overdue_tasks = tasks.filter(due_date__lt=timezone.now().date()).exclude(status='completed').count()
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get users for assignee dropdown
    if is_manager:
        # Only show users managed by this manager
        manager_username = request.user.username
        users = User.objects.filter(
            models_Q(profile__manager_username=manager_username) |
            models_Q(id=request.user.id)  # Include the manager themselves
        ).distinct().order_by('username')
    else:
        # Admin sees all users
        users = User.objects.all().order_by('username')
    
    # Calculate task data for charts with different time frames
    task_counts = {
        'week': get_task_data_for_week(request.user),
        'month': get_task_data_for_month(request.user),
        'year': get_task_data_for_year(request.user)
    }
    
    # Calculate priority data for charts with different time frames
    priority_counts = {
        'week': get_priority_data_for_week(request.user),
        'month': get_priority_data_for_month(request.user),
        'year': get_priority_data_for_year(request.user)
    }
    
    # Get leads, contacts, accounts, and deals for the related items dropdown
    if is_manager:
        # Filter leads by manager
        manager_username = request.user.username
        manager_id = request.user.id
        
        # Get IDs of users managed by this manager
        managed_user_ids = []
        for user in User.objects.all():
            if hasattr(user, 'profile') and user.profile and user.profile.manager_username == manager_username:
                managed_user_ids.append(user.id)
        
        # Filter leads by manager_username OR assigned_to is a user managed by this manager OR created_by is this manager
        leads = Lead.objects.filter(
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('first_name', 'last_name')
        
        # Filter contacts by manager
        contacts = Contact.objects.filter(
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('first_name', 'last_name')
        
        # Filter accounts by manager
        accounts = Account.objects.filter(
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('name')
        
        # Filter deals by manager
        deals = Deal.objects.filter(
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        ).distinct().order_by('name')
    else:
        # Admin sees all items
        leads = Lead.objects.all().order_by('first_name', 'last_name')
        contacts = Contact.objects.all().order_by('first_name', 'last_name')
        accounts = Account.objects.all().order_by('name')
        deals = Deal.objects.all().order_by('name')
    
    # Convert related items to JSON for JavaScript
    # Add explicit type conversion to ensure JSON serialization works correctly
    leads_json = json.dumps([{
        'id': str(lead.id),  # Convert ID to string to ensure proper JSON serialization
        'name': f"{lead.first_name} {lead.last_name} ({lead.email})"
    } for lead in leads])
    
    contacts_json = json.dumps([{
        'id': str(contact.id),  # Convert ID to string to ensure proper JSON serialization
        'name': f"{contact.first_name} {contact.last_name} ({contact.email})"
    } for contact in contacts])
    
    accounts_json = json.dumps([{
        'id': str(account.id),  # Convert ID to string to ensure proper JSON serialization
        'name': f"{account.name} ({account.website or 'No website'})"
    } for account in accounts])
    
    deals_json = json.dumps([{
        'id': str(deal.id),  # Convert ID to string to ensure proper JSON serialization
        'name': f"{deal.name} (${deal.amount})"
    } for deal in deals])
    
    context = {
        'active_page': 'tasks',
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_rate': completion_rate,
        'users': users,
        'task_counts_json': json.dumps(task_counts),
        'priority_counts_json': json.dumps(priority_counts),
        'leads_json': leads_json,
        'contacts_json': contacts_json,
        'accounts_json': accounts_json,
        'deals_json': deals_json
    }
    
    return render(request, 'admin/tasks.html', context)


# Admin Calendar View
@login_required
@user_passes_test(is_admin)
def admin_calendar(request):
    """Render calendar showing tasks of logged-in admin / manager and managed users."""
    # Determine role
    is_manager = False
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        is_manager = request.user.profile.role.lower() == 'manager'

    # Build users queryset for dropdown
    if is_manager:
        manager_username = request.user.username
        users_qs = User.objects.filter(
            models_Q(profile__manager_username=manager_username) |
            models_Q(id=request.user.id)
        ).distinct().order_by('username')
    else:
        users_qs = User.objects.all().order_by('username')

    users_json = json.dumps([
        {
            'id': str(u.id),
            'name': u.get_full_name() or u.username
        } for u in users_qs
    ])

    context = {
        'active_page': 'calendar',
        'users': users_qs,
        'users_json': users_json,
    }
    return render(request, 'admin/calendar.html', context)

# Helper function to get task data for the past week
def get_task_data_for_week(user=None):
    # Get dates for the past 7 days
    today = timezone.now().date()
    days = []
    created_counts = []
    completed_counts = []
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Get data for each day of the week
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.strftime('%a'))  # Day name (Mon, Tue, etc.)
        
        # Filter tasks based on user role
        if is_manager:
            # Filter tasks for manager
            task_filter = models_Q(created_at__date=day)
            task_filter = task_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            created_count = Task.objects.filter(task_filter).distinct().count()
            
            # Count tasks completed on this day
            completed_filter = models_Q(status='completed', completed_date__date=day)
            completed_filter = completed_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            completed_count = Task.objects.filter(completed_filter).distinct().count()
        else:
            # Admin sees all tasks
            created_count = Task.objects.filter(created_at__date=day).count()
            completed_count = Task.objects.filter(status='completed', completed_date__date=day).count()
        
        created_counts.append(created_count)
        completed_counts.append(completed_count)
    
    return {
        'labels': days,
        'created': created_counts,
        'completed': completed_counts
    }

# Helper function to get task data for the past month
def get_task_data_for_month(user=None):
    # Get dates for the past 30 days
    today = timezone.now().date()
    days = []
    created_counts = []
    completed_counts = []
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Get data for each day of the month
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.day)  # Day of month (1-31)
        
        # Filter tasks based on user role
        if is_manager:
            # Filter tasks for manager
            task_filter = models_Q(created_at__date=day)
            task_filter = task_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            created_count = Task.objects.filter(task_filter).distinct().count()
            
            # Count tasks completed on this day
            completed_filter = models_Q(status='completed', completed_date__date=day)
            completed_filter = completed_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            completed_count = Task.objects.filter(completed_filter).distinct().count()
        else:
            # Admin sees all tasks
            created_count = Task.objects.filter(created_at__date=day).count()
            completed_count = Task.objects.filter(status='completed', completed_date__date=day).count()
        
        created_counts.append(created_count)
        completed_counts.append(completed_count)
    
    return {
        'labels': days,
        'created': created_counts,
        'completed': completed_counts
    }

# Helper function to get task data for the past year
def get_task_data_for_year(user=None):
    # Get data for each month of the past year
    today = timezone.now().date()
    months = []
    created_counts = []
    completed_counts = []
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Get data for each month of the year
    for i in range(11, -1, -1):
        # Calculate the first day of each month in the past year
        year = today.year
        month = today.month - i
        
        # Adjust year if we go to previous year
        while month <= 0:
            month += 12
            year -= 1
        
        # Get the month name
        month_name = datetime(year, month, 1).strftime('%b')  # Month name (Jan, Feb, etc.)
        months.append(month_name)
        
        # Count tasks created in this month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        # Filter tasks based on user role
        if is_manager:
            # Filter tasks for manager
            task_filter = models_Q(created_at__gte=start_date, created_at__lt=end_date)
            task_filter = task_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            created_count = Task.objects.filter(task_filter).distinct().count()
            
            # Count tasks completed in this month
            completed_filter = models_Q(status='completed', completed_date__gte=start_date, completed_date__lt=end_date)
            completed_filter = completed_filter & (
                models_Q(manager_username=manager_username) |
                models_Q(assigned_to__id__in=managed_user_ids) |
                models_Q(created_by_id=manager_id)
            )
            completed_count = Task.objects.filter(completed_filter).distinct().count()
        else:
            # Admin sees all tasks
            created_count = Task.objects.filter(created_at__gte=start_date, created_at__lt=end_date).count()
            completed_count = Task.objects.filter(status='completed', completed_date__gte=start_date, completed_date__lt=end_date).count()
        
        created_counts.append(created_count)
        completed_counts.append(completed_count)
    
    return {
        'labels': months,
        'created': created_counts,
        'completed': completed_counts
    }

# Helper function to get priority data for the past week
def get_priority_data_for_week(user=None):
    # Get tasks from the past 7 days
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Filter tasks based on user role
    if is_manager:
        # Filter tasks for manager
        base_filter = (
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        )
        
        # Count tasks by priority
        high_count = Task.objects.filter(
            models_Q(created_at__date__gte=week_ago, created_at__date__lte=today, priority='high') & base_filter
        ).distinct().count()
        
        medium_count = Task.objects.filter(
            models_Q(created_at__date__gte=week_ago, created_at__date__lte=today, priority='medium') & base_filter
        ).distinct().count()
        
        low_count = Task.objects.filter(
            models_Q(created_at__date__gte=week_ago, created_at__date__lte=today, priority='low') & base_filter
        ).distinct().count()
    else:
        # Admin sees all tasks
        high_count = Task.objects.filter(
            created_at__date__gte=week_ago,
            created_at__date__lte=today,
            priority='high'
        ).count()
        
        medium_count = Task.objects.filter(
            created_at__date__gte=week_ago,
            created_at__date__lte=today,
            priority='medium'
        ).count()
        
        low_count = Task.objects.filter(
            created_at__date__gte=week_ago,
            created_at__date__lte=today,
            priority='low'
        ).count()
    
    return {
        'high': high_count,
        'medium': medium_count,
        'low': low_count
    }

# Helper function to get priority data for the past month
def get_priority_data_for_month(user=None):
    # Get tasks from the past 30 days
    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Filter tasks based on user role
    if is_manager:
        # Filter tasks for manager
        base_filter = (
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        )
        
        # Count tasks by priority
        high_count = Task.objects.filter(
            models_Q(created_at__date__gte=month_ago, created_at__date__lte=today, priority='high') & base_filter
        ).distinct().count()
        
        medium_count = Task.objects.filter(
            models_Q(created_at__date__gte=month_ago, created_at__date__lte=today, priority='medium') & base_filter
        ).distinct().count()
        
        low_count = Task.objects.filter(
            models_Q(created_at__date__gte=month_ago, created_at__date__lte=today, priority='low') & base_filter
        ).distinct().count()
    else:
        # Admin sees all tasks
        high_count = Task.objects.filter(
            created_at__date__gte=month_ago,
            created_at__date__lte=today,
            priority='high'
        ).count()
        
        medium_count = Task.objects.filter(
            created_at__date__gte=month_ago,
            created_at__date__lte=today,
            priority='medium'
        ).count()
        
        low_count = Task.objects.filter(
            created_at__date__gte=month_ago,
            created_at__date__lte=today,
            priority='low'
        ).count()
    
    return {
        'high': high_count,
        'medium': medium_count,
        'low': low_count
    }

# Helper function to get priority data for the past year
def get_priority_data_for_year(user=None):
    # Get tasks from the current year
    today = timezone.now().date()
    start_of_year = datetime(today.year, 1, 1).date()
    
    # Check if the user is a manager
    is_manager = False
    manager_username = None
    manager_id = None
    managed_user_ids = []
    
    if user and hasattr(user, 'profile') and user.profile and user.profile.role:
        is_manager = user.profile.role.lower() == 'manager'
        if is_manager:
            manager_username = user.username
            manager_id = user.id
            
            # Get IDs of users managed by this manager
            for managed_user in User.objects.all():
                if hasattr(managed_user, 'profile') and managed_user.profile and managed_user.profile.manager_username == manager_username:
                    managed_user_ids.append(managed_user.id)
    
    # Filter tasks based on user role
    if is_manager:
        # Filter tasks for manager
        base_filter = (
            models_Q(manager_username=manager_username) |
            models_Q(assigned_to__id__in=managed_user_ids) |
            models_Q(created_by_id=manager_id)
        )
        
        # Count tasks by priority
        high_count = Task.objects.filter(
            models_Q(created_at__date__gte=start_of_year, created_at__date__lte=today, priority='high') & base_filter
        ).distinct().count()
        
        medium_count = Task.objects.filter(
            models_Q(created_at__date__gte=start_of_year, created_at__date__lte=today, priority='medium') & base_filter
        ).distinct().count()
        
        low_count = Task.objects.filter(
            models_Q(created_at__date__gte=start_of_year, created_at__date__lte=today, priority='low') & base_filter
        ).distinct().count()
    else:
        # Admin sees all tasks
        high_count = Task.objects.filter(
            created_at__date__gte=start_of_year,
            created_at__date__lte=today,
            priority='high'
        ).count()
        
        medium_count = Task.objects.filter(
            created_at__date__gte=start_of_year,
            created_at__date__lte=today,
            priority='medium'
        ).count()
        
        low_count = Task.objects.filter(
            created_at__date__gte=start_of_year,
            created_at__date__lte=today,
            priority='low'
        ).count()
    
    return {
        'high': high_count,
        'medium': medium_count,
        'low': low_count
    }

# Admin Reports View
@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    # Get basic stats for reports
    total_accounts = Account.objects.count()
    total_contacts = Contact.objects.count()
    total_deals = Deal.objects.count()
    total_revenue = Transaction.objects.filter(transaction_type='income').aggregate(Sum('amount'))
    revenue = total_revenue['amount__sum'] if total_revenue['amount__sum'] else 0
    
    # Deal stage distribution
    deal_stages = {}
    for stage_id, stage_name in DEAL_STAGE_CHOICES:
        stage_count = Deal.objects.filter(stage=stage_id).count()
        deal_stages[stage_name] = stage_count
    
    # Create sample data for report
    total_sales = revenue
    deals_closed = Deal.objects.filter(stage='closed_won').count()
    avg_deal_size = revenue / deals_closed if deals_closed > 0 else 0
    new_customers = Account.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    
    # Sample top products data
    top_products = []
    
    # Get actual products if available
    products = Product.objects.all()[:5]
    for i, product in enumerate(products):
        # Create sample product data
        trend = random.randint(-20, 30)
        
        top_products.append({
            'name': product.name,
            'category': product.category.name if hasattr(product, 'category') and product.category else 'General',
            'units_sold': random.randint(10, 100),
            'revenue': product.unit_price * random.randint(10, 100),
            'percentage': round(random.uniform(5, 25), 1),
            'trend': trend,
            'trend_abs': abs(trend) if trend < 0 else trend  # Add the absolute value for negative trends
        })
    
    # If no products, add sample data
    if not top_products:
        sample_products = [
            {'name': 'Premium Plan', 'category': 'Subscription'},
            {'name': 'Basic Plan', 'category': 'Subscription'},
            {'name': 'Enterprise Solution', 'category': 'Software'},
            {'name': 'Data Analytics', 'category': 'Service'},
            {'name': 'Consulting Package', 'category': 'Service'}
        ]
        
        for product in sample_products:
            trend = random.randint(-20, 30)
            top_products.append({
                'name': product['name'],
                'category': product['category'],
                'units_sold': random.randint(10, 100),
                'revenue': random.randint(1000, 10000),
                'percentage': round(random.uniform(5, 25), 1),
                'trend': trend,
                'trend_abs': abs(trend) if trend < 0 else trend  # Add the absolute value for negative trends
            })
    
    # Sample account data for the sales by account section
    accounts_data = []
    
    # Get actual accounts if available
    accounts_list = Account.objects.all()[:5]
    for account in accounts_list:
        trend = random.randint(-15, 25)
        accounts_data.append({
            'name': account.name,
            'revenue': random.randint(5000, 50000),
            'deals': random.randint(1, 10),
            'trend': trend,
            'trend_abs': abs(trend) if trend < 0 else trend  # Add the absolute value for negative trends
        })
    
    # If no accounts, add sample data
    if not accounts_data:
        sample_accounts = [
            {'name': 'Acme Corporation'},
            {'name': 'Globex Industries'},
            {'name': 'Wayne Enterprises'},
            {'name': 'Stark Industries'},
            {'name': 'Umbrella Corp'}
        ]
        
        for sample_account in sample_accounts:
            trend = random.randint(-15, 25)
            accounts_data.append({
                'name': sample_account['name'],
                'revenue': random.randint(5000, 50000),
                'deals': random.randint(1, 10),
                'trend': trend,
                'trend_abs': abs(trend) if trend < 0 else trend  # Add the absolute value for negative trends
            })
    
    context = {
        'active_page': 'reports',
        'total_accounts': total_accounts,
        'total_contacts': total_contacts,
        'total_deals': total_deals,
        'total_revenue': revenue,
        'deal_stages': deal_stages,
        'total_sales': total_sales,
        'deals_closed': deals_closed,
        'avg_deal_size': avg_deal_size,
        'new_customers': new_customers,
        'top_products': top_products,
        'accounts': accounts_data
    }
    
    return render(request, 'admin/reports.html', context)

# Admin Deals View
@login_required
@user_passes_test(is_admin)
def admin_deals(request):
    # Get all deals
    deals = Deal.objects.all().order_by('-created_at')
    
    # Calculate deal stats
    total_deals = deals.count()
    won_deals = deals.filter(stage='closed_won').count()
    pipeline_value = deals.exclude(stage__in=['closed_won', 'closed_lost']).aggregate(Sum('amount'))
    pipeline_total = pipeline_value['amount__sum'] if pipeline_value['amount__sum'] else 0
    win_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0
    
    # Get all accounts for filtering
    accounts = Account.objects.all().order_by('name')
    
    # Prepare data for charts in JSON format
    stage_names = [stage_name for stage_id, stage_name in DEAL_STAGE_CHOICES]
    stage_counts_list = []
    stage_values_list = []
    
    import json
    
    for stage_id, stage_name in DEAL_STAGE_CHOICES:
        stage_deals = deals.filter(stage=stage_id)
        stage_counts_list.append(stage_deals.count())
        
        stage_amount = stage_deals.aggregate(Sum('amount'))
        stage_values_list.append(stage_amount['amount__sum'] if stage_amount['amount__sum'] else 0)
    
    # Convert to JSON strings for the template
    stage_labels = json.dumps(stage_names)
    stage_counts_json = json.dumps(stage_counts_list)
    stage_values_json = json.dumps(stage_values_list)
    
    context = {
        'active_page': 'deals',
        'deals': deals,
        'total_deals': total_deals,
        'won_deals': won_deals,
        'pipeline_value': pipeline_total,
        'win_rate': round(win_rate, 1),
        'accounts': accounts,
        'deal_stages': DEAL_STAGE_CHOICES,
        'stage_labels': stage_labels,
        'stage_counts_json': stage_counts_json,
        'stage_values_json': stage_values_json
    }
    
    return render(request, 'admin/deals.html', context)

# Admin Products View
@login_required
@user_passes_test(is_admin)
def admin_products(request):
    # Get all products
    products = Product.objects.all().order_by('name')
    
    # Calculate product stats
    total_products = products.count()
    # Since active field doesn't exist, we're setting all products as active
    active_products = total_products
    # Since we don't have the stock_quantity field, we'll set low_stock_products to 0
    low_stock_products = 0
    
    # Calculate total inventory value based on unit_price only
    inventory_value = 0
    for product in products:
        inventory_value += product.unit_price if hasattr(product, 'unit_price') else 0
    
    # Get categories for filters
    categories = set()
    for product in products:
        if product.category:
            categories.add(product.category)
    
    context = {
        'active_page': 'products',
        'products': products,
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'inventory_value': inventory_value,
        'categories': categories
    }
    
    return render(request, 'admin/products.html', context)

# Admin Task Create View
@login_required
@user_passes_test(is_admin)
def admin_task_create(request):
    if request.method == 'POST':
        # Get form data
        subject = request.POST.get('subject')
        due_date = request.POST.get('due_date')
        status = request.POST.get('status')
        priority = request.POST.get('priority')
        description = request.POST.get('description')
        assigned_to_id = request.POST.get('assigned_to')
        related_to_type = request.POST.get('related_to_type')
        related_to_id = request.POST.get('related_to_id')
        
        # Validate required data
        if not subject or not due_date or not assigned_to_id:
            messages.error(request, 'Please provide all required fields')
            return redirect('admin_tasks')
            
        # Check if the current user is a manager
        manager_username = None
        if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
            if request.user.profile.role.lower() == 'manager':
                manager_username = request.user.username
        
        # Create task
        task = Task(
            subject=subject,
            due_date=due_date,
            status=status,
            priority=priority,
            description=description,
            created_by=request.user,
            manager_username=manager_username
        )
        
        # Set assigned user
        if assigned_to_id:
            try:
                task.assigned_to = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist:
                pass
        
        # Handle related entity
        if related_to_type and related_to_id:
            if related_to_type == 'lead':
                try:
                    task.related_lead = Lead.objects.get(id=related_to_id)
                except Lead.DoesNotExist:
                    pass
            elif related_to_type == 'contact':
                try:
                    task.related_contact = Contact.objects.get(id=related_to_id)
                except Contact.DoesNotExist:
                    pass
            elif related_to_type == 'account':
                try:
                    task.related_account = Account.objects.get(id=related_to_id)
                except Account.DoesNotExist:
                    pass
            elif related_to_type == 'deal':
                try:
                    task.related_deal = Deal.objects.get(id=related_to_id)
                except Deal.DoesNotExist:
                    pass
        
        task.save()
        messages.success(request, 'Task created successfully')
        return redirect('admin_tasks')
    
    # If it's not a POST request, redirect to tasks list
    return redirect('admin_tasks')

# Admin Product Management Views
@login_required
@user_passes_test(is_admin)
def admin_product_create(request):
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        sku = request.POST.get('sku')
        price = request.POST.get('price', 0)
        stock_quantity = request.POST.get('stock_quantity', 0)
        description = request.POST.get('description')
        product_image = request.FILES.get('product_image')
        low_stock_threshold = request.POST.get('low_stock_threshold', 10)
        
        # Validate required data
        if not name or not price:
            messages.error(request, 'Product name and price are required')
            return redirect('admin_products')
        
        # Create product
        product = Product(
            name=name,
            sku=sku,
            price=price,
            stock_quantity=stock_quantity,
            description=description,
            low_stock_threshold=low_stock_threshold,
            created_by=request.user
        )
        
        # Set category if provided
        if category_id:
            try:
                # Assuming you have a ProductCategory model
                # Adjust as needed for your actual model
                product.category = ProductCategory.objects.get(id=category_id)
            except Exception:
                pass
        
        # Handle product image if uploaded
        if product_image:
            product.image = product_image
        
        product.save()
        messages.success(request, 'Product created successfully')
        return redirect('admin_products')
    
    # If it's not a POST request, redirect to products list
    return redirect('admin_products')

@login_required
@user_passes_test(is_admin)
def admin_product_detail(request, product_id):
    # Get product or 404
    product = get_object_or_404(Product, id=product_id)
    
    # Get related transactions
    # This would need to be adjusted based on your data model
    # e.g., how products are associated with transactions
    transactions = Transaction.objects.filter(product=product).order_by('-date')
    
    context = {
        'active_page': 'products',
        'product': product,
        'transactions': transactions
    }
    
    return render(request, 'admin/product_detail.html', context)

@login_required
@user_passes_test(is_admin)
def admin_product_edit(request, product_id):
    # Get product or 404
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Get form data
        product.name = request.POST.get('name')
        category_id = request.POST.get('category')
        product.sku = request.POST.get('sku')
        product.price = request.POST.get('price', 0)
        product.stock_quantity = request.POST.get('stock_quantity', 0)
        product.description = request.POST.get('description')
        product_image = request.FILES.get('product_image')
        product.low_stock_threshold = request.POST.get('low_stock_threshold', 10)
        
        # Validate required data
        if not product.name or not product.price:
            messages.error(request, 'Product name and price are required')
            return redirect('admin_product_edit', product_id=product.id)
        
        # Set category if provided
        if category_id:
            try:
                product.category = ProductCategory.objects.get(id=category_id)
            except Exception:
                pass
        else:
            product.category = None
        
        # Handle product image if uploaded
        if product_image:
            product.image = product_image
        
        product.save()
        messages.success(request, 'Product updated successfully')
        return redirect('admin_products')
    
    # Get all categories for dropdown
    # Adjust based on your actual model
    try:
        categories = ProductCategory.objects.all().order_by('name')
    except Exception:
        categories = []
    
    context = {
        'active_page': 'products',
        'product': product,
        'categories': categories
    }
    
    return render(request, 'admin/product_edit.html', context)

@login_required
@user_passes_test(is_admin)
def admin_product_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_products')
        
        try:
            # Check if file is too large
            if csv_file.size > 1048576:  # 1 MB
                messages.error(request, 'The uploaded file is too large')
                return redirect('admin_products')
            
            # Process CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            
            # Skip header row if specified
            header_row = request.POST.get('header_row') == 'on'
            if header_row:
                next(reader)  # Skip the header row
            
            # Process rows
            products_created = 0
            for row in reader:
                if len(row) < 2:  # Must have at least name and price
                    continue
                
                name = row[0].strip()
                price = 0
                try:
                    price = float(row[3].strip()) if len(row) > 3 and row[3].strip() else 0
                except ValueError:
                    price = 0
                
                if not name or price <= 0:  # Skip if name is empty or price is invalid
                    continue
                
                # Create product with available data
                product = Product(
                    name=name,
                    sku=row[2].strip() if len(row) > 2 else '',
                    price=price,
                    stock_quantity=int(row[4]) if len(row) > 4 and row[4].strip() else 0,
                    description=row[5].strip() if len(row) > 5 else '',
                    low_stock_threshold=int(row[6]) if len(row) > 6 and row[6].strip() else 10,
                    created_by=request.user
                )
                
                # Set category if provided
                if len(row) > 1 and row[1].strip():
                    try:
                        category_id = int(row[1].strip())
                        product.category = ProductCategory.objects.get(id=category_id)
                    except Exception:
                        pass
                
                product.save()
                products_created += 1
            
            messages.success(request, f'Successfully imported {products_created} products')
        except Exception as e:
            messages.error(request, f'Error importing products: {str(e)}')
        
        return redirect('admin_products')
    
    return redirect('admin_products')

@login_required
@user_passes_test(is_admin)
def admin_download_product_template(request):
    # Create a response object with appropriate headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="product_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'category_id', 'sku', 'price', 'stock_quantity', 'description', 'low_stock_threshold'])
    
    return response

# Admin Transaction Management Views
@login_required
@user_passes_test(is_admin)
def admin_transaction_create(request):
    if request.method == 'POST':
        # Get form data
        transaction_type = request.POST.get('transaction_type')
        amount = request.POST.get('amount', 0)
        date = request.POST.get('date')
        status = request.POST.get('status')
        account_id = request.POST.get('account')
        deal_id = request.POST.get('deal')
        description = request.POST.get('description')
        category = request.POST.get('category')
        
        # Validate required data
        if not transaction_type or not amount or not date:
            messages.error(request, 'Transaction type, amount, and date are required')
            return redirect('admin_transactions')
        
        # Create transaction
        transaction = Transaction(
            transaction_type=transaction_type,
            amount=amount,
            date=date,
            status=status,
            description=description,
            category=category,
            created_by=request.user
        )
        
        # Set account if provided
        if account_id:
            try:
                transaction.account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                pass
        
        # Set deal if provided
        if deal_id:
            try:
                transaction.deal = Deal.objects.get(id=deal_id)
            except Deal.DoesNotExist:
                pass
        
        transaction.save()
        messages.success(request, 'Transaction created successfully')
        return redirect('admin_transactions')
    
    # If it's not a POST request, redirect to transactions list
    return redirect('admin_transactions')

@login_required
@user_passes_test(is_admin)
def admin_transaction_detail(request, transaction_id):
    # Get transaction or 404
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Check if user came from the dashboard
    # This implements the security feature from the memory about requiring coming from dashboard
    from_dashboard = request.session.get('from_dashboard', False)
    
    # Only users coming from dashboard can view transaction details
    if not from_dashboard and not request.user.is_superuser:
        messages.warning(request, 'Please access transactions from the dashboard')
        return redirect('admin_dashboard')
    
    context = {
        'active_page': 'transactions',
        'transaction': transaction,
        'from_dashboard': from_dashboard
    }
    
    return render(request, 'admin/transaction_detail.html', context)

@login_required
@user_passes_test(is_admin)
def admin_transaction_edit(request, transaction_id):
    # Get transaction or 404
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    if request.method == 'POST':
        # Get form data
        transaction.transaction_type = request.POST.get('transaction_type')
        transaction.amount = request.POST.get('amount', 0)
        transaction.date = request.POST.get('date')
        transaction.status = request.POST.get('status')
        account_id = request.POST.get('account')
        deal_id = request.POST.get('deal')
        transaction.description = request.POST.get('description')
        transaction.category = request.POST.get('category')
        
        # Validate required data
        if not transaction.transaction_type or not transaction.amount or not transaction.date:
            messages.error(request, 'Transaction type, amount, and date are required')
            return redirect('admin_transaction_edit', transaction_id=transaction.id)
        
        # Set account if provided
        if account_id:
            try:
                transaction.account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                pass
        else:
            transaction.account = None
        
        # Set deal if provided
        if deal_id:
            try:
                transaction.deal = Deal.objects.get(id=deal_id)
            except Deal.DoesNotExist:
                pass
        else:
            transaction.deal = None
        
        transaction.save()
        messages.success(request, 'Transaction updated successfully')
        return redirect('admin_transactions')
    
    # Get all accounts and deals for dropdowns
    accounts = Account.objects.all().order_by('name')
    deals = Deal.objects.all().order_by('-created_at')
    
    context = {
        'active_page': 'transactions',
        'transaction': transaction,
        'accounts': accounts,
        'deals': deals
    }
    
    return render(request, 'admin/transaction_edit.html', context)

@login_required
@user_passes_test(is_admin)
def admin_transaction_import(request):
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        
        # Check if file is CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_transactions')
        
        try:
            # Check if file is too large
            if csv_file.size > 1048576:  # 1 MB
                messages.error(request, 'The uploaded file is too large')
                return redirect('admin_transactions')
            
            # Process CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            
            # Skip header row if specified
            header_row = request.POST.get('header_row') == 'on'
            if header_row:
                next(reader)  # Skip the header row
            
            # Process rows
            transactions_created = 0
            for row in reader:
                if len(row) < 3:  # Must have at least type, amount, and date
                    continue
                
                transaction_type = row[0].strip()
                amount = 0
                try:
                    amount = float(row[1].strip()) if row[1].strip() else 0
                except ValueError:
                    amount = 0
                
                date = row[2].strip()
                
                if not transaction_type or amount <= 0 or not date:  # Skip if essential data is missing
                    continue
                
                # Create transaction with available data
                transaction = Transaction(
                    transaction_type=transaction_type,
                    amount=amount,
                    date=date,
                    status=row[3].strip() if len(row) > 3 else 'completed',
                    description=row[6].strip() if len(row) > 6 else '',
                    category=row[7].strip() if len(row) > 7 else '',
                    created_by=request.user
                )
                
                # Set account if provided
                if len(row) > 4 and row[4].strip():
                    try:
                        account_id = int(row[4].strip())
                        transaction.account = Account.objects.get(id=account_id)
                    except Exception:
                        pass
                
                # Set deal if provided
                if len(row) > 5 and row[5].strip():
                    try:
                        deal_id = int(row[5].strip())
                        transaction.deal = Deal.objects.get(id=deal_id)
                    except Exception:
                        pass
                
                transaction.save()
                transactions_created += 1
            
            messages.success(request, f'Successfully imported {transactions_created} transactions')
        except Exception as e:
            messages.error(request, f'Error importing transactions: {str(e)}')
        
        return redirect('admin_transactions')
    
    return redirect('admin_transactions')

@login_required
@user_passes_test(is_admin)
def admin_download_transaction_template(request):
    # Create a response object with appropriate headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transaction_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['transaction_type', 'amount', 'date', 'status', 'account_id', 'deal_id', 'description', 'category'])
    
    return response

# Admin API for dashboard data
@login_required
@user_passes_test(is_admin)
def admin_api_dashboard_data(request):
    data = {
        'sales_chart': {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': [18500, 22000, 19500, 24000, 25500, 28000, 30000, 32500, 34000, 36500, 39000, 42000]
                },
                {
                    'label': 'Deals Closed',
                    'data': [15, 18, 14, 20, 22, 25, 28, 30, 32, 34, 36, 40]
                }
            ]
        },
        'lead_sources': {
            'labels': ['Website', 'Referral', 'Social Media', 'Email', 'Phone', 'Other'],
            'data': [35, 25, 15, 10, 10, 5]
        },
        'user_roles': {
            'labels': ['Admin', 'Manager', 'Sales', 'Support'],
            'data': [5, 10, 25, 15]
        }
    }
    
    return JsonResponse(data)
