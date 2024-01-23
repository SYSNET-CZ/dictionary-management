import connexion

from management.data import DictionaryError
from settings import LOG
from swagger_server.models.descriptor import Descriptor  # noqa: E501
from swagger_server.service.api import COUNTER, implementation_activate_descriptor, implementation_add_descriptor, \
    implementation_delete_descriptor, implementation_export_all, implementation_export_dictionary, \
    implementation_import_descriptors, implementation_import_dictionary, implementation_put_descriptor
from swagger_server.util2 import who_am_i


def activate_descriptor(dictionary, key, active):  # noqa: E501
    """activates/deactivates the descriptor by key

    By passing the key or alternate key, you can get the descriptor  # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param key: Descriptor key or alternate key
    :type key: str
    :param active: activate/deactivate descriptor
    :type active: bool

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
    if active is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing activation value'))
        return 'Missing activation value', 400
    try:
        out = implementation_activate_descriptor(dictionary=dictionary, key=key, active=active)
        if out:
            if active:
                return 'Descriptor activated', 200
            else:
                return 'Descriptor deactivated', 200
        else:
            if active:
                return 'Error activating descriptor', 409
            else:
                return 'Error deactivating descriptor', 409
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def add_descriptor(dictionary, body=None):  # noqa: E501
    """adds a descriptor

    Adds a descriptor to the system # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param body: Descriptor to add
    :type body: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = Descriptor.from_dict(connexion.request.get_json())  # noqa: E501

    __name__ = who_am_i()
    COUNTER[__name__] += 1

    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary name'))
        return 'Missing dictionary name', 400
    if body is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing descriptor data'))
        return 'Missing descriptor data', 400
    try:
        out = implementation_add_descriptor(dictionary=dictionary, descriptor=body)
        if out:
            return 'Descriptor successfully created', 201
        return 'Error creating descriptor', 500
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def delete_descriptor(dictionary, key):  # noqa: E501
    """removes a descriptor

    By passing the key or alternate key, you can remove the descriptor  # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param key: Descriptor key or alternate key
    :type key: str

    :rtype: bool
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
        out = implementation_delete_descriptor(dictionary=dictionary, key=key)
        if out:
            return True, 200
        else:
            return 'Cannot delete descriptor', 500
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def export_all():  # noqa: E501
    """exports all descriptors from the system

    You can get all descriptors  # noqa: E501


    :rtype: List[Descriptor]
    """
    __name__ = who_am_i()
    COUNTER[__name__] += 1
    try:
        out = implementation_export_all()
        if out is not None and bool(out):
            return out, 200
        else:
            return 'Nothing to export', 204
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def export_dictionary(dictionary):  # noqa: E501
    """exports all descriptors from specifies dictionary

    By passing the dictionary name, you can get all descriptors of it  # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str

    :rtype: List[Descriptor]
    """
    __name__ = who_am_i()
    COUNTER[__name__] += 1
    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary name'))
        return 'Missing dictionary name', 400
    try:
        out = implementation_export_dictionary(dictionary=dictionary)
        if out is not None and bool(out):
            return out, 200
        else:
            return 'Nothing to export', 204
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def import_descriptors(body=None, replace=None):  # noqa: E501
    """imports descriptors of several directories

    Imports descriptors of several directories to the system  # noqa: E501

    :param body: Array of descriptors to import
    :type body: list | bytes
    :param replace: replaces whole database
    :type replace: bool

    :rtype: ReplyImported
    """
    if connexion.request.is_json:
        body = [Descriptor.from_dict(d) for d in connexion.request.get_json()]  # noqa: E501

    __name__ = who_am_i()
    COUNTER[__name__] += 1
    if body is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing data to import'))
        return 'Missing data to import', 400
    if replace is None:
        replace = False
    try:
        out = implementation_import_descriptors(descriptors=body, replace=replace)
        if out is not None and bool(out):
            return out, 200
        else:
            return 'Nothing imported', 204
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def import_dictionary(dictionary, body=None, replace=None):  # noqa: E501
    """imports a dictionary

    Imports whole dictionary to the system. Ignores data field &#x27;dictionary&#x27;   # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param body: Array of descriptors to import
    :type body: list | bytes
    :param replace: replaces existing dictionary
    :type replace: bool

    :rtype: ReplyImported
    """
    if connexion.request.is_json:
        body = [Descriptor.from_dict(d) for d in connexion.request.get_json()]  # noqa: E501
    __name__ = who_am_i()
    COUNTER[__name__] += 1
    if body is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing data to import'))
        return 'Missing data to import', 400
    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary code'))
        return 'Missing dictionary code', 400
    if replace is None:
        replace = False
    try:
        out = implementation_import_dictionary(dictionary=dictionary, descriptors=body, replace=replace)
        if out is not None and bool(out):
            return out, 200
        else:
            return 'Nothing imported', 204
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status


def put_descriptor(dictionary, key, body=None):  # noqa: E501
    """replaces a descriptor

    By passing the key or alternate key, you can replace the descriptor  # noqa: E501

    :param dictionary: Dictionary identifier
    :type dictionary: str
    :param key: Descriptor key or alternate key
    :type key: str
    :param body: Descriptor to replace
    :type body: dict | bytes

    :rtype: Descriptor
    """
    if connexion.request.is_json:
        body = Descriptor.from_dict(connexion.request.get_json())  # noqa: E501
    __name__ = who_am_i()
    COUNTER[__name__] += 1
    if body is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing data to import'))
        return 'Missing data to import', 400
    if dictionary is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing dictionary code'))
        return 'Missing dictionary code', 400
    if key is None:
        LOG.logger.error('{}: {}'.format(__name__, 'Missing descriptor key'))
        return 'Missing descriptor key', 400
    try:
        out = implementation_put_descriptor(dictionary=dictionary, key=key, descriptor=body)
        if out is not None and bool(out):
            return out, 200
        else:
            return 'No data updated, descriptor not found', 204
    except DictionaryError as e:
        LOG.logger.error('{}: {}'.format(__name__, e.message))
        return 'Dictionary error: {}'.format(e.message), e.status
