# AI Agent Design Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026

---

## 1. Agent Architecture Overview

The AI Agent is the core differentiator of IPTC — a conversational assistant that guides Nurse Practitioners through the transfer process, generates clinical summaries, and coordinates with receiving facilities.

```
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENT SYSTEM                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  ORCHESTRATOR                           │ │
│  │                                                         │ │
│  │  • Session management (conversation state)              │ │
│  │  • Intent classification                                │ │
│  │  • Agent routing                                        │ │
│  │  • Response assembly                                    │ │
│  │  • Safety guardrails enforcement                        │ │
│  └──────────┬──────────────────────┬──────────────────────┘ │
│             │                      │                         │
│    ┌────────▼────────┐   ┌────────▼────────┐               │
│    │  TRANSFER FLOW   │   │  QUESTION        │               │
│    │  AGENT           │   │  ANSWERING AGENT │               │
│    │                  │   │                   │               │
│    │  Guides NP       │   │  Answers policy,  │               │
│    │  through transfer│   │  procedure, and   │               │
│    │  initiation      │   │  regulatory       │               │
│    │                  │   │  questions         │               │
│    └────────┬────────┘   └────────┬──────────┘               │
│             │                      │                         │
│    ┌────────▼──────────────────────▼──────────┐             │
│    │            TOOL EXECUTION LAYER           │             │
│    │                                            │             │
│    │  ┌──────────┐ ┌──────────┐ ┌───────────┐ │             │
│    │  │ FHIR     │ │ SBAR     │ │ Facility  │ │             │
│    │  │ Client   │ │ Generator│ │ Matcher   │ │             │
│    │  └──────────┘ └──────────┘ └───────────┘ │             │
│    │  ┌──────────┐ ┌──────────┐ ┌───────────┐ │             │
│    │  │ Transfer │ │ Compliance│ │ Knowledge │ │             │
│    │  │ API      │ │ Checker  │ │ Base (RAG)│ │             │
│    │  └──────────┘ └──────────┘ └───────────┘ │             │
│    └────────────────────────────────────────────┘             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  SAFETY LAYER                           │ │
│  │                                                         │ │
│  │  • PHI access logging                                   │ │
│  │  • Clinical decision guardrails                         │ │
│  │  • Hallucination detection                              │ │
│  │  • Output validation                                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. LLM Configuration

### Model Selection
| Parameter | Value | Rationale |
|---|---|---|
| **Model** | Azure OpenAI GPT-4 (latest) | HIPAA BAA available; best reasoning capability |
| **Temperature** | 0.1 | Low creativity — clinical accuracy is paramount |
| **Max Tokens** | 4,096 | Sufficient for SBAR + conversation |
| **Top P** | 0.95 | Slight diversity in language, not facts |
| **Frequency Penalty** | 0.0 | No penalty — medical terms should repeat |
| **Presence Penalty** | 0.0 | Same as above |
| **Stop Sequences** | None | Let model complete naturally |

### Fallback Strategy
```
Primary:   Azure OpenAI GPT-4 (East US)
Fallback:  Azure OpenAI GPT-4 (West US)  — if primary >5s or 5xx
Emergency: Template-based responses       — if all LLM calls fail
```

---

## 3. System Prompt Design

### Master System Prompt

```
You are the Intelligent Patient Transfer Coordinator (IPTC) AI Assistant. You help 
Nurse Practitioners and clinical staff coordinate interfacility patient transfers 
safely and efficiently.

## YOUR ROLE
- You are a clinical workflow assistant, NOT a clinician.
- You help gather, organize, and communicate clinical information for transfers.
- You generate SBAR summaries from structured EHR data.
- You recommend receiving facilities based on patient needs and availability.
- You track transfer status and ensure compliance requirements are met.

## CRITICAL SAFETY RULES (NEVER VIOLATE)
1. NEVER make clinical decisions. You do not diagnose, prescribe, or determine 
   treatment. All clinical decisions are made by licensed clinicians.
2. NEVER fabricate clinical data. All vitals, labs, medications, and diagnoses MUST 
   come from the EHR (FHIR) data or be explicitly stated by the clinician. If data 
   is missing, say "This information is not available in the current EHR data."
3. NEVER advise whether to transfer or not. The decision to transfer is a clinical 
   judgment made by the treating provider.
