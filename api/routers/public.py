from __future__ import annotations

import logging
from typing import Annotated, Union, List

from fastapi import APIRouter, Path, Query
from sysnet_pyutils.models.general import ErrorModel, ApiError

from api.commons import create_query
from api.model.dictionary import DescriptorType
from api.model.odm import DbDescriptor

logging.basicConfig(
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO)


router = APIRouter(tags=['public'])

LOGGER = logging.getLogger(__name__)


@router.get(
    path='/descriptor/{dictionary}/{key}',
    response_model=DescriptorType,
    responses={'default': {'model': ErrorModel}},
    summary='Vrátí konkrétní deskriptor',
)
async def get_descriptor(
        dictionary: Annotated[
            str,
            Path(title='Kód slovníku', description='Kód řízeného slovníku')],
        key: Annotated[
            str,
            Path(title='Kód deskriptoru', description='Kód deskriptoru z řízeného slovníku')]
) -> Union[DescriptorType, ErrorModel]:
    LOGGER.info(f'GET /descriptor')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if key in [None, '']:
        raise ApiError(code=400, message='Missing key')
    reply = await DbDescriptor.by_key(dictionary=dictionary, key=key)
    if (reply is None) or (not reply):
        LOGGER.info(f"GET /descriptor/{dictionary}/{key} NOT FOUND")
        raise  ApiError(code=404, message='DescriptorType not found')
    LOGGER.info(f"GET /descriptor/{dictionary}/{key} FOUND")
    out = reply.document
    return out


@router.get(
    path='/descriptor/{dictionary}',
    response_model=List[DescriptorType],
    responses={'default': {'model': ErrorModel}},
    summary='Prohledává slovník (autocomplete)',
)
async def get_descriptor_dictionary_list(
        dictionary: Annotated[
            str,
            Path(title='Kód slovníku', description='Kód řízeného slovníku')],
        query: Annotated[
            Union[str, None], Query(title='Vyhledávaný text', description='Text k vyhledání')] = None,
        key: Annotated[
            Union[str, None], Query(title='Vyhledávaný klíč', description='Klíčové slovo k vyhledání')] = None,
        lang: Annotated[
            Union[str, None], Query(title='Jazyk deskriptoru', description='Jazyk deskriptoru k vyhledání')] = None,
        active: Annotated[
            Union[bool, None], Query(title='Aktivní/neaktivní deskriptory', description='Aktivní/neaktivní deskriptory k vyhledání')] = None,
        skip: Annotated[
            Union[int, None], Query(title='Počet přeskočených výsledků')] = None,
        limit: Annotated[
            Union[int, None], Query(title='Maximální počet vrácených výsledků')] = None,
) -> Union[List[DescriptorType], ErrorModel]:
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if skip is None:
        skip = 0
    if limit is None:
        limit = 999
    query, paging, sort = create_query(dictionary=dictionary, key=key, lang=lang, active=active, search=query, skip=skip, limit=limit)
    reply = await DbDescriptor.by_query(query=query, paging=paging, sort=sort)
    if reply is None or not bool(reply):
        raise ApiError(code=404, message='Nothing found')
    if reply.count == 0:
        raise ApiError(code=404, message='Nothing found')
    return reply
