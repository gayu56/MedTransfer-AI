# System Architecture Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026

---

## 1. Architecture Principles

| Principle | Description |
|---|---|
| **Microservices** | Each domain capability is an independent, deployable service |
| **Event-Driven** | Services communicate via events for loose coupling and real-time updates |
| **API-First** | All functionality exposed via well-defined REST/GraphQL APIs |
| **HIPAA by Design** | Security and compliance baked into every layer, not bolted on |
| **Human-in-the-Loop** | AI assists but never makes clinical decisions autonomously |
| **FHIR-Native** | Internal data models aligned with HL7 FHIR R4 resources |
| **Cloud-Native** | Designed for Azure Health Data Services (HIPAA-eligible) |
| **Resilient** | Circuit breakers, retries, graceful degradation |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENTS / CHANNELS                               │
│                                                                          │
│   ┌──────────────┐   ┌───────────────┐   ┌─────────────────────────┐   │
│   │  Web App      │   │  Mobile App    │   │  Voice (Twilio/Phone)   │   │
│   │  (React SPA)  │   │  (React Native)│   │  Future Phase           │   │
│   └──────┬───────┘   └───────┬───────┘   └────────────┬────────────┘   │
└──────────┼───────────────────┼────────────────────────┼─────────────────┘
           │                   │                        │
           ▼                   ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                                        │
│                    (Azure API Management)                                  │
│                                                                           │
│   • TLS 1.3 termination          • JWT / OAuth 2.0 authentication        │
│   • Rate limiting (per user/org) • Request/response logging               │
│   • IP whitelisting              • API versioning (v1/, v2/)              │
│   • CORS management              • Request transformation                 │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     SERVICE MESH (Dapr / Istio)                           │
│          Service discovery · mTLS · Observability · Retries               │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  CORE        │  │  AI / INTELLIGENCE│  │  INTEGRATION     │
│  SERVICES    │  │  SERVICES         │  │  SERVICES        │
│              │  │                   │  │                   │
│ • Transfer   │  │ • AI Agent        │  │ • FHIR Gateway   │
│ • Facility   │  │ • SBAR Generator  │  │ • EMS Dispatch   │
│ • Transport  │  │ • Facility Matcher│  │ • Insurance      │
│ • Compliance │  │ • NLP Pipeline    │  │ • Notification   │
│ • User/Auth  │  │                   │  │ • Telecom        │
│ • Analytics  │  │                   │  │                   │
└──────┬───────┘  └────────┬─────────┘  └────────┬─────────┘
       │                   │                      │
       ▼                   ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     EVENT BUS (Apache Kafka)                              │
│                                                                           │
│   Topics:                                                                 │
│   • transfer.initiated    • transfer.accepted     • transfer.declined    │
│   • transfer.in_transit   • transfer.completed    • transfer.cancelled   │
│   • compliance.check      • facility.bed_update   • transport.status     │
│   • notification.send     • audit.event                                  │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      DATA STORES                                          │
│                                                                           │
│   ┌──────────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│   │ PostgreSQL 16 │  │ Redis 7  │  │ Azure Blob│  │ Azure AI Search  │  │
│   │               │  │          │  │ Storage   │  │ (Vector Store)   │  │
│   │ • Transfers   │  │ • Cache  │  │           │  │                  │  │
│   │ • Facilities  │  │ • Session│  │ • Transfer│  │ • Clinical doc   │  │
│   │ • Users       │  │ • Pub/Sub│  │   packets │  │   embeddings     │  │
│   │ • Audit logs  │  │ • Locks  │  │ • ECGs    │  │ • Facility       │  │
│   │ • Compliance  │  │          │  │ • Reports │  │   capability     │  │
│   └──────────────┘  └──────────┘  └───────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Service Decomposition

### 3.1 Core Services

#### Transfer Service
**Responsibility**: Manages the entire lifecycle of a transfer request.

```
Transfer States:
  DRAFT → INITIATED → PENDING_REVIEW → ACCEPTED → TRANSPORT_DISPATCHED
    → IN_TRANSIT → ARRIVED → COMPLETED
                    ↘ DECLINED → RE_ROUTING
                    ↘ CANCELLED
```

| Endpoint Group | Purpose |
|---|---|
| `POST /transfers` | Create new transfer request |
| `GET /transfers/{id}` | Get transfer details |
| `PATCH /transfers/{id}/status` | Update transfer status |
| `GET /transfers?status=active` | List transfers with filters |
| `POST /transfers/{id}/accept` | Accept a transfer |
| `POST /transfers/{id}/decline` | Decline with reason |
| `GET /transfers/{id}/timeline` | Full event timeline |

