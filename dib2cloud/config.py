import yaml


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
    def from_yaml_file(path):
        config_dict = None
        with open(path, 'r') as fh:
            config_dict = yaml.safe_load(fh)

        diskimages = [Diskimage(**x) for x in
                      config_dict.get('diskimages', [])]
        providers = [Provider(**x) for x in
                     config_dict.get('providers', [])]

        return Config(diskimages=diskimages,
                      providers=providers)

    def __init__(self, **kwargs):
        super(Config, self).__init__(['diskimages',
                                      'providers'], kwargs)

    def to_yaml_file(self, path):
        with open(path, 'w') as fh:
            yaml.safe_dump(self, fh)


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
