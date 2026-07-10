# 🧠 Repository Mentor AI

[![Production Validated](https://img.shields.io/badge/Production-Validated-emerald?style=for-the-badge&logo=checkmarx&logoColor=white)](https://github.com/parthmandore/RepoMentor-AI)
[![Render Compatible](https://img.shields.io/badge/Render-Free%20Tier%20Compatible-blue?style=for-the-badge&logo=render&logoColor=white)](https://github.com/parthmandore/RepoMentor-AI)
[![Python Version](https://img.shields.io/badge/Python-3.11-gold?style=for-the-badge&logo=python&logoColor=white)](https://github.com/parthmandore/RepoMentor-AI)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://github.com/parthmandore/RepoMentor-AI)
[![pgvector](https://img.shields.io/badge/Vector-pgvector-orange?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/parthmandore/RepoMentor-AI)

Repository Mentor AI is a production-ready, high-performance repository analysis and intelligence platform. It performs deep codebase audits—evaluating code smells, structural complexity, and security vulnerabilities—while building a semantic knowledge base. Utilizing local vector embeddings and advanced RAG, it powers an interactive **AI Code Mentor** that guides developers through refactoring, architecture walkthroughs, and security remediations in real time.

---

## 🏗️ Architecture

Repository Mentor AI is built on a decoupled, service-oriented architecture designed to scale within highly constrained container resources (such as the Render Free Tier).

```mermaid
graph TB
    %% Client & Gateway
    User([Developer / Recruiter]) <-->|HTTPS / WSS| FE[Next.js 14 Web Portal]
    FE <-->|REST API / JSON| BE[FastAPI Gateway Server]

    %% Ingestion & Orchestration
    subgraph Backend Pipeline
        BE -->|Async Process| Cloner[Repo Cloner]
        Cloner -->|Local Walk| Parser[Static File Parser]
        Parser -->|ThreadPool| Analyzers[Parallel Analyzers]
        
        subgraph Static Analysis Engines
            Analyzers --> Metrics[Complexity & Metrics Engine]
            Analyzers --> Smells[Refactoring Smell Detector]
            Analyzers --> Security[AST Security Scanner]
        end
        
        subgraph Knowledge & Semantic Indexing
            Parser -->|Priority Queue| Chunker[Semantic Code Chunker]
            Chunker -->|FastEmbed Local| Embedder[ONNX Embedding Engine]
        end
    end

    %% Storage Layer
    Metrics & Smells & Security -->|SQLAlchemy Bulk Mappings| DB[(PostgreSQL Database)]
    Embedder -->|pgvector Insert| VectorDB[(PostgreSQL + pgvector)]
    
    %% AI Orchestration
    BE <-->|Context Grounding| RAG[RAG Pipeline]
    RAG <-->|Semantic Search| VectorDB
    RAG <-->|LLM Inference| Groq[Groq Llama-3.1 API]
```

---

## 🛠️ Technology Stack

| Component | Technologies | Implementation Details |
| :--- | :--- | :--- |
| **Frontend** | React, Next.js 14 (App Router), ReactFlow, Tailwind CSS, TypeScript | Glassmorphism dashboard interface, dynamic dependency cycle graphs, real-time status polling, and slide-over evidence viewers. |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic, Alembic | Async REST API orchestrating multi-threaded codebase scanning, technology stack detection, and database transactions. |
| **Database** | PostgreSQL 15, `pgvector` extension | Stores file metadata, code smell details, security audit records, and high-dimensional vector embeddings in a single database instance. |
| **Local Embeddings** | FastEmbed (`BAAI/bge-small-en-v1.5`) | Runs local CPU-bound inference for 384-dimension vector generation. |
| **LLM Inference** | Groq Cloud Platform (`llama-3.1-8b-instant`) | Serverless low-latency model inference for RAG-grounded conversational code guidance. |

---

## 🚀 Key Features

* 📦 **Decoupled Repository Ingestion**: Clones, parses, and processes any public Git repository in parallel threads without blocking server lifecycle loops.
* 📐 **Deterministic Health Scoring**: Combines cyclomatic complexity, coupling/cohesion ratios, security vulnerabilities, and code smell counts into an explainable letter-grade score (`A` to `F`).
* 🔗 **Interactive Dependency Mapping**: Generates a module-level dependency diagram using **ReactFlow**, mapping structural relationships and highlighting dependency loops/cycles.
* 🛡️ **AST Security Auditing**: Scans source files for critical vulnerabilities, including SQL injection, hardcoded secrets, weak hashing functions, and unsafe API usages.
* 📚 **pgvector Code Knowledge Base**: Extracts structural context and semantic blocks from files, indexing them as vector embeddings for RAG grounding.
* 💬 **Explainable AI Mentor**: Features a conversational workspace where developers can ask repository-specific questions, receive inline code citations, and get step-by-step refactoring advice.
* 📋 **Actionable Refactoring Planner**: Produces a prioritized task checklist estimating time-to-fix, expected health score gain, and target code locations for every detected smell.

---

## 📂 Project Structure

```text
repository-mentor-ai/
├── frontend/                    # Next.js Client
│   ├── src/app/                 # Next.js App Router Routing
│   │   ├── page.tsx             # Landing Page
│   │   ├── globals.css          # Design system, CSS variables & themes
│   │   └── repositories/[id]/  # Interactive Code Dashboard
│   │       ├── architecture/    # ReactFlow module relations mapping
│   │       ├── assessment/      # Scorer explanation & code simulator
│   │       ├── knowledge/       # pgvector semantic block explorer
│   │       ├── mentor/          # AI Chat RAG workspace
│   │       └── security/        # Security auditor view
│   ├── Dockerfile               # Client container specification
│   └── package.json             # JS Dependencies and builds
├── backend/                     # FastAPI Backend Server
│   ├── app/
│   │   ├── main.py              # Application initialization & middleware
│   │   ├── api/endpoints/       # API Router controllers
│   │   ├── core/config.py       # Configuration and env loaders
│   │   ├── models/              # SQLAlchemy schema declarations
│   │   └── services/            # Decoupled business logic
│   │       ├── ingestion/       # Git cloner & static file parser
│   │       ├── analysis/        # Smell & metric calculation pipelines
│   │       ├── architecture/    # ReactFlow node/link generators
│   │       ├── security/        # AST regex scanners
│   │       ├── knowledge/       # FastEmbed + pgvector chunk pipelines
│   │       └── expert/          # RAG QA & pipelines
│   ├── alembic/                 # Database migrations
│   ├── Dockerfile               # Server container specification
│   └── requirements.txt         # Python dependencies
├── docker-compose.yml           # Unified services compositor
├── netlify.toml                 # Frontend deployment configuration
└── .env.example                 # Configuration blueprint
```

---

## ⚙️ Performance & Memory Optimizations

Repository Mentor AI was designed for deployment on highly resource-constrained environments like **Render Free Tier (512 MB RAM / 0.1 vCPU)**. The following architectural optimizations keep memory footprint minimal and speed optimal:

### 1. ONNX Runtime & FastEmbed Custom Tuning
By default, ONNX Runtime allocates large C++ memory arenas and spins up multi-threaded pools, which consumes **~2.3 GB of virtual address space**, causing immediate Out-of-Memory (OOM) kills on Render.
* **Patched Inference Session Options**: We hook the `onnxruntime.InferenceSession.__init__` call to enforce:
  * `intra_op_num_threads = 2` and `inter_op_num_threads = 2` (limits CPU usage on free cores).
  * `enable_cpu_mem_arena = False` (disables massive Virtual Address reservations).
  * `graph_optimization_level = ORT_ENABLE_BASIC` (reduces memory-heavy graph compile overhead).
* **Eviction of Model Cache**: Following the knowledge base indexing stage, the global FastEmbed model instance cache is cleared via `embedder._model = None` and Python's garbage collector `gc.collect()` is triggered immediately, releasing **~200 MB of native RAM**.

### 2. Database Write Optimization (Batch Mappings)
Instead of row-by-row ORM inserts (which create massive session tracking overhead and sequential network round-trips), the backend utilizes SQLAlchemy Core's **`bulk_insert_mappings()`** and **`bulk_update_mappings()`**.
* Bypasses the instantiation of heavy SQLAlchemy ORM objects.
* Groups file metrics, code smells, and security vulnerability writes into single-transaction batches.
* **Result**: **80%+ reduction** in database connection lock durations and network round-trips.

### 3. Aggressive Memory Eviction (Knowledge Base Generation)
* Implements in-memory list clearing (`.clear()`) and explicit garbage collection (`del`) on candidate chunks and raw text arrays immediately after database insertion.
* Ensures memory footprint remains completely flat across consecutive stress testing iterations.

---

## 📊 Production Validation & Benchmarks

The backend was validated in a production-grade `python:3.11-slim` Linux Docker container under stress testing constraints:

### 1. Memory Profile (Stable vs. Startup)

| State | Memory RSS | Threads Count | DB Connections |
| :--- | :--- | :--- | :--- |
| **Idle Startup** | `68 MB` | 36 | 2 |
| **Post-Database Handshake** | `122 MB` | 36 | 2 |
| **Peak Ingestion (Embedding Phase)** | `345 MB` | 51 | 9 |
| **Post-Eviction Cleanup (Idle)** | `315 MB` | 51 | 8 |
| **Stress Run 5 (Loop Average)** | `315.55 MB` | 51 | 8 |

* **Headroom**: With a peak memory footprint of **345 MB**, the backend guarantees a **167 MB safety margin** under the 512 MB Render Free Tier limit.
* **Memory Leak Trajectory**: Over 5 consecutive repository ingestion stress tests, the stable post-cleanup RSS remained flat at **315 MB** (0 MB leakage).

### 2. Ingestion Performance Benchmarks

| Repository | Files | Total Duration | Avg per File | Health Score | Smells / Vulns |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **simple-feedback-hub** | 75 | `34.23s` | 0.45s | 74 / 100 | 14 / 0 |
| **AegisHealth** | 38 | `31.32s` | 0.82s | 58 / 100 | 192 / 0 |
| **codegenie-ai** | 50 | `57.60s` | 1.15s | 51 / 100 | 258 / 1 |

### 3. Concurrent Request Handling
Multi-threaded python workers were validated against simultaneous ingestion workloads:
* **2 Concurrent Ingests**: `100% Success` (Duration: 59.07s)
* **3 Concurrent Ingests**: `100% Success` (Duration: 43.82s)
* **Result**: Zero SQLAlchemy connection pool deadlocks or database transaction collisions.

---

## 🛠️ Setup & Installation

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Version 20.10 or higher)

### Environment Configuration
1. Clone the repository and copy the environment blueprint:
   ```bash
   cp .env.example .env
   ```
2. Configure the following variables inside `.env`:
   ```ini
   # Groq LLM Provider configuration (Required for AI Mentor)
   GROQ_API_KEY=gsk_your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant

   # Database settings (Defaults are pre-configured for Docker setup)
   DATABASE_URL=postgresql://postgres:postgres@postgres:5432/repository_mentor

   # Memory Optimization Fallback
   # Set to 'false' to disable FastEmbed ONNX engine (reduces memory to <90MB)
   ENABLE_KNOWLEDGE_BASE=true
   ```

### Running Locally with Docker Compose

1. Build and run all containerized services:
   ```bash
   docker compose up --build
   ```
2. Access the active local platforms:
   * 💻 **Next.js Web Portal**: `http://localhost:3000`
   * ⚙️ **FastAPI Gateway Server**: `http://localhost:8080`
   * 📑 **Interactive API Documentation (Swagger)**: `http://localhost:8080/docs`

---

## 🌐 Production Deployment

### Backend Server (Render Deployment)
Repository Mentor AI is configured for one-click Docker deployments on Render.
1. Create a new **Web Service** on Render and connect your Git Repository.
2. Select **Docker** as the Runtime environment.
3. Choose the **Free** instance type (512MB RAM, 0.1 vCPU).
4. Under **Advanced Settings**, configure:
   * **Dockerfile Path**: `backend/Dockerfile`
   * **Build Context**: `backend`
5. Input the following Environment Variables in the Render console:
   * `DATABASE_URL`: Your managed Supabase/Neon PostgreSQL connection string.
   * `GROQ_API_KEY`: Your active Groq API Key.
   * `ENABLE_KNOWLEDGE_BASE`: `true`

### Frontend Client (Netlify Deployment)
1. Create a new Site on Netlify and connect your Git Repository.
2. Configure the site settings:
   * **Base Directory**: `frontend`
   * **Build Command**: `npm run build`
   * **Publish Directory**: `frontend/.next`
3. Add the following Environment Variable in Netlify's build console:
   * `NEXT_PUBLIC_API_URL`: Your deployed Render backend URL (e.g. `https://your-app.onrender.com/api/v1`).

---

## 🛣️ Future Roadmap

- [ ] **Incremental Re-indexing**: Analyze and update database vectors only for modified files in repository updates instead of triggering full rebuilds.
- [ ] **Fully Offline Ollama Provider**: Provide configuration mappings for self-hosted local Ollama servers to ensure data privacy.
- [ ] **Auto-Generated Remediation Pull Requests**: Allow the AI Mentor to generate and commit refactoring fixes directly to the analyzed repository.
- [ ] **Multilingual Architecture Support**: Expand static parsers to build visual dependency cycles for Rust, Go, and C++ codebases.

---

## 📄 License & Credits

Distributed under the **MIT License**. See `LICENSE` for more information.

### Author
* **Parth Mandore** — [GitHub Profile](https://github.com/parthmandore)

### Acknowledgements
* [ONNX Runtime Group](https://onnxruntime.ai/) for high-speed local inference.
* [Groq Cloud Team](https://groq.com/) for serverless Llama-3.1 inference.
* [Supabase PGVector](https://supabase.com/docs/guides/database/extensions/pgvector) for cloud vector database architecture support.
