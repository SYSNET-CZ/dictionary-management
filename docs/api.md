# REST API Reference — SYSNET Managed Dictionaries

Základní URL závisí na konfiguraci `DICT_ROOT_PATH` (default: `dict`).
Příklady používají `http://localhost:8000`.

## Autentizace

Admin endpointy vyžadují HTTP hlavičku:

```
X-API-KEY: <api-klíč>
```

Chybějící klíč vrátí `401 Unauthorized`, neplatný klíč `403 Forbidden`.

---

## Info endpointy

### `GET /`

Základní informace o aplikaci.

**Odpověď `200`:**
```json
{
  "name": "SYSNET Managed Dictionaries API",
  "version": "2.0.1"
}
```

---

### `HEAD /`

Zdravotní check — vrátí `200` pokud aplikace běží.

---

### `GET /info`

Servisní stav včetně stavu databáze a seznamu slovníků.

**Odpověď `200`:**
```json
{
  "status": "GREEN",
  "mongo": { "status": "GREEN" },
  "dictionaries": [
    { "dictionary": "country", "count": 249 },
    { "dictionary": "species", "count": 1042 }
  ]
}
```

Možné hodnoty `status`:
- `GREEN` — MongoDB dostupná, vše v pořádku
- `RED` — problém s připojením k databázi

---

### `HEAD /info`

Dostupnost služby bez těla odpovědi — vhodné pro load balancer healthcheck.

---

## Veřejné endpointy (bez autentizace)

### `GET /descriptor/{dictionary}/{key}`

Vrátí jeden deskriptor podle slovníku a klíče. Hledá jak v `key`, tak v `key_alt`.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku, např. `country` |
| `key` | string | Kód deskriptoru, např. `AT` |

**Odpověď `200`:**
```json
{
  "identifier": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "key": "AT",
  "key_alt": "AUT",
  "dictionary": "country",
  "active": true,
  "values": [
    { "lang": "cs", "value": "Rakousko", "value_alt": "Rakouská spolková republika" },
    { "lang": "en", "value": "Austria", "value_alt": null }
  ]
}
```

**Chyby:** `404` pokud deskriptor neexistuje.

---

### `GET /descriptor/{dictionary}`

Prohledává slovník s podporou stránkování, fulltext i regex filtrů. Vhodné pro obecné listování; pro typeahead viz `GET /suggest/{dictionary}`.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku |

**Query parametry:**

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `query` | string | — | Fulltext hledání (`$text`) — celá slova, nikoliv prefixy |
| `key` | string | — | Unanchored regex v `key`, `key_alt` a `values.value` |
| `lang` | string | — | Filtr jazyka hodnot, např. `cs` |
| `active` | bool | — | `true` = jen aktivní, `false` = jen neaktivní |
| `skip` | int | `0` | Přeskočit N výsledků |
| `limit` | int | `10` | Max. počet výsledků |

> **Poznámka k `query`:** Parametr `query` používá MongoDB `$text` search, který tokenizuje na celá slova. `?query=Rak` tudíž **nenajde** „Rakousko" — `$text` není vhodný pro živý typeahead. Pro prefix-matching použijte `GET /suggest/{dictionary}`.

**Odpověď `200`:** seznam `DescriptorType` objektů (stejná struktura jako u GET jednoho deskriptoru), seřazený abecedně podle `key`.

**Chyby:** `404` pokud nic nebylo nalezeno.

---

### `GET /suggest/{dictionary}`

**Dedikovaný typeahead endpoint.** Vrátí deskriptory začínající zadaným prefixem. Používá zakotvený regex `^prefix` pro efektivní využití B-tree indexu. Vždy filtruje pouze aktivní záznamy.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku |

**Query parametry:**

| Parametr | Typ | Default | Povinný | Popis |
|----------|-----|---------|---------|-------|
| `prefix` | string | — | ✓ | Předpona pro vyhledání (min. 1 znak) |
| `lang` | string | — | | Filtrovat hodnoty podle jazyka, např. `cs` |
| `limit` | int | `15` | | Maximální počet výsledků (1–50) |

**Příklad — typeahead na „Rak":**
```
GET /suggest/country?prefix=Rak&lang=cs
```

**Odpověď `200`:** pole `DescriptorType` objektů seřazených abecedně podle `key`.

**Chyby:** `404` pokud nic nebylo nalezeno, `422` při nevalidních parametrech (chybějící `prefix`, `limit` mimo rozsah 1–50).

---

## Admin endpointy (vyžadují `X-API-KEY`)

### `POST /descriptor/{dictionary}`

Vytvoří nový deskriptor. Vrátí `409` pokud klíč ve slovníku již existuje.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku |

**Tělo požadavku:**
```json
{
  "key": "SK",
  "key_alt": "SVK",
  "dictionary": "country",
  "active": true,
  "values": [
    { "lang": "cs", "value": "Slovensko", "value_alt": "Slovenská republika" },
    { "lang": "en", "value": "Slovakia", "value_alt": null }
  ]
}
```

**Odpověď `200`:** plný `DescriptorType` včetně vygenerovaného `identifier`.

