from __future__ import annotations

from decimal import Decimal

import pytest

from kiros.cli import main


def test_models_lists_only_closed_free_and_paid_routes(capsys):
    assert main(["models"]) == 0
    out = capsys.readouterr().out
    assert "nvidia/nemotron-3-ultra-550b-a55b:free" in out
    assert "deepseek/deepseek-v4.1-flash" in out
    assert "Kostenlos:" in out and "Bezahlt" in out


def test_key_status_reports_presence_only(monkeypatch, capsys):
    monkeypatch.setattr("kiros.cli.key_available", lambda: True)
    assert main(["key", "status"]) == 0
    out = capsys.readouterr().out
    assert out.strip() == "OpenRouter-Schlüssel: vorhanden"
    assert "sk-" not in out and "Bearer" not in out


def test_key_status_never_prints_secret_even_if_checker_raises(monkeypatch, capsys):
    def fail():
        raise RuntimeError("synthetic-secret-value")

    monkeypatch.setattr("kiros.cli.key_available", fail)
    assert main(["key", "status"]) == 0
    out = capsys.readouterr().out
    assert out.strip() == "OpenRouter-Schlüssel: nicht verfügbar"
    assert "synthetic-secret-value" not in out


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--model", "unknown/model", "prompt"], 2),
        (["--model", "deepseek/deepseek-v4.1-flash", "prompt"], 2),
        (["--allow-paid", "--model", "deepseek/deepseek-v4.1-flash", "prompt"], 2),
    ],
)
def test_paid_and_unknown_routes_fail_closed(argv, expected, capsys):
    assert main(argv) == expected
    assert "Schlüssel" not in capsys.readouterr().err


def test_secret_is_not_an_cli_option():
    # There is intentionally no CLI key argument; secrets are loaded by the
    # KiraBridge adapter from its configured local credential stores.
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_repl_commands_keep_budget_across_new(monkeypatch, capsys):
    import builtins

    from kiros import cli

    lines = iter(
        [
            "/model",
            "/model deepseek/deepseek-v4.1-flash",
            "/new",
            "/cost",
            "hello",
            "/quit",
        ]
    )
    seen = []

    def fake_input(_prompt):
        return next(lines)

    async def fake_send(session, text):
        seen.append((session.model, session.remaining_budget, text))
        return True

    monkeypatch.setattr(builtins, "input", fake_input)
    monkeypatch.setattr(cli, "_send", fake_send)
    assert main(["--allow-paid", "--max-cost", "0.10"]) == 0
    out = capsys.readouterr().out
    assert "Gesprächskontext gelöscht; Sitzungsbudget bleibt bestehen." in out
    assert "Budgetobergrenze: $0.100000 USD" in out
    assert seen == [("deepseek/deepseek-v4.1-flash", Decimal("0.10"), "hello")]
