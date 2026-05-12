# Verzování Docker images — SYSNET Managed Dictionaries

## Schéma verzování

Projekt používá [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`:

| Segment | Kdy se zvyšuje |
|---------|----------------|
| `MAJOR` | Změna breaking API (nekompatibilní s předchozí verzí) |
| `MINOR` | Nové funkce, zpětně kompatibilní |
| `PATCH` | Opravy chyb, zpětně kompatibilní |

## Jediný zdroj pravdy — soubor `VERSION`

Aktuální verze je vždy uložena v souboru `VERSION` v kořeni repozitáře:

```
2.0.2
```

Tento soubor čtou:
- `build.sh` — pro tagování Docker image
- `init.py` — jako fallback (přebíjí ho env proměnná `DICT_VERSION`)
- `docker/.env` — musí být ručně synchronizován při vydání nové verze

## Tagovací strategie

Každý release vytvoří čtyři tagy stejného image:

```
sysnetcz/dictionaries:2.1.3   ← přesná verze (immutable)
sysnetcz/dictionaries:2.1     ← nejnovější patch tohoto minor (mutable)
sysnetcz/dictionaries:2       ← nejnovější minor tohoto major (mutable)
sysnetcz/dictionaries:latest  ← nejnovější stabilní verze (mutable)
```

Klienti, kteří potřebují stabilitu, používají `2.1.3`. Klienti přijímající
automatické patch-updaty používají `2.1`.

## Vydání nové verze

### 1. Změňte `VERSION` soubor

```bash
echo "2.1.0" > VERSION
```

### 2. Aktualizujte `docker/.env`

```
DICT_VERSION=2.1.0
```

### 3. Commitněte a otagujte v gitu

```bash
git add VERSION docker/.env
git commit -m "chore: release 2.1.0"
git tag -a v2.1.0 -m "Release 2.1.0"
git push origin main --tags
```

### 4. Sestavte a pushněte image

```bash
./build.sh --push
```

Skript automaticky přečte `VERSION`, sestaví image a pushne všechny čtyři tagy.

## Použití `build.sh`

```bash
# Lokální sestavení (bez push)
./build.sh

# Sestavení a push do Docker Hub
./build.sh --push

# Vlastní registr
./build.sh --registry ghcr.io/sysnetcz --push

# Přebít verzi (bez úpravy VERSION souboru)
./build.sh --version 2.1.0-rc1 --no-latest

# Multi-arch build (vyžaduje docker buildx)
./build.sh --platform linux/amd64,linux/arm64 --push

# Nápověda
./build.sh --help
```

### Argumenty

| Argument | Popis |
|----------|-------|
| `--push` | Po sestavení pushne všechny tagy do registru |
| `--no-latest` | Netvoří tag `:latest` |
| `--registry <url>` | Prefix registru, např. `ghcr.io/sysnetcz` |
| `--version <ver>` | Přebije verzi z `VERSION` souboru |
| `--platform <list>` | Cílové platformy pro `docker buildx` |

## Dockerfile — build argumenty

`Dockerfile` přijímá tři `ARG` hodnoty pro OCI labely:

| ARG | Popis | Nastavuje |
|-----|-------|-----------|
| `DICT_VERSION` | Verze aplikace | `build.sh` z `VERSION` souboru |
| `BUILD_DATE` | Datum sestavení (ISO 8601) | `build.sh` automaticky |
| `VCS_REF` | Git commit hash (short) | `build.sh` z `git rev-parse` |

Tyto hodnoty jsou zapsány jako OCI standard labely (`org.opencontainers.image.*`)
a jsou dostupné přes:

```bash
docker inspect sysnetcz/dictionaries:2.1.0 \
  --format '{{json .Config.Labels}}' | jq
```

Příklad výstupu:
```json
{
  "org.opencontainers.image.version": "2.1.0",
  "org.opencontainers.image.created": "2026-05-12T10:00:00Z",
  "org.opencontainers.image.revision": "a1b2c3d",
  "org.opencontainers.image.vendor": "SYSNET s.r.o."
}
```

## Přehled souborů

```
VERSION                     ← aktuální verze (2.0.2)
build.sh                    ← build a tag skript
Dockerfile                  ← připnutý python:3.13-slim, ARG DICT_VERSION
docker/.env                 ← konfigurace pro docker-compose (DICT_VERSION musí souhlasit)
docker/.env.template        ← šablona pro nová prostředí
docker/docker-compose.yml   ← používá ${DICT_VERSION} z .env
```

## Pořadí priority pro hodnotu verze za běhu

```
DICT_VERSION env proměnná   (Docker: nastaveno v Dockerfile ENV nebo docker-compose)
        │
        └── pokud není nastavena: čte se soubor VERSION
                │
                └── pokud soubor neexistuje: fallback "0.0.0"
```

Při lokálním vývoji bez env proměnné se verze načte automaticky z `VERSION` souboru.
V Dockeru je `DICT_VERSION` vždy nastaveno přes `ENV` v Dockerfile (hodnota z `ARG`).
