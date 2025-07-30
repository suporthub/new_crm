from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import UserSettings
from .serializers import UserSettingsSerializer
from .utils import log_user_activity

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """
    Get or update the current user's settings
    """
    # Get the user's settings or create if they don't exist
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        serializer = UserSettingsSerializer(settings)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action_type='update',
                action_detail='Updated user settings',
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_general_settings(request):
    """
    Update general settings for the current user
    """
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    # Only update general settings fields
    general_fields = ['timezone', 'date_format', 'time_format', 'language']
    data = {k: v for k, v in request.data.items() if k in general_fields}
    
    serializer = UserSettingsSerializer(settings, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='update',
            action_detail='Updated general settings',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_notification_settings(request):
    """
    Update notification settings for the current user
    """
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    # Only update notification settings fields
    notification_fields = ['email_notifications', 'browser_notifications', 
                          'task_reminders', 'deal_updates', 'lead_notifications']
    data = {k: v for k, v in request.data.items() if k in notification_fields}
    
    serializer = UserSettingsSerializer(settings, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='update',
            action_detail='Updated notification settings',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_security_settings(request):
    """
    Update security settings for the current user
    """
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    # Only update security settings fields
    security_fields = ['two_factor_auth', 'auto_logout', 'session_timeout']
    data = {k: v for k, v in request.data.items() if k in security_fields}
    
    serializer = UserSettingsSerializer(settings, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='update',
            action_detail='Updated security settings',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_appearance_settings(request):
    """
    Update appearance settings for the current user
    """
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    # Only update appearance settings fields
    appearance_fields = ['theme', 'color_scheme', 'font_size', 'compact_view']
    data = {k: v for k, v in request.data.items() if k in appearance_fields}
    
    serializer = UserSettingsSerializer(settings, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Log the activity
        log_user_activity(
            user=request.user,
            action_type='update',
            action_detail='Updated appearance settings',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
