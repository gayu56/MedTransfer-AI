# Data Models Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026

---

## 1. Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   User       │       │   Organization   │       │    Facility      │
│──────────────│       │──────────────────│       │──────────────────│
│ id           │──┐    │ id               │──┐    │ id               │
│ email        │  │    │ name             │  │    │ organization_id  │──▶ Organization
│ name         │  │    │ type             │  │    │ name             │
│ role         │  │    │ npi              │  │    │ npi              │
│ phone        │  │    │ address          │  │    │ address          │
│ org_id       │──┘──▶ │ ehr_system       │  │    │ latitude         │
│ facility_id  │──────▶│                  │  │    │ longitude        │
│              │       └──────────────────┘  │    │ phone            │
└──────────────┘                             │    │ transfer_phone   │
                                             │    │ ehr_system       │
                                             │    │ capabilities[]   │
┌──────────────────┐                         │    │ bed_counts{}     │
│   Patient        │                         │    └──────────────────┘
│──────────────────│                         │             │
│ id               │                         │             │
│ mrn              │                         │    ┌────────┴─────────┐
│ fhir_id          │                         │    │ FacilityCapability│
│ first_name       │                         │    │──────────────────│
│ last_name        │                         │    │ facility_id      │
│ dob              │                         │    │ specialty        │
│ gender           │                         │    │ service_name     │
│ insurance_plan   │                         │    │ is_active        │
│ insurance_id     │                         │    │ available_24_7   │
│ allergies[]      │                         │    └──────────────────┘
│ code_status      │                         │
└────────┬─────────┘                         │
         │                                   │
         │         ┌─────────────────────────┘
         │         │
         ▼         ▼
┌──────────────────────────┐
│   TransferRequest        │
│──────────────────────────│
│ id                       │
│ patient_id               │──▶ Patient
│ sending_facility_id      │──▶ Facility
│ receiving_facility_id    │──▶ Facility (nullable until accepted)
│ initiated_by_user_id     │──▶ User (NP)
│ accepted_by_user_id      │──▶ User (MD, nullable)
│ status                   │    [DRAFT, INITIATED, PENDING_REVIEW,
│                          │     ACCEPTED, TRANSPORT_DISPATCHED,
│                          │     IN_TRANSIT, ARRIVED, COMPLETED,
│                          │     DECLINED, CANCELLED]
│ urgency                  │    [EMERGENT, URGENT, ROUTINE]
│ reason_for_transfer      │
│ clinical_summary_id      │──▶ ClinicalSummary
│ compliance_record_id     │──▶ ComplianceRecord
│ transport_request_id     │──▶ TransportRequest
│ matched_facilities[]     │──▶ FacilityMatch[]
│ created_at               │
│ updated_at               │
└──────────────────────────┘
         │
         │
         ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   ClinicalSummary        │    │   ComplianceRecord       │
│──────────────────────────│    │──────────────────────────│
│ id                       │    │ id                       │
│ transfer_id              │    │ transfer_id              │
│ sbar_situation           │    │ mse_completed            │ (bool)
│ sbar_background          │    │ mse_completed_at         │
│ sbar_assessment          │    │ stabilization_attempted  │ (bool)
│ sbar_recommendation      │    │ stabilization_notes      │
│ vitals{}                 │    │ md_certification_signed  │ (bool)
│ active_conditions[]      │    │ md_certification_at      │
│ current_medications[]    │    │ certifying_physician_id  │
│ lab_results[]            │    │ consent_obtained         │ (bool)
│ imaging_results[]        │    │ consent_signed_at        │
│ additional_notes         │    │ consent_signer           │
│ generated_by_ai          │ (bool) │ receiving_confirmed  │ (bool)
│ reviewed_by_user_id      │    │ transport_appropriate    │ (bool)
│ reviewed_at              │    │ records_sent             │ (bool)
│ version                  │    │ all_checks_passed        │ (bool)
│ created_at               │    │ checked_at               │
└──────────────────────────┘    └──────────────────────────┘

