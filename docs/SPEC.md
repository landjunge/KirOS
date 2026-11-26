# KirOS — Spezifikation (v0.2, 26.11.2026)

Status: Entwurf, Entscheidungen des Koordinators eingearbeitet. Grundlage: `KirOS/README.md` (angelegt 26.11.2026, „Status: planning") und gelesener KiraBridge-Code. BELEGT = aus Datei belegt (Dateiname genannt); VORSCHLAG = noch zu bestätigen.

## 1 Ziel und Nicht-Ziele

**Ziel (BELEGT: README; Beschluss 26.11.2026):**
- Universelle Agenten-CLI in Python; festes Modul von KiraBridge, kein sechstes Produkt.
- Erste Ausbaustufe: Prompteingabe im Terminal, direkte OpenRouter-/DeepSeek-Anbindung (DeepSeek zunächst über OpenRouter), Modellauswahl.
- Danach Koordinatorfunktionen: Rolle, Nachrichtenkanal, Completion-Hook, MCP, ACP.

**Nicht-Ziele:**
- Keine grafische Oberfläche am Anfang (später Integration in die Family-App; BELEGT README).
- Kein eigener Daemon und keine eigenen Releases unabhängig von KiraBridge.
- Keine Anbindung weiterer Fremd-CLIs, solange ACP-/MCP-Steuerung nicht nachweislich zuverlässig ist (Beschluss 26.11.).
- Kein eigenes Budgetsystem statt TollGate.

## 2 Architektur

**BELEGT — KiraBridge besitzt bereits fast alles:**
- `src/kirabridge/agent_manager/openrouter.py`: kompletter OpenRouter-Client (`OpenRouterAdapter`) mit geschlossener Modelliste, Kostenobergrenze, Tool-Umschlag über task-bezogenen stdio-MCP-Proxy, Fehler-/Nachweisfeldern.
- `src/kirabridge/agent_manager/openrouter_credentials.py`: Keychain-Dienst `KiraBridge.OpenRouter` + Rückfall auf OpenCode-`auth.json`.
- `src/kirabridge/openrouter_models.py`: pinnte Modell- und Preisliste.
- `src/kirabridge/agent_manager/acp.py`: ACP-v1-stdio-Client (eine Sitzung, bounded, kein Auto-Retry).
- `src/kirabridge/completion_handoff.py`: Completion-Hook mit Rücklese-Bestätigung und Secret-Filter.

**VORSCHLAG — Paketabhängigkeit, keine Kopie:**
- KirOS hängt das `kirabridge`-Paket an (Installations-/Lockfile-Abhängigkeit) und importiert darüber Provider, Credentials, ACP und Hook. Begründung: Kosten- und Fehlersemantik ist dort schon getestet; eine Kopie würde bei KiraBridge-Änderungen still abdriften.
- KirOS-eigene Dünnschicht: `kiros/cli.py` (Ein-/Mehrplatz-Sitzung), `kiros/config.py`, `kiros/keys.py` (4AllPass-Broker), `kiros/budget.py` (Obergrenzen bis TollGate bereitsteht), `kiros/coordinator.py` (ab K1).
- Falls KiraBridge-Importe (Module unter `agent_manager/`) noch nicht als stabil gelten: nur `openrouter_models.py`-Daten und eine schmale Adapter-Fassade referenzieren, nicht den Client duplizieren. Entscheidung offen (siehe 8).

## 3 CLI-Bedienung (VORSCHLAG)

```
kiros "prompt"                # Einzelprompt, Antwort auf stdout
kiros                         # interaktive Sitzung (REPL)
kiros --model nvidia/nemotron-3-ultra-550b-a55b:free --timeout 120 "…"
kiros --max-cost 0.10 --allow-paid --model deepseek/deepseek-v4.1-flash "…"
kiros key status              # nur Verfügbarkeit, niemals der Wert
kiros models                  # geschlossene Liste, als free/paid markiert
```
REPL-Kommandos: `/model <id>`, `/cost`, `/tools on|off`, `/new`, `/quit`.
Beispielsitzung: Prompt → Antwort → Fußzeile `Modell · Prompt-/Completion-Tokens · Kosten USD · Rest Budget`.
Kein Secret in Argumenten, Umgebungsvariablen von Kindprozessen oder Verlaufsdatei (zu prüfen: Shell-History, siehe 6).

## 4 Konfiguration und Schluesselbezug

**BELEGT — Übergangspfad existiert schon** (`openrouter_credentials.py`):
- Bevorzugt Keychain-Item `KiraBridge.OpenRouter` / Account `openrouter` über `/usr/bin/security`; danach OpenCode `~/.local/share/opencode/auth.json` mit strengen Dateiprüfungen (reguläre Datei, Eigentümer, keine Gruppen-/Other-Rechte, ≤1 MiB); Import über versteckte TTY-Abfrage, ohne dass der Wert diesen Prozess durchläuft (`import_from_hidden_tty`); Status nur alsbool (`credential_status`).

**Ziel (Beschluss 26.11.):**
- Erste Quelle: 4AllPass-Loopback-Broker mit ausdrücklicher Nutzerfreigabe; überträgt nur `raw_secret` in den Speicher; Wert nie in Log, Chat oder Befehlszeile.
- Reihenfolge VORSCHLAG: 4AllPass → Keychain `KiraBridge.OpenRouter` → OpenCode `auth.json` → Umgebungsvariable (nur für CI).
- Konfiguration `~/.config/kiros/config.toml`: Standardmodell, Sitzungs-Obergrenze, Freigabemodus, Broker-Port. Rechte 0600.

## 5 Modelle und Kosten

**BELEGT** (`openrouter_models.py`, `openrouter.py`):
- Geschlossene free-Liste, Katalogprüfung 22.11.2026: `particle-ai/particle-1:free`, Fallback `baidu/ernie-5.5-flash-preview:free`, `nvidia/nemotron-3-ultra-550b-a55b:free` (zuletzt 26.11. getestet).
- Einzige bezahlte Route: `deepseek/deepseek-v4.1-flash`; Preisgrenze USD/1M Token: prompt 0.0498, completion 0.1992 (`OPENROUTER_DEEPSEEK_MAX_PRICE`); Überschreitung bricht mit `provider_paid_budget` ab.
- Kosten-Nachweise je Antwort vorhanden: `paid_cost_upper_bound_usd` (Vorab-Obergrenze) und `reported_cost_usd` (aus `usage`); bezahlte Fallback-Modelle sind verboten, zahlende Nutzung verlangt `openrouter_allow_paid` plus explizite Limits.

**Beschluss 26.11.:** Kostenlose Modelle zuerst; Budget „OpenRouter bis 10 USD verbrauchen, mindestens 10 USD Rest" ist als Regel hinterlegt, aber technischer Vollzug obliegt TollGate (noch nicht bereit).

**VORSCHLAG bis TollGate bereitsteht:** harte Obergrenze je KirOS-Sitzung (`--max-cost`, Standard: nur free, effectively 0 USD); bezahltes Modell nur mit `--allow-paid`; Kosten-/Tokenzeile nach jeder Antwort; Sitzungsabruf verweigert vor der Anfrage, wenn Obergrenze erreicht (`provider_paid_budget`-Semantik wiederverwenden).

## 6 Sicherheit

**BELEGT:**
- Authorization-Header wird nur für die Anfrage gebaut und danach verworfen; HTTP-Fehler werden nur als Kategorie (authentication/payment/rate_limit) protokolliert (`openrouter.py`, `_post_chat`).
- Credentials bleiben im Speicher des Aufrufers (`openrouter_credentials.py` Docstring).
- Brett-Metadaten werden gegen Token-/Passwort-Muster gefiltert (`_SECRETS` in `completion_handoff.py`).
- MCP-Werkzeuge: Katalog gegen Freigabeliste geprüft, zu viel oder nicht freigegeben → Abweisung, Grenzen auf Ergebnisgröße und Aufrufzahl (`openrouter.py`).

**VORSCHLAG KirOS:**
- Schwarze Liste auf allen Ausgaben: Secret-Wert, `sk-`-Muster, Bearer-Blöcke; Chat-Protokoll/Sitzungsverlauf vor dem Speichern filtern; keine Secrets in `ps`-Sichtbarkeit (Argumente) und in Fehlertexten.
- Werkzeug-Freigaben: Datei-Schreib- und Befehlsausführung nur mit Freigabe je Sitzung (an/aus + Nachfragen); Standard aus.
- Dateirechte: Konfiguration/Sitzungen 0600, Verzeichnis 0700.
- Der KiraBridge-Keychain bleibt unangetastet: KirOS liest wie vorhanden und schreibt nur über den 4AllPass-Weg neu.

## 7 Tests und Abnahmekriterien

- **S2 CLI-Kern und S3 OpenRouter** (Prompt → OpenRouter → Antwort): Mock-API-Test ohne Kosten (Anfrageaufbau, `finish_reason`, Abbruchgrenzen); Realtest mit `nvidia/nemotron-3-ultra-550b-a55b:free`. *Abnahme:* nichtleere Antwort, `reported_cost_usd` 0 bzw. fehlend, `ps`-Ausgabe und Log ohne Schlüsselsplitter.
- **S5 Schlüsselbezug 4AllPass**: 4AllPass-Broker mit Freigabefenster; Fallback-Kette Keychain → `auth.json`. *Abnahme:* `kiros key status` ohne Werte; fehlender Schlüssel → `agent_auth`-artige klare Meldung; Secret-Scan der Protokolle leer; Broker-Verweigerung beendet die Sitzung ohne Anfrage.
- **S4 DeepSeek und Budget**: Modusumschaltung, bezahlte Route nur mit `--allow-paid` und Preisgrenze; Sitzungs-Obergrenze. *Abnahme:* zweite Anfrage über der Obergrenze bricht vor Versand ab; free-Tests kosten nachweislich 0 USD (belegtes `usage`-Feld); Modell außerhalb Liste wird abgewiesen.
- **S6 Werkzeuge/MCP und Gesamtabnahme**: Datei-/Befehls Werkzeuge mit Freigabe; Mock-Werkzeugkreis plus ein Realtest. *Abnahme:* ohne Freigabe keine Anfrage; nicht freigegebenes/überzähliges Werkzeug wird abgewiesen; Kataloggrenzen greifen (16 Werkzeuge, Bytegrenzen).
- **K1 Koordinator (nach S6)**: Rolle, Nachrichtenkanal, Completion-Hook (Reuse `completion_handoff.py`), MCP-Server, ACP-Client (Reuse `acp.py`). *Abnahme:* KirOS führt als Worker registriert einen KiraBridge-Auftrag aus, schreibt und liest das Ergebnis mit Rücklese-Bestätigung; ACP-Sitzung über 10 Züge stabil ohne Duplikat-Text.

## 8 Entscheidungen zu den offenen Fragen (Koordinator, 26.11.2026)

1. **Importstabilität:** KiraBridge bekommt eine schmale, dokumentierte Fassade (`kirabridge.kiros_api`), die Provider, Credentials, ACP-Client und Completion-Hook für KirOS exportiert. KirOS importiert nur darüber. Änderungen an der Fassade brauchen einen Test aus KirOS-Sicht. Erster PR in KiraBridge, vor S2.
2. **4AllPass-Broker:** KirOS spricht das dokumentierte Protokoll des Loopback-Brokers (4AllPass `docs/local-access-broker.md`) mit einem kleinen Python-Client nach; Token nur über die Umgebungsvariable `FOURALLPASS_BROKER_TOKEN`. Vor S5 wird das Protokoll in `docs/BROKER.md` festgehalten.
3. **Budget:** Die Sitzungs-Obergrenze von KirOS bleibt als harte Grenze bestehen. TollGate ergänzt später die Konto-Ebene (Mindestrest, Budget je Schlüssel); beide wirken nebeneinander, die strengere gilt.
4. **Modellliste:** weiter manuell gepinnt; ein späteres `kiros models sync` nur mit ausdrücklicher Nutzerfreigabe und Preisprüfung.
5. **Sitzungsverlauf:** lokal unter `~/.local/state/kiros/` (Verzeichnis 0700, Dateien 0600), Standard an, abschaltbar (`--no-history`), vor dem Schreiben nach Geheimnismustern gefiltert; nie Schlüsselwerte.
6. **Lizenz:** gleiche Lizenz wie KiraBridge (Netzwerkpunkt Personal Use License 1.0); gleiche Rechteinhaberin bzw. gleicher Rechteinhaber, daher keine Kompatibilitätsfrage zwischen KirOS und dem `kirabridge`-Paket.

## 9 Nächste Schritte

S1 (diese Spezifikation) → Fassade `kirabridge.kiros_api` in KiraBridge → S2/S3 CLI-Kern mit OpenRouter (kostenlos) → S4 DeepSeek mit Preisgrenze → S5 Schlüsselbezug 4AllPass → S6 Werkzeuge und Gesamtabnahme → K1 Koordinatorfunktionen.
