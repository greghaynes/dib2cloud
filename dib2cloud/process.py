import errno
import fcntl
import os
import signal
import subprocess
import time

import yaml

from dib2cloud import util


def sigchld_handler(signum, frame):
    try:
        os.waitpid(0, 0)
    except OSError as e:
        if e.errno == errno.ECHILD:
            # Child process was already reaped
            pass


signal.signal(signal.SIGCHLD, sigchld_handler)


class Process(object):
    def __init__(self, pid=None):
        self.pid = None

    def start(self, blocking=False):
        self.pid = self._run(blocking)
        return self.pid


class PythonProcess(Process):
    def __init__(self, func, *args, **kwargs):
        super(Process, self).__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _run(self, blocking=False):
        if not blocking:
            chpid = os.fork()
            if chpid != 0:
                # We are the parent
                return chpid
            else:
                # We are the child
                self._func(*self._args, **self._kwargs)
                # Become the session and group leader
                os.setsid()
                # Use _exit so we don't call any atexit registered functions of
                # our parent. This has the downside of not flushing any stdio
                # fd's so care must be taken when using things like
                # multiprocessing.Queue which rely on a separate i/o thread
                os._exit(0)
        else:
            self._func(*self._args, **self._kwargs)


class CmdProcess(Process):
    def __init__(self, cmd, stdout, stderr):
        super(Process, self).__init__()
        self._cmd = cmd
        self._stdout = stdout
        self._stderr = stderr
        self._proc = None

    def _run(self, blocking=False):
        self._subproc = subprocess.Popen(self._cmd,
                                         stdout=self._stdout,
                                         stderr=self._stderr)
        self._subproc.wait()
        return self._subproc.pid


def processfile_for_uuid(pf_dir, uuid):
    return os.path.join(pf_dir, '%s.processfile' % uuid)


class LockedFile(object):
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.fh = open(self.path, 'w')
        fcntl.lockf(self.fh, fcntl.LOCK_EX)
        return self.fh

    def __exit__(self, exc_type, exc_value, traceback):
        fcntl.lockf(self.fh, fcntl.LOCK_UN)
        self.fh.close()


class ProcessTracker(object):
    @staticmethod
    def from_processfile(pt_type, pf, **extra_kwargs):
        with open(pf, 'r') as fh:
            kwargs = yaml.safe_load(fh)
            kwargs.update(extra_kwargs)
            return pt_type(**kwargs)

    @classmethod
    def get_all(cls, pt_type, pf_dir, **extra_kwargs):
        pts = []
        if os.path.exists(pf_dir):
            for pf in os.listdir(pf_dir):
                if pf.endswith('processfile'):
                    pts.append(cls.from_processfile(
                        pt_type,
                        os.path.join(pf_dir, pf),
                        **extra_kwargs
                    ))
        return pts

    @classmethod
    def from_uuid(cls, pt_type, pf_dir, uuid, **extra_kwargs):
        return cls.from_processfile(pt_type,
                                    processfile_for_uuid(pf_dir, uuid),
                                    **extra_kwargs)

    def __init__(self, uuid, pf_dir, pid=None):
        self.uuid = uuid
        self.pf_dir = pf_dir
        self.pid = pid
        self._proc = None

    @property
    def processfile(self):
        util.assert_dir(self.pf_dir)
        return LockedFile(processfile_for_uuid(self.pf_dir, self.uuid))

    def to_yaml_file(self, dest):
        with dest as fh:
            out = {}
            for attr in self.process_properties + ['uuid', 'pf_dir', 'pid']:
                out[attr] = getattr(self, attr)
            yaml.safe_dump(out, fh)

    def update_processfile(self):
        self.to_yaml_file(self.processfile)

    def run(self, blocking=False):
        if self.pid:
            raise RuntimeError('Image build for image uuid %s with name %s has'
                               ' already been run.', self.uuid, self.name)
        self._proc = self._get_process()
        self._proc.start(blocking)
        self.pid = self._proc.pid
        self.to_yaml_file(self.processfile)

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