┌──────────────────────────┐    ┌──────────────────────────┐
│   TransportRequest       │    │   FacilityMatch          │
│──────────────────────────│    │──────────────────────────│
│ id                       │    │ id                       │
│ transfer_id              │    │ transfer_id              │
│ transport_level          │    │ facility_id              │
│   [BLS, ALS, CCT, AIR]  │    │ match_score              │ (0-100)
│ transport_provider       │    │ specialty_score          │
│ ems_dispatch_id          │    │ bed_availability_score   │
│ pickup_facility_id       │    │ distance_score           │
│ dropoff_facility_id      │    │ insurance_score          │
│ pickup_eta               │    │ historical_score         │
│ departure_time           │    │ rank                     │
│ arrival_time             │    │ status                   │
│ status                   │    │   [SUGGESTED, SENT,      │
│   [REQUESTED, DISPATCHED,│    │    ACCEPTED, DECLINED]   │
│    EN_ROUTE_PICKUP,      │    │ declined_reason          │
│    ON_SCENE, TRANSPORTING│    │ responded_at             │
│    ARRIVED, COMPLETED]   │    └──────────────────────────┘
│ gps_lat                  │
│ gps_lng                  │    ┌──────────────────────────┐
│ crew_notes               │    │   AuditEvent             │
└──────────────────────────┘    │──────────────────────────│
                                │ id                       │
┌──────────────────────────┐    │ timestamp                │
│   TransferTimeline       │    │ user_id                  │
│──────────────────────────│    │ user_role                │
│ id                       │    │ action                   │
│ transfer_id              │    │ resource_type            │
│ event_type               │    │ resource_id              │
│ event_description        │    │ details{}                │ (JSONB)
│ triggered_by_user_id     │    │ ip_address               │
│ triggered_by_system      │    │ facility_id              │
│ metadata{}               │    │ phi_accessed             │ (bool)
│ created_at               │    └──────────────────────────┘
└──────────────────────────┘

┌──────────────────────────┐
│   Notification           │
│──────────────────────────│
│ id                       │
│ transfer_id              │
│ recipient_user_id        │
│ channel                  │
│   [PUSH, SMS, EMAIL,     │
│    IN_APP, WEBHOOK]      │
│ message_type             │
│   [TRANSFER_REQUEST,     │
│    ACCEPTANCE, DECLINE,  │
│    STATUS_UPDATE,        │
│    TRANSPORT_UPDATE]     │
│ content                  │
│ sent_at                  │
│ delivered_at             │
│ read_at                  │
│ status                   │
│   [PENDING, SENT,        │
│    DELIVERED, READ,      │
│    FAILED]               │
└──────────────────────────┘
```

---

## 2. Detailed Schema Definitions (PostgreSQL)

### 2.1 Core Tables

```sql
-- Organizations (hospital systems, clinic groups)
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(50) NOT NULL CHECK (type IN ('HOSPITAL_SYSTEM', 'CLINIC_GROUP', 'INDEPENDENT')),
    npi             VARCHAR(10) UNIQUE,
    address_line1   VARCHAR(255),
    address_line2   VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip_code        VARCHAR(10),
    phone           VARCHAR(20),
    ehr_system      VARCHAR(50),  -- EPIC, CERNER, MEDITECH, ALLSCRIPTS, OTHER
    fhir_base_url   VARCHAR(500),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Facilities (individual hospitals, clinics, urgent care centers)
