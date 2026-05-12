# Datový model — SYSNET Managed Dictionaries

## MongoDB schéma

Kolekce: `descriptor`

```json
{
  "_id":             "ObjectId",
  "identifier":      "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "key":             "AT",
  "key_alt":         "AUT",
  "dictionary":      "country",
  "active":          true,
  "values": [
    {
      "lang":      "cs",
      "value":     "Rakousko",
      "value_alt": "Rakouská spolková republika"
    },
    {
      "lang":      "en",
      "value":     "Austria",
      "value_alt": null
    }
  ],
  "version":         3,
  "timestamp":       "2024-06-15T12:30:00.000Z",
  "is_consolidated": true
}
```

### Popis polí

| Pole | Typ | Popis |
|------|-----|-------|
| `_id` | ObjectId | MongoDB interní identifikátor |
| `identifier` | string | Aplikační UUID (str), unikátní přes celou kolekci |
| `key` | string | Hlavní klíč deskriptoru, unikátní v rámci slovníku |
| `key_alt` | string | Alternativní klíč (synonymum), prohledáván spolu s `key` |
| `dictionary` | string | Kód řízeného slovníku (např. `country`, `species`) |
| `active` | bool | Příznak aktivního záznamu; neaktivní záznamy nejsou mazány |
| `values` | array | Jazykové překlady klíče |
| `values[].lang` | string | Kód jazyka (např. `cs`, `en`, `de`) |
| `values[].value` | string | Hodnota deskriptoru v daném jazyce |
| `values[].value_alt` | string\|null | Alternativní (dlouhá) hodnota v daném jazyce |
| `version` | int | Počítadlo verzí — inkrementuje se při každé změně |
| `timestamp` | datetime | Čas poslední změny (UTC, nastavuje Beanie before_event hook) |
| `is_consolidated` | bool\|null | Příznak migrace (viz níže) |

### Pole `is_consolidated`

Pole rozlišuje záznamy z různých epoch:

| Hodnota | Třída | Popis |
|---------|-------|-------|
| `true` | `DbDescriptor` | Konsolidovaný (nový) formát, `identifier` jako `str` |
| `false` nebo `null` nebo chybí | `DbDescriptorSav` | Legacy formát, `identifier` jako MongoDB UUID (BinData) |

Po úspěšné konsolidaci mají všechny záznamy `is_consolidated = true`.

---

## Pydantic modely (`api/model/dictionary.py`)

### `DescriptorValueType`

Hodnota deskriptoru pro jeden jazyk.

```python
class DescriptorValueType(BaseModel):
    lang:      Optional[str]   # kód jazyka, např. "cs"
    value:     Optional[str]   # překlad
    value_alt: Optional[str]   # alternativní překlad (může být None)
```

### `DescriptorBaseType`

Základní data deskriptoru bez systémového identifikátoru. Používá se při importu a exportu.

```python
class DescriptorBaseType(BaseModel):
    key:        Optional[str]
    key_alt:    Optional[str]
    dictionary: Optional[str]
    active:     Optional[bool]
    values:     Optional[List[DescriptorValueType]]
```

### `DescriptorType`

Plný deskriptor vrácený z API — rozšiřuje `DescriptorBaseType` o `identifier`.

```python
class DescriptorType(DescriptorBaseType):
    identifier: Optional[str]
```

### `DictionaryType`

Souhrn jednoho slovníku vrácený z `/info`.

```python
class DictionaryType(BaseModel):
    dictionary: str    # alias pro MongoDB pole "_id"
    count:      int
```

### `ReplyImported`

Výsledek hromadného importu.

```python
class ReplyImported(BaseModel):
    count_added:    int
    count_replaced: int
    count_rejected: int
    count_error:    int
    added:          List[ImportedItem]
    replaced:       List[ImportedItem]
    rejected:       List[ImportedItem]
    error:          List[ImportedItem]
```

### `ImportedItem`

Výsledek zpracování jednoho záznamu při importu.

```python
class ImportedItem(BaseModel):
    dictionary: str
    key:        str
    status:     StatusEnum   # added | replaced | rejected | failed
```