**Internal Events Published**:
- `transfer.initiated` — triggers facility matching + compliance check
- `transfer.accepted` — triggers transport coordination + notification
- `transfer.declined` — triggers re-routing logic
- `transfer.completed` — triggers analytics + audit finalization

---

#### Facility Service
**Responsibility**: Manages facility registry, capabilities, and bed availability.

| Data Managed | Details |
|---|---|
| Facility profiles | Name, address, NPI, contact info, transfer center number |
| Capabilities | Specialties, services (cath lab, neuro IR, burn, NICU, etc.) |
| Bed availability | Real-time counts by unit type (ICU, tele, med-surg, psych) |
| On-call schedules | Which physician is accepting for which service |
| Transfer agreements | Which facilities have agreements with which |
| Operating hours | 24/7 vs. limited-hour facilities |

---

#### Compliance Service
**Responsibility**: Enforces EMTALA and other regulatory requirements.

```
Compliance Check Flow:

Transfer Request Created
        │
        ▼
┌─────────────────────────────┐
│  EMTALA Checklist Validator  │
│                              │
│  ✓ MSE documented?          │
│  ✓ Stabilization attempted? │
│  ✓ MD certification signed? │
│  ✓ Consent obtained?        │
│  ✓ Receiving facility       │
│    accepted?                 │
│  ✓ Appropriate transport?   │
│  ✓ Records prepared?        │
└──────────┬──────────────────┘
           │
     ┌─────┴─────┐
     │            │
  ALL PASS     MISSING
     │            │
     ▼            ▼
  APPROVED    BLOCKED
  (transport   (NP notified
   can be      of missing
   dispatched)  items)
```

---

#### User & Auth Service
**Responsibility**: Authentication, authorization, role-based access control.

| Role | Permissions |
|---|---|
| `NP / Sending Clinician` | Create transfers, view own transfers, upload documents |
| `Transfer Coordinator` | View all incoming transfers, manage bed assignments, dispatch transport |
| `Accepting Physician` | View assigned transfers, accept/decline |
| `EMS Crew` | View assigned transport, update transport status |
| `Administrator` | All permissions + analytics + user management |
| `System / AI Agent` | Read EHR data, generate SBAR, suggest facilities (no clinical decisions) |

**Auth Strategy**: OAuth 2.0 + OIDC via Azure AD B2C (supports SMART on FHIR for EHR SSO)

---

### 3.2 AI / Intelligence Services

#### AI Agent Service
**Responsibility**: Conversational AI that assists NPs in transfer initiation.

```
Architecture:

  User Message
       │
       ▼
┌─────────────────┐
│  Intent Router   │  Classifies user intent
└────────┬────────┘
         │
    ┌────┴────────────────────────┐
    ▼              ▼              ▼
┌────────┐  ┌───────────┐  ┌──────────┐
│ Transfer│  │ Question  │  │ Status   │
│ Flow    │  │ Answering │  │ Check    │
│ Agent   │  │ Agent     │  │ Agent    │
└────┬────┘  └─────┬─────┘  └────┬─────┘
     │             │              │
     ▼             ▼              ▼
┌─────────────────────────────────────┐
│         Tool Execution Layer         │
│                                      │
│  • FHIR Client (read patient data)  │
│  • SBAR Generator (create summary)  │
│  • Facility Matcher (find hospitals)│
│  • Transfer API (create request)    │
│  • Compliance Checker               │
└─────────────────────────────────────┘
```

**LLM Configuration**:
- Model: Azure OpenAI GPT-4 (HIPAA BAA in place)
- Temperature: 0.1 (low creativity for clinical accuracy)
- Max tokens: 4,096 per response
- System prompt: Carefully crafted with clinical guardrails (see AI Agent Design doc)

---

#### SBAR Generator Service
**Responsibility**: Generates structured SBAR clinical summaries from EHR data.

**Pipeline**:
1. Fetch FHIR resources (Patient, Encounter, Conditions, Observations, Meds, DiagnosticReports)
2. Structure data into pre-SBAR template (JSON)
3. Pass structured data + NP context to LLM with SBAR prompt
4. Validate output against structured data (no hallucination check)
5. Return SBAR as structured JSON + rendered text
6. NP reviews and edits → version saved

---

#### Facility Matching Service
**Responsibility**: Scores and ranks potential receiving facilities.

**Algorithm**:
```
Score = Σ (weight_i × criterion_score_i)

Where:
  criterion_1 = specialty_match(patient_needs, facility_capabilities)  [0-1]  × 0.30
  criterion_2 = bed_availability(unit_type, facility)                  [0-1]  × 0.25
  criterion_3 = distance_score(sending_facility, receiving_facility)   [0-1]  × 0.15
  criterion_4 = insurance_match(patient_insurance, facility_networks)  [0-1]  × 0.15
  criterion_5 = historical_acceptance_rate(facility, transfer_type)    [0-1]  × 0.10
  criterion_6 = patient_preference(if stated)                          [0-1]  × 0.05

Output: Top N facilities ranked by score with explanation
```

