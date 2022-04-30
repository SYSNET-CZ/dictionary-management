from mongoengine import Document, StringField, connect, OperationError, ValidationError, disconnect, DoesNotExist, \
    NotUniqueError
from pymongo.errors import OperationFailure, PyMongoError

from settings import MONGO_CLIENT_ALIAS, MONGO_DATABASE, MONGO_HOST, MONGO_PORT, MONGO_USERNAME, \
    MONGO_PASSWORD, MONGO_COLLATION_CS, LOG


class Descriptor(Document):
    meta = {
        'db_alias': MONGO_CLIENT_ALIAS,
        'collection': 'descriptor',
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


class DictionaryFactory:
    def __init__(
            self, database=MONGO_DATABASE, host=MONGO_HOST, port=MONGO_PORT,
            username=MONGO_USERNAME, password=MONGO_PASSWORD):
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
        try:
            self.connection = connect(
                db=self.database,
                alias='mandir-alias',
                host=self.host, port=self.port, username=self.username, password=self.password,
                authentication_source='admin')
            LOG.logger.info('DictionaryFactory created')
        except PyMongoError as e:
            LOG.logger.error(e)
            self.connection = None

    def __del__(self):
        if self.connection is not None:
            self.connection.close()
            disconnect()
            LOG.logger.info('DictionaryFactory deleted')

    def create_descriptor(self, dictionary=None, key=None, json_data=None, **kwargs):
        self.current_descriptor = Descriptor()
        try:
            if json_data is not None:
                self.current_descriptor = Descriptor.from_json(json_data=json_data)
            elif dictionary is not None and key is not None:
                self.current_descriptor.identifier = '{}*{}'.format(dictionary.lower(), key.lower())
                self.current_descriptor.dictionary = dictionary
                self.current_descriptor.key = key
                for key, value in kwargs.items():
                    if key == 'key_alt':
                        self.current_descriptor.key_alt = value
                    elif key == 'value':
                        self.current_descriptor.value = value
                    elif key == 'value_en':
                        self.current_descriptor.value_en = value
            LOG.logger.info('Descriptor created: {}'.format(self.current_descriptor.identifier))
        except OperationError as e:
            LOG.logger.error(e)
            self.current_descriptor = None
        return self.current_descriptor

    def save_descriptor(self):
        out = None
        try:
            if self.current_descriptor is not None:
                out = self.current_descriptor.save()
                LOG.logger.info('Descriptor saved: {}'.format(self.current_descriptor.identifier))
        except [OperationError, ValidationError, NotUniqueError] as e:
            LOG.logger.error(e)
            out = None
        return out

    def remove_descriptor(self):
        try:
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
        if dictionary is None:
            return False
        self.qs = Descriptor.objects(dictionary=dictionary)
        if self.qs.count() < 1:
            return False
        self.qs.delete()
        return True

    def remove_all(self):
        self.qs = Descriptor.objects()
        if self.qs.count() < 1:
            return False
        self.qs.delete()
        return True

    def get_descriptor(self, dictionary=None, key=None, key_alt=None):
        self.current_descriptor = None
        try:
            if (dictionary is not None) and (key is not None):
                identifier = '{}*{}'.format(dictionary.lower(), key.lower())
                d = Descriptor.objects.get(identifier=identifier)
                self.current_descriptor = d
                LOG.logger.info('Descriptor loaded by key: {}'.format(d.identifier))
            elif (dictionary is not None) and (key_alt is not None):
                d = Descriptor.objects.get(dictionary=dictionary, key_alt__iexact=key_alt)
                self.current_descriptor = d
                LOG.logger.info('Descriptor loaded by key_alt: {}'.format(d.identifier))
        except DoesNotExist as e:
            LOG.logger.error(e)
            self.current_descriptor = None
        return self.current_descriptor

    def autocomplete_cs(self, dictionary=None, query=None):
        self.search_result = []
        if (dictionary is None) or (query is None):
            return self.search_result
        qs = Descriptor.objects(dictionary=dictionary, value__icontains=query)
        if qs.count() < 1:
            return self.search_result
        qs1 = qs.collation(MONGO_COLLATION_CS)
        for item in qs1.values_list():
            self.search_result.append(item)
        return self.search_result

    def autocomplete_en(self, dictionary=None, query=None):
        self.search_result = []
        if (dictionary is None) or (query is None):
            return self.search_result
        qs = Descriptor.objects(dictionary=dictionary, value_en__icontains=query)
        if qs.count() < 1:
            return self.search_result
        self.search_result = qs.values_list()
        for item in qs.values_list():
            self.search_result.append(item)
        return self.search_result

    def get_descriptor_list(self, dictionary=None):
        self.search_result = []
        if dictionary is None:
            qs = Descriptor.objects()
        else:
            qs = Descriptor.objects(dictionary=dictionary)
        if qs.count() < 1:
            return self.search_result
        for item in qs.values_list():
            self.search_result.append(item)
        return self.search_result

    def get_dictionaries(self):
        self.dictionaries = {}
        qs = Descriptor.objects.only('dictionary')
        if qs.count() < 1:
            return self.dictionaries
        for item in qs:
            d = item.dictionary
            if d in self.dictionaries:
                self.dictionaries[d] += 1
            else:
                self.dictionaries[d] = 1
        return self.dictionaries

    def get_info(self):
        self.get_dictionaries()
        self.info = {
            'count': {'dictionaries': len(self.dictionaries), 'descriptors': sum(self.dictionaries.values())},
            'dictionaries': self.dictionaries
        }
        return self.info


def create_mongo_client(
        database=MONGO_DATABASE,
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD):
    try:
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
    if (dictionary is not None) and (key is not None):
        identifier = '{}*{}'.format(dictionary.lower(), key.lower())
        qs = Descriptor.objects(identifier=identifier)
        if qs.count() > 0:
            out = qs.first()
    elif (dictionary is not None) and (key_alt is not None):
        qs = Descriptor.objects(dictionary=dictionary, key_alt=key_alt)
        if qs.count() > 0:
            out = qs.first()
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
    out = Descriptor()
    try:
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
