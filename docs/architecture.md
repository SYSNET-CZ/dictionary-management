# Architektura — SYSNET Managed Dictionaries

## Přehled

SYSNET Managed Dictionaries je bezstavová RESTful API služba pro správu řízených slovníků (číselníků). Slouží jako sdílený centrální zdroj pravdy pro překladové tabulky a klasifikační číselníky napříč systémy SYSNET (primárně CITES Registry).

## Technologický stack

| Vrstva | Technologie | Verze |
|--------|-------------|-------|
| Runtime | Python (asynchronní) | 3.13 |
| REST framework | FastAPI | 0.115+ |
| Databáze | MongoDB | 6.0+ |
| ODM | Beanie | 1.29+ |
| MongoDB driver | pymongo (async) | 4.9+ |
| Validace dat | Pydantic | 2.x |
| Utility | sysnet-pyutils | 1.7.5+ |

## Strukturální přehled

```
┌──────────────────────────────────────────────────────────────────┐
│                          FastAPI app                              │
│                                                                  │
│  ┌──────────────────┐  ┌────────────────────┐  ┌──────────────┐ │
│  │  public router   │  │   admins router    │  │monitor router│ │
│  │  (bez auth)      │  │  (X-API-KEY)       │  │  (X-API-KEY) │ │
│  │                  │  │                    │  │              │ │
│  │  GET /descriptor │  │  POST/PUT/DELETE   │  │  GET /stats  │ │
│  │  GET /suggest    │  │  /descriptor       │  │  GET /health │ │
│  │  GET /info       │  │  /export, /import  │  │  GET /dict/  │ │
│  └────────┬─────────┘  └────────┬───────────┘  └──────┬───────┘ │
│           │                     │                      │         │
│           └─────────────────────┬──────────────────────┘         │
│                                 │                                 │
│                     ┌───────────▼──────────────┐                 │
│                     │    api/model/odm.py       │                 │
│                     │                          │                 │
│                     │  DbDescriptor            │                 │
│                     │  DbDescriptorSav         │                 │
│                     └───────────┬──────────────┘                 │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   MongoDB               │
                     │   kolekce "descriptor"  │
                     └─────────────────────────┘
```

## Klíčové moduly

### `init.py`

Centrální inicializace celé aplikace. Načítá se jako první — vytváří adresáře, konfiguruje logging, načítá `conf/dict.yml`.

Exportuje:
- `CONFIG` — konfigurační slovník (po sloučení s proměnnými prostředí)
- `CONTEXT` — singleton `Context` pro stav autentizace
- `MONGO_CONNECTION_STRING` — sestavený connection string z konfigurace
- `COLLATION` — MongoDB collation pro českou abecedu (`cs@collation=search`)
- `paging_to_mongo()` — převod stránkovacích parametrů na `skip`/`limit`
- `EXPORT_LIMIT` (v `odm.py`) — maximální počet záznamů při hromadném čtení (1000)

### `api/model/dictionary.py`

Pydantic v2 modely pro request/response serializaci. Žádná byznysová logika.

`DescriptorBaseType` dědí z `GlobalModel` (sysnet-pyutils ≥ 1.7.5), který přidává `@field_validator("*", mode="before")` normalizující všechna `datetime` pole na UTC — naivní hodnoty jsou nejprve lokalizovány jako Europe/Prague. Pravidlo se propaguje do `DescriptorType` → `DbDescriptor`.

### `api/model/odm.py`

Beanie ODM modely mapované na MongoDB kolekci `descriptor`. Obsahuje veškerou databázovou logiku. Viz [data-model.md](data-model.md).

### `api/routers/public.py`

Veřejné endpointy bez autentizace. Pouze čtení.

### `api/routers/admins.py`

Admin endpointy chráněné API klíčem. Zápis, mazání, import, export.

### `api/routers/monitor.py`

Monitoring endpointy chráněné API klíčem. Tři endpointy:

- `GET /monitor/stats?hours=24` — agregované statistiky kolekce (celkové součty, per-slovník breakdown, nedávno přidané/upravené záznamy). Tři aggregation pipeline dotazy v jednom požadavku.
- `GET /monitor/health` — stav MongoDB a detaily kolekce (počet dokumentů, indexy). Vrátí `200` i při stavu RED; stav je v těle odpovědi. Indexy čte přes `get_pymongo_collection().index_information()`.
- `GET /monitor/dict/{dictionary}` — detailní statistiky jednoho slovníku plus ukázka 10 naposledy upravených klíčů.

