"""
Testy Pydantic modelů — api/model/dictionary.py.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.model.dictionary import (
    DescriptorBaseType,
    DescriptorType,
    DescriptorValueType,
    DictionaryType,
    DominoImport,
    ImportedItem,
    ReplyImported,
    StatusEnum,
)


class TestDescriptorValueType:

    def test_valid_value(self):
        v = DescriptorValueType(lang="cs", value="Rakousko", value_alt="Rak. spolk. republika")
        assert v.lang == "cs"
        assert v.value == "Rakousko"

    def test_value_alt_none_allowed(self):
        v = DescriptorValueType(lang="en", value="Austria", value_alt=None)
        assert v.value_alt is None


class TestDescriptorBaseType:

    def test_valid_descriptor(self):
        d = DescriptorBaseType(
            key="AT",
            key_alt="AUT",
            dictionary="country",
            active=True,
            values=[DescriptorValueType(lang="cs", value="Rakousko", value_alt=None)],
        )
        assert d.key == "AT"
        assert d.dictionary == "country"
        assert len(d.values) == 1

    def test_model_dump_contains_expected_keys(self):
        d = DescriptorBaseType(
            key="CZ",
            key_alt=None,
            dictionary="country",
            active=True,
            values=[],
        )
        dump = d.model_dump()
        assert "key" in dump
        assert "dictionary" in dump
        assert "active" in dump
        assert "values" in dump


class TestDescriptorType:

    def test_includes_identifier(self):
        d = DescriptorType(
            identifier="test-uuid",
            key="DE",
            key_alt="DEU",
            dictionary="country",
            active=True,
            values=[],
        )
        assert d.identifier == "test-uuid"

    def test_identifier_optional_none(self):
        d = DescriptorType(
            identifier=None,
            key="DE",
            key_alt=None,
            dictionary="country",
            active=True,
            values=[],
        )
        assert d.identifier is None


class TestDictionaryType:

    def test_alias_id(self):
        d = DictionaryType.model_validate({"_id": "country", "count": 42})
        assert d.dictionary == "country"
        assert d.count == 42

    def test_model_dump_uses_alias(self):
        d = DictionaryType.model_validate({"_id": "country", "count": 5})
        dump = DictionaryType.model_dump(d)
        assert "dictionary" in dump


class TestStatusEnum:

    def test_all_values(self):
        assert StatusEnum.ADDED.value == "added"
        assert StatusEnum.REPLACED.value == "replaced"
        assert StatusEnum.REJECTED.value == "rejected"
        assert StatusEnum.ERROR.value == "failed"


class TestReplyImported:

    def test_defaults(self):
        r = ReplyImported()
        assert r.count_added == 0
        assert r.count_replaced == 0
        assert r.count_rejected == 0
        assert r.count_error == 0
        assert r.added is None
        assert r.replaced is None
        assert r.rejected is None
        assert r.error is None

    def test_with_items(self):
        item = ImportedItem(dictionary="country", key="AT", status=StatusEnum.ADDED)
        r = ReplyImported(count_added=1, added=[item])
        assert r.count_added == 1
        assert len(r.added) == 1
        assert r.added[0].status == StatusEnum.ADDED


class TestDominoImport:

    def test_valid(self):
        d = DominoImport(dictionary="country", value_key_text="Rakous|AT\nNěmecko|DE")
        assert d.dictionary == "country"
        assert "AT" in d.value_key_text

    def test_none_allowed(self):
        d = DominoImport(dictionary=None, value_key_text=None)
        assert d.dictionary is None
