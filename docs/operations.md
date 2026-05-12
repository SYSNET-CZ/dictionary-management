# Provozní příručka — SYSNET Managed Dictionaries

## Docker

### Sestavení obrazu

```bash
docker build -t sysnetcz/dictionaries:latest .
```

### Spuštění kontejneru

```bash
docker run -d \
  --name dict-api \
  -p 8080:8000 \
  -e MONGO_HOST=mongo \
  -e MONGO_PORT=27017 \
  -e MONGO_USERNAME=root \
  -e MONGO_PASSWORD=produkční-heslo \
  -e INSTANCE=PROD \
  -v /data/dict/logs:/app/logs \
  -v /data/dict/conf:/app/conf \
  sysnetcz/dictionaries:latest
```

### Docker Compose (doporučeno pro produkci)

```bash
cd docker/
cp template.env .env
# Upravte .env — minimálně nastavte MONGO_PASSWORD
docker compose up -d
```

## Zdravotní kontrola

```bash
# Rychlý check (HEAD request)
curl -I http://localhost:8080/

# Detailní stav s MongoDB statusem
curl http://localhost:8080/info
```

Odpověď `/info`:
```json
{
  "status": "GREEN",
  "mongo": { "status": "GREEN" },
  "dictionaries": [
    { "dictionary": "country", "count": 249 }
  ]
}
```

Možné stavy:
- `GREEN` — MongoDB dostupná, vše v pořádku
- `RED` — problém s připojením k MongoDB

Docker `HEALTHCHECK` by měl cílit na `HEAD /` nebo `HEAD /info`.

## Zálohování MongoDB

### Záloha

```bash
# Záloha jedné databáze do souboru
docker exec mongo sh -c \
  'mongodump --archive \
   --db=dictionaries \
   --username root \
   --password heslo \
   --authenticationDatabase=admin' \
  > backup/dictionaries-$(date +%Y%m%d-%H%M%S).dump
```

Nebo přes `docker cp`:

```bash
docker exec mongo sh -c \
  'mongodump --archive \
   --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin > /backup/dictionaries.dump'
docker cp mongo:/backup/dictionaries.dump ./backup/
```

### Obnova

```bash
docker cp ./backup/dictionaries.dump mongo:/backup/
docker exec mongo sh -c \
  'mongorestore --archive \
   --db=dictionaries \
   --username root --password heslo \
   --authenticationDatabase=admin \
   < /backup/dictionaries.dump'
```

> **Pozor:** `mongorestore` bez `--drop` přidává záznamy k existujícím — pro plnou obnovu přidejte `--drop`.

## Logy

Soubory v adresáři `logs/` (nebo `$LOG_DIR`):

| Soubor | Level | Obsah |
|--------|-------|-------|
| `dict.log` | INFO+ | Běžný provoz — přístupy, operace |
| `dict-debug.log` | DEBUG+ | Podrobné ladění — MongoDB dotazy |
| `dict-error.log` | WARN+ | Chyby a varování |

Rotace je automatická (RotatingFileHandler). `dict.log`: max 500 KB, 10 záložních kopií. `dict-debug.log`: max 1 MB, 10 kopií.

### Sledování live logu

```bash
tail -f logs/dict.log
# nebo pro chyby:
tail -f logs/dict-error.log
```

### Důležité log záznamy

| Zpráva | Úroveň | Popis |
|--------|--------|-------|
| `Connected to database cluster.` | INFO | Úspěšné připojení k MongoDB při startu |
| `User 'jméno' logged in` | INFO | Úspěšná autentizace API klíčem |
| `export_all: výsledek oříznut na 1000 záznamů` | WARNING | Kolekce obsahuje více než 1000 záznamů, export je nekompletní |
| `IMPORT item N FAILED: ...` | ERROR | Chyba při importu jednoho záznamu |
| `Problem connecting to database cluster.` | ERROR | MongoDB nedostupná při startu |

## Aktualizace aplikace

```bash
# Pull nové verze
docker pull sysnetcz/dictionaries:latest

# Restart kontejneru (zachová data v MongoDB)
docker compose down
docker compose up -d
```

Po aktualizaci ověřte stav:
```bash
curl http://localhost:8080/info
```

## Migrace dat po aktualizaci

Pokud aktualizace zahrnuje konsolidaci dat (UUID → str migrace), spusťte po startu:

```bash
docker exec dict-api python3 -c "
import asyncio
from sprint1 import init_sprint, consolidate_data

async def main():
    await init_sprint()
    n = await consolidate_data()
    print(f'Konsolidováno: {n}')

asyncio.run(main())
"
```

Viz [consolidation.md](consolidation.md) pro detaily.

## Monitoring

### Doporučené metriky

| Metrika | Jak zjistit |
|---------|-------------|
| Dostupnost | `HEAD /` → HTTP 200 |
| Stav MongoDB | `GET /info` → `$.status == "GREEN"` |
| Počty deskriptorů | `GET /info` → `$.dictionaries[*].count` |

### Uptime monitoring

Pokud používáte Uptime Kuma, Prometheus blackbox exporter nebo podobný nástroj:

```yaml
# Uptime Kuma: HTTP monitor
URL: http://localhost:8080/
Method: HEAD
Expected status: 200
```

### Doporučená zálohovací frekvence

| Prostředí | Frekvence | Počet záložních kopií |
|-----------|-----------|----------------------|
| Produkce | 1× denně (noc) | 14 dní |
| Staging | 1× týdně | 4 týdny |
| Vývoj | ad hoc | — |

## Škálování

Aplikace je bezstavová (stateless) — lze provozovat více instancí za load balancerem. MongoDB zajišťuje konzistenci dat. Každá instance se při startu připojí k MongoDB a inicializuje Beanie.

> **Pozor na indexy:** `init_beanie()` vytváří indexy při startu. Při souběžném spuštění více instancí může dojít k souběžnému pokusu o vytvoření stejného indexu — MongoDB tuto situaci zvládá bezpečně (idempotentní operace).
