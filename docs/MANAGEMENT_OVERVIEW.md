# Manažerský přehled — SYSNET Managed Dictionaries

## Co systém dělá

SYSNET Managed Dictionaries je RESTful API služba pro centrální správu řízených slovníků (číselníků). Slouží jako sdílený zdroj pravdy pro překladové tabulky a klasifikační číselníky napříč systémy SYSNET.

Typické použití: číselník států, druhů, typů dokladů, klasifikací CITES a podobně.

## Klíčové funkce

**Čtení slovníků (bez omezení)**
- Klienti mohou získat libovolnou položku slovníku podle kódu
- Podpora fulltextového hledání a autocomplete pro uživatelská rozhraní
- Stránkování výsledků
- Filtrování podle jazyka a stavu (aktivní/neaktivní)

**Správa slovníků (pro oprávněné uživatele)**
- Přidávání, úprava a mazání položek
- Aktivace a deaktivace položek bez ztráty dat
- Hromadný import z JSON nebo textového formátu (Domino)
- Export celého slovníku nebo všech dat jako JSON

## Technický stack

| Komponenta | Technologie | Verze |
|------------|-------------|-------|
| Programovací jazyk | Python (asynchronní) | 3.13 |
| REST framework | FastAPI | 0.115+ |
| Databáze | MongoDB | 6.0+ |
| ODM | Beanie | 1.29+ |
| MongoDB driver | pymongo (async) | 4.9+ |
| Kontejnerizace | Docker / Docker Compose | — |

## Bezpečnost

Přístup k admin operacím (zápis, mazání, import, export) je chráněn API klíči.
Veřejné čtecí operace nevyžadují autentizaci.

API klíče jsou uloženy v konfiguraci na serveru, nikoliv v kódu.
Každý klientský systém má vlastní klíč pro auditní záznamy.

## Dostupnost a monitoring

Služba exponuje endpoint `/info` vracející stav:
- `GREEN` — služba a databáze v pořádku
- `RED` — problém s připojením k databázi

Docker kontejner má vestavěnou zdravotní kontrolu (HEALTHCHECK).
Doporučeno monitorovat `/info` v 1minutových intervalech.

## Provozní požadavky

- Server s Dockerem nebo Python 3.13+
- MongoDB instance (lokální nebo vzdálená)
- Sdílený volume pro logy a zálohy
- Reverzní proxy (nginx, Traefik) pro HTTPS a path routing

## Rozšiřitelnost

Služba je navržena bez stavovosti (stateless) — lze provozovat více instancí
za load balancerem. MongoDB zajišťuje konzistenci dat.

Každá operace loguje kdo, kdy a co změnil (API klíč + timestamp).

## Dokumentace

| Dokument | Určen pro |
|----------|-----------|
| [USER_GUIDE.md](USER_GUIDE.md) | Klienti API — čtení slovníků |
| [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | Správci — správa slovníků, instalace |
| [import-export.md](import-export.md) | Správci — detailní průvodce importem a exportem |
| [TECHNICAL.md](TECHNICAL.md) | Vývojáři — technický přehled |
| [architecture.md](architecture.md) | Vývojáři — architektura systému |
| [consolidation.md](consolidation.md) | Vývojáři/správci — migrace dat |

## Podpora a kontakt

SYSNET s.r.o.
Web: [https://sysnet.cz](https://sysnet.cz)
Email: info@sysnet.cz
Licence: GNU AGPL v3.0
