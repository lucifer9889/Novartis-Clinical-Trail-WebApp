# Schema Rebuild Summary

## Overview

The Clinical Trial Control Tower database schema has been rebuilt to match the ER diagram requirements. All migrations have been created and applied successfully.

---

## ER Diagram Tables → Django Models Mapping

### Core Dimensions (apps/core/models.py)

| ER Table | Django Model | Table Name | Status |
|----------|--------------|------------|--------|
| Study | `Study` | `dim_study` | ✅ Complete |
| Country | `Country` | `dim_country` | ✅ Complete |
| Site | `Site` | `dim_site` | ✅ Complete |
| Subject | `Subject` | `dim_subject` | ✅ Complete |
| Visit | `Visit` | `dim_visit` | ✅ Complete |
| FormPage | `FormPage` | `dim_form_page` | ✅ Complete |

### Monitoring / Quality Domain (apps/monitoring/models.py)

| ER Table | Django Model | Table Name | Status |
|----------|--------------|------------|--------|
| OpenIssueSummary | `OpenIssueSummary` | `fact_open_issue_summary` | ✅ **New** |
| CRFEvent | `CRFEvent` | `fact_crf_event` | ✅ **New** |
| Query | `Query` | `fact_query_event` | ✅ Updated |
| SDVStatus | `SDVStatus` | `fact_sdv_status` | ✅ Complete |
| PISignatureStatus | `PISignatureStatus` | `fact_pi_signature_status` | ✅ Complete |
| ProtocolDeviation | `ProtocolDeviation` | `fact_protocol_deviation` | ✅ Complete |
| NonConformant | `NonConformantEvent` | `fact_nonconformant_event` | ✅ Complete |
| MissingVisit | `MissingVisit` | `fact_missing_visit` | ✅ Updated |
| MissingPage | `MissingPage` | `fact_missing_page` | ✅ Updated |

### Safety Domain (apps/safety/models.py)

| ER Table | Django Model | Table Name | Status |
|----------|--------------|------------|--------|
| SAEDiscrepancy | `SAEDiscrepancy` | `fact_sae_discrepancy` | ✅ Updated |
| LabIssue | `LabIssue` | `fact_lab_issue` | ✅ Updated |

### Medical Coding (apps/medical_coding/models.py)

| ER Table | Django Model | Table Name | Status |
|----------|--------------|------------|--------|
| CodingItem | `CodingItem` | `fact_coding_item` | ✅ Complete |
| InactivatedRecord | `InactivatedRecord` | `fact_inactivated_record` | ✅ Updated |
| EDRROpenIssue | `EDRROpenIssue` | `fact_edrr_open_issue` | ✅ Complete |

### Metrics/Marts (apps/metrics/models.py)

| Mart Table | Django Model | Table Name | Status |
|------------|--------------|------------|--------|
| DQIWeightConfig | `DQIWeightConfig` | `dqi_weight_config` | ✅ Complete |
| CleanPatientStatus | `CleanPatientStatus` | `mart_clean_patient_status` | ✅ Complete |
| DQIScoreSubject | `DQIScoreSubject` | `mart_dqi_score_subject` | ✅ Complete |
| DQIScoreSite | `DQIScoreSite` | `mart_dqi_score_site` | ✅ Complete |
| DQIScoreStudy | `DQIScoreStudy` | `mart_dqi_score_study` | ✅ Complete |

---

## Key Fields Added (per ER Requirements)

### Query Model (monitoring)
- `study` FK (nullable)
- `site` FK (nullable)
- `visit` FK (nullable)
- `region` (denormalized)
- `country_code` (denormalized)
- `site_number` (denormalized)
- `query_iters` (query iterations)
- `query_repair_date` (repair date)

### MissingVisit / MissingPage Models
- `study` FK (nullable)
- `site` FK (nullable)
- `is_resolved` (boolean flag)