4. NEVER share patient information with unauthorized parties. Only communicate PHI 
   within the transfer workflow to involved clinical staff.
5. ALWAYS flag uncertainty. If you are unsure about any clinical data, explicitly 
   state your uncertainty and ask the clinician to verify.
6. ALWAYS require human review of generated SBAR summaries before they are sent 
   to a receiving facility.

## YOUR CAPABILITIES (TOOLS)
You have access to the following tools:
- fetch_patient_data: Retrieve patient information from EHR via FHIR
- generate_sbar: Create SBAR clinical summary from structured data
- search_facilities: Find and rank potential receiving facilities
- create_transfer: Initiate a transfer request
- check_compliance: Verify EMTALA compliance status
- get_transfer_status: Check current transfer status
- search_knowledge_base: Look up transfer policies and procedures

## COMMUNICATION STYLE
- Be concise and professional — clinicians are busy.
- Use clinical terminology appropriately but don't be overly verbose.
- Present information in structured formats (bullet points, tables) when possible.
- Always confirm critical information before proceeding with actions.
- Proactively suggest next steps in the transfer workflow.

## CONVERSATION FLOW
1. Identify the patient (MRN, name, or search)
2. Understand the reason for transfer and urgency
3. Pull clinical data from EHR
4. Generate and present SBAR for review
5. Recommend receiving facilities
6. Initiate transfer request upon NP approval
7. Track compliance checklist
8. Coordinate transport when ready
```

---

## 4. Tool Definitions (Function Calling)

### Tool: fetch_patient_data
```json
{
  "name": "fetch_patient_data",
  "description": "Retrieves patient clinical data from the EHR system via FHIR APIs. Returns demographics, active conditions, current medications, recent vitals, lab results, and imaging reports for the current encounter.",
  "parameters": {
    "type": "object",
    "properties": {
      "patient_identifier": {
        "type": "string",
        "description": "Patient MRN, FHIR ID, or name search string"
      },
      "identifier_type": {
        "type": "string",
        "enum": ["mrn", "fhir_id", "name_search"],
        "description": "Type of identifier provided"
      },
      "facility_id": {
        "type": "string",
        "description": "UUID of the facility where the patient is located"
      },
      "data_categories": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["demographics", "conditions", "medications", "vitals", "labs", "imaging", "allergies", "all"]
        },
        "description": "Categories of clinical data to retrieve"
      }
    },
    "required": ["patient_identifier", "identifier_type", "facility_id"]
  }
}
```

### Tool: generate_sbar
```json
{
  "name": "generate_sbar",
  "description": "Generates a structured SBAR (Situation-Background-Assessment-Recommendation) clinical summary from patient data. The summary MUST be reviewed and approved by the NP before sending to a receiving facility.",
  "parameters": {
    "type": "object",
    "properties": {
      "patient_id": {
        "type": "string",
        "description": "Patient UUID in IPTC system"
      },
      "reason_for_transfer": {
        "type": "string",
        "description": "Clinical reason for the transfer"
      },
      "urgency": {
        "type": "string",
        "enum": ["EMERGENT", "URGENT", "ROUTINE"]
      },
      "additional_context": {
        "type": "string",
        "description": "Additional clinical context provided by the NP not in the EHR"
      },
      "requested_specialty": {
        "type": "string",
        "description": "Specialty or service needed at receiving facility"
      }
    },
    "required": ["patient_id", "reason_for_transfer", "urgency"]
  }
}
```

### Tool: search_facilities
```json
{
  "name": "search_facilities",
  "description": "Searches for and ranks potential receiving facilities based on patient needs, bed availability, distance, insurance, and historical acceptance rates. Returns top matched facilities.",
  "parameters": {
    "type": "object",
    "properties": {
      "transfer_id": {
        "type": "string",
        "description": "Transfer request UUID (for context)"
      },
      "required_specialty": {
        "type": "string",
        "description": "Required medical specialty"
      },
      "required_services": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Required services (e.g., CATH_LAB, NEURO_IR)"
      },
      "required_unit_type": {
        "type": "string",
        "description": "Required unit type (ICU, CCU, TELE, etc.)"
      },
      "insurance_provider": {
        "type": "string",
        "description": "Patient's insurance provider for network check"
      },
      "max_distance_miles": {
        "type": "integer",
        "description": "Maximum search radius in miles (default: 50)"
      },
      "max_results": {
        "type": "integer",
        "description": "Number of results to return (default: 5)"
      }
    },
    "required": ["required_specialty"]
  }
}
```

### Tool: create_transfer
```json
{
  "name": "create_transfer",
  "description": "Creates a new transfer request and sends it to the selected receiving facility. Requires NP confirmation before execution.",
  "parameters": {
    "type": "object",
    "properties": {
      "patient_id": { "type": "string" },
      "receiving_facility_id": { "type": "string" },
      "urgency": { "type": "string", "enum": ["EMERGENT", "URGENT", "ROUTINE"] },
      "reason_for_transfer": { "type": "string" },
      "clinical_summary_id": { "type": "string" },
      "requested_specialty": { "type": "string" },
      "requested_unit_type": { "type": "string" }
    },
    "required": ["patient_id", "receiving_facility_id", "urgency", "reason_for_transfer", "clinical_summary_id"]
  }
}
```

### Tool: check_compliance
```json
{
  "name": "check_compliance",
  "description": "Checks the EMTALA compliance status for a transfer request. Returns which checklist items are completed and which are pending.",
  "parameters": {
    "type": "object",
    "properties": {
      "transfer_id": {
        "type": "string",
        "description": "Transfer request UUID"
      }
    },
    "required": ["transfer_id"]
  }
}
```

### Tool: search_knowledge_base
```json
{
  "name": "search_knowledge_base",
  "description": "Searches the transfer policy and procedure knowledge base using RAG. Use this for questions about transfer policies, EMTALA requirements, insurance procedures, or facility-specific protocols.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query"
      },
      "category": {
        "type": "string",
        "enum": ["emtala", "hipaa", "transfer_policy", "insurance", "transport", "general"],
        "description": "Category to narrow search"
      }
    },
    "required": ["query"]
  }
}
```

---

## 5. Conversation Flows

### Flow 1: Standard Transfer Initiation

```
NP: "I need to transfer a patient"
    │
    ▼
