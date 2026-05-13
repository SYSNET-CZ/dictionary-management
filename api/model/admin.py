from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DictionaryBreakdown(BaseModel):
    """Statistiky jednoho řízeného slovníku."""

    dictionary: str = Field(description='Kód řízeného slovníku')
    count: int = Field(description='Celkový počet deskriptorů')
    active: int = Field(description='Počet aktivních deskriptorů')
    inactive: int = Field(description='Počet neaktivních deskriptorů')
    last_modified: Optional[datetime] = Field(default=None, description='Datum poslední změny (UTC)')


class AdminStatsOut(BaseModel):
    """Agregované statistiky kolekce deskriptorů."""

    generated_at: datetime = Field(description='Čas vygenerování statistiky (UTC)')
    period_hours: int = Field(description='Délka okna pro "nedávno upravené" záznamy (hodiny)')
    total_descriptors: int = Field(description='Celkový počet deskriptorů ve všech slovnících')
    total_dictionaries: int = Field(description='Počet různých slovníků')
    active_descriptors: int = Field(description='Počet aktivních deskriptorů')
    inactive_descriptors: int = Field(description='Počet neaktivních deskriptorů')
    recently_added: int = Field(description='Nově vložené záznamy v posledních period_hours hodinách (version=1)')
    recently_modified: int = Field(description='Upravené záznamy v posledních period_hours hodinách (version>1)')
    by_dictionary: List[DictionaryBreakdown] = Field(
        description='Přehled statistik per slovník, seřazeno abecedně'
    )


class IndexInfo(BaseModel):
    """Informace o MongoDB indexu."""

    name: str = Field(description='Název indexu')
    keys: dict = Field(description='Pole a směr řazení')


class AdminHealthOut(BaseModel):
    """Stav databáze a kolekce."""

    status: str = Field(description='Celkový stav služby (GREEN / RED)')
    mongo_status: str = Field(description='Stav MongoDB připojení')
    collection_name: str = Field(description='Název MongoDB kolekce')
    document_count: int = Field(description='Aktuální počet dokumentů v kolekci')
    index_count: int = Field(description='Počet indexů na kolekci')
    indexes: List[IndexInfo] = Field(description='Seznam indexů s jejich klíči')
    version: str = Field(description='Verze aplikace')


class DictionaryDetailOut(BaseModel):
    """Detailní statistiky jednoho slovníku."""

    dictionary: str = Field(description='Kód řízeného slovníku')
    count: int = Field(description='Celkový počet deskriptorů')
    active: int = Field(description='Počet aktivních deskriptorů')
    inactive: int = Field(description='Počet neaktivních deskriptorů')
    last_modified: Optional[datetime] = Field(default=None, description='Datum poslední změny (UTC)')
    sample_keys: List[str] = Field(description='Ukázka posledních 10 upravených klíčů')
