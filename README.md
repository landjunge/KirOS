# KirOS

**English** | [Deutsch](README.de.md)

KirOS is a universal agent CLI and a fixed module of KiraBridge. It is not a sixth product: it ships with the desktop KiraBridge installer and is updated with it (not needed on servers).

> Status: S2/S3 first implementation in progress. The CLI and mock tests are being added; the free-model live check is a separate acceptance step.

## Direction (decided 26 November 2026)

- First a classic CLI in the terminal: prompt input, direct OpenRouter and DeepSeek API access (DeepSeek first through the OpenRouter balance), model selection, agent functions (files, commands, multi-step tasks).
- API keys come from 4AllPass (with the user's approval); budgets per key come from TollGate.
- Native MCP and ACP interfaces, role management, message channel and completion hooks, so KirOS can be a worker or the coordinator next to Codex, Claude and Qwen.
- Only afterwards: a graphical integration in the shared Family app (tabs, sidebars, media preview).

## CLI preview

The first implementation adds a single-prompt command and an in-memory REPL:

```sh
uv sync --locked
uv run kiros
uv run kiros "Explain this error"
uv run kiros models
uv run kiros key status
uv run kiros --model nvidia/nemotron-3-ultra-550b-a55b:free "Summarize this text"
uv run kiros --model deepseek/deepseek-v4.1-flash --allow-paid --max-cost 0.10 "Explain this error"
```

The REPL supports `/model [ID]`, `/cost`, `/new`, and `/quit`. It uses the pinned KiraBridge OpenRouter adapter and closed model list. Free models are the default; paid use requires both `--allow-paid` and a positive `--max-cost` session ceiling. `kiros key status` reports availability only; key values are never command-line arguments or printed. This is source status, not a KiraBridge release or installed CLI.

Planning lives in ThreadDesk (thread "KirOS Arbeiten"), overarching decisions in the Big Plan. This repository contains code, tests and install/release documentation only.

## License

Netzwerkpunkt Personal Use License 1.0 (see `LICENSE`).
