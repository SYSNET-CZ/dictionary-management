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

## Strukturální přehled

```
┌─────────────────────────────────────────────────────────┐
│                        FastAPI app                       │
│                                                         │
│  ┌──────────────────┐   ┌─────────────────────────────┐ │
│  │  public router   │   │       admins router         │ │
│  │  (bez auth)      │   │  (vyžaduje X-API-KEY)       │ │
│  │                  │   │                             │ │
│  │  GET /descriptor │   │  POST/PUT/DELETE /descriptor│ │
│  │  GET /info       │   │  GET/POST /export, /import  │ │
│  └────────┬─────────┘   └──────────────┬──────────────┘ │
│           │                            │                 │
│           └──────────────┬─────────────┘                 │
│                          │                               │
│              ┌───────────▼──────────────┐                │
│              │    api/model/odm.py      │                │
│              │                         │                 │
│              │  DbDescriptor           │                 │
│              │  DbDescriptorSav        │                 │
│              └───────────┬─────────────┘                 │
└──────────────────────────┼─────────────────────────────-─┘
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

### `api/model/odm.py`

Beanie ODM modely mapované na MongoDB kolekci `descriptor`. Obsahuje veškerou databázovou logiku. Viz [data-model.md](data-model.md).

### `api/routers/public.py`

Veřejné endpointy bez autentizace. Pouze čtení.

### `api/routers/admins.py`

Admin endpointy chráněné API klíčem. Zápis, mazání, import, export.

### `api/commons.py`

Pomocné funkce sdílené routery:
- `create_query()` — sestaví MongoDB query filtr z HTTP parametrů
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