### `DominoImport`

Vstup pro import z Domino textového formátu.

```python
class DominoImport(BaseModel):
    dictionary:     str
    value_key_text: str   # formát: "Hodnota|klíč\nHodnota2|klíč2"
```

---

## ODM modely (`api/model/odm.py`)

Obě třídy mapují na stejnou MongoDB kolekci `descriptor` — liší se typem pole `identifier` a filtrem přes `is_consolidated`.

### `DbDescriptor`

Primární třída pro čtení a zápis konsolidovaných dat.

```python
class DbDescriptor(Document, DescriptorType):
    identifier:      str           # UUID jako string
    version:         int = 0
    timestamp:       datetime      # Field(default_factory=local_now)
    is_consolidated: Optional[bool] = None

    class Settings:
        name = "descriptor"
```

**Klíčové metody:**

| Metoda | Popis |
|--------|-------|
| `by_key(dictionary, key)` | Najde deskriptor podle slovníku a klíče (hledá v `key` i `key_alt`) |
| `by_identifier(uuid)` | Najde deskriptor podle `identifier` (str) |
| `by_query(query, paging, sort)` | Obecný dotaz s stránkováním a řazením |
| `get_by_dictionary(dictionary)` | Všechny deskriptory slovníku, seřazené podle `key` |
| `dictionary_list()` | Agregace — seznam slovníků s počty |
| `export_dictionary(dictionary)` | Export jednoho slovníku jako `DescriptorBaseType` |
| `export_all()` | Export všech deskriptorů jako `DescriptorBaseType` |
| `all_documents()` | Všechny záznamy s `is_consolidated = true` |
| `activate(doit, save)` | Nastaví `active` a uloží |

**Beanie before_event hooki:**

| Event | Hook | Efekt |
|-------|------|-------|
| `Insert` | `init_values()` | Nastaví `timestamp`, `version = 1`, doplní `identifier` pokud chybí |
| `Replace, Update, SaveChanges` | `update_timestamp()` | Inkrementuje `version`, aktualizuje `timestamp` |

**Property `document`:**

Konvertuje `DbDescriptor` na `DescriptorType` (bez ODM polí). Používá se k vrácení čistého API modelu z routerů.

### `DbDescriptorSav`

Pomocná třída pro přístup k legacy datům před konsolidací.

```python
class DbDescriptorSav(Document, DescriptorType):
    identifier:      UUID          # nativní MongoDB UUID
    version:         int = 0
    timestamp:       datetime
    is_consolidated: Optional[bool] = None

    class Settings:
        name = "descriptor"        # stejná kolekce jako DbDescriptor
```

**Klíčové property:**

| Property | Popis |
|----------|-------|
| `document` | Konvertuje na `DescriptorType` (UUID → str) |
| `consolidated` | Konvertuje na `DbDescriptor` s `is_consolidated = True` |

**Metoda `all_documents()`:**

Vrátí záznamy, které dosud nebyly konsolidovány — tj. `is_consolidated` je `False`, `None` nebo pole zcela chybí:

```python
query = Or(
    Eq("is_consolidated", False),
    Exists("is_consolidated", False),
    In("is_consolidated", [None, ""])
)
```

---

## Indexy kolekce `descriptor`

```python
IndexModel(keys=[("key", ASCENDING)],                          collation=COLLATION)  # idx_key
IndexModel(keys=[("dictionary", ASCENDING)])                                          # idx_dictionary
IndexModel(keys=[("dictionary", ASCENDING), ("key", ASCENDING)])                      # idx_dict_key
IndexModel(keys=[("identifier", ASCENDING)])                                          # idx_identifier
IndexModel(keys=[("$**", ASCENDING)],                          collation=COLLATION)  # idx_wildcard
IndexModel([("key","text"),("key_alt","text"),("dictionary","text"),
            ("values.value","text"),("values.value_alt","text")])                     # idx_text
```

`COLLATION = Collation(locale='cs@collation=search')` — česká abeceda s diakritikou, case-insensitive vyhledávání.
