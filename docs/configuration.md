# Konfigurace — SYSNET Managed Dictionaries

## Proměnné prostředí

| Proměnná | Výchozí hodnota | Popis |
|----------|-----------------|-------|
| `DICT_VERSION` | `2.0.1` | Verze API vrácená v `/` a titulu OpenAPI |
| `DICT_NAME` | `SYSNET Managed Dictionaries API` | Název aplikace |
| `INSTANCE` | `DEV` | Prostředí: `DEV`, `TEST`, `PROD` — ovlivňuje log level |
| `DICT_ROOT_PATH` | `dict` | Root path při běhu za reverzní proxy (FastAPI `root_path`) |
| `MONGO_HOST` | `localhost` | Hostname MongoDB serveru |
| `MONGO_PORT` | `27017` | Port MongoDB serveru |
| `MONGO_USERNAME` | `root` | Uživatelské jméno MongoDB |
| `MONGO_PASSWORD` | *(povinné)* | Heslo MongoDB — v produkci vždy nastavit přes env, nikoli v kódu |
| `MONGO_DATABASE` | `dictionaries` | Název MongoDB databáze |
| `LOG_DIR` | `./logs` | Adresář pro log soubory |
| `LOG_FILE_NAME` | `dict.log` | Název hlavního log souboru |
| `CONFIG_DIRECTORY` | `./conf` | Adresář s konfiguračním YAML souborem |
| `CONFIG_FILE_NAME` | `dict.yml` | Název konfiguračního souboru |
| `BACKUP_DIR` | `./backup` | Adresář pro zálohy |
| `UPLOAD_DIRECTORY` | `./upload` | Adresář pro nahrané soubory |

> **Produkční poznámka:** Proměnná `MONGO_PASSWORD` má v kódu bezpečnostní placeholder. V produkci ji vždy nastavujte přes proměnnou prostředí nebo Docker secret — nikdy ji nevkládejte přímo do `dict.yml`, který může být verzován.

## Konfigurační soubor `conf/dict.yml`

Primární způsob konfigurace API klíčů a databáze. Hodnoty z `dict.yml` mají přednost před výchozími hodnotami v `init.py`, ale proměnné prostředí mají přednost před `dict.yml`.

### Struktura

```yaml
dict:
  api_keys:
    - AbCdEfGhIjKlMnOp: "Systemový klient 1"
    - XyZaBcDeFgHiJkLm: "Integrační systém CITES"
    - Qr5sTuVwXyZ01234: "Testovací klient"
  database: dictionaries

mongo:
  host: localhost
  port: 27017
  user: root
  password: s3cr3t
  status: RED
```

### Sekce `dict`

| Klíč | Popis |
|------|-------|
| `api_keys` | Seznam API klíčů — každý klíč je mapa `token: "Popis"` |
| `database` | Název MongoDB databáze (přepisuje `MONGO_DATABASE`) |

### Sekce `mongo`

| Klíč | Popis |
|------|-------|
| `host` | MongoDB hostname (přepisuje `MONGO_HOST`) |
| `port` | MongoDB port (přepisuje `MONGO_PORT`) |
| `user` | Uživatelské jméno (přepisuje `MONGO_USERNAME`) |
| `password` | Heslo (přepisuje `MONGO_PASSWORD`) |
| `status` | Runtime stav `GREEN`/`RED` — zapisuje aplikace, nenastavuje se ručně |

## Generování API klíče

Nový klíč vygenerujte v Pythonu:

```python
import secrets
print(secrets.token_urlsafe(16))
# Výstup: AbCdEfGhIjKlMnOp (22 znaků, URL-safe base64)
```

Nebo přímo z příkazové řádky:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

Vygenerovaný klíč přidejte do `conf/dict.yml` a restartujte službu.

## Sestavení connection stringu

`MONGO_CONNECTION_STRING` se sestavuje automaticky v `init.py`:

```python
MONGO_CONNECTION_STRING = (
    f"mongodb://{CONFIG['mongo']['user']}:{CONFIG['mongo']['password']}"
    f"@{CONFIG['mongo']['host']}:{CONFIG['mongo']['port']}"
)
```

Pro připojení k MongoDB Atlas nebo clusteru s replikací nastavte celý connection string přes vlastní inicializaci nebo přímou úpravou `MONGO_HOST` na hostname clusteru.

## Pořadí načítání konfigurace

1. Výchozí hodnoty v `init.py` (proměnné `MONGO_HOST`, `MONGO_PORT` atd.)
2. Proměnné prostředí — přepisují výchozí hodnoty přes `os.getenv()`
3. `conf/dict.yml` — načten pomocí `sysnet_pyutils.utils.Config`; hodnoty z YAML přepisují výchozí hodnoty, ale **ne** proměnné prostředí

> **Výsledný `CONFIG`** je tedy: výchozí hodnoty → přebity proměnnými prostředí → přebity YAML (kde YAML explicitně přepisuje jen ty klíče, které definuje).

## Logování — konfigurace

Log level závisí na proměnné `INSTANCE`:

```python
ROOT_LEVEL = DEBUG if INSTANCE == "DEV" else INFO
```

Handlery jsou nakonfigurované staticky v `LOGGING_CONFIG` (`init.py`):

| Handler | Třída | Level | Cíl |
|---------|-------|-------|-----|
| `debug_console_handler` | StreamHandler | DEBUG | stdout |
| `info_console_handler` | StreamHandler | INFO | stdout |
| `info_rotating_file_handler` | RotatingFileHandler | INFO | `dict.log` (500 KB × 10) |
| `debug_rotating_file_handler` | RotatingFileHandler | DEBUG | `dict-debug.log` (1 MB × 10) |
| `error_file_handler` | FileHandler | WARN | `dict-error.log` |

Speciální logger `ODM` loguje databázové operace, `uvicorn.error` a `uvicorn.access` jsou přesměrovány do file handlerů.
