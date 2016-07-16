import errno
import os
import subprocess
import uuid

from dib2cloud import config
from dib2cloud import process
from dib2cloud import util


def gen_uuid():
    return uuid.uuid4().hex


def get_dib_processes(processfile_dir):
    processes = []
    if os.path.exists(processfile_dir):
        for pf in os.listdir(processfile_dir):
            if pf.endswith('processfile'):
                processes.append(process.from_processfile(
                    Build,
                    os.path.join(processfile_dir, pf)
                ))
    return processes


class DibError(object):
    OutputMissing = 0
    StillRunning = 1


class Build(process.Process):
    process_properties = [
        'log_dir',
        'images_dir',
        'image_config',
        'output_formats'
    ]

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
        return [os.path.join(self.dest_dir, '%s.%s' % (self.uuid, x))
                for x in self.output_formats]

    def _exec(self):
        with open(self.log_path, 'w') as log_fh:
            proc = subprocess.Popen(self.dib_cmd, stdout=log_fh, stderr=log_fh)
        return proc

    def succeeded(self):
        if self.is_running():
            return False, DibError.StillRunning
        if not all(map(os.path.exists, self.dest_paths)):
            return False, DibError.OutputMissing
        return True, None


class App(object):
    def __init__(self, config_path):
        self.config = config.Config.from_yaml_file(config_path)

    def build_image(self, name):
        # TODO(greghaynes) determine output_formats based on provider
        output_formats = ['qcow2']
        config = None
        if name.startswith('dib2cloud_'):
            config = config.Config.get_default_diskimages()[name]
        else:
            config = self.config.get_diskimage_by_name(name)

        process = Build(self.config['buildlog_dir'],
                        os.path.join(self.config.build_pf_dir),
                        self.config['images_dir'],
                        config,
                        gen_uuid(),
                        output_formats)
        process.run()
        return process

    def get_local_images(self):
        return get_dib_processes(self.config.build_pf_dir)

    def delete_image(self, image_id):
        pf_path = os.path.join(self.config.build_pf_dir,
                               '%s.processfile' % image_id)
        if not os.path.exists(pf_path):
            raise ValueError('No build with id %s found' % image_id)
        build = process.from_processfile(Build, pf_path)
        if build.is_running():
            raise ValueError('Cannot delete build %s while it is running' %
                             image_id)
        for path in build.dest_paths:
            try:
                os.unlink(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
        os.unlink(pf_path)
        return build
