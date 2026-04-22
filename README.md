# MaaSathi AI Code Analysis

This document is a code-driven walkthrough of the current MaaSathi AI repository. It is based on the implementation in the Flask backend, AI engine modules, and static frontend files.

## What The Project Is

MaaSathi AI is a full-stack assistant for mothers built as:

- A Flask backend in `backend/app.py`
- A local/static frontend in `frontend/`
- An AI layer in `ai_engine/`
- A local vector memory store using FAISS and Sentence Transformers
- A provider chain that prefers Groq, falls back to Ollama, and finally uses rule-based responses

The application supports:

- Registration and login with server-side sessions
- Dashboard overview metrics
- Task management
- Reminder management
- Meal saving and meal-plan generation
- Safety logs and SOS guidance
- General AI chat
- Energy-smart day planning

## Top-Level Structure

```mermaid
graph TD
    A["frontend/"] --> B["dashboard.js + HTML pages"]
    C["backend/app.py"] --> D["Auth routes"]
    C --> E["Data routes"]
    C --> F["AI assist routes"]
    C --> G["Static file serving"]

    H["ai_engine/vector_memory.py"] --> I["FAISS index"]
    H --> J["docs.pkl metadata store"]
    K["ai_engine/rag.py"] --> L["GroqAgent"]
    K --> M["OllamaAgent"]
    K --> N["fallback_response"]

    C --> H
    C --> K
    O["data/users.json"] --> C
    P["data/vector_memory/"] --> H
```

## Runtime Architecture

```mermaid
flowchart LR
    U["Browser"] --> F["Flask app<br/>backend/app.py"]
    F --> S["Session auth<br/>Flask session cookie"]
    F --> D["In-memory app data<br/>tasks/reminders/meals/safety"]
    F --> VM["VectorMemory"]
    F --> R["RAGAssistant"]

    VM --> FA["FAISS index.faiss"]
    VM --> PK["docs.pkl"]

    R --> G["GroqAgent<br/>primary"]
    R --> O["OllamaAgent<br/>backup"]
    R --> RB["Rule fallback"]
```

## Main Backend Responsibilities

The backend in `backend/app.py` is the central orchestrator.

- Serves `frontend/index.html` at `/`
- Serves other frontend files through `/<path:path>`
- Loads environment variables from the project root `.env`
- Creates the `data/` folder if missing
- Initializes vector memory at `data/vector_memory`
- Seeds vector memory from `ai_engine/sample_data.py` if the store is empty
- Keeps tasks, reminders, meals, and safety logs in process memory
- Stores registered users in `data/users.json`
- Uses Flask session cookies for authentication state

## Request/Response Layers

```mermaid
flowchart TD
    A["Client request"] --> B["Flask route"]
    B --> C{"Protected route?"}
    C -- "No" --> D["Handle request directly"]
    C -- "Yes" --> E["login_required"]
    E --> F{"session user_id exists?"}
    F -- "No" --> G["401 JSON + redirect hint"]
    F -- "Yes" --> D
    D --> H["JSON response or static file"]
```

## Authentication Flow

Authentication is simple and file-backed.

- Users are stored by email in `data/users.json`
- Passwords are hashed with HMAC SHA-256 using a static salt string
- Successful register/login writes `user_id`, `user_email`, `user_name`, and `user_avatar` into session
- Protected API routes use the `login_required` decorator

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Flask
    participant Users as users.json
    participant Session as Flask Session

    User->>Frontend: Submit register or login form
    Frontend->>Flask: POST /api/auth/register or /api/auth/login
    Flask->>Users: Read existing users
    alt Register
        Flask->>Users: Write new user with hashed password
    else Login
        Flask->>Flask: Compare hashed password
    end
    Flask->>Session: Save user_id, user_email, user_name, user_avatar
    Flask-->>Frontend: Auth success JSON
    Frontend-->>User: Redirect to dashboard.html
