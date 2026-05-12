"""
Testy pro api/dependencies.py -- import_data logika.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import os
os.environ.setdefault("DICT_VERSION", "test")
os.environ.setdefault("INSTANCE", "TEST")
os.environ.setdefault("MONGO_PASSWORD", "test")

from api.model.dictionary import (
    DescriptorBaseType,
    DescriptorValueType,
    StatusEnum,
)


def make_item(key="AT", dictionary="country") -> DescriptorBaseType:
    return DescriptorBaseType(
        key=key,
        key_alt="",
        dictionary=dictionary,
        active=True,
        values=[DescriptorValueType(lang="cs", value="Testovaci hodnota", value_alt=None)],
    )


def make_db_doc(key="AT"):
    doc = MagicMock()
    doc.key = key
    doc.key_alt = ""
    doc.active = True
    doc.values = []
    doc.replace = AsyncMock(return_value=doc)
    return doc


def make_mock_db_class(existing_docs: dict):
    """
    Vraci mock DbDescriptor tridy. existing_docs = {key: doc_mock | None}
    """
    mock_cls = MagicMock()
    mock_cls.return_value = MagicMock()  # DbDescriptor(**b1) vrati mock

    async def by_key(dictionary, key):
        return existing_docs.get(key)

    mock_cls.by_key = AsyncMock(side_effect=by_key)
    mock_cls.insert_one = AsyncMock(return_value=None)
    return mock_cls


@pytest.mark.asyncio
class TestImportData:

    async def test_adds_new_descriptor(self):
        from api.dependencies import import_data

        mock_db = make_mock_db_class({})  # nic neexistuje
        with patch("api.dependencies.DbDescriptor", mock_db):
            result = await import_data(data=[make_item("NEW")], replace=False)

        assert result.count_added == 1
        assert result.count_rejected == 0
        assert len(result.added) == 1
        assert result.added[0].status == StatusEnum.ADDED
        assert result.added[0].key == "NEW"

    async def test_rejects_existing_when_replace_false(self):
        from api.dependencies import import_data

        existing = make_db_doc("AT")
        mock_db = make_mock_db_class({"AT": existing})
        with patch("api.dependencies.DbDescriptor", mock_db):
            result = await import_data(data=[make_item("AT")], replace=False)

        assert result.count_rejected == 1
        assert result.count_added == 0
        assert result.rejected[0].status == StatusEnum.REJECTED

    async def test_replaces_existing_when_replace_true(self):
        from api.dependencies import import_data

        existing = make_db_doc("AT")
        mock_db = make_mock_db_class({"AT": existing})
        with patch("api.dependencies.DbDescriptor", mock_db):
            result = await import_data(data=[make_item("AT")], replace=True)

        assert result.count_replaced == 1
        assert result.count_added == 0
        assert result.replaced[0].status == StatusEnum.REPLACED

    async def test_error_handling(self):
        from api.dependencies import import_data

        mock_db = MagicMock()
        mock_db.by_key = AsyncMock(side_effect=Exception("DB error"))
        mock_db.insert_one = AsyncMock()

        with patch("api.dependencies.DbDescriptor", mock_db):
            result = await import_data(data=[make_item("AT")], replace=False)

        assert result.count_error == 1
        assert result.error[0].status == StatusEnum.ERROR

    async def test_mixed_batch(self):
        from api.dependencies import import_data

        existing = make_db_doc("AT")
        mock_db = make_mock_db_class({"AT": existing})  # AT existuje, NEW ne
        with patch("api.dependencies.DbDescriptor", mock_db):
            result = await import_data(
                data=[make_item("AT"), make_item("NEW")],
                replace=False
            )

        assert result.count_added == 1
        assert result.count_rejected == 1

    async def test_empty_data_returns_zeros(self):
        from api.dependencies import import_data

        result = await import_data(data=[], replace=False)
        assert result.count_added == 0
        assert result.count_rejected == 0
        assert result.count_replaced == 0
        assert result.count_error == 0
