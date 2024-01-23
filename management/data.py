from mongoengine import Document, StringField, connect, OperationError, ValidationError, disconnect, DoesNotExist, \
    NotUniqueError, BooleanField
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError, ServerSelectionTimeoutError
from sysnet_pyutils.utils import Singleton

from settings import MONGO_CLIENT_ALIAS, LOG, MONGO_COLLECTION, CONFIG, DEFAULT_AGENDA


class DescriptorItem(Document):
    meta = {
        'db_alias': MONGO_CLIENT_ALIAS,
        'collection': MONGO_COLLECTION,
        'shard_key': ('dictionary', 'key'),
        'indexes': [
            'identifier',
            ('dictionary', 'key'),
            ('dictionary', 'key_alt'),
            '$value',
        ]
    }

    identifier = StringField(required=True, unique=True)  # id je třeba předem vytvořit jako dictionary*key
    dictionary = StringField(required=True)
    key = StringField(unique_with='dictionary', required=True)
    key_alt = StringField()
    value = StringField(required=True)
    value_en = StringField()
    active = BooleanField()


class DictionaryFactory(metaclass=Singleton):
    def __init__(
            self, database=CONFIG[DEFAULT_AGENDA]['database'],
            host=CONFIG['mongo']['host'], port=CONFIG['mongo']['port'],
            username=CONFIG['mongo']['user'], password=CONFIG['mongo']['password']):
        self.database = database
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.current_descriptor = None
        self.connection = None
        self.search_result = []
        self.dictionaries = {}
        self.info = {}
        self.qs = None
        self.db_initialized = False
        self.server_info = None
        try:
            self.init_database()
            if self.db_initialized:
                self.connect_server()
                LOG.logger.info('DictionaryFactory created')
            else:
                LOG.logger.error('DictionaryFactory creation failed')
                self.connection = None
        except (PyMongoError, ServerSelectionTimeoutError) as e:
            LOG.logger.error(e)
            self.connection = None

    def __del__(self):
        if self.connection is not None:
            self.connection.close()
            disconnect()
            LOG.logger.info('DictionaryFactory deleted')

    def connect_server(self):
        self.disconnect_server()
        self.connection = connect(
            db=self.database,
            alias=MONGO_CLIENT_ALIAS,
            host=self.host, port=self.port, username=self.username, password=self.password,
            authentication_source='admin')
        return self.connection

    def disconnect_server(self):
        if self.connection is not None:
            disconnect(alias=MONGO_CLIENT_ALIAS)

    def init_database(self):
        try:
            client = MongoClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                authSource='admin',
                serverSelectionTimeoutMS=1
            )
            si = client.server_info()
            self.server_info = {
                'server': 'mongo://{}:{}'.format(client.HOST, client.PORT),
                'version': si['version'],
                'platform': si['buildEnvironment']['target_os'],
                'architecture': si['buildEnvironment']['target_arch']
            }
            dbnames = client.list_database_names()
            if self.database in dbnames:
                LOG.logger.info('Dictionary database ready to use')
                client.close()
                del client
                self.db_initialized = True
                return False
            db = client[self.database]
            col = db[MONGO_COLLECTION]
            init_desc = {
                'identifier': 'init*0',
                'dictionary': 'init',
                'key': '0',
                'key_alt': '00000',
                'value': 'Databáze slovníků inicializována',
                'value_en': 'Dictionary database initialized',
                'active': False
            }
            desc = col.insert_one(init_desc)
            LOG.logger.info('Dictionary database initiated {}'.format(str(desc.inserted_id)))
            client.close()
            del client
            self.db_initialized = True
            return True
        except ServerSelectionTimeoutError as e:
            LOG.logger.error(e)
            self.db_initialized = False
            self.server_info = {
                'error': str(e)
            }
            return False

    def create_descriptor(self, dictionary=None, key=None, json_data=None, active=True, descriptor=None, **kwargs):
        self.current_descriptor = DescriptorItem()
        try:
            self.connect_server()
            if descriptor is not None:
                self.current_descriptor = descriptor
            elif json_data is not None:
                self.current_descriptor = DescriptorItem.from_json(json_data=json_data)
            elif dictionary is not None and key is not None:
                self.current_descriptor.identifier = '{}*{}'.format(dictionary.lower(), key.lower())
                self.current_descriptor.dictionary = dictionary
                self.current_descriptor.key = key
                self.current_descriptor.active = active
                for key, value in kwargs.items():
                    if key == 'key_alt':
                        self.current_descriptor.key_alt = value
                    elif key == 'value':
                        self.current_descriptor.value = value
                    elif key == 'value_en':
                        self.current_descriptor.value_en = value
            self.disconnect_server()
            LOG.logger.info('Descriptor created: {}'.format(self.current_descriptor.identifier))
        except OperationError as e:
            LOG.logger.error(e)
            self.current_descriptor = None
        return self.current_descriptor

    def save_descriptor(self, descriptor=None):
        out = None
        try:
            if descriptor is not None:
                self.current_descriptor = descriptor
            if self.current_descriptor is not None:
                out = self.current_descriptor.save()
                LOG.logger.info('Descriptor saved: {}'.format(self.current_descriptor.identifier))
        except [OperationError, ValidationError, NotUniqueError] as e:
            LOG.logger.error(e)
            out = None
        return out

    def activate_descriptor(self):
        if self.current_descriptor is not None:
            self.current_descriptor.active = True
            return True
        return False

    def deactivate_descriptor(self):
        if self.current_descriptor is not None:
            self.current_descriptor.active = False
            return True
        return False

    def replace_descriptor(self, descriptor=None):
        d = self.get_descriptor(dictionary=descriptor.dictionary, key=descriptor.key)
        if d is None:
            LOG.logger.error('{}: descriptor not found {}/{}'.format(__name__, descriptor.dictionary, descriptor.key))
            return None
        self.remove_descriptor(d)
        self.save_descriptor(descriptor=descriptor)
        return self.current_descriptor

    def add_descriptor(self, descriptor=None, replace=False):
        out = {'dictionary': descriptor.dictionary, 'key': descriptor.key, 'status': ''}
        d = self.get_descriptor(dictionary=descriptor.dictionary, key=descriptor.key)
        if d is None:
            self.save_descriptor(descriptor=descriptor)
            LOG.logger.info('{}: descriptor added {}/{}'.format(__name__, descriptor.dictionary, descriptor.key))
            out['status'] = 'added'
        else:
            if replace:
                self.remove_descriptor(d)
                self.save_descriptor(descriptor=descriptor)
                LOG.logger.info('{}: descriptor replaced {}/{}'.format(
                    __name__, descriptor.dictionary, descriptor.key))
                out['status'] = 'replaced'
            else:
                LOG.logger.info('{}: descriptor already exists {}/{}'.format(
                    __name__, descriptor.dictionary, descriptor.key))
                self.current_descriptor = None
                out['status'] = 'rejected'
        return out

    def remove_descriptor(self, descriptor=None):
        try:
            if descriptor is not None:
                self.current_descriptor = descriptor
            if self.current_descriptor is not None:
                ident = self.current_descriptor.identifier
                self.current_descriptor.delete()
                LOG.logger.info('Descriptor removed: {}'.format(ident))
                return True
        except OperationError as e:
            LOG.logger.error(e)
            return False

    def remove_dictionary(self, dictionary=None):
        self.qs = None
        self.connect_server()
        if dictionary is None:
            return False
        self.qs = DescriptorItem.objects(dictionary=dictionary)
        if self.qs.count() < 1:
            return False
        self.qs.delete()
        self.disconnect_server()
        return True

    def remove_all(self):
        self.connect_server()
        self.qs = DescriptorItem.objects()
        if self.qs.count() < 1:
            return False
        self.qs.delete()
        self.disconnect_server()
        return True

    def get_descriptor(self, dictionary=None, key=None, key_alt=None):
        self.current_descriptor = None
        try:
            self.connect_server()
            if (dictionary is not None) and (key is not None):
                identifier = '{}*{}'.format(dictionary.lower(), key.lower())
                d = DescriptorItem.objects.get(identifier=identifier)
                self.current_descriptor = d
                LOG.logger.info('Descriptor loaded by key: {}'.format(d.identifier))
            elif (dictionary is not None) and (key_alt is not None):
                d = DescriptorItem.objects.get(dictionary=dictionary, key_alt__iexact=key_alt)
                self.current_descriptor = d
                LOG.logger.info('Descriptor loaded by key_alt: {}'.format(d.identifier))
            self.disconnect_server()
        except DoesNotExist as e:
            LOG.logger.error(e)
            self.current_descriptor = None
        return self.current_descriptor

    def get_all(self):
        self.search_result = []
        self.connect_server()
        qs = DescriptorItem.objects()
        if qs.count() < 1:
            return self.search_result
        qs1 = qs.collation(CONFIG['mongo']['collation'])
        for item in qs1.values_list():
            self.search_result.append(item)
        self.disconnect_server()
        return self.search_result

    def get_dictionary(self, dictionary=None):
        self.search_result = []
        self.connect_server()
        qs = DescriptorItem.objects(dictionary=dictionary)
        if qs.count() < 1:
            return self.search_result
        qs1 = qs.collation(CONFIG['mongo']['collation'])
        for item in qs1.values_list():
            self.search_result.append(item)
        self.disconnect_server()
        return self.search_result

    def _get_descriptors(self, dictionary=None, query=None):
        self.search_result = []
        if (dictionary is None) or (query is None):
            return None
        self.connect_server()
        qs = DescriptorItem.objects(dictionary=dictionary, value__icontains=query)
        if qs.count() < 1:
            return None
        return qs

    def autocomplete_cs(self, dictionary=None, query=None):
        qs = self._get_descriptors(dictionary=dictionary, query=query)
        if qs is None:
            return self.search_result
        qs1 = qs.collation(CONFIG['mongo']['collation'])
        for item in qs1.values_list():
            self.search_result.append(item)
        self.disconnect_server()
        return self.search_result

    def autocomplete_en(self, dictionary=None, query=None):
        qs = self._get_descriptors(dictionary=dictionary, query=query)
        if qs is None:
            return self.search_result
        self.search_result = qs.values_list()
        for item in qs.values_list():
            self.search_result.append(item)
        self.disconnect_server()
        return self.search_result

    def get_descriptor_list(self, dictionary=None):
        self.search_result = []
        self.connect_server()
        if dictionary is None:
            qs = DescriptorItem.objects()
        else:
            qs = DescriptorItem.objects(dictionary=dictionary)
        if qs.count() < 1:
            return self.search_result
        for item in qs.values_list():
            self.search_result.append(item)
        self.disconnect_server()
        return self.search_result

    def get_dictionaries(self):
        self.dictionaries = {}
        self.connect_server()
        qs = DescriptorItem.objects.only('dictionary')
        if qs.count() < 1:
            return self.dictionaries
        for item in qs:
            d = item.dictionary
            if d in self.dictionaries:
                self.dictionaries[d] += 1
            else:
                self.dictionaries[d] = 1
        self.disconnect_server()
        return self.dictionaries

    def get_info(self):
        if self.db_initialized:
            self.get_dictionaries()
            self.info = {
                'count': {
                    'dictionaries': len(self.dictionaries),
                    'descriptors': sum(self.dictionaries.values())},
                'dictionaries': self.dictionaries
            }
        else:
            self.info = {'error': 'Database is not initialized'}
        return self.info