```

## API Surface

### Public routes

- `/`
- `/<path:path>`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Protected data routes

- `GET /api/overview`
- `GET, POST /api/tasks`
- `PATCH, DELETE /api/tasks/<task_id>`
- `GET, POST /api/reminders`
- `DELETE /api/reminders/<rem_id>`
- `GET, POST /api/meals`
- `GET /api/safety`
- `POST /api/safety/alert`

### Protected AI routes

- `POST /api/assist/task_balance`
- `POST /api/assist/meal_planner`
- `POST /api/assist/day_plan`
- `POST /api/chat`
- `GET /api/ai/status`

## Feature Map

```mermaid
mindmap
  root((MaaSathi AI))
    Auth
      Register
      Login
      Logout
      Session check
    Dashboard
      Overview counts
      Quick chat
      AI provider status
      Day plan
    Tasks
      List
      Add
      Update status
      Delete
      AI balance
    Reminders
      List
      Add
      Auto priority detection
      Delete
      Sound controls
    Meals
      List saved meals
      Save meal
      AI meal planner
    Safety
      View safety logs
      Trigger SOS
      AI safety guidance
    AI
      Chat
      RAG memory retrieval
      Groq primary
      Ollama backup
      Rule fallback
```

## Data Lifecycle

The project uses two different persistence styles:

- File-backed persistence for users and vector memory
- In-memory runtime collections for business objects

### Persisted data

- `data/users.json`
- `data/vector_memory/index.faiss`
- `data/vector_memory/docs.pkl`

### Non-persisted runtime collections

- `TASKS`
- `REMINDERS`
- `MEALS`
- `SAFETY_LOGS`

Those collections are initialized from `ai_engine/sample_data.py` and updated at runtime, but they are not written back to disk by the backend.

```mermaid
flowchart TD
    A["sample_data.py"] --> B["Initial TASKS / REMINDERS / MEALS / SAFETY_LOGS"]
    C["API create/update/delete"] --> B
    D["Process restart"] --> E["Collections reset from sample_data.py"]

    F["push_memory()"] --> G["VectorMemory.add_documents()"]
    G --> H["docs.pkl"]
    G --> I["index.faiss"]

    J["Auth register/login"] --> K["users.json"]
```

## AI Engine Design

The AI pipeline is implemented across:

- `ai_engine/rag.py`
- `ai_engine/vector_memory.py`
- `ai_engine/groq_agent.py`
- `ai_engine/ollama_agent.py`
- `ai_engine/fallback.py`

### Core idea

1. Retrieve relevant memory documents from FAISS
2. Build a purpose-specific prompt
3. Try Groq first
4. If Groq is unavailable or fails, try Ollama
5. If that still fails, use a rule-based fallback response

```mermaid
flowchart TD
    A["User input"] --> B["VectorMemory.similarity_search()"]
    B --> C["Top-k docs"]
    C --> D["RAGAssistant._build_prompt()"]
    D --> E["Try GroqAgent.generate()"]
    E -->|success| F["Return Groq response"]
    E -->|not configured or error| G["Try OllamaAgent.generate()"]
    G -->|success| H["Return Ollama response"]
    G -->|not ready or error| I["fallback_response()"]
    I --> J["Return rule-based answer"]
```

## Prompt Specialization

`RAGAssistant` changes prompt structure by `purpose`.

- `task_balance`
- `meal_planner`
- `safety`
- `day_plan`
- default `chat`

Each mode injects different extra context such as:

- current task inventory
- available ingredients
- safety message
- energy level, time available, and focus area

```mermaid
graph TD
    A["assistant.generate(user_input, purpose, extra)"] --> B{"purpose"}
    B --> C["task_balance prompt"]
    B --> D["meal_planner prompt"]
    B --> E["safety prompt"]
    B --> F["day_plan prompt"]
    B --> G["generic chat prompt"]
