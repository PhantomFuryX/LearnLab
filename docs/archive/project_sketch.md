# 🧠 LearnLab — Multi-Agent AI Automation Manager

## 📘 Overview

**LearnLab** is a multi-agent AI automation platform that combines **LangGraph**, **LangChain**, **FastAPI**, and **n8n** to execute intelligent workflow automations.  
It allows users to interact with a **central orchestrator agent**, which coordinates **specialized agents** to perform AI-driven automation and connect with external APIs or services through **n8n**.

---

## 🎯 Objective

- Learn and demonstrate **LangGraph** and **LangChain** for multi-agent orchestration.  
- Build a **FastAPI backend** that handles user requests and orchestrates agents.  
- Integrate **n8n** for real-world automation (email, Slack, Notion, etc.).  
- Showcase how multiple AI agents can collaborate to perform meaningful automation.  
- Deploy the system as a **web application** (FastAPI + frontend dashboard).

---

##Core Concept:
A web platform where a team of agents automatically discovers the latest AI knowledge (papers, tools, tutorials), turns it into short summaries, runnable code demos, lesson modules, and shareable posts — while also tutoring users through personalized learning paths and quizzes.

Key user flows:

“Show me this week’s top AI research + runnable example”

“Make a 1-hour learning plan on agentic AI”

“Generate a LinkedIn post & code snippet from this paper”

Interactive tutoring + quizzes based on content the system discovered

🧩 Core Agents (concrete, ready-to-build)

Research Agent

Inputs: user query or scheduled job (e.g., “agent architectures”).

Tools: web search, arXiv API, RSS, Reddit / Twitter scraping, feed ingestion.

Outputs: ranked list of sources (title, link, date, excerpt).

Summarizer Agent

Inputs: Research Agent results.

Tasks: create TL;DR, 3–5 bullet summary, key takeaways, one-line headline.

Output: structured summary + extract of claims & methods.

Code Agent

Inputs: summary + target stack preference (LangChain/PyTorch).

Tasks: generate runnable example, explain steps, add comments and test prompts.

Output: code file(s) + short how-to.

Tutor Agent

Inputs: summary + user state (memory).

Tasks: conversational explanations, step-by-step walkthroughs, code walkthrough.

Output: chat responses, recommended exercises.

Quiz Agent

Inputs: summary + tutor content.

Tasks: generate 5–10 MCQs / short-answer questions; auto-grade rubric.

Output: quiz JSON, solutions, difficulty tags.

Planner Agent

Inputs: user goals, available time, past progress.

Tasks: craft study schedules, prioritize modules, set reminders.

Output: calendar items / task checklist (persisted).

Post Agent (Automation)

Inputs: selected summary + code snippet.

Tasks: create social copy (short, medium), image suggestion, hashtags.

Output: post drafts (LinkedIn/Twitter/Medium).

Orchestrator (LangGraph Controller)

Coordinates the graph flow: triggers the right agents in sequence/parallel, handles retries/failures, collects outputs.

⚙️ Minimal Viable Product (MVP) — prioritized features

Core must-haves

FastAPI backend with authenticated endpoints

LangGraph orchestration for Research → Summarize → Code → Tutor

One simple frontend page to:

request a topic,

view summary + code,

start a quick interactive tutoring chat,

generate a shareable post draft

Persistence: store summaries, code, user memory (MongoDB)

Vector store for retrieval-based tutoring (Chroma or FAISS)

Background queue for scheduled research jobs (Redis + RQ/Celery)

Nice-to-have (phase 2)

Quiz generation & grading

Schedule/Planner + calendar export

Social-post auto-scheduler (optional API integrations)

User profiles / progress tracking / achievements

🔁 Data & Control Flow (high-level)

User requests topic (or scheduled job triggers).

FastAPI receives request → creates task entry → pushes to queue.

Worker pops task → LangGraph builds graph:

Research Agent (RAG / web) → Summarizer → Code Agent (parallel) → Tutor/Quiz/Planner.

Agents store artifacts:

Summaries & metadata → DB

Embeddings → Vector store

Code → file storage (S3-like or DB blob)

FastAPI serves results to frontend; user can launch chat sessions where Tutor uses stored embeddings + memory to answer interactively.

🛠️ Tech Choices (concrete)

Backend: FastAPI (async)

Agents / Orchestration: LangGraph + LangChain (LLM wrappers, tools)

LLM Provider: OpenAI or a hybrid (OpenAI for core LLM; local/affordable models for dev/testing)

DB: MongoDB (document store) + Redis (cache, queue)

Vector DB: Chroma or FAISS (local) or Pinecone/Weaviate (hosted)

Task Queue: Celery or RQ (Redis-backed)

Storage: S3-compatible (for code artifacts)

Frontend: Next.js (React) — simple dashboard + chat

Deployment: Docker + cloud host (Render / Railway / AWS ECS)

Monitoring/Logging: Sentry + Prometheus / Grafana (optional)

🔐 Security & Practical Concerns (must-do)

Use API key vaults (env vars / secrets manager).

Rate-limit LLM calls and web scraping; cache research results.

Sanitize web-scraped content before prompting LLMs (avoid PII).

Implement user auth & roles for posting automation to social platforms.

Add permissioned scheduler and usage quotas per user to control cost.

## 🏗️ Project Structure

