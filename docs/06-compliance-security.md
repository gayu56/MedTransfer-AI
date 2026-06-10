# Compliance & Security Design Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026

---

## 1. Regulatory Landscape

IPTC must comply with multiple overlapping regulations:

```
┌─────────────────────────────────────────────────────────┐
│                 REGULATORY REQUIREMENTS                   │
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                 │
│  │    EMTALA       │  │     HIPAA      │                 │
│  │                 │  │                │                  │
│  │ Transfer        │  │ Privacy Rule   │                  │
│  │ requirements,   │  │ Security Rule  │                  │
│  │ documentation,  │  │ Breach         │                  │
│  │ anti-dumping    │  │ Notification   │                  │
│  └────────────────┘  └────────────────┘                  │
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                  │
│  │  CMS CoP       │  │  21st Century  │                  │
│  │                 │  │  Cures Act     │                  │
│  │ Conditions of   │  │                │                  │
│  │ Participation   │  │ Information    │                  │
│  │ for hospitals   │  │ blocking,      │                  │
│  │                 │  │ FHIR mandates  │                  │
│  └────────────────┘  └────────────────┘                  │
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                  │
│  │  State Laws    │  │  SOC 2 Type II │                  │
│  │                 │  │                │                  │
│  │ State-specific  │  │ Security,      │                  │
│  │ consent,        │  │ availability,  │                  │
│  │ recording,      │  │ processing     │                  │
│  │ telemedicine    │  │ integrity      │                  │
│  └────────────────┘  └────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. EMTALA Compliance Engine

### 2.1 EMTALA Requirements for Transfers

The Emergency Medical Treatment and Labor Act (42 U.S.C. § 1395dd) mandates specific requirements for interfacility transfers. Our system enforces each one:

| EMTALA Requirement | System Implementation | Enforcement Level |
|---|---|---|
| **Medical Screening Exam (MSE)** | System requires MSE documentation before transfer can be initiated. NP must confirm MSE is complete. | HARD BLOCK — cannot proceed without |
| **Stabilization** | System requires documentation that stabilizing treatment was provided, or physician certification that benefits of transfer outweigh risks of not stabilizing. | HARD BLOCK |
| **Physician Certification** | Digital signature workflow. Sending physician must sign certification form stating transfer benefits outweigh risks, with specific clinical rationale. | HARD BLOCK |
| **Informed Consent** | Digital consent form generated. Patient (or representative) must sign. System handles exceptions (unconscious, incapacitated) with documentation. | HARD BLOCK (with exception workflow) |
| **Receiving Facility Acceptance** | System tracks acceptance from receiving facility with timestamp, accepting physician name, and assigned unit. | HARD BLOCK |
| **Appropriate Transport** | System recommends transport level based on acuity. Must document that transport has qualified personnel and equipment. | HARD BLOCK |
| **Medical Records** | System auto-generates transfer packet from EHR data. Checklist ensures all available records are included. | HARD BLOCK |
| **Transfer Agreement** | System verifies transfer agreement exists between facilities (or documents that this is an EMTALA-mandated transfer). | SOFT CHECK — warning only |

### 2.2 Compliance Check Flow

```
Transfer Request Created
         │
         ▼
