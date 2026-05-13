# Import a export dat — SYSNET Managed Dictionaries

Všechny import a export operace vyžadují HTTP hlavičku `X-API-KEY`.

---

## Export

### Export jednoho slovníku

```
GET /export/{dictionary}
```

Vrátí všechny deskriptory daného slovníku seřazené podle klíče (`key`).

```bash
curl -H "X-API-KEY: vas-klic" \
     http://localhost:8000/export/country
```

**Odpověď — pole `DescriptorBaseType`:**

```json
[
  {
    "key": "AT",
    "key_alt": "AUT",
    "dictionary": "country",
    "active": true,
    "values": [
      { "lang": "cs", "value": "Rakousko", "value_alt": "Rakouská spolková republika" },
      { "lang": "en", "value": "Austria", "value_alt": null }
    ]
  },
  {
    "key": "CZ",
    "key_alt": "CZE",
    "dictionary": "country",
    "active": true,
    "values": [
      { "lang": "cs", "value": "Česko", "value_alt": "Česká republika" }
    ]
  }
]
```

> **Limit:** maximálně 1000 záznamů. Při překročení je výsledek oříznut a zalogován WARNING. Slovníky s více záznamy exportujte po částech přes `/descriptor/{dictionary}?skip=0&limit=1000`.

**Uložit do souboru:**

```bash
curl -H "X-API-KEY: vas-klic" \
     http://localhost:8000/export/country \
     -o country.json
```

---

### Export všech slovníků

```
GET /export
```

Vrátí všechny deskriptory ze všech slovníků v jednom poli.

```bash
curl -H "X-API-KEY: vas-klic" \
     http://localhost:8000/export \
     -o all-dictionaries.json
```

Formát odpovědi je totožný s `/export/{dictionary}` — pole `DescriptorBaseType` objektů
(pole `dictionary` v každém záznamu určuje příslušný slovník).

---

## Import — formát JSON

```
POST /import?replace=false
```

Hromadný import pole deskriptorů ve formátu JSON. Každý deskriptor se zpracuje samostatně.

### Query parametry

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `replace` | bool | `false` | Chování při kolizi klíče — viz níže |

### Chování při kolizi klíče

| `replace` | Klíč existuje | Výsledek |
|-----------|--------------|---------|
| `false` (default) | ano | Záznam **přeskočen** → `status: rejected` |
| `true` | ano | Záznam **přepsán** → `status: replaced` |
| — | ne | Záznam **vložen** → `status: added` |

### Formát těla požadavku

```json
[
  {
    "key":        "AT",
    "key_alt":    "AUT",
    "dictionary": "country",
    "active":     true,
    "values": [
      { "lang": "cs", "value": "Rakousko",  "value_alt": "Rakouská spolková republika" },
      { "lang": "en", "value": "Austria",   "value_alt": null }
    ]
  },
  {
    "key":        "CZ",
    "key_alt":    "CZE",
    "dictionary": "country",
    "active":     true,
    "values": [
      { "lang": "cs", "value": "Česko",     "value_alt": "Česká republika" },
      { "lang": "en", "value": "Czechia",   "value_alt": null }
    ]
  }
]
```

### Popis polí

| Pole | Typ | Povinné | Popis |
|------|-----|---------|-------|
| `key` | string | ✓ | Hlavní klíč deskriptoru — musí být unikátní v rámci slovníku |
| `key_alt` | string | | Alternativní klíč (synonymum); může být prázdný řetězec |
| `dictionary` | string | ✓ | Kód řízeného slovníku |
| `active` | bool | ✓ | `true` = aktivní položka |
| `values` | array | ✓ | Pole jazykových překladů; může být prázdné pole `[]` |
| `values[].lang` | string | ✓ | Kód jazyka, např. `cs`, `en`, `de` |
| `values[].value` | string | ✓ | Překlad klíče v daném jazyce |
| `values[].value_alt` | string | | Alternativní (delší) překlad; `null` pokud není |