CREATE TABLE facilities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id),
    name                VARCHAR(255) NOT NULL,
    facility_type       VARCHAR(50) NOT NULL CHECK (facility_type IN (
        'HOSPITAL', 'TRAUMA_CENTER', 'URGENT_CARE', 'CLINIC',
        'SNF', 'REHAB', 'PSYCH_FACILITY', 'BURN_CENTER'
    )),
    trauma_level        VARCHAR(10),  -- LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4, NONE
    npi                 VARCHAR(10) UNIQUE,
    address_line1       VARCHAR(255),
    address_line2       VARCHAR(255),
    city                VARCHAR(100),
    state               VARCHAR(2),
    zip_code            VARCHAR(10),
    latitude            DECIMAL(10, 7),
    longitude           DECIMAL(10, 7),
    phone               VARCHAR(20),
    transfer_center_phone VARCHAR(20),
    ehr_system          VARCHAR(50),
    fhir_base_url       VARCHAR(500),
    accepts_transfers   BOOLEAN DEFAULT TRUE,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_facilities_org ON facilities(organization_id);
CREATE INDEX idx_facilities_location ON facilities USING GIST (
    ll_to_earth(latitude, longitude)
);

-- Facility capabilities (specialties and services)
CREATE TABLE facility_capabilities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID NOT NULL REFERENCES facilities(id),
    category        VARCHAR(50) NOT NULL,  -- SPECIALTY, SERVICE, UNIT_TYPE
    name            VARCHAR(100) NOT NULL,  -- e.g., 'CARDIOLOGY', 'CATH_LAB', 'ICU'
    is_active       BOOLEAN DEFAULT TRUE,
    available_24_7  BOOLEAN DEFAULT FALSE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(facility_id, category, name)
);

CREATE INDEX idx_facility_capabilities ON facility_capabilities(facility_id, category);

-- Bed availability (real-time or manually updated)
CREATE TABLE bed_availability (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID NOT NULL REFERENCES facilities(id),
    unit_type       VARCHAR(50) NOT NULL,  -- ICU, MICU, SICU, CCU, TELE, MED_SURG, PSYCH, PEDS, NICU, ER
    total_beds      INTEGER NOT NULL DEFAULT 0,
    occupied_beds   INTEGER NOT NULL DEFAULT 0,
    available_beds  INTEGER GENERATED ALWAYS AS (total_beds - occupied_beds) STORED,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      UUID REFERENCES users(id),
    UNIQUE(facility_id, unit_type)
);

CREATE INDEX idx_bed_availability ON bed_availability(facility_id, unit_type);
```

### 2.2 User & Auth Tables

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     VARCHAR(255) UNIQUE,  -- Azure AD B2C object ID
    email           VARCHAR(255) NOT NULL UNIQUE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    role            VARCHAR(50) NOT NULL CHECK (role IN (
        'NURSE_PRACTITIONER', 'PHYSICIAN', 'TRANSFER_COORDINATOR',
        'EMS_CREW', 'ADMINISTRATOR', 'SYSTEM'
    )),
    phone           VARCHAR(20),
    npi             VARCHAR(10),
    specialty       VARCHAR(100),
    organization_id UUID REFERENCES organizations(id),
    facility_id     UUID REFERENCES facilities(id),
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_facility ON users(facility_id);
CREATE INDEX idx_users_role ON users(role);

-- On-call schedules
CREATE TABLE on_call_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID NOT NULL REFERENCES facilities(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    specialty       VARCHAR(100) NOT NULL,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_oncall_active ON on_call_schedules(facility_id, specialty, start_time, end_time)
    WHERE is_active = TRUE;
```

### 2.3 Patient & Clinical Tables

