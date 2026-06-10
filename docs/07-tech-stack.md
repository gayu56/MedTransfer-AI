# Tech Stack & Infrastructure Document
## Intelligent Patient Transfer Coordinator (IPTC)

**Version**: 1.0  
**Date**: June 2026

---

## 1. Technology Decisions

### 1.1 Backend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| **Language** | Python | 3.12+ | Rich healthcare/ML ecosystem, FHIR libraries, fast prototyping |
| **Web Framework** | FastAPI | 0.115+ | Async, auto-generated OpenAPI docs, Pydantic validation, high performance |
| **ORM** | SQLAlchemy | 2.0+ | Mature, async support, complex query capabilities |
| **Migration** | Alembic | 1.13+ | SQLAlchemy-native migrations |
| **Task Queue** | Celery | 5.4+ | Background task processing (SBAR generation, notifications) |
| **Message Broker** | Apache Kafka | 3.7+ | Event streaming between services, high throughput, durability |
| **Caching** | Redis | 7.2+ | Session cache, rate limiting, pub/sub for WebSocket |
| **WebSocket** | Socket.io (python-socketio) | 5.11+ | Real-time transfer status updates |

### 1.2 Frontend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| **Framework** | React | 18.3+ | Industry standard, large ecosystem, component model |
| **Language** | TypeScript | 5.4+ | Type safety, better DX, catch errors early |
| **Build Tool** | Vite | 5.4+ | Fast HMR, modern bundling |
| **Styling** | TailwindCSS | 3.4+ | Utility-first, rapid UI development |
| **Components** | shadcn/ui | latest | Beautiful, accessible, customizable components |
| **Icons** | Lucide React | latest | Clean, consistent icon set |
| **State Management** | Zustand | 4.5+ | Lightweight, simple, performant |
| **Data Fetching** | TanStack Query | 5.50+ | Server state management, caching, real-time |
| **Forms** | React Hook Form + Zod | latest | Performant forms with schema validation |
| **Charts** | Recharts | 2.12+ | Analytics dashboards |
| **Real-time** | Socket.io Client | 4.7+ | WebSocket for live updates |
| **Routing** | React Router | 6.23+ | Client-side routing |

### 1.3 AI / LLM

| Component | Technology | Rationale |
|---|---|---|
| **LLM** | Azure OpenAI GPT-4 | HIPAA BAA available; best reasoning for clinical text |
| **Embeddings** | text-embedding-3-large | High-quality embeddings for RAG knowledge base |
| **Vector Store** | Azure AI Search | Hybrid search (vector + keyword), Azure-native |
| **LLM Framework** | LangChain | Agent orchestration, tool calling, conversation memory |
| **Prompt Management** | LangSmith | Prompt versioning, testing, monitoring |
| **STT (Future)** | Deepgram | Real-time streaming STT, medical vocabulary |
| **TTS (Future)** | Azure Neural TTS | Natural voice, HIPAA-eligible |

### 1.4 EHR Integration

| Component | Technology | Rationale |
|---|---|---|
| **Standard** | HL7 FHIR R4 | Industry standard, mandated by 21st Century Cures |
| **FHIR Client** | fhir.resources (Python) | Pydantic-based FHIR models |
| **Auth** | SMART on FHIR (OAuth 2.0) | Standard EHR authentication |
| **Sandbox** | HAPI FHIR Server | Open-source FHIR server for development/testing |
| **Test Data** | Synthea | Synthetic patient data generator |

### 1.5 Database

| Component | Technology | Rationale |
|---|---|---|
| **Primary DB** | PostgreSQL 16 | Robust, JSONB support, PostGIS for geo queries, pgcrypto for encryption |
| **Cache** | Redis 7.2 | Session management, rate limiting, real-time pub/sub |
| **Document Store** | Azure Blob Storage | Transfer packets (PDFs), uploaded documents, ECG images |
| **Vector Store** | Azure AI Search | RAG knowledge base for policies and procedures |

### 1.6 Infrastructure

| Component | Technology | Rationale |
|---|---|---|
| **Cloud** | Microsoft Azure | HIPAA-eligible, Health Data Services, BAA available |
| **Container Orchestration** | Azure Kubernetes Service (AKS) | Scalable microservice deployment |
| **Container Registry** | Azure Container Registry | Private Docker image storage |
| **API Gateway** | Azure API Management | Auth, rate limiting, routing, monitoring |
| **Secrets** | Azure Key Vault | Encryption keys, connection strings, API keys |
| **DNS** | Azure DNS | Domain management |
| **CDN** | Azure Front Door | Global CDN for frontend assets |
| **Monitoring** | Azure Monitor + Application Insights | Metrics, logs, distributed tracing |
| **SIEM** | Microsoft Sentinel | Security event monitoring, threat detection |

