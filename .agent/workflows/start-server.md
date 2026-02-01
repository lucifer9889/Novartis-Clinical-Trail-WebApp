---
description: Start the Clinical Trial Portal development server
---

# Start Development Server

This workflow starts the Django development server for the Clinical Trial Control Tower.

## Steps

1. Navigate to the project directory
   ```
   cd "s:\NMIMS\CASE COMP\Novartis\Code\Clinical-Trail-Portal"
   ```

// turbo
2. Activate the virtual environment and start the server
   ```powershell
   & '.\venv\Scripts\Activate.ps1'; cd backend; python manage.py runserver
   ```

3. Access the application at:
   - Homepage: http://127.0.0.1:8000/
   - Login: http://127.0.0.1:8000/login/
   - Dashboard: http://127.0.0.1:8000/dashboard/

## Demo Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin | Admin |
| Aarav | Aarav | Sponsor |
| Priya | Priya | CRA |
| Rohit | Rohit | Site User |
| Neha | Neha | Data Manager |
| Vikram | Vikram | Safety User |
| Ananya | Ananya | Medical Coder |