### Příklad importu ze souboru

```bash
# Nejdříve zkuste bez replace — zobrazte co by se přepsalo
curl -X POST "http://localhost:8000/import?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @country.json

# Skutečný import s přepsáním existujících
curl -X POST "http://localhost:8000/import?replace=true" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @country.json
```

### Formát odpovědi

```json
{
  "count_added":    2,
  "count_replaced": 1,
  "count_rejected": 0,
  "count_error":    0,
  "added": [
    { "dictionary": "country", "key": "SK", "status": "added" },
    { "dictionary": "country", "key": "PL", "status": "added" }
  ],
  "replaced": [
    { "dictionary": "country", "key": "AT", "status": "replaced" }
  ],
  "rejected": [],
  "error":    []
}
```

### Hodnoty `status`

| Hodnota | Popis |
|---------|-------|
| `added` | Nový záznam úspěšně vložen |
| `replaced` | Existující záznam přepsán (`replace=true`) |
| `rejected` | Přeskočen — klíč existuje a `replace=false` |
| `failed` | Chyba při zpracování (viz `error` pole) |

---

## Import — formát Domino

```
POST /import/domino?replace=false
```

Import z jednoduchého textového formátu používaného systémem Domino.
Každý řádek obsahuje jednu položku ve formátu `Hodnota|klíč`.

### Query parametry

Stejné jako `/import` — parametr `replace`.

### Formát těla požadavku

```json
{
  "dictionary":     "permit_type",
  "value_key_text": "Průvodní dopis|pd\nObálka|ob\nFaktura|fk\nDovozní povolení|dp"
}
```

| Pole | Typ | Povinné | Popis |
|------|-----|---------|-------|
| `dictionary` | string | ✓ | Kód řízeného slovníku, do kterého se importuje |
| `value_key_text` | string | ✓ | Víceřádkový text — jeden záznam na řádek ve formátu `Hodnota\|klíč` |

### Formát řádku

```
Hodnota|klíč
```

Kde:
- část **před** `|` = hodnota (`value`) v jazyce `cs`
- část **za** `|` = klíč (`key`) deskriptoru

Nové záznamy jsou vždy vytvořeny s:
- `lang = "cs"`
- `key_alt = ""` (prázdný řetězec)
- `active = true`

### Příklad

Vstup:
```
Průvodní dopis|pd
Obálka|ob
Faktura|fk
Dovozní povolení|dp
```

Jako JSON:
```json
{
  "dictionary": "permit_type",
  "value_key_text": "Průvodní dopis|pd\nObálka|ob\nFaktura|fk\nDovozní povolení|dp"
}
```

Výsledné deskriptory:

```json
[
  { "key": "pd", "key_alt": "", "dictionary": "permit_type", "active": true,
    "values": [{ "lang": "cs", "value": "Průvodní dopis", "value_alt": "" }] },
  { "key": "ob", "key_alt": "", "dictionary": "permit_type", "active": true,
    "values": [{ "lang": "cs", "value": "Obálka", "value_alt": "" }] },
  ...
]
```

### Příklad curl

```bash
curl -X POST "http://localhost:8000/import/domino?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d '{
    "dictionary": "permit_type",
    "value_key_text": "Průvodní dopis|pd\nObálka|ob\nFaktura|fk"
  }'
```

---

## Typické scénáře

### Plná synchronizace slovníku ze souboru

```bash
# 1. Exportujte aktuální stav (záloha)
curl -H "X-API-KEY: vas-klic" http://localhost:8000/export/country -o country-backup.json

# 2. Importujte nová data (přepište existující)
curl -X POST "http://localhost:8000/import?replace=true" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @country-new.json
```

### Přenos slovníku mezi prostředími (staging → produkce)

```bash
# Na staging:
curl -H "X-API-KEY: staging-klic" \
     https://staging.api.sysnet.cz/dict/export/species \
     -o species.json

# Na produkci:
curl -X POST "https://api.sysnet.cz/dict/import?replace=false" \
  -H "X-API-KEY: prod-klic" \
  -H "Content-Type: application/json" \
  -d @species.json
```

