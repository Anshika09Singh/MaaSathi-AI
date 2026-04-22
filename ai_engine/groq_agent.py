import os
from typing import Optional

import requests


class GroqAgentError(RuntimeError):
    """Raised when Groq is configured but a request cannot be completed."""


class GroqNotConfiguredError(GroqAgentError):
    """Raised when a Groq API key is not available."""


class GroqAgent:
    """
    Talks to the Groq chat completions API.
    Uses OpenAI-compatible endpoints so the integration stays simple.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: str = "https://api.groq.com/openai/v1/chat/completions",
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "").strip()
        self.model = model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.endpoint = endpoint
        self.timeout = int(os.environ.get("GROQ_TIMEOUT", "25"))
        # Some local Windows setups inject dead proxy values like 127.0.0.1:9.
        # Groq requests should bypass those unless you explicitly wire a working proxy here.
        self.session = requests.Session()
        self.session.trust_env = False

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict:
        configured = self.is_configured()
        return {
            "provider": "groq",
            "configured": configured,
            "online": configured,
            "ready": configured,
            "active_model": self.model if configured else None,
            "message": (
                f"Groq is configured with model {self.model}."
                if configured
                else "Add GROQ_API_KEY to use Groq as the primary AI provider."
            ),
        }

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 300,
    ) -> str:
        if not self.is_configured():
            raise GroqNotConfiguredError(
                "Groq is not configured. Set GROQ_API_KEY to enable the primary AI provider."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MaaSathi AI, a practical and supportive motherhood assistant. "
                        "Give clear, realistic, family-first guidance with compassionate tone."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        try:
            resp = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                raise GroqAgentError("Groq returned no completion choices.")
            text = (
                choices[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not text:
                raise GroqAgentError("Groq returned an empty response.")
            return text
        except requests.exceptions.Timeout:
            raise GroqAgentError(
                f"Groq request timed out after {self.timeout} s."
            )
        except requests.exceptions.HTTPError as exc:
            detail = ""
            try:
                payload = exc.response.json()
                detail = (
                    payload.get("error", {}).get("message")
                    or payload.get("error")
                    or ""
                )
            except Exception:
                detail = ""
            if detail:
                raise GroqAgentError(f"Groq HTTP error: {detail}")
            raise GroqAgentError(f"Groq HTTP error: {exc}")
        except requests.exceptions.RequestException as exc:
            raise GroqAgentError(f"Groq request failed: {exc}")