AGENT: "I can help with that. Could you provide the patient's MRN or name 
        so I can pull their information?"
    │
    ▼
NP: "MRN 12345"
    │
    ▼
AGENT: [calls fetch_patient_data(mrn="12345")]
       "I found the patient:
        • John Doe, 67M, DOB 03/15/1958
        • Current encounter at Urgent Care East
        • Active conditions: Acute chest pain, HTN, DM2
        
        What is the reason for transfer and how urgent is it?"
    │
    ▼
NP: "STEMI on ECG, needs cath lab, emergent"
    │
    ▼
AGENT: [calls generate_sbar(patient_id=..., reason="STEMI requiring cath lab", 
        urgency="EMERGENT")]
       "I've generated the SBAR summary. Please review:
        
        **SITUATION**: 67-year-old male with acute inferior STEMI...
        **BACKGROUND**: PMH of HTN, DM2, prior MI...
        **ASSESSMENT**: BP 160/95, HR 110, Troponin 0.8...
        **RECOMMENDATION**: Emergent transfer for cardiac cath...
        
        Is this accurate? Would you like to make any changes?"
    │
    ▼
NP: "Looks good, also add that family is at bedside"
    │
    ▼
AGENT: [updates SBAR with additional note]
       "Updated. Now let me find the best facilities.
        [calls search_facilities(specialty="INTERVENTIONAL_CARDIOLOGY", 
         services=["CATH_LAB"], unit="CCU")]
        
        **Top Matches:**
        1. 🏥 Metro General (8.2 mi) — Score: 92.5
           CCU beds: 2 available | Cath lab: OPEN | In-network ✓
        2. 🏥 University Medical (15.7 mi) — Score: 85.3
           CCU beds: 1 available | Cath lab: OPEN | In-network ✓
        3. 🏥 St. Mary's (22.1 mi) — Score: 78.1
           CCU beds: 3 available | Cath lab: OPEN | Out-of-network ✗
        
        Which facility would you like to send the request to?"
    │
    ▼
NP: "Metro General"
    │
    ▼
