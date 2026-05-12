"""
Fixtures pro integracni testy - pouzivaji realnou MongoDB.

Pozadavky:
- MongoDB bezi na localhost:27017 (Docker kontejner)
- Konfigurace v conf/dict.yml (user: root, password: s3cr3t)
- Testovaci databaze: dictionaries_test (izolace od produkce)

Architektura:
- Vsechny async fixtures jsou function-scoped, aby sdilely event loop s testem.
- Kazdy test dostane cisty AsyncMongoClient + cerstve inicializovane Beanie.
- Beanie je inicializovano do testovaci databaze dictionaries_test.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo import AsyncMongoClient
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

os.environ.setdefault("DICT_VERSION", "test")
os.environ.setdefault("INSTANCE", "TEST")

TEST_DB_NAME = "dictionaries_test"
VALID_API_KEY = "1ywA1Fxc9QBB3CtvP6kGJw"  # klic z conf/dict.yml


@pytest_asyncio.fixture
async def beanie_db():
    """
    Function-scoped fixture: cerstvy MongoDB klient + Beanie init pro kazdy test.
    Cisti testovaci kolekci pred i po testu.
    """
    from init import MONGO_CONNECTION_STRING
    from api.model.odm import DbDescriptor, DbDescriptorSav

    client = AsyncMongoClient(MONGO_CONNECTION_STRING)
    # Ping pred pouzitim
    await client[TEST_DB_NAME].command("ping")
    # Vymazat data z predchoziho testu
    await client[TEST_DB_NAME]["descriptor"].delete_many({})

    await init_beanie(
        database=client[TEST_DB_NAME],
        document_models=[DbDescriptor, DbDescriptorSav],
    )
    yield client[TEST_DB_NAME]

    # Cleanup po testu
    await client[TEST_DB_NAME]["descriptor"].delete_many({})
    await client.close()


@pytest_asyncio.fixture
async def api_client(beanie_db):
    """
    httpx AsyncClient pro integracni API testy.
    Beanie uz inicializovano pres beanie_db fixture (stejny event loop).
    Lifespan je nahrazen mockem - MongoDB pripojeni uz existuje.
    """
    @asynccontextmanager
    async def test_lifespan(app):
        # Beanie je uz inicializovano v beanie_db fixture
        yield

    def mock_is_authorized(key):
        return key == VALID_API_KEY

    with (
        patch("api.main.lifespan", test_lifespan),
        patch("api.routers.admins.is_api_authorized", side_effect=mock_is_authorized),
    ):
        from api.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


def auth_headers():
    return {"X-API-KEY": VALID_API_KEY}