---

## 2. Project Structure

```
intelligent-patient-transfer-coordinator/
├── README.md
├── docs/
│   ├── 01-PRD.md
│   ├── 02-system-architecture.md
│   ├── 03-data-models.md
│   ├── 04-api-specification.md
│   ├── 05-ai-agent-design.md
│   ├── 06-compliance-security.md
│   └── 07-tech-stack.md
│
├── backend/
│   ├── pyproject.toml              # Python project config (Poetry)
│   ├── alembic.ini                 # Database migration config
│   ├── alembic/
│   │   └── versions/               # Migration scripts
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Settings & environment config
│   │   ├── dependencies.py         # Dependency injection
│   │   │
│   │   ├── api/                    # API layer
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py       # Main v1 router
│   │   │   │   ├── transfers.py    # Transfer endpoints
│   │   │   │   ├── patients.py     # Patient endpoints
│   │   │   │   ├── facilities.py   # Facility endpoints
│   │   │   │   ├── agent.py        # AI agent endpoints
│   │   │   │   ├── compliance.py   # Compliance endpoints
│   │   │   │   ├── transport.py    # Transport endpoints
│   │   │   │   ├── analytics.py    # Analytics endpoints
│   │   │   │   └── notifications.py# Notification endpoints
│   │   │   └── middleware/
│   │   │       ├── auth.py         # JWT authentication
│   │   │       ├── audit.py        # Audit logging middleware
│   │   │       └── rate_limit.py   # Rate limiting
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base model with common fields
│   │   │   ├── organization.py
│   │   │   ├── facility.py
│   │   │   ├── user.py
│   │   │   ├── patient.py
│   │   │   ├── transfer.py
│   │   │   ├── clinical_summary.py
│   │   │   ├── compliance.py
│   │   │   ├── transport.py
│   │   │   ├── audit.py
│   │   │   └── notification.py
│   │   │
│   │   ├── schemas/                # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── transfer.py
│   │   │   ├── patient.py
│   │   │   ├── facility.py
│   │   │   ├── clinical_summary.py
│   │   │   ├── compliance.py
│   │   │   ├── transport.py
│   │   │   └── common.py           # Shared schemas (pagination, errors)
│   │   │
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── transfer_service.py
│   │   │   ├── patient_service.py
│   │   │   ├── facility_service.py
│   │   │   ├── compliance_service.py
│   │   │   ├── transport_service.py
│   │   │   ├── notification_service.py
│   │   │   └── analytics_service.py
│   │   │
│   │   ├── ai/                     # AI/LLM components
│   │   │   ├── __init__.py
│   │   │   ├── agent/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py  # Main agent orchestrator
│   │   │   │   ├── transfer_agent.py# Transfer flow agent
│   │   │   │   ├── qa_agent.py      # Question answering agent
│   │   │   │   └── tools.py         # Tool definitions for function calling
│   │   │   ├── sbar/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── generator.py     # SBAR generation pipeline
│   │   │   │   ├── validator.py     # Hallucination detection
│   │   │   │   └── prompts.py       # SBAR prompt templates
│   │   │   ├── facility_matcher/
│   │   │   │   ├── __init__.py
│   │   │   │   └── matcher.py       # Facility scoring & ranking
│   │   │   └── rag/
│   │   │       ├── __init__.py
│   │   │       ├── indexer.py        # Document indexing pipeline
│   │   │       └── retriever.py      # RAG retrieval
│   │   │
│   │   ├── integrations/           # External service integrations
│   │   │   ├── __init__.py
│   │   │   ├── fhir/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py        # FHIR API client
│   │   │   │   ├── mapper.py        # FHIR resource → internal model mapper
│   │   │   │   └── auth.py          # SMART on FHIR authentication
│   │   │   ├── azure_openai.py      # Azure OpenAI client
│   │   │   ├── twilio_client.py     # SMS/Voice (future)
│   │   │   └── sendgrid_client.py   # Email notifications
│   │   │
│   │   ├── events/                 # Event-driven communication
│   │   │   ├── __init__.py
│   │   │   ├── producer.py         # Kafka event producer
│   │   │   ├── consumer.py         # Kafka event consumer
│   │   │   └── schemas.py          # Event payload schemas
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── encryption.py       # PHI encryption utilities
│   │       ├── audit_logger.py     # Audit event helper
│   │       └── transfer_number.py  # Transfer number generator
│   │
│   └── tests/
│       ├── conftest.py             # Shared fixtures
│       ├── test_transfers.py
│       ├── test_sbar_generator.py
│       ├── test_facility_matcher.py
│       ├── test_compliance.py
│       └── test_agent.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.tsx                 # App entry point
│       ├── App.tsx                  # Root component + routing
│       │
│       ├── components/
│       │   ├── ui/                  # shadcn/ui components
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Header.tsx
│       │   │   └── MainLayout.tsx
│       │   ├── transfer/
│       │   │   ├── TransferForm.tsx
│       │   │   ├── TransferCard.tsx
│       │   │   ├── TransferTimeline.tsx
│       │   │   ├── SBARView.tsx
│       │   │   └── ComplianceChecklist.tsx
│       │   ├── facility/
│       │   │   ├── FacilityCard.tsx
│       │   │   └── FacilityMatchList.tsx
│       │   ├── agent/
│       │   │   ├── ChatPanel.tsx
│       │   │   ├── ChatMessage.tsx
│       │   │   └── SuggestedActions.tsx
│       │   └── analytics/
│       │       ├── TransferMetrics.tsx
│       │       └── Charts.tsx
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── NewTransfer.tsx
│       │   ├── TransferDetail.tsx
│       │   ├── TransferList.tsx
│       │   ├── FacilityList.tsx
│       │   ├── Analytics.tsx
│       │   └── Settings.tsx
│       │
│       ├── hooks/
│       │   ├── useTransfers.ts
│       │   ├── useWebSocket.ts
│       │   ├── useAgent.ts
│       │   └── useAuth.ts
│       │
│       ├── stores/
│       │   ├── authStore.ts
│       │   ├── transferStore.ts
│       │   └── notificationStore.ts
│       │
│       ├── services/
│       │   ├── api.ts               # Axios/fetch client
│       │   ├── transferApi.ts
│       │   ├── facilityApi.ts
│       │   ├── agentApi.ts
│       │   └── websocket.ts
│       │
│       ├── types/
│       │   ├── transfer.ts
│       │   ├── patient.ts
│       │   ├── facility.ts
│       │   └── api.ts
│       │
│       └── utils/
│           ├── formatters.ts
│           └── constants.ts
│
├── infrastructure/
│   ├── terraform/                   # Infrastructure as Code
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── aks/                 # Kubernetes cluster
│   │   │   ├── database/            # PostgreSQL + Redis
│   │   │   ├── storage/             # Blob Storage
│   │   │   ├── ai/                  # Azure OpenAI
│   │   │   ├── monitoring/          # Azure Monitor
│   │   │   └── networking/          # VNet, NSGs, Private Endpoints
│   │   └── environments/
│   │       ├── dev.tfvars
│   │       ├── staging.tfvars
│   │       └── prod.tfvars
│   │
│   ├── kubernetes/                  # K8s manifests
│   │   ├── base/
│   │   │   ├── namespace.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── secrets.yaml
│   │   ├── services/
│   │   │   ├── transfer-service.yaml
│   │   │   ├── ai-agent-service.yaml
│   │   │   ├── facility-service.yaml
│   │   │   └── ...
│   │   └── monitoring/
│   │       ├── prometheus.yaml
│   │       └── grafana.yaml
│   │
│   └── docker/
│       ├── backend.Dockerfile
│       ├── frontend.Dockerfile
│       └── docker-compose.yml       # Local development
│
├── scripts/
│   ├── seed_facilities.py           # Seed facility database
│   ├── seed_test_patients.py        # Generate test patients (Synthea)
│   └── setup_fhir_sandbox.py        # Setup HAPI FHIR server
│
└── .github/
    └── workflows/
        ├── ci.yml                   # Test + lint on PR
        ├── cd-staging.yml           # Deploy to staging
        └── cd-production.yml        # Deploy to production
```

