from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from api.models import DescriptorDb
from init import CONFIG, DEFAULT_AGENDA, MONGO_CONNECTION_STRING

DB_NAME = CONFIG[DEFAULT_AGENDA]['database']
CLIENT = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
DATABASE = CLIENT.get_database(DB_NAME)


async def ping():
    out = await DATABASE.command("ping")
    return out


async def init_sprint():
    await init_beanie(
        database=CLIENT[DB_NAME],
        document_models=[DescriptorDb])