```

## Vector Memory Internals

`VectorMemory` uses:

- `SentenceTransformer("all-MiniLM-L6-v2")`
- FAISS `IndexFlatIP`
- Pickled document storage

Stored documents have the shape:

- `page_content`
- `metadata`

Chat history documents are compacted to keep them shorter.

```mermaid
flowchart LR
    A["Document text"] --> B["SentenceTransformer embeddings"]
    B --> C["NumPy float32 vectors"]
    C --> D["FAISS IndexFlatIP"]
    A --> E["docs list with metadata"]
    D --> F["index.faiss"]
    E --> G["docs.pkl"]
```

## Memory Write Triggers

The backend writes to vector memory when users perform important actions.

- New task added
- New reminder added
- New meal saved
- New day plan requested
- New safety alert triggered
- New chat exchange summarized

```mermaid
flowchart TD
    A["Create task"] --> M["push_memory(type=task)"]
    B["Create reminder"] --> N["push_memory(type=reminder)"]
    C["Save meal"] --> O["push_memory(type=meal_preference)"]
    D["Request day plan"] --> P["push_memory(type=day_plan)"]
    E["Trigger safety alert"] --> Q["push_memory(type=safety)"]
    F["Chat completed"] --> R["summarize_chat_memory()"]
    R --> S["push_memory(type=chat_history)"]
```

## Groq And Ollama Provider Chain

### Groq

- Uses the OpenAI-compatible Groq chat completions endpoint
- Requires `GROQ_API_KEY`
- Default model is `llama-3.1-8b-instant`
- Uses `requests.Session` with `trust_env = False`

### Ollama

- Connects to `http://127.0.0.1:11434`
- Default model preference starts with `phi3:latest`
- Detects installed local models via `/api/tags`
- Tries multiple candidate models in preference order
- Falls through if a model requires more memory

```mermaid
sequenceDiagram
    participant App
    participant Groq
    participant Ollama
    participant Rules as Fallback Rules

    App->>Groq: generate(prompt)
    alt Groq success
        Groq-->>App: response text
    else Groq unavailable/error
        App->>Ollama: generate(prompt)
        alt Ollama success
            Ollama-->>App: response text
        else Ollama unavailable/error
            App->>Rules: fallback_response(query, docs)
            Rules-->>App: static guidance
        end
    end
```

## Frontend Pages

The frontend is a static multi-page UI.

- `frontend/index.html` is the landing page
- `frontend/login.html` is the sign-in page
- `frontend/register.html` is the account creation page
- `frontend/dashboard.html` is the authenticated app

The backend serves these files directly from the `frontend/` directory.

```mermaid
graph LR
    A["index.html"] --> B["login.html"]
    A --> C["register.html"]
    B --> D["dashboard.html"]
    C --> D
```

## Dashboard Frontend Logic

`frontend/dashboard.js` is the main client-side controller.

It handles:

- auth check on load
- sidebar navigation
- API calls with session cookies
- rendering lists and overview cards
- AI chat windows
- task/reminder/meal actions
- AI status polling every 30 seconds
- SOS flow
- reminder sound preferences in `localStorage`

```mermaid
flowchart TD
    A["DOMContentLoaded"] --> B["checkAuth()"]
    B -->|ok| C["Initialize dashboard"]
    C --> D["loadOverview()"]
    C --> E["checkAIStatus() every 30s"]
    C --> F["Bind forms and buttons"]
    F --> G["Tasks actions"]
    F --> H["Reminders actions"]
    F --> I["Meals actions"]
    F --> J["Chat actions"]
    F --> K["SOS actions"]
    F --> L["Day plan actions"]
```

## Dashboard Interaction Map

```mermaid
graph TD
    A["dashboard.html"] --> B["Overview section"]
    A --> C["Chat section"]
    A --> D["Tasks section"]
    A --> E["Reminders section"]
    A --> F["Meals section"]
    A --> G["Safety section"]

    B --> H["Quick chat"]
    B --> I["Current plan cards"]
    B --> J["Energy-smart day plan"]
    D --> K["Task CRUD"]
    D --> L["AI task balance"]
    E --> M["Reminder CRUD"]
    E --> N["Sound controls"]
    F --> O["AI meal planner"]
    F --> P["Saved meals"]
    G --> Q["SOS trigger"]
    G --> R["Safety logs"]
```

