# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.descriptor_value import DescriptorValue  # noqa: F401,E501
from swagger_server import util


class Descriptor(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, key: str=None, key_alt: str=None, dictionary: str=None, active: bool=None, values: List[DescriptorValue]=None):  # noqa: E501
        """Descriptor - a model defined in Swagger

        :param key: The key of this Descriptor.  # noqa: E501
        :type key: str
        :param key_alt: The key_alt of this Descriptor.  # noqa: E501
        :type key_alt: str
        :param dictionary: The dictionary of this Descriptor.  # noqa: E501
        :type dictionary: str
        :param active: The active of this Descriptor.  # noqa: E501
        :type active: bool
        :param values: The values of this Descriptor.  # noqa: E501
        :type values: List[DescriptorValue]
        """
        self.swagger_types = {
            'key': str,
            'key_alt': str,
            'dictionary': str,
            'active': bool,
            'values': List[DescriptorValue]
        }

        self.attribute_map = {
            'key': 'key',
            'key_alt': 'key_alt',
            'dictionary': 'dictionary',
            'active': 'active',
            'values': 'values'
        }
        self._key = key
        self._key_alt = key_alt
        self._dictionary = dictionary
        self._active = active
        self._values = values

    @classmethod
    def from_dict(cls, dikt) -> 'Descriptor':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Descriptor of this Descriptor.  # noqa: E501
        :rtype: Descriptor
        """
        return util.deserialize_model(dikt, cls)

    @property
    def key(self) -> str:
        """Gets the key of this Descriptor.

        Hlavní klíč deskriptoru  # noqa: E501

        :return: The key of this Descriptor.
        :rtype: str
        """
        return self._key

    @key.setter
    def key(self, key: str):
        """Sets the key of this Descriptor.

        Hlavní klíč deskriptoru  # noqa: E501

        :param key: The key of this Descriptor.
        :type key: str
        """
        if key is None:
            raise ValueError("Invalid value for `key`, must not be `None`")  # noqa: E501

        self._key = key

    @property
    def key_alt(self) -> str:
        """Gets the key_alt of this Descriptor.

        Alternativní klíč deskriptoru  # noqa: E501

        :return: The key_alt of this Descriptor.
        :rtype: str
        """
        return self._key_alt

    @key_alt.setter
    def key_alt(self, key_alt: str):
        """Sets the key_alt of this Descriptor.

        Alternativní klíč deskriptoru  # noqa: E501

        :param key_alt: The key_alt of this Descriptor.
        :type key_alt: str
        """

        self._key_alt = key_alt

    @property
    def dictionary(self) -> str:
        """Gets the dictionary of this Descriptor.

        Kód řízeného slovníku  # noqa: E501

        :return: The dictionary of this Descriptor.
        :rtype: str
        """
        return self._dictionary

    @dictionary.setter
    def dictionary(self, dictionary: str):
        """Sets the dictionary of this Descriptor.

        Kód řízeného slovníku  # noqa: E501

        :param dictionary: The dictionary of this Descriptor.
        :type dictionary: str
        """
        if dictionary is None:
            raise ValueError("Invalid value for `dictionary`, must not be `None`")  # noqa: E501

        self._dictionary = dictionary

    @property
    def active(self) -> bool:
        """Gets the active of this Descriptor.

        Descriptor is active  # noqa: E501

        :return: The active of this Descriptor.
        :rtype: bool
        """
        return self._active

    @active.setter
    def active(self, active: bool):
        """Sets the active of this Descriptor.

        Descriptor is active  # noqa: E501

        :param active: The active of this Descriptor.
        :type active: bool
        """

        self._active = active

    @property
    def values(self) -> List[DescriptorValue]:
        """Gets the values of this Descriptor.


        :return: The values of this Descriptor.
        :rtype: List[DescriptorValue]
        """
        return self._values

    @values.setter
    def values(self, values: List[DescriptorValue]):
        """Sets the values of this Descriptor.


        :param values: The values of this Descriptor.
        :type values: List[DescriptorValue]
        """
        if values is None:
            raise ValueError("Invalid value for `values`, must not be `None`")  # noqa: E501

        self._values = values
