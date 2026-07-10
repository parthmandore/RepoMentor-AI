# Repository Mentor AI — Production Deployment Guide

This document provides step-by-step instructions for deploying Repository Mentor AI to production environments (FastAPI on Render and Next.js 14 on Netlify) using Supabase as the PostgreSQL + pgvector database.

---

## 1. Managed Database Setup (Supabase)

Repository Mentor AI requires a PostgreSQL database with `pgvector` support.
1. Create a project on [Supabase](https://supabase.com/).
2. Retrieve your connection string from the database settings page.
3. Keep the connection string handy for the backend environment setup.

---

## 2. Backend Server Deployment (Render)

The backend is deployed as a Web Service on Render using the Docker runtime.

### Configuration Steps:
1. Create a new **Web Service** on Render and link your GitHub Repository.
2. Select **Docker** as the Runtime environment.
3. Choose the **Free** instance type (512 MB RAM, 0.1 vCPU).
4. Click **Advanced Settings** and configure the following paths:
   * **Dockerfile Path**: `backend/Dockerfile`
   * **Build Context**: `backend`
5. Input the following Environment Variables in the Render console:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres` | Managed Supabase connection pooler URL. |
| `GROQ_API_KEY` | `gsk_your_groq_api_key` | Groq Cloud platform API key (for Llama-3.1 inference). |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Model used for RAG code reasoning. |
| `ENABLE_KNOWLEDGE_BASE` | `true` | Set to `false` to disable FastEmbed ONNX engine (reduces memory to <90MB). |

6. Click **Deploy Web Service**. Render will build the container and deploy it automatically.

---

## 3. Frontend Client Deployment (Netlify)

The Next.js 14 frontend is deployed as a static site on Netlify.

### Configuration Steps:
1. Create a new Site on Netlify and link your GitHub Repository.
2. Configure the build settings:
   * **Base Directory**: `frontend`
   * **Build Command**: `npm run build`
   * **Publish Directory**: `frontend/.next`
3. Add the following Environment Variable in the Netlify site configuration:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://repomentor-ai.onrender.com/api/v1` | Your active Render backend API endpoint. |

4. Click **Deploy Site**. Netlify will build the client and deploy the application.