def get_info():
    out = DICTIONARY_FACTORY.get_info()
    return out


def create_mongo_client(
        database=CONFIG[DEFAULT_AGENDA]['database'],
        host=CONFIG['mongo']['host'],
        port=CONFIG['mongo']['port'],
        username=CONFIG['mongo']['user'],
        password=CONFIG['mongo']['password']):
    try:
        disconnect(alias=MONGO_CLIENT_ALIAS)
        out = connect(
            db=database,
            alias=MONGO_CLIENT_ALIAS,
            host=host, port=port, username=username, password=password,
            authentication_source='admin')
    except OperationFailure as e:
        print(str(e))
        out = None
    return out


def delete_mongo_client(client):
    if client is not None:
        client.close()
        disconnect(MONGO_CLIENT_ALIAS)
        return True
    return False


def get_descriptor(dictionary=None, key=None, key_alt=None):
    if dictionary is None:
        return None
    if key is None and key_alt is None:
        return None
    out = None
    DICTIONARY_FACTORY.connect_server()
    if (dictionary is not None) and (key is not None):
        identifier = '{}*{}'.format(dictionary.lower(), key.lower())
        qs = DescriptorItem.objects(identifier=identifier)
        if qs.count() > 0:
            out = qs.first()
    elif (dictionary is not None) and (key_alt is not None):
        qs = DescriptorItem.objects(dictionary=dictionary, key_alt=key_alt)
        if qs.count() > 0:
            out = qs.first()
    DICTIONARY_FACTORY.disconnect_server()
    return out


