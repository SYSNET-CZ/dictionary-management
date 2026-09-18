# dictionary-management — kontext pro Hermes

## Co je tento projekt

REST API služba pro správu řízených slovníků (číselníků) SYSNET.
Centrální zdroj pravdy pro překladové tabulky napříč systémy (primárně CITES Registry).

- **Image:** `sysnetcz/dictionaries`
- **Verze:** viz `VERSION`
- **Stack:** Python 3.13 + FastAPI + MongoDB (Beanie) + sysnet-pyutils

## Prostředí

| Instance | Host | Kontejner | Použití |
|---|---|---|---|
| Obecná | sysnet-athos | `dictionaries` | Sdílená pro všechny systémy |
| IPPC | sysnet-athos | `ippc-dict` | IPPC stack |

## Cesty

- Projekt: `~/projects/dictionary-management/`
- Konfigurace: `conf/dict.yml` (gitignorováno, dodává se ručně)
- Dokumentace: `docs/`

## Spuštění testů

```bash
cd ~/projects/dictionary-management
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -q
.venv/bin/python -m pytest tests/ -q --tb=short --ignore=tests/integration
# 148 testů, ~3s
```

## Architektura

```
api/
  main.py          — FastAPI app, lifespan, middleware
  routers/
    public.py      — GET /descriptor/{dict}/{key}, GET /list, GET /suggest
    admins.py      — POST/PUT/DELETE /descriptor (X-API-KEY)
    monitor.py     — GET /info, HEAD /
  model/
    odm.py         — DbDescriptor (Beanie Document)
    dictionary.py  — DictionaryType enum
    admin.py       — admin schémata
  dependencies.py  — FastAPI Depends (API key validace)
  commons.py       — sdílené utility
init.py            — konfigurace z conf/dict.yml + env
```

## Konfigurace (conf/dict.yml)

```yaml
dictionaries:
  database: dictionaries
  api_keys:
    - <key>: <label>
mongo:
  host: mongo-db
  port: 27017
  user: mongo
  password: <heslo>
```

## Issue tracking

GitHub Issues: https://github.com/SYSNET-CZ/dictionary-management/issues

```bash
gh issue list --repo SYSNET-CZ/dictionary-management
gh issue create --repo SYSNET-CZ/dictionary-management --title "..." --body "..."
```

## Release postup

```bash
# 1. Bump verze
echo "X.Y.Z" > VERSION
git add VERSION && git commit -m "chore: bump version to X.Y.Z"
git push origin main

# 2. CI automaticky builduje a pushuje image na Docker Hub
# (workflow_dispatch nebo tag)

# 3. Deploy na Athos
ssh sysnet-athos "cd /opt/docker/dictionaries && \
  sed -i 's/DICT_VERSION=.*/DICT_VERSION=X.Y.Z/' .env && \
  docker compose pull && docker compose up -d"
```

## Dokumentace

- `docs/architecture.md` — architektura, moduly
- `docs/api.md` — kompletní API reference
- `docs/data-model.md` — MongoDB schéma
- `docs/configuration.md` — env proměnné
- `docs/operations.md` — Docker, zálohování, monitoring