```sql
-- Patients (cached from EHR, not source of truth)
CREATE TABLE patients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mrn                 VARCHAR(50),       -- Medical Record Number at sending facility
    fhir_patient_id     VARCHAR(255),      -- FHIR Patient resource ID
    fhir_server_url     VARCHAR(500),      -- Which EHR this came from
    first_name          VARCHAR(100) NOT NULL,  -- Encrypted at column level
    last_name           VARCHAR(100) NOT NULL,  -- Encrypted at column level
    date_of_birth       DATE NOT NULL,          -- Encrypted at column level
    gender              VARCHAR(20),
    ssn_last_four       VARCHAR(4),             -- Encrypted at column level
    phone               VARCHAR(20),            -- Encrypted at column level
    insurance_provider  VARCHAR(255),
    insurance_plan_name VARCHAR(255),
    insurance_member_id VARCHAR(100),
    insurance_group_id  VARCHAR(100),
    code_status         VARCHAR(50),  -- FULL_CODE, DNR, DNI, DNR_DNI, COMFORT_CARE
    allergies           JSONB DEFAULT '[]',
    primary_language    VARCHAR(50) DEFAULT 'English',
    interpreter_needed  BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Clinical summaries (SBAR)
CREATE TABLE clinical_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id         UUID NOT NULL,  -- FK added after transfer table created
    patient_id          UUID NOT NULL REFERENCES patients(id),
    version             INTEGER NOT NULL DEFAULT 1,

    -- SBAR sections
    situation           TEXT NOT NULL,
    background          TEXT NOT NULL,
    assessment          TEXT NOT NULL,
    recommendation      TEXT NOT NULL,

    -- Structured clinical data (JSONB for flexibility)
    vitals              JSONB DEFAULT '{}',
    -- { "bp_systolic": 160, "bp_diastolic": 95, "hr": 110,
    --   "rr": 22, "spo2": 94, "temp": 98.6, "pain": 7,
    --   "gcs": 15, "recorded_at": "2026-06-08T10:00:00Z" }

    active_conditions   JSONB DEFAULT '[]',
    -- [{ "code": "I21.0", "display": "Acute ST elevation MI",
    --    "system": "ICD-10", "onset": "2026-06-08" }]

    current_medications JSONB DEFAULT '[]',
    -- [{ "name": "Heparin", "dose": "1000 units/hr", "route": "IV",
    --    "frequency": "continuous" }]

    lab_results         JSONB DEFAULT '[]',
    -- [{ "name": "Troponin I", "value": "0.8", "unit": "ng/mL",
    --    "reference_range": "0.0-0.04", "flag": "HIGH",
    --    "collected_at": "2026-06-08T09:30:00Z" }]

    imaging_results     JSONB DEFAULT '[]',
    -- [{ "type": "ECG", "finding": "ST elevation leads II, III, aVF",
    --    "impression": "Inferior STEMI", "performed_at": "..." }]

    additional_notes    TEXT,
    generated_by_ai     BOOLEAN DEFAULT FALSE,
    ai_model_version    VARCHAR(50),
    reviewed_by_user_id UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clinical_summaries_transfer ON clinical_summaries(transfer_id);
```

### 2.4 Transfer Tables

