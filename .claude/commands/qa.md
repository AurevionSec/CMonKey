---
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, TodoWrite
description: Iterativer QA-Prozess mit automatischer Aufgabenteilung und Auto-Fix. Läuft bis alle Checks bestanden sind.
argument-hint: [scope: datei/modul oder leer für ganzes Projekt]
---

# QA-Modus: Qualitätssicherung

## Ablauf

Dieser QA-Prozess funktioniert iterativ:

1. **Erste Ausführung**: Teile die Aufgabe in sinnvolle Unteraufgaben (TodoWrite)
2. **Jede Unteraufgabe**: Bei erstem Aufruf weiter unterteilen falls komplex
3. **Schleife**: Prüfen → Fixen → Erneut prüfen bis sauber
4. **Abschluss**: Erst beenden wenn ALLE Checks ohne Einwände bestehen

## QA-Phasen

### Phase 1: Projekt analysieren und Aufgaben erstellen

Analysiere das Projekt:
- Welche Sprachen/Frameworks werden verwendet?
- Welche Build-Tools existieren (package.json, pyproject.toml, Cargo.toml, Makefile)?
- Welche Test-Frameworks sind konfiguriert?

Erstelle dann mit TodoWrite eine strukturierte Aufgabenliste basierend auf:
1. **Formatierung** - Auto-Format vor allen anderen Checks
2. **Linting** (pro Sprache/Modul)
3. **Type-Checking** (pro Sprache/Modul)
4. **Tests + Coverage** (Mindest-Abdeckung prüfen)
5. **Build-Prüfung**
6. **Complexity-Check** - Zyklomatische Komplexität messen
7. **Dead-Code-Detection** - Ungenutzten Code finden
8. **Security-Scans**:
   - Dependency-Audit (veraltete/unsichere Pakete)
   - Secrets-Scan (hardcodierte Keys/Passwörter)
   - Lizenz-Check (Kompatibilität)
9. **Performance** (für C: Memory-Leak-Check)
10. **Dokumentations-Prüfung** (README, API-Docs, Changelog)
11. **Code-Review** (Architektur, Best Practices)
12. **Codex-Analyse** (finale Validierung)

### Phase 2: Iterative Prüf-Schleife

Für jede Unteraufgabe:

```
WIEDERHOLE:
  1. Führe den Check aus
  2. Bei Fehlern:
     - Analysiere die Ursache
     - Implementiere Fix
     - Markiere NICHT als erledigt
     - Gehe zu Schritt 1
  3. Bei Erfolg:
     - Markiere Unteraufgabe als erledigt
     - Gehe zur nächsten Unteraufgabe
BIS: Alle Unteraufgaben erledigt
```

### Phase 3: Finale Validierung

Nach allen Einzelchecks:
1. Führe ALLE Checks nochmal durch (Full Build + Test Suite)
2. Bei neuen Fehlern: Zurück zu Phase 2
3. Bei Erfolg: QA abgeschlossen

## Check-Befehle (Auto-Detect)

Je nach Projekt-Setup verwende die passenden Befehle:

---

### JavaScript/TypeScript

| Check | Befehl |
|-------|--------|
| Format | `npx prettier --write .` |
| Lint | `npm run lint` oder `npx eslint .` |
| Types | `npx tsc --noEmit` |
| Test + Coverage | `npm test -- --coverage` (Ziel: ≥80%) |
| Build | `npm run build` |
| Complexity | `npx es6-plato -r -d report src/` |
| Dead Code | `npx ts-prune` oder `npx knip` |
| Dependency-Audit | `npm audit` |
| Secrets-Scan | `npx secretlint .` |
| Lizenz-Check | `npx license-checker --summary` |

---

### Python

| Check | Befehl |
|-------|--------|
| Format | `black .` oder `ruff format .` |
| Lint | `ruff check .` oder `flake8` |
| Types | `mypy .` oder `pyright` |
| Test + Coverage | `pytest --cov=. --cov-fail-under=80` |
| Build | `python -m build` |
| Complexity | `radon cc . -a -s` |
| Dead Code | `vulture .` |
| Dependency-Audit | `pip-audit` oder `safety check` |
| Secrets-Scan | `detect-secrets scan` |
| Lizenz-Check | `pip-licenses` |

---

### Rust

| Check | Befehl |
|-------|--------|
| Format | `cargo fmt` |
| Lint | `cargo clippy -- -D warnings` |
| Types | (integriert) |
| Test + Coverage | `cargo tarpaulin --fail-under 80` |
| Build | `cargo build --release` |
| Complexity | `cargo geiger` (unsafe-Code) |
| Dead Code | `cargo udeps` |
| Dependency-Audit | `cargo audit` |
| Secrets-Scan | `trufflehog filesystem .` |
| Lizenz-Check | `cargo deny check licenses` |

