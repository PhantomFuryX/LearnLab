# LearnLab Agentic Architecture

This document outlines the multi-agent system powering LearnLab.

## 🧠 Agent System

The system uses a hub-and-spoke architecture where specialized agents handle specific domains.

### 1. Orchestrator (`backend/core/orchestrator.py`)
- Routes user intents to the correct agent (Knowledge, Automation, Integration).
- Manages state and history.
- **Graph Flow**: Uses a lightweight state graph to manage agent transitions.

### 2. Specialized Agents

| Agent | File | Responsibility |
|-------|------|----------------|
| **Planner** | `planner_agent.py` | Generates JSON curricula, milestones, and schedules. |
| **Quiz** | `quiz_agent.py` | Generates assessment questions and grades user answers. |
| **Research** | `research_agent.py` | multi-step search (ArXiv/Web), storage, and synthesis. |
| **Knowledge** | `knowledge_agent.py` | Handles RAG (Retrieval Augmented Generation) queries. |
| **Automation** | `automation_agent.py` | (Pending) Handles n8n webhook triggers. |

### 3. Services

- **LLMService**: Central wrapper for OpenAI/Anthropic with rate limiting and **Redis Caching**.
- **RAGService**: Manages ChromaDB, ingestion (Trafilatura/BeautifulSoup), and embeddings.
- **UserService**: Handles Auth, Profiles, and API Key encryption.
- **CacheService**: Redis abstraction for key-value storage.

## 🛠️ Development Guidelines

- **Strict JSON**: Agents typically output strict JSON for frontend consumption.
- **Async/Await**: All I/O bound operations (LLM, DB, Network) must be async.
- **Testing**: Use `backend/tests/` (to be implemented).

## 🔄 Data Flow

1. **Frontend** sends request to specific Router (e.g., `/api/v1/plans`).
2. **Router** validates input (Pydantic) and calls the specific **Agent**.
3. **Agent** constructs prompt, calls **LLMService**.
4. **LLMService** checks **Cache**. If miss, calls API.
5. **Agent** processes response (parses JSON) and returns data.
6. **Router** saves result to **MongoDB** (via DBService) and returns to Frontend.
