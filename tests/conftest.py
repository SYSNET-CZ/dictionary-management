"""
Sdílené fixtures pro pytest — SYSNET Managed Dictionaries.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Nastavení proměnných prostředí PŘED importem aplikace
os.environ.setdefault("DICT_VERSION", "test")
os.environ.setdefault("INSTANCE", "TEST")
os.environ.setdefault("MONGO_PASSWORD", "test_password")


# ---------------------------------------------------------------------------
# Fixtures pro mock DbDescriptor
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_descriptor_dict() -> dict:
    return {
        "identifier": "test-uuid-1234",
        "key": "AT",
        "key_alt": "AUT",
        "dictionary": "country",
        "active": True,
        "values": [
            {"lang": "cs", "value": "Rakousko", "value_alt": "Rakouská spolková republika"},
            {"lang": "en", "value": "Austria", "value_alt": None},
        ],
        "version": 1,
        "timestamp": "2024-01-01T00:00:00",
        "is_consolidated": True,
    }


@pytest.fixture
def mock_db_descriptor(sample_descriptor_dict):
    """Vrátí mockovaný DbDescriptor objekt."""
    from api.model.dictionary import DescriptorType, DescriptorValueType

    doc_mock = MagicMock()
    doc_mock.identifier = sample_descriptor_dict["identifier"]
    doc_mock.key = sample_descriptor_dict["key"]
    doc_mock.key_alt = sample_descriptor_dict["key_alt"]
    doc_mock.dictionary = sample_descriptor_dict["dictionary"]
    doc_mock.active = sample_descriptor_dict["active"]
    doc_mock.version = sample_descriptor_dict["version"]
    doc_mock.values = [
        DescriptorValueType(**v) for v in sample_descriptor_dict["values"]
    ]

    descriptor_type = DescriptorType(
        identifier=sample_descriptor_dict["identifier"],
        key=sample_descriptor_dict["key"],
        key_alt=sample_descriptor_dict["key_alt"],
        dictionary=sample_descriptor_dict["dictionary"],
        active=sample_descriptor_dict["active"],
        values=doc_mock.values,
    )
    doc_mock.document = descriptor_type
    doc_mock.model_dump.return_value = sample_descriptor_dict
    return doc_mock


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Vrátí httpx AsyncClient pro testování FastAPI aplikace.
    Lifespan (MongoDB init) je patchován.
    """
    from contextlib import asynccontextmanager
    from unittest.mock import patch

    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    with patch("api.main.lifespan", mock_lifespan):
        from api.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
