from management.data import DictionaryError
from settings import LOG
from swagger_server.models.descriptor import Descriptor  # noqa: E501
from swagger_server.service.api import COUNTER, implementation_get_descriptor, implementation_search_dictionary
from swagger_server.util2 import who_am_i


def get_descriptor(dictionary, key):  # noqa: E501
    """gets a descriptor by key

    By passing the key or alternate key, you can get the descriptor  # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param key: Descriptor key or alternate key
    :type key: str

    :rtype: Descriptor
    """
    __name__ = who_am_i()
    COUNTER[__name__] += 1

    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary name'))
        return 'Missing dictionary name', 400
    if key is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing descriptor key'))
        return 'Missing descriptor key', 400
    try:
        out = implementation_get_descriptor(dictionary=dictionary, key=key)
        if out is not None:
            LOG.logger.info('{}: {}'.format(__name__, 'Result returned'))
            return out
        else:
            LOG.logger.error('{}: Descriptor  for key {} not found in the dictionary {}'.format(
                __name__, key, dictionary))
            return 'Descriptor  for key {} not found in the dictionary {}'.format(key, dictionary), 404
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def search_dictionary(dictionary, query=None, active=None, skip=None, limit=None):  # noqa: E501
    """searches dictionary (autocomplete)

    By passing in the appropriate options, you can search for available descriptors in the system.   # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param query: pass an optional search string for looking up dictionary
    :type query: str
    :param active: return active/inactive descriptors
    :type active: bool
    :param skip: number of records to skip for pagination
    :type skip: int
    :param limit: maximum number of records to return
    :type limit: int

    :rtype: List[Descriptor]
    """
    __name__ = who_am_i()
    COUNTER[__name__] += 1

    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary name'))
        return 'Missing dictionary name', 400
    try:
        out = implementation_search_dictionary(dictionary=dictionary, query=query, active=active, skip=skip, limit=limit)
        if (out is not None) or out:
            LOG.logger.info('{}: {}'.format(__name__, 'Result returned'))
            return out
        else:
            LOG.logger.error('{}: Nothing found for query {} in the dictionary {}'.format(
                __name__, query, dictionary))
            return 'Nothing found for query {} not found in the dictionary {}'.format(query, dictionary), 404
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status