---

### 3.3 Integration Services

#### FHIR Gateway
**Responsibility**: Standardized interface to external EHR systems.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ IPTC Services│────▶│ FHIR Gateway  │────▶│ EHR FHIR Server │
│              │◀────│               │◀────│ (Epic/Cerner)   │
└─────────────┘     │  • Auth       │     └─────────────────┘
                    │  • Transform  │
                    │  • Cache      │
                    │  • Rate Limit │
                    │  • Retry      │
                    └──────────────┘
```

**Supported FHIR Operations**:
| Operation | FHIR Resource | Use Case |
|---|---|---|
| `GET /Patient/{id}` | Patient | Demographics |
| `GET /Encounter?patient={id}&status=in-progress` | Encounter | Current visit |
| `GET /Condition?patient={id}&encounter={id}` | Condition | Active diagnoses |
| `GET /Observation?patient={id}&category=vital-signs` | Observation | Latest vitals |
| `GET /MedicationRequest?patient={id}&status=active` | MedicationRequest | Current meds |
| `GET /DiagnosticReport?patient={id}&encounter={id}` | DiagnosticReport | Lab/imaging results |
| `GET /AllergyIntolerance?patient={id}` | AllergyIntolerance | Allergies |

---

#### Notification Service
**Responsibility**: Multi-channel notifications to all stakeholders.

| Channel | Use Case | Technology |
|---|---|---|
| **Push Notification** | MD accept/decline prompt | Firebase Cloud Messaging |
| **SMS** | Backup for MD notification, EMS alerts | Twilio SMS |
| **Email** | Transfer confirmations, reports | SendGrid |
| **In-App** | Real-time dashboard updates | WebSocket (Socket.io) |
| **Webhook** | External system integration | HTTP callbacks |

---

## 4. Data Flow — Complete Transfer Lifecycle

```
Step 1: INITIATION
──────────────────
NP opens IPTC → Selects patient → System fetches FHIR data
→ AI generates SBAR → NP reviews/edits → Submits transfer request

    [NP] ──▶ [Web App] ──▶ [API Gateway] ──▶ [AI Agent Service]
                                                      │
                                              ┌───────┴───────┐
                                              ▼               ▼
                                        [FHIR Gateway]  [SBAR Generator]
                                              │               │
                                              ▼               │
                                        [EHR System]          │
                                              │               │
                                              └───────┬───────┘
                                                      ▼
                                              [Transfer Service]
                                                      │
                                          Event: transfer.initiated
                                                      │
                                                      ▼

Step 2: MATCHING & ROUTING
──────────────────────────
System scores facilities → Sends request to top-ranked facility

                                              [Facility Matcher]
                                                      │
                                              Ranked facility list
                                                      │
                                                      ▼
                                              [Transfer Service]
                                                      │
                                          Event: transfer.pending_review
                                                      │
                                                      ▼

Step 3: ACCEPTANCE
──────────────────
Transfer coordinator receives → Pages MD → MD reviews SBAR → Accepts

                                              [Notification Service]
                                                      │
                                            ┌─────────┴─────────┐
                                            ▼                   ▼
                                     [Push to MD]        [Dashboard Alert]
                                            │
                                            ▼
                                     [MD Reviews SBAR]
                                            │
                                     Accepts / Declines
                                            │
                                            ▼
                                     [Transfer Service]
                                            │
                                  Event: transfer.accepted
                                            │
                                            ▼

Step 4: COMPLIANCE CHECK
────────────────────────
System verifies all EMTALA requirements are met

                                     [Compliance Service]
                                            │
                                   All checks passed?
                                      │           │
                                     YES          NO
                                      │           │
                                      ▼           ▼
                               Proceed to    Block & notify
                               transport     NP of missing items

Step 5: TRANSPORT
─────────────────
Transport dispatched → EMS picks up → In transit → Arrived

                                     [Transport Service]
                                            │
                                    ┌───────┴───────┐
                                    ▼               ▼
                             [EMS Dispatch]   [Status Tracker]
                                    │               │
                              GPS Updates      Dashboard Updates
                                    │               │
                                    └───────┬───────┘
                                            │
                                  Event: transfer.completed
