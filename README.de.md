# KirOS

[English](README.md) | **Deutsch**

KirOS ist eine universelle Agenten-CLI und ein festes Modul von KiraBridge. Es ist kein sechstes Produkt: Es wird mit dem Desktop-Installer von KiraBridge ausgeliefert und mit aktualisiert (auf Servern nicht nötig).

> Stand: Erste S2/S3-Implementierung in Arbeit. CLI und Mock-Tests entstehen; der Live-Aufruf mit einem kostenlosen Modell ist ein eigener Abnahmeschritt.

## Richtung (beschlossen am 26. November 2026)

- Zuerst eine klassische CLI im Terminal: Prompteingabe, direkte OpenRouter- und DeepSeek-API-Anbindung (DeepSeek zunächst über das OpenRouter-Guthaben), Modellauswahl, Agentenfunktionen (Dateien, Befehle, mehrstufige Aufgaben).
- API-Schlüssel kommen aus 4AllPass (mit Freigabe des Nutzers); Budgets je Schlüssel über TollGate.
- Native MCP- und ACP-Schnittstellen, Rollenverwaltung, Nachrichtenkanal und Completion-Hooks, damit KirOS neben Codex, Claude und Qwen Worker oder Koordinator sein kann.
- Erst danach: grafische Integration in die gemeinsame Family-App (Tabs, Sidebars, Medienvorschau).

## CLI-Vorschau

Die erste Implementierung ergänzt einen Einzelprompt-Befehl und eine REPL im Arbeitsspeicher:

```sh
uv sync --locked
uv run kiros
uv run kiros "Erkläre diesen Fehler"
uv run kiros models
uv run kiros key status
uv run kiros --model nvidia/nemotron-3-ultra-550b-a55b:free "Fasse diesen Text zusammen"
uv run kiros --model deepseek/deepseek-v4.1-flash --allow-paid --max-cost 0.10 "Erkläre diesen Fehler"
```

Die REPL unterstützt `/model [ID]`, `/cost`, `/new` und `/quit`. Sie nutzt den gepinnten KiraBridge-OpenRouter-Adapter und die geschlossene Modellliste. Standard sind kostenlose Modelle; bezahlte Nutzung braucht sowohl `--allow-paid` als auch eine positive Sitzungsobergrenze mit `--max-cost`. `kiros key status` zeigt nur die Verfügbarkeit; Schlüsselwerte erscheinen weder als Kommandozeilenargument noch in der Ausgabe. Dies beschreibt den Quellstand, kein KiraBridge-Release oder bereits installiertes CLI.

Die Planung liegt in ThreadDesk (Thread „KirOS Arbeiten“), übergeordnete Entscheidungen im Big Plan. Dieses Repository enthält nur Code, Tests und Install-/Release-Dokumentation.

## Lizenz

Netzwerkpunkt Personal Use License 1.0 (siehe `LICENSE`).
