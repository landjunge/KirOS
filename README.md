# KirOS

**English** | [Deutsch](README.de.md)

KirOS is a universal agent CLI and a fixed module of KiraBridge. It is not a sixth product: it ships with the desktop KiraBridge installer and is updated with it (not needed on servers).

> Status: planning. Nothing is implemented yet. This repository was created on 26 November 2026 to hold KirOS' own codebase and tests.

## Direction (decided 26 November 2026)

- First a classic CLI in the terminal: prompt input, direct OpenRouter and DeepSeek API access (DeepSeek first through the OpenRouter balance), model selection, agent functions (files, commands, multi-step tasks).
- API keys come from 4AllPass (with the user's approval); budgets per key come from TollGate.
- Native MCP and ACP interfaces, role management, message channel and completion hooks, so KirOS can be a worker or the coordinator next to Codex, Claude and Qwen.
- Only afterwards: a graphical integration in the shared Family app (tabs, sidebars, media preview).

Planning lives in ThreadDesk (thread "KirOS Arbeiten"), overarching decisions in the Big Plan. This repository contains code, tests and install/release documentation only.

## License

Netzwerkpunkt Personal Use License 1.0 (see `LICENSE`).