AGENT: "Sending transfer request to Metro General Hospital.
        [calls create_transfer(...)]
        
        ✅ Transfer request TR-20260608-0001 sent to Metro General.
        
        **Status**: PENDING_REVIEW
        **Urgency**: EMERGENT
        
        The on-call cardiologist has been notified. I'll update you 
        as soon as they respond.
        
        **Meanwhile, let's check your EMTALA compliance checklist:**
        [calls check_compliance(transfer_id=...)]
        
        ✅ MSE completed
        ✅ Stabilization attempted
        ⬜ MD certification — needs physician signature
        ⬜ Patient consent — needs signature
        ✅ Receiving facility contacted
        ⬜ Transport arranged — pending acceptance
        ⬜ Records prepared
        
        Would you like me to generate the certification and consent forms?"
```

### Flow 2: Transfer Declined — Auto-Reroute

```
AGENT: "⚠️ Update on TR-20260608-0001:
        
        Metro General has **DECLINED** the transfer.
        Reason: No CCU beds available (went to divert 5 min ago)
        
        I'm automatically routing to your next best match:
        **University Medical Center** (15.7 mi, Score: 85.3)
        
        Request sent. On-call physician notified.
        
        Would you like me to also contact St. Mary's as a backup?"
```

### Flow 3: Policy Question

```
NP: "Does EMTALA require consent if the patient is unconscious?"
    │
    ▼
AGENT: [calls search_knowledge_base(query="EMTALA consent unconscious patient", 
        category="emtala")]
       "Under EMTALA, if a patient is unable to provide informed consent 
        (unconscious, altered mental status), the transfer can proceed if:
        
        1. A physician certifies that the medical benefits of transfer 
           outweigh the risks
        2. The receiving facility has accepted the patient
        3. The transfer is medically necessary
        
        You should document the patient's inability to consent and the 
        clinical justification in the transfer record. If a legal 
        representative (spouse, POA) is available, their consent should 
        be obtained if time permits.
        
        Shall I update the compliance record to note that the patient 
        is unable to consent?"
```

---

## 6. SBAR Generation Pipeline

### Step-by-Step Process

```
Step 1: DATA COLLECTION
────────────────────────
┌──────────────────────────────────────────────┐
│ FHIR API Calls (parallel)                     │
│                                               │
│ GET /Patient/{id}           → demographics    │
│ GET /Encounter?patient={id} → current visit   │
│ GET /Condition?patient={id} → diagnoses       │
│ GET /Observation?patient={id}&category=       │
│     vital-signs             → latest vitals   │
│ GET /Observation?patient={id}&category=       │
│     laboratory              → recent labs     │
│ GET /MedicationRequest?patient={id}&          │
│     status=active           → current meds    │
│ GET /AllergyIntolerance?patient={id}          │
│                             → allergies       │
│ GET /DiagnosticReport?patient={id}            │
│                             → imaging/ECG     │
└──────────────────────────────────────────────┘

Step 2: DATA STRUCTURING
────────────────────────
Raw FHIR resources → Normalized JSON structure
{
  "patient": { "name": "...", "age": 67, "gender": "M", ... },
  "encounter": { "type": "...", "chief_complaint": "...", ... },
  "conditions": [ { "display": "...", "status": "active", ... } ],
  "vitals": { "bp": "160/95", "hr": 110, ... },
  "labs": [ { "name": "Troponin", "value": 0.8, ... } ],
  "medications": [ { "name": "Heparin", "dose": "1000 u/hr", ... } ],
  "allergies": [ ... ],
  "imaging": [ { "type": "ECG", "finding": "ST elevation...", ... } ]
}

Step 3: LLM GENERATION
──────────────────────
Structured data + NP context + SBAR prompt template → LLM → SBAR text

Step 4: VALIDATION
──────────────────
┌────────────────────────────────────────────────┐
│ Post-generation checks:                         │
│                                                  │
│ ✓ All vitals in SBAR match source FHIR data    │
│ ✓ All lab values in SBAR match source data      │
│ ✓ All medications in SBAR match source data     │
│ ✓ No clinical assertions not grounded in data   │
│ ✓ Patient identifiers are correct               │
│ ✓ No hallucinated conditions or medications     │
└────────────────────────────────────────────────┘

Step 5: NP REVIEW
─────────────────
SBAR presented to NP → NP edits if needed → NP approves → Version saved
```

### SBAR Prompt Template

```
Given the following structured patient data, generate a clinical SBAR 
(Situation-Background-Assessment-Recommendation) transfer summary.

RULES:
1. Use ONLY the data provided below. Do NOT infer, assume, or add any 
   clinical information not present in the data.
