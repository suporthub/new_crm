from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, status, authentication, filters
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import UserProfile, AllotManager
from .serializers import UserSerializer, UserProfileSerializer, AllotManagerSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication, authentication.SessionAuthentication]
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'user activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'user deactivated'})
    
    def create(self, request, *args, **kwargs):
        # Get user data from request
        user_data = {
            'username': request.data.get('username'),
            'email': request.data.get('email'),
            'first_name': request.data.get('first_name', ''),
            'last_name': request.data.get('last_name', ''),
            'is_active': request.data.get('status') == 'active',
            'password': request.data.get('password')
        }
        
        # Get profile data
        profile_data = {
            'role': request.data.get('role'),
            'department': request.data.get('department', ''),
            'phone': request.data.get('phone', ''),
            'manager_username': request.data.get('manager_username')
        }
        
        # Create the user
        serializer = self.get_serializer(data=user_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Set the password properly
        user.set_password(user_data['password'])
        user.save()
        
        # Create or update the profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile_serializer = UserProfileSerializer(profile, data=profile_data)
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()
        
        # Return the response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Get user data from request
        user_data = {
            'username': request.data.get('username', instance.username),
            'email': request.data.get('email', instance.email),
            'first_name': request.data.get('first_name', instance.first_name),
            'last_name': request.data.get('last_name', instance.last_name),
            'is_active': request.data.get('status', 'active' if instance.is_active else 'inactive') == 'active'
        }
        
        # Get profile data
        profile_data = {
            'role': request.data.get('role'),
            'department': request.data.get('department', ''),
            'phone': request.data.get('phone', ''),
            'manager_username': request.data.get('manager_username')
        }
        
        # Update the user
        serializer = self.get_serializer(instance, data=user_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Update password if provided
        if 'password' in request.data and request.data['password']:
            instance.set_password(request.data['password'])
            instance.save()
        
        # Create or update the profile
        profile, created = UserProfile.objects.get_or_create(user=instance)
        profile_serializer = UserProfileSerializer(profile, data=profile_data, partial=partial)
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()
        
        # Return the response
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@authentication_classes([JWTAuthentication, authentication.SessionAuthentication])
def get_users_by_manager(request):
    """
    API endpoint to get users based on manager relationship.
    Logic:
    1. Get the current user's manager_username
    2. Return all users who have that manager_username
    3. If current user is a manager, also return users who have current user as their manager
    4. If current user is an admin, return all users
    """
    current_user = request.user
    
    try:
        # Get current user's profile
        current_user_profile = UserProfile.objects.get(user=current_user)
        current_user_role = current_user_profile.role
        current_user_manager = current_user_profile.manager_username
        
        # Initialize queryset
        users = []
        
        # Check if user is admin - return all users
        if current_user_role == 'admin':
            users = User.objects.all().order_by('first_name', 'last_name')
        # Check if user is manager - return all users where manager_username = current_username
        elif current_user_role == 'manager':
            users = User.objects.filter(
                profile__manager_username=current_user.username
            ).order_by('first_name', 'last_name')
        # Otherwise, return users with the same manager
        elif current_user_manager:
            users = User.objects.filter(
                profile__manager_username=current_user_manager
            ).order_by('first_name', 'last_name')
        
        # Serialize the users with their profiles
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    except UserProfile.DoesNotExist:
        return Response(
            {'error': 'User profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AllotManagerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for manager allocation by country
    """
    queryset = AllotManager.objects.all().order_by('country')
    serializer_class = AllotManagerSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication, authentication.SessionAuthentication]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['country', 'manager_username']
    ordering_fields = ['country', 'manager_username', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save()
