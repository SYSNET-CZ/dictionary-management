from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Union, List
from uuid import uuid4, UUID

from beanie import Document, before_event, Insert, Replace, Update, SaveChanges, SortDirection
from beanie.odm.operators.find.comparison import Eq, In
from beanie.odm.operators.find.element import Exists
from beanie.odm.operators.find.logical import Or
from pydantic import Field, ValidationError
from pymongo import IndexModel, ASCENDING
from sysnet_pyutils.utils import local_now, uuid_factory

from api.model.dictionary import DescriptorType, DictionaryType, DescriptorBaseType
from init import COLLATION

LOGGER = logging.getLogger('ODM')

EXPORT_LIMIT = 1000  # maximální počet záznamů při hromadném čtení; při překročení je zalogován warning


class DbDescriptor(Document, DescriptorType):
    identifier: str = Field(
        default_factory=uuid_factory,
        description='Document unique identifier',
        examples=['123e4567-e89b-12d3-a456-426614174000'])
    version: int = 0
    timestamp: datetime = Field(default_factory=local_now)
    is_consolidated: Optional[bool] = Field(default=None, description='Descriptor is consolidated')

    class Settings:
        name = "descriptor"
        indexes = [
            IndexModel(
                keys=[("key", ASCENDING)],
                name="idx_key",
                collation=COLLATION,
            ),
            IndexModel(
                keys=[("dictionary", ASCENDING)],
                name="idx_dictionary",
            ),
            IndexModel(
                keys=[("dictionary", ASCENDING), ("key", ASCENDING)],
                name="idx_dict_key",
            ),
            IndexModel(
                keys=[("identifier", ASCENDING)],
                name="idx_identifier",
            ),
            IndexModel(
                keys=[("$**", ASCENDING)],
                name="idx_wildcard",
                collation=COLLATION,
            ),
            IndexModel(
                [("key", "text"), ("key_alt", "text"), ("dictionary", 'text'), ('values.value', 'text'), ('values.value_alt', 'text')],
                name="idx_text",
                # default_language=None,
                # language_override=None,
                # collation=COLLATION,
            )
        ]

    @before_event(Insert)
    async def init_values(self):
        timestamp = local_now()
        if self.identifier is None:
            self.identifier = str(uuid4())
        self.timestamp = timestamp
        self.version = 1

    @before_event(Replace, Update, SaveChanges)
    async def update_timestamp(self):
        timestamp = local_now()
        self.timestamp = timestamp
        self.version += 1

    @property
    def document(self) -> Optional[DescriptorType]:
        LOGGER.info(f"{type(self).__name__}.document")
        try:
            dump = self.model_dump()
            out = DescriptorType(**dump)
            LOGGER.info(f"{type(self).__name__}.document SUCCESS: {type(out)}")
            return out
        except Exception as e:
            LOGGER.error(f"{type(self).__name__}.document FAILED: {str(e)}")
            return None

    @classmethod
    async def by_identifier(cls, uuid: str) -> Optional[DbDescriptor]:
        query = {'identifier': uuid}
        return await cls.find_one(query)

    @classmethod
    async def all_documents(cls) -> List[Optional[DbDescriptor]]:
        try:
            query = Eq("is_consolidated", True)
            reply = await cls.find(query).to_list()
            return reply
        except ValidationError as e:
            LOGGER.error(f"{type(cls).__name__}.all_documents FAILED Validation: {str(e)}")
            return []
        except Exception as e:
            LOGGER.error(f"{type(cls).__name__}.all_documents FAILED: {type(e)} - {str(e)}")
            return []

    @classmethod
    async def by_key(cls, dictionary: str, key: str) -> Optional[DbDescriptor]:
        query = {'$and': [{'dictionary': dictionary}, {'$or': [{'key': key}, {'key_alt': key}]}]}
        reply = await cls.find_one(query)
        if reply is None:
            return None
        return reply

    @classmethod
    async def by_query(
            cls, query: Union[dict, None], paging: Union[dict, None], sort: Union[tuple, None]) -> List[DescriptorType]:
        reply = await cls.find(query).limit(paging['limit']).skip(paging['skip']).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def get_by_dictionary(cls, dictionary: str) -> List[DescriptorType]:
        """Vraci vsechny deskriptory daneho slovniku serazene podle klice.
        Poznamka: puvodni nazev 'dictionary' byl prejmenovam na 'get_by_dictionary'
        kvuli konfliktu s Beanie ExpressionField pro ODM pole stejneho jmena.
        """
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.get_by_dictionary: výsledek oříznut na {EXPORT_LIMIT} záznamů (dictionary={dictionary!r})")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary_list(cls) -> List[DictionaryType]:
        out = await cls.find({}).aggregate(
            [{"$group" : {"_id":"$dictionary", "count":{"$sum":1}}}],
            projection_model=DictionaryType).to_list()
        return out

    @classmethod
    async def export_dictionary(cls, dictionary: str) -> List[DescriptorBaseType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.export_dictionary: výsledek oříznut na {EXPORT_LIMIT} záznamů (dictionary={dictionary!r})")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def export_all(cls) -> List[DescriptorBaseType]:
        query = {}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.export_all: výsledek oříznut na {EXPORT_LIMIT} záznamů")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def suggest(
            cls, dictionary: str, prefix: str,
            lang: Optional[str] = None, limit: int = 15) -> List[DescriptorType]:
        """Efektivní prefix-matching pro typeahead/autocomplete.

        Používá zakotvený regex ``^prefix`` — MongoDB může využít B-tree index
        (na rozdíl od unanchored regexu, který způsobuje collection scan).
        Vždy filtruje ``active=True`` a řadí výsledky abecedně podle klíče.
        """
        import re
        safe_prefix = re.escape(prefix)
        pattern = f'^{safe_prefix}'
        or_clauses: list = [
            {'values.value': {'$regex': pattern, '$options': 'i'}},
            {'key': {'$regex': pattern, '$options': 'i'}},
            {'key_alt': {'$regex': pattern, '$options': 'i'}},
        ]
        query: dict = {'dictionary': dictionary, 'active': True, '$or': or_clauses}
        if lang not in (None, ''):
            query['values.lang'] = lang
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(limit).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])
            out.append(DescriptorType(**dump))
        return out

    async def activate(self, doit=True, save=True):
        if doit is None:
            doit = True
        self.active = doit
        if save:
            reply = await self.replace()
            return reply
        return self


