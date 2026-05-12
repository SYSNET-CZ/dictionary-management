# Správcovská příručka — SYSNET Managed Dictionaries API

## Instalace a spuštění

### Požadavky

- Python 3.13+
- MongoDB 6.0+
- Docker (volitelně)

### Lokální spuštění

```bash
git clone <repo-url>
cd dictionary-management

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Nastavte konfiguraci (viz níže)
fastapi dev api/main.py
```

API běží na `http://localhost:8000`.
OpenAPI dokumentace: `http://localhost:8000/docs`

### Spuštění v Dockeru

```bash
docker build -t sysnetcz/dictionaries:latest .
docker run -d -p 8080:8000 \
  -e MONGO_HOST=mongo \
  -e MONGO_PASSWORD=produkční-heslo \
  -e INSTANCE=PROD \
  sysnetcz/dictionaries:latest
```

### Docker Compose

```bash
cd docker/
cp template.env .env
# Upravte .env — minimálně MONGO_PASSWORD
docker compose up -d
```

## Konfigurace API klíčů

Klíče jsou uloženy v `conf/dict.yml`:

```yaml
dict:
  api_keys:
    - AbCdEfGhIjKlMnOp: "Systémový klient 1"
    - XyZaBcDeFgHiJkLm: "Integrační systém CITES"
  database: dictionaries
```

Nový klíč vygenerujte:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

Po změně klíčů restartujte službu.

Všechny admin operace vyžadují HTTP hlavičku:

```
X-API-KEY: <váš-api-klíč>
```

## Správa deskriptorů

### Vytvoření nového deskriptoru

```bash
curl -X POST http://localhost:8000/descriptor/country \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "SK",
    "key_alt": "SVK",
    "dictionary": "country",
    "active": true,
    "values": [
      { "lang": "cs", "value": "Slovensko", "value_alt": "Slovenská republika" },
      { "lang": "en", "value": "Slovakia", "value_alt": null }
    ]
  }'
```

Vrátí `409 Conflict` pokud klíč ve slovníku již existuje.

### Aktualizace deskriptoru

```bash
curl -X PUT http://localhost:8000/descriptor/country/SK \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d '{ ...stejná struktura jako POST... }'
```

### Smazání deskriptoru

```bash
curl -X DELETE http://localhost:8000/descriptor/country/SK \
  -H "X-API-KEY: vas-klic"
```

Vrátí `true` při úspěchu.

### Aktivace / deaktivace

```bash
# Deaktivovat
curl -X PATCH "http://localhost:8000/descriptor/activate/country/SK?doit=false" \
  -H "X-API-KEY: vas-klic"

# Aktivovat zpět
curl -X PATCH "http://localhost:8000/descriptor/activate/country/SK?doit=true" \
  -H "X-API-KEY: vas-klic"
```

## Import a export

Viz detailní příručku [import-export.md](import-export.md).

**Stručný přehled:**

```bash
# Export slovníku do souboru
curl -H "X-API-KEY: vas-klic" http://localhost:8000/export/country > country.json

# Import ze souboru
curl -X POST "http://localhost:8000/import?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @country.json
```

## Monitorování a logy

```bash
# Zdravotní check
curl http://localhost:8000/info

# Logy v reálném čase
tail -f logs/dict.log
tail -f logs/dict-error.log
```

Viz [operations.md](operations.md) pro detaily.

## Zálohování MongoDB

```bash
# Záloha
docker exec mongo sh -c \
  'mongodump --archive \
   --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin > /backup/dictionaries.dump'
docker cp mongo:/backup/dictionaries.dump ./backup/

# Obnova
docker cp ./backup/dictionaries.dump mongo:/backup/
docker exec mongo sh -c \
  'mongorestore --archive \
   --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin < /backup/dictionaries.dump'
```

## Migrace dat (konsolidace)

Pokud přecházíte ze starší verze služby ukládající `identifier` jako MongoDB UUID:

```bash
python3 -c "
import asyncio
from sprint1 import init_sprint, consolidate_data

async def main():
    await init_sprint()
    n = await consolidate_data()
    print(f'Konsolidováno: {n}')

asyncio.run(main())
"
```

Viz [consolidation.md](consolidation.md) pro kompletní dokumentaci.