```

---

## 5. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Cloud (HIPAA-Eligible)                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Azure Kubernetes Service (AKS)               │   │
│  │                                                           │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │ Transfer   │ │ AI Agent   │ │ Facility   │           │   │
│  │  │ Service    │ │ Service    │ │ Service    │           │   │
│  │  │ (3 pods)   │ │ (3 pods)   │ │ (2 pods)   │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘           │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │ Compliance │ │ FHIR       │ │ Notification│           │   │
│  │  │ Service    │ │ Gateway    │ │ Service     │           │   │
│  │  │ (2 pods)   │ │ (2 pods)   │ │ (2 pods)    │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘           │   │
│  │  ┌────────────┐ ┌────────────┐                           │   │
│  │  │ Transport  │ │ Analytics  │                           │   │
│  │  │ Service    │ │ Service    │                           │   │
│  │  │ (2 pods)   │ │ (2 pods)   │                           │   │
│  │  └────────────┘ └────────────┘                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │ Azure DB for │  │ Azure Cache  │  │ Azure Blob        │     │
│  │ PostgreSQL   │  │ for Redis    │  │ Storage            │     │
│  │ (Flexible)   │  │              │  │ (HIPAA-encrypted)  │     │
│  └──────────────┘  └──────────────┘  └───────────────────┘     │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │ Azure OpenAI │  │ Azure Event  │  │ Azure Monitor     │     │
│  │ (GPT-4)      │  │ Hubs (Kafka) │  │ + Log Analytics   │     │
│  └──────────────┘  └──────────────┘  └───────────────────┘     │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Azure Health │  │ Azure Key    │                             │
│  │ Data Services│  │ Vault        │                             │
│  │ (FHIR Server)│  │ (Secrets)    │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                              │
│                                                                   │
│  Layer 1: NETWORK                                                │
│  ├── Azure Virtual Network with subnet isolation                 │
│  ├── Network Security Groups (NSGs) per subnet                   │
│  ├── Azure DDoS Protection                                       │
│  └── Private endpoints for all PaaS services                     │
│                                                                   │
│  Layer 2: IDENTITY                                               │
│  ├── Azure AD B2C for user authentication                        │
│  ├── SMART on FHIR for EHR SSO                                  │
│  ├── OAuth 2.0 + OIDC for API access                            │
│  ├── Managed identities for service-to-service auth             │
│  └── RBAC with principle of least privilege                      │
│                                                                   │
│  Layer 3: DATA                                                   │
│  ├── TLS 1.3 for all data in transit                             │
│  ├── AES-256 encryption at rest (Azure-managed keys)             │
│  ├── Column-level encryption for PII/PHI fields                  │
│  ├── Data masking in non-production environments                 │
│  └── Azure Key Vault for all secrets and certificates            │
│                                                                   │
│  Layer 4: APPLICATION                                            │
│  ├── Input validation and sanitization                           │
│  ├── OWASP Top 10 protections                                    │
│  ├── Content Security Policy (CSP) headers                       │
│  ├── Rate limiting per user/organization                         │
│  └── Automated vulnerability scanning (Snyk/Dependabot)         │
│                                                                   │
│  Layer 5: AUDIT                                                  │
│  ├── Immutable audit log for all PHI access                      │
│  ├── Azure Monitor + Log Analytics                               │
│  ├── SIEM integration (Microsoft Sentinel)                       │
│  ├── Automated anomaly detection                                 │
│  └── 7-year audit log retention                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Reliability & Disaster Recovery

| Aspect | Strategy |
|---|---|
| **High Availability** | Multi-AZ deployment in Azure; 3+ replicas per service |
| **Database** | Azure PostgreSQL with zone-redundant HA; read replicas |
| **Failover** | Automatic failover for DB and cache; health check-based pod restart |
| **Backup** | Daily automated backups; 30-day retention; geo-redundant |
| **DR** | Paired Azure region (e.g., East US ↔ West US); RPO <1 min, RTO <15 min |
| **Circuit Breaker** | Resilience4j / Polly for external service calls |
| **Graceful Degradation** | If AI service is down, fall back to manual transfer form |
| **Chaos Engineering** | Periodic fault injection to test resilience |

---

## 8. Observability

| Pillar | Tool | Purpose |
|---|---|---|
| **Metrics** | Azure Monitor + Prometheus + Grafana | Service health, latency, throughput, error rates |
| **Logging** | Structured JSON logs → Azure Log Analytics | Centralized searchable logs |
| **Tracing** | OpenTelemetry → Azure Application Insights | Distributed request tracing across services |
| **Alerting** | Azure Alerts + PagerDuty | On-call rotation for critical issues |
| **Dashboards** | Grafana | Operational dashboards per service |

**Key SLIs (Service Level Indicators)**:
- Transfer API latency p99 < 500ms
- SBAR generation time p95 < 10s
- System availability > 99.95%
- Error rate < 0.1%
- Kafka consumer lag < 1000 messages
