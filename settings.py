import logging
import os
import secrets
import sys
import yaml

VERSION = os.getenv('MANDIR_VERSION', '1.0.0')
DEBUG = os.getenv("DEBUG", 'True').lower() in ('true', '1', 't')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(levelname)s in %(module)s: %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%d.%m.%Y %H:%M:%S')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
LOG_DIR = os.getenv('LOG_DIR', os.path.join(ROOT_DIR, 'logs'))
BACKUP_DIR = os.getenv('BACKUP_DIR', os.path.join(ROOT_DIR, 'backup'))
CONFIG_DIR = os.getenv('CONFIG_DIRECTORY', os.path.join(ROOT_DIR, 'conf'))
CONFIG_FILE_NAME = os.getenv('CONFIG_FILE_NAME', 'dict.yml')
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

MONGO_CLIENT_ALIAS = 'mandir-alias'
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'dictionaries')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'descriptor')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_USERNAME = os.getenv('MONGO_USERNAME', 'root')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'Egalite1651.')
MONGO_COLLATION_CS = {"locale": "cs@collation=search"}


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Log(object, metaclass=Singleton):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        if DEBUG:
            self.logger.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
            handler.setLevel(logging.INFO)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.propagate = False
        self.logger.info('LOG created')


def init_config():
    if os.path.isfile(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as yamlfile:
            out = yaml.load(yamlfile, Loader=yaml.FullLoader)
            LOG.logger.info('Configuration loaded')
        return out
    out = create_config()
    with open(CONFIG_FILE_PATH, 'w') as yamlfile:
        yaml.dump(out, yamlfile)
        LOG.logger.info('Configuration stored')
    return out


def create_config():
    out = {
        'api_keys': init_api_keys('dictionaries')
    }
    return out


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


LOG = Log()
CONFIG = init_config()