**Chyby:** `400` chybějící klíč nebo slovník, `409` deskriptor již existuje.

---

### `PUT /descriptor/{dictionary}/{key}`

Aktualizuje existující deskriptor. Přepíše všechna pole předaná v těle.

**Path parametry:** stejné jako POST.

**Tělo požadavku:** stejná struktura jako POST. Pole `key` v těle musí souhlasit s `key` v cestě (nebo může být vynecháno — doplní se automaticky).

**Odpověď `200`:** aktualizovaný `DescriptorType`.

**Chyby:** `400` nesoulad klíčů, `404` deskriptor neexistuje.

---

### `DELETE /descriptor/{dictionary}/{key}`

Odstraní deskriptor ze slovníku.

**Odpověď `200`:** `true` při úspěchu.

**Chyby:** `404` deskriptor neexistuje.

---

### `PATCH /descriptor/activate/{dictionary}/{key}`

Aktivuje nebo deaktivuje deskriptor (mění pole `active`) bez jiných změn dat.

**Query parametry:**

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `doit` | bool | `true` | `true` = aktivovat, `false` = deaktivovat |

**Odpověď `200`:** aktualizovaný `DescriptorType`.

**Chyby:** `404` deskriptor neexistuje.

---

### `GET /export`

Exportuje všechny deskriptory ze všech slovníků jako JSON pole.

> **Limit:** maximálně 1000 záznamů. Při překročení je výsledek oříznut a zalogován `WARNING`.

**Odpověď `200`:** pole `DescriptorBaseType` (bez `identifier`).

**Chyby:** `404` žádná data neexistují.

---

### `GET /export/{dictionary}`

Exportuje všechny deskriptory jednoho slovníku, seřazené podle `key`.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku |

**Odpověď `200`:** pole `DescriptorBaseType` (bez `identifier`).

**Chyby:** `404` slovník neexistuje nebo je prázdný.

**Příklad — export slovníku `country` do souboru:**
```bash
curl -H "X-API-KEY: vas-klic" \
     http://localhost:8000/export/country \
     > country.json
```

---

### `POST /import?replace=false`

Hromadný import deskriptorů z JSON pole. Každý deskriptor se zpracuje samostatně.

**Query parametry:**

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `replace` | bool | `false` | `true` = přepsat existující, `false` = přeskočit |

**Tělo požadavku:** pole `DescriptorBaseType` objektů:
```json
[
  {
    "key": "AT", "key_alt": "AUT", "dictionary": "country", "active": true,
    "values": [{ "lang": "cs", "value": "Rakousko", "value_alt": null }]
  },
  {
    "key": "DE", "key_alt": "DEU", "dictionary": "country", "active": true,
    "values": [{ "lang": "cs", "value": "Německo", "value_alt": null }]
  }
]
```

**Odpověď `200`:**
```json
{
  "count_added": 1,
  "count_replaced": 0,
  "count_rejected": 1,
  "count_error": 0,
  "added":    [{ "dictionary": "country", "key": "DE", "status": "added" }],
  "replaced": [],
  "rejected": [{ "dictionary": "country", "key": "AT", "status": "rejected" }],
  "error":    []
}
```

Hodnoty `status`:
- `added` — vložen jako nový
- `replaced` — přepsán (jen při `replace=true`)
- `rejected` — přeskočen, klíč již existuje (při `replace=false`)
- `failed` — chyba při zpracování

**Chyby:** `400` prázdné tělo.

---

### `POST /import/domino?replace=false`

Import z Domino textového formátu. Každý řádek má formát `Hodnota|klíč`.

**Query parametry:** stejné jako `/import`.

**Tělo požadavku:**
```json
{
  "dictionary": "permit_type",
  "value_key_text": "Průvodní dopis|pd\nObálka|ob\nFaktura|fk"
}
```

Výsledné deskriptory mají vždy `lang="cs"`, `key_alt=""`, `active=true`.

**Odpověď `200`:** stejná struktura jako `/import`.

**Chyby:** `400` chybějící `dictionary` nebo `value_key_text`.

---

### `POST /import/legacy?replace=false`

Import pole deskriptorů z descriptor-service v1 (starý flat formát s poli `value` a `value_en`). Endpoint transformuje vstup do aktuálního `values` formátu.

**Query parametry:** stejné jako `/import`.

**Tělo požadavku:**
```json
[
  {
    "dictionary": "country",
    "key": "CZ",
    "key_alt": "CZE",
    "value": "Česká republika",
    "value_en": "Czech Republic",
    "active": true
  }
]
```

**Odpověď `200`:** stejná struktura jako `/import`.

**Chyby:** `400` prázdné nebo chybějící tělo.

---

### `POST /import/legacy/file?replace=false`

Import ze souboru NDJSON (JSON Lines) — formát `descriptor-service_1.json`. Přijímá multipart upload; každý řádek je samostatný JSON objekt.

**Query parametry:** stejné jako `/import`.

**Formulář (multipart):**

| Pole | Typ | Popis |
|------|-----|-------|
| `file` | `UploadFile` | Soubor `descriptor-service_1.json` |