┌────────────────────────────────────────────┐
│         EMTALA COMPLIANCE ENGINE            │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 1: MSE Documentation          │   │
│  │ Source: NP confirmation + EHR note   │   │
│  │ Required: YES                        │   │
│  │ Status: ✅ or ❌                     │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 2: Stabilization              │   │
│  │ Source: NP documentation            │   │
│  │ Required: YES                        │   │
│  │ Options:                             │   │
│  │   a) Patient stabilized             │   │
│  │   b) Benefits outweigh risks (MD    │   │
│  │      certification required)        │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 3: MD Transfer Certification  │   │
│  │ Source: Digital signature           │   │
│  │ Required: YES                        │   │
│  │ Must include:                        │   │
│  │   - Physician name & NPI            │   │
│  │   - Clinical justification          │   │
│  │   - Risk/benefit statement          │   │
│  │   - Timestamp                       │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 4: Informed Consent           │   │
│  │ Source: Digital signature           │   │
│  │ Required: YES (with exceptions)      │   │
│  │ Exceptions handled:                  │   │
│  │   - Patient unconscious/incapacitated│  │
│  │   - Legal representative not available│  │
│  │   - Emergency exception (document)  │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 5: Receiving Facility Confirmed│  │
│  │ Source: System (acceptance workflow) │   │
│  │ Required: YES                        │   │
│  │ Tracked: Accepting MD, unit, time   │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 6: Transport Appropriate      │   │
│  │ Source: Transport service selection  │   │
│  │ Required: YES                        │   │
│  │ Validates: Level matches acuity     │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ CHECK 7: Records Prepared           │   │
│  │ Source: Transfer packet generator   │   │
│  │ Required: YES                        │   │
│  │ Includes: SBAR, labs, imaging, ECG, │   │
│  │   meds, consent, certification      │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ALL CHECKS PASSED?                        │
│    YES → Transport can be dispatched       │
│    NO  → Block + notify NP of missing items│
└────────────────────────────────────────────┘
```

### 2.3 EMTALA Document Templates

The system auto-generates these compliance documents:

1. **Physician Transfer Certification Form**
   - Certifying physician name, NPI, signature
   - Summary of patient's emergency medical condition
   - Statement that benefits of transfer outweigh risks
   - Specific risks and benefits enumerated
   - Receiving facility name and accepting physician
   - Timestamp

2. **Patient Transfer Consent Form**
   - Patient name and identifiers
   - Explanation of transfer (in plain language)
   - Risks of transfer and risks of not transferring
   - Patient/representative signature and date
   - Witness signature
   - Exception documentation (if patient unable to consent)

3. **Transfer Summary / Face Sheet**
   - Complete SBAR summary
   - All current orders
   - Medication reconciliation
   - Copies of relevant test results
   - Advance directives

---

## 3. HIPAA Compliance

### 3.1 Privacy Rule Implementation

| HIPAA Principle | Implementation |
|---|---|
| **Minimum Necessary** | API responses only include PHI fields relevant to the user's role and the specific action. Transfer coordinators see clinical summary; billing sees insurance only. |
| **Treatment Exception** | PHI sharing between involved clinicians for transfer coordination falls under the Treatment exception (45 CFR § 164.506). No patient authorization required for treatment-related disclosures. |
| **Access Controls** | Role-based access control (RBAC) enforced at API layer. Every PHI field has an access policy. |
| **Accounting of Disclosures** | Every PHI access logged with user, timestamp, purpose, and specific fields accessed. Patients can request disclosure accounting. |
| **Patient Rights** | System supports patient access requests, amendment requests, and restriction requests. |
| **Business Associates** | BAAs executed with all cloud vendors (Azure, Twilio, SendGrid, etc.) |

### 3.2 Security Rule Implementation

#### Administrative Safeguards

| Safeguard | Implementation |
|---|---|
| Security Officer | Designated security officer responsible for IPTC security program |
| Risk Analysis | Annual risk assessment; continuous risk monitoring |
| Workforce Training | Mandatory HIPAA training for all system users |
| Access Management | Role-based provisioning; immediate deprovisioning on termination |
| Incident Response | Documented IR plan; 60-day breach notification compliance |
| Contingency Plan | DR plan tested quarterly; data backup verified daily |

#### Physical Safeguards

| Safeguard | Implementation |
|---|---|
| Facility Access | Azure data centers (SOC 2, ISO 27001 certified) |
| Workstation Security | Enforced via Azure AD Conditional Access policies |
| Device Controls | MDM for mobile devices; remote wipe capability |

#### Technical Safeguards

| Safeguard | Implementation |
|---|---|
| **Access Control** | Unique user IDs, automatic logoff (15 min), encryption/decryption |
| **Audit Controls** | Every action logged to immutable audit store; 7-year retention |
| **Integrity** | Data validation, checksums, tamper detection on audit logs |
| **Transmission Security** | TLS 1.3 for all data in transit; certificate pinning for mobile |

### 3.3 PHI Data Classification

```
┌─────────────────────────────────────────────────────────┐
│                PHI DATA CLASSIFICATION                    │
│                                                          │
│  ┌─────────────────────┐                                │
│  │ CRITICAL PHI         │  Encryption: Column-level     │
│  │                      │  Access: Need-to-know only    │
│  │ • SSN (last 4)      │  Logging: Every access         │
│  │ • Full name         │  Masking: In non-prod envs     │
│  │ • Date of birth     │                                │
│  │ • Phone number      │                                │
│  │ • Address           │                                │
│  └─────────────────────┘                                │
│                                                          │
│  ┌─────────────────────┐                                │
│  │ SENSITIVE PHI        │  Encryption: At rest (AES-256)│
│  │                      │  Access: Role-based            │
│  │ • MRN               │  Logging: Every access          │
│  │ • Insurance IDs     │                                │
│  │ • Clinical data     │                                │
│  │ • Diagnoses         │                                │
│  │ • Medications       │                                │
│  │ • Lab results       │                                │
│  └─────────────────────┘                                │
│                                                          │
│  ┌─────────────────────┐                                │
│  │ OPERATIONAL DATA     │  Encryption: At rest           │
│  │                      │  Access: By role               │
│  │ • Transfer status   │  Logging: Write operations      │
│  │ • Facility data     │                                │
│  │ • User accounts     │                                │
│  │ • Audit logs        │                                │
│  └─────────────────────┘                                │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Audit Logging System

