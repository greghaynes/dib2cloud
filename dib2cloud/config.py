import os

import yaml


DEFAULT_PROCESSFILE_DIR = os.path.expanduser('~/.dib2cloud')
DEFAULT_BUILDLOG_DIR = os.path.expanduser('~/.dib2cloud')
DEFAULT_IMAGES_DIR = os.path.expanduser('~/.dib2cloud')


class ConfigDict(dict):
    def __init__(self, properties, sub_kwargs):
        self.properties = properties
        for key, val in sub_kwargs.items():
            self[key] = val


class Diskimage(ConfigDict):
    def __init__(self, **kwargs):
        super(Diskimage, self).__init__(['name',
                                         'elements',
                                         'release',
                                         'env_vars'], kwargs)


class Provider(ConfigDict):
    def __init__(self, **kwargs):
        super(Provider, self).__init__(['name',
                                        'cloud'], kwargs)


class Config(ConfigDict):
    @staticmethod
    def get_default_diskimages():
        return {'dib2cloud-ubuntu-debootstrap': Diskimage(
            name='dib2cloud-ubuntu-debootstrap',
            elements=['ubuntu-minimal', 'simple-init']
        )}

    @classmethod
    def from_yaml_file(cls, path):
        config_dict = {}

        if os.path.exists(path):
            with open(path, 'r') as fh:
                config_dict = yaml.safe_load(fh)

        diskimages = [Diskimage(**x) for x in
                      config_dict.get('diskimages', [])]
        providers = [Provider(**x) for x in
                     config_dict.get('providers', [])]
        processfile_dir = config_dict.get('processfile_dir',
                                          DEFAULT_PROCESSFILE_DIR)
        buildlog_dir = config_dict.get('buildlog_dir',
                                       DEFAULT_BUILDLOG_DIR)
        images_dir = config_dict.get('images_dir',
                                     DEFAULT_IMAGES_DIR)

        return Config(diskimages=diskimages,
                      providers=providers,
                      processfile_dir=processfile_dir,
                      buildlog_dir=buildlog_dir,
                      images_dir=images_dir)

    def __init__(self, **kwargs):
        super(Config, self).__init__(['diskimages',
                                      'providers',
                                      'processfile_dir',
                                      'buildlog_dir',
                                      'images_dir'], kwargs)

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            yaml.safe_dump(self, fh)

    def get_diskimage_by_name(self, name):
        ret = None
        for di in self.get('diskimages', []):
            if di['name'] == name:
                if ret is not None:
                    raise ValueError('Multiple diskimages with name %s' % name)
                else:
                    ret = di
        if ret is None:
            raise ValueError('No image with name %s found in config' % name)
        return ret


yaml.representer.SafeRepresenter.add_representer(
    Diskimage,
    yaml.representer.SafeRepresenter.represent_dict
)


yaml.representer.SafeRepresenter.add_representer(
    Provider,
    yaml.representer.SafeRepresenter.represent_dict
)


yaml.representer.SafeRepresenter.add_representer(
    Config,
    yaml.representer.SafeRepresenter.represent_dict
)
