# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.descriptor import Descriptor  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPublicController(BaseTestCase):
    """PublicController integration test stubs"""

    def test_get_descriptor(self):
        """Test case for get_descriptor

        gets a descriptor by key
        """
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/{key}'.format(dictionary='dictionary_example', key='key_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_search_dictionary(self):
        """Test case for search_dictionary

        searches dictionary (autocomplete)
        """
        query_string = [('query', 'query_example'),
                        ('active', true),
                        ('skip', 1),
                        ('limit', 50)]
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}'.format(dictionary='dictionary_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