---

### C/C++

| Check | Befehl |
|-------|--------|
| Format | `clang-format -i *.c *.h` |
| Lint | `clang-tidy *.c` oder `cppcheck --enable=all .` |
| Compile (GCC) | `gcc -Wall -Wextra -Werror -pedantic -std=c11` |
| Compile (Clang) | `clang -Wall -Wextra -Werror -pedantic -std=c11` |
| Static Analysis | `scan-build make` oder `clang --analyze` |
| Test | `make test` oder Test-Binary ausführen |
| Build | `make` oder `cmake --build .` |
| Coverage | `gcov` + `lcov --fail-under-lines 80` |
| Complexity | `pmccabe *.c` oder `lizard .` |
| Dead Code | `cppcheck --enable=unusedFunction` |
| Memory-Leaks | `valgrind --leak-check=full ./binary` |
| AddressSanitizer | Compile mit `-fsanitize=address` |
| Dependency-Audit | Manuell oder `cve-bin-tool` |
| Secrets-Scan | `gitleaks detect` oder `trufflehog` |

---

### Allgemein (alle Sprachen)

| Check | Befehl |
|-------|--------|
| Secrets-Scan | `gitleaks detect --source .` |
| Lizenz-Scan | `licensefinder` oder `fossa analyze` |
| SBOM generieren | `syft .` |
| Docs aktuell? | Vergleiche README mit tatsächlicher API |
| Changelog | Prüfe ob CHANGELOG.md aktualisiert wurde |

- Prüfe Makefile, justfile, oder scripts/ für projektspezifische Befehle
- Falls Tool nicht installiert: Installieren oder Alternative nutzen

## OpenAI Codex Review

Nach den automatischen Checks, führe eine Codex-Analyse durch (nicht-interaktiv).

**Syntax:** Prompt MUSS via stdin übergeben werden (Heredoc oder echo):

```bash
cat << 'EOF' | codex review --uncommitted -
Aufgabe: [Hauptaufgabe aus TodoWrite]
├── Unteraufgabe: [Aktuelle Unteraufgabe]
│   └── Unterunteraufgabe: [Aktuelle Unterunteraufgabe falls vorhanden]

Prüfe sorgfältig und tiefgründig ob die Aufgabe gemäß der Dokumentation ausgeführt wurde. Bei Abweichung schreibe den Missstand.
EOF
```

**Beispiel-Aufruf:**

```bash
cat << 'EOF' | codex review --uncommitted -
Aufgabe: QA für Authentifizierungs-Modul
├── Unteraufgabe: Input-Validierung prüfen
│   └── Unterunteraufgabe: SQL-Injection-Schutz verifizieren

Prüfe sorgfältig und tiefgründig ob die Aufgabe gemäß der Dokumentation ausgeführt wurde. Bei Abweichung schreibe den Missstand.
EOF
```

**Kurzform:**
```bash
echo "Prüfe ob die Implementierung korrekt ist. Bei Abweichung schreibe den Missstand." | codex review --uncommitted -
```

**Codex-Integration in Schleife:**
1. Nach jedem erfolgreichen Check: `codex review --uncommitted` mit Aufgabenhierarchie
2. Bei Missständen:
   - Missstand dokumentieren
   - Fix implementieren
   - Erneut Codex aufrufen
3. Erst weiter wenn Codex keine Missstände mehr findet

## Code-Review Kriterien

Prüfe auf:
- [ ] Keine offensichtlichen Bugs oder Logikfehler
- [ ] Keine Security-Schwachstellen (Injection, XSS, etc.)
- [ ] Keine hardcodierten Secrets oder Credentials
- [ ] Sinnvolle Fehlerbehandlung
- [ ] Keine auskommentierten Code-Blöcke
- [ ] Keine TODO/FIXME ohne Kontext
- [ ] Konsistenter Code-Stil

## Wichtige Regeln

1. **Niemals aufgeben**: Bei Fehlern immer versuchen zu fixen
2. **Gründlich sein**: Jede Unteraufgabe vollständig abarbeiten
3. **Dokumentieren**: Bei komplexen Fixes kurz erklären was/warum
4. **Ehrlich sein**: Nur "erledigt" markieren wenn wirklich sauber
5. **Scope beachten**: Falls Argument gegeben, nur diesen Bereich prüfen

## Start

Beginne JETZT mit Phase 1: Analysiere das Projekt und erstelle die Aufgabenliste.
