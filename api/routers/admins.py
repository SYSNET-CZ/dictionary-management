from __future__ import annotations

import logging
from typing import Annotated, Union, List

from fastapi import APIRouter, Path, Depends, Query, Body, File, UploadFile
from sysnet_pyutils.models.general import ErrorModel, ApiError

from api.commons import update_changed_values
from api.dependencies import header_scheme, is_api_authorized, import_data
from api.model.dictionary import (
    DescriptorType, DescriptorBaseType, DescriptorValueType,
    ReplyImported, DominoImport, LegacyDescriptorImport, LegacyNdjsonImport,
)
from api.model.odm import DbDescriptor

logging.basicConfig(
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO)


router = APIRouter(tags=['admins'])

LOGGER = logging.getLogger(__name__)


@router.delete(
    path='/descriptor/{dictionary}/{key}',
    response_model=bool,
    responses={'default': {'model': ErrorModel}},
    summary='Odstrani deskriptor',
)
async def descriptor_delete(
        dictionary: Annotated[
            str,
            Path(title='Kod slovniku', description='Kod rizeneho slovniku')],
        key: Annotated[
            str,
            Path(title='Kod deskriptoru', description='Kod deskriptoru z rizeneho slovniku')],
        api_key: str = Depends(header_scheme)
) -> Union[bool, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    LOGGER.info(f'DELETE /descriptor')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if key in [None, '']:
        raise ApiError(code=400, message='Missing key')
    reply = await DbDescriptor.by_key(dictionary=dictionary, key=key)
    if not reply:
        LOGGER.info(f"DELETE /descriptor/{dictionary}/{key} NOT FOUND")
        raise ApiError(code=404, message=f"DescriptorType {dictionary}/{key} not found")
    LOGGER.info(f"DELETE /descriptor/{dictionary}/{key} FOUND")
    reply1 = await reply.delete()
    return reply1.acknowledged


@router.patch(
    path='/descriptor/activate/{dictionary}/{key}',
    response_model=DescriptorType,
    responses={'default': {'model': ErrorModel}},
    summary='Aktivuje/deaktivuje deskriptor',
)
async def descriptor_patch_activate(
        dictionary: Annotated[
            str,
            Path(title='Kod slovniku', description='Kod rizeneho slovniku')],
        key: Annotated[
            str,
            Path(title='Kod deskriptoru', description='Kod deskriptoru z rizeneho slovniku')],
        doit: Annotated[
            bool,
            Query(
                title='Aktivacni promenna',
                description='Aktivuje/Deaktivuje deskriptor')] = True,
        api_key: str = Depends(header_scheme)
) -> Union[DescriptorType, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    LOGGER.info(f'PATCH /descriptor/activate')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if key in [None, '']:
        raise ApiError(code=400, message='Missing key')
    reply = await DbDescriptor.by_key(dictionary=dictionary, key=key)
    if not reply:
        LOGGER.info(f"PATCH /descriptor/activate/{dictionary}/{key} NOT FOUND")
        raise ApiError(code=404, message=f"DescriptorType {dictionary}/{key} not found")
    LOGGER.info(f"PATCH /descriptor/activate/{dictionary}/{key} FOUND")
    reply1 = await reply.activate(doit=doit)
    out = reply1.document
    return out


@router.post(
    path='/descriptor/{dictionary}',
    response_model=None,
    responses={'default': {'model': ErrorModel}},
    summary='Prida novy deskriptor',
)
async def descriptor_post(
        dictionary: Annotated[
            str,
            Path(title='Kod slovniku', description='Kod rizeneho slovniku')],
        body: Annotated[
            DescriptorBaseType,
            Body(title='Data deskriptoru')] = None,
        api_key: str = Depends(header_scheme)
) -> Union[DescriptorType, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    LOGGER.info(f'POST /descriptor')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if body is None:
        raise ApiError(code=400, message='Missing data')
    if body.key in [None, '']:
        raise ApiError(code=400, message=f"Illegal or missing key")
    key = body.key
    reply = await DbDescriptor.by_key(dictionary=dictionary, key=key)
    if reply:
        LOGGER.info(f"POST /descriptor/{dictionary}/{key} FOUND")
        raise ApiError(code=409, message=f"DescriptorType {dictionary}/{key} already exist")
    try:
        b1 = DescriptorBaseType.model_dump(body)
        dbdoc = DbDescriptor(**b1)
        await DbDescriptor.insert_one(dbdoc)
        out = dbdoc.document
        LOGGER.info(f'POST /descriptor/{dictionary} done: {str(dbdoc.identifier)}')
        return out
    except Exception as e:
        LOGGER.error(f'POST /descriptor/{dictionary} FAILED: {str(e)}')
        raise ApiError(code=500, message=str(e))


@router.put(
    path='/descriptor/{dictionary}/{key}',
    response_model=DescriptorType,
    responses={'default': {'model': ErrorModel}},
    summary='Aktualizuje deskriptor',
)
async def descriptor_put(
        dictionary: Annotated[
            str,
            Path(title='Kod slovniku', description='Kod rizeneho slovniku')],
        key: Annotated[
            str,
            Path(title='Kod deskriptoru', description='Kod deskriptoru z rizeneho slovniku')],
        body: Annotated[
            DescriptorBaseType,
            Body(title='Data deskriptoru')] = None,
        api_key: str = Depends(header_scheme)
) -> Union[DescriptorType, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    LOGGER.info(f'PUT /descriptor')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    LOGGER.debug(f'PUT /descriptor/{dictionary}')
    if key in [None, '']:
        raise ApiError(code=400, message='Missing key')
    LOGGER.debug(f'PUT /descriptor/{dictionary}/{key}')
    if body is None:
        raise ApiError(code=400, message='Missing data')
    LOGGER.debug(f'PUT /descriptor/{dictionary}/{key} - BODY: {type(body)} ')
    if body.key in [None, '']:
        body.key = key
    if body.key != key:
        raise ApiError(code=400, message=f"Illegal key: {key} != {body.key}")
    vl = []
    for v in body.values:
        LOGGER.debug(f'PUT /descriptor/{dictionary}/{key} - VALUES: {type(v)} ')
        if isinstance(v, dict):
            dv = DescriptorValueType(**v)
            vl.append(dv)
    if vl:
        body.values = vl
    reply = await DbDescriptor.by_key(dictionary=dictionary, key=key)
    if not reply:
        LOGGER.info(f"PUT /descriptor/{dictionary}/{key} NOT FOUND")
        raise ApiError(code=404, message=f"DescriptorType {dictionary}/{key} not found")
    LOGGER.info(f"PUT /descriptor/{dictionary}/{key} FOUND")
    LOGGER.debug(f'PUT /descriptor/{dictionary}/{key} - REPLY: {type(reply)} ')
    b = reply.model_dump()
    body_old = DescriptorBaseType(**b)
    dict_old = body_old.model_dump()
    dict_new = body.model_dump()
    update_changed_values(reply, dict_old, dict_new)
    vl2 = []
    for v2 in reply.values:
        LOGGER.debug(f'PUT /descriptor/{dictionary}/{key} - VALUES2: {type(v2)} ')
        if isinstance(v2, dict):
            dv2 = DescriptorValueType(**v2)
            vl2.append(dv2)
    if vl2:
        reply.values = vl2
    reply1 = await reply.replace()
    if reply1 is None:
        raise ApiError(code=500, message=f"DescriptorType '{dictionary}/{key}' cannot be updated")
    LOGGER.info(f"PUT /descriptor/{dictionary}/{key}: {type(reply1)} ")
    out = reply1.document
    LOGGER.info(f"PUT /descriptor/{dictionary}/{key} DONE: {type(out)} ")
    return out


@router.get(
    path='/export',
    response_model=List[DescriptorBaseType],
    responses={'default': {'model': ErrorModel}},
    summary='Exportuje vsechny data jako JSON',
)
async def export_all(api_key: str = Depends(header_scheme)) -> Union[List[DescriptorBaseType], ErrorModel]:
    LOGGER.info(f'GET /export')
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    try:
        out = await DbDescriptor.export_all()
    except Exception as e:
        LOGGER.error(f'GET /export FAILED: {str(e)}')
        raise ApiError(code=500, message=str(e))
    if not out:
        raise ApiError(code=404, message='Nothing found')
    LOGGER.info(f'GET /export done: {len(out)}')
    return out


@router.get(
    path='/export/{dictionary}',
    response_model=List[DescriptorBaseType],
    responses={'default': {'model': ErrorModel}},
    summary='Exportuje jeden slovnik jako JSON',
)
async def export_dictionary(
        dictionary: Annotated[
            str,
            Path(title='Kod slovniku', description='Kod rizeneho slovniku')],
        api_key: str = Depends(header_scheme)
) -> Union[List[DescriptorBaseType], ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    LOGGER.info(f'GET /export/{dictionary}')
    if dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    try:
        out = await DbDescriptor.export_dictionary(dictionary=dictionary)
    except Exception as e:
        LOGGER.error(f'GET /export/{dictionary} FAILED: {str(e)}')
        raise ApiError(code=500, message=str(e))
    if not out:
        raise ApiError(code=404, message='Nothing found')
    LOGGER.info(f'GET /export/{dictionary} done: {len(out)}')
    return out


@router.post(
    path='/import/domino',
    response_model=ReplyImported,
    responses={'default': {'model': ErrorModel}},
    summary='Importuje deskriptory do ruznych slovniku',
)
async def import_domino(
        replace: Annotated[Union[bool, None], Query(title='Nahradit puvodni hodnoty')] = None,
        body: Annotated[DominoImport, Body(title='Cistelnik z Domina')] = None,
        api_key: str = Depends(header_scheme)
) -> Union[ReplyImported, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    if replace is None:
        replace = False
    if body is None:
        raise ApiError(code=400, message='Missing body')
    if body.dictionary in [None, '']:
        raise ApiError(code=400, message='Missing dictionary')
    if body.value_key_text in [None, '']:
        raise ApiError(code=400, message='Missing data values')
    txt_list = body.value_key_text.split('\n')
    dictionary = body.dictionary
    data = []
    for item in txt_list:
        key = item.split('|')[-1]
        value = item.split('|')[0]
        d = DescriptorBaseType(
            dictionary=dictionary, key=key, key_alt='', active=True,
            values=[DescriptorValueType(lang='cs', value=value, value_alt='')],
        )
        data.append(d)
    if not data:
        raise ApiError(code=400, message='data contains nothing')
    out = await import_data(data=data, replace=replace)
    return out



@router.post(
    path='/import/legacy/file',
    response_model=ReplyImported,
    responses={'default': {'model': ErrorModel}},
    summary='Importuje deskriptory ze souboru descriptor-service v1',
    description=(
        'Nahraje soubor descriptor-service_1.json (NDJSON format -- kazdy radek je JSON objekt). '
        'Pole _id a identifier jsou ignorovany, nova UUID jsou generovana automaticky. '
        'BOM znaky a whitespace jsou sanitizovany. '
        'Parametr replace=true povoli prepis existujicich deskriptoru.'
    ),
)
async def import_legacy_file(
        replace: Annotated[Union[bool, None], Query(title='Nahradit puvodni hodnoty')] = None,
        file: UploadFile = File(..., description='Soubor descriptor-service_1.json'),
        api_key: str = Depends(header_scheme)
) -> Union[ReplyImported, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    if replace is None:
        replace = False
    import json
    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode('utf-8-sig')  # utf-8-sig odstrани BOM na zacatku souboru
    except UnicodeDecodeError as e:
        raise ApiError(code=400, message=f'Chyba dekodovani souboru: {str(e)}')
    legacy_items = []
    for lineno, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            legacy_items.append(LegacyDescriptorImport(**raw))
        except Exception as e:
            raise ApiError(code=400, message=f'Radek {lineno}: chybny format ({str(e)})')
    if not legacy_items:
        raise ApiError(code=400, message='Soubor neobsahuje zadna data')
    LOGGER.info(f'POST /import/legacy/file: {len(legacy_items)} items, replace={replace}')
    data = [item.to_descriptor_base() for item in legacy_items]
    out = await import_data(data=data, replace=replace)
    LOGGER.info(
        f'POST /import/legacy/file done: added={out.count_added}, '
        f'replaced={out.count_replaced}, rejected={out.count_rejected}, error={out.count_error}'
    )
    return out

@router.post(
    path='/import/legacy',
    response_model=ReplyImported,
    responses={'default': {'model': ErrorModel}},
    summary='Importuje deskriptory ze stareho formatu (descriptor-service v1)',
    description=(
        'Prijme seznam deskriptoru exportovanych ze starsi verze sluzby. '
        'Stary format pouziva flat pole value / value_en misto struktury values. '
        'Endpoint provede transformaci a preda data standardni importni logice. '
        'BOM znaky a okolni whitespace jsou automaticky sanitizovany. '
        'Parametr replace=true povoli prepis existujicich deskriptoru.'
    ),
)
async def import_legacy(
        replace: Annotated[Union[bool, None], Query(title='Nahradit puvodni hodnoty')] = None,
        body: Annotated[
            List[LegacyDescriptorImport],
            Body(title='Deskriptory ve starem formatu'),
        ] = None,
        api_key: str = Depends(header_scheme)
) -> Union[ReplyImported, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    if replace is None:
        replace = False
    if body is None:
        raise ApiError(code=400, message='Missing body')
    if not body:
        raise ApiError(code=400, message='Data is empty')
    LOGGER.info(f'POST /import/legacy: {len(body)} items, replace={replace}')
    data = [item.to_descriptor_base() for item in body]
    out = await import_data(data=data, replace=replace)
    LOGGER.info(
        f'POST /import/legacy done: added={out.count_added}, '
        f'replaced={out.count_replaced}, rejected={out.count_rejected}, error={out.count_error}'
    )
    return out


@router.post(
    path='/import',
    response_model=ReplyImported,
    responses={'default': {'model': ErrorModel}},
    summary='Importuje deskriptory do ruznych slovniku',
)
async def import_descriptors(
        replace: Annotated[Union[bool, None], Query(title='Nahradit puvodni hodnoty')] = None,
        body: Annotated[List[DescriptorBaseType], Body(title='Seznam deskriptoru')] = None,
        api_key: str = Depends(header_scheme)
) -> Union[ReplyImported, ErrorModel]:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')
    if replace is None:
        replace = False
    if body is None:
        raise ApiError(code=400, message='Missing body')
    if not body:
        raise ApiError(code=400, message='Data is empty')
    out = await import_data(data=body, replace=replace)
    return out
