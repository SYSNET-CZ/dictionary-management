# Uživatelská příručka — SYSNET Managed Dictionaries API

## Co je tato služba?

SYSNET Managed Dictionaries je REST API pro správu řízených slovníků (číselníků).
Slovník je sada pojmenovaných položek (**deskriptorů**), kde každá položka má kód a překlad do jednoho nebo více jazyků.

**Příklad:** slovník `country` obsahuje položky `AT`, `CZ`, `DE`, ... s překlady „Rakousko", „Česko", „Německo".

## Základní pojmy

| Pojem | Popis | Příklad |
|-------|-------|---------|
| **Slovník** | Pojmenovaná sada deskriptorů | `country`, `species`, `permit_type` |
| **Deskriptor** | Jedna položka slovníku identifikovaná klíčem | klíč `AT` ve slovníku `country` |
| **Klíč** | Krátký identifikátor položky | `AT`, `CZE`, `pd` |
| **Alternativní klíč** | Synonymum klíče, prohledáváno stejně jako klíč | `AUT` jako alternativa k `AT` |
| **Hodnota** | Jazykový překlad klíče | „Rakousko" pro `lang=cs` |
| **Aktivní/neaktivní** | Položky lze deaktivovat bez smazání | `active=false` |

## Jak číst slovník

### Získat jednu položku

```
GET /descriptor/{slovník}/{klíč}
```

**Příklad — najdi zemi „AT" ve slovníku „country":**

```bash
curl http://api.sysnet.cz/dict/descriptor/country/AT
```

**Odpověď:**
```json
{
  "identifier": "abc-123",
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

Endpoint hledá jak v `key`, tak v `key_alt` — dotaz na `AUT` vrátí stejný výsledek jako dotaz na `AT`.

### Vyhledávání / autocomplete

```
GET /descriptor/{slovník}?query=Text&lang=cs&active=true&skip=0&limit=20
```

| Parametr | Popis | Příklad |
|----------|-------|---------|
| `query` | Fulltext hledání v hodnotách | `query=Rak` najde „Rakousko" |
| `key` | Regex hledání v kódu položky | `key=A` najde vše začínající A |
| `lang` | Filtr jazyka | `lang=cs` |
| `active` | Jen aktivní (`true`) nebo neaktivní (`false`) | `active=true` |
| `skip` | Přeskočit N výsledků (stránkování) | `skip=20` |
| `limit` | Max. počet vrácených výsledků | `limit=10` |

**Příklad — najdi všechny aktivní země začínající „Rak" v češtině:**

```bash
curl "http://api.sysnet.cz/dict/descriptor/country?query=Rak&lang=cs&active=true"
```

**Příklad — autocomplete pro UI (prvních 10 výsledků):**

```bash
curl "http://api.sysnet.cz/dict/descriptor/species?query=Panth&limit=10"
```

## Stav služby

```bash
curl http://api.sysnet.cz/dict/info
```

Odpověď ukazuje stav připojení k databázi a seznam dostupných slovníků:

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

Stavy: `GREEN` = vše v pořádku, `RED` = problém s databází.

## Chybové odpovědi

Všechny chybové odpovědi mají formát:

```json
{ "message": "Popis chyby" }
```

| HTTP kód | Situace |
|----------|---------|
| `400` | Chybějící nebo neplatný parametr |
| `404` | Položka nebo slovník nenalezen |
| `409` | Položka již existuje (při vytváření) |

## Příklady použití (curl)

```bash
# Jeden deskriptor
curl http://api.sysnet.cz/dict/descriptor/country/AT

# Hledat v číselníku druhů
curl "http://api.sysnet.cz/dict/descriptor/species?query=Panthera&limit=5"

# Jen aktivní položky daného slovníku
curl "http://api.sysnet.cz/dict/descriptor/permit_type?active=true"

# Stránkování — strana 2 (10 výsledků na stránku)
curl "http://api.sysnet.cz/dict/descriptor/country?skip=10&limit=10"

# Stav služby
curl http://api.sysnet.cz/dict/info
```
