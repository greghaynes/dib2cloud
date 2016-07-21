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

from io import BytesIO
import json
import multiprocessing
import os
import tempfile

import fixtures
import shutil

from dib2cloud import app
from dib2cloud import cmd
from dib2cloud import config
from dib2cloud import process
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
            providers=[ProviderConfigFixture.get('simple')],
        )
    }

    def _setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(delete=False)
        self.path = self.tempfile.name
        self.addCleanup(self._remove_tempfile)
        self.config = self.get(self.fixture_name)
        self.config['processfile_dir'] = tempfile.mkdtemp()
        self.addCleanup(self._cleanup_processfile_dir)
        self.config['buildlog_dir'] = tempfile.mkdtemp()
        self.addCleanup(self._cleanup_buildlog_dir)
        self.config['images_dir'] = tempfile.mkdtemp()
        self.addCleanup(self._cleanup_images_dir)
        self.config.to_yaml_file(self.path)

    def _remove_tempfile(self):
        os.unlink(self.path)

    def _cleanup_processfile_dir(self):
        shutil.rmtree(self.config['processfile_dir'])

    def _cleanup_buildlog_dir(self):
        shutil.rmtree(self.config['buildlog_dir'])

    def _cleanup_images_dir(self):
        shutil.rmtree(self.config['images_dir'])


class TestConfig(base.TestCase):
    def test_simple_config_inflation(self):
        config_fxtr = self.useFixture(ConfigFixture('simple'))
        loaded_config = config.Config.from_yaml_file(config_fxtr.path)
        self.assertEqual(config_fxtr.config, loaded_config)


class BaseFake(object):
    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs


class FakeBuild(BaseFake):
    name = 'fake_diskimage'
    uuid = 'fake-uuid'
    log_path = '/some/logfile'
    dest_paths = ['/some/dest']

    def succeeded(self):
        return (False, app.DibError.OutputMissing)

    def is_running(self):
        return False


class FakeApp(BaseFake):
    def build_image(self, name):
        return FakeBuild(name)

    def get_local_images(self):
        return [FakeBuild()]

    def delete_image(eslf, image_id):
        return FakeBuild()


class TestCmd(base.TestCase):
    def setUp(self):
        super(TestCmd, self).setUp()
        self.useFixture(fixtures.MonkeyPatch('dib2cloud.app.App', FakeApp))
        self.out = BytesIO()
        self.useFixture(fixtures.MonkeyPatch('dib2cloud.cmd.output',
                                             self.out.write))

    def test_build_image(self):
        cmd.main(['dib2cloud', '--config', 'some_config',
                  'build', 'test_diskimage'])
        out = json.loads(self.out.getvalue().decode('utf-8'))
        self.assertEqual({
            'destinations': ['/some/dest'],
            'id': 'fake-uuid',
            'log': '/some/logfile',
            'name': 'fake_diskimage',
            'pid': None,
            'status': 'error'}, out)

    def test_list_builds(self):
        cmd.main(['dib2cloud', '--config', 'some_config', 'list-builds'])
        out = json.loads(self.out.getvalue().decode('utf-8'))
        self.assertEqual([{
            'destinations': ['/some/dest'],
            'id': 'fake-uuid',
            'log': '/some/logfile',
            'name': 'fake_diskimage',
            'pid': None,
            'status': 'error'}], out)

    def test_delete_build(self):
        cmd.main(['dib2cloud', '--config', 'some_config',
                  'delete-build', '123'])
        out = json.loads(self.out.getvalue().decode('utf-8'))
        self.assertEqual({
            'destinations': ['/some/dest'],
            'id': 'fake-uuid',
            'log': '/some/logfile',
            'name': 'fake_diskimage',
            'pid': None,
            'status': 'deleted'}, out)


class TestApp(base.TestCase):
    def setUp(self):
        super(TestApp, self).setUp()

        class FakePopen(object):
            pid = 123

        self.popen_cmd = None

        def mock_popen(cmd, stderr, stdout):
            destnext = False
            dest = None
            typenext = False
            type_ = None
            for arg in cmd:
                if destnext:
                    destnext = False
                    dest = arg
                if typenext:
                    typenext = False
                    type_ = arg
                if arg == '-o':
                    destnext = True
                elif arg == '-t':
                    typenext = True
            if dest:
                type_ = type_ or 'qcow2'
                open('%s.%s' % (dest, type_), 'w')
            self.popen_cmd = cmd
            return FakePopen()

        self.useFixture(fixtures.MonkeyPatch('subprocess.Popen', mock_popen))

    def test_build_image_simple(self):
        config_path = self.useFixture(ConfigFixture('simple')).path
        d2c = app.App(config_path=config_path)
        dib = d2c.build_image('test_diskimage')
        self.assertEqual(['disk-image-create', '-t', 'qcow2', '-o',
                          dib.dest_path, 'element1', 'element2'],
                         self.popen_cmd)

    def test_get_local_images_empty(self):
        config_path = self.useFixture(ConfigFixture('simple')).path
        d2c = app.App(config_path=config_path)
        self.assertEqual([], d2c.get_local_images())

    def test_get_local_images_simple_missing_output(self):
        config_path = self.useFixture(ConfigFixture('simple')).path
        d2c = app.App(config_path=config_path)
        dib = d2c.build_image('test_diskimage')
        for path in dib.dest_paths:
            os.unlink(path)
        dibs = d2c.get_local_images()
        self.assertEqual(1, len(dibs))
        self.assertEqual((False, app.DibError.OutputMissing),
                         dibs[0].succeeded())

    def test_get_local_images_simple(self):
        config_path = self.useFixture(ConfigFixture('simple')).path
        d2c = app.App(config_path=config_path)
        d2c.build_image('test_diskimage')
        dibs = d2c.get_local_images()
        self.assertEqual(1, len(dibs))
        self.assertEqual((True, None), dibs[0].succeeded())

    def test_delete_build_simple(self):
        config_path = self.useFixture(ConfigFixture('simple')).path
        d2c = app.App(config_path=config_path)
        build = d2c.build_image('test_diskimage')
        self.assertEqual(True, all(map(os.path.exists, build.dest_paths)))

        del_build = d2c.delete_image('%s' % build.uuid)
        self.assertEqual(build.uuid, del_build.uuid)

        self.assertEqual(False, any(map(os.path.exists, build.dest_paths)))
        dibs = d2c.get_local_images()
        self.assertEqual(0, len(dibs))


class TestPythonProcess(base.TestCase):
    def test_python_process(self):
        recv, send = multiprocessing.Pipe()

        def put_pid(dest):
            send.send(os.getpid())

        proc = process.PythonProcess(put_pid, send)
        ch_pid = proc.start()
        queue_pid = recv.recv()
        self.assertEqual(ch_pid, queue_pid)
        self.assertNotEqual(queue_pid, os.getpid())
