# Clinical Trial Control Tower - Updated Frontend

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Installation & Setup

1. **Navigate to project directory**
   ```bash
   cd "s:\NMIMS\CASE COMP\Novartis\Code\Clinical-Trail-Portal"
   ```

2. **Activate virtual environment**
   ```powershell
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   
   # Or Windows CMD
   .\venv\Scripts\activate.bat
   ```

3. **Install dependencies** (if not already installed)
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   cd backend
   python manage.py migrate
   ```

5. **Seed authentication data** (creates users and groups)
   ```bash
   python manage.py seed_auth
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Homepage: http://127.0.0.1:8000/
   - Login: http://127.0.0.1:8000/login/
   - Dashboard: http://127.0.0.1:8000/dashboard/

---

## 🔐 Login Credentials

All demo users have **username = password**:

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `admin` | `admin` | Admin | Full system access |
| `Aarav` | `Aarav` | Sponsor | Dashboard, Reports, Predictive AI |
| `Priya` | `Priya` | CRA | Dashboard, Sites, Queries, Audit, Reports |
| `Rohit` | `Rohit` | Site User | Dashboard, Excel Input, Queries |
| `Neha` | `Neha` | Data Manager | Dashboard, Queries, Reports, Excel Input |
| `Vikram` | `Vikram` | Safety User | Dashboard, Safety, Reports |
| `Ananya` | `Ananya` | Medical Coder | Dashboard, Coding, Reports |

---

## 📱 Application Structure

### Main Pages

| Route | Description | Protected |
|-------|-------------|-----------|
| `/` | Landing page | No |
| `/login/` | Login page | No |
| `/dashboard/` | Main dashboard (KPIs, charts, Trial Pulse) | Yes |
| `/excel-input/` | Data entry spreadsheet view | Yes |
| `/predictive-ai/` | Risk heatmap & AI assistant | Yes |
| `/sites/` | Sites management | Yes |
| `/queries/` | Query management | Yes |
| `/reports/` | Reports generation | Yes |
| `/audit/` | Audit trail | Yes |
| `/safety/` | SAE management | Yes |
| `/coding/` | Medical coding | Yes |
| `/security-alerts/` | Security alerts | Yes |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/me/` | GET | Current user info |
| `/api/v1/frontend-overview/` | GET | Dashboard KPI data |
| `/api/v1/role-visibility/` | GET | Subject listing |
| `/api/v1/study-summary/` | GET | Study summary |
| `/api/v1/sites/` | GET | Site listing |
| `/api/v1/risk-heatmap/` | GET | Site risk heatmap data |
| `/api/v1/at-risk-subjects/` | GET | High-risk subjects |
| `/api/v1/user-context/` | GET | User context & permissions |

---

## 🎨 UI Features

### Dashboard
- **KPI Cards**: Total enrolled, clean patients, active sites, open queries, DQI score
- **Enrollment Timeline Chart**: Projected vs actual enrollment over time
- **Open Issues Table**: Prioritized list of issues with severity indicators
- **Trial Pulse Summary**: AI-generated insights on trial health
- **Top Filter Bar**: Study selector, region filter, date range
- **AI Assistant Panel**: Slide-out panel with contextual prompts

### Excel Input
- **Spreadsheet View**: Subject data in tabular format
- **Cell Selection**: Click to select cells for details
- **Validation Indicators**: Green (valid), yellow (warning), red (error)
- **Field Details Panel**: Field metadata, validation rules, edit history
- **AI Explanation**: Get AI-powered field explanations

### Predictive AI
- **Risk Heatmap**: Sites × Risk Dimensions matrix with color-coded risks
- **Site Drilldown**: Click a site to see:
  - Why flagged (risk drivers)
  - Evidence (links to reports)
  - Recommended actions
- **AI Assistant**: Contextual questions and answers

---

## 🔒 Role-Based Access Control

### How It Works

1. **Backend Enforcement**: Views use `@login_required` decorator
2. **Frontend Enforcement**: Navigation items hidden based on user's `allowed_modules`
3. **API Protection**: Endpoints return 401/403 for unauthorized access

### Module Visibility by Role

| Module | Admin | Sponsor | CRA | Site User | Data Manager | Safety | Coder |
|--------|-------|---------|------|-----------|--------------|--------|-------|
| dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| sites | ✓ | - | ✓ | - | - | - | - |
| queries | ✓ | - | ✓ | ✓ | ✓ | - | - |
| excel_input | ✓ | - | - | ✓ | ✓ | - | - |
| reports | ✓ | ✓ | ✓ | - | ✓ | ✓ | ✓ |
| predictive_ai | ✓ | ✓ | - | - | - | - | - |
| audit | ✓ | - | ✓ | - | - | - | - |
| safety | ✓ | - | - | - | - | ✓ | - |
| coding | ✓ | - | - | - | - | - | ✓ |
| security_alerts | ✓ | - | - | - | - | - | - |
| admin | ✓ | - | - | - | - | - | - |

---

## 🛠 Management Commands

### seed_auth
Seeds authentication groups and users.

```bash
python manage.py seed_auth
```

Creates:
- 7 Django Groups (Admin, Sponsor, CRA, SiteUser, DataManager, SafetyUser, MedicalCoder)
- 7 Users with predefined credentials

---

## 📁 Key Files Added/Modified

### New Files
- `backend/apps/core/management/commands/seed_auth.py` - Auth seeding command
- `backend/apps/core/auth_helpers.py` - Role/permission utilities
- `backend/apps/core/auth_views.py` - Login/logout views
- `frontend/html/login.html` - Login page
- `frontend/html/dashboard.html` - Main dashboard
- `frontend/html/excel-input.html` - Data entry view
- `frontend/html/predictive-ai.html` - Predictive AI view
- `frontend/html/{sites,queries,reports,audit,safety,coding,security-alerts}.html` - Placeholder pages

### Modified Files
- `backend/config/urls.py` - Added auth routes and protected views
- `backend/config/settings.py` - Added LOGIN_URL settings
- `backend/apps/api/urls.py` - Added risk-heatmap and user-context endpoints
- `backend/apps/api/views.py` - Added new API view functions
- `frontend/html/index.html` - Updated links to new routes

---

## 🎯 Team Zenith - NMIMS Mumbai - NEST 2.0
