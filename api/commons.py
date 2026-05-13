from beanie import SortDirection
from init import paging_to_mongo


def create_query(
        dictionary=None, key=None, lang=None, active=None, search=None,
        start=None, pagesize=None, page=None,
        skip=None, limit=None):
    paging = paging_to_mongo(start=start, page_size=pagesize, page=page, skip=skip, limit=limit)
    query_dictionary = {}
    query_key = {}
    query_lang = {}
    query_active = {}
    query_search = {}
    sort = 'key'
    sort_direction = SortDirection.ASCENDING
    if dictionary not in [None, '']:
        query_dictionary = {'dictionary': {"$regex": dictionary, "$options": "i"}}
    if key not in [None, '']:
        query_list_key = [
            {'key': {"$regex": key, "$options": "i"}},
            {'key_alt': {"$regex": key, "$options": "i"}},
            {'values.value': {"$regex": key, "$options": "i"}}]
        query_key = {'$or': query_list_key}
    if lang not in [None, '']:
        query_lang = {'values.lang': {"$regex": lang, "$options": "i"}}
    if active is not None:
        query_active = {'active': active}
    if search not in [None, '']:
        query_search = {"$text": {"$search": search}}
    query = {}
    query_list_1 = [query_dictionary, query_key, query_lang, query_active, query_search]
    query_list_2 = []
    for q in query_list_1:
        if bool(q):
            query_list_2.append(q)
    if bool(query_list_2):
        if len(query_list_2) == 1:
            query = query_list_2[0]
        else:
            query = {"$and": query_list_2}
    sort = (sort, sort_direction)
    return query, paging, sort


def update_changed_values(out_object=None, dict_old=None, dict_new=None):
    if (out_object is None) or (dict_new is None) or (dict_old is None):
        return False
    for key, value in dict_old.items():
        if isinstance(value, dict):
            if (key in dict_new) and dict_new[key] is not None:
                update_changed_values(getattr(out_object, key), value, dict_new[key])
        else:
            if key in dict_new:
                if value != dict_new[key]:
                    setattr(out_object, key, dict_new[key])
    return True
