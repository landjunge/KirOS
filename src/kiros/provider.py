"""Small caller-side bridge to the supported KiraBridge KirOS facade."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kirabridge.kiros_api import (
    OPENROUTER_FREE_MODELS,
    OPENROUTER_PAID_MODELS,
    OpenRouterAdapter,
    credential_status,
)

DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MAX_PROMPT_BYTES = 262_144
MAX_OUTPUT_TOKENS = 1024


class KirosError(Exception):
    """A safe-to-display CLI error without provider payloads or credentials."""


@dataclass(frozen=True)
class TurnResult:
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    reported_cost_usd: Decimal | None
    reserved_cost_usd: Decimal
    success: bool


def validate_model(model: str, *, allow_paid: bool, max_cost: Decimal) -> bool:
    if model in OPENROUTER_FREE_MODELS:
        return False
    if model not in OPENROUTER_PAID_MODELS:
        raise KirosError("Modell ist nicht in der freigegebenen KirOS-Modellliste.")
    if not allow_paid:
        raise KirosError("Bezahlte Modelle erfordern --allow-paid.")
    if max_cost <= 0:
        raise KirosError("Bezahlte Modelle erfordern ein positives --max-cost.")
    return True


def key_available() -> bool:
    try:
        return bool(credential_status())
    except Exception:
        return False


async def execute_prompt(
    prompt: str,
    *,
    model: str,
    allow_paid: bool,
    remaining_budget: Decimal,
    adapter_factory=OpenRouterAdapter,
) -> TurnResult:
    paid = validate_model(model, allow_paid=allow_paid, max_cost=remaining_budget)
    if not prompt.strip():
        raise KirosError("Prompt darf nicht leer sein.")
    if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise KirosError("Prompt überschreitet das Größenlimit von 256 KiB.")

    config = SimpleNamespace(
        model=model,
        openrouter_fallback_models=[],
        openrouter_max_prompt_bytes=MAX_PROMPT_BYTES,
        openrouter_max_output_tokens=MAX_OUTPUT_TOKENS,
        openrouter_max_turns=1,
        openrouter_max_tool_calls=1,
        openrouter_max_tool_result_bytes=32768,
        openrouter_allow_paid=paid,
        openrouter_paid_max_prompt_bytes=MAX_PROMPT_BYTES if paid else None,
        openrouter_paid_max_output_tokens=MAX_OUTPUT_TOKENS if paid else None,
        openrouter_paid_max_cost_usd=remaining_budget if paid else None,
        openrouter_credential_source="macos_keychain",
        api_key_env="OPENROUTER_API_KEY",
        openrouter_mcp_tools=[],
        openrouter_mcp_operations=[],
        openrouter_mcp_read_roots=[],
    )
    args = SimpleNamespace(
        agent="kiros",
        prompt=prompt,
        timeout=120,
        cwd=str(Path.cwd()),
        mcp_grants=[],
        mcp_operations=[],
        mcp_read_roots=[],
    )

    async def no_op(_event: dict[str, Any]) -> None:
        return None

    try:
        adapter = adapter_factory()
        result = await adapter.execute({}, args, config, [], no_op, no_op)
    except Exception as exc:
        code = getattr(exc, "code", None)
        # Never display exception text: provider and credential errors can carry
        # untrusted response details. KiraBridge's stable error code is bounded.
        if isinstance(code, str) and code.replace("_", "").isalnum():
            raise KirosError(f"Anfrage fehlgeschlagen ({code}).") from None
        raise KirosError("Anfrage fehlgeschlagen; Ergebnis nicht bestätigt.") from None

    if not isinstance(result, dict) or not isinstance(result.get("evidence"), dict):
        raise KirosError("Provider-Antwort konnte nicht bestätigt werden.")
    evidence = result["evidence"]
    text = result.get("text")
    if not isinstance(text, str) or not text.strip():
        raise KirosError("Provider hat keine Textantwort geliefert.")
    reported_cost = _decimal_or_none(evidence.get("reported_cost_usd"))
    reserved_value = _decimal_or_none(evidence.get("paid_cost_upper_bound_usd"))
    reserved = (
        remaining_budget if paid and reserved_value is None else reserved_value or Decimal("0")
    )
    return TurnResult(
        text=text,
        model=str(evidence.get("selected_model") or model),
        prompt_tokens=_token_or_none(evidence.get("prompt_tokens")),
        completion_tokens=_token_or_none(evidence.get("completion_tokens")),
        reported_cost_usd=reported_cost,
        reserved_cost_usd=reserved,
        success=result.get("success") is True,
    )


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def _token_or_none(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None
