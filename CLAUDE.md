# Dictionary management - pokyny pro Claude

Tento projekt pouziva **Beads** pro rizeni ukolu a projektove pameti misto markdown planu.

## Prace s tasky

Na zacatku kazde session:
```bash
bd ready          # co je pripraveno k praci
bd show <id>      # detail ukolu
```

Pri praci:
```bash
bd update <id> --claim        # vezmi ukol
bd update <id> --status done  # uzavri ukol
bd create "Novy ukol" -t bug  # zaznamenej objev
```

Na konci session (pristat letadlo):
```bash
bd list --status in_progress  # co zustalo otevrene
bd ready                      # predej kontext pristi session
git add .beads/; git commit -m "beads: sync"
```

## Pravidla pro praci s projektem

- Vzdy pouzivej Beads jako jediny zdroj pravdy pro ukoly, epiky, bugy, funkce i planovani.
- Nepouzivej interni seznamy "Tasks" Claude, pokud o to vyslozne nepozadam.
- Veskere kroky planovani, rozpad funkci i identifikace sub-ukolu vzdy provadej pomoci Beads CLI.

### Mapovani prikazu (claude.ai chat - Desktop Commander)

| Zamer | Co udelam |
|-------|-----------|
| Novy ukol | ``bd create ...`` pres Desktop Commander |
| Zahajit praci | ``bd update <id> --claim`` |
| Ukoncit praci | ``bd update <id> --status done`` |
| Rozpad zadani | ``bd create`` epicy + tasky s ``--parent`` |
| Prehled stavu | ``bd list`` / ``bd ready`` |
| Zavislosti | ``bd dep add <id> <id> --type blocks`` |

### Spousteni prikazu

Pracujeme v **claude.ai chatu** s nastrojem **Desktop Commander**.
Slash commandy (``/beads:*``) nejsou dostupne - misto nich spoustim
odpovidajici ``bd`` CLI prikazy primo pres Desktop Commander.

## Cesty nastroju (PATH neni dostupny ve vsech kontextech)

- `bd.exe`: `C:\Users\rjaeg\go\bin\bd.exe`
- `git.exe`: `C:\Program Files\Git\bin\git.exe`
- Vzdy pouzivej plnou cestu pri volani z Desktop Commander nebo JetBrains terminalu.

## Backend Beads

Beads pouziva Dolt SQL server bezici na:

- host: ``127.0.0.1``
- port: ``3307``

## Ocekavane chovani

- Udrzuj vsechny ukoly, zavislosti a postup prace v Beads.
- Pri praci vychazej z existujicich issues v Beads.
- Pokud bude treba vytvorit subtasky nebo rozsirit plan, pouzij ``bd create`` s ``--parent``.
- Pokud reknu "pokracuj na ukolech", nejprve zjisti stav pres ``bd ready``.
- Pokud pozadam o prehled celeho projektu, pouzij ``bd list``.
- Pokud je potreba vytvorit zavislosti mezi ukoly, pouzivej ``bd dep add``.

## Architektura a dokumentace

- **Denik vyvoje:** docs/architecture.md
- **Plan projektu:** docs/plan.md
- **DB schema:** docs/database.md

## Stack

Python 3.13 + FastAPI | MongoDB (Beanie 2.0) 


## Testování

Testů je příliš mnoho pro jediný spuštění — MCP nástroje mají timeout ~4 minuty, ale celá sada trvá 6+ minut.
Testuj vždy po jednom souboru a výsledky sbírej ze souboru.
Nakonec vytvoř souhrnnou zprávu.

### Jak spouštět testy (fungující postup)

**Preferovaná metoda: JetBrains terminál** (pokud je PyCharm otevřený s projektem):
```
# JetBrains MCP: execute_terminal_command s truncateMode=START
.venv\Scripts\python.exe -m pytest tests\test_X.py -v --tb=short
```

**Záložní metoda: Desktop Commander do souboru + čtení výsledku:**
```
# 1. Spustit na pozadí do souboru (Desktop Commander start_process, timeout_ms=10000):
cmd /c "cd /d D:\development\git\ippc-docs && .venv\Scripts\python.exe -m pytest tests\test_X.py -v --tb=short > test_log_X.txt 2>&1 && echo DONE >> test_log_X.txt"

# 2. Opakovaně číst výsledek dokud se neobjeví DONE (Desktop Commander read_file, offset=-20):
Desktop Commander read_file D:\development\git\ippc-docs\test_log_X.txt offset=-20
```

**DŮLEŽITÉ:** Nespouštěj read_process_output s dlouhým timeout_ms — způsobí zaseknutí MCP.
Místo toho: start_process spustí na pozadí, pak čti soubor v krátkých smyčkách.

### Venv a Python

- Python: `D:\development\git\dictionary-management\.venv\Scripts\python.exe` (Python 3.13)
- Pytest: `.venv\Scripts\python.exe -m pytest ...`

