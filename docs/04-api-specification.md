# API Specification Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026  
**Base URL**: `https://api.iptc.health/v1`

---

## 1. API Design Principles

| Principle | Implementation |
|---|---|
| **RESTful** | Resource-oriented URLs, standard HTTP methods |
| **JSON:API** | Consistent response envelope with `data`, `meta`, `errors` |
| **Versioned** | URL-based versioning (`/v1/`, `/v2/`) |
| **Authenticated** | OAuth 2.0 Bearer tokens (Azure AD B2C) |
| **Rate Limited** | Per-user and per-organization limits |
| **Paginated** | Cursor-based pagination for list endpoints |
| **HIPAA Audited** | Every request logged with user, action, resource |

---

## 2. Authentication

All API calls require a valid OAuth 2.0 Bearer token.

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Token Claims**:
```json
{
  "sub": "user-uuid",
  "email": "sarah.np@urgentcare.com",
  "role": "NURSE_PRACTITIONER",
  "org_id": "org-uuid",
  "facility_id": "facility-uuid",
  "permissions": ["transfer:create", "transfer:read", "patient:read"],
  "exp": 1717849200
}
```

---

## 3. Response Envelope

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "request_id": "req-uuid",
    "timestamp": "2026-06-08T15:00:00Z"
  }
}
```

### List Response
```json
{
  "data": [ ... ],
  "meta": {
    "total_count": 42,
    "page_size": 20,
    "next_cursor": "eyJpZCI6...",
    "request_id": "req-uuid"
  }
}
```

### Error Response
```json
{
  "errors": [
    {
      "code": "TRANSFER_NOT_FOUND",
      "message": "Transfer request TR-20260608-0001 not found",
      "field": null,
      "details": {}
    }
  ],
  "meta": {
    "request_id": "req-uuid",
    "timestamp": "2026-06-08T15:00:00Z"
  }
}
```

---

## 4. API Endpoints

### 4.1 Transfer Endpoints

#### Create Transfer Request
```http
POST /v1/transfers
```

**Request Body**:
```json
{
  "patient_id": "patient-uuid",
  "urgency": "EMERGENT",
  "reason_for_transfer": "Acute inferior STEMI requiring emergent cardiac catheterization. No cath lab capability at this facility.",
  "requested_specialty": "INTERVENTIONAL_CARDIOLOGY",
  "requested_unit_type": "CCU",
  "preferred_facility_id": "facility-uuid",
  "additional_notes": "Patient is hemodynamically stable on heparin and nitro drips. Family at bedside, aware of transfer."
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "transfer-uuid",
    "transfer_number": "TR-20260608-0001",
    "status": "DRAFT",
    "urgency": "EMERGENT",
    "patient": {
      "id": "patient-uuid",
      "name": "John Doe",
      "dob": "1958-03-15",
      "mrn": "MRN-12345"
    },
    "sending_facility": {
      "id": "facility-uuid",
      "name": "Urgent Care East"
    },
    "receiving_facility": null,
    "reason_for_transfer": "Acute inferior STEMI...",
    "requested_specialty": "INTERVENTIONAL_CARDIOLOGY",
    "clinical_summary": null,
    "compliance_record": null,
    "created_at": "2026-06-08T15:00:00Z"
  }
}
```

---

#### Get Transfer Details
```http
GET /v1/transfers/{transfer_id}
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "transfer-uuid",
    "transfer_number": "TR-20260608-0001",
    "status": "PENDING_REVIEW",
    "urgency": "EMERGENT",
    "patient": {
      "id": "patient-uuid",
      "name": "John Doe",
      "dob": "1958-03-15",
      "mrn": "MRN-12345",
      "insurance": {
        "provider": "Blue Cross",
        "plan": "PPO Gold",
        "member_id": "BC-987654"
      }
    },
    "sending_facility": {
      "id": "facility-uuid",
      "name": "Urgent Care East",
      "phone": "555-0100"
    },
    "receiving_facility": {
      "id": "facility-uuid",
      "name": "Metro General Hospital",
      "phone": "555-0200"
    },
    "clinical_summary": {
      "id": "summary-uuid",
      "situation": "67-year-old male presenting with acute chest pain...",
      "background": "PMH: HTN, DM2, prior MI 2019...",
      "assessment": "Vitals: BP 160/95, HR 110...",
      "recommendation": "Requesting emergent transfer to cath lab..."
    },
    "compliance_record": {
      "id": "compliance-uuid",
      "all_checks_passed": false,
      "checklist": {
        "mse_completed": true,
        "stabilization_attempted": true,
        "md_certification_signed": true,
        "consent_obtained": false,
        "receiving_confirmed": true,
        "transport_appropriate": true,
        "records_sent": false
      }
    },
    "matched_facilities": [
      {
        "rank": 1,
        "facility_name": "Metro General Hospital",
        "score": 92.5,
        "distance_miles": 8.2,
        "status": "SENT"
      }
    ],
    "timeline": [
      {
        "event": "Transfer initiated",
        "timestamp": "2026-06-08T15:00:00Z",
        "by": "Sarah NP"
      },
      {
        "event": "SBAR generated",
        "timestamp": "2026-06-08T15:00:05Z",
        "by": "System"
      }
    ],
    "timestamps": {
      "initiated_at": "2026-06-08T15:00:00Z",
      "first_facility_contacted_at": "2026-06-08T15:00:10Z",
      "accepted_at": null,
      "completed_at": null
    },
    "created_at": "2026-06-08T15:00:00Z",
    "updated_at": "2026-06-08T15:02:30Z"
  }
}
```

---

#### List Transfers
```http
GET /v1/transfers?status=active&urgency=EMERGENT&page_size=20&cursor={cursor}
```

**Query Parameters**:
| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by status. Use `active` for all non-terminal states |
| `urgency` | string | Filter by urgency level |
| `sending_facility_id` | UUID | Filter by sending facility |
| `receiving_facility_id` | UUID | Filter by receiving facility |
| `initiated_by` | UUID | Filter by initiating user |
| `date_from` | ISO 8601 | Filter by creation date (start) |
| `date_to` | ISO 8601 | Filter by creation date (end) |
| `page_size` | integer | Results per page (default: 20, max: 100) |
| `cursor` | string | Cursor for pagination |

---

#### Accept Transfer
```http
POST /v1/transfers/{transfer_id}/accept
```

**Request Body**:
```json
{
  "accepting_physician_notes": "Will accept to CCU. Cath lab team notified. Bed 4 assigned.",
  "assigned_unit": "CCU",
  "assigned_bed": "CCU-04"
}
```

---

#### Decline Transfer
```http
POST /v1/transfers/{transfer_id}/decline
```

**Request Body**:
```json
{
  "reason": "NO_BED_AVAILABLE",
  "notes": "CCU and MICU both at capacity. Suggest trying St. Mary's.",
  "auto_reroute": true
}
```

**Decline Reasons** (enum):
- `NO_BED_AVAILABLE`
- `NO_SPECIALIST_AVAILABLE`
- `SERVICE_NOT_OFFERED`
- `INSURANCE_NOT_ACCEPTED`
- `PATIENT_TOO_UNSTABLE`
- `DIVERT_STATUS`
- `OTHER`

---

#### Update Transfer Status
```http
PATCH /v1/transfers/{transfer_id}/status
```

**Request Body**:
```json
{
  "status": "TRANSPORT_DISPATCHED",
  "notes": "ALS ambulance dispatched, ETA 15 minutes"
}
```

---

#### Get Transfer Timeline
```http
GET /v1/transfers/{transfer_id}/timeline
```

---

### 4.2 Clinical Summary (SBAR) Endpoints

#### Generate SBAR
```http
POST /v1/transfers/{transfer_id}/sbar/generate
```

**Request Body**:
```json
{
  "patient_id": "patient-uuid",
  "additional_context": "Patient also complaining of nausea and diaphoresis. Family requesting transfer to Metro General where their cardiologist practices.",
  "include_sections": ["situation", "background", "assessment", "recommendation"]
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "summary-uuid",
    "version": 1,
    "situation": "This is a transfer request from Urgent Care East for John Doe, a 67-year-old male (DOB: 03/15/1958, MRN: 12345), presenting with acute onset chest pain and diaphoresis for the past 2 hours. ECG shows ST elevation in leads II, III, and aVF consistent with acute inferior STEMI. Patient requires emergent cardiac catheterization not available at this facility.",
    "background": "Past Medical History:\n- Hypertension (controlled)\n- Type 2 Diabetes Mellitus\n- Prior myocardial infarction (2019, s/p PCI to LAD)\n\nCurrent Medications:\n- Metoprolol 50mg PO BID\n- Metformin 1000mg PO BID\n- Aspirin 81mg PO daily\n- Atorvastatin 40mg PO daily\n\nAllergies: No known drug allergies\nCode Status: Full Code",
    "assessment": "Vital Signs (recorded 10:00):\n- BP: 160/95 mmHg\n- HR: 110 bpm (sinus tachycardia)\n- RR: 22 breaths/min\n- SpO2: 94% on 2L NC\n- Temp: 98.6°F\n- Pain: 7/10 substernal chest pain\n\nKey Lab Results:\n- Troponin I: 0.8 ng/mL (CRITICAL HIGH, ref: 0.00-0.04)\n- BMP: Within normal limits\n- CBC: WBC 12.1 (mildly elevated)\n\nECG: ST elevation in leads II, III, aVF; reciprocal changes in I, aVL\n\nCurrent Interventions:\n- Heparin drip 1000 units/hr (bolus 5000 units given)\n- Nitroglycerin drip 10 mcg/min\n- Aspirin 325mg given\n- O2 via NC at 2L/min",
    "recommendation": "Requesting EMERGENT transfer to facility with cardiac catheterization capability for suspected acute inferior STEMI. Recommend ALS transport with cardiac monitoring. Patient is hemodynamically stable but requires time-sensitive intervention. Door-to-balloon time is critical.",
    "generated_by_ai": true,
    "ai_model_version": "gpt-4-2026",
    "requires_review": true,
    "data_sources": ["FHIR:Patient", "FHIR:Observation", "FHIR:Condition", "FHIR:MedicationRequest", "FHIR:DiagnosticReport", "NP_CONTEXT"]
  }
}
```

---

#### Update SBAR (NP Edit)
```http
PUT /v1/transfers/{transfer_id}/sbar/{sbar_id}
```

**Request Body**:
```json
{
  "situation": "Updated situation text...",
  "background": "Updated background...",
  "assessment": "Updated assessment...",
  "recommendation": "Updated recommendation...",
  "reviewed": true
}
```

---

### 4.3 Facility Endpoints

#### Search Facilities
```http
GET /v1/facilities?specialty=INTERVENTIONAL_CARDIOLOGY&lat=40.7128&lng=-74.0060&radius_miles=50
```

**Query Parameters**:
| Parameter | Type | Description |
|---|---|---|
| `specialty` | string | Required specialty |
| `service` | string | Required service (e.g., `CATH_LAB`) |
| `unit_type` | string | Required unit type (e.g., `CCU`) |
| `lat` | decimal | Latitude for distance search |
| `lng` | decimal | Longitude for distance search |
| `radius_miles` | integer | Search radius (default: 50) |
| `insurance_provider` | string | Filter by accepted insurance |
| `has_available_beds` | boolean | Only show facilities with available beds |
| `accepts_transfers` | boolean | Only show facilities accepting transfers |

---

#### Get Facility Details
```http
GET /v1/facilities/{facility_id}
```

---

#### Update Bed Availability
```http
PATCH /v1/facilities/{facility_id}/beds
```

**Request Body**:
```json
{
  "beds": [
    { "unit_type": "CCU", "total_beds": 12, "occupied_beds": 10 },
    { "unit_type": "MICU", "total_beds": 20, "occupied_beds": 18 }
  ]
}
```

---

#### Get Facility Match Recommendations
```http
POST /v1/transfers/{transfer_id}/match
```

**Response**:
```json
{
  "data": [
    {
      "rank": 1,
      "facility": {
        "id": "facility-uuid-1",
        "name": "Metro General Hospital",
        "distance_miles": 8.2,
        "estimated_transport_min": 18
      },
      "scores": {
        "overall": 92.5,
        "specialty": 100,
        "bed_availability": 85,
        "distance": 90,
        "insurance": 100,
        "historical_acceptance": 78
      },
      "details": {
        "has_cath_lab": true,
        "cath_lab_available": true,
        "ccu_beds_available": 2,
        "in_network": true,
        "acceptance_rate_30d": "78%"
      }
    },
    {
      "rank": 2,
      "facility": {
        "id": "facility-uuid-2",
        "name": "University Medical Center",
        "distance_miles": 15.7,
        "estimated_transport_min": 28
      },
      "scores": {
        "overall": 85.3,
        "specialty": 100,
        "bed_availability": 70,
        "distance": 72,
        "insurance": 100,
        "historical_acceptance": 92
      }
    }
  ]
}
```

---

### 4.4 AI Agent Endpoints

#### Chat with AI Agent
```http
POST /v1/agent/chat
```

**Request Body**:
```json
{
  "session_id": "session-uuid",
  "message": "I need to transfer a patient with a STEMI to a facility with a cath lab",
  "context": {
    "transfer_id": "transfer-uuid",
    "patient_id": "patient-uuid"
  }
}
```

**Response** (200 OK):
```json
{
  "data": {
    "session_id": "session-uuid",
    "response": "I can help you with this STEMI transfer. I've pulled the patient's data from the EHR. Let me generate the SBAR summary and find the nearest facilities with available cath labs.\n\nI found 3 facilities within 30 miles with active cath labs:\n1. **Metro General** (8.2 mi) — 2 CCU beds available, cath lab open\n2. **University Medical** (15.7 mi) — 1 CCU bed available, cath lab open\n3. **St. Mary's** (22.1 mi) — 3 CCU beds available, cath lab open\n\nShall I send the transfer request to Metro General?",
    "actions_taken": [
      { "action": "FHIR_DATA_FETCHED", "details": "Patient data retrieved from EHR" },
      { "action": "SBAR_GENERATED", "details": "Clinical summary created (version 1)" },
      { "action": "FACILITIES_MATCHED", "details": "3 facilities matched within 30 miles" }
    ],
    "suggested_actions": [
      { "action": "SEND_TO_FACILITY", "label": "Send to Metro General", "facility_id": "facility-uuid-1" },
      { "action": "SEND_TO_FACILITY", "label": "Send to University Medical", "facility_id": "facility-uuid-2" },
      { "action": "EDIT_SBAR", "label": "Review/Edit SBAR first" }
    ]
  }
}
```

---

### 4.5 Compliance Endpoints

#### Get Compliance Status
```http
GET /v1/transfers/{transfer_id}/compliance
```

---

#### Update Compliance Checklist Item
```http
PATCH /v1/transfers/{transfer_id}/compliance
```

**Request Body**:
```json
{
  "field": "consent_obtained",
  "value": true,
  "consent_signer_name": "John Doe",
  "consent_signer_relationship": "PATIENT",
  "consent_signed_at": "2026-06-08T15:10:00Z"
}
```

---

### 4.6 Transport Endpoints

#### Request Transport
```http
POST /v1/transfers/{transfer_id}/transport
```

**Request Body**:
```json
{
  "transport_level": "ALS",
  "preferred_provider": "Metro EMS",
  "special_requirements": ["cardiac_monitor", "12_lead_ecg", "iv_pump"],
  "pickup_notes": "Patient on 2nd floor, room 204. Elevator access required."
}
```

---

#### Update Transport Status
```http
PATCH /v1/transfers/{transfer_id}/transport/status
```

**Request Body**:
```json
{
  "status": "TRANSPORTING",
  "gps_lat": 40.7489,
  "gps_lng": -73.9680,
  "notes": "Patient stable during transport. Vitals unchanged."
}
```

---

### 4.7 Patient Endpoints

#### Search Patient (via FHIR)
```http
GET /v1/patients/search?mrn=12345&facility_id={facility_id}
```

---

#### Get Patient Details
```http
GET /v1/patients/{patient_id}
```

---

### 4.8 Analytics Endpoints

#### Transfer Metrics
```http
GET /v1/analytics/transfers?facility_id={id}&date_from=2026-01-01&date_to=2026-06-30
```

**Response**:
```json
{
  "data": {
    "period": { "from": "2026-01-01", "to": "2026-06-30" },
    "total_transfers": 1247,
    "by_status": {
      "completed": 1089,
      "cancelled": 58,
      "declined": 100
    },
    "by_urgency": {
      "emergent": 312,
      "urgent": 587,
      "routine": 348
    },
    "avg_times": {
      "initiation_to_acceptance_min": 12.4,
      "acceptance_to_departure_min": 28.7,
      "door_to_door_min": 68.2
    },
    "acceptance_rate": 0.916,
    "top_decline_reasons": [
      { "reason": "NO_BED_AVAILABLE", "count": 52 },
      { "reason": "NO_SPECIALIST_AVAILABLE", "count": 28 }
    ]
  }
}
```

---

### 4.9 Notification Endpoints

#### Get User Notifications
```http
GET /v1/notifications?unread_only=true
```

---

#### Mark Notification Read
```http
PATCH /v1/notifications/{notification_id}/read
```

---

## 5. WebSocket Events (Real-time Updates)

**Connection**: `wss://api.iptc.health/v1/ws?token={jwt}`

