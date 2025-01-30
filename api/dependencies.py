import logging
from typing import List

from fastapi.security import APIKeyHeader

from api.models import ReplyImported, ImportedItem, DescriptorDb, DescriptorBase, StatusEnum
from init import CONTEXT

headers_no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}

header_scheme = APIKeyHeader(name="X-API-KEY")

LOGGER = logging.getLogger(__name__)


def is_api_authorized(key):
    return CONTEXT.check_api_key(api_key=key)


async def import_data(data: List[DescriptorBase], replace: bool):
    out = ReplyImported(count_added=0, count_rejected=0, count_replaced=0, count_error=0)
    out.added = []
    out.replaced = []
    out.rejected = []
    out.error = []
    i = 0
    for item in data:
        imp = ImportedItem(dictionary=item.dictionary, key=item.key, status=None)
        i += 1
        try:
            reply = await DescriptorDb.by_key(dictionary=imp.dictionary, key=item.key)
            if reply is None:
                b1 = DescriptorBase.model_dump(item)
                dbdoc = DescriptorDb(**b1)
                await DescriptorDb.insert_one(dbdoc)
                imp.status = StatusEnum.ADDED
                out.count_added += 1
                out.added.append(imp)
            else:
                if replace:
                    reply.key_alt = item.key_alt
                    reply.active = item.active
                    reply.values = item.values
                    await reply.replace(None)
                    imp.status = StatusEnum.REPLACED
                    out.count_replaced += 1
                    out.replaced.append(imp)
                else:
                    imp.status = StatusEnum.REJECTED
                    out.count_rejected += 1
                    out.rejected.append(imp)
        except Exception as e:
            imp.status = StatusEnum.ERROR
            out.count_error += 1
            out.error.append(imp)
            LOGGER.error(f'IMPORT item {i} FAILED: {str(e)}')
    return out
