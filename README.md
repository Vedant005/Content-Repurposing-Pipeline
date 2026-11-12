# Content Repurposing Studio

Content Repurposing Studio is an enterprise-grade AI automation pipeline that ingests a YouTube video URL and orchestrates a multi-stage LangGraph workflow to produce production-ready content assets: an SEO-optimized blog article, an engagement-driven Twitter/X thread, a thought-leadership LinkedIn post, and timestamped video chapters with grounded quotes.

The system combines a FastAPI backend, LangGraph state-graph pipeline, ARQ distributed worker queue, Redis Pub/Sub, PostgreSQL storage, Groq multi-model inference, and a Next.js 16 editorial publication workbench.

---

## Key Features

- **LangGraph Multi-Stage State Machine**: Orchestrates transcript fetching, semantic chunking, map-reduce chapter extraction, parallel asset generation, critique evaluation, and atomic database persistence.
- **Multi-Model LLM Routing with Automated Fallback**:
  - Deep Model (`openai/gpt-oss-120b`): High-context reasoning for comprehensive SEO blog posts.
  - Fast Model (`openai/gpt-oss-20b`): High-throughput generation for atomic tweets, LinkedIn posts, and chapters.
  - Fallback Model (`qwen/qwen3.8-27b`): Automated failover for rate limit (429) backoffs and JSON validation errors.
- **Brand Voice and Style Profiles**: Custom profiles (tone, target audience, voice rules, few-shot examples) dynamically injected into generation prompts.
- **Real-Time Event Streaming (SSE)**: Full Server-Sent Events architecture via Redis Pub/Sub with sequence-based event replay and automatic PostgreSQL polling fallback.
- **Targeted Per-Asset Regeneration**: Regenerate individual assets (e.g. only the Twitter thread or only the Blog) without re-running the transcript extraction or other assets.
- **Semantic Chunking and Map-Reduce**: Token-aware recursive text chunking preserving sentence boundaries and punctuation for transcripts of varying lengths.
- **Distributed Task Queue (ARQ + Redis)**: Heavy video pipelines run asynchronously in background workers with stale job detection and automatic recovery.
- **Publication Workbench UI**: Built with Next.js 16, React 19, and Tailwind CSS using an editorial monochrome layout, featuring live SSE progress tracking, copy-to-clipboard actions, single-click bundle export, and brand persona selection.
- **Full Docker Containerization**: Complete multi-container orchestration (`docker-compose.yml`) including PostgreSQL 16, Redis 7, FastAPI backend, and ARQ worker.

---

## Architecture Overview

```
                         Browser / Next.js 16 Client
                                     │
                 ┌───────────────────┴───────────────────┐
                 │ POST /api/v1/repurpose                │ GET /api/v1/jobs/{id}/events
                 ▼                                       ▼
        FastAPI API Gateway ────────────────────► SSE Stream Handler
                 │                                       ▲
        Enqueue Job (Redis)                              │ Pub/Sub & DB Fallback
                 │                                       │
                 ▼                                       │
         ARQ Worker Process ─────────────────────────────┤
                 │                                       │
                 ▼                                       │
     ┌──────────────────────────────────────────────┐    │
     │      LangGraph Repurposing Pipeline          │    │
     │                                              │    │
     │  1. Extract Transcript (Supadata API)        │───►┤
     │  2. Semantic Chunking (Sliding Window)       │───►┤
     │  3. Map-Reduce Chapter Generation            │───►┤
     │  4. Parallel Asset Generation:               │    │
     │     ├─ SEO Blog Post (GPT-OSS-120B)          │───►┤
     │     ├─ Twitter Thread (GPT-OSS-20B)          │───►┤
     │     └─ LinkedIn Post (GPT-OSS-20B)           │───►┤
     │  5. Automated Critique & Quality Check       │───►┤
     │  6. Database Persistence & Final Status      │───►┘
     └──────────────────────┬───────────────────────┘
                            │
                            ▼
              PostgreSQL 16 Database
        (jobs, assets, events, transcripts, profiles)
```

---

## Tech Stack

### Backend

