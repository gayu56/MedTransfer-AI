# Intelligent Patient Transfer Coordinator (IPTC)

> An AI-powered platform that automates interfacility patient transfer coordination between medical centers and hospitals, reducing transfer times from hours to minutes while ensuring regulatory compliance.

---

## Problem Statement

When patients need to be transferred from a medical center or clinic to a hospital, a complex manual communication process occurs between **Nurse Practitioners (NPs)** and **hospital transfer centers**. This process involves:

- **Long hold times** (10–45 min) calling transfer centers
- **Verbal miscommunication** of critical clinical data
- **Repetitive data entry** across disconnected systems
- **No real-time visibility** into bed/capacity availability
- **Paper/fax-based documentation** leading to lost records
- **Total coordination time**: 45 minutes to 4+ hours per transfer

With **~1.5–2 million interfacility transfers per year in the US**, this inefficiency directly impacts patient outcomes — especially for time-sensitive conditions like STEMI, stroke, and trauma.

## Solution

IPTC is an **AI-native, end-to-end transfer coordination platform** that:

1. **Auto-generates SBAR clinical summaries** from EHR data via FHIR APIs
2. **AI Transfer Agent** conducts structured transfer conversations with NPs and receiving facilities
3. **Intelligent facility matching** based on bed availability, specialty, distance, and insurance
4. **Automated compliance documentation** (EMTALA, consent, transfer records)
5. **Real-time transfer tracking** dashboard for all stakeholders
6. **Transport coordination** with EMS dispatch integration

## Key Features

| Feature | Description |
|---|---|
| **AI Transfer Agent** | Conversational AI (chat + voice) that guides NPs through transfer initiation and communicates with receiving facilities |
| **SBAR Generator** | LLM-powered clinical summary generation grounded in structured EHR data |
| **Facility Matcher** | Real-time matching engine considering capacity, specialty, geography, insurance, and acuity |
| **Compliance Engine** | Automated EMTALA certification, transfer consent, and documentation generation |
| **Transfer Dashboard** | Real-time status tracking for sending facility, receiving facility, transport, and families |
| **EHR Integration** | HL7 FHIR-based bidirectional integration with Epic, Cerner, and other EHR systems |
| **Transport Coordinator** | EMS dispatch integration for BLS/ALS/CCT ambulance and air transport |
| **Analytics & Reporting** | Transfer time metrics, acceptance rates, outcome tracking |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ Web Dashboard │  │ Mobile App   │  │ Voice Interface   │ │
│  │ (React)       │  │ (React Native│  │ (Twilio + STT/TTS)│ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘ │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     API GATEWAY (Kong/AWS)                    │
│          Authentication · Rate Limiting · Routing            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    SERVICE LAYER                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Transfer    │ │ AI Agent   │ │ Facility   │ │ Transport│ │
│  │ Service     │ │ Service    │ │ Matching   │ │ Service  │ │
│  │             │ │ (LLM +     │ │ Service    │ │          │ │
│  │             │ │  RAG)      │ │            │ │          │ │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬─────┘ │
│  ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐ ┌────┴─────┐ │
│  │ Compliance  │ │ SBAR       │ │ Notification│ │ Analytics│ │
│  │ Service     │ │ Generator  │ │ Service     │ │ Service  │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    DATA LAYER                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ PostgreSQL  │ │ Redis      │ │ S3/Blob    │ │ Vector   │ │
│  │ (Primary DB)│ │ (Cache +   │ │ (Documents)│ │ Store    │ │
│  │             │ │  Pub/Sub)  │ │            │ │ (Pinecone│ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                 INTEGRATION LAYER                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ EHR/FHIR   │ │ EMS/CAD    │ │ Insurance  │ │ Telecom  │ │
│  │ (Epic,     │ │ Dispatch   │ │ Eligibility│ │ (Twilio) │ │
│  │  Cerner)   │ │ APIs       │ │ APIs       │ │          │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Documentation

| Document | Description |
|---|---|
| [Product Requirements](docs/01-PRD.md) | Scope, personas, user stories, feature specifications |
| [System Architecture](docs/02-system-architecture.md) | Detailed architecture, component design, data flow |
| [Data Models](docs/03-data-models.md) | Entity schemas, FHIR mapping, database design |
| [API Specification](docs/04-api-specification.md) | REST API endpoints, request/response schemas |
| [AI Agent Design](docs/05-ai-agent-design.md) | Conversation flows, SBAR logic, prompt engineering |
| [Compliance & Security](docs/06-compliance-security.md) | EMTALA, HIPAA, audit logging, security controls |
| [Tech Stack & Infrastructure](docs/07-tech-stack.md) | Technology choices, deployment, CI/CD |

## Tech Stack

- **Backend**: Python 3.12+ / FastAPI
- **Frontend**: React 18 + TypeScript + TailwindCSS + shadcn/ui
- **AI/LLM**: Azure OpenAI (GPT-4) with HIPAA BAA
- **Database**: PostgreSQL 16 + Redis 7
- **EHR Integration**: HL7 FHIR R4
- **Voice**: Twilio + Deepgram (STT) + Azure TTS
- **Infrastructure**: Azure Health Data Services (HIPAA-compliant)
- **Messaging**: Apache Kafka for event streaming

## Regulatory Compliance

- **EMTALA** — Automated transfer certification and documentation
- **HIPAA** — End-to-end encryption, BAAs, audit trails, minimum necessary principle
- **HL7 FHIR R4** — Standard interoperability with certified EHR systems
- **CMS Conditions of Participation** — Transfer agreement management
- **21st Century Cures Act** — Leveraging mandated FHIR API access

## License

Proprietary — All rights reserved.
