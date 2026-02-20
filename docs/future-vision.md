# Fitness Evaluation App — Future Vision Architecture

**Version:** 0.1 (Vision Draft)
**Last Updated:** 2026-02-19
**Audience:** Project Lead & Development Team

---

## 1. Product Vision

### The Big Picture
A **white-label fitness intelligence platform** that transforms raw assessment data into actionable insights, professional reports, and personalized training programs — powered by AI, delivered through coaches and gyms.

### From POC to Platform

```
POC (Now)              → V1 Production (6-12mo)        → Full Platform (12-24mo)
─────────────────────────────────────────────────────────────────────────────────
Single coach tool        Multi-coach SaaS                 B2B2C marketplace
Manual input             Manual + device integrations     Auto-sync wearables
One-time PDF             Longitudinal tracking            Progress dashboards
Ollama (local)           Cloud LLM (OpenAI/Anthropic)     Multi-model + RAG
Streamlit                React web app                    React + Mobile (RN)
No auth                  Auth + multi-tenancy             SSO + gym admin portal
JSON norms               PostgreSQL + licensed data       Full ACSM/NSCA datasets
Docker on 1 server       Cloud deployment (AWS/GCP)       Auto-scaling infra
```

---

## 2. Business Model Evolution

### 2.1 Phase 1: B2B SaaS ("Super-Coach Tool")
- **Who pays:** Individual coaches and small studios.
- **Pricing:** Monthly subscription per coach seat ($29-49/mo).
- **Value:** Save 2-3 hours per client assessment; deliver premium-looking reports.

