from __future__ import annotations

from typing import List, Optional, Union, Annotated

from pydantic import BaseModel, Field, RootModel
from sysnet_pyutils.models.general import BaseEnum


class StatusEnum(BaseEnum):
    ADDED = 'added'
    REPLACED = 'replaced'
    REJECTED = 'rejected'
    ERROR = 'failed'


class DictionaryType(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Název řízeného slovníku', alias="_id")]
    count: Annotated[Union[int, None], Field(description='Počet položek řízeného slovníku')]


class DominoImport(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Název řízeného slovníku', examples=['country'])]
    value_key_text: Annotated[
        Union[str, None],
        Field(
            description='Obsah řízeného slovníku',
            examples=['Průvodní dopis|pd\nObálka|ob'])]


class ImportedItem(BaseModel):
    dictionary: Annotated[Union[str, None], Field(description='Řízený slovník', examples=['country'])]
    key: Annotated[Union[str, None], Field(description='Identifikátor deskriptoru', examples=['AT'])]
    status: Annotated[Union[StatusEnum, None], Field(description='Stav importu', examples=['replaced'])]


class ReplyImported(BaseModel):
    count_added: Optional[int] = Field(0, description='počet nově přidaných deskriptorů', examples=[25])
    count_replaced: Optional[int] = Field(0, description='počet nahrazených deskriptorů', examples=[5])
    count_rejected: Optional[int] = Field(0, description='počet zamítnutých deskriptorů', examples=[10])
    count_error: Optional[int] = Field(0, description='počet chyb importu', examples=[1])
    added: Optional[List[ImportedItem]] = None
    replaced: Optional[List[ImportedItem]] = None
    rejected: Optional[List[ImportedItem]] = None
    error: Optional[List[ImportedItem]] = None


class DescriptorValueType(BaseModel):
    lang: Optional[str] = Field(..., description='jazyk hodnoty deskriptoru', examples=['cs'])
    value: Optional[str] = Field(..., description='Hodnota deskriptoru pro jazyk', examples=['Rakousko'])
    value_alt: Optional[str] = Field(..., description='Alternativní hodnota deskriptoru pro jazyk', examples=['Rakouská spolková republika'])


class DescriptorBaseType(BaseModel):
    key: Optional[str] = Field(..., description='Hlavní klíč deskriptoru', examples=['AT'])
    key_alt: Optional[str] = Field(..., description='Alternativní klíč deskriptoru', examples=['AUT'])
    dictionary: Optional[str] = Field(..., description='Kód řízeného slovníku', examples=['country'])
    active: Optional[bool] = Field(..., description='Descriptor is active', examples=[True])
    values: Optional[List[DescriptorValueType]] = Field(..., description='Seznam hodnot deskriptoru')


class DescriptorType(DescriptorBaseType):
    identifier: Optional[str] = Field(..., description='Identifikátor deskriptoru')


class FieldDictionaryImportPostRequest(RootModel):
    root: List[DescriptorType]


class ImportPostRequest(RootModel):
    root: List[DescriptorType]
