"""
seed_auth - Management command to seed authentication data.

Creates/updates Django Groups and Users for role-based access control.
This command is idempotent - safe to run multiple times.

Usage:
    python manage.py seed_auth

Users created (username == password):
    - admin (superuser)
    - Aarav (Sponsor)
    - Priya (CRA/Monitor)
    - Rohit (Site User)
    - Neha (Data Manager)
    - Vikram (Safety User)
    - Ananya (Medical Coder)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Seed authentication groups and users for CTCT portal'

    # Define roles with their permissions and allowed modules
    ROLES = {
        'Admin': {
            'description': 'Full system access',
            'allowed_modules': ['dashboard', 'sites', 'queries', 'reports', 'audit', 
                               'security_alerts', 'predictive_ai', 'excel_input', 
                               'safety', 'coding', 'admin'],
            'is_superuser': True,
        },
        'Sponsor': {
            'description': 'High-level dashboards + reports + predictive AI; no raw editing',
            'allowed_modules': ['dashboard', 'reports', 'predictive_ai'],
            'is_superuser': False,
        },
        'CRA': {
            'description': 'Sites + queries + audit + reports; limited predictive',
            'allowed_modules': ['dashboard', 'sites', 'queries', 'audit', 'reports'],
            'is_superuser': False,
        },
        'SiteUser': {
            'description': 'Data entry / excel input + queries for their site only',
            'allowed_modules': ['dashboard', 'excel_input', 'queries'],
            'is_superuser': False,
        },
        'DataManager': {
            'description': 'Queries + missing pages + missing visits + data entry timeliness',
            'allowed_modules': ['dashboard', 'queries', 'reports', 'excel_input'],
            'is_superuser': False,
        },
        'SafetyUser': {
            'description': 'SAE discrepancy dashboards only + reports',
            'allowed_modules': ['dashboard', 'safety', 'reports'],
            'is_superuser': False,
        },
        'MedicalCoder': {
            'description': 'Coding dashboards only + reports',
            'allowed_modules': ['dashboard', 'coding', 'reports'],
            'is_superuser': False,
        },
    }

    # Define users with their roles (username == name == password)
    USERS = [
        {'username': 'admin', 'email': 'admin@ctct.local', 'role': 'Admin', 'first_name': 'Admin', 'last_name': 'User'},
        {'username': 'Aarav', 'email': 'aarav@ctct.local', 'role': 'Sponsor', 'first_name': 'Aarav', 'last_name': 'Sharma'},
        {'username': 'Priya', 'email': 'priya@ctct.local', 'role': 'CRA', 'first_name': 'Priya', 'last_name': 'Patel'},
        {'username': 'Rohit', 'email': 'rohit@ctct.local', 'role': 'SiteUser', 'first_name': 'Rohit', 'last_name': 'Verma'},
        {'username': 'Neha', 'email': 'neha@ctct.local', 'role': 'DataManager', 'first_name': 'Neha', 'last_name': 'Gupta'},
        {'username': 'Vikram', 'email': 'vikram@ctct.local', 'role': 'SafetyUser', 'first_name': 'Vikram', 'last_name': 'Singh'},
        {'username': 'Ananya', 'email': 'ananya@ctct.local', 'role': 'MedicalCoder', 'first_name': 'Ananya', 'last_name': 'Reddy'},
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding authentication data...'))
        
        # Step 1: Create Groups
        self.stdout.write('\n1. Creating/updating groups...')
        for role_name, role_info in self.ROLES.items():
            group, created = Group.objects.get_or_create(name=role_name)
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'   {action} group: {role_name}')
        
        # Step 2: Create/Update Users
        self.stdout.write('\n2. Creating/updating users...')
        for user_info in self.USERS:
            username = user_info['username']
            role = user_info['role']
            
            # Create or get user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': user_info['email'],
                    'first_name': user_info['first_name'],
                    'last_name': user_info['last_name'],
                }
            )
            
            # Update user info if exists
            if not created:
                user.email = user_info['email']
                user.first_name = user_info['first_name']
                user.last_name = user_info['last_name']
            
            # Set password to be same as username
            user.set_password(username)
            
            # Set superuser status
            if self.ROLES[role]['is_superuser']:
                user.is_superuser = True
                user.is_staff = True
            else:
                user.is_superuser = False
                user.is_staff = False
            
            user.save()
            
            # Clear existing groups and add the role group
            user.groups.clear()
            group = Group.objects.get(name=role)
            user.groups.add(group)
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'   {action} user: {username} ({role})')
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n✓ Authentication seeding complete!'))
        self.stdout.write('\nLogin credentials (username = password):')
        self.stdout.write('-' * 50)
        self.stdout.write(f'{"Username":<12} {"Role":<15} {"Password":<12}')
        self.stdout.write('-' * 50)
        for user_info in self.USERS:
            self.stdout.write(
                f'{user_info["username"]:<12} {user_info["role"]:<15} {user_info["username"]:<12}'
            )
        self.stdout.write('-' * 50)