### Hromadný export všech slovníků a reimport

```bash
# Export
curl -H "X-API-KEY: vas-klic" http://localhost:8000/export -o all.json

# Reimport (bez přepisování — jen doplní chybějící)
curl -X POST "http://localhost:8000/import?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @all.json
```

---

## Import — legacy formát (descriptor-service v1)

Pokud migrujete data ze starší verze služby (soubor `descriptor-service_1.json`), použijte jeden ze dvou legacy importních endpointů.

### Rozdíly oproti aktuálnímu formátu

| Pole | Starý formát | Nový formát |
|------|-------------|-------------|
| Překlad do češtiny | `"value": "Česko"` | `values: [{"lang": "cs", "value": "Česko", ...}]` |
| Anglický překlad | `"value_en": "Czechia"` | `values: [{"lang": "en", "value": "Czechia", ...}]` |
| Identifikátor | `"dictionary*key"` — ignorován | Nové UUID generováno automaticky |
| `_id` | MongoDB ObjectId — ignorován | Nové MongoDB `_id` |

### Varianta A — nahrání souboru (`POST /import/legacy/file`)

Přijímá soubor přímo jako multipart upload. Soubor `descriptor-service_1.json` je ve formátu NDJSON — každý řádek je samostatný JSON objekt.

```bash
curl -X POST "http://localhost:8000/import/legacy/file?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -F "file=@data/descriptor-service_1.json"
```

Endpoint automaticky:
- Stripuje BOM na začátku souboru (`utf-8-sig` dekódování)
- Ignoruje prázdné řádky
- Sanitizuje embedded U+FEFF (neviditelný BOM uvnitř textu) a okolní whitespace

### Varianta B — JSON pole (`POST /import/legacy`)

Pokud chcete odeslat data přímo jako JSON array (ne soubor):

```bash
# 1. Převeďte NDJSON → JSON array
python -c "
import sys, json
data = [json.loads(l) for l in open('data/descriptor-service_1.json') if l.strip()]
print(json.dumps(data))
" > /tmp/legacy_payload.json

# 2. Import
curl -X POST "http://localhost:8000/import/legacy?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -H "Content-Type: application/json" \
  -d @/tmp/legacy_payload.json
```

### Postup migrace

```bash
# 1. První průchod — bez replace, zjistíte co je nové vs. existující
curl -X POST "http://localhost:8000/import/legacy/file?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -F "file=@data/descriptor-service_1.json"

# Zkontrolujte count_added, count_rejected, count_error v odpovědi

# 2. Druhý průchod — s replace=true pro přepis existujících
curl -X POST "http://localhost:8000/import/legacy/file?replace=true" \
  -H "X-API-KEY: vas-klic" \
  -F "file=@data/descriptor-service_1.json"
```

Soubor `descriptor-service_1.json` obsahuje 757 záznamů ve 71 slovnících — vše pod limitem 1000, import proběhne v jednom požadavku.

---

## Omezení a poznámky

- **Limit exportu:** Endpointy `/export` a `/export/{dictionary}` vrátí maximálně 1000 záznamů. Při překročení limitu je výsledek oříznut a v logu se objeví `WARNING`. Pro větší slovníky stránkujte přes `/descriptor/{dictionary}?skip=0&limit=1000`.
- **Import po dávkách:** Při importu velkých souborů (stovky tisíc záznamů) zvažte rozdělení na menší dávky — každý záznam se zpracuje individuálně a výjimka v jednom záznamu nezastaví import dalších.
- **Klíče jsou case-sensitive:** `AT` a `at` jsou různé klíče. Ujistěte se o konzistenci před importem.
- **Hodnota `value_alt` může být `null`:** Pokud alternativní překlad neexistuje, použijte `null`, nikoliv prázdný řetězec — API obě hodnoty akceptuje, ale `null` je sémanticky správnější.
