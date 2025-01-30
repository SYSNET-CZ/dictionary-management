from fastapi.security import APIKeyHeader

from init import CONTEXT

headers_no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}

header_scheme = APIKeyHeader(name="X-API-KEY")


def is_api_authorized(key):
    return CONTEXT.check_api_key(api_key=key)