Pomocné funkce sdílené routerem: `_check_auth()`, `_check_mongo()` (503 pokud `CONFIG['mongo']['status'] != 'GREEN'`), `_aggregate()` (wrapper nad `find({}).aggregate().to_list()` s logováním chyb).

### `api/model/admin.py`

Pydantic modely pro monitoring endpointy: `AdminStatsOut`, `AdminHealthOut`, `DictionaryDetailOut`, `DictionaryBreakdown`, `IndexInfo`.

### `api/commons.py`

Pomocné funkce sdílené routery:
- `create_query()` — sestaví MongoDB query filtr z HTTP parametrů; výchozí řazení je `key ASC`
- `update_changed_values()` — in-place aktualizace Pydantic objektu z diff slovníků

### `api/dependencies.py`

FastAPI závislosti (Depends):
- `header_scheme` — čte hlavičku `X-API-KEY`
- `is_api_authorized()` — ověří klíč vůči konfiguraci
- `import_data()` — jádro importní logiky (sdíleno mezi `/import` a `/import/domino`)

## Dvojí ODM pohled na jednu kolekci

Kolekce `descriptor` je přistupována ze dvou Beanie tříd:

```
kolekce "descriptor"
        │
        ├── DbDescriptor     (identifier: str)   ← konsolidovaná data
        │                    is_consolidated = True
        │
        └── DbDescriptorSav  (identifier: UUID)  ← legacy data (starší verze)
                             is_consolidated = None / False
```

Starší verze služby ukládala `identifier` jako nativní MongoDB UUID (BinData subtype 4). Nová verze používá `str`. Pole `is_consolidated` slouží jako příznak, zda byl dokument převeden. Viz [consolidation.md](consolidation.md).

## Autentizace

Admin operace jsou chráněny API klíčem předávaným v HTTP hlavičce `X-API-KEY`. Klíče jsou uloženy v `conf/dict.yml` pod agendou `dict.api_keys`. Každý klíč je mapován na popisek uživatele (pro audit log).

Ověřování probíhá přes singleton `Context`, který při úspěchu uloží aktivní API klíč, agendu a jméno uživatele.

## Stránkování

`paging_to_mongo()` v `init.py` podporuje dva styly volání:

**skip/limit styl** (používaný v routerech):
```
skip=20, limit=10  →  přeskoč 20, vrať 10
```

**start/page/pagesize styl** (legacy):
```
page=2, page_size=10  →  skip=20, limit=10
```

Default: `skip=0`, `limit=10` (`PAGE_SIZE`).

## Limity hromadného čtení

Metody `get_by_dictionary()`, `export_dictionary()`, `export_all()` pracují s limitem `EXPORT_LIMIT = 1000`. Interně se dotazují na `EXPORT_LIMIT + 1` dokumentů — pokud přijde víc než limit, výsledek se ořízne na 1000 a do logu se zapíše `WARNING`. Tím se odlišuje kolekce s přesně 1000 záznamy od skutečného překročení limitu.

## Indexy MongoDB

Kolekce `descriptor` má tyto indexy (definované v `Settings.indexes`):

| Název | Pole | Vlastnosti |
|-------|------|-----------|
| `idx_key` | `key ASC` | CS collation |
| `idx_dictionary` | `dictionary ASC` | — |
| `idx_dict_key` | `(dictionary, key) ASC` | — |
| `idx_identifier` | `identifier ASC` | — |
| `idx_wildcard` | `$** ASC` | CS collation |
| `idx_text` | `key, key_alt, dictionary, values.value, values.value_alt` | fulltext |

## Logging

Tři RotatingFileHandler handlery (adresář `logs/` nebo `$LOG_DIR`):

| Soubor | Úroveň | Max. velikost |
|--------|--------|---------------|
| `dict.log` | INFO+ | 500 KB × 10 |
| `dict-debug.log` | DEBUG+ | 1 MB × 10 |
| `dict-error.log` | WARN+ | — |

Úroveň root loggeru: `DEBUG` při `INSTANCE=DEV`, jinak `INFO`.

## Životní cyklus aplikace

FastAPI lifespan hook (`api/main.py`):

