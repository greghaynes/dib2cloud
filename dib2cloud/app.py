import os
import subprocess
import uuid

import yaml

from dib2cloud import config


def gen_uuid():
    return uuid.uuid4().hex


class DibProcess(object):
    @staticmethod
    def from_processfile(log_dir, path):
        with open(path, 'r') as fh:
            return DibProcess(log_dir, **yaml.safe_load(fh))

    def __init__(self, log_dir, processfile_dir, image_config, uuid, pid=None):
        self.log_dir = log_dir
        self.pf_dir = processfile_dir
        self.image_config = image_config
        self.uuid = uuid
        self.pid = None

    @property
    def processfile_path(self):
        return os.path.join(self.pf_dir, '%s.processfile' % self.uuid)

    @property
    def dib_cmd(self):
        return ['disk-image-create'] + self.image_config['elements']

    @property
    def log_path(self):
        log_dir = os.path.join(self.log_dir, self.image_config['name'])
        os.makedirs(log_dir)
        return os.path.join(log_dir, self.uuid)

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            out = {}
            for attr in ('image_config', 'uuid', 'pid'):
                out[attr] = getattr(self, attr)
            yaml.safe_dump(out, fh)

    def exec_dib(self):
        with open(self.log_path, 'w') as log_fh:
            self.pid = subprocess.Popen(self.dib_cmd,
                                        stdout=log_fh,
                                        stderr=log_fh).pid
        return self.pid

    def run(self):
        if self.pid:
            raise RuntimeError('Image build for image uuid %s with name %s has'
                               ' already been run.', self.uuid, self.name)
        self.exec_dib()
        self.to_yaml_file(self.processfile_path)


class App(object):
    def __init__(self, config_path):
        self.config = config.Config.from_yaml_file(config_path)

    def build_image(self, name):
        process = DibProcess(self.config['buildlog_dir'],
                             self.config['processfile_dir'],
                             self.config.get_diskimage_by_name(name),
                             gen_uuid())
        process.run()
