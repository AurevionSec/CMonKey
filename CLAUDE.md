# Projekt-Anweisungen für Claude

## QA-Modus

Wenn der Benutzer den **QA-Modus aktiviert** (z.B. "QA-Modus an", "mit QA arbeiten"), gilt folgendes:

### Aufgabenstruktur

Bei jeder Programmieraufgabe:

1. **Hauptaufgabe** in sinnvolle **Unteraufgaben** teilen (TodoWrite)
2. Jede **Unteraufgabe** beim ersten Bearbeiten in **Unterunteraufgaben** teilen
3. Unterunteraufgaben sind die kleinste Arbeitseinheit

### Ablauf pro Unterunteraufgabe

```
FÜR JEDE Unterunteraufgabe:
  1. Implementieren
  2. QA-Prüfung durchführen (siehe unten)
  3. Bei Fehlern:
     - Fixen
     - Zurück zu Schritt 2
  4. Bei Erfolg:
     - Codex-Validierung
     - Bei Missständen: Fixen → Zurück zu Schritt 4
  5. Erst wenn alles sauber: Unterunteraufgabe als erledigt markieren
  6. Nächste Unterunteraufgabe
```

### QA-Prüfung (nach jeder Unterunteraufgabe)

Führe **nur für die geänderten Dateien** durch:

1. **Formatierung** - Auto-Format anwenden
2. **Linting** - Code-Style prüfen
3. **Type-Check** - Typ-Fehler finden
4. **Compile/Build** - Kompiliert es?
5. **Tests** - Relevante Tests ausführen
6. **Security-Quick-Check** - Offensichtliche Probleme?

### Codex-Validierung

Nach erfolgreicher QA-Prüfung, verwende `codex review` (nicht-interaktiv).

**Syntax:** Prompt muss via stdin übergeben werden:

```bash
cat << 'EOF' | codex review --uncommitted -
Aufgabe: [Hauptaufgabe]
├── Unteraufgabe: [Aktuelle Unteraufgabe]
│   └── Unterunteraufgabe: [Gerade abgeschlossene Unterunteraufgabe]

Prüfe sorgfältig und tiefgründig ob die Aufgabe gemäß der Dokumentation ausgeführt wurde. Bei Abweichung schreibe den Missstand.
EOF
```

**Kurzform:**
```bash
echo "Prüfe ob die Implementierung korrekt ist. Bei Abweichung schreibe den Missstand." | codex review --uncommitted -
```

### Nach Abschluss ALLER Unterunteraufgaben einer Unteraufgabe

Führe erweiterte Checks durch:
- Coverage-Prüfung
- Complexity-Check
- Dead-Code-Detection
- Dependency-Audit

### Nach Abschluss der gesamten Hauptaufgabe

Führe `/qa` aus für finale Validierung des gesamten Projekts.

---

## Check-Befehle (Referenz)

### JavaScript/TypeScript
| Check | Befehl |
|-------|--------|
| Format | `npx prettier --write [datei]` |
| Lint | `npx eslint [datei]` |
| Types | `npx tsc --noEmit` |
| Test | `npm test -- --findRelatedTests [datei]` |

### Python
| Check | Befehl |
|-------|--------|
| Format | `ruff format [datei]` |
| Lint | `ruff check [datei]` |
| Types | `mypy [datei]` |
| Test | `pytest [test_datei]` |

### Rust
| Check | Befehl |
|-------|--------|
| Format | `cargo fmt` |
| Lint | `cargo clippy` |
| Test | `cargo test [testname]` |

### C/C++
| Check | Befehl |
|-------|--------|
| Format | `clang-format -i [datei]` |
| Lint | `clang-tidy [datei]` |
| Compile | `gcc -Wall -Wextra -Werror -c [datei]` |
| Memory | `valgrind ./[binary]` |

---

## QA-Modus Steuerung

- **Aktivieren**: "QA-Modus an" / "mit QA arbeiten" / "QA aktivieren"
- **Deaktivieren**: "QA-Modus aus" / "ohne QA" / "QA deaktivieren"
- **Status**: Standardmäßig AUS bis explizit aktiviert
