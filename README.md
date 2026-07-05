# 🎬 Content Repurposing Pipeline

An AI-powered content automation pipeline that transforms a single **YouTube video** into multiple high-quality content formats.

Simply provide a YouTube video URL, and the application automatically:
- 📝 Generates an SEO-optimized blog post
- 🐦 Creates a Twitter/X thread
- 💼 Writes a professional LinkedIn post

The project is built using **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **Groq LLMs**, and **Supadata**, while supporting asynchronous background processing, job tracking, session-based history, retries, and rate limiting.

---

# ✨ Features

- Convert any supported YouTube video into:
  - SEO Blog
  - Twitter Thread
  - LinkedIn Post
- Asynchronous processing using FastAPI Background Tasks
- Job status tracking
- Session-based content history
- Automatic transcript extraction
- AI-powered content generation
- Retry mechanism for LLM failures
- Video duration validation
- Transcript truncation for token safety
- JSON validation for Twitter output
- Rate limiting
- Comprehensive logging
- Error handling with persistent failure status

---

# 🏗 Architecture

```
                   User
                     │
                     ▼
             FastAPI REST API
                     │
                     ▼
          Create Processing Job
                     │
                     ▼
        Background Processing Task
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  Supadata API             Video Metadata
 Transcript Fetch          Duration Check
        │
        ▼
 Transcript Processing
        │
        ▼
   Parallel AI Generation
 ┌─────────┬──────────┬──────────┐
 ▼         ▼          ▼
 Blog    Twitter   LinkedIn
        │
        ▼
 Store Results in PostgreSQL
        │
        ▼
  Poll Job Status API
```

---

# 🛠 Tech Stack

## Backend

- FastAPI
- Python 3.11+
- AsyncIO
- SQLAlchemy (Async)
- PostgreSQL

## AI

- Groq API
- Llama 3.3 70B
- Llama 3.1 8B

## Transcript Service

- Supadata API

## Validation

- Pydantic

## Database

- PostgreSQL
- SQLAlchemy ORM

---

# 📂 Project Structure

```
src/
│
├── api/
│   └── router.py
│
├── services/
│   └── youtube_service.py
│
├── models/
│   └── content.py
│
├── schemas/
│   └── content.py
│
├── db/
│   ├── session.py
│   └── base.py
│
├── core/
│   └── config.py
│
└── main.py
```

---

# ⚙ How It Works

## 1. User submits a YouTube URL

```
POST /repurpose
```

Example

```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

---

## 2. URL Validation

The API validates:

- Correct YouTube domain
- Extractable video ID
- Duplicate processing requests
- Active user session

Invalid URLs are rejected immediately.

---

## 3. Background Job Creation

A database record is created.

Initial status:

```
processing
```

The API instantly returns

```json
{
    "job_id": 12,
    "status": "processing"
}
```

The heavy processing happens asynchronously.

---

## 4. Video Duration Check

Before downloading the transcript, the service queries Supadata metadata.

Current limit:

```
25 minutes
```

Longer videos are rejected with a meaningful error message.

This prevents:

- excessive token usage
- expensive LLM calls
- long processing times

---

## 5. Transcript Extraction

The transcript is fetched using Supadata.

Features:

- English transcript retrieval
- Runs in a background thread
- Non-blocking AsyncIO integration
- Handles missing captions
- Graceful failure handling

---

## 6. Transcript Truncation

Large transcripts are trimmed to

```
50,000 characters
```

The truncation preserves sentence boundaries whenever possible.

---

## 7. AI Content Generation

Three independent AI requests run **concurrently** using `asyncio.gather()`.

### Blog

Model:

```
llama-3.3-70b-versatile
```

Produces:

- SEO optimized article
- Markdown formatting
- Detailed explanations

---

### Twitter Thread

Model:

```
llama-3.3-70b-versatile
```

Produces

- JSON array
- Maximum 10 tweets
- No markdown
- No extra text

The output is validated before storing.

---

### LinkedIn Post

Model

```
llama-3.1-8b-instant
```

Produces

- Professional tone
- Business audience
- Engagement focused

---

# 🔄 Parallel Processing

Instead of generating one asset after another:

```
Blog
 ↓
