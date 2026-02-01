# Clinical Trial Control Tower (CTCT)

Enterprise blockchain-enabled clinical trial management system with AI-powered insights.

## Project Overview

The Clinical Trial Control Tower integrates operational and clinical trial data from multiple sources into a unified, role-based platform. It provides:

- **Data Quality Index (DQI)** scoring
- **Clean Patient Status** computation
- **Role-based dashboards** (CRA, DQT, Site, Leadership)
- **GenAI assistance** for query resolution and analysis
- **Predictive AI models** for risk assessment
- **Blockchain-backed** audit trails and data integrity

## Features

### Phase 1-11 Implementation
- Phase 0: Project Setup
- Phase 1: Frontend Development
- Phase 2: Backend Logic
- Phase 3: Database Setup
- Phase 4: Frontend-Backend Connection
- Phase 5: GenAI Integration
- Phase 6: Predictive AI Models
- Phase 7: Blockchain Implementation
- Phase 8: Module Integration
- Phase 9: Authentication System
- Phase 10: Auth Integration
- Phase 11: Encryption Layer

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for blockchain)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/clinical-trial-portal.git
cd clinical-trial-portal
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run migrations**
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Initialize DQI weights**
```bash
python manage.py init_dqi_weights
```

8. **Load sample data**
```bash
python manage.py import_study_data --study_id=Study_1 --data_dir=../data/study_1/
```

9. **Compute metrics**
```bash
python manage.py compute_metrics
```

10. **Run development server**
```bash
python manage.py runserver
```

11. **Access the application**
- Admin Panel: http://localhost:8000/admin/
- CRA Dashboard: http://localhost:8000/dashboards/cra/
- DQT Dashboard: http://localhost:8000/dashboards/dqt/
- Leadership Dashboard: http://localhost:8000/dashboards/leadership/

## Project Structure

```
clinical-trial-portal/
├── backend/           # Django backend application
├── frontend/          # Static frontend (HTML/CSS/JS)
├── ai_models/         # Machine learning models
├── blockchain/        # Smart contracts and scripts
├── data/              # Data storage (not committed)
├── docs/              # Documentation
└── tests/             # Test suites
```

## Database Schema

The system uses 23 tables organized in three layers:

**Dimensions (6 tables)**:
- Study, Country, Site, Subject, Visit, FormPage

**Facts (12 tables)**:
- Query, SDV, PISignature, ProtocolDeviation, NonConformant
- MissingVisit, MissingPage, LabIssue, SAEDiscrepancy
- CodingItem, EDRROpenIssue, InactivatedRecord

**Marts (5 tables)**:
- DQIWeightConfig, CleanPatientStatus
- DQIScoreSubject, DQIScoreSite, DQIScoreStudy

See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) for detailed schema.

## User Roles

1. **CRA** (Clinical Research Associate) - Site monitoring
2. **DQT** (Data Quality Team) - Quality oversight
3. **Site Staff** - Data entry and resolution
4. **Leadership** - Executive dashboards
5. **Admin** - System administration

## AI Features

### GenAI (Phase 5)
- Query response suggestions
- Protocol deviation analysis
- SAE report generation
- DQI score explanations

### Predictive AI (Phase 6)
- Enrollment forecasting (LSTM)
- Site risk prediction (CNN)
- Query likelihood prediction (RNN)
- Patient dropout prediction (PNN)

## AI API Keys Setup

The Clinical Trial Control Tower uses AI services for intelligent suggestions and analysis. AI features will gracefully degrade to rule-based fallbacks if API keys are not configured.

### Quick Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Get your Anthropic API key:**
   - Go to [https://console.anthropic.com/](https://console.anthropic.com/)
   - Create an account or sign in
   - Navigate to API Keys and create a new key
   - Copy the key (format: `sk-ant-api03-...`)

3. **Set the key in your `.env` file:**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
   ```

4. **Restart the development server**

### Setting Environment Variables

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**For production deployments**, use your platform's secrets management:
- Docker: Use `--env-file` or `-e` flags
- Kubernetes: Use Secrets
- AWS: Use Secrets Manager or Parameter Store
- Azure: Use Key Vault

### Required Keys by Feature

| Feature | Required Key | Fallback Behavior |
|---------|-------------|-------------------|
| GenAI Suggested Actions | `ANTHROPIC_API_KEY` | Rule-based priority actions |
| Query Response Suggestions | `ANTHROPIC_API_KEY` | "Please review manually" message |
| Subject Risk Assessment | `ANTHROPIC_API_KEY` | Basic DQI-based assessment |
| Predictive AI (Phase 6) | None (local models) | Always available |

### Security Best Practices

⚠️ **IMPORTANT: Never commit real API keys to version control.**

- `.env` files are already in `.gitignore`
- Use `.env.example` as a template (no real secrets)
- Rotate keys immediately if accidentally exposed
- Use different keys for development and production
- Set appropriate API key permissions/rate limits in provider console

### Verifying AI Configuration

Check if AI is properly configured by calling:
```
GET /api/v1/genai/suggested-actions/
```

If AI is disabled, the response will include:
```json
{
  "ai_disabled": true,
  "message": "Set ANTHROPIC_API_KEY in .env to enable AI features."
}
```

## Blockchain Integration

- Data fingerprinting (SHA-256 hashes)
- Immutable audit trails
- Approval/signature recording
- Data integrity verification

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_models.py
```

## Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [User Guide](docs/USER_GUIDE.md)

## Security

- HTTPS encryption (TLS 1.3)
- Database field-level encryption
- Role-based access control (RBAC)
- API token encryption
- Blockchain audit trails
- Session security
- CSRF protection

## Contributing

This is a hackathon project developed by Team Zenith for NEST 2.0 Semi-Finals.

## License

Proprietary - Novartis NEST 2.0 Hackathon

## Team

**Team Zenith** - NMIMS Mumbai
- [Team Member Names]

## Support

For issues or questions:
- Email: support@ctct.local
- Documentation: /docs/

## Acknowledgments

- Novartis for the NEST 2.0 hackathon
- Anthropic for Claude AI
- Open source community

---

**Version**: 1.0.0
**Last Updated**: January 2026
**Status**: In Development (Phase 0 Complete)
