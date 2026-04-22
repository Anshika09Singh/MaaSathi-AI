import os
from typing import Optional

import requests


class OllamaAgentError(RuntimeError):
    """Raised when Ollama is reachable but cannot serve a generation request."""


class OllamaNotReadyError(OllamaAgentError):
    """Raised when Ollama is online but no usable model is available."""


class OllamaAgent:
    """
    Talks to a locally running Ollama server.
    Default model: llama2  (change via OLLAMA_MODEL env var)
    Default base:  http://127.0.0.1:11434
    """

    def __init__(
        self,
        model: Optional[str] = None,
        endpoint: str = "http://127.0.0.1:11434",
    ):
        self.model = model or os.environ.get("OLLAMA_MODEL", "phi3:latest")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
        self._preferred_models = [
            self.model,
            os.environ.get("OLLAMA_MODEL"),
            "phi3:latest",
            "phi3",
            "llama3.2",
            "llama3.1",
            "llama3",
            "mistral",
            "gemma2",
            "llama2",
        ]

    def _ordered_available_models(self) -> list[str]:
        """Return installed models ordered by local preference."""
        available = self.list_models()
        if not available:
            raise OllamaNotReadyError(
                "Ollama is running but no local model is installed. Run: ollama pull phi3"
            )

        preferred = []
        normalized = {name.lower(): name for name in available}
        seen = set()

        for name in [item for item in self._preferred_models if item]:
            resolved = normalized.get(name.lower())
            if resolved and resolved.lower() not in seen:
                preferred.append(resolved)
                seen.add(resolved.lower())

        for name in available:
            if name.lower() not in seen:
                preferred.append(name)
                seen.add(name.lower())

        return preferred

    def list_models(self) -> list[str]:
        """Return the locally installed Ollama model names."""
        url = f"{self.endpoint}/api/tags"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for item in data.get("models", []):
                name = (item.get("name") or "").strip()
                if name:
                    models.append(name)
            return models
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Ollama is not running. Start it with: ollama serve")
        except requests.exceptions.Timeout:
            raise RuntimeError("Ollama health check timed out.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama health check failed: {e}")

    def resolve_model(self) -> str:
        """Pick a model that actually exists in the local Ollama registry."""
        resolved = self._ordered_available_models()[0]
        self.model = resolved
        return resolved

    def status(self) -> dict:
        """Expose Ollama readiness information for the API/UI."""
        try:
            models = self.list_models()
            active_model = None
            if models:
                active_model = self.resolve_model()
            return {
                "online": True,
                "ready": bool(models),
                "models": models,
                "active_model": active_model,
                "message": (
                    f"Ready with model {active_model}."
                    if active_model
                    else "Ollama is online, but no local model is installed yet."
                ),
            }
        except RuntimeError as exc:
            return {
                "online": False,
                "ready": False,
                "models": [],
                "active_model": None,
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 256) -> str:
        """
        Send a prompt to Ollama and return the text response.
        Raises RuntimeError on failure so RAGAssistant can fall back.
        """
        url = f"{self.endpoint}/api/generate"
        memory_errors = []
        for candidate in self._ordered_available_models():
            payload = {
                "model": candidate,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "").strip()
                if not text:
                    raise RuntimeError("Ollama returned an empty response.")
                self.model = candidate
                return text
            except requests.exceptions.ConnectionError:
                raise RuntimeError("Ollama is not running. Start it with: ollama serve")
            except requests.exceptions.Timeout:
                raise OllamaAgentError(
                    f"Ollama request timed out after {self.timeout} s. "
                    "The model is installed, but your machine needs more time to generate a reply."
                )
            except requests.exceptions.HTTPError as e:
                detail = ""
                try:
                    detail = e.response.json().get("error", "").strip()
                except Exception:
                    detail = ""
                if "requires more system memory" in detail.lower():
                    memory_errors.append(f"{candidate}: {detail}")
                    continue
                if detail:
                    raise OllamaAgentError(f"Ollama HTTP error: {detail}")
                raise RuntimeError(f"Ollama HTTP error: {e}")

        if memory_errors:
            raise OllamaAgentError(
                "All installed Ollama models exceeded available memory. " + " | ".join(memory_errors)
            )
        raise OllamaAgentError("Ollama could not find a usable installed model.")