Twitter
 ↓
LinkedIn
```

the application runs:

```
          Transcript
               │
      ┌────────┼─────────┐
      ▼        ▼         ▼
    Blog    Twitter   LinkedIn
```

This significantly reduces total response time.

---

# 🔁 Retry Mechanism

Each AI request supports retries.

Current configuration:

- 3 attempts
- exponential backoff

This improves reliability during temporary API failures.

---

# 💾 Database Schema

## ContentJob

| Column | Description |
|----------|-------------|
| id | Primary key |
| youtube_url | Original video URL |
| status | processing/completed/failed |
| error_message | Failure reason |
| blog_content | Generated blog |
| tweets | JSON Twitter thread |
| linkedin_post | LinkedIn content |
| created_at | Creation timestamp |
| updated_at | Last update |
| session_id | Browser session |
| user_id | Reserved for authentication |

---

# 📌 Job Lifecycle

```
             processing
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
   completed             failed
```

Possible failure reasons include:

- Invalid YouTube URL
- Missing transcript
- Video exceeds duration limit
- AI API failures
- Timeout
- JSON parsing errors

---

# 📡 API Endpoints

## POST `/repurpose`

Starts a new content generation job.

Response

```json
{
    "job_id": 7,
    "status": "processing"
}
```

---

## GET `/status/{job_id}`

Returns the current status.

Possible values

- processing
- completed
- failed

Example

```json
{
    "id": 7,
    "status": "completed",
    "blog_content": "...",
    "tweets": [
        "...",
        "..."
    ],
    "linkedin_post": "..."
}
```

---

## GET `/history`

Returns previous jobs for the current session.

Supports pagination.

Examples

```
GET /history
```

```
GET /history?limit=10
```

```
GET /history?offset=20
```

---

# 🚦 Rate Limiting

The API prevents abuse using request limits.

```
5 requests / minute
20 requests / hour
```

---

# 📝 Logging

The application logs:

- Job creation
- Transcript retrieval
- Duration validation
- AI generation
- Completion
- Failures
- Timeouts
- JSON parsing issues

This makes debugging significantly easier.

---

# 🛡 Error Handling

The project gracefully handles:

- Invalid URLs
- Missing transcripts
- Unsupported videos
- Long videos
- Groq failures
- Supadata failures
- Timeout errors
- JSON parsing failures
- Database rollback

Failed jobs are permanently stored with an appropriate error message.

---

# 🔒 Session Isolation

Every browser session receives its own session identifier.

Users can only:

- access their own jobs
- retrieve their own history
- check status of their own requests

This provides lightweight user isolation without requiring authentication.

---

# 📈 Future Improvements

- User authentication
- Multi-language transcript support
- Support for videos longer than 25 minutes
- PDF export
- DOCX export
- Content customization (tone, audience, length)
- Additional content formats
  - Instagram captions
  - Facebook posts
  - Email newsletters
  - Medium articles
- Queue system using Celery or RabbitMQ
- WebSocket support for live progress updates
- Caching previously processed videos
- Multiple LLM provider support

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/Vedant005/Content-Repurposing-Pipeline.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```env
DATABASE_URL=...
GROQ_API_KEY=...
SUPADATA_API_KEY=...
SECRET_KEY=...
```

Run database migrations (if using Alembic)

```bash
alembic upgrade head
```

Start the server

```bash
uvicorn src.main:app --reload
```

---

# 📋 Example Workflow

1. Submit a YouTube URL.
2. A processing job is created.
3. The API validates the URL.
4. Video duration is checked.
5. Transcript is downloaded.
6. Transcript is truncated if necessary.
7. Three AI models generate content in parallel.
8. Results are stored in PostgreSQL.
9. Client polls the status endpoint.
10. Generated content is returned to the user.

---

# 💡 Highlights

- Fully asynchronous backend
- AI-powered content generation
- Parallel LLM execution
- Background job processing
- Persistent job history
- Robust validation and error handling
- Session-based isolation
- Retry and timeout mechanisms
- Production-oriented API design
