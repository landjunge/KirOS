from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
from kirabridge.kiros_api import OpenRouterAdapter

from kiros.provider import DEFAULT_MODEL, KirosError, execute_prompt, validate_model
from kiros.session import Session


@pytest.fixture
def keychain_stub(monkeypatch):
    monkeypatch.setattr(
        "kirabridge.agent_manager.openrouter._credential", lambda _config: "synthetic-test-key"
    )


def test_model_allowlist_and_paid_gate():
    assert not validate_model(DEFAULT_MODEL, allow_paid=False, max_cost=Decimal("0"))
    with pytest.raises(KirosError, match="freigegeben"):
        validate_model("vendor/unlisted:free", allow_paid=False, max_cost=Decimal("0"))
    with pytest.raises(KirosError, match="--allow-paid"):
        validate_model("deepseek/deepseek-v4.1-flash", allow_paid=False, max_cost=Decimal("1"))
    with pytest.raises(KirosError, match="positives --max-cost"):
        validate_model("deepseek/deepseek-v4.1-flash", allow_paid=True, max_cost=Decimal("0"))


async def test_free_request_uses_pinned_model_and_never_returns_secret(keychain_stub):
    observed = {}

    def handler(request):
        observed["body"] = json.loads(request.content)
        observed["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "id": "synthetic-request",
                "model": DEFAULT_MODEL,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "synthetic answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 3, "cost": 0},
            },
        )

    def client_factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    result = await execute_prompt(
        "a synthetic prompt",
        model=DEFAULT_MODEL,
        allow_paid=False,
        remaining_budget=Decimal("0"),
        adapter_factory=lambda: OpenRouterAdapter(client_factory=client_factory),
    )

    assert result.success is True
    assert result.text == "synthetic answer"
    assert observed["body"]["models"] == [DEFAULT_MODEL]
    assert observed["body"]["messages"] == [{"role": "user", "content": "a synthetic prompt"}]
    assert "tools" not in observed["body"]
    assert observed["authorization"] == "Bearer synthetic-test-key"
    assert result.reported_cost_usd == Decimal("0")
    assert "synthetic-test-key" not in repr(result)


async def test_paid_turn_receives_remaining_hard_ceiling():
    observed = {}

    class Adapter:
        async def execute(self, _task, _args, config, _roots, _running, _progress):
            observed["cap"] = config.openrouter_paid_max_cost_usd
            return {
                "success": True,
                "text": "paid mock",
                "evidence": {
                    "selected_model": "deepseek/deepseek-v4.1-flash",
                    "reported_cost_usd": "0.002",
                    "paid_cost_upper_bound_usd": "0.01",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                },
            }

    result = await execute_prompt(
        "prompt",
        model="deepseek/deepseek-v4.1-flash",
        allow_paid=True,
        remaining_budget=Decimal("0.02"),
        adapter_factory=Adapter,
    )
    assert observed["cap"] == Decimal("0.02")
    assert result.reserved_cost_usd == Decimal("0.01")
    assert result.reported_cost_usd == Decimal("0.002")


async def test_provider_exception_text_never_reaches_cli_error():
    class Adapter:
        async def execute(self, *_args):
            raise RuntimeError("synthetic-secret-value provider response")

    with pytest.raises(KirosError) as exc:
        await execute_prompt(
            "prompt",
            model=DEFAULT_MODEL,
            allow_paid=False,
            remaining_budget=Decimal("0"),
            adapter_factory=Adapter,
        )
    assert "synthetic-secret-value" not in str(exc.value)


def test_session_cap_is_not_reset_by_new_conversation():
    session = Session(model=DEFAULT_MODEL, max_cost=Decimal("0.10"), allow_paid=True)
    session.reserved_cost_usd = Decimal("0.08")
    session.reset_conversation()
    assert session.remaining_budget == Decimal("0.02")


def test_unknown_paid_outcome_consumes_remaining_ceiling():
    session = Session(model="deepseek/deepseek-v4.1-flash", max_cost=Decimal("0.10"))
    session.reserved_cost_usd = Decimal("0.03")
    session.reserve_unknown_paid_attempt()
    assert session.remaining_budget == Decimal("0")
