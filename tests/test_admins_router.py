"""
Testy admin endpointu.
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

from api.model.dictionary import (
    DescriptorBaseType, DescriptorType, DescriptorValueType,
    ReplyImported, StatusEnum, ImportedItem,
)

VALID_API_KEY = "test-api-key"


def make_descriptor(key="AT", dictionary="country") -> DescriptorType:
    return DescriptorType(
        identifier="test-uuid", key=key, key_alt=f"{key}T",
        dictionary=dictionary, active=True,
        values=[DescriptorValueType(lang="cs", value="Test", value_alt=None)],
    )


def make_db_doc(key="AT", dictionary="country", activated=True):
    doc = MagicMock()
    doc.document = make_descriptor(key=key, dictionary=dictionary)
    doc.key = key
    doc.key_alt = f"{key}T"
    doc.dictionary = dictionary
    doc.active = activated
    doc.values = [DescriptorValueType(lang="cs", value="Test", value_alt=None)]
    doc.model_dump.return_value = {
        "identifier": "test-uuid", "key": key, "key_alt": f"{key}T",
        "dictionary": dictionary, "active": activated,
        "values": [{"lang": "cs", "value": "Test", "value_alt": None}],
        "version": 1, "timestamp": "2024-01-01T00:00:00", "is_consolidated": True,
    }
    doc.__bool__ = lambda self: True
    return doc


def make_mock_db_class(existing_doc=None):
    """Mock DbDescriptor tridy pro admins router."""
    mock_cls = MagicMock()
    mock_cls.return_value = MagicMock()
    mock_cls.by_key = AsyncMock(return_value=existing_doc)
    mock_cls.insert_one = AsyncMock(return_value=None)
    return mock_cls


def auth_headers():
    return {"X-API-KEY": VALID_API_KEY}


@pytest_asyncio.fixture
async def client():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    def mock_is_authorized(key):
        return key == VALID_API_KEY

    with patch("api.main.lifespan", mock_lifespan), \
         patch("api.routers.admins.is_api_authorized", side_effect=mock_is_authorized):
        from api.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c


@pytest.mark.asyncio
class TestAuthorization:

    async def test_missing_api_key_returns_4xx(self, client):
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.delete("/descriptor/country/AT")
        # FastAPI vraci 401 (APIKeyHeader), ne 403
        assert resp.status_code in (401, 403, 422)

    async def test_invalid_api_key_returns_403(self, client):
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.delete(
                "/descriptor/country/AT",
                headers={"X-API-KEY": "wrong-key"}
            )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestDeleteDescriptor:

    async def test_delete_existing(self, client):
        doc = make_db_doc()
        delete_result = MagicMock()
        delete_result.acknowledged = True
        doc.delete = AsyncMock(return_value=delete_result)

        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.delete("/descriptor/country/AT", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json() is True

    async def test_delete_not_found_returns_404(self, client):
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.delete("/descriptor/country/XX", headers=auth_headers())
        assert resp.status_code == 404

    async def test_delete_missing_dictionary(self, client):
        resp = await client.delete("/descriptor//AT", headers=auth_headers())
        assert resp.status_code in (404, 400)


@pytest.mark.asyncio
class TestPatchActivate:

    async def test_activate_existing(self, client):
        doc = make_db_doc(activated=False)
        activated_doc = make_db_doc(activated=True)
        doc.activate = AsyncMock(return_value=activated_doc)

        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.patch(
                "/descriptor/activate/country/AT?doit=true",
                headers=auth_headers()
            )
        assert resp.status_code == 200

    async def test_activate_not_found_returns_404(self, client):
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.patch(
                "/descriptor/activate/country/XX?doit=true",
                headers=auth_headers()
            )
        assert resp.status_code == 404

    async def test_deactivate(self, client):
        doc = make_db_doc(activated=True)
        deactivated = make_db_doc(activated=False)
        doc.activate = AsyncMock(return_value=deactivated)

        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.patch(
                "/descriptor/activate/country/AT?doit=false",
                headers=auth_headers()
            )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestPostDescriptor:

    def _body(self, key="NEW"):
        return {
            "key": key, "key_alt": "", "dictionary": "country",
            "active": True,
            "values": [{"lang": "cs", "value": "Nova zeme", "value_alt": None}]
        }

    async def test_create_new(self, client):
        new_doc = make_db_doc(key="NEW")
        new_doc.identifier = "new-uuid"
        mock_db = make_mock_db_class(existing_doc=None)
        mock_db.return_value = new_doc
        mock_db.return_value.document = make_descriptor(key="NEW")

        with patch("api.routers.admins.DbDescriptor", mock_db):
            resp = await client.post(
                "/descriptor/country",
                json=self._body("NEW"),
                headers=auth_headers()
            )
        assert resp.status_code == 200

    async def test_create_existing_returns_409(self, client):
        existing = make_db_doc(key="AT")
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=existing)):
            resp = await client.post(
                "/descriptor/country",
                json=self._body("AT"),
                headers=auth_headers()
            )
        assert resp.status_code == 409

    async def test_missing_body_returns_4xx(self, client):
        # Endpoint ma body=None jako default, vraci 400 (ne 422)
        resp = await client.post("/descriptor/country", headers=auth_headers())
        assert resp.status_code in (400, 422)

    async def test_missing_key_returns_400(self, client):
        body = {"key": "", "key_alt": "", "dictionary": "country", "active": True, "values": []}
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.post(
                "/descriptor/country",
                json=body,
                headers=auth_headers()
            )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestPutDescriptor:

    def _body(self, key="AT"):
        return {
            "key": key, "key_alt": "AUT", "dictionary": "country",
            "active": True,
            "values": [{"lang": "cs", "value": "Aktualizovano", "value_alt": None}]
        }

    async def test_update_existing(self, client):
        doc = make_db_doc(key="AT")
        updated = make_db_doc(key="AT")
        doc.replace = AsyncMock(return_value=updated)
        doc.values = [DescriptorValueType(lang="cs", value="Stara", value_alt=None)]

        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.put(
                "/descriptor/country/AT",
                json=self._body("AT"),
                headers=auth_headers()
            )
        assert resp.status_code == 200

    async def test_update_not_found_returns_404(self, client):
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=None)):
            resp = await client.put(
                "/descriptor/country/XX",
                json=self._body("XX"),
                headers=auth_headers()
            )
        assert resp.status_code == 404

    async def test_key_mismatch_returns_400(self, client):
        doc = make_db_doc(key="AT")
        with patch("api.routers.admins.DbDescriptor.by_key", AsyncMock(return_value=doc)):
            resp = await client.put(
                "/descriptor/country/AT",
                json=self._body("DE"),
                headers=auth_headers()
            )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestExport:

    def _make_base(self, key="AT"):
        return DescriptorBaseType(
            key=key, key_alt="", dictionary="country", active=True, values=[]
        )

    async def test_export_all(self, client):
        items = [self._make_base("AT"), self._make_base("DE")]
        with patch("api.routers.admins.DbDescriptor.export_all", AsyncMock(return_value=items)):
            resp = await client.get("/export", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_export_all_empty_returns_404(self, client):
        with patch("api.routers.admins.DbDescriptor.export_all", AsyncMock(return_value=[])):
            resp = await client.get("/export", headers=auth_headers())
        assert resp.status_code == 404

    async def test_export_dictionary(self, client):
        items = [self._make_base("AT")]
        with patch("api.routers.admins.DbDescriptor.export_dictionary", AsyncMock(return_value=items)):
            resp = await client.get("/export/country", headers=auth_headers())
        assert resp.status_code == 200

    async def test_export_dictionary_empty_returns_404(self, client):
        with patch("api.routers.admins.DbDescriptor.export_dictionary", AsyncMock(return_value=[])):
            resp = await client.get("/export/country", headers=auth_headers())
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestImportDescriptors:

    def _body(self):
        return [{"key": "AT", "key_alt": "AUT", "dictionary": "country",
                 "active": True,
                 "values": [{"lang": "cs", "value": "Rakousko", "value_alt": None}]}]

    async def test_import_new(self, client):
        result = ReplyImported(
            count_added=1,
            added=[ImportedItem(dictionary="country", key="AT", status=StatusEnum.ADDED)]
        )
        # Patch v modulu, kde je importovano
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post("/import", json=self._body(), headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["count_added"] == 1

    async def test_import_with_replace_query_param(self, client):
        result = ReplyImported(count_replaced=1)
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import?replace=true", json=self._body(), headers=auth_headers()
            )
        assert resp.status_code == 200

    async def test_import_empty_body_returns_400(self, client):
        resp = await client.post("/import", json=[], headers=auth_headers())
        assert resp.status_code == 400

    async def test_import_missing_body_returns_4xx(self, client):
        # body=None default -> 400 (ne 422)
        resp = await client.post("/import", headers=auth_headers())
        assert resp.status_code in (400, 422)


@pytest.mark.asyncio
class TestImportDomino:

    def _body(self):
        return {"dictionary": "country", "value_key_text": "Rakousko|AT\nNemecko|DE"}

    async def test_import_domino_basic(self, client):
        result = ReplyImported(count_added=2)
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post("/import/domino", json=self._body(), headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["count_added"] == 2

    async def test_import_domino_replace_as_query(self, client):
        result = ReplyImported(count_replaced=2)
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import/domino?replace=true", json=self._body(), headers=auth_headers()
            )
        assert resp.status_code == 200

    async def test_import_domino_missing_dict_returns_400(self, client):
        body = {"dictionary": None, "value_key_text": "Hodnota|KOD"}
        resp = await client.post("/import/domino", json=body, headers=auth_headers())
        assert resp.status_code == 400

    async def test_import_domino_missing_data_returns_400(self, client):
        body = {"dictionary": "country", "value_key_text": None}
        resp = await client.post("/import/domino", json=body, headers=auth_headers())
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestImportLegacy:
    """Testy endpointu POST /import/legacy."""

    def _legacy_body(self, n=1):
        """Vraci n zaznamu ve starem formatu descriptor-service v1."""
        return [
            {
                "dictionary": "country",
                "key": f"X{i}",
                "key_alt": f"XX{i}",
                "value": f"Zeme {i}",
                "value_en": f"Country {i}",
                "active": True,
            }
            for i in range(n)
        ]

    async def test_import_legacy_added(self, client):
        result = ReplyImported(
            count_added=1,
            added=[ImportedItem(dictionary="country", key="X0", status=StatusEnum.ADDED)],
        )
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import/legacy", json=self._legacy_body(1), headers=auth_headers()
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count_added"] == 1

    async def test_import_legacy_replace_mode(self, client):
        result = ReplyImported(count_replaced=2)
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import/legacy?replace=true",
                json=self._legacy_body(2),
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["count_replaced"] == 2

    async def test_import_legacy_empty_body_returns_400(self, client):
        resp = await client.post("/import/legacy", json=[], headers=auth_headers())
        assert resp.status_code == 400

    async def test_import_legacy_missing_body_returns_4xx(self, client):
        resp = await client.post("/import/legacy", headers=auth_headers())
        assert resp.status_code in (400, 422)

    async def test_import_legacy_unauthorized(self, client):
        resp = await client.post(
            "/import/legacy",
            json=self._legacy_body(1),
            headers={"X-API-KEY": "wrong"},
        )
        assert resp.status_code == 403

    async def test_import_legacy_transforms_to_values_structure(self, client):
        """Verifikuje, ze import_data dostane spravne transformovana data."""
        captured = []

        async def capturing_import_data(data, replace):
            captured.extend(data)
            return ReplyImported(count_added=len(data))

        with patch("api.routers.admins.import_data", side_effect=capturing_import_data):
            resp = await client.post(
                "/import/legacy",
                json=[{
                    "dictionary": "country",
                    "key": "CZ",
                    "key_alt": "CZE",
                    "value": "Ceska republika",
                    "value_en": "Czech republic",
                    "active": True,
                }],
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert len(captured) == 1
        item = captured[0]
        # Musi byt DescriptorBaseType s values strukturou
        langs = {v.lang: v.value for v in item.values}
        assert langs.get("cs") == "Ceska republika"
        assert langs.get("en") == "Czech republic"
        assert item.key == "CZ"
        assert item.dictionary == "country"

    async def test_import_legacy_bom_sanitized(self, client):
        """Zaznam s BOM v nazvu slovniku musi byt sanitizovan pred zapisem."""
        captured = []

        async def capturing_import_data(data, replace):
            captured.extend(data)
            return ReplyImported(count_added=len(data))

        bom = "\ufeff"
        with patch("api.routers.admins.import_data", side_effect=capturing_import_data):
            resp = await client.post(
                "/import/legacy",
                json=[{
                    "dictionary": f"noti{bom}ce_roles",
                    "key": "ORG",
                    "value": "Organizace",
                }],
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert captured[0].dictionary == "notice_roles"

    async def test_import_legacy_empty_value_en_produces_only_cs(self, client):
        """Prazdne value_en nesmi produkovat en zaznam v values."""
        captured = []

        async def capturing_import_data(data, replace):
            captured.extend(data)
            return ReplyImported(count_added=1)

        with patch("api.routers.admins.import_data", side_effect=capturing_import_data):
            await client.post(
                "/import/legacy",
                json=[{"dictionary": "cloning", "key": "F", "value": "Z fotografii", "value_en": ""}],
                headers=auth_headers(),
            )
        assert len(captured[0].values) == 1
        assert captured[0].values[0].lang == "cs"


@pytest.mark.asyncio
class TestImportLegacyFile:
    """Testy endpointu POST /import/legacy/file (UploadFile)."""

    def _ndjson_bytes(self, n=2) -> bytes:
        import json
        lines = [
            json.dumps({
                "dictionary": "country", "key": f"X{i}", "key_alt": f"XX{i}",
                "value": f"Zeme {i}", "value_en": f"Country {i}", "active": True,
            })
            for i in range(n)
        ]
        return "\n".join(lines).encode("utf-8")

    def _upload(self, content: bytes, filename="descriptor-service_1.json"):
        from io import BytesIO
        return {"file": (filename, BytesIO(content), "application/json")}

    async def test_import_file_added(self, client):
        result = ReplyImported(
            count_added=2,
            added=[
                ImportedItem(dictionary="country", key="X0", status=StatusEnum.ADDED),
                ImportedItem(dictionary="country", key="X1", status=StatusEnum.ADDED),
            ],
        )
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import/legacy/file",
                files=self._upload(self._ndjson_bytes(2)),
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["count_added"] == 2

    async def test_import_file_replace_mode(self, client):
        result = ReplyImported(count_replaced=2)
        with patch("api.routers.admins.import_data", AsyncMock(return_value=result)):
            resp = await client.post(
                "/import/legacy/file?replace=true",
                files=self._upload(self._ndjson_bytes(2)),
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["count_replaced"] == 2

    async def test_import_file_empty_lines_ignored(self, client):
        import json
        line = json.dumps({"dictionary": "country", "key": "CZ", "value": "CR", "active": True})
        content = f"\n\n{line}\n\n".encode("utf-8")
        captured = []

        async def capturing(data, replace):
            captured.extend(data)
            return ReplyImported(count_added=len(data))

        with patch("api.routers.admins.import_data", side_effect=capturing):
            resp = await client.post(
                "/import/legacy/file",
                files=self._upload(content),
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        assert len(captured) == 1

    async def test_import_file_transforms_to_values(self, client):
        import json
        captured = []

        async def capturing(data, replace):
            captured.extend(data)
            return ReplyImported(count_added=1)

        line = json.dumps({
            "dictionary": "country", "key": "CZ", "key_alt": "CZE",
            "value": "Ceska republika", "value_en": "Czech republic", "active": True,
        })
        with patch("api.routers.admins.import_data", side_effect=capturing):
            resp = await client.post(
                "/import/legacy/file",
                files=self._upload(line.encode("utf-8")),
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        langs = {v.lang: v.value for v in captured[0].values}
        assert langs["cs"] == "Ceska republika"
        assert langs["en"] == "Czech republic"

    async def test_import_file_invalid_json_returns_400(self, client):
        content = b"toto neni json\nani toto"
        resp = await client.post(
            "/import/legacy/file",
            files=self._upload(content),
            headers=auth_headers(),
        )
        assert resp.status_code == 400

    async def test_import_file_empty_file_returns_400(self, client):
        content = b"\n\n\n"
        resp = await client.post(
            "/import/legacy/file",
            files=self._upload(content),
            headers=auth_headers(),
        )
        assert resp.status_code == 400

    async def test_import_file_unauthorized(self, client):
        resp = await client.post(
            "/import/legacy/file",
            files=self._upload(self._ndjson_bytes(1)),
            headers={"X-API-KEY": "wrong"},
        )
        assert resp.status_code == 403
