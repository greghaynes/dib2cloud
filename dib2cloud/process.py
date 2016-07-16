import os
import time

import yaml

from dib2cloud import util


def from_processfile(process_type, path):
    with open(path, 'r') as fh:
        return process_type(**yaml.safe_load(fh))


class Process(object):
    def __init__(self, uuid, pf_dir, pid=None):
        self.uuid = uuid
        self.pf_dir = pf_dir
        self.pid = pid
        self._proc = None

    @property
    def processfile_path(self):
        util.assert_dir(self.pf_dir)
        return os.path.join(self.pf_dir, '%s.processfile' % self.uuid)

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            out = {}
            for attr in self.process_properties + ['uuid', 'pf_dir', 'pid']:
                out[attr] = getattr(self, attr)
            yaml.safe_dump(out, fh)

    def run(self):
        if self.pid:
            raise RuntimeError('Image build for image uuid %s with name %s has'
                               ' already been run.', self.uuid, self.name)
        self._proc = self._exec()
        self.pid = self._proc.pid
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