---

## 3. Development Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 20 LTS+
- Docker Desktop
- Azure CLI
- kubectl

### Local Development Stack (Docker Compose)

```yaml
# docker-compose.yml
services:
  # Backend API
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis, kafka]

  # Frontend
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: iptc
      POSTGRES_USER: iptc
      POSTGRES_PASSWORD: dev_password
    volumes: [postgres_data:/var/lib/postgresql/data]

  # Redis
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  # Kafka
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    ports: ["9092:9092"]
    environment:
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_NODE_ID: 1
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER

  # HAPI FHIR Server (EHR Sandbox)
  fhir-server:
    image: hapiproject/hapi:latest
    ports: ["8080:8080"]

volumes:
  postgres_data:
```

---

## 4. CI/CD Pipeline

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌────────────┐
│  Commit   │───▶│  CI Build  │───▶│ Staging  │───▶│ Production │
│  + PR     │    │  + Test    │    │ Deploy   │    │ Deploy     │
└──────────┘    └───────────┘    └──────────┘    └────────────┘
                     │                │                │
              ┌──────┴──────┐   ┌────┴────┐     ┌────┴────┐
              │ • Lint       │   │ Auto    │     │ Manual  │
              │ • Unit tests │   │ deploy  │     │ approval│
              │ • SAST scan  │   │ on merge│     │ required│
              │ • Dep scan   │   │ to main │     │         │
              │ • Build      │   └─────────┘     └─────────┘
              │ • Container  │
              │   scan       │
              └─────────────┘