def delete_descriptor(descriptor):
    try:
        if descriptor is not None:
            descriptor.delete()
            return True
    except OperationError as e:
        print(str(e))
        return False


def create_descriptor(dictionary=None, key=None, json_data=None, **kwargs):
    out = DescriptorItem()
    try:
        DICTIONARY_FACTORY.connect_server()
        if dictionary is not None and key is not None:
            out.identifier = '{}*{}'.format(dictionary.lower(), key.lower())
            out.dictionary = dictionary
            out.key = key
            for key, value in kwargs.items():
                if key == 'key_alt':
                    out.key_alt = value
                elif key == 'value':
                    out.value = value
                elif key == 'value_en':
                    out.value_en = value
        if json_data is not None:
            out.from_json(json_data=json_data)
        DICTIONARY_FACTORY.disconnect_server()
    except OperationError as e:
        print(str(e))
        out = None
    return out


def save_descriptor(descriptor):
    out = None
    try:
        if descriptor is not None:
            out = descriptor.save()
    except [OperationError, ValidationError] as e:
        print(str(e))
        out = None
    return out


class DictionaryError(Exception):
    def __init__(self, status=500, message="Dictionary exception", module=None):
        self.status = status
        self.message = message
        self.module = module
        super().__init__(self.message)


DICTIONARY_FACTORY = DictionaryFactory()