### 4.1 What Gets Logged

Every interaction with the system generates an audit event:

| Event Category | Examples | PHI Involved |
|---|---|---|
| **Authentication** | Login, logout, failed login, token refresh | No |
| **PHI Access** | Patient record viewed, SBAR viewed, labs viewed | Yes |
| **Transfer Actions** | Created, accepted, declined, cancelled, completed | Yes |
| **Clinical Data** | SBAR generated, SBAR edited, vitals viewed | Yes |
| **Compliance** | Checklist item updated, form signed, form generated | Yes |
| **Administrative** | User created, role changed, facility updated | No |
| **AI Agent** | Chat message, tool call, SBAR generation, facility search | Mixed |
| **System** | Notification sent, transport dispatched, FHIR API call | Mixed |

### 4.2 Audit Event Schema

```json
{
  "id": "audit-uuid",
  "timestamp": "2026-06-08T15:00:00.000Z",
  "user_id": "user-uuid",
  "user_email": "sarah.np@urgentcare.com",
  "user_role": "NURSE_PRACTITIONER",
  "facility_id": "facility-uuid",
  "organization_id": "org-uuid",
  "action": "PHI_VIEWED",
  "resource_type": "PATIENT",
  "resource_id": "patient-uuid",
  "details": {
    "fields_accessed": ["name", "dob", "vitals", "medications"],
    "purpose": "TRANSFER_COORDINATION",
    "transfer_id": "transfer-uuid"
  },
  "ip_address": "10.0.1.45",
  "user_agent": "IPTC-Web/1.0 Chrome/126.0",
  "session_id": "session-uuid",
  "phi_accessed": true,
  "request_id": "req-uuid"
}
```

### 4.3 Audit Storage & Retention

```
Audit Events → Kafka (audit.event topic) → 
    ├── Azure Log Analytics (30-day hot storage, searchable)
    ├── Azure Blob Storage (7-year cold storage, immutable)
    └── Microsoft Sentinel (SIEM, real-time alerting)

Properties:
  • Immutable: Write-once, append-only
  • Tamper-proof: SHA-256 hash chain
  • Encrypted: AES-256 at rest
  • Retention: 7 years (HIPAA requirement)
  • Searchable: By user, patient, time range, action type
```

---

## 5. Encryption Strategy

### 5.1 Data in Transit

| Connection | Protocol | Certificate |
|---|---|---|
| Client ↔ API Gateway | TLS 1.3 | Azure-managed wildcard cert |
| Service ↔ Service | mTLS (Istio/Dapr) | Auto-rotated service certs |
| Service ↔ Database | TLS 1.3 | Azure-managed |
| Service ↔ External EHR | TLS 1.2+ | EHR vendor cert |
| Mobile App | TLS 1.3 + Certificate Pinning | Pinned cert in app bundle |

### 5.2 Data at Rest

| Store | Encryption | Key Management |
|---|---|---|
| PostgreSQL | AES-256 (Azure-managed) | Azure Key Vault |
| Redis | AES-256 | Azure-managed |
| Blob Storage | AES-256 | Azure Key Vault (CMK option) |
| Column-level (PHI) | AES-256-GCM via pgcrypto | Azure Key Vault |
| Backups | AES-256 | Azure-managed |

### 5.3 Column-Level Encryption for Critical PHI