- **Framework**: FastAPI, Uvicorn, Python 3.12
- **Orchestration**: LangGraph, LangChain Core
- **Database & ORM**: PostgreSQL 16, SQLAlchemy 2.0 (AsyncIO), Alembic migrations
- **Queue & Streaming**: ARQ, Redis 7 (aioredis), Server-Sent Events (SSE)
- **External APIs**: Groq Cloud API, Supadata YouTube Transcript API
- **Validation**: Pydantic v2, Pydantic-Settings
- **Security & Rate Limiting**: SlowAPI, HTTP-only SameSite session cookies

### Frontend

- **Framework**: Next.js 16.1 (App Router, Turbopack), React 19
- **Styling**: Tailwind CSS, Lucide React icons
- **State & Data**: Native React Hooks, EventSource SSE API, LocalStorage persistence

### Infrastructure & Testing

- **Containers**: Docker, Docker Compose
- **Test Suite**: Pytest, Pytest-AsyncIO, Respx, HTTPX (45 passing tests)

---

## Project Structure

```
crp/
├── docker-compose.yml              # Multi-container orchestration
├── backend/
│   ├── Dockerfile                  # Production container definition
│   ├── alembic/                    # Database migration scripts
│   │   └── versions/               # Schema revisions (jobs, assets, events, profiles)
│   ├── src/
│   │   ├── api/                    # REST endpoints
│   │   │   ├── brand.py            # Brand profile CRUD routes
│   │   │   └── repurpose.py        # Video repurposing, status, history, retry, SSE
│   │   ├── core/                   # Application settings & logging
│   │   │   └── config.py           # Environment variables and model configurations
│   │   ├── db/                     # Database engine & session factories
│   │   │   └── session.py          # Async connection pool & SSL handling
│   │   ├── middleware/             # Request middleware
│   │   │   └── session.py          # Lightweight browser session identification
│   │   ├── models/                 # SQLAlchemy declarative models
│   │   │   └── content.py          # ContentJob, ContentAsset, JobEvent, BrandProfile
│   │   ├── pipeline/               # LangGraph DAG definition & nodes
│   │   │   ├── chunker.py          # Token-aware sliding window semantic chunker
│   │   │   ├── graph.py            # StateGraph builder and compiled pipeline
│   │   │   ├── nodes.py            # Pipeline node implementations
│   │   │   └── state.py            # TypedDict PipelineState definition
│   │   ├── queue/                  # Redis queue client
│   │   │   └── redis.py            # ARQ connection pool
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   └── content.py          # Strict structured output contracts
│   │   ├── services/               # Core application services
│   │   │   ├── event_service.py    # Redis Pub/Sub and SSE streaming engine
│   │   │   ├── llm_provider.py     # Groq API client with backoff and model failover
│   │   │   └── youtube_service.py  # Supadata transcript retrieval & validation
│   │   ├── worker/                 # Asynchronous background worker
│   │   │   └── worker.py           # ARQ worker settings and stale job recovery
│   │   └── main.py                 # FastAPI application root and lifespan hooks
│   └── tests/                      # Automated test suite
│       ├── test_brand_profiles.py
│       ├── test_chunker.py
│       ├── test_content_models.py
│       ├── test_event_service.py
│       ├── test_health.py
│       ├── test_langgraph_pipeline.py
│       ├── test_llm_provider.py
│       ├── test_map_reduce.py
│       ├── test_quality_benchmark.py
│       ├── test_schemas.py
│       ├── test_sse_endpoint.py
│       ├── test_transcript_service.py
│       └── test_worker.py
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx          # Root application layout
    │   │   ├── page.tsx            # Landing page
    │   │   └── pipeline/
    │   │       └── page.tsx        # Main pipeline application & results workbench
    │   └── components/
    │       ├── AssetEditor.tsx     # In-place markdown editor and targeted retry controls
    │       ├── BrandProfileSelector.tsx # Brand voice modal and selector
    │       ├── CostAndQualityBadge.tsx  # Cost and quality benchmark dialog
    │       ├── SSEProgressTicker.tsx    # Live pipeline stage stream listener
    │       └── YouTubeInput.tsx    # URL entry form with validation
    ├── package.json
    └── tailwind.config.js
```

---

## Detailed Pipeline Flow

1. **Submission & Ingestion**:
   - The user inputs a YouTube URL and optionally chooses a Brand Profile.
   - The API validates the URL format, creates a `ContentJob` record in PostgreSQL with status `queued`, and enqueues the job into Redis.
   - If Redis is unavailable, the API gracefully falls back to local FastAPI background execution.

