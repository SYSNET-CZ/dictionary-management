from typing import List

import connexion

from settings import LOG, check_api_key, CONTEXT

"""
controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""


def check_apiKey(api_key, required_scopes):
    __name__ = check_apiKey.__name__
    if api_key is None:
        LOG.logger.error('{0}: missing api key'.format(__name__))
        raise connexion.exceptions.Unauthorized('missing api key')
    check_api_key(api_key)
    if not CONTEXT.authenticated:
        LOG.logger.error('{0}: invalid api key'.format(__name__))
        raise connexion.exceptions.Unauthorized('invalid api key')
    if required_scopes:
        LOG.logger.debug('required_scopes: {}'.format(str(required_scopes)))
    out = {'x-api-key': api_key, 'description': CONTEXT.user_name, 'agenda': CONTEXT.agenda}
    LOG.logger.info('{}: x-api-key={}, agenda={}'.format(__name__, CONTEXT.user_name, CONTEXT.agenda))
    return out
