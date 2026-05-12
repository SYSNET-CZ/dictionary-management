# Vývojová příručka — SYSNET Managed Dictionaries

## Požadavky

- Python 3.13+
- MongoDB 6.0+ (doporučeno přes Docker)
- Git

## Nastavení prostředí

```bash
git clone <repo-url>
cd dictionary-management

# Vytvoř virtuální prostředí
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# Nainstaluj závislosti
pip install -r requirements.txt
```

## Spuštění MongoDB pro vývoj

```bash
docker run -d \
  --name mongo-dict \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=s3cr3t \
  mongo:6
```

## Konfigurace pro vývoj

Zkopírujte vzorový konfigurační soubor a upravte heslo:

```bash
cp conf/dict.yml.example conf/dict.yml   # pokud existuje vzor
# nebo ručně vytvořte conf/dict.yml
```

Minimální obsah `conf/dict.yml`:
```yaml
dict:
  api_keys:
    - dev-api-key-1234567890123: "Dev klient"
  database: dictionaries

mongo:
  host: localhost
  port: 27017
  user: root
  password: s3cr3t
  status: RED
```

## Spuštění vývojového serveru

```bash
# S automatickým reloadem
fastapi dev api/main.py

# Nebo přímo
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI dokumentace: [http://localhost:8000/docs](http://localhost:8000/docs)
ReDoc dokumentace: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testování

### Prerekvizity pro integrační testy

Integrační testy vyžadují běžící MongoDB na `localhost:27017` s přihlašovacími údaji z `conf/dict.yml`. Testy používají izolovanou databázi `dictionaries_test` — produkční data jsou oddělena.

### Spuštění testů

```bash
# Všechny integrační testy
.venv/Scripts/python.exe -m pytest tests/integration/ -v

# Jen ODM testy (rychlejší, bez HTTP vrstvy)
.venv/Scripts/python.exe -m pytest tests/integration/test_odm.py -v

# Jen API testy
.venv/Scripts/python.exe -m pytest tests/integration/test_api.py -v

# Unit testy (bez MongoDB)
.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/integration -v

# S měřením pokrytí
.venv/Scripts/python.exe -m pytest tests/integration/ --cov=api --cov-report=term-missing
```

> **Poznámka k timeoutu:** Celá testovací sada trvá 10–15 sekund. Spouštějte testy po jednom souboru pokud MCP nástroj má krátký timeout.

### Struktura testů

```
tests/
├── __init__.py
├── conftest.py               # sdílené fixtures (bez DB)
├── test_paging.py            # unit: paging_to_mongo()
├── test_commons.py           # unit: create_query(), update_changed_values()
├── test_models.py            # unit: Pydantic modely
├── test_dependencies.py      # unit: import_data() (mockované DB)
├── test_public_router.py     # unit: public router (mockované DB)
├── test_admins_router.py     # unit: admins router (mockované DB)
└── integration/
    ├── __init__.py
    ├── conftest.py           # fixtures s reálnou MongoDB
    ├── test_odm.py           # ODM operace (25 testů)
    └── test_api.py           # API end-to-end (38 testů)
```

### Izolace integračních testů

Každý test dostane vlastní event loop a čerstvé Beanie inicializované spojení.
Fixture `beanie_db` (function scope) před a po každém testu vymaže kolekci:

```python
@pytest_asyncio.fixture
async def beanie_db():
    client = AsyncMongoClient(MONGO_CONNECTION_STRING)
    await client["dictionaries_test"]["descriptor"].delete_many({})
    await init_beanie(database=client["dictionaries_test"],
                      document_models=[DbDescriptor, DbDescriptorSav])
    yield client["dictionaries_test"]
    await client["dictionaries_test"]["descriptor"].delete_many({})
    await client.close()
