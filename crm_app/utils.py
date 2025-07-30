from .models import UserActivityLog

def log_user_activity(user, action_type, action_detail, model_affected=None, object_id=None, ip_address=None, additional_data=None):
    """
    Utility function to log user activities throughout the application
    
    Parameters:
    - user: The user performing the action
    - action_type: Type of action (from UserActivityLog.ACTION_TYPES)
    - action_detail: Description of the action
    - model_affected: Optional model name affected by the action
    - object_id: Optional ID of the object affected
    - ip_address: Optional IP address of the user
    - additional_data: Optional JSON data with additional information
    """
    try:
        UserActivityLog.objects.create(
            user=user,
            action_type=action_type,
            action_detail=action_detail,
            model_affected=model_affected,
            object_id=object_id,
            ip_address=ip_address,
            additional_data=additional_data
        )
    except Exception as e:
        # Log the error but don't disrupt the user experience
        print(f"Error logging user activity: {str(e)}")