## Landing Page vs Dashboard Script

There are two different frontend JavaScript paths:

- `frontend/dashboard.js` is the active authenticated dashboard logic
- `frontend/script.js` appears to be an older or alternate script for a simpler UI flow

`script.js` still references endpoints like:

- `/overview`
- `/chat`
- `/assist/task_balance`

Those are appended to `http://127.0.0.1:5000/api`, so they still resolve correctly, but the current main dashboard experience is clearly built around `dashboard.html` + `dashboard.js`.

## Important Implementation Observations

### 1. Tasks, reminders, meals, and safety logs are not persisted

Only users and vector memory survive restarts. The runtime collections are rebuilt from sample data every time the Flask app restarts.

### 2. Memory and visible business data can diverge

If a user adds tasks or reminders, those actions are written into vector memory and survive in `data/vector_memory/`, but the task and reminder lists themselves reset on restart.

### 3. The root landing page copy does not fully match the provider chain

`frontend/index.html` markets the app as fully local and Ollama-powered, while the actual code prefers Groq first and only then uses Ollama backup.

### 4. Authentication is simple but not production-grade

- Password hashing uses a fixed salt rather than per-user salts
- Users are stored in a flat JSON file
- Flask secret key has a development fallback value

### 5. The app is intentionally easy to demo

The seeded sample data, in-memory feature collections, and static frontend make it easy to run locally without setting up a database.

## End-To-End User Journey

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Backend
    participant Memory as VectorMemory
    participant AI as RAGAssistant

    User->>Browser: Login
    Browser->>Backend: POST /api/auth/login
    Backend-->>Browser: Session established

    User->>Browser: Open dashboard
    Browser->>Backend: GET /api/auth/me
    Backend-->>Browser: Authenticated user

    User->>Browser: Add task / reminder / meal
    Browser->>Backend: Protected POST request
    Backend->>Memory: push_memory(...)
    Backend-->>Browser: Updated item JSON

    User->>Browser: Ask AI question
    Browser->>Backend: POST /api/chat or /api/assist/*
    Backend->>AI: generate(...)
    AI->>Memory: similarity_search(...)
    AI-->>Backend: final answer
    Backend->>Memory: save summary when needed
    Backend-->>Browser: AI response JSON
```

## File-Level Summary

- `backend/app.py`: Flask server, route definitions, auth/session handling, in-memory business state, AI entry points
- `ai_engine/rag.py`: prompt construction, memory retrieval, provider fallback sequence
- `ai_engine/vector_memory.py`: embeddings, FAISS storage, similarity search, compaction
- `ai_engine/groq_agent.py`: Groq HTTP client wrapper
- `ai_engine/ollama_agent.py`: Ollama model discovery and generation wrapper
- `ai_engine/fallback.py`: keyword-based rule responses
- `ai_engine/sample_data.py`: initial demo data and vector seed documents
- `frontend/dashboard.html`: main authenticated UI
- `frontend/dashboard.js`: dashboard behavior and API orchestration
- `frontend/index.html`: marketing/landing page
- `frontend/login.html`: login page
- `frontend/register.html`: registration page
- `frontend/script.js`: alternate or legacy simplified client flow

## Summary

MaaSathi AI is currently a Flask-based local-first demo application with a richer architecture than a basic CRUD dashboard:

- session-based auth
- static frontend delivery
- in-memory domain data
- persistent vector memory
- prompt-specialized RAG orchestration
- Groq primary inference
- Ollama local backup
- rule-based final fallback

The main architectural strength is the simple but effective AI pipeline. The main architectural limitation is that most user-facing business data is still volatile across server restarts.
