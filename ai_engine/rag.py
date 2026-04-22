from .groq_agent import GroqAgent, GroqAgentError, GroqNotConfiguredError
from .ollama_agent import OllamaAgent, OllamaAgentError, OllamaNotReadyError
from .fallback import fallback_response

class RAGAssistant:
    def __init__(self, memory, user_profile=None):
        self.memory = memory
        self.primary_llm = GroqAgent()
        self.fallback_llm = OllamaAgent()
        self.llm = self.fallback_llm
        self.user_profile = user_profile or {
            "name": "MaaSathi",
            "household": "two adults and one child",
            "diet": "vegetarian with occasional high-protein meals",
        }
        self.max_context_docs = 3
        self.max_context_chars = 700

    def _clip_text(self, text, limit=220):
        text = " ".join(str(text).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _format_context(self, docs):
        if not docs:
            return "No relevant context was found in memory."
        lines = []
        total_chars = 0
        for doc in docs[:self.max_context_docs]:
            clipped = self._clip_text(doc["page_content"])
            remaining = self.max_context_chars - total_chars
            if remaining <= 0:
                break
            if len(clipped) > remaining:
                clipped = self._clip_text(clipped, remaining)
            lines.append(f"- {clipped}")
            total_chars += len(clipped)
        return "\n".join(lines) if lines else "No relevant context was found in memory."

    def _build_prompt(self, user_input, docs, purpose, extra=None):
        context_section = self._format_context(docs)
        instructions = (
            "You are MaaSathi AI, the intelligent life assistant for mothers. "
            "Use past memory, meal preferences, reminders, tasks, and safety logs to provide helpful recommendations. "
            "Always personalize responses for a busy family and keep answers practical. "
            "Respond in a systematic format using short labeled sections when useful. "
            "Prefer headings like Summary, Priority Actions, Schedule, Tips, and Next Step. "
            "Use bullets or numbered lists instead of long dense paragraphs."
        )
        if purpose == "task_balance":
            task_text = extra.get("tasks_text", "No current task list available.")
            return (
                f"{instructions}\n\n"
                f"Current household profile: {self.user_profile['household']}. Diet profile: {self.user_profile['diet']}.\n"
                f"Task inventory:\n{task_text}\n\n"
                f"Memory context:\n{context_section}\n\n"
                f"Question: {user_input}\n"
                f"Provide a practical workload plan, prioritizing urgent tasks and fair assignment. "
                f"Structure it as: Summary, Priority Actions, Assignment Plan, and Next Step."
            )
        if purpose == "meal_planner":
            ingredients = extra.get("ingredients", "")
            return (
                f"{instructions}\n\n"
                f"User food preferences: {self.user_profile['diet']}.\n"
                f"Available ingredients: {ingredients}.\n"
                f"Memory context:\n{context_section}\n\n"
                f"Question: {user_input}\n"
                f"Provide a meal suggestion plan for today and tomorrow using these ingredients. "
                f"Structure it as: Summary, Today, Tomorrow, and Prep Tips."
            )
        if purpose == "safety":
            return (
                f"{instructions}\n\n"
                f"Memory context:\n{context_section}\n\n"
                f"Question: {user_input}\n"
                f"Offer safety advice, predictive hazard suggestions, and an immediate next step. "
                f"Structure it as: Immediate Action, Safety Checks, and Next Step."
            )
        if purpose == "day_plan":
            energy_level = extra.get("energy_level", "medium")
            available_minutes = extra.get("available_minutes", "90")
            focus_area = extra.get("focus_area", "home rhythm")
            return (
                f"{instructions}\n\n"
                f"Current household profile: {self.user_profile['household']}. Diet profile: {self.user_profile['diet']}.\n"
                f"Mother's current energy level: {energy_level}.\n"
                f"Available time today: {available_minutes} minutes.\n"
                f"Main focus for today: {focus_area}.\n"
                f"Memory context:\n{context_section}\n\n"
                f"Question: {user_input}\n"
                f"Create a realistic motherhood day plan with 3 priority actions, 2 optional actions, and 1 reset tip. "
                f"Structure it as: Summary, Priority Actions, Optional Actions, and Reset Tip."
            )
        return (
            f"{instructions}\n\n"
            f"Memory context:\n{context_section}\n\n"
            f"User query: {user_input}\n"
            f"Respond with a context-aware, family-first answer. "
            f"Prefer a short Summary, actionable bullet points, and a clear Next Step."
        )

    def status(self):
        primary = self.primary_llm.status()
        backup = self.fallback_llm.status()
        provider = "fallback"
        summary = backup.get("message", "Backup AI status unavailable.")

        if primary.get("ready"):
            provider = "groq"
            summary = primary.get("message", "Groq is ready.")
        elif backup.get("ready"):
            provider = "ollama"
            summary = backup.get("message", "Ollama backup is ready.")
        elif primary.get("configured"):
            provider = "groq"
            summary = primary.get("message", "Groq is configured.")

        return {
            "provider": provider,
            "message": summary,
            "primary": primary,
            "backup": backup,
            "online": bool(primary.get("online") or backup.get("online")),
            "ready": bool(primary.get("ready") or backup.get("ready")),
            "active_model": (
                primary.get("active_model")
                if provider == "groq"
                else backup.get("active_model")
            ),
        }

    def generate(self, user_input, purpose="chat", extra=None):
        docs = self.memory.similarity_search(user_input, k=self.max_context_docs)
        prompt = self._build_prompt(user_input, docs, purpose, extra or {})
        try:
            return self.primary_llm.generate(prompt)
        except GroqNotConfiguredError:
            pass
        except GroqAgentError:
            pass

        try:
            return self.fallback_llm.generate(prompt)
        except OllamaNotReadyError as exc:
            return str(exc)
        except OllamaAgentError as exc:
            return f"I reached Ollama, but it could not complete the request: {exc}"
        except RuntimeError as exc:
            return f"I reached Ollama, but the request failed: {exc}"
        except Exception:
            return fallback_response(user_input, docs, extra)
