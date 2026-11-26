# KirOS

[English](README.md) | **Deutsch**

KirOS ist eine universelle Agenten-CLI und ein festes Modul von KiraBridge. Es ist kein sechstes Produkt: Es wird mit dem Desktop-Installer von KiraBridge ausgeliefert und mit aktualisiert (auf Servern nicht nötig).

> Stand: Planung. Noch nichts ist umgesetzt. Dieses Repository wurde am 26. November 2026 angelegt, damit KirOS eine eigene Codebasis und eigene Tests bekommt.

## Richtung (beschlossen am 26. November 2026)

- Zuerst eine klassische CLI im Terminal: Prompteingabe, direkte OpenRouter- und DeepSeek-API-Anbindung (DeepSeek zunächst über das OpenRouter-Guthaben), Modellauswahl, Agentenfunktionen (Dateien, Befehle, mehrstufige Aufgaben).
- API-Schlüssel kommen aus 4AllPass (mit Freigabe des Nutzers); Budgets je Schlüssel über TollGate.
- Native MCP- und ACP-Schnittstellen, Rollenverwaltung, Nachrichtenkanal und Completion-Hooks, damit KirOS neben Codex, Claude und Qwen Worker oder Koordinator sein kann.
- Erst danach: grafische Integration in die gemeinsame Family-App (Tabs, Sidebars, Medienvorschau).

Die Planung liegt in ThreadDesk (Thread „KirOS Arbeiten“), übergeordnete Entscheidungen im Big Plan. Dieses Repository enthält nur Code, Tests und Install-/Release-Dokumentation.

## Lizenz

Netzwerkpunkt Personal Use License 1.0 (siehe `LICENSE`).
