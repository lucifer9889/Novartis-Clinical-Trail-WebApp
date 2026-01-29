# Database Schema - Clinical Trial Control Tower

## Overview
The database consists of 23 tables organized in three layers:
1. **Dimensions** (6 tables) - Core entities
2. **Facts** (12 tables) - Transactional data
3. **Marts** (5 tables) - Derived metrics

---

## Dimensions

### DIM_STUDY
Represents clinical trials.

| Column | Type | Description |
|--------|------|-------------|
| study_id | VARCHAR(100) PK | Unique study identifier |
| study_name | VARCHAR(500) | Study name |
| region | VARCHAR(100) | Geographic region |
| status | VARCHAR(50) | Active/Completed/On-Hold |
| snapshot_date | DATE | Data snapshot date |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### DIM_COUNTRY
Countries participating in studies.

| Column | Type | Description |
|--------|------|-------------|
| country_code | VARCHAR(10) PK | Country code |
| country_name | VARCHAR(200) | Country name |
| region | VARCHAR(100) | Geographic region |
| study_id | FK -> Study | Parent study |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### DIM_SITE
Clinical trial sites.

| Column | Type | Description |
|--------|------|-------------|
| site_id | VARCHAR(100) PK | Unique site identifier |
| study_id | FK -> Study | Parent study |
| country_code | FK -> Country | Site country |
| site_number | VARCHAR(50) | Site number |
| site_name | VARCHAR(500) | Site name |
| status | VARCHAR(50) | Active/Inactive |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### DIM_SUBJECT
Study participants.

| Column | Type | Description |
|--------|------|-------------|
| subject_id | VARCHAR(100) PK | Unique subject identifier |
| study_id | FK -> Study | Parent study |
| site_id | FK -> Site | Subject's site |
| subject_external_id | VARCHAR(100) | External ID |
| subject_status | VARCHAR(50) | Enrolled/Completed/Withdrawn |
| enrollment_date | DATE | Date enrolled |
| latest_visit | VARCHAR(200) | Most recent visit |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### DIM_VISIT
Subject visits.

| Column | Type | Description |
|--------|------|-------------|
| visit_id | INTEGER PK AUTO | Unique visit identifier |
| subject_id | FK -> Subject | Subject |
| visit_name | VARCHAR(200) | Visit name |
| visit_date | DATE | Actual visit date |
| projected_date | DATE | Projected visit date |
| status | VARCHAR(50) | Scheduled/Completed/Missed |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### DIM_FORM_PAGE
CRF forms and pages.

| Column | Type | Description |
|--------|------|-------------|
| page_id | INTEGER PK AUTO | Unique page identifier |
| visit_id | FK -> Visit | Parent visit |
| folder_name | VARCHAR(200) | Folder name |
| form_name | VARCHAR(200) | Form name |
| form_oid | VARCHAR(200) | Form OID |
| page_name | VARCHAR(200) | Page name |
| status | VARCHAR(50) | Draft/Submitted/Locked/Signed |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

---

## Facts

### FACT_QUERY_EVENT
Data queries raised during monitoring.

| Column | Type | Description |
|--------|------|-------------|
| query_id | INTEGER PK AUTO | Unique query identifier |
| subject_id | FK -> Subject | Subject |
| page_id | FK -> FormPage | Related form page |
| folder_name | VARCHAR(200) | Folder name |
| form_name | VARCHAR(200) | Form name |
| field_oid | VARCHAR(200) | Field OID |
| log_number | VARCHAR(100) | Query log number |
| query_status | VARCHAR(50) | Open/Answered/Closed |
| action_owner | VARCHAR(100) | CRA/Site/DM |
| query_open_date | DATE | Date query opened |
| query_response_date | DATE | Date responded |
| days_since_open | INTEGER | Days open |
| created_at | TIMESTAMP | Record creation time |

### FACT_MISSING_VISIT
Projected visits not yet occurred.

| Column | Type | Description |
|--------|------|-------------|
| missing_visit_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| visit_name | VARCHAR(200) | Visit name |
| projected_date | DATE | Expected date |
| days_outstanding | INTEGER | Days overdue |
| created_at | TIMESTAMP | Record creation time |

### FACT_MISSING_PAGE
Missing CRF pages.

