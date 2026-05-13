"""
Testy veřejných endpointů — GET /descriptor/{dictionary}/{key}
                              GET /descriptor/{dictionary}
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import os
os.environ.setdefault("DICT_VERSION", "test")
os.environ.setdefault("INSTANCE", "TEST")
os.environ.setdefault("MONGO_PASSWORD", "test")

from api.model.dictionary import DescriptorType, DescriptorValueType


# ---------------------------------------------------------------------------
# Pomocné funkce
# ---------------------------------------------------------------------------

def make_descriptor(key="AT", dictionary="country") -> DescriptorType:
    return DescriptorType(
        identifier="test-uuid",
        key=key,
        key_alt=f"{key}T",
        dictionary=dictionary,
        active=True,
        values=[DescriptorValueType(lang="cs", value="Testovací hodnota", value_alt=None)],
    )


def make_db_doc(key="AT", dictionary="country"):
    doc = MagicMock()
    doc.document = make_descriptor(key=key, dictionary=dictionary)
    doc.key = key
    doc.dictionary = dictionary
    doc.__bool__ = lambda self: True
    return doc


# ---------------------------------------------------------------------------
# Fixture — AsyncClient s mocknutým lifespan
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    with patch("api.main.lifespan", mock_lifespan):
        from api.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /descriptor/{dictionary}/{key}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetDescriptor:

    async def test_found(self, client):
        doc = make_db_doc()
        with patch("api.routers.public.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.get("/descriptor/country/AT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "AT"
        assert data["dictionary"] == "country"

    async def test_not_found_returns_404(self, client):
        with patch("api.routers.public.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.get("/descriptor/country/XX")
        assert resp.status_code == 404

    async def test_empty_key_returns_400(self, client):
        """Prázdný key v path — FastAPI vrátí 404 (path neodpovídá)."""
        resp = await client.get("/descriptor/country/")
        assert resp.status_code in (404, 307)

    async def test_response_contains_values(self, client):
        doc = make_db_doc()
        with patch("api.routers.public.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.get("/descriptor/country/AT")
        data = resp.json()
        assert "values" in data
        assert len(data["values"]) > 0


# ---------------------------------------------------------------------------
# GET /descriptor/{dictionary} — seznam / autocomplete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetDescriptorList:

    async def test_returns_list(self, client):
        descriptors = [make_descriptor(key="AT"), make_descriptor(key="DE")]
        with patch("api.routers.public.DbDescriptor.by_query", AsyncMock(return_value=descriptors)):
            resp = await client.get("/descriptor/country")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_empty_result_returns_404(self, client):
        with patch("api.routers.public.DbDescriptor.by_query", AsyncMock(return_value=[])):
            resp = await client.get("/descriptor/country")
        assert resp.status_code == 404

    async def test_with_query_param(self, client):
        descriptors = [make_descriptor(key="AT")]
        with patch("api.routers.public.DbDescriptor.by_query", AsyncMock(return_value=descriptors)):
            resp = await client.get("/descriptor/country?query=Rak")
        assert resp.status_code == 200

    async def test_with_skip_limit(self, client):
        descriptors = [make_descriptor(key="AT")]
        with patch("api.routers.public.DbDescriptor.by_query", AsyncMock(return_value=descriptors)):
            resp = await client.get("/descriptor/country?skip=0&limit=50")
        assert resp.status_code == 200

    async def test_skip_limit_not_capped_at_10(self, client):
        """Regression test: limit=50 v dotazu musí být předán jako 50, ne PAGE_SIZE=10."""
        received_paging = {}

        async def capture_query(query, paging, sort):
            received_paging.update(paging)
            return [make_descriptor()]

        with patch("api.routers.public.DbDescriptor.by_query", side_effect=capture_query):
            await client.get("/descriptor/country?skip=0&limit=50")

        assert received_paging.get("limit") == 50, (
            f"limit byl {received_paging.get('limit')}, očekáváno 50 (paging bugfix regression)"
        )

    async def test_active_filter(self, client):
        descriptors = [make_descriptor()]
        with patch("api.routers.public.DbDescriptor.by_query", AsyncMock(return_value=descriptors)):
            resp = await client.get("/descriptor/country?active=true")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /suggest/{dictionary} — typeahead / autocomplete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetSuggest:

    async def test_returns_list_on_match(self, client):
        descriptors = [make_descriptor(key="AT"), make_descriptor(key="AU")]
        with patch("api.routers.public.DbDescriptor.suggest", AsyncMock(return_value=descriptors)):
            resp = await client.get("/suggest/country?prefix=A")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_empty_result_returns_404(self, client):
        with patch("api.routers.public.DbDescriptor.suggest", AsyncMock(return_value=[])):
            resp = await client.get("/suggest/country?prefix=xyz")
        assert resp.status_code == 404

    async def test_missing_prefix_returns_422(self, client):
        """Parametr prefix je povinný — bez něj FastAPI vrátí 422."""
        resp = await client.get("/suggest/country")
        assert resp.status_code == 422

    async def test_prefix_too_short_returns_422(self, client):
        """min_length=1 — prázdný prefix musí selhat validací."""
        resp = await client.get("/suggest/country?prefix=")
        assert resp.status_code == 422

    async def test_limit_above_50_returns_422(self, client):
        """le=50 — limit>50 musí selhat validací."""
        resp = await client.get("/suggest/country?prefix=A&limit=51")
        assert resp.status_code == 422

    async def test_limit_zero_returns_422(self, client):
        """ge=1 — limit=0 musí selhat validací."""
        resp = await client.get("/suggest/country?prefix=A&limit=0")
        assert resp.status_code == 422

    async def test_suggest_called_with_correct_args(self, client):
        """Ověří, že endpoint předává správné argumenty do DbDescriptor.suggest."""
        received: dict = {}

        async def capture(dictionary, prefix, lang, limit):
            received.update({"dictionary": dictionary, "prefix": prefix,
                             "lang": lang, "limit": limit})
            return [make_descriptor()]

        with patch("api.routers.public.DbDescriptor.suggest", side_effect=capture):
            await client.get("/suggest/country?prefix=Rak&lang=cs&limit=10")

        assert received["dictionary"] == "country"
        assert received["prefix"] == "Rak"
        assert received["lang"] == "cs"
        assert received["limit"] == 10

    async def test_default_limit_is_15(self, client):
        """Výchozí limit je 15, pokud není zadán."""
        received: dict = {}

        async def capture(dictionary, prefix, lang, limit):
            received["limit"] = limit
            return [make_descriptor()]

        with patch("api.routers.public.DbDescriptor.suggest", side_effect=capture):
            await client.get("/suggest/country?prefix=A")

        assert received["limit"] == 15

    async def test_response_schema_contains_key_and_values(self, client):
        """Response musí obsahovat key a values pro UI našeptávače."""
        descriptors = [make_descriptor(key="AT")]
        with patch("api.routers.public.DbDescriptor.suggest", AsyncMock(return_value=descriptors)):
            resp = await client.get("/suggest/country?prefix=AT")
        data = resp.json()
        assert data[0]["key"] == "AT"
        assert "values" in data[0]
