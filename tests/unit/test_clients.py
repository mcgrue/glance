# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import os
import stubout
import StringIO
import unittest

import webob

from glance import client
from glance.registry import client as rclient
from glance.common import flags
from glance.common import exception
from tests import stubs

FLAGS = flags.FLAGS


class TestBadClients(unittest.TestCase):

    """Test exceptions raised for bad clients"""

    def test_bad_address(self):
        """Test ClientConnectionError raised"""
        c = client.Client("127.999.1.1")
        self.assertRaises(client.ClientConnectionError,
                          c.get_image,
                          1)


class TestRegistryClient(unittest.TestCase):

    """
    Test proper actions made for both valid and invalid requests
    against a Registry service
    """

    def setUp(self):
        """Establish a clean test environment"""
        self.stubs = stubout.StubOutForTesting()
        stubs.stub_out_registry_db_image_api(self.stubs)
        stubs.stub_out_registry_and_store_server(self.stubs)
        self.client = rclient.RegistryClient("0.0.0.0")

    def tearDown(self):
        """Clear the test environment"""
        self.stubs.UnsetAll()

    def test_get_image_index(self):
        """Test correct set of public image returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2'}
        images = self.client.get_images()
        self.assertEquals(len(images), 1)

        for k, v in fixture.iteritems():
            self.assertEquals(v, images[0][k])

    def test_get_image_details(self):
        """Tests that the detailed info about public images returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        expected = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        images = self.client.get_images_detailed()
        self.assertEquals(len(images), 1)

        for k, v in expected.iteritems():
            self.assertEquals(v, images[0][k])

    def test_get_image(self):
        """Tests that the detailed info about an image returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        expected = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        data = self.client.get_image(2)

        for k, v in expected.iteritems():
            self.assertEquals(v, data[k])

    def test_get_image_non_existing(self):
        """Tests that NotFound is raised when getting a non-existing image"""

        self.assertRaises(exception.NotFound,
                          self.client.get_image,
                          42)

    def test_add_image_basic(self):
        """Tests that we can add image metadata and returns the new id"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/acct/3.gz.0",
                  }

        new_image = self.client.add_image(fixture)

        # Test ID auto-assigned properly
        self.assertEquals(3, new_image['id'])

        # Test all other attributes set
        data = self.client.get_image(3)

        for k, v in fixture.iteritems():
            self.assertEquals(v, data[k])

        # Test status was updated properly
        self.assertTrue('status' in data.keys())
        self.assertEquals('available', data['status'])

    def test_add_image_with_properties(self):
        """Tests that we can add image metadata with properties"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }
        expected = {'name': 'fake public image',
                    'is_public': True,
                    'type': 'kernel',
                    'size': 19,
                    'location': "file:///tmp/glance-tests/2",
                    'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }

        new_image = self.client.add_image(fixture)

        # Test ID auto-assigned properly
        self.assertEquals(3, new_image['id'])

        for k, v in expected.iteritems():
            self.assertEquals(v, new_image[k])

        # Test status was updated properly
        self.assertTrue('status' in new_image.keys())
        self.assertEquals('available', new_image['status'])

    def test_add_image_already_exists(self):
        """Tests proper exception is raised if image with ID already exists"""
        fixture = {'id': 2,
                   'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                  }

        self.assertRaises(exception.Duplicate,
                          self.client.add_image,
                          fixture)

    def test_add_image_with_bad_status(self):
        """Tests proper exception is raised if a bad status is set"""
        fixture = {'id': 3,
                   'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                  }

        self.assertRaises(exception.BadInputError,
                          self.client.add_image,
                          fixture)

    def test_update_image(self):
        """Tests that the /images PUT registry API updates the image"""
        fixture = {'name': 'fake public image #2',
                   'type': 'ramdisk'
                  }

        self.assertTrue(self.client.update_image(2, fixture))

        # Test all other attributes set
        data = self.client.get_image(2)

        for k, v in fixture.iteritems():
            self.assertEquals(v, data[k])

    def test_update_image_not_existing(self):
        """Tests non existing image update doesn't work"""
        fixture = {'id': 3,
                   'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status'
                  }

        self.assertRaises(exception.NotFound,
                          self.client.update_image,
                          3,
                          fixture)

    def test_delete_image(self):
        """Tests that image metadata is deleted properly"""

        # Grab the original number of images
        orig_num_images = len(self.client.get_images())

        # Delete image #2
        self.assertTrue(self.client.delete_image(2))

        # Verify one less image
        new_num_images = len(self.client.get_images())

        self.assertEquals(new_num_images, orig_num_images - 1)

    def test_delete_image_not_existing(self):
        """Tests cannot delete non-existing image"""

        self.assertRaises(exception.NotFound,
                          self.client.delete_image,
                          3)