| Column | Type | Description |
|--------|------|-------------|
| missing_page_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| visit_name | VARCHAR(200) | Visit name |
| page_name | VARCHAR(200) | Page name |
| form_details | VARCHAR(500) | Form details |
| visit_date | DATE | Visit date |
| days_missing | INTEGER | Days missing |
| created_at | TIMESTAMP | Record creation time |

### FACT_SDV
Source Data Verification records.

| Column | Type | Description |
|--------|------|-------------|
| sdv_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| visit_name | VARCHAR(200) | Visit name |
| form_name | VARCHAR(200) | Form name |
| sdv_status | VARCHAR(50) | Verified/Not Verified |
| verified_date | DATE | Date verified |
| created_at | TIMESTAMP | Record creation time |

### FACT_PI_SIGNATURE
Principal Investigator signature records.

| Column | Type | Description |
|--------|------|-------------|
| pi_signature_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| visit_name | VARCHAR(200) | Visit name |
| form_name | VARCHAR(200) | Form name |
| signature_status | VARCHAR(50) | Signed/Not Signed |
| signed_date | DATE | Date signed |
| created_at | TIMESTAMP | Record creation time |

### FACT_PROTOCOL_DEVIATION
Protocol deviation records.

| Column | Type | Description |
|--------|------|-------------|
| deviation_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| deviation_type | VARCHAR(200) | Deviation type |
| severity | VARCHAR(50) | Major/Minor |
| description | TEXT | Description |
| deviation_date | DATE | Date of deviation |
| created_at | TIMESTAMP | Record creation time |

### FACT_NON_CONFORMANT
Non-conformant records.

| Column | Type | Description |
|--------|------|-------------|
| non_conformant_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| form_name | VARCHAR(200) | Form name |
| field_name | VARCHAR(200) | Field name |
| reason | TEXT | Reason for non-conformance |
| created_at | TIMESTAMP | Record creation time |

### FACT_LAB_ISSUE
Laboratory data issues.

| Column | Type | Description |
|--------|------|-------------|
| lab_issue_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| lab_test | VARCHAR(200) | Lab test name |
| issue_type | VARCHAR(200) | Issue type |
| severity | VARCHAR(50) | High/Medium/Low |
| created_at | TIMESTAMP | Record creation time |

### FACT_SAE_DISCREPANCY
Serious Adverse Event discrepancy records.

| Column | Type | Description |
|--------|------|-------------|
| sae_discrepancy_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| sae_number | VARCHAR(100) | SAE number |
| discrepancy_type | VARCHAR(200) | Discrepancy type |
| severity | VARCHAR(50) | Critical/Major/Minor |
| description | TEXT | Description |
| created_at | TIMESTAMP | Record creation time |

### FACT_CODING_ITEM
Medical coding items (MedDRA/WHODD).

| Column | Type | Description |
|--------|------|-------------|
| coding_item_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| coding_type | VARCHAR(50) | MedDRA/WHODD |
| verbatim_term | VARCHAR(500) | Verbatim term |
| coded_term | VARCHAR(500) | Coded term |
| coding_status | VARCHAR(50) | Coded/Uncoded/Review |
| created_at | TIMESTAMP | Record creation time |

### FACT_EDRR_OPEN_ISSUE
EDRR open issue records.

| Column | Type | Description |
|--------|------|-------------|
| edrr_issue_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| issue_type | VARCHAR(200) | Issue type |
| description | TEXT | Description |
| status | VARCHAR(50) | Open/Resolved |
| opened_date | DATE | Date opened |
| created_at | TIMESTAMP | Record creation time |

### FACT_INACTIVATED_RECORD
Inactivated record tracking.

| Column | Type | Description |
|--------|------|-------------|
| inactivated_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject | Subject |
| record_type | VARCHAR(200) | Record type |
| reason | TEXT | Inactivation reason |
| inactivated_date | DATE | Date inactivated |
| created_at | TIMESTAMP | Record creation time |

---

## Marts

### MART_DQI_WEIGHT_CONFIG
DQI weight configuration.