```sql
-- Example: Encrypting patient name at column level
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt on insert
INSERT INTO patients (first_name, last_name, date_of_birth)
VALUES (
    pgp_sym_encrypt('John', current_setting('app.encryption_key')),
    pgp_sym_encrypt('Doe', current_setting('app.encryption_key')),
    pgp_sym_encrypt('1958-03-15', current_setting('app.encryption_key'))
);

-- Decrypt on read (only for authorized queries)
SELECT 
    pgp_sym_decrypt(first_name::bytea, current_setting('app.encryption_key')) as first_name,
    pgp_sym_decrypt(last_name::bytea, current_setting('app.encryption_key')) as last_name
FROM patients
WHERE id = 'patient-uuid';
```

---

## 6. Access Control Matrix

### Role-Based Permissions

| Resource / Action | NP | Transfer Coordinator | Accepting MD | EMS | Admin |
|---|---|---|---|---|---|
| **Create transfer** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **View own transfers** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **View all facility transfers** | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Accept/decline transfer** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **View patient PHI** | ✅* | ✅* | ✅* | ✅* | ❌ |
| **Generate SBAR** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Edit SBAR** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Sign MD certification** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Dispatch transport** | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Update transport status** | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Update bed availability** | ❌ | ✅ | ❌ | ❌ | ✅ |
| **View analytics** | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Manage users** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **View audit logs** | ❌ | ❌ | ❌ | ❌ | ✅ |

*Only for patients involved in their assigned transfers.

---

## 7. Incident Response Plan

### 7.1 Breach Classification

| Severity | Definition | Response Time | Examples |
|---|---|---|---|
| **P1 — Critical** | Confirmed PHI breach affecting >500 individuals | 1 hour | Database breach, mass PHI exposure |
| **P2 — High** | Confirmed PHI breach affecting <500 individuals | 4 hours | Misdirected transfer with PHI, unauthorized access |
| **P3 — Medium** | Potential PHI exposure, unconfirmed | 24 hours | Suspicious login activity, access anomaly |
| **P4 — Low** | Security event, no PHI exposure | 72 hours | Failed login attempts, vulnerability discovered |

### 7.2 Response Workflow

```
Detection (automated or reported)
        │
        ▼
Classification (P1-P4)
        │
        ▼
Containment
  • Isolate affected systems
  • Revoke compromised credentials
  • Block suspicious IPs
        │
        ▼
Investigation
  • Audit log analysis
  • Scope determination (what PHI, how many patients)
  • Root cause analysis
        │
        ▼
Notification (if breach confirmed)
  • HHS/OCR: Within 60 days (or annual if <500)
  • Affected individuals: Within 60 days
  • Media: If >500 in a state/jurisdiction
  • State AG: Per state law requirements
        │
        ▼
Remediation
  • Fix vulnerability
  • Update security controls
  • Post-incident review
  • Update risk assessment
```

---

## 8. Security Testing

| Test Type | Frequency | Tool/Method |
|---|---|---|
| **SAST** (Static Analysis) | Every commit | SonarQube, Semgrep |
| **DAST** (Dynamic Analysis) | Weekly | OWASP ZAP |
| **Dependency Scanning** | Daily | Snyk, Dependabot |
| **Container Scanning** | Every build | Trivy, Azure Defender |
| **Penetration Testing** | Annually (+ after major releases) | Third-party firm |
| **Phishing Simulation** | Quarterly | Internal exercise |
| **Red Team Exercise** | Annually | Third-party firm |
| **HIPAA Risk Assessment** | Annually | Internal + external auditor |

---

## 9. Compliance Checklist for Go-Live

| Item | Status | Owner |
|---|---|---|
| BAA with Azure | ⬜ | Legal |
| BAA with Twilio | ⬜ | Legal |
| BAA with SendGrid | ⬜ | Legal |
| HIPAA Risk Assessment completed | ⬜ | Security |
| Penetration test passed | ⬜ | Security |
| SOC 2 Type II audit initiated | ⬜ | Compliance |
| Privacy policy published | ⬜ | Legal |
| Workforce HIPAA training completed | ⬜ | HR |
| Incident response plan tested | ⬜ | Security |
| Audit logging verified (7-year retention) | ⬜ | Engineering |
| Encryption verified (at rest + in transit) | ⬜ | Engineering |
| Access controls tested (RBAC) | ⬜ | Engineering |
| EMTALA workflow validated by clinical advisor | ⬜ | Clinical |
| State-specific consent laws reviewed | ⬜ | Legal |
| Data backup and DR tested | ⬜ | Engineering |
