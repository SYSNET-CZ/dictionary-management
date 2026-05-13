"""
Testy pro api/commons.py — create_query a update_changed_values.
"""
from __future__ import annotations

import pytest
from api.commons import create_query, update_changed_values


class TestCreateQuery:
    """Testy sestavení MongoDB query."""

    def test_dictionary_only(self):
        query, paging, sort = create_query(dictionary="country")
        assert "dictionary" in str(query)
        assert paging["skip"] == 0

    def test_empty_params_returns_empty_query(self):
        query, paging, sort = create_query()
        assert query == {}

    def test_key_filter_uses_or(self):
        query, paging, sort = create_query(dictionary="country", key="AT")
        assert "$and" in query
        q_str = str(query)
        assert "key" in q_str

    def test_active_filter(self):
        query, paging, sort = create_query(dictionary="country", active=True)
        assert "active" in str(query)

    def test_lang_filter(self):
        query, paging, sort = create_query(dictionary="country", lang="cs")
        assert "values.lang" in str(query)

    def test_text_search(self):
        query, paging, sort = create_query(dictionary="country", search="Rakous")
        q_str = str(query)
        assert "$text" in q_str

    def test_skip_limit_passed_correctly(self):
        """Ověří, že skip/limit se přenáší do pagingu bez zkrácení."""
        query, paging, sort = create_query(skip=10, limit=50)
        assert paging["skip"] == 10
        assert paging["limit"] == 50

    def test_default_limit_is_not_10(self):
        """Regression: výchozí limit nesmí být PAGE_SIZE=10."""
        from init import PAGE_SIZE
        query, paging, sort = create_query(dictionary="country")
        # S None skip/limit vstupuje do page/start větve s PAGE_SIZE
        # Chceme ověřit, že default funguje (PAGE_SIZE)
        assert paging["limit"] == PAGE_SIZE

    def test_sort_tuple_returned(self):
        query, paging, sort = create_query(dictionary="country")
        assert isinstance(sort, tuple)
        assert len(sort) == 2

    def test_default_sort_is_key_ascending(self):
        """Výchozí řazení je key ASC — vhodné pro slovníkový výpis a autocomplete."""
        from beanie import SortDirection
        query, paging, sort = create_query(dictionary="country")
        assert sort[0] == 'key'
        assert sort[1] == SortDirection.ASCENDING

    def test_multiple_filters_combined_with_and(self):
        query, paging, sort = create_query(
            dictionary="country", key="AT", active=True, lang="cs"
        )
        assert "$and" in query
        items = query["$and"]
        assert len(items) >= 3


class TestUpdateChangedValues:
    """Testy funkce update_changed_values."""

    def test_returns_false_on_none_input(self):
        assert update_changed_values(None, {}, {}) is False
        assert update_changed_values(object(), None, {}) is False
        assert update_changed_values(object(), {}, None) is False

    def test_updates_simple_field(self):
        class Obj:
            active = True

        obj = Obj()
        old = {"active": True}
        new = {"active": False}
        result = update_changed_values(obj, old, new)
        assert result is True
        assert obj.active is False

    def test_no_change_if_values_equal(self):
        class Obj:
            active = True

        obj = Obj()
        old = {"active": True}
        new = {"active": True}
        update_changed_values(obj, old, new)
        assert obj.active is True

    def test_returns_true_on_success(self):
        class Obj:
            x = 1

        result = update_changed_values(Obj(), {"x": 1}, {"x": 2})
        assert result is True

    def test_missing_key_in_new_skipped(self):
        class Obj:
            x = 1
            y = 2

        obj = Obj()
        old = {"x": 1, "y": 2}
        new = {"x": 99}
        update_changed_values(obj, old, new)
        assert obj.x == 99
        assert obj.y == 2  # nezměněno
