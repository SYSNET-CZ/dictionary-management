# Technická dokumentace — SYSNET Managed Dictionaries API

> Tato stránka je stručný technický přehled pro vývojáře.
> Detailní dokumentace je rozdělena do samostatných souborů — viz [README.md](README.md).

## Přehled architektury

```
FastAPI app
  public router (bez auth)  +  admins router (X-API-KEY required)
                │                         │
                └──────────┬──────────────┘
                           │
                    DbDescriptor (Beanie ODM)
                           │
                  MongoDB kolekce "descriptor"
```

Viz [architecture.md](architecture.md) pro kompletní popis.

## Klíčové soubory

| Soubor | Popis |
|--------|-------|
| `init.py` | Konfigurace, logging, MongoDB connection string |
| `api/main.py` | FastAPI app, lifespan hook, exception handler |
| `api/model/dictionary.py` | Pydantic modely (request/response) |
| `api/model/odm.py` | Beanie ODM třídy (`DbDescriptor`, `DbDescriptorSav`) |
| `api/routers/public.py` | Veřejné endpointy (čtení, bez auth) |
| `api/routers/admins.py` | Admin endpointy (zápis, auth X-API-KEY) |
| `api/commons.py` | `create_query()`, `update_changed_values()` |
| `api/dependencies.py` | `is_api_authorized()`, `import_data()` |
| `sprint1.py` | Konsolidační skript (UUID → str migrace) |
| `conf/dict.yml` | API klíče, databáze, hesla |

## API endpointy — rychlý přehled

Viz [api.md](api.md) pro kompletní referenci s příklady.

### Veřejné (bez auth)

| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/` | Info o aplikaci |
| GET | `/info` | Servisní stav |
| GET | `/descriptor/{dictionary}/{key}` | Jeden deskriptor |
| GET | `/descriptor/{dictionary}` | Prohledávání / autocomplete |

### Admin (X-API-KEY)

| Metoda | Cesta | Popis |
|--------|-------|-------|
| POST | `/descriptor/{dictionary}` | Vytvoří deskriptor |
| PUT | `/descriptor/{dictionary}/{key}` | Aktualizuje deskriptor |
| DELETE | `/descriptor/{dictionary}/{key}` | Smaže deskriptor |
| PATCH | `/descriptor/activate/{dictionary}/{key}` | Aktivuje/deaktivuje |
| GET | `/export` | Export všeho |
| GET | `/export/{dictionary}` | Export jednoho slovníku |
| POST | `/import` | Hromadný import (JSON) |
| POST | `/import/domino` | Import Domino formátu |

## Datový model

Viz [data-model.md](data-model.md).

## Konsolidace legacy dat

Viz [consolidation.md](consolidation.md).

## Konfigurace

Viz [configuration.md](configuration.md).

## Vývoj a testování

Viz [development.md](development.md).

## Provoz

Viz [operations.md](operations.md).