2. If a data field is missing or empty, note it as "Not available" in 
   the relevant section.
3. Present vitals, labs, and medications EXACTLY as they appear in the 
   source data. Do not round, convert, or modify values.
4. The Recommendation section should state the transfer need factually. 
   Do NOT make clinical recommendations about treatment.
5. Use concise, professional clinical language.
6. Format each section clearly with headers.

PATIENT DATA:
{structured_patient_json}

ADDITIONAL CONTEXT FROM CLINICIAN:
{np_additional_context}

TRANSFER DETAILS:
- Reason for transfer: {reason_for_transfer}
- Urgency: {urgency}
- Requested specialty: {requested_specialty}
- Sending facility: {sending_facility_name}

Generate the SBAR summary with sections: SITUATION, BACKGROUND, 
ASSESSMENT, and RECOMMENDATION.
```

---

## 7. Hallucination Prevention

### Multi-Layer Defense

```
Layer 1: GROUNDING
──────────────────
• All clinical data comes from FHIR APIs (structured, verified)
• LLM receives pre-structured JSON, not free-text notes
• Prompt explicitly forbids adding data not in the source

Layer 2: VALIDATION
───────────────────
Post-generation automated checks:
• Extract all numbers from SBAR text → compare to source data
• Extract all medication names → compare to source medication list
• Extract all condition names → compare to source condition list
• Flag any entity in SBAR not found in source data

Layer 3: HUMAN REVIEW
─────────────────────
• NP must review and approve every SBAR before it's sent
• Side-by-side view: SBAR text | Source EHR data
• Edit capability with version tracking
• "Report inaccuracy" button for quality tracking

Layer 4: MONITORING
───────────────────
• Track hallucination rate (NP-reported edits to AI-generated content)
• A/B test prompt variations for accuracy
• Regular prompt tuning based on error patterns
```

---

## 8. RAG Knowledge Base

### Content Indexed

| Category | Content Sources |
|---|---|
| **EMTALA** | CMS regulations, interpretive guidelines, FAQ, case studies |
| **HIPAA** | Privacy Rule, Security Rule, Breach Notification Rule |
| **Transfer Policies** | Facility-specific transfer protocols, agreements |
| **Insurance** | Network directories, pre-authorization requirements |
| **Transport** | BLS/ALS/CCT criteria, air transport guidelines |
| **Clinical Protocols** | STEMI protocol, stroke protocol, trauma criteria |

### RAG Architecture

```
Query → Embedding (text-embedding-3-large) → Vector Search (Azure AI Search)
    → Top-K chunks retrieved → Re-ranked → Injected into LLM context
    → Answer generated with citations
```

| Parameter | Value |
|---|---|
| **Embedding Model** | text-embedding-3-large (3072 dimensions) |
| **Chunk Size** | 512 tokens with 50-token overlap |
| **Top-K Retrieval** | 5 chunks |
| **Re-ranking** | Cross-encoder re-ranker |
| **Vector Store** | Azure AI Search (hybrid: vector + keyword) |

---

## 9. Safety Guardrails

### Input Guardrails
- Reject prompts attempting to override system instructions
- Filter PII/PHI from being sent to external services
- Rate limit per user to prevent abuse

### Output Guardrails
- Block any response that contains clinical diagnoses not from EHR data
- Block any response that recommends specific treatments
- Block any response that advises for/against transfer
- Ensure all PHI in responses is appropriate for the user's role

### Monitoring & Alerting
| Metric | Threshold | Action |
|---|---|---|
| Hallucination rate (NP edits) | >5% of SBARs | Alert + prompt review |
| Safety guardrail triggers | >10/hour | Alert + manual review |
| LLM latency p95 | >15 seconds | Alert + check Azure OpenAI status |
| User-reported inaccuracies | Any | Immediate review + incident report |

---

## 10. Future: Voice Agent (Phase 2)

### Architecture
```
Phone Call (NP) → Twilio → Deepgram STT → Text → AI Agent → Text 
    → Azure TTS → Audio → Twilio → Phone Call (NP)
```

### Key Considerations
- Real-time streaming STT (< 500ms latency)
- Interruption handling (barge-in)
- Clinical terminology recognition (custom vocabulary)
- HIPAA-compliant call recording with consent
- Fallback to human transfer center if AI cannot handle