### Events Published

| Event | Payload | Subscribers |
|---|---|---|
| `transfer.status_changed` | `{ transfer_id, old_status, new_status, timestamp }` | All parties on transfer |
| `transfer.new_request` | `{ transfer_id, urgency, sending_facility, specialty }` | Receiving facility coordinators |
| `transfer.accepted` | `{ transfer_id, receiving_facility, accepting_md }` | Sending NP |
| `transfer.declined` | `{ transfer_id, reason, next_facility }` | Sending NP |
| `transport.status_changed` | `{ transfer_id, transport_status, gps, eta }` | All parties on transfer |
| `bed.availability_changed` | `{ facility_id, unit_type, available_beds }` | Facility matcher service |
| `compliance.item_updated` | `{ transfer_id, field, value, all_passed }` | Transfer coordinators |

---

## 6. Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `AUTH_REQUIRED` | 401 | Missing or invalid authentication token |
| `FORBIDDEN` | 403 | User lacks permission for this action |
| `TRANSFER_NOT_FOUND` | 404 | Transfer request does not exist |
| `PATIENT_NOT_FOUND` | 404 | Patient not found in system or EHR |
| `FACILITY_NOT_FOUND` | 404 | Facility does not exist |
| `INVALID_STATUS_TRANSITION` | 422 | Invalid transfer status change |
| `COMPLIANCE_INCOMPLETE` | 422 | Cannot dispatch transport — compliance checks not passed |
| `SBAR_GENERATION_FAILED` | 500 | AI failed to generate SBAR summary |
| `FHIR_CONNECTION_FAILED` | 502 | Could not connect to EHR FHIR server |
| `RATE_LIMITED` | 429 | Too many requests |

---

## 7. Rate Limits

| Tier | Limit | Scope |
|---|---|---|
| **Standard** | 100 requests/min | Per user |
| **AI Agent** | 20 requests/min | Per user (LLM calls are expensive) |
| **Webhook** | 1000 requests/min | Per organization |
| **Analytics** | 10 requests/min | Per user (heavy queries) |