```sql
-- Transfer requests (core entity)
CREATE TABLE transfer_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_number         VARCHAR(20) NOT NULL UNIQUE,  -- Human-readable: TR-20260608-0001
    patient_id              UUID NOT NULL REFERENCES patients(id),
    sending_facility_id     UUID NOT NULL REFERENCES facilities(id),
    receiving_facility_id   UUID REFERENCES facilities(id),  -- NULL until accepted
    initiated_by_user_id    UUID NOT NULL REFERENCES users(id),
    accepted_by_user_id     UUID REFERENCES users(id),

    status                  VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT', 'INITIATED', 'PENDING_REVIEW', 'ACCEPTED',
        'TRANSPORT_DISPATCHED', 'IN_TRANSIT', 'ARRIVED',
        'COMPLETED', 'DECLINED', 'RE_ROUTING', 'CANCELLED'
    )),
    urgency                 VARCHAR(20) NOT NULL CHECK (urgency IN (
        'EMERGENT', 'URGENT', 'ROUTINE'
    )),
    reason_for_transfer     TEXT NOT NULL,
    requested_specialty     VARCHAR(100),
    requested_unit_type     VARCHAR(50),  -- ICU, TELE, MED_SURG, etc.

    clinical_summary_id     UUID,  -- FK to clinical_summaries
    compliance_record_id    UUID,  -- FK to compliance_records
    transport_request_id    UUID,  -- FK to transport_requests

    decline_reason          TEXT,
    cancellation_reason     TEXT,

    -- Timestamps for SLA tracking
    initiated_at            TIMESTAMPTZ,
    first_facility_contacted_at TIMESTAMPTZ,
    accepted_at             TIMESTAMPTZ,
    transport_dispatched_at TIMESTAMPTZ,
    patient_departed_at     TIMESTAMPTZ,
    patient_arrived_at      TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transfers_status ON transfer_requests(status) WHERE status NOT IN ('COMPLETED', 'CANCELLED');
CREATE INDEX idx_transfers_sending ON transfer_requests(sending_facility_id);
CREATE INDEX idx_transfers_receiving ON transfer_requests(receiving_facility_id);
CREATE INDEX idx_transfers_patient ON transfer_requests(patient_id);
CREATE INDEX idx_transfers_initiated_by ON transfer_requests(initiated_by_user_id);
CREATE INDEX idx_transfers_created ON transfer_requests(created_at DESC);

-- Add FK from clinical_summaries back to transfers
ALTER TABLE clinical_summaries
    ADD CONSTRAINT fk_clinical_summary_transfer
    FOREIGN KEY (transfer_id) REFERENCES transfer_requests(id);

-- Facility match results
CREATE TABLE facility_matches (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id             UUID NOT NULL REFERENCES transfer_requests(id),
    facility_id             UUID NOT NULL REFERENCES facilities(id),
    rank                    INTEGER NOT NULL,
    overall_score           DECIMAL(5,2) NOT NULL,  -- 0-100
    specialty_score         DECIMAL(5,2) NOT NULL,
    bed_availability_score  DECIMAL(5,2) NOT NULL,
    distance_score          DECIMAL(5,2) NOT NULL,
    insurance_score         DECIMAL(5,2) NOT NULL,
    historical_score        DECIMAL(5,2) NOT NULL,
    distance_miles          DECIMAL(7,1),
    estimated_transport_min INTEGER,
    status                  VARCHAR(20) DEFAULT 'SUGGESTED' CHECK (status IN (
        'SUGGESTED', 'SENT', 'ACCEPTED', 'DECLINED', 'SKIPPED'
    )),
    declined_reason         TEXT,
    responded_by_user_id    UUID REFERENCES users(id),
    responded_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_facility_matches_transfer ON facility_matches(transfer_id);

-- Transfer timeline (event log)
CREATE TABLE transfer_timeline (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id         UUID NOT NULL REFERENCES transfer_requests(id),
    event_type          VARCHAR(50) NOT NULL,
    event_description   TEXT NOT NULL,
    triggered_by_user_id UUID REFERENCES users(id),
    triggered_by_system BOOLEAN DEFAULT FALSE,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_timeline_transfer ON transfer_timeline(transfer_id, created_at);
```

### 2.5 Compliance & Transport Tables

