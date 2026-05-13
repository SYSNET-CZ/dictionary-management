"""
api/routers/monitor.py

Monitoring router — statistiky, stav databáze a přehled slovníků.

Přístup:
    Každý endpoint vyžaduje platný X-API-KEY (stejný mechanismus jako admins router).

Endpointy:
    GET  /monitor/stats              — agregované statistiky kolekce deskriptorů
    GET  /monitor/health             — stav MongoDB a detaily kolekce
    GET  /monitor/dict/{dictionary}  — detailní statistiky jednoho slovníku

Architektura:
    - Statistiky jsou počítány přes MongoDB aggregation pipeline (jeden round-trip na skupinu).
    - Pro /stats jsou z jedné pipeline odvozeny jak per-slovník tak celkové součty.
    - Agregace běží přes Beanie find().aggregate() — konzistentní s odm.py.
    - /health čte document count přes Beanie a indexy přes get_motor_collection().index_information().
    - Chyby databáze jsou vraceny jako 503.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sysnet_pyutils.models.general import ApiError, ErrorModel

from api.dependencies import header_scheme, is_api_authorized
from api.model.admin import (
    AdminHealthOut,
    AdminStatsOut,
    DictionaryBreakdown,
    DictionaryDetailOut,
    IndexInfo,
)
from api.model.odm import DbDescriptor
from init import CONFIG, VERSION

LOGGER = logging.getLogger('monitor')

router = APIRouter(prefix='/monitor', tags=['monitor'])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_auth(api_key: str) -> None:
    if not is_api_authorized(key=api_key):
        raise ApiError(code=403, message='Forbidden')


def _check_mongo() -> None:
    """503 pokud MongoDB není dostupná (dle stavu lifespan hooku)."""
    if CONFIG.get('mongo', {}).get('status') != 'GREEN':
        raise HTTPException(status_code=503, detail='MongoDB not available')


async def _aggregate(pipeline: list) -> list:
    """
    Spustí surový aggregation pipeline přes Beanie.

    Beanie find({}).aggregate() připojí prázdný $match: {} před pipeline —
    to je no-op (nefiltruje nic), ale zajistí kompatibilitu s Beanie interními
    hooky (timezones, ODM lifecycle).
    """
    try:
        return await DbDescriptor.find({}).aggregate(pipeline).to_list()
    except Exception as exc:
        LOGGER.error('MongoDB aggregation failed: %s', exc)
        raise HTTPException(status_code=503, detail=f'Aggregation failed: {exc}') from exc


# ---------------------------------------------------------------------------
# GET /monitor/stats
# ---------------------------------------------------------------------------

@router.get(
    '/stats',
    response_model=AdminStatsOut,
    responses={
        '403': {'model': ErrorModel},
        '503': {'model': ErrorModel},
    },
    summary='Agregované statistiky kolekce deskriptorů',
    description=(
        'Vrátí celkové počty, aktivní/neaktivní rozdělení a přehled per slovník. '
        'Parametr hours určuje okno pro výpočet "nedávno přidaných" a '
        '"nedávno upravených" záznamů (výchozí 24 h, max 720 = 30 dní). '
        'Nově přidané = version=1 v daném okně; upravené = version>1.'
    ),
)
async def get_stats(
        hours: Annotated[
            int,
            Query(title='Okno (hodiny)', description='Délka okna pro nedávné záznamy (1–720)', ge=1, le=720),
        ] = 24,
        api_key: str = Depends(header_scheme),
) -> Union[AdminStatsOut, ErrorModel]:
    _check_auth(api_key)
    _check_mongo()

    now = datetime.now(tz=timezone.utc)
    from_ts = now - timedelta(hours=hours)

    # --- per-slovník: count, active, inactive, last_modified ---
    dict_pipeline = [
        {
            '$group': {
                '_id': '$dictionary',
                'count': {'$sum': 1},
                'active': {'$sum': {'$cond': [{'$eq': ['$active', True]}, 1, 0]}},
                'inactive': {'$sum': {'$cond': [{'$eq': ['$active', True]}, 0, 1]}},
                'last_modified': {'$max': '$timestamp'},
            }
        },
        {'$sort': {'_id': 1}},
    ]

    # --- nedávno přidané: version == 1, timestamp >= from_ts ---
    added_pipeline = [
        {'$match': {'timestamp': {'$gte': from_ts}, 'version': 1}},
        {'$count': 'n'},
    ]

    # --- nedávno upravené: version > 1, timestamp >= from_ts ---
    updated_pipeline = [
        {'$match': {'timestamp': {'$gte': from_ts}, 'version': {'$gt': 1}}},
        {'$count': 'n'},
    ]

    dict_results = await _aggregate(dict_pipeline)
    added_results = await _aggregate(added_pipeline)
    updated_results = await _aggregate(updated_pipeline)

    breakdown = [
        DictionaryBreakdown(
            dictionary=row['_id'],
            count=row['count'],
            active=row['active'],
            inactive=row['inactive'],
            last_modified=row.get('last_modified'),
        )
        for row in dict_results
        if row.get('_id')  # skip null _id (dokumenty bez dictionary pole)
    ]

    return AdminStatsOut(
        generated_at=now,
        period_hours=hours,
        total_descriptors=sum(b.count for b in breakdown),
        total_dictionaries=len(breakdown),
        active_descriptors=sum(b.active for b in breakdown),
        inactive_descriptors=sum(b.inactive for b in breakdown),
        recently_added=added_results[0]['n'] if added_results else 0,
        recently_modified=updated_results[0]['n'] if updated_results else 0,
        by_dictionary=breakdown,
    )


# ---------------------------------------------------------------------------
# GET /monitor/health
# ---------------------------------------------------------------------------

@router.get(
    '/health',
    response_model=AdminHealthOut,
    responses={
        '403': {'model': ErrorModel},
        '503': {'model': ErrorModel},
    },
    summary='Stav MongoDB a detaily kolekce',
    description=(
        'Vrátí aktuální stav MongoDB připojení, počet dokumentů v kolekci '
        'a seznam indexů s jejich klíči. Nevyžaduje dostupnou MongoDB — '
        'pokud je stav RED, vrátí informace bez DB dotazu.'
    ),
)
async def get_health(
        api_key: str = Depends(header_scheme),
) -> Union[AdminHealthOut, ErrorModel]:
    _check_auth(api_key)

    mongo_status = CONFIG.get('mongo', {}).get('status', 'RED')
    collection_name = DbDescriptor.Settings.name

    if mongo_status != 'GREEN':
        return AdminHealthOut(
            status='RED',
            mongo_status=mongo_status,
            collection_name=collection_name,
            document_count=0,
            index_count=0,
            indexes=[],
            version=VERSION,
        )

    try:
        doc_count = await DbDescriptor.find().count()
        coll = DbDescriptor.get_pymongo_collection()
        raw_indexes = await coll.index_information()
    except Exception as exc:
        LOGGER.error('monitor/health DB query failed: %s', exc)
        raise HTTPException(status_code=503, detail=f'DB query failed: {exc}') from exc

    indexes = [
        IndexInfo(
            name=name,
            keys=dict(info.get('key', {})),
        )
        for name, info in sorted(raw_indexes.items())
    ]

    return AdminHealthOut(
        status='GREEN',
        mongo_status=mongo_status,
        collection_name=collection_name,
        document_count=doc_count,
        index_count=len(indexes),
        indexes=indexes,
        version=VERSION,
    )


# ---------------------------------------------------------------------------
# GET /monitor/dict/{dictionary}
# ---------------------------------------------------------------------------

@router.get(
    '/dict/{dictionary}',
    response_model=DictionaryDetailOut,
    responses={
        '403': {'model': ErrorModel},
        '404': {'model': ErrorModel},
        '503': {'model': ErrorModel},
    },
    summary='Detailní statistiky jednoho slovníku',
    description=(
        'Vrátí počty aktivních/neaktivních deskriptorů a ukázku '
        'posledních 10 upravených klíčů pro zadaný slovník.'
    ),
)
async def get_dictionary_detail(
        dictionary: Annotated[
            str,
            Path(title='Kód slovníku', description='Kód řízeného slovníku'),
        ],
        api_key: str = Depends(header_scheme),
) -> Union[DictionaryDetailOut, ErrorModel]:
    _check_auth(api_key)
    _check_mongo()

    stats_pipeline = [
        {'$match': {'dictionary': dictionary}},
        {
            '$group': {
                '_id': None,
                'count': {'$sum': 1},
                'active': {'$sum': {'$cond': [{'$eq': ['$active', True]}, 1, 0]}},
                'inactive': {'$sum': {'$cond': [{'$eq': ['$active', True]}, 0, 1]}},
                'last_modified': {'$max': '$timestamp'},
            }
        },
    ]

    sample_pipeline = [
        {'$match': {'dictionary': dictionary}},
        {'$sort': {'timestamp': -1}},
        {'$limit': 10},
        {'$project': {'_id': 0, 'key': 1}},
    ]

    agg = await _aggregate(stats_pipeline)
    sample = await _aggregate(sample_pipeline)

    if not agg or agg[0].get('count', 0) == 0:
        raise ApiError(code=404, message=f"Dictionary '{dictionary}' not found")

    row = agg[0]
    return DictionaryDetailOut(
        dictionary=dictionary,
        count=row['count'],
        active=row['active'],
        inactive=row['inactive'],
        last_modified=row.get('last_modified'),
        sample_keys=[doc.get('key', '') for doc in sample],
    )
