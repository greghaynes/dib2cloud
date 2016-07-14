# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
test_dib2cloud
----------------------------------

Tests for `dib2cloud` module.
"""

import os
import tempfile

import fixtures

from dib2cloud import config
from dib2cloud.tests import base


class ConfigFragmentFixture(fixtures.Fixture):
    @classmethod
    def get(cls, name):
        return cls._configs[name]

    def __init__(self, fixture_name):
        self.fixture_name = fixture_name


class ProviderConfigFixture(ConfigFragmentFixture):
    _configs = {
        'simple': config.Provider(name='test_provider',
                                  cloud='dib2cloud_test')
    }


class DiskimageConfigFixture(ConfigFragmentFixture):
    _configs = {
        'simple': config.Diskimage(name='test_diskimage',
                                   elements=['element1', 'element2'],
                                   release='releaseno',
                                   env_vars={'var1': 'val1',
                                             'var2': 'val2'})
    }


class ConfigFixture(ConfigFragmentFixture):
    _configs = {
        'simple': config.Config(
                    diskimages=[DiskimageConfigFixture.get('simple')],
                    providers=[ProviderConfigFixture.get('simple')])
    }

    def _setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(delete=False)
        self.path = self.tempfile.name
        self.addCleanup(self._remove_tempfile)
        self.config = self.get(self.fixture_name)
        self.config.to_yaml_file(self.path)

    def _remove_tempfile(self):
        os.unlink(self.path)


class TestConfig(base.TestCase):
    def test_simple_config_inflation(self):
        config_fxtr = self.useFixture(ConfigFixture('simple'))
        loaded_config = config.Config.from_yaml_file(config_fxtr.path)
        self.assertEqual(config_fxtr.config, loaded_config)


class TestDib2cloud(base.TestCase):
    def test_something(self):
        pass
