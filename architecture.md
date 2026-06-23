# HR Voice + Vision Interview Platform — Architecture & System Design

This document details the production-ready architecture design and system specifications for the **HR Voice + Vision Interview Agent** platform. It has been compiled in accordance with the STRICT OPERATING RULES defined in `PRD.md`.

---

## 1. Requirement Review

The target system is an AI-powered interview platform that conducts automated candidate evaluations using real-time voice analysis.

### Core Functional Flow
```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    actor Recruiter
    participant Frontend
    participant Backend as FastAPI Backend
    participant Pipecat as Pipecat Agent
    participant DB as PostgreSQL

    %% Step 1-3: Registration & Setup
    Candidate->>Frontend: Submit Name, Email, Phone, Resume & JD
    Frontend->>Backend: Forward registration
    Backend->>DB: Persist Candidate & Job records (PDFs stored as BYTEA)
    Backend->>Backend: Extract Skills & Generate Question Bank via Groq LLM
    Backend->>DB: Store Generated Question Bank
    Backend->>Frontend: Registration Success (Return Interview ID)

    %% Step 4-6: Live Interview
    Candidate->>Frontend: Start Interview
    Frontend->>Pipecat: Initiate WebSocket Connection
    Pipecat->>DB: Fetch Interview Context & Question Bank
    Pipecat->>Candidate: Speak greeting / first question
    loop For each question
        Candidate->>Pipecat: Speak answer (Audio Stream)
        Pipecat->>DB: Intercept and Post Answer Transcript (persistence processor)
        Pipecat->>Candidate: Speak next question
    end

    %% Step 7-9: Reporting & Recruiter Access
    Candidate->>Frontend: Hang Up (Disconnect)
    Pipecat->>Backend: Trigger Final Evaluation Use Case
    Backend->>Backend: Generate Evaluation Report (Groq LLM) & PDF (fpdf2)
    Backend->>DB: Update Interview status to Evaluated & save PDF binary
    Recruiter->>Frontend: Access Dashboard
    Frontend->>Backend: Query candidate database
    Backend->>DB: Fetch records
    Backend->>Recruiter: Render list, metrics, and download PDF URL
```

### Key Metrics & SLAs
*   **Response Latency**: Voice turn-around time (silence detection to start of AI audio playback) must be **< 1.0 second**.
*   **Scale**: Designed to handle **10,000+** concurrent active interviews.
*   **Data Isolation**: All candidate PII, resumes, and PDFs are securely stored locally within PostgreSQL.

---

## 2. Clarifying Questions & Architecture Assumptions

### Q1: Candidate-to-Job Cardinality
*   *Strategy*: We design a **1-to-Many relationship** between Candidate and Interviews. A candidate profile is unique by email, but they can have multiple `Interview` instances (each mapped to a specific Job ID).

### Q2: Vision Analytics Data Ingestion
*   *Strategy*: For the MVP, Vision Analytics is deferred to a future phase. The current platform strictly focuses on high-fidelity Voice and Transcription gathering.

### Q3: File Storage Strategy (No S3/Redis)
*   *Strategy*: To optimize for immediate local deployment on Windows without complex Docker volumes or cloud storage, **PostgreSQL `BYTEA` columns** natively store both the input Resume PDFs and the generated Evaluation PDFs. State tracking (current question index) is also handled directly by PostgreSQL, entirely eliminating the need for Redis and Amazon S3.

---

## 3. Microservice Breakdown

The platform is divided into specialized layers that share a single robust PostgreSQL database:

```
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
 ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
 │  Core Backend   │  │ Pipecat Worker  │  │ React Frontend  │
 │    (FastAPI)    │  │  (Voice Agent)  │  │  (Vite App)     │
 └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
          │                    │                    │
          └──────────┐         │         ┌──────────┘
                     ▼         ▼         ▼
                ┌────────────────────────┐
                │  Shared Storage/State  │
                │     (PostgreSQL)       │
                └────────────────────────┘
```

---

## 4. Database Design (PostgreSQL)

We use PostgreSQL as the sole source of truth for both relational mapping and blob storage.

### ER Diagram

```mermaid
erDiagram
    CANDIDATE ||--o{ INTERVIEW : undergoes
    JOB ||--o{ INTERVIEW : maps_to
    INTERVIEW ||--o{ QUESTION_BANK : contains
    INTERVIEW ||--o{ INTERVIEW_RESPONSE : records
    INTERVIEW ||--o| EVALUATION : concludes

    CANDIDATE {
        uuid id PK
        string name
        string email UK
        string phone
        bytea resume_data
        string resume_filename
        timestamp created_at
    }

    JOB {
        uuid id PK
        string title
        text description_text
        timestamp created_at
    }

    INTERVIEW {
        uuid id PK
        uuid candidate_id FK
        uuid job_id FK
        string status "scheduled | active | completed | evaluated"
        integer current_question_idx
        integer total_questions
        timestamp created_at
        timestamp completed_at
    }

    QUESTION_BANK {
        uuid id PK
        uuid interview_id FK
        string category
        text question_text
        integer sort_order
        timestamp created_at
    }

    INTERVIEW_RESPONSE {
        uuid id PK
        uuid interview_id FK
        uuid question_id FK
        text candidate_transcript
        text bot_transcript
        timestamp created_at
    }

    EVALUATION {
        uuid id PK
        uuid interview_id FK
        float technical_score
        float communication_score
        float overall_score
        string recommendation "Hire | Hold | Reject"
        text summary
        bytea pdf_report
        timestamp created_at
    }
```

---

## 5. Security Review

*   **Data Masking**: Candidate PDFs and Evaluation PDFs are kept entirely out of the public filesystem, stored safely as byte binaries inside the database.
*   **Decoupled Voice**: The Pipecat voice pipeline receives instructions from the Database, completely insulating the LLM logic from frontend manipulation.

---

## 6. Folder Structure (Clean Architecture)

```
pipecat/
├── PRD.md
├── architecture.md
├── requirements.txt
├── bot.py
├── frontend/                  # React + Vite Application
│   ├── index.css
│   └── src/pages/
├── src/
│   ├── config.py
│   ├── pipeline.py
│   ├── application/             # Business Logic & Orchestrators
│   │   ├── schemas.py
│   │   └── use_cases/
│   │       ├── register_candidate.py
│   │       ├── generate_questions.py
│   │       └── evaluate_interview.py
│   ├── infrastructure/          # Data Adapters & Outer Layers
│   │   └── db/
│   │       ├── database.py
│   │       ├── models.py
│   │       └── repository.py
│   ├── interface/               # Routers, Controllers, API Spec
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── candidate_handler.py
│   │   └── pipecat/
│   │       └── persistence.py
│   └── utils/
│       └── pdf_generator.py
```
