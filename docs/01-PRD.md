# Product Requirements Document (PRD)
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026  
**Status**: Draft

---

## 1. Executive Summary

The Intelligent Patient Transfer Coordinator (IPTC) is an AI-powered platform that automates the interfacility patient transfer process. It replaces the current manual, phone-based coordination workflow with an intelligent system that generates clinical summaries, matches patients to appropriate receiving facilities, manages the acceptance workflow, ensures regulatory compliance, and tracks transfers in real-time.

**Primary Goal**: Reduce average transfer coordination time from **2+ hours to under 15 minutes** while improving patient safety and regulatory compliance.

---

## 2. Target Users (Personas)

### Persona 1: Nurse Practitioner (NP) — "Sarah"
- **Role**: NP at an urgent care center / small community hospital
- **Age**: 32, 6 years experience
- **Pain Points**:
  - Spends 30–90 min on hold with transfer centers
  - Must verbally relay complex clinical data, risking miscommunication
  - Manually compiles transfer paperwork while managing other patients
  - Gets transfers rejected, must start over with another hospital
- **Goals**:
  - Initiate transfers quickly without leaving the bedside
  - Ensure clinical data is accurately communicated
  - Track transfer status without repeated phone calls

### Persona 2: Transfer Center Coordinator — "Maria"
- **Role**: RN working in a hospital transfer center
- **Age**: 45, 15 years experience
- **Pain Points**:
  - Handles 40–80 transfer calls per shift
  - Manually pages physicians and waits for callbacks
  - Re-enters data into multiple systems (bed board, EHR, transport)
  - Manages complex multi-party communication
- **Goals**:
  - Receive structured, complete transfer requests digitally
  - Auto-route requests to appropriate on-call physicians
  - Track all active transfers on a single dashboard

### Persona 3: Accepting Physician — "Dr. Patel"
- **Role**: Hospitalist / On-call specialist at receiving hospital
- **Age**: 38, attending physician
- **Pain Points**:
  - Receives incomplete clinical information via phone
  - Interrupted by transfer pages during patient care
  - Must make accept/decline decisions with limited data
- **Goals**:
  - Review complete, structured clinical summary before accepting
  - Accept or decline transfers via mobile with one tap
  - See only transfers relevant to their specialty/service

### Persona 4: EMS / Transport Crew — "Mike"
- **Role**: Paramedic, ALS ambulance crew
- **Pain Points**:
  - Receives vague pickup instructions
  - Doesn't know patient acuity until arrival
  - No visibility into receiving facility readiness
- **Goals**:
  - Receive detailed patient summary and transport requirements before dispatch
  - Know exact pickup/dropoff locations and contacts
  - Report transport status in real-time

### Persona 5: Hospital Administrator — "Linda"
- **Role**: VP of Operations at a regional hospital system
- **Pain Points**:
  - No visibility into transfer volumes, times, or outcomes
  - Cannot identify bottlenecks in the transfer process
  - Compliance risk from undocumented transfers
- **Goals**:
  - Dashboard with transfer KPIs and trends
  - Compliance audit trail for all transfers
  - Capacity planning based on transfer patterns

---

## 3. User Stories

### Epic 1: Transfer Initiation

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-101 | As an NP, I want to initiate a transfer request from a web or mobile interface so that I don't have to make phone calls | P0 | NP can create transfer request in <3 min |
| US-102 | As an NP, I want the system to auto-populate patient data from the EHR so that I don't re-enter information | P0 | Demographics, vitals, labs, meds auto-filled from FHIR |
| US-103 | As an NP, I want the AI to generate an SBAR summary so that clinical handoff is accurate and complete | P0 | SBAR generated from EHR data, editable by NP before sending |
| US-104 | As an NP, I want to specify the reason for transfer and urgency level so that the request is properly prioritized | P0 | Urgency levels: Emergent, Urgent, Routine |
| US-105 | As an NP, I want to use voice to dictate additional clinical context so that I can add nuance beyond structured data | P1 | Voice-to-text transcription added to clinical notes |

