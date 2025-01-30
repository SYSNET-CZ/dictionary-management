import os
import secrets

from pymongo.collation import Collation
from sysnet_pyutils.utils import LoggedObject, Singleton, api_keys_init, Log, Config

VERSION = os.getenv('DICT_VERSION', '2.0.0')
APP_NAME = os.getenv('DICT_NAME', 'SYSNET Managed Dictionaries API')
APP_CODE = 'dict'
DEBUG = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')
INSTANCE = os.getenv('INSTANCE', 'DEV')  # DEV, PROD, TEST
COLLATION = Collation(locale='cs@collation=search')

API_ROOT_PATH = os.getenv('API_ROOT_PATH', APP_CODE)

LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(levelname)s in %(module)s: %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%d.%m.%Y %H:%M:%S')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
LOG_DIR = os.getenv('LOG_DIR', os.path.join(ROOT_DIR, 'logs'))
LOG_FILE_NAME = os.getenv('LOG_FILE_NAME', f'{APP_CODE}.log')
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)
ERROR_FILE_PATH = os.path.join(LOG_DIR, f'{APP_CODE}-error.log')
DEBUG_FILE_PATH = os.path.join(LOG_DIR, f'{APP_CODE}-debug.log')
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
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'xxxxxxxxxxxxxxx')
MONGO_COLLATION_CS = {"locale": "cs@collation=search"}
PAGE_SIZE = 10

DEFAULT_AGENDA = os.getenv('DEFAULT_AGENDA', APP_CODE)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


class Context(LoggedObject, metaclass=Singleton):
    def __init__(self, object_name='CONTEXT', api_key=None, user_name=None, agenda=None, cert_file=None, cert_pass=None):
        super().__init__(object_name=object_name)
        self.api_key = api_key
        self.user_name = user_name
        self.agenda = agenda
        self.authenticated = False
        self.cert_file = cert_file
        self.cert_pass = cert_pass
        self.log.info(f"{self.name} Created")

    def clear(self):
        self.api_key = None
        self.user_name = None
        self.agenda = None
        self.authenticated = False
        self.cert_file = None
        self.cert_pass = None
        self.log.info(f"{self.name} Cleared")

    def check_api_key(self, api_key):
        self.clear()
        if api_key in [None, '']:
            return False
        for agenda in CONFIG.keys():
            if 'api_keys' not in CONFIG[agenda]:
                continue
            for ak in CONFIG[agenda]['api_keys']:
                if api_key in ak.keys():
                    self.api_key = api_key
                    self.agenda = agenda
                    self.user_name = ak[api_key]
                    self.authenticated = True
                    self.log.info(f"{self.name} - User '{self.user_name}' logged in")
                    break
            if self.authenticated:
                break
        return self.authenticated



CONFIG_INIT = {
    DEFAULT_AGENDA: {
        'api_keys': api_keys_init(DEFAULT_AGENDA),
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


def paging_to_mongo(start=0, page_size=PAGE_SIZE, page=0, skip=0, limit=999):
    if (skip is not None) and (limit is not None):
        page_size = PAGE_SIZE
        page = int(skip / PAGE_SIZE)
        start = skip % PAGE_SIZE
    else:
        if start is None:
            start = 0
        if page_size is None:
            page_size = PAGE_SIZE
        if page is None:
            page = 0
        page += start // page_size
        start = start % page_size
        # pokud pocatecni dokument nesouhlasí se začátkem stránky, zkrátí se stránka
        skip = start + page * page_size
        limit = page_size
        if start != 0:
            limit = page_size - start
    out = {
        'start': start,
        'page_size': page_size,
        'page': page,
        'skip': skip,
        'limit': limit
    }
    return out


def set_ext_logger(ext_logger):
    if ext_logger is not None:
        LOG.logger = ext_logger


LOG = Log()
CC = Config(config_path=CONFIG_FILE_PATH, config_dict=CONFIG_INIT)
if CC.loaded:
    LOG.logger.info('{} version {}: CONFIG loaded'.format(APP_NAME, VERSION))
CONFIG = CC.config
CONTEXT = Context()

MONGO_CONNECTION_STRING = f"mongodb://{CONFIG['mongo']['user']}:{CONFIG['mongo']['password']}@{CONFIG['mongo']['host']}:{CONFIG['mongo']['port']}"
