"""
Authentication and Authorization Helpers for Clinical Trial Control Tower.

Contains utility functions and decorators for role-based access control (RBAC).
These helpers work with Django's built-in auth system and Groups.

Usage:
    from apps.core.auth_helpers import user_role, require_roles, get_allowed_modules
    
    @require_roles(['Admin', 'Sponsor'])
    def my_view(request):
        ...
"""

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


# Role to allowed modules mapping (mirrors seed_auth.py)
ROLE_PERMISSIONS = {
    'Admin': {
        'allowed_modules': ['dashboard', 'sites', 'queries', 'reports', 'audit',
                           'security_alerts', 'predictive_ai', 'excel_input',
                           'safety', 'coding', 'admin'],
    },
    'Sponsor': {
        'allowed_modules': ['dashboard', 'reports', 'predictive_ai'],
    },
    'CRA': {
        'allowed_modules': ['dashboard', 'sites', 'queries', 'audit', 'reports'],
    },
    'SiteUser': {
        'allowed_modules': ['dashboard', 'excel_input', 'queries'],
    },
    'DataManager': {
        'allowed_modules': ['dashboard', 'queries', 'reports', 'excel_input'],
    },
    'SafetyUser': {
        'allowed_modules': ['dashboard', 'safety', 'reports'],
    },
    'MedicalCoder': {
        'allowed_modules': ['dashboard', 'coding', 'reports'],
    },
}


def user_role(request):
    """
    Get the primary role (group name) for the authenticated user.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Role name (group name) or 'Anonymous' if not authenticated
    """
    if not request.user.is_authenticated:
        return 'Anonymous'
    
    # Get first group (primary role)
    groups = request.user.groups.all()
    if groups.exists():
        return groups.first().name
    
    # Superusers without a group are treated as Admin
    if request.user.is_superuser:
        return 'Admin'
    
    return 'Unknown'


def get_allowed_modules(request):
    """
    Get the list of modules the current user can access.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        list: List of allowed module names
    """
    role = user_role(request)
    
    if role in ROLE_PERMISSIONS:
        return ROLE_PERMISSIONS[role]['allowed_modules']
    
    # Superusers get all modules
    if request.user.is_authenticated and request.user.is_superuser:
        return ROLE_PERMISSIONS['Admin']['allowed_modules']
    
    return []


def can_access_module(request, module_name):
    """
    Check if the current user can access a specific module.
    
    Args:
        request: Django HttpRequest object
        module_name: Name of the module to check access for
        
    Returns:
        bool: True if user can access the module
    """
    allowed_modules = get_allowed_modules(request)
    return module_name in allowed_modules


def require_roles(allowed_roles, redirect_url='/login/', api_mode=False):
    """
    Decorator to require specific roles for a view.
    
    Args:
        allowed_roles: List of role names that can access the view
        redirect_url: URL to redirect to if access denied (for page views)
        api_mode: If True, return 403 JSON response instead of redirect
        
    Usage:
        @require_roles(['Admin', 'Sponsor'])
        def sponsor_dashboard(request):
            ...
            
        @require_roles(['Admin'], api_mode=True)
        def admin_api_endpoint(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # First check if user is authenticated
            if not request.user.is_authenticated:
                if api_mode:
                    return JsonResponse(
                        {'error': 'Authentication required', 'code': 'AUTH_REQUIRED'},
                        status=401
                    )
                return redirect(redirect_url)
            
            # Get user's role
            role = user_role(request)
            
            # Check if role is allowed
            if role not in allowed_roles:
                # Also check if user is superuser (always allowed)
                if not request.user.is_superuser:
                    if api_mode:
                        return JsonResponse(
                            {
                                'error': 'Access denied',
                                'code': 'FORBIDDEN',
                                'required_roles': allowed_roles,
                                'user_role': role
                            },
                            status=403
                        )
                    # For page views, redirect to dashboard with error
                    return redirect('/dashboard/?error=access_denied')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_module_access(module_name, redirect_url='/login/', api_mode=False):
    """
    Decorator to require access to a specific module.
    
    Args:
        module_name: Name of the module required
        redirect_url: URL to redirect to if access denied
        api_mode: If True, return 403 JSON response instead of redirect
        
    Usage:
        @require_module_access('predictive_ai')
        def predictions_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if api_mode:
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=401
                    )
                return redirect(redirect_url)
            
            if not can_access_module(request, module_name):
                if api_mode:
                    return JsonResponse(
                        {
                            'error': 'Access denied',
                            'module': module_name,
                            'message': f'You do not have permission to access {module_name}'
                        },
                        status=403
                    )
                return redirect('/dashboard/?error=module_access_denied')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_user_context(request):
    """
    Get a context dictionary with user info for templates.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: User context for templates
    """
    if not request.user.is_authenticated:
        return {
            'is_authenticated': False,
            'username': '',
            'full_name': '',
            'role': 'Anonymous',
            'allowed_modules': [],
        }
    
    user = request.user
    role = user_role(request)
    
    return {
        'is_authenticated': True,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
        'allowed_modules': get_allowed_modules(request),
    }