### Epic 2: Facility Matching

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-201 | As an NP, I want the system to recommend receiving facilities based on patient needs so that I target the right hospital | P0 | Top 3 facilities ranked by match score |
| US-202 | As an NP, I want to see real-time bed availability at potential receiving facilities so that I avoid rejected transfers | P1 | Bed counts updated within 15 min |
| US-203 | As an NP, I want the system to check insurance network compatibility so that financial barriers are identified early | P1 | Insurance eligibility verified before sending request |
| US-204 | As an NP, I want to see distance and ETA to each facility so that I factor in transport time | P0 | Driving/flight distance and estimated transport time shown |
| US-205 | As the system, I should factor in specialty capabilities (cath lab, neuro IR, burn unit, etc.) when matching | P0 | Facility capability database with real-time status |

### Epic 3: Transfer Acceptance Workflow

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-301 | As a transfer coordinator, I want to receive structured transfer requests digitally so that I don't rely on phone calls | P0 | Request appears on dashboard with complete SBAR |
| US-302 | As a transfer coordinator, I want the system to auto-notify the on-call physician so that I don't manually page | P0 | Push notification + SMS to on-call MD within 30 sec |
| US-303 | As an accepting physician, I want to review the SBAR on my mobile device so that I can decide quickly | P0 | Mobile-optimized clinical summary view |
| US-304 | As an accepting physician, I want to accept or decline with one tap and optional notes so that the process is fast | P0 | Accept/Decline with reason; response time tracked |
| US-305 | As an NP, I want automatic escalation to the next facility if declined so that I don't start over manually | P1 | Auto-send to next ranked facility within 2 min of decline |

### Epic 4: Compliance & Documentation

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-401 | As the system, I must generate EMTALA-compliant transfer certification so that the facility avoids violations | P0 | Certification form auto-generated with required fields |
| US-402 | As an NP, I want the system to generate the transfer consent form so that I only need to collect the signature | P0 | Digital consent form with e-signature capability |
| US-403 | As the system, I must compile a complete transfer packet (summary, labs, imaging, ECG) automatically | P0 | PDF packet generated from EHR data + uploaded documents |
| US-404 | As an administrator, I want a complete audit trail for every transfer so that we can demonstrate compliance | P0 | Every action timestamped with user, role, and facility |
| US-405 | As the system, I must verify that required EMTALA steps are completed before approving transport dispatch | P0 | Checklist enforcement: MSE, stabilization, certification, consent |

### Epic 5: Transport Coordination

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-501 | As the system, I should recommend the appropriate transport level (BLS, ALS, CCT, air) based on patient acuity | P0 | Transport level recommendation with clinical rationale |
| US-502 | As a transfer coordinator, I want to dispatch transport with one click so that I don't make separate calls | P1 | Integration with EMS dispatch (CAD) systems |
| US-503 | As an EMS crew member, I want to receive the patient summary and transport requirements on my device | P1 | Mobile-friendly patient summary pushed to EMS |
| US-504 | As all stakeholders, I want real-time transport tracking (en route, on scene, transporting, arrived) | P1 | GPS-based status updates visible on dashboard |

### Epic 6: Transfer Dashboard & Analytics

| ID | User Story | Priority | Acceptance Criteria |
|---|---|---|---|
| US-601 | As a transfer coordinator, I want a real-time dashboard showing all active transfers and their status | P0 | Dashboard with status: Initiated, Pending, Accepted, In-Transit, Completed |
| US-602 | As an NP, I want to see the status of my transfer request in real-time so I can update the patient/family | P0 | Status visible on web and mobile |
| US-603 | As an administrator, I want analytics on transfer volumes, times, acceptance rates, and outcomes | P1 | Monthly/quarterly reports with drill-down capability |
| US-604 | As an administrator, I want to identify bottlenecks (long acceptance times, frequent declines by facility) | P1 | Heat maps and trend analysis |
| US-605 | As the system, I want to track "door-to-departure" and "door-to-door" times for quality improvement | P1 | Automated time tracking from initiation to completion |

---

## 4. Feature Specifications

### 4.1 AI Transfer Agent

The core differentiator — a conversational AI agent that assists NPs in initiating transfers.

**Capabilities**:
- Guides NP through a structured transfer request via chat or voice
- Pulls patient data from EHR via FHIR APIs
- Generates SBAR summary using LLM grounded in structured data
- Suggests appropriate receiving facilities
- Communicates with receiving facility's system (AI-to-system) or transfer coordinator (AI-assisted)
- Answers NP questions about transfer process, policies, EMTALA requirements

