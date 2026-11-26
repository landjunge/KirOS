"""Command line entry point for KirOS S2/S3."""

from __future__ import annotations

import argparse
import asyncio
import sys
from decimal import Decimal, InvalidOperation

from kirabridge.kiros_api import OPENROUTER_FREE_MODELS, OPENROUTER_PAID_MODELS

from kiros.provider import (
    DEFAULT_MODEL,
    KirosError,
    execute_prompt,
    key_available,
    validate_model,
)
from kiros.session import Session


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiros", description="KiraBridge OpenRouter CLI")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Pinned model ID")
    parser.add_argument(
        "--max-cost",
        type=_cost,
        default=Decimal("0"),
        help="Per-process cost ceiling in USD (default: 0)",
    )
    parser.add_argument("--allow-paid", action="store_true", help="Allow the listed paid model")
    parser.add_argument("prompt", nargs="*", help="Prompt; omit for an interactive session")
    return parser


def _cost(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError("--max-cost must be a decimal USD amount") from None
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("1000000"):
        raise argparse.ArgumentTypeError("--max-cost must be between 0 and 1000000 USD")
    return parsed


def _print_models() -> None:
    print("Kostenlos:")
    for model in sorted(OPENROUTER_FREE_MODELS):
        print(f"  {model}")
    print("Bezahlt (nur mit --allow-paid und --max-cost):")
    for model in sorted(OPENROUTER_PAID_MODELS):
        print(f"  {model}")


def _cost_status(session: Session) -> str:
    actual = f"${session.reported_cost_usd:.6f} USD" if session.reported_cost_known else "unbekannt"
    return (
        f"Gemeldete Kosten: {actual} · Budgetobergrenze: ${session.max_cost:.6f} USD · "
        f"verbleibend: ${session.remaining_budget:.6f} USD"
    )


def _footer(session: Session, result) -> str:
    tokens = (
        f"Prompt {result.prompt_tokens} + Antwort {result.completion_tokens} Tokens"
        if result.prompt_tokens is not None and result.completion_tokens is not None
        else "Tokens unbekannt"
    )
    if result.reported_cost_usd is None:
        cost = "Kosten unbekannt"
    else:
        cost = f"${result.reported_cost_usd:.6f} USD"
    remaining = f" · Budget übrig ${session.remaining_budget:.6f} USD" if session.max_cost else ""
    return f"{result.model} · {tokens} · {cost}{remaining}"


async def _send(session: Session, text: str) -> bool:
    try:
        validate_model(
            session.model, allow_paid=session.allow_paid, max_cost=session.remaining_budget
        )
        prompt = session.prompt_for(text)
        result = await execute_prompt(
            prompt,
            model=session.model,
            allow_paid=session.allow_paid,
            remaining_budget=session.remaining_budget,
        )
    except KirosError as exc:
        if session.model not in OPENROUTER_FREE_MODELS and session.allow_paid:
            session.reserve_unknown_paid_attempt()
        print(str(exc), file=sys.stderr)
        return False
    except Exception:
        # An unclassified provider error may follow a transmitted request. Fail
        # closed for paid use and do not expose raw exception/provider details.
        if session.model not in OPENROUTER_FREE_MODELS and session.allow_paid:
            session.reserve_unknown_paid_attempt()
        print("Anfrage fehlgeschlagen; Ergebnis nicht bestätigt.", file=sys.stderr)
        return False

    session.record(text, result)
    print(result.text)
    if not result.success:
        print("Antwort ist unvollständig.", file=sys.stderr)
    print(_footer(session, result))
    return result.success


def _select_model(session: Session, value: str) -> None:
    validate_model(value, allow_paid=session.allow_paid, max_cost=session.remaining_budget)
    session.model = value


async def _repl(session: Session) -> int:
    while True:
        try:
            line = (await asyncio.to_thread(input, "kiros> ")).strip()
        except EOFError:
            print()
            return 0
        if not line:
            continue
        command, _, argument = line.partition(" ")
        if command == "/quit":
            return 0
        if command == "/cost":
            print(_cost_status(session))
            continue
        if command == "/new":
            session.reset_conversation()
            print("Gesprächskontext gelöscht; Sitzungsbudget bleibt bestehen.")
            continue
        if command == "/model":
            if not argument:
                print(session.model)
                continue
            try:
                _select_model(session, argument.strip())
            except KirosError as exc:
                print(str(exc), file=sys.stderr)
                continue
            print(f"Modell: {session.model}")
            continue
        if command.startswith("/"):
            print("Befehle: /model [ID], /cost, /new, /quit", file=sys.stderr)
            continue
        await _send(session, line)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["models"]:
        _print_models()
        return 0
    if args == ["key", "status"]:
        try:
            present = key_available()
        except Exception:
            present = False
        print("OpenRouter-Schlüssel: " + ("vorhanden" if present else "nicht verfügbar"))
        return 0

    parsed = _parser().parse_args(args)
    session = Session(
        model=parsed.model,
        max_cost=parsed.max_cost,
        allow_paid=parsed.allow_paid,
    )
    try:
        validate_model(
            session.model, allow_paid=session.allow_paid, max_cost=session.remaining_budget
        )
    except KirosError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if parsed.allow_paid and parsed.max_cost <= 0:
        print("--allow-paid erfordert ein positives --max-cost.", file=sys.stderr)
        return 2
    if parsed.prompt:
        return 0 if asyncio.run(_send(session, " ".join(parsed.prompt))) else 2
    return asyncio.run(_repl(session))


if __name__ == "__main__":
    raise SystemExit(main())