class TestClient(unittest.TestCase):

    """
    Test proper actions made for both valid and invalid requests
    against a Glance service
    """

    def setUp(self):
        """Establish a clean test environment"""
        self.stubs = stubout.StubOutForTesting()
        stubs.stub_out_registry_db_image_api(self.stubs)
        stubs.stub_out_registry_and_store_server(self.stubs)
        stubs.stub_out_filesystem_backend()
        self.orig_filesystem_store_datadir = FLAGS.filesystem_store_datadir
        FLAGS.filesystem_store_datadir = stubs.FAKE_FILESYSTEM_ROOTDIR
        self.client = client.Client("0.0.0.0")

    def tearDown(self):
        """Clear the test environment"""
        FLAGS.filesystem_store_datadir = self.orig_filesystem_store_datadir
        stubs.clean_out_fake_filesystem_backend()
        self.stubs.UnsetAll()

    def test_get_image(self):
        """Test a simple file backend retrieval works as expected"""
        expected_image = 'chunk00000remainder'
        expected_meta = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}
        meta, image_chunks = self.client.get_image(2)

        image_data = ""
        for image_chunk in image_chunks:
            image_data += image_chunk

        self.assertEquals(expected_image, image_data)
        for k, v in expected_meta.iteritems():
            self.assertEquals(v, meta[k])

    def test_get_image_not_existing(self):
        """Test retrieval of a non-existing image returns a 404"""

        self.assertRaises(exception.NotFound,
                          self.client.get_image,
                          3)

    def test_get_image_index(self):
        """Test correct set of public image returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2'}
        images = self.client.get_images()
        self.assertEquals(len(images), 1)

        for k, v in fixture.iteritems():
            self.assertEquals(v, images[0][k])

    def test_get_image_details(self):
        """Tests that the detailed info about public images returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        expected = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        images = self.client.get_images_detailed()
        self.assertEquals(len(images), 1)

        for k, v in expected.iteritems():
            self.assertEquals(v, images[0][k])

    def test_get_image_meta(self):
        """Tests that the detailed info about an image returned"""
        fixture = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        expected = {'id': 2,
                   'name': 'fake image #2',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'available',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {}}

        data = self.client.get_image_meta(2)

        for k, v in expected.iteritems():
            self.assertEquals(v, data[k])

    def test_get_image_non_existing(self):
        """Tests that NotFound is raised when getting a non-existing image"""

        self.assertRaises(exception.NotFound,
                          self.client.get_image,
                          42)

    def test_add_image_without_location_or_raw_data(self):
        """Tests client throws Invalid if missing both location and raw data"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel'
                  }

        self.assertRaises(exception.Invalid,
                          self.client.add_image,
                          fixture)

    def test_add_image_basic(self):
        """Tests that we can add image metadata and returns the new id"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                  }

        new_id = self.client.add_image(fixture)

        # Test ID auto-assigned properly
        self.assertEquals(3, new_id)

        # Test all other attributes set
        data = self.client.get_image_meta(3)

        for k, v in fixture.iteritems():
            self.assertEquals(v, data[k])

        # Test status was updated properly
        self.assertTrue('status' in data.keys())
        self.assertEquals('available', data['status'])

    def test_add_image_with_properties(self):
        """Tests that we can add image metadata with properties"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                   'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }
        expected = {'name': 'fake public image',
                    'is_public': True,
                    'type': 'kernel',
                    'size': 19,
                    'location': "file:///tmp/glance-tests/2",
                    'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }

        new_id = self.client.add_image(fixture)

        # Test ID auto-assigned properly
        self.assertEquals(3, new_id)

        # Test all other attributes set
        data = self.client.get_image_meta(3)

        for k, v in expected.iteritems():
            self.assertEquals(v, data[k])

        # Test status was updated properly
        self.assertTrue('status' in data.keys())
        self.assertEquals('available', data['status'])

    def test_add_image_already_exists(self):
        """Tests proper exception is raised if image with ID already exists"""
        fixture = {'id': 2,
                   'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                  }

        self.assertRaises(exception.Duplicate,
                          self.client.add_image,
                          fixture)

    def test_add_image_with_bad_status(self):
        """Tests a bad status is set to a proper one by server"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status',
                   'size': 19,
                   'location': "file:///tmp/glance-tests/2",
                  }

        new_id = self.client.add_image(fixture)

        data = self.client.get_image_meta(new_id)

        self.assertEquals(data['status'], 'available')

    def test_add_image_with_image_data_as_string(self):
        """Tests can add image by passing image data as string"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }

        image_data_fixture = r"chunk0000remainder"

        new_id = self.client.add_image(fixture, image_data_fixture)

        self.assertEquals(3, new_id)

        new_meta, new_image_chunks = self.client.get_image(3)

        new_image_data = ""
        for image_chunk in new_image_chunks:
            new_image_data += image_chunk

        self.assertEquals(image_data_fixture, new_image_data)
        for k, v in fixture.iteritems():
            self.assertEquals(v, new_meta[k])

    def test_add_image_with_image_data_as_file(self):
        """Tests can add image by passing image data as file"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }

        image_data_fixture = r"chunk0000remainder"

        tmp_image_filepath = '/tmp/rubbish-image'

        if os.path.exists(tmp_image_filepath):
            os.unlink(tmp_image_filepath)

        tmp_file = open(tmp_image_filepath, 'wb')
        tmp_file.write(image_data_fixture)
        tmp_file.close()

        new_id = self.client.add_image(fixture, open(tmp_image_filepath))

        self.assertEquals(3, new_id)

        if os.path.exists(tmp_image_filepath):
            os.unlink(tmp_image_filepath)

        new_meta, new_image_chunks = self.client.get_image(3)

        new_image_data = ""
        for image_chunk in new_image_chunks:
            new_image_data += image_chunk

        self.assertEquals(image_data_fixture, new_image_data)
        for k, v in fixture.iteritems():
            self.assertEquals(v, new_meta[k])

    def test_add_image_with_bad_store(self):
        """Tests BadRequest raised when supplying bad store name in meta"""
        fixture = {'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'size': 19,
                   'store': 'bad',
                   'properties': {'distro': 'Ubuntu 10.04 LTS'}
                  }

        image_data_fixture = r"chunk0000remainder"

        self.assertRaises(exception.BadInputError,
                          self.client.add_image,
                          fixture,
                          image_data_fixture)

    def test_update_image(self):
        """Tests that the /images PUT registry API updates the image"""
        fixture = {'name': 'fake public image #2',
                   'type': 'ramdisk'
                  }

        self.assertTrue(self.client.update_image(2, fixture))

        # Test all other attributes set
        data = self.client.get_image_meta(2)

        for k, v in fixture.iteritems():
            self.assertEquals(v, data[k])

    def test_update_image_not_existing(self):
        """Tests non existing image update doesn't work"""
        fixture = {'id': 3,
                   'name': 'fake public image',
                   'is_public': True,
                   'type': 'kernel',
                   'status': 'bad status'
                  }

        self.assertRaises(exception.NotFound,
                          self.client.update_image,
                          3,
                          fixture)

    def test_delete_image(self):
        """Tests that image metadata is deleted properly"""

        # Grab the original number of images
        orig_num_images = len(self.client.get_images())

        # Delete image #2
        self.assertTrue(self.client.delete_image(2))

        # Verify one less image
        new_num_images = len(self.client.get_images())

        self.assertEquals(new_num_images, orig_num_images - 1)

    def test_delete_image_not_existing(self):
        """Tests cannot delete non-existing image"""

        self.assertRaises(exception.NotFound,
                          self.client.delete_image,
                          3)