```sql
-- Compliance records (EMTALA tracking)
CREATE TABLE compliance_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id                 UUID NOT NULL UNIQUE REFERENCES transfer_requests(id),

    -- EMTALA checklist items
    mse_completed               BOOLEAN DEFAULT FALSE,
    mse_completed_at            TIMESTAMPTZ,
    mse_documented_by           UUID REFERENCES users(id),

    stabilization_attempted     BOOLEAN DEFAULT FALSE,
    stabilization_notes         TEXT,

    md_certification_signed     BOOLEAN DEFAULT FALSE,
    md_certification_at         TIMESTAMPTZ,
    certifying_physician_id     UUID REFERENCES users(id),
    certification_reason        TEXT,  -- "Benefits of transfer outweigh risks because..."

    consent_obtained            BOOLEAN DEFAULT FALSE,
    consent_signed_at           TIMESTAMPTZ,
    consent_signer_name         VARCHAR(255),
    consent_signer_relationship VARCHAR(100),  -- PATIENT, SPOUSE, PARENT, POA, etc.
    consent_unable_reason       TEXT,  -- If patient unable to consent

    receiving_facility_confirmed BOOLEAN DEFAULT FALSE,
    receiving_confirmed_at       TIMESTAMPTZ,

    transport_appropriate       BOOLEAN DEFAULT FALSE,
    transport_level_justified   TEXT,

    records_sent                BOOLEAN DEFAULT FALSE,
    records_sent_at             TIMESTAMPTZ,

    all_checks_passed           BOOLEAN GENERATED ALWAYS AS (
        mse_completed AND stabilization_attempted AND
        md_certification_signed AND consent_obtained AND
        receiving_facility_confirmed AND transport_appropriate AND
        records_sent
    ) STORED,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Transport requests
CREATE TABLE transport_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id             UUID NOT NULL REFERENCES transfer_requests(id),
    transport_level         VARCHAR(10) NOT NULL CHECK (transport_level IN (
        'BLS', 'ALS', 'CCT', 'AIR_ROTOR', 'AIR_FIXED'
    )),
    transport_provider_name VARCHAR(255),
    ems_dispatch_id         VARCHAR(100),
    pickup_facility_id      UUID NOT NULL REFERENCES facilities(id),
    dropoff_facility_id     UUID NOT NULL REFERENCES facilities(id),

    status                  VARCHAR(30) NOT NULL DEFAULT 'REQUESTED' CHECK (status IN (
        'REQUESTED', 'DISPATCHED', 'EN_ROUTE_PICKUP', 'ON_SCENE',
        'TRANSPORTING', 'ARRIVED', 'COMPLETED', 'CANCELLED'
    )),

    estimated_pickup_at     TIMESTAMPTZ,
    actual_pickup_at        TIMESTAMPTZ,
    estimated_arrival_at    TIMESTAMPTZ,
    actual_arrival_at       TIMESTAMPTZ,

    current_gps_lat         DECIMAL(10, 7),
    current_gps_lng         DECIMAL(10, 7),
    crew_lead_name          VARCHAR(255),
    crew_lead_phone         VARCHAR(20),
    crew_notes              TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transport_transfer ON transport_requests(transfer_id);
CREATE INDEX idx_transport_status ON transport_requests(status)
    WHERE status NOT IN ('COMPLETED', 'CANCELLED');
```

### 2.6 Audit & Notification Tables

```sql
-- Audit events (immutable, append-only)
CREATE TABLE audit_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id         UUID,
    user_role       VARCHAR(50),
    user_email      VARCHAR(255),
    action          VARCHAR(100) NOT NULL,  -- e.g., 'TRANSFER_CREATED', 'PHI_VIEWED', 'SBAR_GENERATED'
    resource_type   VARCHAR(50) NOT NULL,   -- e.g., 'TRANSFER', 'PATIENT', 'CLINICAL_SUMMARY'
    resource_id     UUID,
    facility_id     UUID,
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,
    phi_accessed    BOOLEAN DEFAULT FALSE,
    session_id      VARCHAR(255)
);

-- Partition by month for performance
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_events(user_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_events(resource_type, resource_id);
CREATE INDEX idx_audit_phi ON audit_events(phi_accessed, timestamp DESC) WHERE phi_accessed = TRUE;

-- Notifications
CREATE TABLE notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id         UUID REFERENCES transfer_requests(id),
    recipient_user_id   UUID NOT NULL REFERENCES users(id),
    channel             VARCHAR(20) NOT NULL CHECK (channel IN (
        'PUSH', 'SMS', 'EMAIL', 'IN_APP', 'WEBHOOK'
    )),
    message_type        VARCHAR(50) NOT NULL,
    title               VARCHAR(255),
    body                TEXT NOT NULL,
    priority            VARCHAR(10) DEFAULT 'NORMAL' CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')),
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'SENT', 'DELIVERED', 'READ', 'FAILED'
    )),
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    read_at             TIMESTAMPTZ,
    failure_reason      TEXT,
    external_message_id VARCHAR(255),  -- Twilio SID, FCM message ID, etc.
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_user_id, created_at DESC);
CREATE INDEX idx_notifications_transfer ON notifications(transfer_id);
```