**Constraints**:
- Must NEVER make clinical decisions (accept/decline is always human)
- Must NEVER fabricate clinical data — all data grounded in EHR
- Must clearly flag when information is missing or uncertain
- Must support human override at every step

### 4.2 SBAR Generator

**Input Sources**:
- FHIR Patient, Encounter, Condition, Observation, MedicationRequest, DiagnosticReport resources
- NP-provided additional context (voice or text)
- Uploaded documents (ECG images, radiology reports)

**Output**:
- Structured SBAR summary (text + structured data)
- Editable by NP before submission
- Versioned — every edit tracked

### 4.3 Facility Matching Engine

**Matching Criteria** (weighted scoring):

| Criterion | Weight | Source |
|---|---|---|
| Specialty/service capability | 30% | Facility capability database |
| Bed availability | 25% | Real-time bed board integration or manual update |
| Distance / transport time | 15% | Geolocation API |
| Insurance network | 15% | Insurance eligibility API |
| Historical acceptance rate | 10% | IPTC analytics |
| Patient preference | 5% | NP input |

### 4.4 Compliance Engine

**EMTALA Checklist** (enforced before transport dispatch):
- [ ] Medical screening examination completed
- [ ] Patient stabilized (or physician certifies benefits outweigh risks)
- [ ] Physician transfer certification signed
- [ ] Informed consent obtained (or documented inability to consent)
- [ ] Receiving facility contacted and accepted
- [ ] Receiving facility has capacity and capability
- [ ] Appropriate transport arranged
- [ ] All available medical records sent with patient

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Availability** | 99.95% uptime (healthcare-grade) |
| **Latency** | API response <500ms; SBAR generation <10 sec |
| **Scalability** | Support 10,000+ concurrent transfers |
| **Security** | HIPAA-compliant; SOC 2 Type II; encryption at rest (AES-256) and in transit (TLS 1.3) |
| **Audit** | Complete audit trail for all actions; 7-year retention |
| **Interoperability** | HL7 FHIR R4 compliant; support Epic, Cerner, MEDITECH, Allscripts |
| **Accessibility** | WCAG 2.1 AA compliant |
| **Mobile** | Responsive web + native mobile (iOS/Android) |
| **Disaster Recovery** | RPO <1 min, RTO <15 min |

---

## 6. MVP Scope (Phase 1)

For the initial release, we focus on the **core transfer workflow with simulated EHR data**:

### In Scope (MVP)
- AI Transfer Agent (chat-based, text only)
- SBAR generator from simulated patient data
- Facility matching with mock facility database
- Transfer request → acceptance workflow (web dashboard)
- EMTALA compliance checklist enforcement
- Transfer status tracking
- Basic analytics (transfer time, acceptance rate)

### Out of Scope (Future Phases)
- Voice agent (Twilio integration)
- Live EHR/FHIR integration (use sandbox first)
- Real EMS dispatch integration
- Insurance eligibility verification
- Mobile native apps (responsive web only for MVP)
- AI-to-AI communication between facilities
- Real-time bed board integration

---

## 7. Success Metrics

| Metric | Current State | MVP Target | Long-term Target |
|---|---|---|---|
| **Transfer coordination time** | 2–4 hours | <30 min | <15 min |
| **Clinical data accuracy** | ~80% (verbal) | >95% (structured) | >99% |
| **EMTALA compliance rate** | ~85% | 100% | 100% |
| **Transfer rejection rate** | ~25% | <15% | <10% |
| **NP satisfaction** | Low | >4.0/5.0 | >4.5/5.0 |
| **Time to first facility contact** | 15–45 min | <2 min | <1 min |

---

## 8. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| AI generates incorrect clinical data | Medium | Critical | Ground all LLM output in structured EHR data; NP review before send |
| EMTALA violation due to system error | Low | Critical | Hard-coded compliance checks; cannot proceed without all steps |
| EHR integration delays | High | High | Start with FHIR sandbox; mock data for MVP |
| Physician adoption resistance | Medium | High | Keep physician role minimal (one-tap accept/decline) |
| HIPAA breach | Low | Critical | HIPAA-eligible infrastructure; penetration testing; audit logs |
| Regulatory changes | Low | Medium | Modular compliance engine; configurable rules |
