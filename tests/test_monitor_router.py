"""
Testy monitoring endpointů — GET /monitor/stats, /monitor/health, /monitor/dict/{dictionary}.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DICT_VERSION", "test")
os.environ.setdefault("INSTANCE", "TEST")
os.environ.setdefault("MONGO_PASSWORD", "test")

API_KEY = "valid-key"


# ---------------------------------------------------------------------------
# Fixtures
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


@pytest.fixture(autouse=True)
def mock_auth():
    """Všechny testy mají k dispozici platný API klíč."""
    with patch("api.routers.monitor.is_api_authorized", return_value=True):
        yield


@pytest.fixture(autouse=True)
def mock_mongo_green():
    """MongoDB stav GREEN pro všechny testy (pokud test nepřepíše)."""
    with patch("api.routers.monitor.CONFIG", {"mongo": {"status": "GREEN"}}):
        yield


# ---------------------------------------------------------------------------
# Sdílená testovací data
# ---------------------------------------------------------------------------

DICT_PIPELINE_RESULT = [
    {"_id": "country", "count": 249, "active": 245, "inactive": 4,
     "last_modified": datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)},
    {"_id": "species", "count": 100, "active": 98, "inactive": 2,
     "last_modified": datetime(2024, 5, 1, 8, 0, 0, tzinfo=timezone.utc)},
]

ADDED_RESULT = [{"n": 5}]
UPDATED_RESULT = [{"n": 12}]


# ---------------------------------------------------------------------------
# GET /monitor/stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMonitorStats:

    async def test_returns_200_with_valid_data(self, client):
        side_effects = [DICT_PIPELINE_RESULT, ADDED_RESULT, UPDATED_RESULT]
        with patch("api.routers.monitor._aggregate", side_effect=side_effects):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 200

    async def test_response_totals_are_correct(self, client):
        side_effects = [DICT_PIPELINE_RESULT, ADDED_RESULT, UPDATED_RESULT]
        with patch("api.routers.monitor._aggregate", side_effect=side_effects):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert data["total_descriptors"] == 349      # 249 + 100
        assert data["total_dictionaries"] == 2
        assert data["active_descriptors"] == 343     # 245 + 98
        assert data["inactive_descriptors"] == 6     # 4 + 2
        assert data["recently_added"] == 5
        assert data["recently_modified"] == 12

    async def test_by_dictionary_contains_both_entries(self, client):
        side_effects = [DICT_PIPELINE_RESULT, ADDED_RESULT, UPDATED_RESULT]
        with patch("api.routers.monitor._aggregate", side_effect=side_effects):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        keys = [d["dictionary"] for d in data["by_dictionary"]]
        assert "country" in keys
        assert "species" in keys

    async def test_default_period_is_24_hours(self, client):
        captured = []

        async def capture_pipeline(pipeline):
            captured.append(pipeline)
            if len(captured) == 1:
                return DICT_PIPELINE_RESULT
            elif len(captured) == 2:
                return ADDED_RESULT
            return UPDATED_RESULT

        with patch("api.routers.monitor._aggregate", side_effect=capture_pipeline):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert data["period_hours"] == 24

    async def test_custom_hours_parameter(self, client):
        side_effects = [DICT_PIPELINE_RESULT, ADDED_RESULT, UPDATED_RESULT]
        with patch("api.routers.monitor._aggregate", side_effect=side_effects):
            resp = await client.get("/monitor/stats?hours=72", headers={"X-API-KEY": API_KEY})
        assert resp.json()["period_hours"] == 72

    async def test_hours_above_720_returns_422(self, client):
        resp = await client.get("/monitor/stats?hours=721", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 422

    async def test_hours_zero_returns_422(self, client):
        resp = await client.get("/monitor/stats?hours=0", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 422

    async def test_missing_api_key_returns_4xx(self, client):
        with patch("api.routers.monitor.is_api_authorized", return_value=False):
            resp = await client.get("/monitor/stats")
        assert resp.status_code in (401, 403)

    async def test_invalid_api_key_returns_403(self, client):
        with patch("api.routers.monitor.is_api_authorized", return_value=False):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": "wrong"})
        assert resp.status_code == 403

    async def test_mongo_red_returns_503(self, client):
        with patch("api.routers.monitor.CONFIG", {"mongo": {"status": "RED"}}):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 503

    async def test_empty_collection_returns_zeros(self, client):
        with patch("api.routers.monitor._aggregate", side_effect=[[], [], []]):
            resp = await client.get("/monitor/stats", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert data["total_descriptors"] == 0
        assert data["total_dictionaries"] == 0
        assert data["recently_added"] == 0
        assert data["recently_modified"] == 0


# ---------------------------------------------------------------------------
# GET /monitor/health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMonitorHealth:

    def _make_index_info(self):
        return {
            "_id_": {"key": [("_id", 1)]},
            "idx_key": {"key": [("key", 1)]},
            "idx_dict_key": {"key": [("dictionary", 1), ("key", 1)]},
        }

    async def test_returns_200_when_green(self, client):
        mock_coll = AsyncMock()
        mock_coll.index_information = AsyncMock(return_value=self._make_index_info())
        with patch("api.routers.monitor.DbDescriptor.find") as mock_find, \
             patch("api.routers.monitor.DbDescriptor.get_pymongo_collection", return_value=mock_coll):
            mock_find.return_value.count = AsyncMock(return_value=349)
            resp = await client.get("/monitor/health", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 200

    async def test_response_structure_when_green(self, client):
        mock_coll = AsyncMock()
        mock_coll.index_information = AsyncMock(return_value=self._make_index_info())
        with patch("api.routers.monitor.DbDescriptor.find") as mock_find, \
             patch("api.routers.monitor.DbDescriptor.get_pymongo_collection", return_value=mock_coll):
            mock_find.return_value.count = AsyncMock(return_value=349)
            resp = await client.get("/monitor/health", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert data["status"] == "GREEN"
        assert data["document_count"] == 349
        assert data["collection_name"] == "descriptor"
        assert data["index_count"] == 3
        assert isinstance(data["indexes"], list)

    async def test_indexes_contain_names_and_keys(self, client):
        mock_coll = AsyncMock()
        mock_coll.index_information = AsyncMock(return_value=self._make_index_info())
        with patch("api.routers.monitor.DbDescriptor.find") as mock_find, \
             patch("api.routers.monitor.DbDescriptor.get_pymongo_collection", return_value=mock_coll):
            mock_find.return_value.count = AsyncMock(return_value=100)
            resp = await client.get("/monitor/health", headers={"X-API-KEY": API_KEY})
        idx_names = [i["name"] for i in resp.json()["indexes"]]
        assert "_id_" in idx_names
        assert "idx_key" in idx_names

    async def test_returns_red_when_mongo_down(self, client):
        with patch("api.routers.monitor.CONFIG", {"mongo": {"status": "RED"}}):
            resp = await client.get("/monitor/health", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert resp.status_code == 200       # health vrátí 200 i při RED stavu
        assert data["status"] == "RED"
        assert data["document_count"] == 0
        assert data["indexes"] == []

    async def test_missing_api_key_returns_4xx(self, client):
        with patch("api.routers.monitor.is_api_authorized", return_value=False):
            resp = await client.get("/monitor/health")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /monitor/dict/{dictionary}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMonitorDictDetail:

    STATS_RESULT = [
        {"_id": None, "count": 249, "active": 245, "inactive": 4,
         "last_modified": datetime(2024, 6, 1, tzinfo=timezone.utc)}
    ]
    SAMPLE_RESULT = [
        {"key": "AT"}, {"key": "CZ"}, {"key": "DE"},
    ]

    async def test_returns_200_for_existing_dictionary(self, client):
        with patch("api.routers.monitor._aggregate",
                   side_effect=[self.STATS_RESULT, self.SAMPLE_RESULT]):
            resp = await client.get("/monitor/dict/country", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 200

    async def test_response_contains_correct_counts(self, client):
        with patch("api.routers.monitor._aggregate",
                   side_effect=[self.STATS_RESULT, self.SAMPLE_RESULT]):
            resp = await client.get("/monitor/dict/country", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert data["dictionary"] == "country"
        assert data["count"] == 249
        assert data["active"] == 245
        assert data["inactive"] == 4

    async def test_sample_keys_returned(self, client):
        with patch("api.routers.monitor._aggregate",
                   side_effect=[self.STATS_RESULT, self.SAMPLE_RESULT]):
            resp = await client.get("/monitor/dict/country", headers={"X-API-KEY": API_KEY})
        data = resp.json()
        assert "AT" in data["sample_keys"]
        assert "CZ" in data["sample_keys"]

    async def test_not_found_returns_404(self, client):
        with patch("api.routers.monitor._aggregate", side_effect=[[], []]):
            resp = await client.get("/monitor/dict/neexistuje", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 404

    async def test_missing_api_key_returns_4xx(self, client):
        with patch("api.routers.monitor.is_api_authorized", return_value=False):
            resp = await client.get("/monitor/dict/country")
        assert resp.status_code in (401, 403)

    async def test_mongo_red_returns_503(self, client):
        with patch("api.routers.monitor.CONFIG", {"mongo": {"status": "RED"}}):
            resp = await client.get("/monitor/dict/country", headers={"X-API-KEY": API_KEY})
        assert resp.status_code == 503