### SAEDiscrepancy Model
- `resolution_status` (choices: Open/Pending/Resolved/Closed)

### LabIssue Model
- `study` FK (nullable)
- `site` FK (nullable)

### InactivatedRecord Model
- `study` FK (nullable)
- `site` FK (nullable)
- `record_label` field

---

## Indexes Added

### Query
- `(study, query_status)`
- `(site, query_status)`
- `(subject, query_status)`
- `(query_status, action_owner)`
- `(action_owner, query_open_date)`

### MissingVisit / MissingPage
- `(site, is_resolved)`

### SAEDiscrepancy
- `(site, resolution_status)`

### OpenIssueSummary
- `(study, total_open_issue_count)`

### CRFEvent
- `(study, event_type)`
- `(subject, event_time)`

---

## Management Commands

### 1. `python manage.py seed_auth`
Creates Django Groups and Users for authentication:
- Groups: Admin, Sponsor, CRA, SiteUser, DataManager, SafetyUser, MedicalCoder
- Users: admin, Aarav, Priya, Rohit, Neha, Vikram, Ananya

### 2. `python manage.py seed_reference_data`
Creates Study 1, Study 2, and associated countries (new command).

### 3. `python manage.py seed_smoke_data`
Creates minimal complete data hierarchy for UI testing (new command).

### 4. `python manage.py load_study`
Existing command for loading Excel data:
```bash
python manage.py load_study --study "Study 1" --data_dir ./data/study1
```

---

## Commands to Rebuild Schema

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Check for model issues
python manage.py check

# Generate migrations (if models changed)
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Seed auth data
python manage.py seed_auth

# Seed reference data (studies and countries)
python manage.py seed_reference_data

# Optional: Seed smoke test data
python manage.py seed_smoke_data

# Start server
python manage.py runserver
```

---

## Files Created/Modified

### New Files
- `backend/apps/monitoring/models.py` - Added `OpenIssueSummary`, `CRFEvent`
- `backend/apps/core/admin.py` - Admin registrations
- `backend/apps/monitoring/admin.py` - Admin registrations
- `backend/apps/safety/admin.py` - Admin registrations
- `backend/apps/metrics/admin.py` - Admin registrations
- `backend/apps/medical_coding/admin.py` - Admin registrations
- `backend/apps/core/management/commands/seed_reference_data.py`
- `backend/apps/core/management/commands/seed_smoke_data.py`

### Modified Files
- `backend/apps/monitoring/models.py` - Added fields to Query, MissingVisit, MissingPage
- `backend/apps/safety/models.py` - Added fields to SAEDiscrepancy, LabIssue
- `backend/apps/medical_coding/models.py` - Added fields to InactivatedRecord

### New Migrations
- `apps/monitoring/migrations/0002_*.py` - OpenIssueSummary, CRFEvent, Query updates, MissingVisit/Page updates
- `apps/safety/migrations/0002_*.py` - LabIssue/SAEDiscrepancy updates
- `apps/medical_coding/migrations/0002_*.py` - InactivatedRecord updates

---

## Verification

### Entity Counts (after smoke data)
- Studies: 3 (Study_1, Study_2, Smoke_Test_Study)
- Countries: 21
- Sites: 28
- Subjects: 100
- Visits: 9
- FormPages: 9
- Queries: 482
- OpenIssueSummary: 1
- DQIScoreSubject: 100
- CleanPatientStatus: 100

### Admin Access
All models are registered in Django Admin:
- http://127.0.0.1:8000/admin/

---

## Next Steps

1. **Load Full Study Data**
   ```bash
   python manage.py load_study --study "Study 1" --data_dir ../data/study1
   python manage.py load_study --study "Study 2" --data_dir ../data/study2
   ```

2. **Compute Metrics**
   ```bash
   python manage.py compute_metrics
   ```

3. **Initialize DQI Weights**
   ```bash
   python manage.py init_dqi_weights
   ```