---

## 3. FHIR Resource Mapping

Maps internal data models to FHIR R4 resources for EHR interoperability:

| Internal Model | FHIR Resource | Key Fields Mapped |
|---|---|---|
| `Patient` | `Patient` | `name`, `birthDate`, `gender`, `identifier` (MRN), `telecom`, `address` |
| `Patient.allergies` | `AllergyIntolerance` | `code`, `clinicalStatus`, `type`, `criticality` |
| `ClinicalSummary.vitals` | `Observation` (category: vital-signs) | `code` (LOINC), `valueQuantity`, `effectiveDateTime` |
| `ClinicalSummary.active_conditions` | `Condition` | `code` (ICD-10/SNOMED), `clinicalStatus`, `onsetDateTime` |
| `ClinicalSummary.current_medications` | `MedicationRequest` | `medicationCodeableConcept`, `dosageInstruction`, `status` |
| `ClinicalSummary.lab_results` | `Observation` (category: laboratory) | `code` (LOINC), `valueQuantity`, `referenceRange`, `interpretation` |
| `ClinicalSummary.imaging_results` | `DiagnosticReport` | `code`, `conclusion`, `effectiveDateTime`, `category` |
| `TransferRequest` | `ServiceRequest` | `status`, `intent`, `priority`, `code`, `subject`, `requester` |
| `Facility` | `Organization` + `Location` | `name`, `identifier` (NPI), `type`, `address`, `position` |

---

## 4. Key JSONB Schemas

### Vitals Object
```json
{
  "bp_systolic": 160,
  "bp_diastolic": 95,
  "heart_rate": 110,
  "respiratory_rate": 22,
  "spo2": 94,
  "temperature": 98.6,
  "temperature_unit": "F",
  "pain_scale": 7,
  "gcs_total": 15,
  "gcs_eye": 4,
  "gcs_verbal": 5,
  "gcs_motor": 6,
  "oxygen_delivery": "Nasal Cannula",
  "oxygen_flow_rate": "2L",
  "weight_kg": 85.0,
  "recorded_at": "2026-06-08T10:00:00Z"
}
```

### Condition Object
```json
{
  "code": "I21.09",
  "display": "ST elevation myocardial infarction involving other coronary artery of anterior wall",
  "coding_system": "ICD-10-CM",
  "snomed_code": "401303003",
  "clinical_status": "active",
  "verification_status": "confirmed",
  "severity": "severe",
  "onset_date": "2026-06-08",
  "notes": "Acute inferior STEMI, presenting with chest pain x 2 hours"
}
```

### Medication Object
```json
{
  "name": "Heparin Sodium",
  "rxnorm_code": "235473",
  "dose": "1000",
  "dose_unit": "units/hr",
  "route": "IV",
  "frequency": "continuous",
  "start_date": "2026-06-08T09:45:00Z",
  "prescribing_provider": "Dr. Smith",
  "notes": "Bolus 5000 units given at 09:30"
}
```

### Lab Result Object
```json
{
  "name": "Troponin I",
  "loinc_code": "10839-9",
  "value": 0.8,
  "value_string": "0.8",
  "unit": "ng/mL",
  "reference_range_low": 0.0,
  "reference_range_high": 0.04,
  "reference_range_text": "0.00 - 0.04 ng/mL",
  "interpretation": "HIGH",
  "flag": "CRITICAL",
  "collected_at": "2026-06-08T09:30:00Z",
  "resulted_at": "2026-06-08T09:50:00Z",
  "performing_lab": "Point-of-Care"
}
```
