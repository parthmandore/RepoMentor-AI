# 🧠 Repository Mentor AI

Repository Mentor AI is a production-ready repository analysis platform designed to evaluate and understand codebases in seconds. Built for developers, recruiters, and engineering managers, it provides deterministic metrics, automated security vulnerability scanning, interactive dependency visualization, and a RAG-powered AI codebase mentor.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([User]) <--> Frontend[Next.js 14 Web UI]
    Frontend <--> Backend[FastAPI Server]
    Backend <--> Database[(PostgreSQL + pgvector)]
    Backend <--> FastEmbed[Local Embeddings Engine]
    Backend <--> Groq[Groq Llama-3.1 API]
```

---

## 🛠️ Features

- **Automated Repository Scanning**: Decoupled ingestion pipeline clones, scans, and parses files from any public or accessible repository.
- **Deterministic Health Scoring**: Generates health scores (0-100) and grades (A-F) based on static metrics, codebase complexity, code smells, and security posture.
- **Interactive Architecture Mapping**: Visualizes module dependency graphs using ReactFlow to reveal structure and dependencies.
- **Codebase Knowledge Base**: Decouples files into semantic chunks using local `FastEmbed` and indexes them into `pgvector` for instant code retrieval.
- **Interactive AI Mentor**: Provides a conversational RAG pipeline to walk through refactoring, explain functionality, and locate implementations.
- **Automated Security Review**: Scans code for vulnerabilities with severity classification and detailed remediation recommendations.
- **Actionable Task Planner**: Generates prioritized refactoring tasks mapped to specific lines of code, estimating health gains and implementation times.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router), React, TypeScript, Tailwind CSS, ReactFlow | Decoupled client with premium Glassmorphism design and real-time state synchronization. |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy, Pydantic | Decoupled REST API orchestrating analysis, chunking, and AI integrations. |
| **Database** | PostgreSQL 15 + `pgvector` extension | Decoupled relational storage for code metrics and high-dimensional vector embeddings. |
| **Embeddings** | FastEmbed (`BAAI/bge-small-en-v1.5`) | Runs local CPU-bound embedding generation (384-dimension vectors). |
| **LLM Runtime**| Groq Cloud API (`llama-3.1-8b-instant`) | Serverless inference engine for low-latency code-review QA. |
| **Migrations** | Alembic | Structured database schema versioning. |
| **Packaging**  | Docker, Docker Compose | Modular containers configuration for local development. |

---

## 📂 Project Structure

```text
repository-mentor-ai/
├── frontend/                    # Next.js 14 Client
│   ├── src/app/                 # App Router Pages
│   │   ├── page.tsx             # Landing Page
│   │   ├── globals.css          # Design system & theme tokens
│   │   ├── ThemeToggle.tsx      # Slide-based theme switch
│   │   └── repositories/[id]/  # Repository Dashboard
│   │       ├── page.tsx         # Main overview dashboard
│   │       ├── architecture/    # ReactFlow module mapper
│   │       ├── security/        # Security auditor view
│   │       ├── knowledge/       # Vector DB explorer
│   │       ├── mentor/          # AI Chat workspace
│   │       └── assessment/      # Deep Code Assessment
│   └── Dockerfile
├── backend/                     # FastAPI Server
│   ├── app/
│   │   ├── main.py              # Application lifecycle entrypoint
│   │   ├── api/endpoints/       # Decoupled routers
│   │   ├── core/config.py       # Configuration and env loading
│   │   ├── models/              # SQLAlchemy database tables
│   │   └── services/            # Decoupled business logic
│   │       ├── ingestion/       # Git clones & static file parsers
│   │       ├── analysis/        # Smell & complexity computing
│   │       ├── architecture/    # Module relation mapping
│   │       ├── security/        # Vuln parsers
│   │       ├── knowledge/       # pgvector semantic chunking
│   │       └── expert/          # RAG QA & planners
│   ├── alembic/                 # Migration versions
│   └── Dockerfile
├── docker-compose.yml           # Unified services compositor
└── .env.example                 # Configuration blueprint
```

---

## 🚀 Setup & Installation

### Prerequisites

Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

### Docker Environment Quickstart

1. Clone the repository and configure your environment variables:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your keys:
   - **`GROQ_API_KEY`**: Obtain a key from the Groq console (required for AI Mentor).
   - **`DATABASE_URL`**: Leave default for local Docker PostgreSQL or point to a managed Supabase database.
3. Start the application:
   ```bash
   docker compose up --build
   ```
4. Access the platforms:
   - **Frontend**: `http://localhost:3000`
   - **Backend API**: `http://localhost:8080/api/v1`
   - **Interactive API Docs**: `http://localhost:8080/docs`

---

## ⚙️ Environment Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string with pgvector support | `postgresql://postgres:postgres@postgres:5432/repository_mentor` |
| `GROQ_API_KEY` | Groq Cloud platform API key (for LLM generation) | *Required* |
| `GROQ_MODEL` | Model used for RAG code reasoning | `llama-3.1-8b-instant` |
| `NEXT_PUBLIC_API_URL` | Frontend connection endpoint for API routing | `http://localhost:8080/api/v1` |

---

## 🛣️ Future Roadmap

- **Incremental Re-indexing**: Analyze and index only modified files on repository commits instead of full rebuilds.
- **Repository Comparison View**: Side-by-side architecture, security, and complexity visualizer for structural diffs.
- **Multilingual Tokenizer**: Expand file parsers and analyzers to support C++, Rust, and Go architecture maps.
- **Local LLM Fallback**: Re-add configuration pathways for fully offline local deployment using local Ollama runners.
- **Auto-generated Pull Request Fixes**: Create direct GitHub PR remediation pipelines for detected smells/vulns.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
