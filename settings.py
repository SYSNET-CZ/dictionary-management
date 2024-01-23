import os
import secrets

import sysnet_pyutils.utils as pu

VERSION = os.getenv('DICT_VERSION', '1.0.0.003')
APP_NAME = os.getenv('DICT_NAME', 'SYSNET Managed Dictionaries API')

DEBUG = os.getenv("DEBUG", 'True').lower() in ('true', '1', 't')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(levelname)s in %(module)s: %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%d.%m.%Y %H:%M:%S')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
LOG_DIR = os.getenv('LOG_DIR', os.path.join(ROOT_DIR, 'logs'))
LOG_FILE_NAME = os.getenv('LOG_FILE_NAME', 'dict.log')
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)
ERROR_FILE_PATH = os.path.join(LOG_DIR, 'error.log')
DEBUG_FILE_PATH = os.path.join(LOG_DIR, 'debug.log')
BACKUP_DIR = os.getenv('BACKUP_DIR', os.path.join(ROOT_DIR, 'backup'))
CONFIG_DIR = os.getenv('CONFIG_DIRECTORY', os.path.join(ROOT_DIR, 'conf'))
CONFIG_FILE_NAME = os.getenv('CONFIG_FILE_NAME', 'dict.yml')
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)
UPLOAD_DIR = os.getenv('UPLOAD_DIRECTORY', os.path.join(ROOT_DIR, 'upload'))

MONGO_CLIENT_ALIAS = 'mandir-alias'
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'dictionaries')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'descriptor')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_USERNAME = os.getenv('MONGO_USERNAME', 'root')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'Egalite1651.')
MONGO_COLLATION_CS = {"locale": "cs@collation=search"}
DEFAULT_AGENDA = os.getenv('DEFAULT_AGENDA', 'dict')

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


class Context(object, metaclass=pu.Singleton):
    def __init__(self, api_key=None, user_name=None, agenda=None):
        self.api_key = api_key
        self.user_name = user_name
        self.agenda = agenda
        self.authenticated = False
        LOG.logger.info('CONTEXT created')

    def clear(self):
        self.api_key = None
        self.user_name = None
        self.agenda = None
        self.authenticated = False
        LOG.logger.info('CONTEXT cleared')


CONFIG_INIT = {
    DEFAULT_AGENDA: {
        'api_keys': pu.api_keys_init(DEFAULT_AGENDA),
        'database': MONGO_DATABASE
    },
    'mongo': {
        'host': MONGO_HOST,
        'port': MONGO_PORT,
        'user': MONGO_USERNAME,
        'password': MONGO_PASSWORD,
        'locale': MONGO_COLLATION_CS['locale'],
        'collation': MONGO_COLLATION_CS
    },
}


def init_api_keys(agenda, amount=4):
    out = []
    for i in range(amount):
        out.append(next_api_key('{} {}'.format(agenda, i + 1)))
    return out


def next_api_key(name, length=16):
    out = {generate_api_key(length=length): name}
    return out


def generate_api_key(length: int):
    return secrets.token_urlsafe(length)


def check_api_key(api_key):
    CONTEXT.clear()
    for agenda in CONFIG.keys():
        if 'api_keys' not in CONFIG[agenda]:
            continue
        for ak in CONFIG[agenda]['api_keys']:
            if api_key in ak.keys():
                CONTEXT.api_key = api_key
                CONTEXT.agenda = agenda
                CONTEXT.user_name = ak[api_key]
                CONTEXT.authenticated = True
                break
    return CONTEXT


def set_ext_logger(ext_logger):
    if ext_logger is not None:
        LOG.logger = ext_logger


LOG = pu.Log()
CC = pu.Config(config_path=CONFIG_FILE_PATH, config_dict=CONFIG_INIT)
if CC.loaded:
    LOG.logger.info('{} version {}: CONFIG loaded'.format(APP_NAME, VERSION))
CONFIG = CC.config
CONTEXT = Context()
