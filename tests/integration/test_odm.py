"""
Integracni testy ODM vrstvy (DbDescriptor) - vyzaduji realnou MongoDB.

Spusteni pouze integracnich testu:
    pytest -m integration

Spusteni vcetne jednotkovych testu:
    pytest
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from api.model.dictionary import DescriptorBaseType, DescriptorValueType


pytestmark = pytest.mark.integration


def make_base(key="AT", dictionary="country", active=True) -> DescriptorBaseType:
    return DescriptorBaseType(
        key=key,
        key_alt=key.lower(),
        dictionary=dictionary,
        active=active,
        values=[DescriptorValueType(lang="cs", value=f"Hodnota {key}", value_alt=None)],
    )


@pytest.mark.asyncio
class TestDbDescriptorInsertAndFind:

    async def test_insert_one_and_by_key(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("CZ", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="CZ")
        assert found is not None
        assert found.key == "CZ"
        assert found.dictionary == "country"

    async def test_by_key_not_found_returns_none(self, beanie_db):
        from api.model.odm import DbDescriptor
        found = await DbDescriptor.by_key(dictionary="country", key="XX_NEEXISTUJE")
        assert found is None

    async def test_by_key_alt(self, beanie_db):
        """by_key hleda take podle key_alt."""
        from api.model.odm import DbDescriptor
        base = make_base("SK", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        # Hleda pres key_alt (= "sk" dle make_base)
        found = await DbDescriptor.by_key(dictionary="country", key="sk")
        assert found is not None
        assert found.key == "SK"

    async def test_version_increments_on_insert(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("DE", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="DE")
        assert found.version == 1

    async def test_timestamp_set_on_insert(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("FR", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="FR")
        assert found.timestamp is not None


@pytest.mark.asyncio
class TestDbDescriptorActivate:

    async def test_activate_true(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("PL", "country", active=False)
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="PL")
        assert found.active is False

        updated = await found.activate(doit=True)
        assert updated.active is True

        # Overeni persistence v DB
        from_db = await DbDescriptor.by_key(dictionary="country", key="PL")
        assert from_db.active is True

    async def test_activate_false(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("HU", "country", active=True)
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="HU")
        updated = await found.activate(doit=False)
        assert updated.active is False

        from_db = await DbDescriptor.by_key(dictionary="country", key="HU")
        assert from_db.active is False

    async def test_activate_increments_version(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("RO", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="RO")
        v_before = found.version
        await found.activate(doit=False)

        from_db = await DbDescriptor.by_key(dictionary="country", key="RO")
        assert from_db.version == v_before + 1


@pytest.mark.asyncio
class TestDbDescriptorReplace:

    async def test_replace_updates_values(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("IT", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="IT")
        found.values = [DescriptorValueType(lang="cs", value="Italie (aktualizovano)", value_alt=None)]
        await found.replace()

        from_db = await DbDescriptor.by_key(dictionary="country", key="IT")
        assert from_db.values[0].value == "Italie (aktualizovano)"

    async def test_replace_increments_version(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("ES", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="ES")
        v_before = found.version
        found.key_alt = "SPA"
        await found.replace()

        from_db = await DbDescriptor.by_key(dictionary="country", key="ES")
        assert from_db.version == v_before + 1
        assert from_db.key_alt == "SPA"


@pytest.mark.asyncio
class TestDbDescriptorDelete:

    async def test_delete_removes_from_db(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("PT", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="PT")
        assert found is not None

        result = await found.delete(None)
        assert result.acknowledged is True

        after = await DbDescriptor.by_key(dictionary="country", key="PT")
        assert after is None


@pytest.mark.asyncio
class TestDbDescriptorExport:

    async def _insert_batch(self):
        from api.model.odm import DbDescriptor
        for key, dictionary in [("A1", "alpha"), ("A2", "alpha"), ("B1", "beta")]:
            base = make_base(key, dictionary)
            doc = DbDescriptor(**base.model_dump())
            await DbDescriptor.insert_one(doc)

    async def test_export_all_returns_all(self, beanie_db):
        from api.model.odm import DbDescriptor
        await self._insert_batch()
        result = await DbDescriptor.export_all()
        assert len(result) == 3

    async def test_export_all_empty_returns_empty_list(self, beanie_db):
        from api.model.odm import DbDescriptor
        result = await DbDescriptor.export_all()
        assert result == []

    async def test_export_dictionary_filters_correctly(self, beanie_db):
        from api.model.odm import DbDescriptor
        await self._insert_batch()
        result = await DbDescriptor.export_dictionary(dictionary="alpha")
        assert len(result) == 2
        assert all(r.dictionary == "alpha" for r in result)

    async def test_export_dictionary_nonexistent_returns_empty(self, beanie_db):
        from api.model.odm import DbDescriptor
        result = await DbDescriptor.export_dictionary(dictionary="neexistujici")
        assert result == []

    async def test_dictionary_list_returns_aggregation(self, beanie_db):
        from api.model.odm import DbDescriptor
        await self._insert_batch()
        result = await DbDescriptor.dictionary_list()
        dict_ids = {r.dictionary for r in result}
        assert "alpha" in dict_ids
        assert "beta" in dict_ids

    async def test_dictionary_returns_sorted_by_key(self, beanie_db):
        from api.model.odm import DbDescriptor
        for key in ["C", "A", "B"]:
            base = make_base(key, "sorted_test")
            doc = DbDescriptor(**base.model_dump())
            await DbDescriptor.insert_one(doc)

        result = await DbDescriptor.get_by_dictionary(dictionary="sorted_test")
        keys = [r.key for r in result]
        assert keys == sorted(keys)


@pytest.mark.asyncio
class TestDbDescriptorDocument:

    async def test_document_property_returns_descriptor_type(self, beanie_db):
        from api.model.odm import DbDescriptor
        from api.model.dictionary import DescriptorType
        base = make_base("NL", "country")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="country", key="NL")
        descriptor = found.document
        assert isinstance(descriptor, DescriptorType)
        assert descriptor.key == "NL"


@pytest.mark.asyncio
class TestDbDescriptorByQuery:
    """Testy pro ODM metodu by_query - pouzivana verejnym endpointem pro vyhledavani."""

    async def _seed(self, dictionary="q_test"):
        from api.model.odm import DbDescriptor
        for key, active in [("QA", True), ("QB", True), ("QC", False)]:
            base = make_base(key, dictionary, active)
            doc = DbDescriptor(**base.model_dump())
            await DbDescriptor.insert_one(doc)

    async def test_by_query_returns_all(self, beanie_db):
        from api.model.odm import DbDescriptor
        from init import paging_to_mongo
        await self._seed()
        query = {'dictionary': 'q_test'}
        paging = paging_to_mongo(skip=0, limit=100)
        sort = ('key', 1)
        result = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
        assert len(result) == 3

    async def test_by_query_filters_active(self, beanie_db):
        from api.model.odm import DbDescriptor
        from init import paging_to_mongo
        await self._seed()
        query = {'$and': [{'dictionary': 'q_test'}, {'active': True}]}
        paging = paging_to_mongo(skip=0, limit=100)
        sort = ('key', 1)
        result = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
        assert len(result) == 2
        assert all(r.active for r in result)

    async def test_by_query_respects_limit(self, beanie_db):
        from api.model.odm import DbDescriptor
        from init import paging_to_mongo
        await self._seed()
        query = {'dictionary': 'q_test'}
        paging = paging_to_mongo(skip=0, limit=2)
        sort = ('key', 1)
        result = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
        assert len(result) == 2

    async def test_by_query_respects_skip(self, beanie_db):
        from api.model.odm import DbDescriptor
        from init import paging_to_mongo
        await self._seed()
        query = {'dictionary': 'q_test'}
        paging = paging_to_mongo(skip=2, limit=100)
        sort = ('key', 1)
        result = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
        assert len(result) == 1

    async def test_by_query_empty_result(self, beanie_db):
        from api.model.odm import DbDescriptor
        from init import paging_to_mongo
        query = {'dictionary': 'neexistujici'}
        paging = paging_to_mongo(skip=0, limit=100)
        sort = ('key', 1)
        result = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
        assert result == []


@pytest.mark.asyncio
class TestDbDescriptorByIdentifier:

    async def test_by_identifier_found(self, beanie_db):
        from api.model.odm import DbDescriptor
        base = make_base("ID_TST", "id_test")
        doc = DbDescriptor(**base.model_dump())
        await DbDescriptor.insert_one(doc)

        found = await DbDescriptor.by_key(dictionary="id_test", key="ID_TST")
        assert found is not None

        by_id = await DbDescriptor.by_identifier(found.identifier)
        assert by_id is not None
        assert by_id.key == "ID_TST"
        assert by_id.identifier == found.identifier

    async def test_by_identifier_not_found(self, beanie_db):
        from api.model.odm import DbDescriptor
        result = await DbDescriptor.by_identifier("neexistujici-uuid-0000")
        assert result is None