| Column | Type | Description |
|--------|------|-------------|
| weight_id | INTEGER PK AUTO | Identifier |
| metric_name | VARCHAR(100) UNIQUE | Metric name |
| weight | DECIMAL(5,4) | Weight value (0-1) |
| description | TEXT | Weight description |
| is_active | BOOLEAN | Active flag |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### MART_CLEAN_PATIENT_STATUS
Clean patient status computation.

| Column | Type | Description |
|--------|------|-------------|
| clean_status_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject (UNIQUE) | Subject |
| is_clean | BOOLEAN | Clean status flag |
| has_missing_visits | BOOLEAN | Has missing visits |
| missing_visits_count | INTEGER | Count of missing visits |
| has_open_queries | BOOLEAN | Has open queries |
| open_queries_count | INTEGER | Count of open queries |
| has_missing_pages | BOOLEAN | Has missing pages |
| missing_pages_count | INTEGER | Count of missing pages |
| has_non_conformant | BOOLEAN | Has non-conformant records |
| non_conformant_count | INTEGER | Count of non-conformant |
| sdv_completion_pct | DECIMAL(5,2) | SDV completion percentage |
| pi_signature_pct | DECIMAL(5,2) | PI signature percentage |
| has_sae_discrepancies | BOOLEAN | Has SAE discrepancies |
| sae_discrepancy_count | INTEGER | Count of SAE discrepancies |
| blockers_json | TEXT | JSON list of blockers |
| last_computed | TIMESTAMP | Last computation time |

### MART_DQI_SCORE_SUBJECT
Subject-level DQI scores.

| Column | Type | Description |
|--------|------|-------------|
| dqi_subject_id | INTEGER PK AUTO | Identifier |
| subject_id | FK -> Subject (UNIQUE) | Subject |
| sae_unresolved_score | DECIMAL(5,2) | SAE component score |
| missing_visits_score | DECIMAL(5,2) | Missing visits score |
| missing_pages_score | DECIMAL(5,2) | Missing pages score |
| open_queries_score | DECIMAL(5,2) | Open queries score |
| overdue_queries_score | DECIMAL(5,2) | Overdue queries score |
| non_conformant_score | DECIMAL(5,2) | Non-conformant score |
| sdv_incomplete_score | DECIMAL(5,2) | SDV incomplete score |
| unsigned_casebooks_score | DECIMAL(5,2) | Unsigned casebooks score |
| lab_issues_score | DECIMAL(5,2) | Lab issues score |
| coding_issues_score | DECIMAL(5,2) | Coding issues score |
| edrr_issues_score | DECIMAL(5,2) | EDRR issues score |
| composite_dqi_score | DECIMAL(5,2) | Weighted DQI (0-100) |
| risk_band | VARCHAR(20) | Low/Medium/High/Critical |
| last_computed | TIMESTAMP | Last computation time |

### MART_DQI_SCORE_SITE
Site-level DQI scores.

| Column | Type | Description |
|--------|------|-------------|
| dqi_site_id | INTEGER PK AUTO | Identifier |
| site_id | FK -> Site (UNIQUE) | Site |
| avg_dqi_score | DECIMAL(5,2) | Average DQI score |
| min_dqi_score | DECIMAL(5,2) | Minimum DQI score |
| max_dqi_score | DECIMAL(5,2) | Maximum DQI score |
| total_subjects | INTEGER | Total subjects |
| clean_subjects | INTEGER | Clean subjects count |
| risk_band | VARCHAR(20) | Low/Medium/High/Critical |
| last_computed | TIMESTAMP | Last computation time |

### MART_DQI_SCORE_STUDY
Study-level DQI scores.

| Column | Type | Description |
|--------|------|-------------|
| dqi_study_id | INTEGER PK AUTO | Identifier |
| study_id | FK -> Study (UNIQUE) | Study |
| avg_dqi_score | DECIMAL(5,2) | Average DQI score |
| total_sites | INTEGER | Total sites |
| total_subjects | INTEGER | Total subjects |
| clean_subjects | INTEGER | Clean subjects count |
| clean_percentage | DECIMAL(5,2) | Clean patient percentage |
| risk_band | VARCHAR(20) | Low/Medium/High/Critical |
| last_computed | TIMESTAMP | Last computation time |

---

**Version**: 1.0.0
**Last Updated**: Phase 0