```

### Integrační testy — přehled pokrytí

**`test_odm.py` (25 testů):**

| Třída | Testuje |
|-------|---------|
| `TestDbDescriptorInsertAndFind` | Insert, vyhledání, key_alt, version, timestamp |
| `TestDbDescriptorActivate` | Aktivace/deaktivace, inkrementace version |
| `TestDbDescriptorReplace` | Aktualizace hodnot, inkrementace version |
| `TestDbDescriptorDelete` | Smazání záznamu |
| `TestDbDescriptorExport` | export_all, export_dictionary, dictionary_list |
| `TestDbDescriptorDocument` | Property `document` → DescriptorType |
| `TestDbDescriptorByQuery` | Filtrace, limit, skip, prázdný výsledek |
| `TestDbDescriptorByIdentifier` | Vyhledání/nenalezení podle identifier |

**`test_api.py` (38 testů):**

| Třída | Testuje |
|-------|---------|
| `TestPublicGet` | GET /descriptor/{dict}/{key}, 404, key_alt |
| `TestAdminPost` | Vytvoření, 409, autentizace, prázdný klíč |
| `TestAdminDelete` | Smazání, 404, autentizace |
| `TestAdminPatch` | Aktivace/deaktivace, 404 |
| `TestAdminPut` | Aktualizace, 404, nesoulad klíče |
| `TestExport` | Export všeho, export slovníku, prázdné 404 |
| `TestImport` | JSON import, reject duplicit, replace flag |
| `TestImportDomino` | Domino formát, replace, chybějící slovník |
| `TestPublicList` | Filtr, stránkování, limit není omezený na 10 |
| `TestInfoEndpoints` | GET /, HEAD /, HEAD /info, GET /info |

## Pokrytí kódu

Aktuální stav (63 integračních testů):

| Soubor | Pokrytí | Poznámka |
|--------|---------|---------|
| `api/model/dictionary.py` | **100 %** | Plně pokryto |
| `api/routers/public.py` | **91 %** | Defensivní null-check Path parametrů (mrtvý kód) |
| `api/commons.py` | **89 %** | Chybí test s `lang` parametrem a nested dict v PUT |
| `api/dependencies.py` | **87 %** | Chybí test výjimky při `insert_one` |
| `api/routers/admins.py` | **81 %** | Defensivní null-checky + error branch importu |
| `api/main.py` | **69 %** | Lifespan záměrně mockován, nelze snadno testovat |
| `api/model/odm.py` | **55 %** | Třída `DbDescriptorSav` bez testů |
| **CELKEM** | **72 %** | |

### Oblasti s nízkým pokrytím

**`DbDescriptorSav` (odm.py ~55 %)**
Konsolidační workflow, UUID→str konverze, `consolidated` property a `all_documents()` nemají integrační testy. Viz [#TODO: odkaz na testovací plán].

**`api/main.py` (~69 %)**
Lifespan hook (startup/shutdown) je v testech záměrně mockován — nelze testovat bez skutečného FastAPI spuštění s vlastním event loop.

## Přidávání nových testů

Nový integrační test v `tests/integration/test_odm.py`:

```python
class TestDbDescriptorSavConsolidation:

    async def test_consolidated_property_converts_uuid_to_str(self, beanie_db):
        # Vložit záznam s UUID identifikátorem přímo přes pymongo
        from uuid import uuid4
        raw_uuid = uuid4()
        await beanie_db["descriptor"].insert_one({
            "identifier": raw_uuid,
            "key": "TEST", "key_alt": "", "dictionary": "test_dict",
            "active": True, "values": [], "version": 1,
            "is_consolidated": None
        })

        # Načíst přes DbDescriptorSav a ověřit konverzi
        items = await DbDescriptorSav.all_documents()
        assert len(items) == 1
        consolidated = items[0].consolidated
        assert consolidated is not None
        assert isinstance(consolidated.identifier, str)
        assert consolidated.identifier == str(raw_uuid)
        assert consolidated.is_consolidated is True
```

## Styl kódu

- Pouze asynchronní kód (`async/await`) — žádné synchronní blokující operace
- Python 3.13, Pydantic v2, Beanie 1.29+
- Pouze `pymongo >= 4.0` jako MongoDB driver — **ne Motor ani Motor-like wrappery**
- Type hints povinné pro všechny veřejné funkce a metody
- Formátování: PEP 8 (bez striktního linteru, ale dodržovat konzistenci s okolím)