LearnLab/
│
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── routers/
│   │   ├── chat.py               # Handles chat and AI query routes
│   │   ├── automation.py         # Handles automation trigger routes
│   │   └── n8n_integration.py    # Routes for n8n webhook communication
│   ├── core/
│   │   ├── orchestrator.py       # Central orchestrator agent logic
│   │   ├── agents/
│   │   │   ├── automation_agent.py   # Creates automation plans
│   │   │   ├── knowledge_agent.py    # Fetches latest AI knowledge
│   │   │   ├── integration_agent.py  # Handles external integrations via APIs/n8n
│   │   └── langgraph_flow.py     # Defines the LangGraph agent graph
│   ├── services/
│   │   ├── langchain_manager.py  # Configures LangChain pipelines/tools
│   │   ├── n8n_service.py        # REST communication with n8n
│   │   ├── db_service.py         # MongoDB or SQLite storage for logs
│   │   └── llm_service.py        # LLM provider interface (OpenAI/Anthropic/Ollama)
│   └── utils/
│       ├── schema.py             # Pydantic models
│       ├── config.py             # Environment/config variables
│       └── helpers.py            # Common utility functions
│
├── frontend/
│   ├── pages/
│   │   ├── index.html            # Home page UI
│   │   └── dashboard.html        # Task dashboard UI
│   ├── static/
│   │   ├── js/
│   │   │   └── chat.js           # Frontend WebSocket chat logic
│   │   └── css/
│   │       └── style.css
│   └── api_client.js             # API client for frontend→backend communication
│
├── docs/
│   ├── PROJECT_OVERVIEW.md       # Overview of system purpose
│   ├── API_SPEC.md               # OpenAPI endpoints documentation
│   ├── FLOW_DESIGN.md            # LangGraph workflow and node design
│   └── n8n_SETUP.md              # Steps for integrating n8n
│
├── tests/
│   ├── test_chat.py
│   ├── test_automation.py
│   └── test_integration.py
│
├── .env                          # Environment variables (API keys, DB URLs)
├── requirements.txt              # Dependencies list
├── docker-compose.yml            # FastAPI + MongoDB + n8n container setup
└── README.md

---

## ⚙️ Core Technologies

| Purpose | Technology |
|----------|-------------|
| API Backend | FastAPI |
| Multi-Agent Framework | LangGraph + LangChain |
| Automation Engine | n8n |
| Database | MongoDB or SQLite |
| LLM Provider | OpenAI / Anthropic / Ollama |
| Frontend | HTML + JS + Tailwind or React |
| Containerization | Docker |
| Version Control | Git + GitHub |

---

## 🤖 Agents

| Agent | Function |
|--------|-----------|
| **Orchestrator Agent** | Main controller — decides which agent handles each task. |
| **Automation Agent** | Generates and manages automation workflows. |
| **Knowledge Agent** | Fetches and summarizes latest AI developments or resources. |
| **Integration Agent** | Interfaces with n8n and other APIs for real-world actions. |

---

## 🔄 LangGraph Flow (Simplified)

User → OrchestratorAgent
    → if task == 'AI research' → KnowledgeAgent
    → if task == 'automation' → AutomationAgent
    → if task == 'external' → IntegrationAgent (→ n8n)
→ Response → User

Graph nodes:
- InputNode
- DecisionNode
- AutomationNode
- KnowledgeNode
- IntegrationNode
- OutputNode

---

## 🌐 FastAPI Endpoints

| Endpoint | Method | Purpose |
|-----------|---------|----------|
| `/chat` | POST | Send user messages and receive AI responses |
| `/automate` | POST | Create or trigger automation workflows |
| `/n8n/trigger` | POST | Send payloads to n8n webhooks |
| `/logs` | GET | Fetch chat and automation history |
| `/status` | GET | System health check |

---

## 🔌 n8n Integration

- n8n runs in a **Docker container** alongside FastAPI.
- FastAPI sends automation tasks via **REST API calls** to n8n webhooks.
- Example:  
  POST http://localhost:5678/webhook/ai-automation
  {
      "action": "send_email",
      "data": { "subject": "Weekly Update", "body": "Summary of tasks" }
  }

- n8n handles:
  - Email sending
  - Slack / Discord messages
  - File uploads
  - Calendar events
  - Custom webhooks or external API automations

---

## 🚀 Setup Steps (for GitHub Copilot)

1. Create a folder:
   mkdir LearnLab && cd LearnLab
2. Add this file as:
   project_sketch.md
3. Ask Copilot:
   “Scaffold the backend structure based on project_sketch.md”
4. Then generate:
   requirements.txt
   docker-compose.yml
   main.py
5. Next prompt Copilot:
   “Implement orchestrator.py using LangGraph to manage three agent nodes: Automation, Knowledge, and Integration.”
6. Then generate:
   “n8n_service.py file that connects to n8n webhook via REST API.”

---

## 🧩 Future Expansions

- Add **user authentication** (JWT + role-based control).
- Add **persistent memory** for agents using MongoDB.
- Add **AI-powered dashboard insights** (auto-summary of automations).
- Add **plugins** for Google Drive, Notion, Slack, Trello, and more via n8n nodes.
- Build **React frontend** with live agent status and history visualizations.

---

## ✅ Goals

- Demonstrate mastery of LangGraph + LangChain multi-agent design.
- Build a deployable full-stack AI automation system.
- Integrate real-world tools (via n8n) for seamless workflow execution.
- Keep architecture modular and expandable.
