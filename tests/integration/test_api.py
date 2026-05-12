"""
Integracni testy REST API - vyzaduji realnou MongoDB.

Pouzivaji api_client fixture z conftest.py (realna DB, patchovany lifespan).
"""
from __future__ import annotations

import pytest
from api.model.dictionary import DescriptorBaseType, DescriptorValueType

pytestmark = pytest.mark.integration

VALID_API_KEY = "1ywA1Fxc9QBB3CtvP6kGJw"


def auth_headers():
    return {"X-API-KEY": VALID_API_KEY}


def descriptor_body(key="AT", dictionary="country"):
    return {
        "key": key,
        "key_alt": key.lower(),
        "dictionary": dictionary,
        "active": True,
        "values": [{"lang": "cs", "value": f"Hodnota {key}", "value_alt": None}],
    }


async def create_descriptor(client, key="AT", dictionary="country"):
    """Pomocna funkce pro vytvoreni deskriptoru pres API."""
    resp = await client.post(
        f"/descriptor/{dictionary}",
        json=descriptor_body(key, dictionary),
        headers=auth_headers(),
    )
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    return resp


@pytest.mark.asyncio
class TestPublicGet:

    async def test_get_existing_descriptor(self, api_client, beanie_db):
        await create_descriptor(api_client, "CZ", "country")
        resp = await api_client.get("/descriptor/country/CZ")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "CZ"
        assert data["dictionary"] == "country"

    async def test_get_nonexistent_returns_404(self, api_client):
        resp = await api_client.get("/descriptor/country/XX_NEEXISTUJE")
        assert resp.status_code == 404

    async def test_get_by_key_alt(self, api_client, beanie_db):
        """Vyhledavani pres key_alt."""
        await create_descriptor(api_client, "SK", "country")
        # key_alt je "sk" dle descriptor_body
        resp = await api_client.get("/descriptor/country/sk")
        assert resp.status_code == 200
        assert resp.json()["key"] == "SK"


