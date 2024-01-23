from management.data import get_info, DICTIONARY_FACTORY
from settings import VERSION, LOG, DEFAULT_AGENDA
from swagger_server.service.api import COUNTER
from swagger_server.util2 import who_am_i


def info_api():  # noqa: E501
    """gets service info

    Returns service info - status, technology versions, etc.  # noqa: E501


    :rtype: str
    """
    __name__ = who_am_i()
    COUNTER[__name__] += 1
    out = {
        'status': 'OK',
        'version': VERSION,
        'systems': [DEFAULT_AGENDA],
        'mongo': DICTIONARY_FACTORY.server_info,
        'data': get_info(),
    }
    out['mongo']['database'] = DICTIONARY_FACTORY.database
    LOG.logger.info('{}: {}'.format(__name__, 'Result returned'))
    return out