2. **Asynchronous Worker Execution**:
   - The ARQ worker claims the task and updates status to `processing`.
   - The worker initializes the LangGraph state machine with job parameters.

3. **Transcript Extraction**:
   - Supadata API fetches video metadata and caption tracks.
   - Videos exceeding duration limits (default 25 minutes) are halted with clear user-facing diagnostics.

4. **Semantic Chunking & Map-Reduce**:
   - The transcript is processed by `SemanticChunker` using a recursive sliding window (target 800 tokens, 150 token overlap).
   - Timestamped chapters are generated across chunk boundaries with exact formatted offsets (`MM:SS`).

5. **Parallel Multi-Model Asset Synthesis**:
   - **SEO Blog Post**: Synthesized using `openai/gpt-oss-120b`, formatted in markdown with executive summaries, headers, and callouts.
   - **Twitter / X Thread**: Generated using `openai/gpt-oss-20b`, validated against strict JSON schema (5 to 10 atomic tweets with thread hooks).
   - **LinkedIn Thought Leadership**: Generated using `openai/gpt-oss-20b`, structured into hooks, body paragraphs, and professional engagement prompts.
   - If a brand profile is selected, style rules and few-shot examples are injected into the respective prompt contexts.

6. **Automated Critique & Grounding Verification**:
   - The critique node inspects each asset for factual grounding against the source transcript.
   - If validation errors are detected, the graph conditionally re-routes the specific asset for refinement (up to 2 retry attempts).

7. **Persistence & Completion**:
   - Generated assets are committed to the `content_assets` table.
   - Legacy columns on `content_jobs` are updated for backwards compatibility.
   - A `job_completed` event is broadcasted via Redis and logged to `job_events`.

---

## API Reference

### Repurposing Endpoints

#### POST `/api/v1/repurpose`

Enqueues a YouTube video for repurposing.

- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "brand_profile_id": 1
  }
  ```
- **Response** (HTTP 202):
  ```json
  {
    "job_id": 42,
    "status": "queued",
    "message": "Video repurposing pipeline successfully queued."
  }
  ```

#### GET `/api/v1/jobs/{job_id}/events`

Establishes a Server-Sent Events (SSE) connection streaming real-time stage updates.

- **Query Parameters**: `last_event_id` (optional integer for event replay).
- **Stream Output**:

  ```text
  id: 1
  event: job_started
  data: {"stage": "job_started", "message": "Worker started"}

  id: 2
  event: job_completed
  data: {"stage": "job_completed", "status": "completed"}
  ```

#### GET `/api/v1/status/{job_id}`

Retrieves job status and effective content outputs.

- **Response** (HTTP 200):
  ```json
  {
    "id": 42,
    "status": "completed",
    "blog_content": "# Article Title...",
    "tweets": ["Tweet 1", "Tweet 2"],
    "linkedin_post": "Hook line...",
    "error_message": null
  }
  ```

#### GET `/api/v1/jobs/{job_id}/assets`

Retrieves granular asset records including validation history and critique scores.

#### POST `/api/v1/jobs/{job_id}/assets/{asset_type}/retry`

Triggers targeted regeneration for a specific asset (`blog`, `twitter_thread`, `linkedin_post`).

#### GET `/api/v1/history`

Returns paginated job history for the active browser session.

- **Query Parameters**: `limit` (default: 10, max: 50), `offset` (default: 0).

#### DELETE `/api/v1/jobs/{job_id}`

Deletes a job and cascades removal of all associated assets and event logs.

- **Response** (HTTP 200):
  ```json
  {
    "status": "success",
    "message": "Job 42 deleted successfully."
  }
  ```

---

### Brand Profile Endpoints

#### GET `/api/v1/brand-profiles`

Lists all brand voice profiles available for the session.

#### POST `/api/v1/brand-profiles`

Creates a new brand persona profile.

- **Request Body**:
  ```json
  {
    "name": "Tech Founder Voice",
    "tone": "Authoritative yet accessible",
    "target_audience": "Engineers and founders",
    "brand_voice_guidelines": "Be concise, use data-backed insights, avoid buzzwords.",
    "few_shot_examples": {
      "twitter": "First tweet example...",
      "linkedin": "First linkedin example..."
    }
  }
  ```

#### GET `/api/v1/brand-profiles/{profile_id}`

Retrieves details for a specific brand profile.

#### DELETE `/api/v1/brand-profiles/{profile_id}`

Deletes a brand profile.

---

## Database Schema

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│          content_jobs           │         │         brand_profiles          │
├─────────────────────────────────┼─────────┼─────────────────────────────────┤
│ id (PK)                         │         │ id (PK)                         │
│ youtube_url                     │         │ name                            │
│ status                          │    ┌───►│ tone                            │
│ error_message                   │    │    │ target_audience                 │
│ session_id                      │    │    │ brand_voice_guidelines          │
│ brand_profile_id (FK) ──────────┼────┘    │ few_shot_examples (JSON)        │
│ transcript_id (FK) ─────────┐   │         │ session_id                      │
│ created_at / updated_at         │   │         └─────────────────────────────────┘
└───────────────┬─────────────────┘   │
                │                     │     ┌─────────────────────────────────┐
                │ 1:N                 │     │        video_transcripts        │
                ├────────────────┐    │     ├─────────────────────────────────┤
                ▼                ▼    └────►│ id (PK)                         │
┌─────────────────────────┐ ┌───────────────┐│ video_id / youtube_url           │
│     content_assets      │ │  job_events   ││ full_transcript / clean_text   │
├─────────────────────────┤ ├───────────────┤│ duration_seconds               │
│ id (PK)                 │ │ id (PK)       ││ chunks (JSON)                  │
│ job_id (FK)             │ │ job_id (FK)   │└─────────────────────────────────┘
│ asset_type              │ │ sequence_num  │
│ status                  │ │ event_type    │
│ content (JSON)          │ │ payload (JSON)│
│ critique_score          │ │ created_at    │
│ validation_errors (JSON)│ └───────────────┘
│ retry_count             │
└─────────────────────────┘
```