class DbDescriptorSav(Document, DescriptorType):
    identifier: UUID = Field(
        default_factory=uuid_factory,
        description='Document unique identifier',
        examples=['123e4567-e89b-12d3-a456-426614174000'])
    version: int = 0
    timestamp: datetime = Field(default_factory=local_now)
    is_consolidated: Optional[bool] = Field(default=None, description='Descriptor is consolidated')

    class Settings:
        name = "descriptor"
        indexes = [
            IndexModel(
                keys=[("key", ASCENDING)],
                name="idx_key",
                collation=COLLATION,
            ),
            IndexModel(
                keys=[("dictionary", ASCENDING)],
                name="idx_dictionary",
            ),
            IndexModel(
                keys=[("dictionary", ASCENDING), ("key", ASCENDING)],
                name="idx_dict_key",
            ),
            IndexModel(
                keys=[("identifier", ASCENDING)],
                name="idx_identifier",
            ),
            IndexModel(
                keys=[("$**", ASCENDING)],
                name="idx_wildcard",
                collation=COLLATION,
            ),
            IndexModel(
                [("key", "text"), ("key_alt", "text"), ("dictionary", 'text'), ('values.value', 'text'), ('values.value_alt', 'text')],
                name="idx_text",
                # default_language=None,
                # language_override=None,
                # collation=COLLATION,
            )
        ]

    @before_event(Insert)
    async def init_values(self):
        timestamp = local_now()
        if self.identifier is None:
            self.identifier = uuid4()
        self.timestamp = timestamp
        self.version = 1

    @before_event(Replace, Update, SaveChanges)
    async def update_timestamp(self):
        timestamp = local_now()
        self.timestamp = timestamp
        self.version += 1

    @property
    def document(self) -> Optional[DescriptorType]:
        LOGGER.info(f"{type(self).__name__}.document")
        try:
            dump = self.model_dump()
            dump['identifier'] = str(dump['identifier'])
            out = DescriptorType(**dump)
            LOGGER.info(f"{type(self).__name__}.document SUCCESS: {type(out)}")
            return out
        except Exception as e:
            LOGGER.error(f"{type(self).__name__}.document FAILED: {type(e)} - {str(e)}")
            return None

    @property
    def consolidated(self) -> Optional[DbDescriptor]:
        LOGGER.info(f"{type(self).__name__}.consolidated")
        try:
            dump = self.model_dump()
            dump['identifier'] = str(dump['identifier'])
            out = DbDescriptor(**dump)
            out.is_consolidated = True
            # LOGGER.info(f"{type(self).__name__}.consolidated SUCCESS: {type(out)}")
            return out
        except Exception as e:
            LOGGER.error(f"{type(self).__name__}.consolidated FAILED: {type(e)} - {str(e)}")
            return None

    @classmethod
    async def by_identifier(cls, uuid: UUID) -> Optional[DbDescriptorSav]:
        query = {'identifier': uuid}
        return await cls.find_one(query)

    @classmethod
    async def all_documents(cls) -> List[Optional[DbDescriptorSav]]:
        try:
            query = Or(
                Eq("is_consolidated", False),
                Exists("is_consolidated", False),
                In("is_consolidated", [None, ""])
            )
            reply = await cls.find(query).to_list()
            return reply
        except ValidationError as e:
            LOGGER.error(f"{type(cls).__name__}.all_documents FAILED Validation: {str(e)}")
            return []
        except Exception as e:
            LOGGER.error(f"{type(cls).__name__}.all_documents FAILED: {type(e)} - {str(e)}")
            return []

    @classmethod
    async def by_key(cls, dictionary: str, key: str) -> Optional[DbDescriptorSav]:
        query = {'$and': [{'dictionary': dictionary}, {'$or': [{'key': key}, {'key_alt': key}]}]}
        reply = await cls.find_one(query)
        if reply is None:
            return None
        return reply

    @classmethod
    async def by_query(
            cls, query: Union[dict, None], paging: Union[dict, None], sort: Union[tuple, None]) -> List[DescriptorType]:
        reply = await cls.find(query).limit(paging['limit']).skip(paging['skip']).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def get_by_dictionary(cls, dictionary: str) -> List[DescriptorType]:
        """Vraci vsechny deskriptory daneho slovniku serazene podle klice.
        Poznamka: puvodni nazev 'dictionary' byl prejmenovam na 'get_by_dictionary'
        kvuli konfliktu s Beanie ExpressionField pro ODM pole stejneho jmena.
        """
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.get_by_dictionary: výsledek oříznut na {EXPORT_LIMIT} záznamů (dictionary={dictionary!r})")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary_list(cls) -> List[DictionaryType]:
        out = await cls.find({}).aggregate(
            [{"$group" : {"_id":"$dictionary", "count":{"$sum":1}}}],
            projection_model=DictionaryType).to_list()
        return out

    @classmethod
    async def export_dictionary(cls, dictionary: str) -> List[DescriptorBaseType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.export_dictionary: výsledek oříznut na {EXPORT_LIMIT} záznamů (dictionary={dictionary!r})")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def export_all(cls) -> List[DescriptorBaseType]:
        query = {}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(EXPORT_LIMIT + 1).skip(0).sort(sort).to_list()
        if len(reply) > EXPORT_LIMIT:
            LOGGER.warning(f"{cls.__name__}.export_all: výsledek oříznut na {EXPORT_LIMIT} záznamů")
            reply = reply[:EXPORT_LIMIT]
        out = []
        for item in reply:
            dump = item.model_dump()
            dump['identifier'] = str(dump['identifier'])  # UUID -> str konverze pro stara data
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    async def activate(self, doit=True, save=True):
        if doit is None:
            doit = True
        self.active = doit
        if save:
            reply = await self.replace()
            return reply
        return self