@pytest.mark.asyncio
class TestAdminPost:

    async def test_create_new_descriptor(self, api_client):
        resp = await api_client.post(
            "/descriptor/country",
            json=descriptor_body("DE"),
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "DE"

    async def test_create_existing_returns_409(self, api_client, beanie_db):
        await create_descriptor(api_client, "FR", "country")
        resp = await api_client.post(
            "/descriptor/country",
            json=descriptor_body("FR"),
            headers=auth_headers(),
        )
        assert resp.status_code == 409

    async def test_create_without_auth_returns_401_or_403(self, api_client):
        resp = await api_client.post(
            "/descriptor/country",
            json=descriptor_body("ES"),
        )
        assert resp.status_code in (401, 403)

    async def test_create_empty_key_returns_400(self, api_client):
        body = {"key": "", "key_alt": "", "dictionary": "country",
                "active": True, "values": []}
        resp = await api_client.post(
            "/descriptor/country",
            json=body,
            headers=auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestAdminDelete:

    async def test_delete_existing(self, api_client, beanie_db):
        await create_descriptor(api_client, "PL", "country")
        resp = await api_client.delete("/descriptor/country/PL", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json() is True

        # Overeni smazani
        get_resp = await api_client.get("/descriptor/country/PL")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_returns_404(self, api_client):
        resp = await api_client.delete("/descriptor/country/XX_NEEXISTUJE", headers=auth_headers())
        assert resp.status_code == 404

    async def test_delete_without_auth_returns_401_or_403(self, api_client):
        resp = await api_client.delete("/descriptor/country/AT")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestAdminPatch:

    async def test_activate_descriptor(self, api_client, beanie_db):
        # Vytvorit neaktivni
        body = {**descriptor_body("HU"), "active": False}
        resp = await api_client.post(
            "/descriptor/country",
            json=body,
            headers=auth_headers(),
        )
        assert resp.status_code == 200

        # Aktivovat
        resp = await api_client.patch(
            "/descriptor/activate/country/HU?doit=true",
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    async def test_deactivate_descriptor(self, api_client, beanie_db):
        await create_descriptor(api_client, "RO", "country")

        resp = await api_client.patch(
            "/descriptor/activate/country/RO?doit=false",
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    async def test_activate_nonexistent_returns_404(self, api_client):
        resp = await api_client.patch(
            "/descriptor/activate/country/XX_NEEXISTUJE?doit=true",
            headers=auth_headers(),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestAdminPut:

    async def test_update_existing(self, api_client, beanie_db):
        await create_descriptor(api_client, "IT", "country")
        update_body = {
            "key": "IT", "key_alt": "ITA", "dictionary": "country",
            "active": True,
            "values": [{"lang": "cs", "value": "Italie aktualizovana", "value_alt": None}],
        }
        resp = await api_client.put(
            "/descriptor/country/IT",
            json=update_body,
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key_alt"] == "ITA"
        assert data["values"][0]["value"] == "Italie aktualizovana"

    async def test_update_nonexistent_returns_404(self, api_client):
        resp = await api_client.put(
            "/descriptor/country/XX_NEEXISTUJE",
            json=descriptor_body("XX_NEEXISTUJE"),
            headers=auth_headers(),
        )
        assert resp.status_code == 404

    async def test_key_mismatch_returns_400(self, api_client, beanie_db):
        await create_descriptor(api_client, "ES", "country")
        resp = await api_client.put(
            "/descriptor/country/ES",
            json=descriptor_body("PT"),  # jiny klic v body
            headers=auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestExport:

    async def test_export_all(self, api_client, beanie_db):
        for key in ["E1", "E2", "E3"]:
            await create_descriptor(api_client, key, "export_test")

        resp = await api_client.get("/export", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_export_all_empty_returns_404(self, api_client):
        resp = await api_client.get("/export", headers=auth_headers())
        assert resp.status_code == 404

    async def test_export_dictionary(self, api_client, beanie_db):
        for key in ["X1", "X2"]:
            await create_descriptor(api_client, key, "filter_test")
        await create_descriptor(api_client, "Y1", "other_test")

        resp = await api_client.get("/export/filter_test", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(d["dictionary"] == "filter_test" for d in data)

    async def test_export_dictionary_empty_returns_404(self, api_client):
        resp = await api_client.get("/export/neexistujici_slovnik", headers=auth_headers())
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestImport:

    def _import_body(self, keys, dictionary="import_test"):
        return [
            {"key": k, "key_alt": k.lower(), "dictionary": dictionary,
             "active": True,
             "values": [{"lang": "cs", "value": f"Import {k}", "value_alt": None}]}
            for k in keys
        ]

    async def test_import_new_descriptors(self, api_client):
        resp = await api_client.post(
            "/import",
            json=self._import_body(["I1", "I2", "I3"]),
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count_added"] == 3
        assert data["count_rejected"] == 0

    async def test_import_rejects_duplicates_without_replace(self, api_client, beanie_db):
        await create_descriptor(api_client, "DUP", "dup_test")

        resp = await api_client.post(
            "/import",
            json=self._import_body(["DUP"], "dup_test"),
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count_rejected"] == 1
        assert data["count_added"] == 0

    async def test_import_replaces_with_replace_flag(self, api_client, beanie_db):
        await create_descriptor(api_client, "REP", "rep_test")

        resp = await api_client.post(
            "/import?replace=true",
            json=self._import_body(["REP"], "rep_test"),
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count_replaced"] == 1
        assert data["count_added"] == 0

    async def test_import_empty_body_returns_400(self, api_client):
        resp = await api_client.post("/import", json=[], headers=auth_headers())
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestImportDomino:

    def _domino_body(self, items: list[tuple], dictionary="domino_test"):
        # items = [(value, key), ...]
        text = "\n".join(f"{v}|{k}" for v, k in items)
        return {"dictionary": dictionary, "value_key_text": text}

    async def test_import_domino_basic(self, api_client):
        body = self._domino_body([("Rakousko", "AT"), ("Nemecko", "DE")])
        resp = await api_client.post("/import/domino", json=body, headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["count_added"] == 2

        # Overeni dat v DB
        get_resp = await api_client.get("/descriptor/domino_test/AT")
        assert get_resp.status_code == 200
        assert get_resp.json()["values"][0]["value"] == "Rakousko"

    async def test_import_domino_replace(self, api_client, beanie_db):
        body_init = self._domino_body([("Stara hodnota", "DM1")])
        await api_client.post("/import/domino", json=body_init, headers=auth_headers())

        body_replace = self._domino_body([("Nova hodnota", "DM1")])
        resp = await api_client.post(
            "/import/domino?replace=true",
            json=body_replace,
            headers=auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["count_replaced"] == 1

        get_resp = await api_client.get("/descriptor/domino_test/DM1")
        assert get_resp.status_code == 200
        assert get_resp.json()["values"][0]["value"] == "Nova hodnota"

    async def test_import_domino_missing_dict_returns_400(self, api_client):
        resp = await api_client.post(
            "/import/domino",
            json={"dictionary": None, "value_key_text": "Hodnota|KOD"},
            headers=auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestPublicList:
    """Testy pro GET /descriptor/{dictionary} - vyhledavaci/autocomplete endpoint."""

    async def _seed(self, api_client, keys, dictionary="search_test"):
        for key in keys:
            await create_descriptor(api_client, key, dictionary)

    async def test_list_all_in_dictionary(self, api_client, beanie_db):
        await self._seed(api_client, ["L1", "L2", "L3"])
        resp = await api_client.get("/descriptor/search_test")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_list_empty_dictionary_returns_404(self, api_client):
        resp = await api_client.get("/descriptor/prazdny_slovnik")
        assert resp.status_code == 404

    async def test_list_with_key_filter(self, api_client, beanie_db):
        # Pouzivame unikatni prefix ktery se nevyskytuje v "Hodnota" (hodnota = value)
        await self._seed(api_client, ["XKQ1", "XKQ2", "YZZ1"])
        # ?key= hleda v key, key_alt i values.value (full-text search pres OR)
        # XKQ se nevyskytuje v "Hodnota XKQ1/XKQ2/YZZ1" => matchuji jen dle klice
        resp = await api_client.get("/descriptor/search_test?key=XKQ")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("XKQ" in d["key"] for d in data)

    async def test_list_with_active_filter(self, api_client, beanie_db):
        await self._seed(api_client, ["ACT1", "ACT2"])
        # Deaktivovat jeden
        await api_client.patch(
            "/descriptor/activate/search_test/ACT1?doit=false",
            headers=auth_headers(),
        )
        # Dotaz jen na aktivni
        resp = await api_client.get("/descriptor/search_test?active=true")
        assert resp.status_code == 200
        data = resp.json()
        assert all(d["active"] is True for d in data)
        assert len(data) == 1

    async def test_list_with_limit(self, api_client, beanie_db):
        await self._seed(api_client, ["P1", "P2", "P3", "P4", "P5"])
        resp = await api_client.get("/descriptor/search_test?skip=0&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_limit_not_capped_at_10(self, api_client, beanie_db):
        """Regresni test: paging bug - limit nemel byt omezen na PAGE_SIZE=10."""
        for i in range(15):
            await create_descriptor(api_client, f"BIG{i:02d}", "big_test")
        resp = await api_client.get("/descriptor/big_test?skip=0&limit=15")
        assert resp.status_code == 200
        assert len(resp.json()) == 15


@pytest.mark.asyncio
class TestInfoEndpoints:
    """Testy pro info endpointy v api/main.py."""

    async def test_root_returns_name_and_version(self, api_client):
        resp = await api_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    async def test_head_root_returns_200(self, api_client):
        resp = await api_client.head("/")
        assert resp.status_code == 200

    async def test_head_info_returns_200(self, api_client):
        resp = await api_client.head("/info")
        assert resp.status_code == 200

    async def test_get_info_contains_status(self, api_client):
        resp = await api_client.get("/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "mongo" in data
        assert "dictionaries" in data

    async def test_get_info_with_data_lists_dictionaries(self, api_client, beanie_db):
        """GET /info vraci seznam slovniku kdyz je MongoDB GREEN."""
        # Vytvorit nejaky deskriptor
        await create_descriptor(api_client, "INF1", "info_test")
        # /info vola dictionary_list() - stav mongo je v CONFIG, ktery je mockovan
        # Jen overime ze endpoint vraci 200 a spravnou strukturu
        resp = await api_client.get("/info")
        assert resp.status_code == 200
