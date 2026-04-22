# MaaSathi AI

Intelligent life assistant for mothers.

## Overview

MaaSathi AI is a practical full-stack system built with:

- Python + Flask backend
- LangChain + FAISS vector memory
- Sentence-Transformers embeddings
- Groq as the primary AI provider
- Local Ollama fallback for offline or backup generation
- HTML/CSS/JavaScript frontend

This system uses Retrieval-Augmented Generation (RAG) to remember user tasks, reminders, meal preferences, safety logs, and chat history.

## Features

- Smart task balancing
- Memory-based reminders
- Nutrition planning with meal personalization
- Safety suggestions and SOS support
- Context-aware AI chat assistant
- Energy-Smart Day Plan for realistic motherhood planning

## Setup

1. Install Python dependencies:

```powershell
cd "E:\SmartBridge\MaaSathi AI"
python -m pip install -r requirements.txt
```

2. Add your Groq API key in a `.env` file at the project root:

```powershell
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
OLLAMA_MODEL=phi3:latest
```

3. Install and start Ollama locally for backup usage.

- Install Ollama from https://ollama.com
- Start the Ollama daemon or run `ollama serve`
- Pull a backup model such as `ollama pull phi3`

4. Run the Flask backend:

```powershell
python backend/app.py
```

5. Open `frontend/index.html` in the browser.

## AI Providers

MaaSathi now uses:

- Groq first for fast real-time responses
- Ollama as the local backup when Groq is unavailable
- Rule-based fallback if both providers are unavailable

The Ollama backup assumes a local model is available at `http://127.0.0.1:11434`.

## Project Structure

- `backend/` - Flask app and API routes
- `ai_engine/` - vector memory, RAG pipeline, Groq and Ollama wrappers, sample seed data
- `frontend/` - dashboard UI, JavaScript, styles

## Notes

- Groq requires an API key.
- Retrieval and memory still run locally with embeddings + vector memory.
- If Groq is unavailable, MaaSathi tries Ollama automatically.
- If both providers fail, the system uses a rule-based intelligent fallback.