1. Vytvoří `AsyncMongoClient`
2. Provede `ping` na databázi — při selhání nastaví stav `RED` a vyhodí výjimku
3. Inicializuje Beanie (`init_beanie`) s dokumentovým modelem `DbDescriptor`
4. Nastaví stav `GREEN` v `CC.config['mongo']['status']`
5. Při shutdown nastaví stav `RED` a zavře klientské spojení

## Typeahead / autocomplete

Endpoint `GET /suggest/{dictionary}` je dedikovaný našeptávač. Klíčové vlastnosti:

- Používá **zakotvený regex** `^prefix` — MongoDB může využít B-tree index na rozdíl od unanchored regexu, který způsobuje collection scan.
- Hledá v `values.value`, `key` a `key_alt` (unií přes `$or`).
- Vždy filtruje `active=True` — deaktivované záznamy se v návrzích nikdy neobjeví.
- Výsledky jsou seřazeny abecedně (`key ASC`).
- Limit 1–50, výchozí 15. Parametr `prefix` je povinný (min. 1 znak), `lang` volitelný.
- Implementováno jako `DbDescriptor.suggest()` v ODM vrstvě.

Kontrast se starším `GET /descriptor/{dictionary}?query=…`: ten používá `$text` search, který provádí tokenizaci na celá slova — není vhodný pro realtime typeahead (nefunguje pro neúplná slova). Je vhodný pro fulltextové vyhledávání.

## Import endpointy

Služba poskytuje tři import endpointy, všechny chráněné API klíčem:

| Endpoint | Formát vstupu | Určení |
|----------|---------------|--------|
| `POST /import` | `List[DescriptorBaseType]` — aktuální formát s `values` strukturou | Standardní import |
| `POST /import/domino` | `DominoImport` — plain-text `hodnota\|klíč` odřádkovaný seznam | Import z Domino systému |
| `POST /import/legacy` | `List[LegacyDescriptorImport]` — starý formát s flat `value`/`value_en` jako JSON pole | Jednorázový import ze staré verze |
| `POST /import/legacy/file` | multipart `UploadFile` — soubor NDJSON (jeden JSON objekt na řádek) | Import ze souboru `descriptor-service_1.json` |

Všechny endpointy sdílejí query parametr `replace: bool = false`. Při `replace=false` jsou existující záznamy odmítnuty (status `rejected`), při `replace=true` přepsány.

Jádro importní logiky je funkce `import_data()` v `api/dependencies.py`. Pracuje s `DescriptorBaseType` — endpointy `/import/domino` a `/import/legacy` transformují svůj vstupní formát před předáním.

### Legacy import (descriptor-service v1)

Starý formát exportu (soubor `data/descriptor-service_1.json`) se liší od aktuálního modelu ve třech bodech:

1. **Struktura hodnot** — flat pole `value` (cs) a `value_en` (en) místo `values: [{lang, value, value_alt}]`
2. **Identifikátor** — řetězec `"dictionary*key"` místo UUID; nová verze generuje vlastní UUID, starý identifikátor je ignorován
3. **`_id`** — MongoDB Extended JSON `{"$oid": "..."}` je ignorováno

Model `LegacyDescriptorImport` (`api/model/dictionary.py`) zapouzdřuje transformaci. Metoda `to_descriptor_base()` převádí flat formát na `DescriptorBaseType`. Pydantic `@field_validator` sanitizuje U+FEFF (BOM) a whitespace ze všech string polí — v `descriptor-service_1.json` je jeden záznam se slovníkem `"noti﻿ce_roles"` (ef bb bf v UTF-8, neviditelné v editorech).

**Postup jednorázového importu:**

```bash
# 1. Transformace JSON Lines → JSON array
python -c "
import sys, json
data = [json.loads(l) for l in open('data/descriptor-service_1.json') if l.strip()]
print(json.dumps(data))
" > /tmp/legacy_payload.json

# 2. Import (první průchod bez replace — vidíme co je nové)
curl -X POST "http://localhost:8000/import/legacy?replace=false" \
  -H "X-API-KEY: <key>" \
  -H "Content-Type: application/json" \
  -d @/tmp/legacy_payload.json

# 3. Případný druhý průchod s replace=true pro přepis existujících
```

Celkem 757 záznamů ve 71 slovnících — pod limitem `EXPORT_LIMIT=1000`, takže import proběhne v jednom požadavku.