---

## Installation & Setup

### Prerequisites

- Docker & Docker Compose (recommended), or Python 3.12+ and Node.js 18+
- Groq Cloud API Key
- Supadata API Key

---

### Option A: Running with Docker Compose (Recommended)

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/Vedant005/Content-Repurposing-Pipeline.git
   cd Content-Repurposing-Pipeline
   ```

2. **Configure Environment Variables**:
   Create `backend/.env`:

   ```env
   PROJECT_NAME="Content Repurposing Studio"
   GROQ_API_KEY=gsk_your_groq_api_key
   SUPADATA_API_KEY=sd_your_supadata_api_key
   DATABASE_URL=postgresql+asyncpg://crp_user:crp_password@postgres:5432/crp_db
   REDIS_URL=redis://redis:6379/0
   DB_SSL=false
   ENV=prod
   ```

   Create `frontend/.env`:

   ```env
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```

3. **Start All Services**:

   ```bash
   docker compose up --build
   ```

4. **Access the Stack**:
   - Backend API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`
   - Frontend UI: Start the local frontend dev server:
     ```bash
     cd frontend
     npm install
     npm run dev
     ```
     Navigate to `http://localhost:3000/pipeline`.

---

### Option B: Local Manual Setup

#### 1. Database and Redis

Start local instances of PostgreSQL (port 5432) and Redis (port 6379).

#### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn src.main:app --reload --port 8000
```

In a separate terminal, start the background worker:

```bash
cd backend
# With virtual environment activated:
arq src.worker.worker.WorkerSettings
```

#### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## Running the Automated Test Suite

The backend includes 45 unit, integration, and mocking tests covering all layers of the pipeline.

```bash
cd backend
pytest tests/ -v
```

Test coverage includes:

- Brand Profile CRUD validation
- Semantic chunking token preservation
- LangGraph DAG execution and conditional branching
- Groq LLM Provider retries, rate limits, and fallback switching
- Map-Reduce summarization nodes
- Server-Sent Events subscription and replay
- ARQ worker task processing and stale job reaping

---

## Production Recommendations

- **PostgreSQL Connection Pooling**: Configured with `AsyncAdaptedQueuePool` (pool size: 5, max overflow: 10, pre-ping enabled).
- **SSL Detection**: Automatically enforces SSL for cloud database connections while bypassing SSL upgrades on local Docker networks.
- **Worker Scaling**: Scale the ARQ worker horizontally by increasing replica counts in container orchestration environments (`docker compose up --scale worker=3`).
- **Rate Limit Safeguards**: Configured via SlowAPI on ingestion endpoints (`5/minute`, `20/hour`) to prevent downstream LLM exhaustion.