### 2.2 Phase 2: B2B2C ("Gym Platform")
- **Who pays:** Gyms and fitness chains.
- **Pricing:** White-label license per gym ($199-499/mo) + per-client usage.
- **Value:** Gym brands the platform as their own; coaches use it under the gym's umbrella.
- **End-client sees:** A branded assessment portal (gym's logo, colors).
- **New revenue streams:**
  - White-label setup fees
  - Per-report usage fees
  - Premium report tiers (basic vs. comprehensive)

### 2.3 Phase 3: Marketplace & Data Play
- **Coach marketplace:** Clients find coaches through the platform.
- **Aggregated insights:** Anonymized population-level fitness data (research partnerships).
- **API licensing:** Other fitness apps integrate our intelligence engine.
- **Content partnerships:** Exercise video libraries, nutrition plan integrations.

### 2.4 Monetization Levers
| Lever | Description |
|---|---|
| Seat-based SaaS | Per-coach monthly subscription |
| White-label licensing | Per-gym flat fee + usage |
| Tiered reports | Basic (free/cheap) vs. Premium (detailed AI analysis) |
| Progress tracking upsell | Longitudinal dashboards as premium add-on |
| API access | Third-party integrations pay per call |
| Data insights | Anonymized aggregate data for research/insurance |

---

## 3. Full Feature Roadmap

### 3.1 Assessment & Data Layer
- **Expanded test battery:** 30+ standardized tests covering all ACSM/NSCA categories.
- **Licensed normative data:** Full ACSM, NSCA, Cooper Institute datasets.
- **Custom tests:** Coaches can define their own tests with custom norms.
- **Device integrations:** Heart rate monitors, smart scales, grip dynamometers via Bluetooth/API.
- **Wearable sync:** Apple Health, Google Fit, Garmin, Fitbit, Whoop — pull resting HR, sleep, activity data.
- **Computer vision (stretch):** Form analysis for movement screens (e.g., FMS overhead squat) via phone camera.

### 3.2 Intelligence Layer (AI/LLM)
- **RAG pipeline:** LLM grounded in vetted exercise science literature (ACSM Guidelines, NSCA Essentials, peer-reviewed journals).
- **Multi-model routing:** Different models for different tasks (fast model for simple summaries, powerful model for complex analysis).
- **Workout plan generation:** Periodized training programs (not just suggestions) based on assessment results + goals.
- **Nutrition integration:** Basic macro recommendations aligned with goals (with appropriate disclaimers).
- **Body Age calculation:** Composite score comparing biological markers to age-matched norms.
- **Risk scoring:** Flag clients who need medical clearance (PAR-Q integration).
- **Progress prediction:** "At your current trajectory, you'll reach X goal in Y weeks."
- **Coach copilot:** Chat interface where the coach can ask questions about a client's data.

### 3.3 Reporting & Visualization
- **Interactive dashboards:** Web-based charts, not just static PDFs.
- **Longitudinal tracking:** Assessment-over-assessment progress visualization.
- **Comparison views:** Client vs. population, client vs. their own history.
- **Exportable reports:** PDF, branded HTML, shareable links.
- **White-label templates:** Fully customizable with gym branding, colors, logos.
- **Client-facing portal:** End-clients can view their own progress (gym-branded).

### 3.4 Platform & Collaboration
- **Multi-tenancy:** Gym → Coaches → Clients hierarchy.
- **Role-based access:** Gym admin, head coach, coach, client.
- **Client management:** CRM-lite features (notes, scheduling, tags).
- **Team collaboration:** Multiple coaches can work with same client.
- **Notification system:** Reassessment reminders, goal milestone alerts.
- **Audit trail:** Track who entered/modified assessment data.

---

## 4. Production Technical Architecture

### 4.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ React Web   │  │ React Native│  │ Client Portal   │  │
│  │ (Coach App) │  │ (Mobile)    │  │ (White-labeled) │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         └────────────────┼───────────────────┘           │
└──────────────────────────┼───────────────────────────────┘
                           │ HTTPS / WebSocket
┌──────────────────────────┼───────────────────────────────┐
│                    API GATEWAY                            │
│              (Auth, Rate Limiting, Routing)               │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                   SERVICE LAYER                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │Assessment│ │  Report   │ │   LLM    │ │   User /   │  │
│  │ Service  │ │  Service  │ │  Service │ │   Auth     │  │
│  │(FastAPI) │ │(FastAPI)  │ │(LangServe│ │  Service   │  │
│  │          │ │           │ │/LangChain│ │            │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       └─────────────┼───────────┼──────────────┘         │
└─────────────────────┼───────────┼────────────────────────┘
                      │           │
┌─────────────────────┼───────────┼────────────────────────┐
│                  DATA LAYER     │                         │
│  ┌──────────┐ ┌──────────┐ ┌───┴──────┐ ┌────────────┐  │
│  │PostgreSQL│ │  Redis    │ │ Vector   │ │ Object     │  │
│  │(Primary  │ │ (Cache,   │ │ Store    │ │ Storage    │  │
│  │ DB)      │ │  Sessions)│ │(Pinecone/│ │ (S3/GCS)   │  │
│  │          │ │           │ │ Chroma)  │ │ PDFs,imgs  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└──────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼────────────────────────────────────┐
│              INFRASTRUCTURE                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  Docker  │ │Kubernetes│ │ CI/CD    │ │ Monitoring │  │
│  │ Compose  │ │ (Prod)   │ │(GitHub   │ │(LangSmith, │  │
│  │ (Dev)    │ │          │ │ Actions) │ │ Sentry)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Tech Stack (Production)

| Layer | Technology | Notes |
|---|---|---|
| **Frontend (Web)** | React + TypeScript + Tailwind | SPA with component library |
| **Frontend (Mobile)** | React Native | Shared component logic with web |
| **API Gateway** | Kong / AWS API Gateway | Auth, rate limiting, routing |
| **Backend Services** | FastAPI (Python) | Microservices or modular monolith |
| **LLM Orchestration** | LangChain + LangGraph | Agents, RAG, multi-step reasoning |
| **LLM Providers** | OpenAI, Anthropic (multi-model) | Route by task complexity |
| **LLM Observability** | LangSmith | Trace, debug, evaluate LLM calls |
| **Database** | PostgreSQL | Primary data store |
| **Cache** | Redis | Session management, LLM response caching |
| **Vector Store** | Pinecone or Chroma | RAG — exercise science knowledge base |
| **Object Storage** | AWS S3 / GCP Cloud Storage | PDFs, images, exports |
| **Auth** | Auth0 or Supabase Auth | SSO, multi-tenancy, RBAC |
| **Deployment** | Docker + Kubernetes | Auto-scaling, rolling updates |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Monitoring** | Sentry + LangSmith + Prometheus | Errors, LLM quality, infra metrics |

### 4.3 Database Schema (Simplified)

```
gyms
├── id, name, branding_config, subscription_tier
│
├── coaches (belongs_to gym)
│   ├── id, gym_id, name, email, role
│   │
│   └── clients (belongs_to coach)
│       ├── id, coach_id, name, age, gender, goals
│       │
│       └── assessments (belongs_to client)
│           ├── id, client_id, date, status
│           │
│           ├── assessment_results (belongs_to assessment)
│           │   └── id, assessment_id, test_type, raw_value, rating, percentile
│           │
│           └── reports (belongs_to assessment)
│               └── id, assessment_id, summary_text, pdf_url, generated_at
│
└── custom_tests (belongs_to gym)
    └── id, gym_id, name, norms_config
```

---

## 5. Key Technical Decisions (Future)

### 5.1 RAG for LLM Grounding
- **Why:** Eliminate hallucinated fitness advice. Ground all recommendations in peer-reviewed literature.
- **How:** Chunk and embed ACSM/NSCA textbooks + key papers → Vector store → Retrieve relevant context per query.
- **Trade-off:** Adds complexity and cost, but critical for credibility and liability.

### 5.2 LangGraph for Agent Workflows
- **Why:** Complex report generation benefits from multi-step agent reasoning (analyze each category → synthesize → generate plan → review).
- **How:** LangGraph state machine with specialized sub-agents per category.
- **Trade-off:** Slower than single prompt, but higher quality output.

### 5.3 Multi-Tenancy Architecture
- **Approach:** Shared database with tenant isolation via `gym_id` foreign keys + Row-Level Security (RLS) in PostgreSQL.
- **Why not separate DBs:** Cost-prohibitive at scale; shared infra is simpler to maintain.

### 5.4 White-Label Strategy
- **Branding config** stored per gym: logo URL, primary/secondary colors, fonts, report header/footer text.
- **Frontend theming:** CSS variables driven by gym config, loaded at runtime.
- **PDF templates:** Gym branding injected via Jinja2 template variables.

---

## 6. Growth & Retention Mechanics

| Mechanic | Description |
|---|---|
| **Longitudinal lock-in** | The more assessments stored, the harder to leave (data gravity). |
| **Progress visualization** | Coaches and clients see improvement over time — drives re-assessment. |
| **Reassessment reminders** | Automated nudges: "Client X is due for reassessment." |
| **Benchmark comparisons** | "Your client is in the top 15% of 30-39yo males" — coaches love sharing this. |
| **Report branding** | Coach's brand on a professional report = marketing for them = retention for us. |
| **API ecosystem** | Integrations with scheduling, billing, and nutrition tools create switching cost. |

---

## 7. Competitive Moat

1. **Intelligence, not storage.** Competitors store data. We interpret it.
2. **White-label DNA.** Built for gym branding from day one, not bolted on.
3. **RAG-grounded advice.** Not generic AI output — recommendations backed by cited literature.
4. **Longitudinal intelligence.** The system gets smarter about each client over time.
5. **Open assessment framework.** Coaches can define custom tests — not locked into one protocol.

---

## 8. Open Questions for Future Phases

- [ ] **Pricing model finalization:** Per-seat vs. per-report vs. hybrid?
- [ ] **Mobile-first or web-first** for production frontend?
- [ ] **HIPAA compliance** needed if handling blood pressure / health data in the US?
- [ ] **International norms:** Different normative data by country/population?
- [ ] **Offline mode** for assessments in gyms with poor connectivity?
- [ ] **Video integration** for movement screen assessments — feasible ROI?
- [ ] **Insurance/corporate wellness** market — different product packaging?