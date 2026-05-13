from __future__ import annotations

import unicodedata
from typing import List, Optional, Union, Annotated

from pydantic import BaseModel, Field, RootModel, field_validator
from sysnet_pyutils.globalmodel.global_model import GlobalModel
from sysnet_pyutils.models.general import BaseEnum


class StatusEnum(BaseEnum):
    ADDED = 'added'
    REPLACED = 'replaced'
    REJECTED = 'rejected'
    ERROR = 'failed'


class DictionaryType(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Nazev rizeneho slovniku', alias="_id")]
    count: Annotated[Union[int, None], Field(description='Pocet polozek rizeneho slovniku')]


class DominoImport(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Nazev rizeneho slovniku', examples=['country'])]
    value_key_text: Annotated[
        Union[str, None],
        Field(
            description='Obsah rizeneho slovniku',
            examples=['Pruvodci dopis|pd\nObalka|ob'])]


class ImportedItem(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Rizeny slovnik', examples=['country'])]
    key: Annotated[Union[str, None], Field(description='Identifikator deskriptoru', examples=['AT'])]
    status: Annotated[Union[StatusEnum, None], Field(description='Stav importu', examples=['replaced'])]


class ReplyImported(BaseModel):
    count_added: Optional[int] = Field(0, description='pocet nove pridanych deskriptoru', examples=[25])
    count_replaced: Optional[int] = Field(0, description='pocet nahrazenych deskriptoru', examples=[5])
    count_rejected: Optional[int] = Field(0, description='pocet zamitnutych deskriptoru', examples=[10])
    count_error: Optional[int] = Field(0, description='pocet chyb importu', examples=[1])
    added: Optional[List[ImportedItem]] = None
    replaced: Optional[List[ImportedItem]] = None
    rejected: Optional[List[ImportedItem]] = None
    error: Optional[List[ImportedItem]] = None


class DescriptorValueType(BaseModel):
    lang: Optional[str] = Field(..., description='jazyk hodnoty deskriptoru', examples=['cs'])
    value: Optional[str] = Field(..., description='Hodnota deskriptoru pro jazyk', examples=['Rakousko'])
    value_alt: Optional[str] = Field(..., description='Alternativni hodnota deskriptoru pro jazyk', examples=['Rakouska spolkova republika'])


class DescriptorBaseType(GlobalModel):
    key: Optional[str] = Field(..., description='Hlavni klic deskriptoru', examples=['AT'])
    key_alt: Optional[str] = Field(..., description='Alternativni klic deskriptoru', examples=['AUT'])
    dictionary: Optional[str] = Field(..., description='Kod rizeneho slovniku', examples=['country'])
    active: Optional[bool] = Field(..., description='Descriptor is active', examples=[True])
    values: Optional[List[DescriptorValueType]] = Field(..., description='Seznam hodnot deskriptoru')


class DescriptorType(DescriptorBaseType):
    identifier: Optional[str] = Field(..., description='Identifikator deskriptoru')


class FieldDictionaryImportPostRequest(RootModel):
    root: List[DescriptorType]


class ImportPostRequest(RootModel):
    root: List[DescriptorType]


# ---------------------------------------------------------------------------
# Legacy import -- descriptor-service v1
# ---------------------------------------------------------------------------

def _sanitize_str(v: Optional[str]) -> Optional[str]:
    """Remove BOM (U+FEFF) and surrounding whitespace.

    The legacy export (descriptor-service_1.json) contains at least one
    dictionary name with an embedded U+FEFF byte sequence (ef bb bf in UTF-8).
    The character is zero-width and invisible in most editors.
    """
    if v is None:
        return v
    return v.replace("﻿", "").strip()


class LegacyDescriptorImport(BaseModel):
    """Descriptor format exported from an older version of the service (descriptor-service v1).

    The old format uses flat fields ``value`` (cs) and ``value_en`` (en) instead of
    the ``values: [{lang, value, value_alt}]`` structure.  The ``_id`` field
    (MongoDB ObjectId) and the legacy ``identifier`` (in the form ``dictionary*key``)
    are intentionally ignored -- the new version generates its own UUID identifiers.
    """

    dictionary: str = Field(..., description='Kod rizeneho slovniku', examples=['country'])
    key: str = Field(..., description='Hlavni klic deskriptoru', examples=['CZ'])
    key_alt: Optional[str] = Field(default=None, description='Alternativni klic', examples=['CZE'])
    value: Optional[str] = Field(default=None, description='Hodnota v cestine', examples=['Ceska republika'])
    value_en: Optional[str] = Field(default=None, description='Anglicka hodnota', examples=['Czech republic'])
    active: bool = Field(default=True, description='Aktivni deskriptor')

    @field_validator('dictionary', 'key', 'key_alt', 'value', 'value_en', mode='before')
    @classmethod
    def sanitize(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v)

    def to_descriptor_base(self) -> DescriptorBaseType:
        """Transform the legacy flat format to the current DescriptorBaseType."""
        values: List[DescriptorValueType] = []
        if self.value is not None:
            values.append(DescriptorValueType(lang='cs', value=self.value, value_alt=''))
        if self.value_en:
            values.append(DescriptorValueType(lang='en', value=self.value_en, value_alt=''))
        return DescriptorBaseType(
            key=self.key,
            key_alt=self.key_alt or '',
            dictionary=self.dictionary,
            active=self.active,
            values=values,
        )


class LegacyNdjsonImport(BaseModel):
    """Surovy obsah souboru descriptor-service_1.json (NDJSON format).

    Kazdy radek je samostatny JSON objekt ve starem formatu descriptor-service v1.
    Prazdne radky jsou ignorovany. Pouzit pro endpoint POST /import/legacy/ndjson.
    """
    content: str = Field(
        ...,
        description=(
            "Obsah souboru descriptor-service_1.json -- kazdy radek je JSON objekt. "
            "Prazdne radky jsou ignorovany."
        ),
        examples=['{"dictionary":"country","key":"CZ","key_alt":"CZE","value":"Ceska republika","value_en":"Czech republic","active":true}'],
    )

    def parse_items(self) -> List[LegacyDescriptorImport]:
        """Parsuje NDJSON obsah a vraci seznam LegacyDescriptorImport objektu."""
        import json
        items = []
        for lineno, line in enumerate(self.content.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            items.append(LegacyDescriptorImport(**raw))
        return items