```

### CI Checks (on every PR)

| Check | Tool | Fail Criteria |
|---|---|---|
| Python lint | Ruff | Any error |
| Python type check | mypy | Any error |
| Python tests | pytest | Any failure; <80% coverage |
| JS/TS lint | ESLint + Prettier | Any error |
| JS/TS type check | tsc --noEmit | Any error |
| JS/TS tests | Vitest | Any failure |
| SAST | Semgrep | High/Critical findings |
| Dependency scan | Snyk | Critical vulnerabilities |
| Container scan | Trivy | Critical/High CVEs |
| OpenAPI validation | Spectral | Any error |

---

## 5. Environment Strategy

| Environment | Purpose | Infrastructure | Data |
|---|---|---|---|
| **Local** | Developer machines | Docker Compose | Synthetic (Synthea) |
| **Dev** | Integration testing | Azure (minimal) | Synthetic |
| **Staging** | Pre-production validation | Azure (prod-like) | Anonymized |
| **Production** | Live system | Azure (full HA) | Real PHI |

### Environment Variables

```bash
# .env.example
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_SECRET_KEY=change-me

# Database
DATABASE_URL=postgresql+asyncpg://iptc:dev_password@localhost:5432/iptc

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-06-01

# FHIR
FHIR_SERVER_URL=http://localhost:8080/fhir

# Auth
AZURE_AD_B2C_TENANT=your-tenant
AZURE_AD_B2C_CLIENT_ID=your-client-id

# Twilio (future)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Encryption
PHI_ENCRYPTION_KEY=change-me-to-256-bit-key
```

---

## 6. Monitoring & Alerting

### Key Dashboards

| Dashboard | Metrics Shown |
|---|---|
| **Transfer Operations** | Active transfers, avg time to acceptance, avg time to completion, decline rate |
| **AI Agent Performance** | SBAR generation latency, hallucination rate, agent response time, tool call success rate |
| **System Health** | CPU/memory per service, API latency p50/p95/p99, error rate, Kafka consumer lag |
| **Security** | Failed auth attempts, PHI access volume, anomalous access patterns |
| **FHIR Integration** | EHR API latency, success rate, data freshness |

### Alert Rules

| Alert | Condition | Severity | Notification |
|---|---|---|---|
| API error rate >1% | 5-min window | P2 | PagerDuty + Slack |
| API latency p99 >2s | 5-min window | P3 | Slack |
| Transfer stuck in PENDING >30 min | Per transfer | P2 | Slack + in-app |
| EMERGENT transfer not accepted in 10 min | Per transfer | P1 | PagerDuty + SMS |
| SBAR generation failure | Per request | P3 | Slack |
| FHIR integration down | 3 consecutive failures | P2 | PagerDuty |
| Database connection pool exhausted | >90% utilization | P2 | PagerDuty |
| Suspicious PHI access pattern | Anomaly detection | P1 | PagerDuty + Security team |

---

## 7. Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| Transfer API response time (p95) | <200ms | Application Insights |
| SBAR generation time (p95) | <8 seconds | Custom metric |
| Facility matching time (p95) | <500ms | Custom metric |
| Dashboard load time | <2 seconds | Real User Monitoring |
| WebSocket event delivery | <100ms | Custom metric |
| Concurrent transfers supported | 10,000+ | Load testing |
| Database query time (p95) | <50ms | Azure Monitor |
