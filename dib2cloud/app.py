import errno
import os
import subprocess
import time
import uuid

import yaml

from dib2cloud import config


def gen_uuid():
    return uuid.uuid4().hex


def get_dib_processes(processfile_dir):
    processes = []
    for pf in os.listdir(processfile_dir):
        processes.append(DibProcess.from_processfile(
            os.path.join(processfile_dir, pf)
        ))
    return processes


class DibError(object):
    OutputMissing = 0
    StillRunning = 1


class DibProcess(object):
    @staticmethod
    def from_processfile(path):
        with open(path, 'r') as fh:
            return DibProcess(**yaml.safe_load(fh))

    def __init__(self, name, log_dir, pf_dir, images_dir,
                 image_config, uuid, output_formats, pid=None):
        self.name = name
        self.log_dir = log_dir
        self.pf_dir = pf_dir
        self.images_dir = images_dir
        self.image_config = image_config
        self.uuid = uuid
        self.output_formats = output_formats
        self.pid = pid
        self._proc = None

    @property
    def processfile_path(self):
        try:
            os.makedirs(self.pf_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return os.path.join(self.pf_dir, '%s.processfile' % self.uuid)

    @property
    def dib_cmd(self):
        return ['disk-image-create', '-t', ','.join(self.output_formats),
                '-o', self.dest_path] + self.image_config['elements']

    @property
    def log_path(self):
        log_dir = os.path.join(self.log_dir, self.image_config['name'])
        try:
            os.makedirs(log_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return os.path.join(log_dir, self.uuid)

    @property
    def dest_path(self):
        return os.path.join(self.images_dir, '%s' % (self.uuid))

    @property
    def dest_paths(self):
        return [os.path.join(self.images_dir, '%s.%s' % (self.uuid, x))
                for x in self.output_formats]

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            out = {}
            for attr in ('name', 'log_dir', 'pf_dir', 'images_dir',
                         'image_config', 'uuid', 'output_formats', 'pid'):
                out[attr] = getattr(self, attr)
            yaml.safe_dump(out, fh)

    def exec_dib(self):
        with open(self.log_path, 'w') as log_fh:
            self._proc = subprocess.Popen(self.dib_cmd,
                                          stdout=log_fh,
                                          stderr=log_fh)
            self.pid = self._proc.pid
        return self.pid

    def run(self):
        if self.pid:
            raise RuntimeError('Image build for image uuid %s with name %s has'
                               ' already been run.', self.uuid, self.name)
        self.exec_dib()
        self.to_yaml_file(self.processfile_path)

    def wait(self, timeout=None):
        if self._proc is not None:
            self._proc.wait(timeout)
        else:
            while True:
                if self.is_running():
                    return True
                else:
                    time.sleep(.5)

    def is_running(self):
        try:
            os.kill(self.pid, 0)
        except OSError:
            return False
        return True

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

        process = DibProcess(name,
                             self.config['buildlog_dir'],
                             self.config['processfile_dir'],
                             self.config['images_dir'],
                             self.config.get_diskimage_by_name(name),
                             gen_uuid(),
                             output_formats)
        process.run()
        return process

    def get_local_images(self):
        return get_dib_processes(self.config['processfile_dir'])
