from beanie import init_beanie
from pymongo import AsyncMongoClient

from api.model.odm import DbDescriptor, DbDescriptorSav
from init import CONFIG, DEFAULT_AGENDA, MONGO_CONNECTION_STRING

DB_NAME = CONFIG[DEFAULT_AGENDA]['database']
CLIENT = AsyncMongoClient(MONGO_CONNECTION_STRING)
DATABASE = CLIENT.get_database(DB_NAME)


async def ping():
    out = await DATABASE.command("ping")
    return out


async def init_sprint():
    await init_beanie(
        database=CLIENT[DB_NAME],
        document_models=[DbDescriptor, DbDescriptorSav]
    )


async def consolidate_data():
    reply = await DbDescriptorSav.all_documents()
    i = 0
    skipped = 0
    for item in reply:
        i += 1
        descriptor = item.consolidated
        if descriptor is None:
            skipped += 1
            print(f"{i}/{len(reply)}: SKIP (None for id={item.identifier})")
            continue
        await descriptor.replace()
        print(f"{i}/{len(reply)}: {descriptor.identifier}")
    return len(reply) - skipped
