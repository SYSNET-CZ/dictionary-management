# Konsolidace dat — migrace UUID identifikátorů

## Kontext

Starší verze služby ukládala pole `identifier` jako nativní MongoDB UUID objekt
(BSON BinData subtype 4). Nová verze vyžaduje `identifier` jako běžný řetězec (`str`).

Tato nekompatibilita způsobovala problémy při exportu a importu dat — UUID se
serializovalo do BSON binárního formátu místo čitelného řetězce.

## Dva ODM pohledy na jednu kolekci

Kolekce `descriptor` obsahuje oba typy záznamů vedle sebe. Rozlišují se polem `is_consolidated`:

```
MongoDB kolekce "descriptor"
│
├── záznamy s is_consolidated = true
│   └── identifier: "a1b2c3d4-..."  (string)
│   └── přistupováno přes DbDescriptor
│
└── záznamy s is_consolidated = false / null / chybí
    └── identifier: BinData(4, "...")  (UUID)
    └── přistupováno přes DbDescriptorSav
```

### `DbDescriptorSav`

- `identifier: UUID` — Pydantic/Beanie přečte BinData z MongoDB jako Python `UUID`
- Metody automaticky konvertují `UUID → str` před vytvořením výstupního modelu
- Property `consolidated` vrátí instanci `DbDescriptor` se `str` identifikátorem a `is_consolidated = True`

### `DbDescriptor`

- `identifier: str` — přijímá pouze řetězcový formát
- Čte pouze záznamy s `is_consolidated = True` (pomocí `all_documents()`)

## Konsolidační skript (`sprint1.py`)

Jednorázový idempotentní skript, který převede všechny nekonsolidované záznamy:

```python
async def consolidate_data():
    reply = await DbDescriptorSav.all_documents()   # najdi nekonsolidované
    i = 0
    skipped = 0
    for item in reply:
        i += 1
        descriptor = item.consolidated              # konvertuj UUID → str, is_consolidated = True
        if descriptor is None:
            skipped += 1
            print(f"{i}/{len(reply)}: SKIP (None for id={item.identifier})")
            continue
        await descriptor.replace()                 # přepiš v MongoDB
        print(f"{i}/{len(reply)}: {descriptor.identifier}")
    return len(reply) - skipped
```

### Krok po kroku

1. `DbDescriptorSav.all_documents()` — dotaz hledá záznamy, kde `is_consolidated` je `False`, `None` nebo pole zcela chybí
2. Pro každý záznam zavolá property `consolidated`:
   - `model_dump()` serializuje dokument
   - `dump['identifier'] = str(dump['identifier'])` — konvertuje UUID na řetězec
   - Vytvoří instanci `DbDescriptor` se `is_consolidated = True`
3. `await descriptor.replace()` — přepíše dokument v MongoDB (triggeruje `update_timestamp` hook, inkrementuje `version`)
4. Vrátí počet úspěšně zpracovaných záznamů

### Idempotence

Skript je bezpečné spustit opakovaně. `DbDescriptorSav.all_documents()` vrací pouze záznamy
bez `is_consolidated = True` — záznamy již jednou konsolidované jsou vyloučeny z výběru.

## Spuštění konsolidace

```bash
cd /path/to/dictionary-management
source .venv/bin/activate

python3 - <<'EOF'
import asyncio
from sprint1 import init_sprint, consolidate_data

async def main():
    await init_sprint()
    n = await consolidate_data()
    print(f"Konsolidováno celkem: {n} záznamů")

asyncio.run(main())
EOF
```

Nebo přímo jako skript:

```bash
python3 -c "
import asyncio
from sprint1 import init_sprint, consolidate_data

async def main():
    await init_sprint()
    n = await consolidate_data()
    print(f'Konsolidováno: {n}')

asyncio.run(main())
"
```

## Výstup při spuštění

```
1/523: a1b2c3d4-e5f6-7890-abcd-ef1234567890
2/523: b2c3d4e5-f6a7-8901-bcde-f12345678901
...
521/523: SKIP (None for id=...)
523/523: f6a7b8c9-d0e1-2345-6789-abcdef012345
Konsolidováno celkem: 521 záznamů
```

`SKIP` nastane, pokud property `consolidated` vrátí `None` — to se stane při validační chybě dokumentu (viz sekce Chybové stavy).

## Ověření po konsolidaci

Po dokončení skriptu by měly být všechny záznamy konsolidované:

```javascript
// MongoDB shell
db.descriptor.countDocuments({ is_consolidated: true })      // mělo by vrátit celkový počet
db.descriptor.countDocuments({ is_consolidated: { $ne: true } }) // mělo by vrátit 0
```

Případně přes API:

```bash
curl http://localhost:8000/info
# "dictionaries" by mělo obsahovat všechny slovníky se správnými počty
```

## Čitelnost legacy dat za provozu

I bez spuštění konsolidačního skriptu jsou legacy záznamy čitelné přes API — routery používají `DbDescriptor`, který mapuje na stejnou kolekci. Beanie přečte BinData UUID a Pydantic ho přijme díky coercion (UUID → str kompatibilita v Pydantic v2).

Metody `by_query()`, `get_by_dictionary()`, `export_dictionary()`, `export_all()` v obou třídách obsahují explicitní konverzi:

```python
dump = item.model_dump()
dump['identifier'] = str(dump['identifier'])  # UUID → str konverze pro stará data
out_item = DescriptorType(**dump)
```

Tato konverze zajišťuje, že API klientům vždy vrátí `identifier` jako řetězec, bez ohledu na formát v MongoDB.

## Chybové stavy

### `consolidated` vrátí `None`

Nastane při validační chybě Pydantic — např. povinné pole je v dokumentu `None` nebo chybí.
Skript takový záznam přeskočí s výpisem `SKIP` a pokračuje.

Doporučený postup: najít přeskočené záznamy ručně v MongoDB a opravit poškozená data před opakovaným spuštěním:

```javascript
db.descriptor.find({ is_consolidated: { $ne: true }, identifier: { $type: "binData" } })
```

### `replace()` selže

Pokud `await descriptor.replace()` vyhodí výjimku (výpadek DB, network error), skript
spadne. Protože je skript idempotentní, je bezpečné ho po obnovení DB znovu spustit —
záznamy, které byly úspěšně zpracované, mají `is_consolidated = True` a nebudou zpracovány znovu.
