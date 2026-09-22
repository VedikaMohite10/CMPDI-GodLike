"""ModelGateway — single internal interface for all LLM and embedding calls.

Every Phase 3 service calls this module instead of hitting Ollama directly.
Benefits:
  - Swapping a model later requires only changing config, not calling code.
  - Centralised retry logic and JSON schema validation.
  - Two named model roles: 'intent' (7b, constrained JSON) and 'synthesis' (14b, NL answers).
  - Embedding always uses bge-m3 (same as Phases 1–2).

Design note: the async HTTP client is instantiated per-call to keep this module
stateless and compatible with FastAPI's async request lifecycle.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class ModelGatewayError(Exception):
    """Raised when the gateway cannot produce a valid response after retries."""


async def generate(
    prompt: str,
    *,
    role: str = "synthesis",
    system: Optional[str] = None,
    json_schema: Optional[Dict[str, Any]] = None,
    max_retries: int | None = None,
) -> str | Dict[str, Any]:
    """Generate a text or JSON response from the appropriate LLM.

    Args:
        prompt:       The user-turn message to send.
        role:         'intent' → INTENT_LLM_MODEL (7b, fast, for structured JSON plans)
                      'synthesis' → SYNTHESIS_LLM_MODEL (14b, for NL answer generation)
        system:       Optional system prompt. Callers should always provide one.
        json_schema:  If provided, the response is validated against this JSON Schema dict.
                      On validation failure the call is retried (up to max_retries times).
                      Returns a dict on success, str otherwise.
        max_retries:  Defaults to QUERY_PLANNER_MAX_RETRIES from config.

    Returns:
        str if json_schema is None, else dict if parsing succeeds.

    Raises:
        ModelGatewayError: if all retries fail or Ollama is unreachable.
    """
    model = _model_for_role(role)
    retries = max_retries if max_retries is not None else settings.QUERY_PLANNER_MAX_RETRIES

    last_exc: Exception | None = None
    last_text: str = ""

    for attempt in range(retries + 1):
        try:
            raw = await _chat(model=model, system=system, user=prompt)
            if json_schema is None:
                return raw

            # Try to parse + validate JSON
            parsed = _extract_json(raw)
            _validate_schema(parsed, json_schema)
            return parsed

        except (json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            last_text = raw if 'raw' in dir() else ""
            if attempt < retries:
                logger.warning(
                    "ModelGateway: JSON validation failed on attempt %d/%d (role=%s): %s",
                    attempt + 1, retries + 1, role, exc,
                )
                # Append correction guidance to the prompt for next attempt
                prompt = _correction_prompt(prompt, last_text, str(exc))
                continue
            break

        except httpx.HTTPError as exc:
            raise ModelGatewayError(f"Ollama HTTP error (model={model}): {exc}") from exc

    raise ModelGatewayError(
        f"Could not get valid JSON from {model} after {retries + 1} attempts. "
        f"Last error: {last_exc}. Last output: {last_text[:200]!r}"
    )


async def embed(text: str) -> List[float]:
    """Embed a string using bge-m3. Delegates to the existing ollama_client for compatibility."""
    from app.services import ollama_client
    return await ollama_client.embed_text(text)


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple strings sequentially using bge-m3."""
    from app.services import ollama_client
    return await ollama_client.embed_batch(texts)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _model_for_role(role: str) -> str:
    if role == "intent":
        return settings.INTENT_LLM_MODEL
    elif role == "synthesis":
        return settings.SYNTHESIS_LLM_MODEL
    else:
        raise ValueError(f"Unknown model role: {role!r}. Expected 'intent' or 'synthesis'.")


async def _chat(model: str, system: Optional[str], user: str) -> str:
    """Make a single Ollama /api/chat call. Returns the assistant content string."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    payload = {
        "model": model,
        "stream": False,
        "messages": messages,
        "options": {
            "temperature": 0,       # deterministic for intent/planning
            "num_predict": 4096,    # generous limit for synthesis
        },
    }

    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    logger.debug("ModelGateway → %s (message len=%d chars)", model, len(user))

    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


def _extract_json(text: str) -> Any:
    """Extract JSON from a raw LLM response, handling code-fence wrappers."""
    text = text.strip()

    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = inner.strip()

    # Find the first { or [ and parse from there
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        idx = text.find(start_char)
        if idx != -1:
            # Find matching close
            candidate = text[idx:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass  # try next strategy

    # Last resort: parse the whole stripped text
    return json.loads(text)


def _validate_schema(data: Any, schema: Dict[str, Any]) -> None:
    """Minimal JSON schema validation — checks required keys and enum values.

    We intentionally avoid pulling in `jsonschema` as a hard dependency (keeps
    the CPU-only install lighter). This validator covers the specific constraints
    we need for the query plan schema.

    Raises:
        ValueError: if validation fails, with a descriptive message.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    required = schema.get("required", [])
    for key in required:
        if key not in data:
            raise ValueError(f"Required field missing from LLM output: '{key}'")

    props = schema.get("properties", {})
    for key, prop_schema in props.items():
        if key not in data:
            continue
        val = data[key]

        # Enum check
        if "enum" in prop_schema and val not in prop_schema["enum"]:
            raise ValueError(
                f"Field '{key}' value {val!r} not in allowed enum {prop_schema['enum']}"
            )

        # Type check (simple)
        type_map = {"string": str, "integer": int, "number": (int, float),
                    "boolean": bool, "array": list, "object": dict}
        if "type" in prop_schema:
            expected = type_map.get(prop_schema["type"])
            if expected and not isinstance(val, expected):
                raise ValueError(
                    f"Field '{key}' expected type {prop_schema['type']}, got {type(val).__name__}"
                )


def _correction_prompt(original_prompt: str, bad_output: str, error: str) -> str:
    """Append a correction instruction to the prompt for a retry attempt."""
    return (
        f"{original_prompt}\n\n"
        f"[CORRECTION REQUIRED]\n"
        f"Your previous response could not be parsed as valid JSON. Error: {error}\n"
        f"Your previous response was: {bad_output[:300]!r}\n"
        f"Respond ONLY with valid JSON conforming to the schema above. "
        f"No explanation, no code fences, no extra text."
    )
