import os

import yaml


DEFAULT_BUILD_PROCESSFILE_DIR = os.path.expanduser('~/.dib2cloud/run/builds')
DEFAULT_UPLOAD_PROCESSFILE_DIR = os.path.expanduser('~/.dib2cloud/run/uploads')
DEFAULT_BUILDLOG_DIR = os.path.expanduser('~/.dib2cloud/logs/builds')
DEFAULT_IMAGES_DIR = os.path.expanduser('~/.dib2cloud/images')


class ConfigValueMissingError(Exception):
    pass


class ConfigKeyInvalidError(Exception):
    pass


class ConfigFlattenError(Exception):
    pass


class ConfigItemNotFoundError(Exception):
    pass


class ConfigMultipleItemsError(Exception):
    pass


class ConfigValue(object):
    def flatten(self):
        raise ConfigFlattenError('Subclass did not reimplement flatten')


class ConfigDict(ConfigValue):
    defaults = {}

    def __init__(self, properties, sub_kwargs):
        self.properties = set(properties)
        self._values = {}
        for key, val in sub_kwargs.items():
            if key not in properties:
                raise ConfigKeyInvalidError(
                    'Key %s is not a valid configuration key' % key
                )
            self._values[key] = val

        for prop in properties:
            if prop not in self._values and prop not in self.defaults:
                raise ConfigValueMissingError(
                    'Missing value for required property %s' % prop
                )

    def get(self, prop):
        try:
            return self._values[prop]
        except KeyError:
            try:
                return self.defaults[prop]
            except KeyError:
                raise ConfigValueMissingError(
                    'Unable to get value for property %s' % prop
                )

    def set(self, prop, val):
        self._values[prop] = val

    def flatten(self):
        ret = {}
        for key, val in self._values.items():
            if isinstance(val, ConfigValue):
                ret[key] = val.flatten()
            else:
                ret[key] = val
        return ret


class ConfigCollection(ConfigValue):
    defaults = []

    def __init__(self, items):
        self._items = items

    def get_one(self, item_property, val):
        found, ret = self._filter_sequence(self._items, item_property, val)
        if found:
            return ret
        else:
            found, ret = self._filter_sequence(self.defaults,
                                               item_property,
                                               val)
            if found:
                return ret
            else:
                return ConfigItemNotFoundError(
                    'No item with property %s=%s found'
                    % (item_property, val)
                )

    def to_list(self):
        return self._items

    def _filter_sequence(self, sequence, prop, val):
        ret = None
        found = False
        for item in sequence:
            if item.get(prop) == val:
                if not found:
                    ret = item
                    found = True
                else:
                    raise ConfigMultipleItemsError(
                        'Multiple items with property %s=%s' % (prop, val)
                    )
        return found, ret

    def flatten(self):
        ret = []
        for item in self._items:
            if isinstance(item, ConfigValue):
                ret.append(item.flatten())
            else:
                ret.append(item)
        return ret


class Diskimage(ConfigDict):
    defaults = {
        'env_vars': []
    }

    def __init__(self, **kwargs):
        super(Diskimage, self).__init__(['name',
                                         'elements',
                                         'env_vars'], kwargs)


class Provider(ConfigDict):
    def __init__(self, **kwargs):
        super(Provider, self).__init__(['name',
                                        'cloud'], kwargs)


class DiskimagesCollection(ConfigCollection):
    defaults = [
        Diskimage(name='dib2cloud-ubuntu-debootstrap',
                  elements=['ubuntu-minimal', 'simple-init'])
    ]


class Config(ConfigDict):
    defaults = {
        'build_processfile_dir': DEFAULT_BUILD_PROCESSFILE_DIR,
        'upload_processfile_dir': DEFAULT_UPLOAD_PROCESSFILE_DIR,
        'buildlog_dir': DEFAULT_BUILDLOG_DIR,
        'images_dir': DEFAULT_IMAGES_DIR,
        'providers': [],
        'diskimages': []
    }

    @classmethod
    def from_yaml_file(cls, path):
        config_dict = {}

        if os.path.exists(path):
            with open(path, 'r') as fh:
                config_dict = yaml.safe_load(fh)

        return Config(**config_dict)

    def __init__(self, **kwargs):
        if 'diskimages' in kwargs:
            kwargs['diskimages'] = DiskimagesCollection(
                [Diskimage(**x) for x in kwargs['diskimages']]
            )

        if 'providers' in kwargs:
            kwargs['providers'] = ConfigCollection(
                [Provider(**x) for x in kwargs['providers']]
            )
        super(Config, self).__init__(['diskimages',
                                      'providers',
                                      'build_processfile_dir',
                                      'upload_processfile_dir',
                                      'buildlog_dir',
                                      'images_dir'], kwargs)

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            yaml.safe_dump(self, fh)


def represet_config_dict(dumper, data):
    return yaml.representer.SafeRepresenter.represent_dict(dumper,
                                                           data.flatten())


yaml.representer.SafeRepresenter.add_representer(
    Diskimage,
    represet_config_dict
)


yaml.representer.SafeRepresenter.add_representer(
    Provider,
    represet_config_dict
)


yaml.representer.SafeRepresenter.add_representer(
    Config,
    represet_config_dict
)
