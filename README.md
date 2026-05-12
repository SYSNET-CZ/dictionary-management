# SYSNET Managed Dictionaries

REST API služba pro správu řízených slovníků (číselníků) SYSNET.
Slouží jako centrální zdroj pravdy pro překladové tabulky a klasifikační číselníky
napříč systémy (primárně CITES Registry).

## Rychlý start

```bash
# Nainstaluj závislosti
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Spusť MongoDB (pokud ještě neběží)
docker run -d --name mongo -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=s3cr3t mongo:6

# Nastav konfiguraci
cp conf/dict.yml.example conf/dict.yml  # a uprav heslo

# Spusť vývojový server
fastapi dev api/main.py
```

API běží na `http://localhost:8000`.
OpenAPI dokumentace: `http://localhost:8000/docs`

## Spuštění v Dockeru

```bash
docker build -t sysnetcz/dictionaries:latest .
docker run -p 8080:8000 \
  -e MONGO_HOST=mongo \
  -e MONGO_PASSWORD=produkční-heslo \
  sysnetcz/dictionaries:latest
```

## Stack

| Vrstva | Technologie |
|--------|-------------|
| Runtime | Python 3.13 (async) |
| Framework | FastAPI 0.115+ |
| Databáze | MongoDB 6.0+ |
| ODM | Beanie 1.29+ (async pymongo ≥ 4.0) |

## Dokumentace

| Dokument | Obsah |
|----------|-------|
| [docs/architecture.md](docs/architecture.md) | Architektura, moduly, indexy, logging |
| [docs/api.md](docs/api.md) | Kompletní API reference s příklady |
| [docs/data-model.md](docs/data-model.md) | MongoDB schéma, Pydantic modely, ODM |
| [docs/consolidation.md](docs/consolidation.md) | Migrace UUID→str identifikátorů |
| [docs/configuration.md](docs/configuration.md) | Proměnné prostředí, dict.yml |
| [docs/development.md](docs/development.md) | Vývoj, testování, pokrytí kódu |
| [docs/operations.md](docs/operations.md) | Docker, zálohování, monitoring |

## Testování

```bash
# Integrační testy (vyžaduje MongoDB na localhost:27017)
.venv/Scripts/python.exe -m pytest tests/integration/ -v

# S měřením pokrytí
.venv/Scripts/python.exe -m pytest tests/integration/ --cov=api --cov-report=term-missing
```

Aktuální pokrytí: **72 %** (63 integračních testů).

## Zálohování a obnova

```bash
# Záloha
docker exec mongo sh -c \
  'mongodump --archive --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin > /backup/dictionaries.dump'
docker cp mongo:/backup/dictionaries.dump .

# Obnova
docker cp dictionaries.dump mongo:/backup/
docker exec mongo sh -c \
  'mongorestore --archive --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin < /backup/dictionaries.dump'
```

## Licence

GNU Affero General Public License v3.0 — viz [https://www.gnu.org/licenses/agpl-3.0.html](https://www.gnu.org/licenses/agpl-3.0.html)

SYSNET s.r.o. | [sysnet.cz](https://sysnet.cz) | info@sysnet.cz
