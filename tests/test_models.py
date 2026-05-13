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


class TestLegacyDescriptorImport:
    """Testy modelu LegacyDescriptorImport a jeho transformacni metody."""

    from api.model.dictionary import LegacyDescriptorImport  # noqa: F401 — docstring odkaz

    # --- to_descriptor_base ---

    def test_both_langs_produced(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(
            dictionary="country", key="CZ", key_alt="CZE",
            value="Ceska republika", value_en="Czech republic",
        )
        out = item.to_descriptor_base()
        assert out.dictionary == "country"
        assert out.key == "CZ"
        assert out.key_alt == "CZE"
        langs = {v.lang: v.value for v in out.values}
        assert langs == {"cs": "Ceska republika", "en": "Czech republic"}

    def test_empty_value_en_produces_only_cs(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="cloning", key="F", value="Z fotografii", value_en="")
        out = item.to_descriptor_base()
        assert len(out.values) == 1
        assert out.values[0].lang == "cs"

    def test_none_value_en_produces_only_cs(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="cloning", key="R", value="Opakovani")
        out = item.to_descriptor_base()
        assert len(out.values) == 1

    def test_none_value_produces_no_cs_entry(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="x", key="K", value=None, value_en=None)
        out = item.to_descriptor_base()
        assert out.values == []

    def test_active_default_is_true(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="x", key="K", value="v")
        out = item.to_descriptor_base()
        assert out.active is True

    def test_active_false_preserved(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="x", key="K", value="v", active=False)
        out = item.to_descriptor_base()
        assert out.active is False

    def test_none_key_alt_becomes_empty_string(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="x", key="K", key_alt=None, value="v")
        out = item.to_descriptor_base()
        assert out.key_alt == ""

    # --- sanitize validator ---

    def test_bom_stripped_from_dictionary(self):
        from api.model.dictionary import LegacyDescriptorImport
        bom = "\ufeff"
        item = LegacyDescriptorImport(
            dictionary=f"noti{bom}ce_roles", key="ORG", value="org"
        )
        assert item.dictionary == "notice_roles"

    def test_bom_stripped_from_key(self):
        from api.model.dictionary import LegacyDescriptorImport
        bom = "\ufeff"
        item = LegacyDescriptorImport(dictionary="x", key=f"K{bom}EY", value="v")
        assert item.key == "KEY"

    def test_whitespace_stripped(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(
            dictionary="  country  ", key=" CZ ", value=" Ceska republika ", value_en=" Czech "
        )
        assert item.dictionary == "country"
        assert item.key == "CZ"
        assert item.value == "Ceska republika"
        assert item.value_en == "Czech"

    def test_none_passes_through_sanitizer(self):
        from api.model.dictionary import LegacyDescriptorImport
        item = LegacyDescriptorImport(dictionary="x", key="K", key_alt=None, value=None)
        assert item.key_alt is None
        assert item.value is None

    def test_missing_key_raises(self):
        from api.model.dictionary import LegacyDescriptorImport
        with pytest.raises(Exception):
            LegacyDescriptorImport(dictionary="x")  # key chybi

    def test_missing_dictionary_raises(self):
        from api.model.dictionary import LegacyDescriptorImport
        with pytest.raises(Exception):
            LegacyDescriptorImport(key="K")  # dictionary chybi


# ---------------------------------------------------------------------------
# GlobalModel — normalizace datetime na UTC
# ---------------------------------------------------------------------------

class TestGlobalModelDatetimeNormalization:
    """Ověří, že DescriptorBaseType (a jeho potomci) normalizují datetime na UTC."""

    def test_naive_datetime_is_converted_to_utc(self):
        """Naivní datetime bez tzinfo musí být převeden na UTC (předpokládá se Europe/Prague)."""
        from datetime import datetime, timezone
        from api.model.dictionary import DescriptorBaseType, DescriptorValueType

        # Naivní čas — žádné tzinfo
        naive_dt = datetime(2024, 6, 15, 10, 0, 0)
        desc = DescriptorBaseType(
            key="CZ", key_alt="", dictionary="country", active=True,
            values=[DescriptorValueType(lang="cs", value="test", value_alt=None)],
        )
        # GlobalModel validator se aplikuje na pole — ověříme na volném testu modelu s datetime
        from sysnet_pyutils.globalmodel.global_model import GlobalModel
        from pydantic import Field

        class _TestModel(GlobalModel):
            ts: datetime

        m = _TestModel(ts=naive_dt)
        # Výsledek musí být timezone-aware UTC
        assert m.ts.tzinfo is not None
        assert m.ts.utcoffset().total_seconds() == 0

    def test_aware_datetime_is_normalized_to_utc(self):
        """Timezone-aware datetime v Europe/Prague musí být normalizován na UTC."""
        from datetime import datetime, timezone
        import pytz
        from sysnet_pyutils.globalmodel.global_model import GlobalModel

        prague = pytz.timezone("Europe/Prague")
        prague_dt = prague.localize(datetime(2024, 6, 15, 12, 0, 0))  # CEST = UTC+2

        class _TestModel(GlobalModel):
            ts: datetime

        m = _TestModel(ts=prague_dt)
        assert m.ts.tzinfo is not None
        # 12:00 CEST → 10:00 UTC
        assert m.ts.hour == 10
        assert m.ts.utcoffset().total_seconds() == 0

    def test_descriptor_base_type_inherits_global_model(self):
        """DescriptorBaseType musí dědit z GlobalModel."""
        from sysnet_pyutils.globalmodel.global_model import GlobalModel
        from api.model.dictionary import DescriptorBaseType
        assert issubclass(DescriptorBaseType, GlobalModel)
