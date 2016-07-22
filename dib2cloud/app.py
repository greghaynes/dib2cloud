import errno
import os
import uuid

import os_client_config
import shade

from dib2cloud import config
from dib2cloud import process
from dib2cloud import util


def gen_uuid():
    return uuid.uuid4().hex


class Upload(process.ProcessTracker):
    process_properties = [
        'build_uuid',
        'image_format',
        'cloud_name',
        'glance_uuid'
    ]

    @staticmethod
    def from_uuid(upload_pf_dir, uuid, build_pf_dir):
        return process.ProcessTracker.from_uuid(Upload, upload_pf_dir, uuid,
                                                build_pf_dir=build_pf_dir)

    def __init__(self, pf_dir, build_pf_dir, uuid, build_uuid,
                 image_format, cloud_name, glance_uuid=None, pid=None):
        super(Upload, self).__init__(uuid, pf_dir, pid)
        self.build_uuid = build_uuid
        self.image_format = image_format
        self.cloud_name = cloud_name
        self.glance_uuid = glance_uuid

        self.build = Build.from_uuid(build_pf_dir, build_uuid)
        self._client_config = None

    @property
    def upload_name(self):
        return '%s-%s' % (self.build.name, self.uuid)

    def _get_process(self):
        # Do some init so we can fail in the calling process if needed
        self._cloud = shade.openstack_cloud(cloud=self.cloud_name)
        return process.PythonProcess(self._do_upload)

    def _do_upload(self):
        filename = self.build.dest_path_for_format(self.image_format)
        image = self._cloud.create_image(self.upload_name, filename=filename,
                                         disk_format=self.image_format,
                                         conatiner_format='bare')
        self.glance_uuid = image.id
        self.update_processfile()
        


class DibError(object):
    OutputMissing = 0
    StillRunning = 1


class Build(process.ProcessTracker):
    process_properties = [
        'log_dir',
        'images_dir',
        'image_config',
        'output_formats'
    ]

    @staticmethod
    def get_all(pf_dir):
        builds = []
        if os.path.exists(pf_dir):
            for pf in os.listdir(pf_dir):
                if pf.endswith('processfile'):
                    builds.append(Build.from_processfile(
                        os.path.join(pf_dir, pf)
                    ))
        return builds

    @staticmethod
    def from_processfile(pf):
        return process.ProcessTracker.from_processfile(Build, pf)

    @staticmethod
    def from_uuid(pf_dir, uuid):
        return process.ProcessTracker.from_uuid(Build, pf_dir, uuid)

    def __init__(self, log_dir, pf_dir, images_dir,
                 image_config, uuid, output_formats, pid=None):
        super(Build, self).__init__(uuid, pf_dir, pid)
        self.name = image_config['name']
        self.log_dir = log_dir
        self.images_dir = images_dir
        self.image_config = image_config
        self.output_formats = output_formats

    @property
    def dib_cmd(self):
        return ['disk-image-create', '-t', ','.join(self.output_formats),
                '-o', self.dest_path] + self.image_config['elements']

    @property
    def log_path(self):
        log_dir = os.path.join(self.log_dir, self.image_config['name'])
        util.assert_dir(log_dir)
        return os.path.join(log_dir, '%s.log' % self.uuid)

    @property
    def dest_dir(self):
        dest_dir = os.path.join(self.images_dir, self.name)
        util.assert_dir(dest_dir)
        return dest_dir

    @property
    def dest_path(self):
        return os.path.join(self.dest_dir, '%s' % (self.uuid))

    @property
    def dest_paths(self):
        return [self.dest_path_for_format(x) for x in self.output_formats]

    def dest_path_for_format(self, img_format):
        return os.path.join(self.dest_dir, '%s.%s' % (self.uuid, img_format))

    def _get_process(self):
        log_fh = open(self.log_path, 'w')
        return process.CmdProcess(self.dib_cmd, stdout=log_fh, stderr=log_fh)

    def succeeded(self):
        if self.is_running():
            return False, DibError.StillRunning
        if not all(map(os.path.exists, self.dest_paths)):
            return False, DibError.OutputMissing
        return True, None


class App(object):
    def __init__(self, config_path):
        self.config = config.Config.from_yaml_file(config_path)

    def build_image(self, name, blocking=False):
        # TODO(greghaynes) determine output_formats based on provider
        output_formats = ['qcow2']
        config = None
        if name.startswith('dib2cloud_'):
            config = config.Config.get_default_diskimages()[name]
        else:
            config = self.config.get_by_name('diskimages', name)

        build = Build(self.config['buildlog_dir'],
                        self.config.build_processfile_dir,
                        self.config['images_dir'],
                        config,
                        gen_uuid(),
                        output_formats)
        build.run(blocking)
        return build

    def get_local_images(self):
        return Build.get_all(self.config.build_processfile_dir)

    def delete_image(self, build_uuid):
        pf_path = os.path.join(self.config.build_processfile_dir,
                               '%s.processfile' % build_uuid)
        if not os.path.exists(pf_path):
            raise ValueError('No build with id %s found' % build_uuid)
        build = Build.from_processfile(pf_path)
        if build.is_running():
            raise ValueError('Cannot delete build %s while it is running' %
                             build_uuid)
        for path in build.dest_paths:
            try:
                os.unlink(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
        os.unlink(pf_path)
        return build

    def upload_image(self, build_uuid, provider_name, blocking=False):
        provider_config = None
        if provider_name.startswith('dib2cloud_'):
            default_providers = config.Config.get_default_providers()
            provider_config = default_providers[provider_name]
        else:
            provider_config = self.config.get_by_name('providers',
                                                       provider_name)

        upload = Upload(self.config.upload_processfile_dir,
                        self.config.build_processfile_dir,
                        gen_uuid(),
                        build_uuid,
                        'qcow2',
                        provider_config['cloud'],
                        provider_config)
        upload.run(blocking)
        return upload

    def get_upload(self, upload_uuid):
        return Upload.from_uuid(self.config.upload_processfile_dir, 
                                upload_uuid,
                                self.config.build_processfile_dir)
