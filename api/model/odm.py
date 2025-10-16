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

class DbDescriptor(Document, DescriptorType):
    identifier: str = Field(
        default_factory=uuid_factory,
        description='Document unique identifier',
        examples=['123e4567-e89b-12d3-a456-426614174000'])
    version: int = 0
    timestamp: datetime = local_now()
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
        log = logging.getLogger(__name__)
        log.info(f"{__name__}.document")
        try:
            dump = self.model_dump()
            out = DescriptorType(**dump)
            log.info(f"{__name__}.document SUCCESS: {type(out)} ")
            return out
        except Exception as e:
            log.error(f"{__name__}.document FAILED: {str(e)}")
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
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary(cls, dictionary: str) -> List[DescriptorType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary_list(cls) -> List[DictionaryType]:
        out = await DbDescriptor.find({}).aggregate(
            [{"$group" : {"_id":"$dictionary", "count":{"$sum":1}}}],
            projection_model=DictionaryType).to_list()
        return out


    @classmethod
    async def export_dictionary(cls, dictionary: str) -> List[DescriptorBaseType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def export_all(cls) -> List[DescriptorBaseType]:
        query = {}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
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


class DbDescriptorSav(Document, DescriptorType):
    identifier: UUID = Field(
        default_factory=uuid_factory,
        description='Document unique identifier',
        examples=['123e4567-e89b-12d3-a456-426614174000'])
    version: int = 0
    timestamp: datetime = local_now()
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
            # LOGGER.error(f"{type(self).__name__}.consolidated FAILED: {type(e)} - {str(e)}")
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
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary(cls, dictionary: str) -> List[DescriptorType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            out_item = DescriptorType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def dictionary_list(cls) -> List[DictionaryType]:
        out = await DbDescriptor.find({}).aggregate(
            [{"$group" : {"_id":"$dictionary", "count":{"$sum":1}}}],
            projection_model=DictionaryType).to_list()
        return out


    @classmethod
    async def export_dictionary(cls, dictionary: str) -> List[DescriptorBaseType]:
        query = {'dictionary': dictionary}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
            out_item = DescriptorBaseType(**dump)
            out.append(out_item)
        return out

    @classmethod
    async def export_all(cls) -> List[DescriptorBaseType]:
        query = {}
        sort = ('key', SortDirection.ASCENDING)
        reply = await cls.find(query).limit(1000).skip(0).sort(sort).to_list()
        out = []
        for item in reply:
            dump = item.model_dump()
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
