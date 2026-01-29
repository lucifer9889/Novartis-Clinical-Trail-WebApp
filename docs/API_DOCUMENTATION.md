# API Documentation - Clinical Trial Control Tower

## Overview
RESTful API endpoints for the Clinical Trial Control Tower.

**Base URL**: `http://localhost:8000/api/v1/`

**Authentication**: JWT Bearer Token

---

## Authentication

### Obtain Token
```http
POST /api/token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password"
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Core Endpoints

### Studies

#### List Studies
```http
GET /api/v1/studies/
Authorization: Bearer {access_token}
```

#### Get Study Detail
```http
GET /api/v1/studies/{study_id}/
Authorization: Bearer {access_token}
```

### Sites

#### List Sites
```http
GET /api/v1/sites/
Authorization: Bearer {access_token}
```

#### Get Site Detail with DQI
```http
GET /api/v1/sites/{site_id}/dqi/
Authorization: Bearer {access_token}
```

---

## Monitoring Endpoints

### Queries

#### List Queries
```http
GET /api/v1/monitoring/queries/
Authorization: Bearer {access_token}

Query Parameters:
- status: open|closed|answered
- action_owner: CRA|Site|DM
- subject_id: {subject_id}
```

---

## Metrics Endpoints

### DQI Scores

#### Get Subject DQI
```http
GET /api/v1/metrics/dqi/subject/{subject_id}/
Authorization: Bearer {access_token}
```

#### Get Site DQI
```http
GET /api/v1/metrics/dqi/site/{site_id}/
Authorization: Bearer {access_token}
```

### Clean Patient Status

#### List Clean Patients
```http
GET /api/v1/metrics/clean-patients/
Authorization: Bearer {access_token}
```

---

## AI Endpoints (Phase 5/6)

### GenAI Assistance

#### Query Response Suggestion
```http
POST /api/v1/ai/query-assist/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query_id": "Q-001",
  "query_text": "Missing visit date",
  "context": {...}
}
```

### Predictive Models

#### Predict Site Risk
```http
POST /api/v1/ai/predict/site-risk/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "site_id": "Site_101"
}
```

---

## Blockchain Endpoints (Phase 7)

### Verify Data Integrity
```http
GET /api/v1/blockchain/verify/{entity_type}/{entity_id}/
Authorization: Bearer {access_token}
```

### Get Audit Trail
```http
GET /api/v1/blockchain/audit-trail/{entity_id}/
Authorization: Bearer {access_token}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error description",
  "status_code": 400
}
```

### Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

**Version**: 1.0.0
**Last Updated**: Phase 0