Endpoint automaticky:
- Stripuje BOM (`utf-8-sig` dekódování)
- Ignoruje prázdné řádky
- Sanitizuje embedded U+FEFF a whitespace v každém záznamu

**Příklad curl:**
```bash
curl -X POST "http://localhost:8000/import/legacy/file?replace=false" \
  -H "X-API-KEY: vas-klic" \
  -F "file=@data/descriptor-service_1.json"
```

**Odpověď `200`:** stejná struktura jako `/import`.

**Chyby:** `400` prázdný soubor, nevalidní JSON na konkrétním řádku (s číslem řádku v chybové zprávě), chyba dekódování.

---

## Monitoring endpointy (vyžadují `X-API-KEY`)

Monitoring endpointy vracejí statistiky a stav databáze. Přístup je řízen stejným mechanismem jako admin endpointy.

---

### `GET /monitor/stats`

Agregované statistiky celé kolekce deskriptorů. Výpočet probíhá přes MongoDB aggregation pipeline (tři round-tripy).

**Query parametry:**

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `hours` | int | `24` | Okno pro výpočet "nedávno přidaných/upravených" záznamů (1–720) |

**Odpověď `200`:**
```json
{
  "generated_at": "2024-06-01T10:00:00Z",
  "period_hours": 24,
  "total_descriptors": 349,
  "total_dictionaries": 2,
  "active_descriptors": 343,
  "inactive_descriptors": 6,
  "recently_added": 5,
  "recently_modified": 12,
  "by_dictionary": [
    {
      "dictionary": "country",
      "count": 249,
      "active": 245,
      "inactive": 4,
      "last_modified": "2024-06-01T10:00:00Z"
    },
    {
      "dictionary": "species",
      "count": 100,
      "active": 98,
      "inactive": 2,
      "last_modified": "2024-05-01T08:00:00Z"
    }
  ]
}
```

Definice polí:
- `recently_added` — záznamy s `version=1` a `timestamp >= now - hours`
- `recently_modified` — záznamy s `version>1` a `timestamp >= now - hours`

**Chyby:** `403` neplatný klíč, `422` neplatný parametr `hours`, `503` MongoDB nedostupná.

---

### `GET /monitor/health`

Stav MongoDB a detaily kolekce. Vrátí `200` i při stavu RED (nevyvolává 503) — stav je obsažen v těle odpovědi.

**Odpověď `200` (GREEN):**
```json
{
  "status": "GREEN",
  "mongo_status": "GREEN",
  "collection_name": "descriptor",
  "document_count": 349,
  "index_count": 3,
  "indexes": [
    { "name": "_id_", "keys": {"_id": 1} },
    { "name": "idx_key", "keys": {"key": 1} },
    { "name": "idx_dict_key", "keys": {"dictionary": 1, "key": 1} }
  ],
  "version": "2.0.1"
}
```

**Odpověď `200` (RED):**
```json
{
  "status": "RED",
  "mongo_status": "RED",
  "collection_name": "descriptor",
  "document_count": 0,
  "index_count": 0,
  "indexes": [],
  "version": "2.0.1"
}
```

**Chyby:** `403` neplatný klíč, `503` DB dotaz selhal (pouze při stavu GREEN ale chybě při čtení).

---

### `GET /monitor/dict/{dictionary}`

Detailní statistiky jednoho slovníku plus ukázka 10 naposledy upravených klíčů.

**Path parametry:**

| Parametr | Typ | Popis |
|----------|-----|-------|
| `dictionary` | string | Kód řízeného slovníku |

**Odpověď `200`:**
```json
{
  "dictionary": "country",
  "count": 249,
  "active": 245,
  "inactive": 4,
  "last_modified": "2024-06-01T10:00:00Z",
  "sample_keys": ["AT", "CZ", "DE", "FR", "GB", "IT", "PL", "SK", "US", "XX"]
}
```

**Chyby:** `403` neplatný klíč, `404` slovník neexistuje, `503` MongoDB nedostupná.

---

## Chybové odpovědi

Všechny chyby mají formát:
```json
{ "message": "Popis chyby (včetně IP adresy klienta)" }
```

| HTTP kód | Situace |
|----------|---------|
| `400` | Chybějící nebo neplatné parametry |
| `401` | Chybějící API klíč |
| `403` | Neplatný API klíč |
| `404` | Deskriptor nebo slovník nenalezen |
| `409` | Deskriptor již existuje (při POST) |
| `500` | Interní chyba serveru |
| `503` | MongoDB nedostupná |

---

## Datové typy

### `DescriptorValueType`
```json
{
  "lang": "cs",
  "value": "Rakousko",
  "value_alt": "Rakouská spolková republika"
}
```

### `DescriptorBaseType`
```json
{
  "key": "AT",
  "key_alt": "AUT",
  "dictionary": "country",
  "active": true,
  "values": [ ...DescriptorValueType... ]
}
```

### `DescriptorType`
`DescriptorBaseType` rozšířený o:
```json
{
  "identifier": "uuid-string"
}
```
