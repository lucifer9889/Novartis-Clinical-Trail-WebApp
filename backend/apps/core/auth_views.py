"""
Authentication Views for Clinical Trial Control Tower.

Provides login, logout, and user API endpoints using Django's built-in auth.

Views:
    - login_view: GET/POST login page
    - logout_view: Logout and redirect
    - user_me_api: GET /api/me/ - current user info

URL Patterns (add to urls.py):
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('api/me/', user_me_api, name='api-user-me'),
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .auth_helpers import user_role, get_allowed_modules, get_user_context


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Handle user login.
    
    GET: Display login form
    POST: Authenticate and redirect to dashboard
    
    Template: login.html
    """
    # If already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    error_message = None
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            error_message = 'Please enter both username and password.'
        else:
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Redirect to 'next' URL if provided, otherwise dashboard
                    next_url = request.GET.get('next', '/dashboard/')
                    return redirect(next_url)
                else:
                    error_message = 'Your account has been disabled.'
            else:
                error_message = 'Invalid username or password.'
    
    return render(request, 'login.html', {
        'error_message': error_message,
    })


def logout_view(request):
    """
    Log out the current user and redirect to login page.
    """
    logout(request)
    return redirect('/login/')


@ensure_csrf_cookie
def user_me_api(request):
    """
    API endpoint to get current user info.
    
    GET /api/me/
    
    Returns:
        JSON object with user info:
        - username
        - full_name
        - email
        - role
        - allowed_modules
        - is_authenticated
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'is_authenticated': False,
            'error': 'Not authenticated'
        }, status=401)
    
    user = request.user
    role = user_role(request)
    
    return JsonResponse({
        'is_authenticated': True,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'allowed_modules': get_allowed_modules(request),
    })
