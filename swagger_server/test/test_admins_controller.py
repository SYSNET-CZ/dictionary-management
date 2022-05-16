# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.descriptor import Descriptor  # noqa: E501
from swagger_server.models.reply_imported import ReplyImported  # noqa: E501
from swagger_server.test import BaseTestCase


class TestAdminsController(BaseTestCase):
    """AdminsController integration test stubs"""

    def test_activate_descriptor(self):
        """Test case for activate_descriptor

        activates/deactivates the descriptor by key
        """
        query_string = [('active', true)]
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/{key}/activate'.format(dictionary='dictionary_example', key='key_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_add_descriptor(self):
        """Test case for add_descriptor

        adds an descriptor
        """
        body = Descriptor()
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}'.format(dictionary='dictionary_example'),
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_descriptor(self):
        """Test case for delete_descriptor

        removes a descriptor
        """
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/{key}'.format(dictionary='dictionary_example', key='key_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_export_all(self):
        """Test case for export_all

        exports all descriptors from the system
        """
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/export',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_export_dictionary(self):
        """Test case for export_dictionary

        exports all descriptors from specifies dictionary
        """
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/export'.format(dictionary='dictionary_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_import_descriptors(self):
        """Test case for import_descriptors

        imports descriptors of several directories
        """
        body = [Descriptor()]
        query_string = [('replace', true)]
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/import',
            method='POST',
            data=json.dumps(body),
            content_type='application/json',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_import_dictionary(self):
        """Test case for import_dictionary

        imports a dictionary
        """
        body = [Descriptor()]
        query_string = [('replace', true)]
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/import'.format(dictionary='dictionary_example'),
            method='POST',
            data=json.dumps(body),
            content_type='application/json',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_put_descriptor(self):
        """Test case for put_descriptor

        replaces a descriptor
        """
        body = Descriptor()
        response = self.client.open(
            '/SYSNET/dictionary/1.0.0/{dictionary}/{key}'.format(dictionary='dictionary_example', key='key_example'),
            method='PUT',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
