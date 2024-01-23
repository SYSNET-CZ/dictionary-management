from management.data import DescriptorItem, DICTIONARY_FACTORY, DictionaryError
from swagger_server.models import Descriptor, DescriptorValue, ReplyImported, ImportedItem

COUNTER = {
    'info_api': 0,
    'activate_descriptor': 0,
    'add_descriptor': 0,
    'delete_descriptor': 0,
    'export_all': 0,
    'export_dictionary': 0,
    'import_descriptors': 0,
    'import_dictionary': 0,
    'put_descriptor': 0,
    'get_descriptor': 0,
    'search_dictionary': 0,
}


def implementation_activate_descriptor(dictionary, key, active):
    d = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key=key)
    if d is None:
        raise DictionaryError(status=404, message='Descriptor not found')
    if active:
        DICTIONARY_FACTORY.activate_descriptor()
    else:
        DICTIONARY_FACTORY.deactivate_descriptor()
    out = DICTIONARY_FACTORY.save_descriptor()
    if out is None:
        return False
    return True


def implementation_add_descriptor(dictionary: str, descriptor: Descriptor):
    if descriptor.dictionary != dictionary:
        raise DictionaryError(status=400, message='Dictionary does not match')
    d = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key=descriptor.key)
    if d is not None:
        raise DictionaryError(status=409, message='Descriptor already exists')
    d = DICTIONARY_FACTORY.create_descriptor(dictionary=dictionary, key=descriptor.key)
    d.key_alt = descriptor.key_alt
    for v in descriptor.values:
        if v.lang.lower() == 'cs':
            d.value = v.value
        elif v.lang.lower() == 'en':
            d.value_en = v.value
    if not descriptor.active:
        d.active = False
    out = DICTIONARY_FACTORY.save_descriptor(d)
    if out is None:
        raise DictionaryError(status=500, message='Cannot save descriptor')
    return True


def implementation_delete_descriptor(dictionary, key):
    d = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key=key)
    if d is None:
        d = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key_alt=key)
    if d is None:
        raise DictionaryError(status=404, message='Descriptor not found')

    out = DICTIONARY_FACTORY.remove_descriptor(descriptor=d)
    return out


def implementation_export_all():
    descriptor_list = DICTIONARY_FACTORY.get_all()
    out = _descriptor_list_to_swagger(descriptor_list=descriptor_list)
    return out


def implementation_export_dictionary(dictionary):
    descriptor_list = DICTIONARY_FACTORY.get_dictionary(dictionary=dictionary)
    out = _descriptor_list_to_swagger(descriptor_list=descriptor_list)
    return out


def implementation_import_descriptors(descriptors, replace):
    out = ReplyImported(count_added=0, count_rejected=0, count_replaced=0, added=[], rejected=[], replaced=[])
    for d in descriptors:
        d1 = _swagger_to_descriptor(d)
        _fill_reply_imported(reply_imported=out, descriptor=d1, replace=replace)
    return out


def _fill_reply_imported(reply_imported, descriptor, replace):
    o = DICTIONARY_FACTORY.add_descriptor(descriptor=descriptor, replace=replace)
    ii = ImportedItem().from_dict(o)
    if ii.status == 'added':
        reply_imported.count_added += 1
        reply_imported.added.append(ii)
    elif ii.status == 'rejected':
        reply_imported.count_rejected += 1
        reply_imported.rejected.append(ii)
    elif ii.status == 'replaced':
        reply_imported.count_replaced += 1
        reply_imported.replaced.append(ii)
    pass


def implementation_import_dictionary(dictionary, descriptors, replace):
    out = ReplyImported(count_added=0, count_rejected=0, count_replaced=0, added=[], rejected=[], replaced=[])
    for d in descriptors:
        d1 = _swagger_to_descriptor(d)
        if d1.dictionary == dictionary:
            _fill_reply_imported(reply_imported=out, descriptor=d1, replace=replace)
        else:
            ii = ImportedItem(dictionary=d1.dictionary, key=d1.key, status='rejected')
            out.count_rejected += 1
            out.rejected.append(ii)
    return out


def implementation_put_descriptor(dictionary, key, descriptor):
    d0 = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key=key)
    if d0 is not None:
        d1 = _swagger_to_descriptor(descriptor=descriptor)
        d = DICTIONARY_FACTORY.replace_descriptor(descriptor=d1)
        out = _descriptor_to_swagger(d)
    else:
        out = None
    return out


# public methods ---------------------------------------------------------------------------------
def implementation_get_descriptor(dictionary, key):
    out = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key=key)
    if out is None:
        out = DICTIONARY_FACTORY.get_descriptor(dictionary=dictionary, key_alt=key)
    if out is None:
        return None
    out = _descriptor_to_swagger(out)
    return out


def implementation_search_dictionary(dictionary, query=None, active=None, skip=None, limit=None):
    reply = DICTIONARY_FACTORY.autocomplete_cs(dictionary=dictionary, query=query)
    if not reply:
        reply = DICTIONARY_FACTORY.autocomplete_en(dictionary=dictionary, query=query)
    out = _descriptor_list_to_swagger(reply, active=active, skip=skip, limit=limit)
    return out


def _descriptor_to_swagger(descriptor: DescriptorItem):
    out = Descriptor()
    out.key = descriptor.key
    out.key_alt = descriptor.key_alt
    out.dictionary = descriptor.dictionary
    out.active = descriptor.active
    out.values = [DescriptorValue(lang='cs', value=descriptor.value)]
    if descriptor.value_en is not None:
        if (len(descriptor.value_en) > 0) and not descriptor.value_en.isspace():
            out.values.append(DescriptorValue(lang='en', value=descriptor.value_en))
    return out


def _swagger_to_descriptor(descriptor: Descriptor):
    out = DescriptorItem()
    out.key = descriptor.key
    out.key_alt = descriptor.key_alt
    out.dictionary = descriptor.dictionary
    out.active = descriptor.active
    out.value = ''
    out.value_en = ''
    out.identifier = '{}*{}'.format(out.dictionary.lower(), out.key.lower())
    if hasattr(descriptor, 'values'):
        for dv in descriptor.values:
            if dv.lang == 'cs':
                out.value = dv.value
            elif dv.lang == 'en':
                out.value_en = dv.value
    return out


def _descriptor_list_to_swagger(descriptor_list, active=None, skip=None, limit=None):
    out = []
    i = 0
    j = 0
    if skip is None:
        skip = 0
    if limit is None:
        limit = 0
    for item in descriptor_list:
        if active is not None:
            if item.active != active:
                continue
        i += 1
        if skip < i:
            j += 1
            if (limit == 0) or (limit >= j):
                out.append(_descriptor_to_swagger(item))
    return out
