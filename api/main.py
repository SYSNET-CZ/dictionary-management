from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Union

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from sysnet_pyutils.models.general import ErrorModel, ApiError

from api.model.dictionary import DictionaryType
from api.model.odm import DbDescriptor
from api.routers import public, admins
from init import APP_NAME, VERSION, CONFIG, DEFAULT_AGENDA, MONGO_CONNECTION_STRING, CC, API_ROOT_PATH, LOG

logging.basicConfig(
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)

# LOGGER = logging.getLogger(__name__)
LOGGER = LOG.logger


@asynccontextmanager
async def lifespan(api: FastAPI):
    # Startup
    db_name = CONFIG[DEFAULT_AGENDA]['database']
    api.mongodb_client = AsyncMongoClient(MONGO_CONNECTION_STRING)
    api.database = api.mongodb_client.get_database(db_name)
    ping_response = await api.database.command("ping")
    if int(ping_response["ok"]) != 1:
        CC.config['mongo']['status'] = 'RED'
        CC.store()
        LOGGER.error("Problem connecting to database cluster.")
        raise Exception("Problem connecting to database cluster.")
    else:
        await init_beanie(
            database=api.mongodb_client[db_name],
            document_models=[DbDescriptor])
        # info ("Connected to database cluster.")
        LOGGER.info(f"Connected to database cluster.")
        CC.config['mongo']['status'] = 'GREEN'
        CC.store()
    yield
    # Shutdown
    CC.config['mongo']['status'] = 'RED'
    CC.store()
    await api.mongodb_client.close()


app = FastAPI(
    lifespan=lifespan,
    title=f"{APP_NAME} verze: {VERSION}",
    summary="Správa řízených slovníků",
    description='REST API of the SYSNET managed dictionaries (code lists) system. \nPrimarily designed for the CITES Registry.\n',
    contact={
        'name': 'SYSNET s.r.o.',
        'url': 'https://sysnet.cz',
        'email': 'info@sysnet.cz',
    },
    license={
        'name': 'GNU Affero General Public License v3.0',
        'url': 'https://www.gnu.org/licenses/agpl-3.0.html',
    },
    version='2.0.0',
    openapi_tags=[
        {"name": "info", "description": "Informace o službě"},
        {"name": "admins", "description": "Operace pro správce"},
        {"name": "public", "description": "Operace pro veřejné uživatele"},
    ],
    root_path=f"/{API_ROOT_PATH}",
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"])]

)

LOGGER.info(f"{__name__} - API is starting up")


@app.exception_handler(ApiError)
async def uvicorn_exception_handler(request: Request, exc: ApiError):
    msg = f"{request.client.host}: {exc.message}"
    LOGGER.error(f"{__name__} - {exc.code}: {msg}")
    return JSONResponse(
        status_code=exc.code,
        content={"message": msg},
    )

"""
@app.middleware("http")
async def log_requests(request: Request, call_next):
    LOGGER.info(f"{__name__}.http - Request: {request.method} {request.url}")

    # Protokolování těla požadavku (pokud chcete)
    body = await request.body()
    LOGGER.debug(f"{__name__}.http - Request body: {body}")
    response = await call_next(request)

    # Protokolování odpovědi
    LOGGER.info(f"{__name__}.http - Response status: {response.status_code}")
    return response
"""

@app.get(
    path="/",
    summary='Informace o aplikaci',
    response_model=dict,
    tags=["info"])
async def get_root() -> JSONResponse:
    out = {'name': APP_NAME, 'version': VERSION, }
    return JSONResponse(status_code=200, content=out)


@app.head(
    path="/",
    summary='Dostupnost služby',
    response_model=None,
    tags=["info"])
async def head_root() -> None:
    return None

@app.head(
    path='/info',
    response_model=None,
    responses={'default': {'model': ErrorModel}},
    summary='Vrací informaci o dostupnosti služby',
    tags=['info'],)
async def head_info() -> Union[None, ErrorModel]:
    """
    Vrací informaci o dostupnosti služby
    """
    return None


@app.get(
    path='/info',
    response_model=dict,
    summary='Vrací servisní informace',
    responses={'404': {'model': ErrorModel}, 'default': {'model': ErrorModel}},
    tags=['info'],)
async def get_info() -> Union[JSONResponse, ErrorModel]:
    """
    Vrací servisní informace
    """
    out = {
        'status': 'RED',
        'mongo': {'status': CONFIG['mongo']['status']},
        'dictionaries': [],
    }
    green = 0
    yellow = 0
    red = 0
    for k, v in out.items():
        if isinstance(v, dict):
            if 'status' in v:
                if v['status'] == 'GREEN':
                    green += 1
                elif v['status'] == 'YELLOW':
                    yellow += 1
                else:
                    red += 1
    if green == 1:
        out['status'] = 'GREEN'
        dl = await DbDescriptor.dictionary_list()
        if dl is not None and bool(dl):
            for item in dl:
                out['dictionaries'].append(DictionaryType.model_dump(item))
    elif red == 0:
        out['status'] = 'YELLOW'
    return JSONResponse(status_code=200, content=out)

app.include_router(public.router)

app.include_router(admins.router)
