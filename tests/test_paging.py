"""
Testy pro funkci paging_to_mongo (init.py).

Ověřuje opravené chování po bugfixu: skip/limit jsou předávány správně
a PAGE_SIZE nepřepisuje explicitně zadaný limit.
"""
from __future__ import annotations

import pytest
from init import paging_to_mongo, PAGE_SIZE


class TestPagingToMongo:
    """Testy skip/limit stylu stránkování."""

    def test_default_no_params_returns_page_size(self):
        """Bez parametrů vrací skip=0, limit=PAGE_SIZE."""
        result = paging_to_mongo()
        assert result["skip"] == 0
        assert result["limit"] == PAGE_SIZE

    def test_skip_zero_limit_explicit(self):
        """skip=0, limit=50 — limit musí být 50, ne PAGE_SIZE."""
        result = paging_to_mongo(skip=0, limit=50)
        assert result["skip"] == 0
        assert result["limit"] == 50

    def test_skip_nonzero_limit_explicit(self):
        """skip=20, limit=100 — obě hodnoty zachovány."""
        result = paging_to_mongo(skip=20, limit=100)
        assert result["skip"] == 20
        assert result["limit"] == 100

    def test_limit_999_not_capped_to_page_size(self):
        """Regression test: limit=999 nesmí být přepsán na PAGE_SIZE=10."""
        result = paging_to_mongo(skip=0, limit=999)
        assert result["limit"] == 999, (
            f"limit byl přepsán na {result['limit']}, očekáváno 999 (bugfix regression)"
        )

    def test_only_skip_provided(self):
        """Pouze skip — limit default PAGE_SIZE."""
        result = paging_to_mongo(skip=5)
        assert result["skip"] == 5
        assert result["limit"] == PAGE_SIZE

    def test_only_limit_provided(self):
        """Pouze limit — skip=0."""
        result = paging_to_mongo(limit=25)
        assert result["skip"] == 0
        assert result["limit"] == 25

    def test_result_keys_present(self):
        """Výstup musí obsahovat všechny očekávané klíče."""
        result = paging_to_mongo(skip=0, limit=10)
        assert set(result.keys()) == {"start", "page_size", "page", "skip", "limit"}


class TestPagingToMongoPageStyle:
    """Testy start/page/page_size stylu stránkování."""

    def test_page_zero_start_zero(self):
        """Stránka 0, start 0 — skip=0, limit=PAGE_SIZE."""
        result = paging_to_mongo(start=0, page=0, page_size=10)
        assert result["skip"] == 0
        assert result["limit"] == 10

    def test_page_one(self):
        """Stránka 1 — skip=10."""
        result = paging_to_mongo(start=0, page=1, page_size=10)
        assert result["skip"] == 10
        assert result["limit"] == 10

    def test_page_two(self):
        """Stránka 2 — skip=20."""
        result = paging_to_mongo(start=0, page=2, page_size=10)
        assert result["skip"] == 20
        assert result["limit"] == 10

    def test_custom_page_size(self):
        """Vlastní velikost stránky."""
        result = paging_to_mongo(start=0, page=0, page_size=25)
        assert result["skip"] == 0
        assert result["limit"] == 25

    def test_start_midpage(self):
        """Začátek uprostřed stránky zkrátí limit."""
        result = paging_to_mongo(start=5, page=0, page_size=10)
        assert result["skip"] == 5
        assert result["limit"] == 5  # PAGE_SIZE - start


class TestPagingToMongoEdgeCases:
    """Hraniční případy."""

    def test_skip_zero_only(self):
        """skip=0 explicitně — aktivuje skip/limit větev."""
        result = paging_to_mongo(skip=0)
        assert result["skip"] == 0
        assert result["limit"] == PAGE_SIZE

    def test_all_none(self):
        """Všechna None — defaults."""
        result = paging_to_mongo(start=None, page_size=None, page=None, skip=None, limit=None)
        assert result["skip"] == 0
        assert result["limit"] == PAGE_SIZE
