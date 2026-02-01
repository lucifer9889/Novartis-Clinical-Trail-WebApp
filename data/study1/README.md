# Study-1 Data Files

This directory contains the real Study-1 Excel data files for the Clinical Trial Control Tower.

## Files

| File Name | Description | Rows |
|-----------|-------------|------|
| Study 1_CPID_EDC_Metrics_URSV2.0_14 NOV 2025_updated.xlsx | Main EDC metrics with multiple sheets | Multiple |
| Study 1_Compiled_EDRR_updated.xlsx | EDRR Open Issues Summary | 28 |
| Study 1_eSAE Dashboard_Standard DM_Safety Report_updated.xlsx | SAE discrepancies (DM + Safety) | 1274 |
| Study 1_GlobalCodingReport_MedDRA_updated.xlsx | MedDRA coding items | 1513 |
| Study 1_GlobalCodingReport_WHODD_updated.xlsx | WHODD coding items | 1573 |
| Study 1_Inactivated Forms, Folders and Records Report_updated.xlsx | Inactivated records | 5607 |
| Study 1_Missing_Lab_Name_and_Missing_Ranges_14NOV2025_updated.xlsx | Lab issues | 128 |
| Study 1_Missing_Pages_Report_URSV3.0_14 NOV 2025_updated.xlsx | Missing pages | 193 |
| Study 1_Visit Projection Tracker_14NOV2025_updated.xlsx | Missing visits | 15 |

## CPID_EDC_Metrics Sheets

- Subject Level Metrics (102 rows)
- Region_Country View
- Query Report - Cumulative (574 rows)
- Query Report - Site Action (388 rows)
- Query Report - CRA Action (26 rows)
- Non conformant (12 rows)
- PI Signature Report (1167 rows)
- SDV (7351 rows)
- Protocol Deviation (15 rows)
- CRF Freeze/UnFreeze/Locked/UnLocked

## Loading Data

```bash
# Dry-run (parse only, no writes)
python manage.py load_study1 --data_dir ../data/study1 --dry-run

# Wipe and reload
python manage.py load_study1 --data_dir ../data/study1 --wipe

# Idempotent upsert
python manage.py load_study1 --data_dir ../data/study1

# Compute metrics after loading
python manage.py compute_metrics --study_id Study_1
```

## Expected Counts After Load

- Countries: 11 (AUT, CHN, CZE, DEU, ESP, FRA, GBR, ISR, KOR, SGP, USA)
- Sites: 27
- Subjects: 99
- Queries: ~988
- SDV Records: ~99
- PI Signatures: ~99
- SAE Discrepancies: ~700
- Lab Issues: ~128
- Coding Items: ~3000+
- Inactivated Records: ~5000+
